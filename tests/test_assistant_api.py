from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.config import Settings
from backend.database import Base
from backend.repositories import MockOccupancyRepository
from backend.assistant.architecture import BROWSER_SAFE_RESULT_FIELDS


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "assistant-api.db"
        url = f"sqlite:///{database.as_posix()}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        engine.dispose()
        self.settings = Settings(
            database_url=url,
            auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_rate_limit_attempts=2,
            assistant_rate_limit_window_seconds=60,
        )
        self.client = TestClient(create_app(
            self.settings, MockOccupancyRepository(self.settings.mock_data_dir)
        ))

    def tearDown(self):
        engine = self.client.app.state.auth_engine
        if engine is not None:
            engine.dispose()
        self.client.close()
        self.temp.cleanup()

    def signup(self):
        response = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Assistant Student",
            "email": "assistant@aust.edu",
            "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]

    def test_query_requires_authentication(self):
        response = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message": "Free rooms"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_query_requires_configured_origin(self):
        self.signup()
        response = self.client.post("/api/assistant/query", json={"message": "Free rooms"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "invalid_origin")

    def test_query_returns_strict_safe_contract_with_only_trusted_room_fields(self):
        user = self.signup()
        created = self.client.post(
            "/api/assistant/query",
            headers={"Origin": ORIGIN},
            json={"message": "Free rooms"},
        )
        self.assertEqual(created.status_code, 200)
        conversation_id = created.json()["conversation_id"]
        response = self.client.post(
            "/api/assistant/query",
            headers={"Origin": ORIGIN},
            json={"message": "  Give me free rooms.  ", "conversation_id": conversation_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        payload = response.json()
        self.assertEqual(payload["conversation_id"], conversation_id)
        self.assertTrue(payload["results"])
        self.assertEqual(payload["applied_filters"]["limit"], 3)
        self.assertEqual(payload["warnings"], [])
        serialized = response.text.lower()
        for secret in ("password_hash", "token_hash", "database_url", "system_prompt"):
            self.assertNotIn(secret, serialized)
        self.assertNotIn(user["id"], payload["answer"])
        self.assertTrue(all(item["status"] == "online" for item in payload["results"]))
        self.assertTrue(all(set(item) == BROWSER_SAFE_RESULT_FIELDS for item in payload["results"]))

    def test_query_generates_conversation_id_when_absent(self):
        self.signup()
        response = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message": "Free rooms"}
        )
        self.assertEqual(response.status_code, 200)
        uuid.UUID(response.json()["conversation_id"])

    def test_query_exposes_only_validated_interpreted_filters(self):
        self.signup()
        response = self.client.post(
            "/api/assistant/query",
            headers={"Origin": ORIGIN},
            json={"message": "Find the top three free rooms on the ground and first floors below 40%"},
        )
        self.assertEqual(response.status_code, 200)
        filters = response.json()["applied_filters"]
        self.assertEqual(filters["floors"], [0, 1])
        self.assertEqual(filters["maximum_occupancy_percentage"], 40)
        self.assertEqual(filters["limit"], 3)
        self.assertEqual(
            [(item["floor"], item["name"]) for item in response.json()["results"]],
            [(0, "Girls' Common Room"), (0, "T.T. Ground")],
        )
        self.assertEqual(
            [item["occupancy_percentage"] for item in response.json()["results"]],
            sorted(item["occupancy_percentage"] for item in response.json()["results"]),
        )
        self.assertEqual(response.json()["warnings"], ["Only 2 reliable matches were available."])

    def test_percentage_only_query_executes_with_the_users_saved_floor_scope(self):
        self.signup()
        response = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN},
            json={"message": "Show rooms below 40% occupancy."},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["applied_filters"]["floors"], [0, 1])
        self.assertEqual(payload["applied_filters"]["maximum_occupancy_percentage"], 40)
        self.assertTrue(payload["results"])
        self.assertTrue(all(item["floor"] in {0, 1} for item in payload["results"]))
        self.assertTrue(all(item["occupancy_percentage"] < 40 for item in payload["results"]))
        self.assertNotIn("No room query was executed.", payload["warnings"])

    def test_queries_are_scoped_to_the_authenticated_users_used_floors(self):
        self.signup()
        defaults = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN},
            json={"message": "What are the quietest places right now?"},
        )
        self.assertEqual(defaults.status_code, 200, defaults.text)
        self.assertEqual(defaults.json()["applied_filters"]["floors"], [0, 1])
        self.assertTrue(all(item["floor"] in {0, 1} for item in defaults.json()["results"]))

        updated = self.client.patch(
            "/api/notification-preferences", headers={"Origin": ORIGIN},
            json={"favorite_floors": [7]},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        selected = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN},
            json={"message": "What are the quietest places right now?"},
        )
        self.assertEqual(selected.status_code, 200, selected.text)
        self.assertEqual(selected.json()["applied_filters"]["floors"], [0, 1, 7])
        self.assertTrue(all(item["floor"] in {0, 1, 7} for item in selected.json()["results"]))

    def test_explicit_unselected_floor_overrides_saved_floor_scope(self):
        self.signup()
        response = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN},
            json={"message": "Show available rooms on Floor 7"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["applied_filters"]["floors"], [7])
        self.assertTrue(all(item["floor"] == 7 for item in response.json()["results"]))
        self.assertFalse(any("not included in your used floors" in warning
                             for warning in response.json()["warnings"]))

    def test_query_rejects_empty_oversized_malformed_and_extra_input(self):
        self.signup()
        cases = (
            {"message": "   "},
            {"message": "x" * 1_001},
            {"message": "Free rooms", "conversation_id": "not-a-uuid"},
            {"message": "Free rooms", "user_id": "another-user"},
        )
        for body in cases:
            with self.subTest(fields=body.keys(), length=len(body["message"])):
                response = self.client.post(
                    "/api/assistant/query", headers={"Origin": ORIGIN}, json=body
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_validation_errors_never_echo_rejected_sensitive_input(self):
        self.signup()
        secret = "unique-secret-that-must-not-be-echoed"
        response = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN},
            json={"message": "Free rooms", "provider_api_key": secret},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(secret, response.text)
        self.assertNotIn("input", response.json()["error"]["details"]["errors"][0])

    def test_query_applies_per_user_and_per_ip_rate_limits(self):
        user = self.signup()
        for _ in range(2):
            response = self.client.post(
                "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message": "Free rooms"}
            )
            self.assertEqual(response.status_code, 200)
        blocked = self.client.post(
            "/api/assistant/query", headers={"Origin": ORIGIN}, json={"message": "Free rooms"}
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "rate_limit_exceeded")
        user_keys = self.client.app.state.assistant_user_rate_limiter._events
        ip_keys = self.client.app.state.assistant_ip_rate_limiter._events
        self.assertIn(f"assistant:user:{user['id']}", user_keys)
        self.assertIn("assistant:ip:testclient", ip_keys)


if __name__ == "__main__":
    unittest.main()
