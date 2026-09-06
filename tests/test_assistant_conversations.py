from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select

from backend.app import create_app
from backend.config import PROJECT_ROOT, Settings
from backend.database import AssistantConversationRow, AssistantMessageRow, Base
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class AssistantConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "conversations.db"
        self.url = f"sqlite:///{self.path.as_posix()}"
        engine = create_engine(self.url)
        Base.metadata.create_all(engine)
        engine.dispose()
        self.settings = Settings(
            database_url=self.url,
            auth_session_pepper="test-pepper-that-is-long-enough",
        )
        self.app = create_app(
            self.settings, MockOccupancyRepository(self.settings.mock_data_dir)
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        if self.app.state.auth_engine is not None:
            self.app.state.auth_engine.dispose()
        self.client.close()
        self.temp.cleanup()

    def signup(self, email="assistant-history@aust.edu"):
        response = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "History Student", "email": email, "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]

    def ask(self, message="available rooms", conversation_id=None):
        body = {"message": message}
        if conversation_id:
            body["conversation_id"] = conversation_id
        return self.client.post("/api/assistant/query", headers={"Origin": ORIGIN}, json=body)

    def test_exchange_is_stored_transactionally_and_can_continue(self):
        self.signup()
        first = self.ask("free rooms on the ground floor")
        self.assertEqual(first.status_code, 200)
        conversation_id = first.json()["conversation_id"]
        second = self.ask("rooms below 40%", conversation_id)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["conversation_id"], conversation_id)

        detail = self.client.get(f"/api/assistant/conversations/{conversation_id}")
        self.assertEqual(detail.status_code, 200)
        messages = detail.json()["messages"]
        self.assertEqual([message["role"] for message in messages], [
            "user", "assistant", "user", "assistant",
        ])
        self.assertEqual(messages[0]["content"], "free rooms on the ground floor")
        self.assertIsNone(messages[0]["structured_results"])
        self.assertIn("results", messages[1]["structured_results"])
        combined = detail.text.lower()
        self.assertNotIn("password_hash", combined)
        self.assertNotIn("session_token", combined)
        self.assertNotIn("chain-of-thought", combined)

        engine = create_engine(self.url)
        with engine.connect() as db:
            self.assertEqual(len(list(db.execute(select(AssistantConversationRow)))), 1)
            self.assertEqual(len(list(db.execute(select(AssistantMessageRow)))), 4)
        engine.dispose()

    def test_list_is_bounded_paginated_newest_first_and_no_store(self):
        self.signup()
        first = self.ask("available rooms").json()["conversation_id"]
        second = self.ask("crowded rooms").json()["conversation_id"]
        page_one = self.client.get("/api/assistant/conversations?page=1&limit=1")
        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_one.headers["cache-control"], "no-store")
        self.assertEqual(page_one.json()["items"][0]["id"], second)
        self.assertEqual(page_one.json()["items"][0]["message_count"], 2)
        self.assertEqual(page_one.json()["next_page"], 2)
        page_two = self.client.get("/api/assistant/conversations?page=2&limit=1")
        self.assertEqual(page_two.json()["items"][0]["id"], first)
        self.assertIsNone(page_two.json()["next_page"])
        self.assertEqual(
            self.client.get("/api/assistant/conversations?limit=51").status_code, 400
        )

    def test_history_survives_logout_backend_restart_and_later_login(self):
        self.signup()
        conversation_id = self.ask().json()["conversation_id"]
        self.assertEqual(
            self.client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code, 204
        )
        restarted_app = create_app(
            self.settings, MockOccupancyRepository(self.settings.mock_data_dir)
        )
        with TestClient(restarted_app) as restarted_client:
            login = restarted_client.post(
                "/api/auth/login",
                headers={"Origin": ORIGIN},
                json={"email": "assistant-history@aust.edu", "password": PASSWORD},
            )
            self.assertEqual(login.status_code, 200)
            self.assertEqual(
                restarted_client.get(
                    f"/api/assistant/conversations/{conversation_id}"
                ).status_code,
                200,
            )

    def test_conversations_are_isolated_and_foreign_id_is_not_revealed(self):
        self.signup()
        conversation_id = self.ask().json()["conversation_id"]
        self.client.cookies.clear()
        self.signup("other-history@aust.edu")
        self.assertEqual(self.client.get("/api/assistant/conversations").json()["items"], [])
        for method in ("get", "delete"):
            response = getattr(self.client, method)(
                f"/api/assistant/conversations/{conversation_id}",
                headers={"Origin": ORIGIN},
            )
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "conversation_not_found")
        continuation = self.ask("available rooms", conversation_id)
        self.assertEqual(continuation.status_code, 404)
        self.assertEqual(continuation.json()["error"]["code"], "conversation_not_found")

    def test_delete_requires_origin_and_removes_only_selected_conversation(self):
        self.signup()
        keep = self.ask("available rooms").json()["conversation_id"]
        remove = self.ask("crowded rooms").json()["conversation_id"]
        self.assertEqual(
            self.client.delete(f"/api/assistant/conversations/{remove}").status_code, 403
        )
        deleted = self.client.delete(
            f"/api/assistant/conversations/{remove}", headers={"Origin": ORIGIN}
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/assistant/conversations/{remove}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/assistant/conversations/{keep}").status_code, 200)

    def test_malformed_conversation_id_is_rejected(self):
        self.signup()
        response = self.client.get("/api/assistant/conversations/not-a-uuid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")


class AssistantConversationMigrationTests(unittest.TestCase):
    def test_migration_upgrades_and_downgrades(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{(Path(directory) / 'migration.db').as_posix()}"
            config = Config(str(PROJECT_ROOT / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", url)
            command.upgrade(config, "head")
            engine = create_engine(url)
            self.assertTrue({"assistant_conversations", "assistant_messages"}.issubset(
                set(inspect(engine).get_table_names())
            ))
            command.downgrade(config, "0005")
            self.assertFalse({"assistant_conversations", "assistant_messages"} & set(
                inspect(engine).get_table_names()
            ))
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
