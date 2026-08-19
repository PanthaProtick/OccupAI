import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
app = create_app(Settings())


class BackendApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_health_reports_mock_source(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "data_source": "mock"})

    def test_rooms_use_canonical_identifiers(self) -> None:
        response = self.client.get("/api/rooms")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["count"], 7)
        self.assertEqual(payload["data"][0]["camera_id"], "cam_001")
        self.assertEqual(len({room["room_id"] for room in payload["data"]}), 7)
        self.assertEqual(len({room["camera_id"] for room in payload["data"]}), 7)

    def test_stale_camera_preserves_last_known_occupancy(self) -> None:
        response = self.client.get("/api/occupancy/cam_003")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "stale")
        self.assertEqual(data["occupancy"], 48)

    def test_offline_camera_is_not_reported_as_zero_occupancy(self) -> None:
        response = self.client.get("/api/occupancy/cam_006")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "offline")
        self.assertIsNone(data["occupancy"])
        self.assertIsNone(data["occupancy_percentage"])
        self.assertEqual(data["raw_occupancy"], 0)

    def test_history_supports_each_documented_aggregation(self) -> None:
        expected_counts = {"hour": 168, "day": 7, "week": 1}
        for history_range, expected_count in expected_counts.items():
            with self.subTest(history_range=history_range):
                response = self.client.get(
                    "/api/history",
                    params={"room_id": "room_cse_201", "range": history_range, "metric": "percentage"},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["meta"]["count"], expected_count)
                self.assertEqual(payload["data"][0]["coverage_percentage"], 100.0)

    def test_unknown_camera_uses_standard_error_shape(self) -> None:
        response = self.client.get("/api/occupancy/cam_999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "camera_not_found")

    def test_invalid_history_query_returns_400(self) -> None:
        response = self.client.get(
            "/api/history",
            params={"room_id": "room_cse_201", "range": "month", "metric": "percentage"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_checked_in_contract_matches_application(self) -> None:
        contract_path = PROJECT_ROOT / "contracts" / "openapi.yaml"
        checked_in = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(checked_in, app.openapi())


if __name__ == "__main__":
    unittest.main()
