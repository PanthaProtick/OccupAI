from __future__ import annotations

import json
import logging
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.assistant import AssistantProviderRequest
from backend.config import Settings
from backend.database import Base
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class CountingRepository(MockOccupancyRepository):
    assistant_snapshot_calls = 0

    def list_assistant_snapshots(self):
        self.assistant_snapshot_calls += 1
        return super().list_assistant_snapshots()


class SlowProvider:
    name = "slow-test-provider"

    def rewrite(self, _: AssistantProviderRequest) -> str:
        time.sleep(0.15)
        return "This response arrives too late."


class AssistantObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.url = f"sqlite:///{(Path(self.temp.name) / 'observability.db').as_posix()}"
        engine = create_engine(self.url)
        Base.metadata.create_all(engine)
        engine.dispose()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def signup(client: TestClient) -> dict:
        response = client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Observed Student", "email": "observed@aust.edu", "password": PASSWORD,
        })
        if response.status_code != 201:
            raise AssertionError(response.text)
        return response.json()["data"]

    @staticmethod
    def assistant_record(captured) -> dict:
        records = [json.loads(message.split(":", 2)[-1]) for message in captured.output]
        return next(record for record in records if record["event"] == "assistant_query")

    def test_success_log_is_structured_traceable_and_contains_no_sensitive_input(self):
        settings = Settings(
            database_url=self.url, auth_session_pepper="test-pepper-that-is-long-enough",
        )
        repository = CountingRepository(settings.mock_data_dir)
        app = create_app(settings, repository)
        with TestClient(app) as client:
            user = self.signup(client)
            sensitive_message = "Show free rooms; password: never-log-this"
            with self.assertLogs("backend.app", level=logging.INFO) as captured:
                response = client.post(
                    "/api/assistant/query", headers={"Origin": ORIGIN, "X-Request-ID":"assistant-trace-1"},
                    json={"message": sensitive_message},
                )
        self.assertEqual(response.status_code, 200)
        record = self.assistant_record(captured)
        self.assertEqual(record["request_id"], "assistant-trace-1")
        self.assertEqual(record["intent"], "find_available_rooms")
        self.assertEqual(record["result_count"], len(response.json()["results"]))
        self.assertEqual(record["provider_used"], "deterministic")
        self.assertFalse(record["fallback_used"])
        self.assertIsNone(record["error_category"])
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertEqual(len(record["user_reference"]), 20)
        serialized = json.dumps(record)
        for forbidden in (user["id"], user["email"], sensitive_message, "never-log-this", "password"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(repository.assistant_snapshot_calls, 1)
        self.assertLessEqual(len(response.json()["results"]), 10)

    def test_provider_timeout_is_bounded_and_logged_as_deterministic_fallback(self):
        settings = Settings(
            database_url=self.url, auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_provider="slow-test", assistant_model="test", assistant_api_key="never-log-key",
            assistant_timeout_seconds=0.02,
        )
        app = create_app(
            settings, CountingRepository(settings.mock_data_dir), assistant_provider=SlowProvider()
        )
        with TestClient(app) as client:
            self.signup(client)
            started = time.perf_counter()
            with self.assertLogs("backend.app", level=logging.INFO) as captured:
                response = client.post(
                    "/api/assistant/query", headers={"Origin":ORIGIN}, json={"message":"Free rooms"}
                )
            elapsed = time.perf_counter() - started
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 0.14)
        record = self.assistant_record(captured)
        self.assertEqual(record["provider_used"], "deterministic")
        self.assertTrue(record["fallback_used"])
        self.assertEqual(record["error_category"], "provider_timeout")
        self.assertNotIn("never-log-key", json.dumps(record))

    def test_disabled_request_logs_safe_error_category_without_message_content(self):
        settings = Settings(
            database_url=self.url, auth_session_pepper="test-pepper-that-is-long-enough",
            assistant_enabled=False,
        )
        app = create_app(settings, CountingRepository(settings.mock_data_dir))
        with TestClient(app) as client:
            self.signup(client)
            with self.assertLogs("backend.app", level=logging.INFO) as captured:
                response = client.post(
                    "/api/assistant/query", headers={"Origin":ORIGIN},
                    json={"message":"private assistant message"},
                )
        self.assertEqual(response.status_code, 503)
        record = self.assistant_record(captured)
        self.assertEqual(record["error_category"], "assistant_disabled")
        self.assertNotIn("private assistant message", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
