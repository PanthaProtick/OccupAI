from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.config import Settings
from backend.database import Base
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class AssistantEndToEndSmokeTests(unittest.TestCase):
    """Exercise the release-critical assistant journey without an external provider."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "assistant-smoke.db"
        self.settings = Settings(
            database_url=f"sqlite:///{database.as_posix()}",
            auth_session_pepper="assistant-smoke-pepper-is-long-enough",
            assistant_provider="deterministic",
        )
        engine = create_engine(self.settings.database_url)
        Base.metadata.create_all(engine)
        engine.dispose()
        self.app = create_app(
            self.settings, MockOccupancyRepository(self.settings.mock_data_dir)
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        if self.app.state.auth_engine is not None:
            self.app.state.auth_engine.dispose()
        self.client.close()
        self.temp.cleanup()

    def signup(self, email: str, name: str = "Assistant Student"):
        response = self.client.post(
            "/api/auth/signup",
            headers={"Origin": ORIGIN},
            json={"name": name, "email": email, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_complete_persistent_owned_deterministic_assistant_journey(self):
        self.signup("assistant-smoke@aust.edu")
        self.assertIsNone(self.app.state.assistant_provider_coordinator.provider)

        answer = self.client.post(
            "/api/assistant/query",
            headers={"Origin": ORIGIN},
            json={"message": "Give me the top 3 free spaces on the ground and first floors"},
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        payload = answer.json()
        results = payload["results"]
        self.assertEqual(payload["applied_filters"]["floors"], [0, 1])
        self.assertLessEqual(len(results), 3)
        self.assertTrue(results)
        self.assertTrue(all(result["floor"] in {0, 1} for result in results))
        self.assertTrue(all(result["status"] == "online" for result in results))
        self.assertEqual(
            [result["occupancy_percentage"] for result in results],
            sorted(result["occupancy_percentage"] for result in results),
        )

        recommended_room = self.client.get(f"/api/rooms/{results[0]['room_id']}")
        self.assertEqual(recommended_room.status_code, 200)
        self.assertEqual(recommended_room.json()["data"]["room_id"], results[0]["room_id"])

        conversation_id = payload["conversation_id"]
        history = self.client.get(f"/api/assistant/conversations/{conversation_id}")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(
            [message["role"] for message in history.json()["messages"]],
            ["user", "assistant"],
        )

        self.assertEqual(
            self.client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code,
            204,
        )
        login = self.client.post(
            "/api/auth/login",
            headers={"Origin": ORIGIN},
            json={"email": "ASSISTANT-SMOKE@AUST.EDU", "password": PASSWORD},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(
            self.client.get(f"/api/assistant/conversations/{conversation_id}").status_code,
            200,
        )

        self.client.cookies.clear()
        self.signup("assistant-other@aust.edu", "Other Student")
        foreign = self.client.get(f"/api/assistant/conversations/{conversation_id}")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json()["error"]["code"], "conversation_not_found")

        deterministic = self.client.post(
            "/api/assistant/query",
            headers={"Origin": ORIGIN},
            json={"message": "Show the top 3 available rooms"},
        )
        self.assertEqual(deterministic.status_code, 200, deterministic.text)
        self.assertTrue(deterministic.json()["results"])
        self.assertTrue(
            all(result["status"] == "online" for result in deterministic.json()["results"])
        )


if __name__ == "__main__":
    unittest.main()
