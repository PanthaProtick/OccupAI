import json
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, func, inspect, select, text
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from backend.app import create_app
from backend.config import PROJECT_ROOT, Settings
from backend.database import create_database_engine, make_session_factory
from backend.database import CameraRow, IngestionReceiptRow, OccupancyBucketRow, OccupancySampleRow
from backend.ingestion import (
    IngestionRecord, ModelServerIngestionAdapter, ModelServerIngestionService,
    SerializedDatabaseWriter,
)
from backend.maintenance import (
    DatabaseMaintenanceService, aggregate_five_minute_buckets, apply_retention, backup_sqlite_database,
    import_history, iso, seed_canonical,
)
from backend.models import HistoryMetric, HistoryRange, HistoryResponse, OccupancyListResponse, RoomsResponse
from backend.repositories.database import DatabaseOccupancyRepository
from backend.repositories.mock import MockOccupancyRepository
from backend.simulation import SimulatedCamera, SimulatedIngestionService
from model_server.model_state import LatestOccupancyStore
from model_server.occupancy import OccupancyRecord


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "occupai.db"
        self.url = f"sqlite:///{self.path.as_posix()}"
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", self.url)
        command.upgrade(config, "head")
        self.engine = create_database_engine(self.url)
        self.sessions = make_session_factory(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def test_migration_schema_constraints_and_pragmas(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()), {
            "alembic_version", "rooms", "cameras", "camera_states", "ingestion_receipts",
            "occupancy_samples", "occupancy_buckets_5m"})
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("PRAGMA foreign_keys")), 1)
            self.assertGreaterEqual(connection.scalar(text("PRAGMA busy_timeout")), 5000)
            self.assertEqual(connection.scalar(text("PRAGMA journal_mode")), "wal")
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0002")
        inspector = inspect(self.engine)
        self.assertEqual({fk["referred_table"] for fk in inspector.get_foreign_keys("cameras")}, {"rooms"})
        self.assertEqual({fk["referred_table"] for fk in inspector.get_foreign_keys("camera_states")}, {"cameras"})
        self.assertIn("ix_occupancy_samples_camera_time", {item["name"] for item in inspector.get_indexes("occupancy_samples")})
        self.assertIn("ix_occupancy_buckets_time", {item["name"] for item in inspector.get_indexes("occupancy_buckets_5m")})
        self.assertTrue(inspector.get_check_constraints("occupancy_buckets_5m"))

    def test_seed_is_idempotent_and_all_rooms_stay_visible(self):
        fixtures = PROJECT_ROOT / "mock" / "generated"
        seed_canonical(self.sessions, fixtures)
        seed_canonical(self.sessions, fixtures)
        repository = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(len(repository.list_rooms()), 4)
        self.assertEqual(len(repository.list_occupancy()), 4)
        self.assertTrue(all(value.status.value == "offline" for value in repository.list_occupancy()))

    def test_seed_refuses_canonical_camera_remapping(self):
        fixtures = PROJECT_ROOT / "mock" / "generated"
        seed_canonical(self.sessions, fixtures)
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory)
            payload = json.loads((fixtures / "rooms.json").read_text(encoding="utf-8"))
            payload["rooms"][0]["camera_id"] = "cam_007"
            (altered / "rooms.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Refusing"):
                seed_canonical(self.sessions, altered)
        repository = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(repository.get_room("room_tt_ground").camera_id, "cam_001")

    def test_ingestion_is_idempotent_preserves_raw_and_survives_repository_restart(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=0)
        record = IngestionRecord(camera_id="1", observed_at=datetime.now(timezone.utc), raw_occupancy=126,
                                 occupancy=126, source_event_id="event-1")
        self.assertTrue(writer.ingest(record))
        self.assertFalse(writer.ingest(record))
        value = DatabaseOccupancyRepository(self.sessions).get_occupancy("cam_001")
        self.assertEqual(value.raw_occupancy, 126)
        self.assertEqual(value.occupancy_percentage, 100)
        self.assertEqual(value.status.value, "online")

    def test_import_history_and_repository_aggregations(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        path = PROJECT_ROOT / "mock" / "generated" / "history_5min_7days.json"
        self.assertEqual(import_history(self.sessions, path), 8064)
        self.assertEqual(import_history(self.sessions, path), 8064)
        repository = DatabaseOccupancyRepository(self.sessions)
        for granularity, expected in ((HistoryRange.HOUR, 168), (HistoryRange.DAY, 7), (HistoryRange.WEEK, 1)):
            self.assertEqual(len(repository.get_history("room_tt_ground", granularity, HistoryMetric.PERCENTAGE)), expected)
        with self.sessions.begin() as session:
            starts = session.scalars(select(OccupancyBucketRow.bucket_start).where(OccupancyBucketRow.camera_id == "cam_004").order_by(OccupancyBucketRow.bucket_start).limit(12)).all()
            session.execute(delete(OccupancyBucketRow).where(OccupancyBucketRow.camera_id == "cam_004", OccupancyBucketRow.bucket_start.in_(starts)))
        missing = repository.get_history("room_girls_common", HistoryRange.HOUR, HistoryMetric.OCCUPANCY)
        self.assertEqual(len(missing), 167)

    def test_database_api_contract_and_restart_persistence(self):
        fixtures = PROJECT_ROOT / "mock" / "generated"
        seed_canonical(self.sessions, fixtures)
        import_history(self.sessions, fixtures / "history_5min_7days.json")
        SerializedDatabaseWriter(self.sessions).ingest(IngestionRecord(
            camera_id="cam_001", observed_at=datetime.now(timezone.utc), raw_occupancy=45,
            occupancy=45, source_event_id="restart-1",
        ))
        repository = DatabaseOccupancyRepository(self.sessions)
        app = create_app(Settings(data_source="database", database_url=self.url), repository=repository)
        with TestClient(app) as client:
            rooms = client.get("/api/rooms")
            occupancy = client.get("/api/occupancy")
            history = client.get("/api/history", params={
                "room_id": "room_tt_ground", "range": "day", "metric": "percentage",
            })
        self.assertEqual((rooms.status_code, occupancy.status_code, history.status_code), (200, 200, 200))
        TypeAdapter(RoomsResponse).validate_python(rooms.json())
        TypeAdapter(OccupancyListResponse).validate_python(occupancy.json())
        TypeAdapter(HistoryResponse).validate_python(history.json())
        self.assertEqual(rooms.json()["meta"]["count"], 4)
        self.assertEqual(history.json()["meta"]["count"], 7)

        self.engine.dispose()
        restarted_engine = create_database_engine(self.url)
        restarted_sessions = make_session_factory(restarted_engine)
        restarted = DatabaseOccupancyRepository(restarted_sessions)
        self.assertEqual(len(restarted.list_rooms()), 4)
        self.assertEqual(restarted.get_occupancy("cam_001").raw_occupancy, 45)
        self.assertEqual(len(restarted.get_history("room_tt_ground", HistoryRange.DAY, HistoryMetric.OCCUPANCY)), 7)
        restarted_engine.dispose()

    def test_mock_and_database_repositories_return_same_domain_model_types(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        mock = MockOccupancyRepository(PROJECT_ROOT / "mock" / "generated")
        database = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(type(mock.list_rooms()[0]), type(database.list_rooms()[0]))
        self.assertEqual(type(mock.list_occupancy()[0]), type(database.list_occupancy()[0]))

    def test_default_database_url_is_relative_under_data(self):
        self.assertEqual(Settings().database_url, "sqlite:///./data/occupai.db")

    def test_five_minute_boundaries(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=0)
        for second in (datetime(2026, 1, 1, 12, 4, 59, tzinfo=timezone.utc), datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)):
            writer.ingest(IngestionRecord(camera_id="cam_001", observed_at=second, raw_occupancy=4, occupancy=4))
        self.assertEqual(aggregate_five_minute_buckets(self.sessions, expected_sample_count=1), 2)

    def test_model_adapter_isolates_malformed_camera_and_normalizes_ids(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions)
        body = (b'{"cameras":{"1":{"status":"online","updated_at":"2026-01-01T00:00:00Z",'
                b'"raw_occupancy":3,"occupancy":3},"cam_002":{"status":"online","occupancy":"bad"}}}')
        response = BytesIO(body)
        with patch("urllib.request.urlopen", return_value=response):
            result = ModelServerIngestionAdapter("http://model", writer).poll_once()
        self.assertTrue(result["cam_001"])
        self.assertFalse(result["cam_002"])
        repository = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(len(repository.list_occupancy()), 4)
        self.assertEqual(repository.get_occupancy("cam_001").raw_occupancy, 3)
        self.assertEqual(repository.get_occupancy("cam_002").status.value, "offline")

    def test_model_adapter_timeout_is_actionable(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                ModelServerIngestionAdapter("http://model", SerializedDatabaseWriter(self.sessions)).poll_once()

    def test_real_http_model_state_contract_populates_durable_database(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        state = LatestOccupancyStore(["cam_001"])
        observed = datetime.now(timezone.utc).isoformat()
        state.update(OccupancyRecord("cam_001", observed, 11, 9, 1.0, 1.0, None, 3.0, 0))

        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                body = json.dumps({"cameras": state.snapshot()}).encode("utf-8")
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "application/json")
                handler_self.send_header("Content-Length", str(len(body)))
                handler_self.end_headers()
                handler_self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            writer = SerializedDatabaseWriter(self.sessions)
            endpoint = f"http://127.0.0.1:{server.server_address[1]}"
            result = ModelServerIngestionAdapter(endpoint, writer).poll_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertTrue(result["cam_001"])
        self.engine.dispose()
        restarted_engine = create_database_engine(self.url)
        durable = DatabaseOccupancyRepository(make_session_factory(restarted_engine)).get_occupancy("cam_001")
        self.assertEqual((durable.raw_occupancy, durable.occupancy), (11, 9))
        restarted_engine.dispose()

    def test_ingestion_validation_normalization_and_raw_stabilized_separation(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        for source, expected in (("1", "cam_001"), ("cam1", "cam_001"), ("cam-007", "cam_007")):
            self.assertEqual(IngestionRecord(
                camera_id=source, observed_at=datetime.now(timezone.utc), raw_occupancy=8, occupancy=6,
            ).camera_id, expected)
        with self.assertRaises(ValidationError):
            IngestionRecord(camera_id="camera-a", observed_at=datetime.now(timezone.utc), raw_occupancy=1, occupancy=1)
        with self.assertRaises(ValidationError):
            IngestionRecord(camera_id="1", observed_at=datetime.now(), raw_occupancy=1, occupancy=1)
        writer = SerializedDatabaseWriter(self.sessions)
        writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=datetime.now(timezone.utc), raw_occupancy=50, occupancy=42,
        ))
        value = DatabaseOccupancyRepository(self.sessions).get_occupancy("cam_001")
        self.assertEqual((value.raw_occupancy, value.occupancy), (50, 42))
        self.assertEqual(value.occupancy_percentage, 100)

    def test_sampling_is_throttled_but_changes_and_heartbeat_are_persisted(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=10)
        start = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
        for offset in range(30):
            writer.ingest(IngestionRecord(
                camera_id="cam_001", observed_at=start + timedelta(seconds=offset / 3),
                raw_occupancy=4, occupancy=4,
            ))
        writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=9.8), raw_occupancy=5, occupancy=5,
        ))
        writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=20), raw_occupancy=5, occupancy=5,
        ))
        with self.sessions() as session:
            count = session.scalar(select(func.count()).select_from(OccupancySampleRow))
        self.assertEqual(count, 3)

    def test_unsampled_updates_are_still_idempotent(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=10)
        start = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=start, raw_occupancy=2, occupancy=2, source_event_id="first",
        )))
        second = IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=1), raw_occupancy=2,
            occupancy=2, source_event_id="unsampled",
        )
        self.assertTrue(writer.ingest(second))
        self.assertFalse(writer.ingest(second))
        self.assertFalse(writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=2), raw_occupancy=2,
            occupancy=2, source_event_id="unsampled",
        )))
        third = IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=3), raw_occupancy=2,
            occupancy=2, source_event_id="newer-event",
        )
        self.assertTrue(writer.ingest(third))
        self.assertFalse(writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=start + timedelta(seconds=4), raw_occupancy=2,
            occupancy=2, source_event_id="unsampled",
        )))
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(IngestionReceiptRow)), 3)

    def test_service_outage_marks_configured_cameras_offline_and_recovers(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions)
        now = datetime.now(timezone.utc)
        writer.ingest(IngestionRecord(camera_id="cam_001", observed_at=now, raw_occupancy=3, occupancy=3))

        class RecoveringAdapter:
            calls = 0
            def poll_once(adapter_self):
                adapter_self.calls += 1
                if adapter_self.calls == 1:
                    raise TimeoutError("model timeout")
                return {"cam_001": writer.ingest(IngestionRecord(
                    camera_id="cam_001", observed_at=now + timedelta(seconds=1), raw_occupancy=4, occupancy=4,
                ))}

        service = ModelServerIngestionService(RecoveringAdapter(), writer, ("cam_001", "cam_002", "cam_003"))
        self.assertFalse(service.run_once()["cam_001"])
        repository = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(repository.get_occupancy("cam_001").status.value, "offline")
        self.assertIsNone(repository.get_occupancy("cam_001").occupancy)
        self.assertTrue(service.run_once()["cam_001"])
        recovered = repository.get_occupancy("cam_001")
        self.assertEqual((recovered.status.value, recovered.occupancy), ("online", 4))

    def test_ingestion_service_starts_and_stops_gracefully(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions)

        class EmptyAdapter:
            def poll_once(self):
                return {}

        service = ModelServerIngestionService(EmptyAdapter(), writer, (), poll_interval_seconds=0.01)
        service.start()
        time.sleep(0.03)
        self.assertTrue(service.is_alive)
        service.stop()
        self.assertFalse(service.is_alive)

    def test_three_configured_and_seventeen_unconfigured_cameras_keep_twenty_room_contract(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions)
        now = datetime.now(timezone.utc)
        for number in range(1, 4):
            writer.ingest(IngestionRecord(
                camera_id=f"cam_{number:03d}", observed_at=now, raw_occupancy=number,
                occupancy=number, source_event_id=f"configured-{number}",
            ))
        repository = DatabaseOccupancyRepository(self.sessions)
        rooms = repository.list_rooms()
        occupancy = repository.list_occupancy()
        self.assertEqual([room.camera_id for room in rooms], [f"cam_{number:03d}" for number in range(1, 21)])
        self.assertEqual(len(occupancy), 4)
        self.assertTrue(all(item.status.value == "online" for item in occupancy[:3]))
        self.assertTrue(all(item.status.value == "offline" and item.occupancy is None for item in occupancy[3:]))

    def test_simulated_cameras_write_fresh_state_for_each_tick(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        first_service = SimulatedIngestionService(
            [SimulatedCamera("cam_004", 40, "classroom")],
            SerializedDatabaseWriter(self.sessions, sample_interval_seconds=10),
        )
        self.assertEqual(first_service.run_once(), {"cam_004": True})
        repository = DatabaseOccupancyRepository(self.sessions)
        first = repository.get_occupancy("cam_004")
        self.assertEqual(first.status.value, "online")
        time.sleep(0.001)
        restarted_service = SimulatedIngestionService(
            [SimulatedCamera("cam_004", 40, "classroom")],
            SerializedDatabaseWriter(self.sessions, sample_interval_seconds=10),
        )
        self.assertEqual(restarted_service.run_once(), {"cam_004": True})
        second = repository.get_occupancy("cam_004")
        self.assertGreater(second.updated_at, first.updated_at)

    def test_live_camera_configuration_requires_unique_canonical_ids(self):
        with self.assertRaisesRegex(ValueError, "LIVE_CAMERA_IDS"):
            Settings(live_camera_ids=("cam_001", "cam_001"))
        with self.assertRaisesRegex(ValueError, "LIVE_CAMERA_IDS"):
            Settings(live_camera_ids=("camera-1",))

    def test_history_import_rejects_non_utc_and_unaligned_buckets(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        base = {
            "generated_at": "2026-08-23T00:00:00Z",
            "records": [{"room_id":"room_tt_ground", "camera_id":"cam_001",
                         "bucket_start":"2026-08-23T00:01:00Z", "avg_occupancy":1,
                         "min_occupancy":1, "max_occupancy":1, "capacity_snapshot":40,
                         "coverage_percentage":100}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "five-minute"):
                import_history(self.sessions, path)
            base["records"][0]["bucket_start"] = "2026-08-23T00:00:00+06:00"
            path.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "UTC"):
                import_history(self.sessions, path)

    def test_partial_bucket_empty_history_gaps_and_capacity_aware_percentage(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        repository = DatabaseOccupancyRepository(self.sessions)
        self.assertEqual(repository.get_history("room_tt_ground", HistoryRange.HOUR, HistoryMetric.OCCUPANCY), [])
        now = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
        with self.sessions.begin() as session:
            session.add_all([
                OccupancySampleRow(camera_id="cam_001", observed_at=iso(now), raw_occupancy=5,
                                   occupancy=5, status="online", capacity_snapshot=10,
                                   created_at=iso(now)),
                OccupancySampleRow(camera_id="cam_001", observed_at=iso(now + timedelta(minutes=10)),
                                   raw_occupancy=5, occupancy=5, status="online", capacity_snapshot=20,
                                   created_at=iso(now)),
            ])
        self.assertEqual(aggregate_five_minute_buckets(self.sessions, expected_sample_count=30), 2)
        with self.sessions() as session:
            buckets = session.scalars(select(OccupancyBucketRow).order_by(OccupancyBucketRow.bucket_start)).all()
            self.assertEqual(len(buckets), 2)
            self.assertAlmostEqual(buckets[0].coverage_percentage, 100 / 30)
        points = repository.get_history("room_tt_ground", HistoryRange.HOUR, HistoryMetric.PERCENTAGE)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].value, 37.5)
        self.assertAlmostEqual(points[0].coverage_percentage, 0.56, places=2)

    def test_retention_deletes_in_bounded_batches(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        old = datetime.now(timezone.utc) - timedelta(days=500)
        with self.sessions.begin() as session:
            for index in range(5):
                stamp = old + timedelta(minutes=5 * index)
                session.add(OccupancySampleRow(
                    camera_id="cam_001", observed_at=iso(stamp), raw_occupancy=1, occupancy=1,
                    status="online", capacity_snapshot=40, created_at=iso(stamp),
                ))
                session.add(OccupancyBucketRow(
                    camera_id="cam_001", bucket_start=iso(stamp), avg_occupancy=1,
                    min_occupancy=1, max_occupancy=1, capacity_snapshot=40,
                    coverage_percentage=100, sample_count=1, expected_sample_count=1,
                    updated_at=iso(stamp),
                ))
        self.assertEqual(apply_retention(self.sessions, 30, 365, batch_size=2), (2, 2))
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(OccupancySampleRow)), 3)
            self.assertEqual(session.scalar(select(func.count()).select_from(OccupancyBucketRow)), 3)

    def test_sqlite_backup_is_transactionally_readable(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        destination = Path(self.temp.name) / "backup.db"
        backup_sqlite_database(self.url, destination)
        connection = sqlite3.connect(destination)
        try:
            cursor = connection.execute("SELECT count(*) FROM rooms")
            try:
                self.assertEqual(cursor.fetchone()[0], 20)
            finally:
                cursor.close()
        finally:
            connection.close()

    def test_aggregation_performance_is_bounded_for_representative_batch(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        start = datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc)
        with self.sessions.begin() as session:
            session.add_all([
                OccupancySampleRow(camera_id="cam_001", observed_at=iso(start + timedelta(seconds=index * 10)),
                                   raw_occupancy=index % 41, occupancy=index % 41, status="online",
                                   capacity_snapshot=40, created_at=iso(start))
                for index in range(1000)
            ])
        started = time.perf_counter()
        count = aggregate_five_minute_buckets(self.sessions, expected_sample_count=30, batch_size=25)
        duration = time.perf_counter() - started
        self.assertEqual(count, 34)
        self.assertLess(duration, 5.0)

    def test_aggregation_reprocesses_only_latest_and_new_buckets(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        start = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)
        with self.sessions.begin() as session:
            session.add_all([
                OccupancySampleRow(camera_id="cam_001", observed_at=iso(start + timedelta(minutes=minute)),
                                   raw_occupancy=1, occupancy=1, status="online", capacity_snapshot=40,
                                   created_at=iso(start))
                for minute in (0, 5)
            ])
        self.assertEqual(aggregate_five_minute_buckets(self.sessions, expected_sample_count=1), 2)
        with self.sessions.begin() as session:
            session.add(OccupancySampleRow(
                camera_id="cam_001", observed_at=iso(start + timedelta(minutes=10)),
                raw_occupancy=2, occupancy=2, status="online", capacity_snapshot=40,
                created_at=iso(start),
            ))
        self.assertEqual(aggregate_five_minute_buckets(self.sessions, expected_sample_count=1), 2)
        with self.sessions() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(OccupancyBucketRow)), 3)

    def test_scheduled_maintenance_and_concurrent_reads(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        start = datetime.now(timezone.utc) - timedelta(hours=1)
        with self.sessions.begin() as session:
            session.add_all([
                OccupancySampleRow(camera_id="cam_001", observed_at=iso(start + timedelta(seconds=index * 10)),
                                   raw_occupancy=index % 40, occupancy=index % 40, status="online",
                                   capacity_snapshot=40, created_at=iso(start))
                for index in range(1000)
            ])
        service = DatabaseMaintenanceService(self.sessions, 30, 365, 100, 30, interval_seconds=0.01)
        repository = DatabaseOccupancyRepository(self.sessions)
        errors: list[Exception] = []

        def maintain():
            try:
                service.run_once()
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=maintain)
        thread.start()
        self.assertEqual(len(repository.list_rooms()), 4)
        while thread.is_alive():
            try:
                self.assertEqual(len(repository.list_rooms()), 4)
                repository.list_occupancy()
            except Exception as exc:
                errors.append(exc)
        thread.join(timeout=5)
        self.assertEqual(errors, [])
        self.assertFalse(thread.is_alive())
        service.start()
        time.sleep(0.03)
        self.assertTrue(service.is_alive)
        service.stop()
        self.assertFalse(service.is_alive)

    def test_shared_http_contract_for_mock_and_database_repositories(self):
        fixtures = PROJECT_ROOT / "mock" / "generated"
        seed_canonical(self.sessions, fixtures)
        import_history(self.sessions, fixtures / "history_5min_7days.json")
        apps = [
            create_app(Settings(), repository=MockOccupancyRepository(fixtures)),
            create_app(Settings(data_source="database", database_url=self.url),
                       repository=DatabaseOccupancyRepository(self.sessions)),
        ]
        payloads = []
        for app in apps:
            with TestClient(app) as client:
                responses = [
                    client.get("/api/rooms"), client.get("/api/occupancy"),
                    client.get("/api/history", params={"room_id":"room_tt_ground", "range":"day", "metric":"percentage"}),
                    client.get("/api/rooms/room_unknown"),
                ]
            self.assertEqual([response.status_code for response in responses], [200, 200, 200, 404])
            TypeAdapter(RoomsResponse).validate_python(responses[0].json())
            TypeAdapter(OccupancyListResponse).validate_python(responses[1].json())
            TypeAdapter(HistoryResponse).validate_python(responses[2].json())
            self.assertEqual(responses[3].json()["error"]["code"], "room_not_found")
            payloads.append(responses)
        self.assertEqual(
            [room["room_id"] for room in payloads[0][0].json()["data"]],
            [room["room_id"] for room in payloads[1][0].json()["data"]],
        )
        self.assertEqual(payloads[0][2].json()["meta"]["count"], payloads[1][2].json()["meta"]["count"])

    def test_offline_online_stale_online_transitions_preserve_last_value(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        repository = DatabaseOccupancyRepository(self.sessions)
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=5)
        self.assertEqual(repository.get_occupancy("cam_001").status.value, "offline")
        with self.sessions.begin() as session:
            session.get(CameraRow, "cam_001").stale_after_seconds = 0.2
        first = datetime.now(timezone.utc)
        writer.ingest(IngestionRecord(camera_id="cam_001", observed_at=first, raw_occupancy=7, occupancy=6))
        self.assertEqual(repository.get_occupancy("cam_001").status.value, "online")
        time.sleep(0.25)
        stale = repository.get_occupancy("cam_001")
        self.assertEqual((stale.status.value, stale.occupancy, stale.raw_occupancy), ("stale", 6, 7))
        writer.ingest(IngestionRecord(
            camera_id="cam_001", observed_at=datetime.now(timezone.utc), raw_occupancy=9, occupancy=8,
        ))
        recovered = repository.get_occupancy("cam_001")
        self.assertEqual((recovered.status.value, recovered.occupancy), ("online", 8))

    def test_concurrent_reads_never_observe_partially_updated_state(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=5)
        repository = DatabaseOccupancyRepository(self.sessions)
        start = datetime.now(timezone.utc)
        observations: list[tuple[int | None, int | None]] = []
        errors: list[Exception] = []

        def update_values():
            try:
                for value in range(1, 31):
                    writer.ingest(IngestionRecord(
                        camera_id="cam_001", observed_at=start + timedelta(milliseconds=value),
                        raw_occupancy=value, occupancy=value,
                    ))
            except Exception as exc:
                errors.append(exc)

        def read_values():
            try:
                for _ in range(40):
                    item = repository.get_occupancy("cam_001")
                    observations.append((item.raw_occupancy, item.occupancy))
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(update_values)] + [executor.submit(read_values) for _ in range(3)]
            for future in futures:
                future.result()
        self.assertEqual(errors, [])
        self.assertTrue(all(raw == stable for raw, stable in observations if raw is not None))
        self.assertEqual(repository.get_occupancy("cam_001").occupancy, 30)

    def test_sqlite_busy_timeout_waits_and_serialized_writer_recovers(self):
        seed_canonical(self.sessions, PROJECT_ROOT / "mock" / "generated")
        blocker = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        blocker.execute("PRAGMA busy_timeout=5000")
        blocker.execute("BEGIN IMMEDIATE")
        result: list[bool] = []
        writer = SerializedDatabaseWriter(self.sessions)

        def write_when_released():
            result.append(writer.ingest(IngestionRecord(
                camera_id="cam_001", observed_at=datetime.now(timezone.utc), raw_occupancy=2, occupancy=2,
            )))

        thread = threading.Thread(target=write_when_released)
        thread.start()
        time.sleep(0.1)
        self.assertTrue(thread.is_alive())
        blocker.commit()
        blocker.close()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [True])

    def test_percentage_capping_and_raw_retention_in_both_repositories(self):
        fixtures = PROJECT_ROOT / "mock" / "generated"
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory)
            for filename in MockOccupancyRepository.REQUIRED_FILES:
                (copied / filename).write_bytes((fixtures / filename).read_bytes())
            live = json.loads((copied / "live_occupancy.json").read_text(encoding="utf-8"))
            live["cameras"][3]["occupancy"] = 126
            (copied / "live_occupancy.json").write_text(json.dumps(live), encoding="utf-8")
            mock_value = MockOccupancyRepository(copied).get_occupancy("cam_003")
        seed_canonical(self.sessions, fixtures)
        SerializedDatabaseWriter(self.sessions).ingest(IngestionRecord(
            camera_id="cam_003", observed_at=datetime.now(timezone.utc), raw_occupancy=126, occupancy=126,
        ))
        database_value = DatabaseOccupancyRepository(self.sessions).get_occupancy("cam_003")
        for value in (mock_value, database_value):
            self.assertEqual(value.raw_occupancy, 126)
            self.assertEqual(value.occupancy_percentage, 100)


if __name__ == "__main__":
    unittest.main()
