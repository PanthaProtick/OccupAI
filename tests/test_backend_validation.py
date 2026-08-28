import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.repositories.mock import FixtureError, MockOccupancyRepository


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "mock" / "generated"


class FixtureValidationTests(unittest.TestCase):
    def copied(self):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name)
        for name in MockOccupancyRepository.REQUIRED_FILES:
            (path / name).write_bytes((FIXTURES / name).read_bytes())
        return temporary, path

    def mutate(self, filename, callback):
        temporary, path = self.copied()
        payload = json.loads((path / filename).read_text())
        callback(payload)
        (path / filename).write_text(json.dumps(payload), encoding="utf-8")
        return temporary, path

    def assert_invalid(self, filename, callback, phrase="Invalid"):
        temporary, path = self.mutate(filename, callback)
        with temporary, self.assertRaisesRegex(FixtureError, phrase):
            MockOccupancyRepository(path)

    def test_all_twenty_mappings(self):
        repository = MockOccupancyRepository(FIXTURES)
        self.assertEqual([(r.room_id, r.camera_id) for r in repository.list_rooms()], [
            ("room_cse_201", "cam_001"), ("room_cse_202", "cam_002"),
            ("room_library_01", "cam_003"), ("room_library_02", "cam_004"),
            ("room_canteen", "cam_005"), ("room_ece_105", "cam_006"),
            ("room_common_01", "cam_007"), ("room_cse_301", "cam_008"),
            ("room_cse_302", "cam_009"), ("room_eee_101", "cam_010"),
            ("room_eee_201", "cam_011"), ("room_library_03", "cam_012"),
            ("room_auditorium", "cam_013"), ("room_seminar_01", "cam_014"),
            ("room_seminar_02", "cam_015"), ("room_canteen_02", "cam_016"),
            ("room_gym", "cam_017"), ("room_workshop", "cam_018"),
            ("room_common_02", "cam_019"), ("room_prayer", "cam_020")
        ])

    def test_duplicate_room_and_camera_ids(self):
        self.assert_invalid("rooms.json", lambda p: p["rooms"].__setitem__(1, deepcopy(p["rooms"][0])), "unique")
        self.assert_invalid("rooms.json", lambda p: p["rooms"][1].__setitem__("camera_id", p["rooms"][0]["camera_id"]), "unique")

    def test_invalid_room_ranges(self):
        self.assert_invalid("rooms.json", lambda p: p["rooms"][0].__setitem__("capacity", 0))
        self.assert_invalid("rooms.json", lambda p: p["rooms"][0].__setitem__("floor", -1))

    def test_invalid_live_occupancy_and_timestamp(self):
        self.assert_invalid("live_occupancy.json", lambda p: p["cameras"][0].__setitem__("occupancy", -1))
        self.assert_invalid("live_occupancy.json", lambda p: p["cameras"][0].__setitem__("updated_at", "not-a-time"))
        self.assert_invalid("live_occupancy.json", lambda p: p["cameras"][0].__setitem__("updated_at", "2026-08-19T13:00:00"))

    def test_missing_and_non_utc_generated_timestamps(self):
        self.assert_invalid("rooms.json", lambda p: p.pop("generated_at"))
        self.assert_invalid("rooms.json", lambda p: p.__setitem__("generated_at", "2026-08-19T19:00:00+06:00"))
        self.assert_invalid("historical_api_views.json", lambda p: p.pop("generated_at"))
        self.assert_invalid("historical_api_views.json", lambda p: p.__setitem__("generated_at", "2026-08-19T13:00:00"))

    def test_invalid_history_values_coverage_timestamp_and_order(self):
        def point(payload):
            return payload["views"]["range"]["hour"]["room_cse_201"]["metric"]["occupancy"][0]
        self.assert_invalid("historical_api_views.json", lambda p: point(p).__setitem__("value", -1))
        self.assert_invalid("historical_api_views.json", lambda p: point(p).__setitem__("coverage_percentage", 101))
        self.assert_invalid("historical_api_views.json", lambda p: point(p).__setitem__("coverage_percentage", -0.1))
        self.assert_invalid("historical_api_views.json", lambda p: point(p).__setitem__("bucket_start", "2026-08-12T00:00:00"))
        self.assert_invalid(
            "historical_api_views.json",
            lambda p: p["views"]["range"]["hour"]["room_cse_201"]["metric"]["occupancy"].reverse(),
            "ordered",
        )

    def test_duplicate_live_camera_and_incomplete_history_fail_at_startup(self):
        self.assert_invalid("live_occupancy.json", lambda p: p["cameras"].append(deepcopy(p["cameras"][0])), "Duplicate")
        self.assert_invalid(
            "historical_api_views.json",
            lambda p: p["views"]["range"]["day"].pop("room_cse_201"),
            "incomplete",
        )

    def test_missing_and_malformed_files(self):
        temporary, path = self.copied()
        with temporary:
            (path / "rooms.json").unlink()
            with self.assertRaisesRegex(FixtureError, "Missing fixture"):
                MockOccupancyRepository(path)

    def test_create_app_rejects_invalid_fixtures_with_actionable_message(self):
        temporary, path = self.mutate("rooms.json", lambda p: p["rooms"][0].__setitem__("capacity", 0))
        with temporary, self.assertRaisesRegex(FixtureError, "Invalid rooms.json"):
            create_app(Settings(mock_data_dir=path))
        temporary, path = self.copied()
        with temporary:
            (path / "rooms.json").write_text("{")
            with self.assertRaisesRegex(FixtureError, "Unable to read"):
                MockOccupancyRepository(path)


class ApiEdgeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(Settings()), raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()

    def test_unknown_room_and_camera(self):
        for path, code in (("/api/rooms/room_unknown", "room_not_found"), ("/api/occupancy/cam_999", "camera_not_found")):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], code)

    def test_invalid_history_range_metric_and_room_id(self):
        for params in ({"room_id":"room_cse_201","range":"month","metric":"percentage"},
                       {"room_id":"room_cse_201","range":"day","metric":"average"},
                       {"room_id":"bad","range":"day","metric":"percentage"}):
            response = self.client.get("/api/history", params=params)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_history_order_counts_zero_partial_and_gaps(self):
        expected = {"hour":168, "day":7, "week":1}
        for granularity, count in expected.items():
            data = self.client.get("/api/history", params={"room_id":"room_cse_201","range":granularity,"metric":"occupancy"}).json()["data"]
            self.assertEqual(len(data), count)
            self.assertEqual([x["bucket_start"] for x in data], sorted(x["bucket_start"] for x in data))
        partial_example = json.loads((ROOT / "contracts" / "examples" / "partial-coverage-history.json").read_text())
        self.assertTrue(any(point["coverage_percentage"] < 100 for point in partial_example["data"]))
        zero = json.loads((ROOT / "contracts" / "examples" / "zero-occupancy.json").read_text())
        self.assertEqual(zero["data"]["occupancy"], 0)
        empty = json.loads((ROOT / "contracts" / "examples" / "empty-history.json").read_text())
        self.assertEqual(empty["data"], [])

    def test_over_capacity_and_valid_zero(self):
        over = json.loads((ROOT / "contracts" / "examples" / "over-capacity.json").read_text())["data"]
        self.assertEqual(over["raw_occupancy"], 126)
        self.assertEqual(over["occupancy_percentage"], 100)
        zero = json.loads((ROOT / "contracts" / "examples" / "zero-occupancy.json").read_text())
        self.assertEqual(zero["data"]["occupancy"], 0)

    def test_cors_and_request_id_cache_headers(self):
        response = self.client.options("/api/rooms", headers={"Origin":"http://localhost:5173", "Access-Control-Request-Method":"GET"})
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        response = self.client.get("/api/rooms", headers={"X-Request-ID":"trace-1"})
        self.assertEqual(response.headers["X-Request-ID"], "trace-1")
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=300")

    def test_every_public_error_uses_standard_envelope(self):
        invalid = self.client.get("/api/history", params={"room_id":"bad","range":"hour","metric":"occupancy"})
        missing = self.client.get("/api/rooms/room_unknown")
        unknown_route = self.client.get("/does-not-exist")
        wrong_method = self.client.post("/api/rooms")
        rejected_cors = self.client.options("/api/rooms", headers={
            "Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET",
        })
        for response in (invalid, missing, unknown_route, wrong_method, rejected_cors):
            self.assertIn("error", response.json())
            self.assertEqual(set(response.json()["error"]), {"code", "message", "details"})

        class BrokenRepository:
            generated_at = None
            def list_rooms(self):
                raise RuntimeError("C:/private/internal.db")

        with TestClient(create_app(Settings(), repository=BrokenRepository()), raise_server_exceptions=False) as client:
            response = client.get("/api/rooms")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(set(response.json()["error"]), {"code", "message", "details"})
        self.assertNotIn("private", response.text)
