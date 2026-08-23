import json
import logging
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.repositories.mock import MockOccupancyRepository


ROOT = Path(__file__).resolve().parents[1]


class OperationalTests(unittest.TestCase):
    def test_request_and_startup_logs_are_structured_and_traceable(self):
        app = create_app(Settings())
        with self.assertLogs("backend.app", level=logging.INFO) as captured:
            with TestClient(app) as client:
                response = client.get("/api/rooms", headers={"X-Request-ID": "operation-trace-1"})
        records = [json.loads(message.split(":", 2)[-1]) for message in captured.output]
        startup = next(item for item in records if item["event"] == "backend_startup")
        request = next(item for item in records if item["event"] == "request")
        self.assertEqual(startup["data_source"], "mock")
        self.assertNotIn("database_url", startup)
        self.assertEqual(request["request_id"], "operation-trace-1")
        self.assertEqual(response.headers["X-Request-ID"], "operation-trace-1")

    def test_cache_policy_distinguishes_metadata_and_live_state(self):
        with TestClient(create_app(Settings())) as client:
            rooms = client.get("/api/rooms")
            occupancy = client.get("/api/occupancy")
            docs = client.get("/docs")
        self.assertEqual(rooms.headers["Cache-Control"], "public, max-age=300")
        self.assertEqual(occupancy.headers["Cache-Control"], "no-store")
        self.assertEqual(docs.status_code, 200)

    def test_readiness_failure_is_sanitized_standard_error(self):
        class UnavailableRepository:
            generated_at = None
            def list_rooms(self):
                raise OSError("D:/secret/database.db")
            def close(self):
                pass

        with TestClient(create_app(Settings(), repository=UnavailableRepository()), raise_server_exceptions=False) as client:
            response = client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "not_ready")
        self.assertNotIn("secret", response.text)

    def test_lifespan_calls_repository_cleanup(self):
        class ClosableRepository(MockOccupancyRepository):
            closed = False
            def close(self):
                self.closed = True

        repository = ClosableRepository(ROOT / "mock" / "generated")
        with TestClient(create_app(Settings(), repository=repository)) as client:
            self.assertEqual(client.get("/health").status_code, 200)
        self.assertTrue(repository.closed)

    def test_database_startup_fails_clearly_without_migrations(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{(Path(directory) / 'empty.db').as_posix()}"
            with self.assertRaisesRegex(RuntimeError, "not migrated"):
                create_app(Settings(data_source="database", database_url=url))

    def test_invalid_operational_configuration_fails_early(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            Settings(raw_sample_interval_seconds=0)
        with self.assertRaisesRegex(ValueError, "DATA_SOURCE"):
            Settings(data_source="unknown")


if __name__ == "__main__":
    unittest.main()
