"""End-to-end account/profile/high-occupancy notification smoke check."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.config import Settings
from backend.database import Base, CameraRow, CameraStateRow, RoomRow, make_session_factory
from backend.ingestion import IngestionRecord, SerializedDatabaseWriter
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "account-smoke.db"
        url = f"sqlite:///{database.as_posix()}"
        engine = create_engine(url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        stamp = now.isoformat()
        sessions = make_session_factory(engine)
        with sessions.begin() as db:
            for room_id, name, camera_id, occupancy, status in (
                ("room_target", "Target 201", "cam_001", 0, "offline"),
                ("room_recommended", "Nearby 202", "cam_002", 20, "online"),
            ):
                db.add(RoomRow(
                    room_id=room_id, name=name, capacity=100, building="AUST", floor=2,
                    behavior_profile="classroom", created_at=stamp, updated_at=stamp,
                    camera=CameraRow(
                        camera_id=camera_id, enabled=True, stale_after_seconds=10,
                        created_at=stamp, updated_at=stamp,
                        state=CameraStateRow(
                            camera_id=camera_id, raw_occupancy=occupancy, occupancy=occupancy,
                            status=status, observed_at=stamp, updated_at=stamp,
                        ),
                    ),
                ))
        settings = Settings(database_url=url, auth_session_pepper="smoke-pepper-that-is-long-enough")
        app = create_app(settings, MockOccupancyRepository(settings.mock_data_dir))
        with TestClient(app) as client:
            signup = client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
                "name": "Smoke Student", "email": "Smoke@AUST.EDU", "password": PASSWORD,
            })
            check(signup.status_code == 201, "signup failed")
            profile = client.get("/api/profile")
            check(profile.json()["name"] == "Smoke Student", "registered name was not loaded")
            check(profile.json()["email"] == "smoke@aust.edu", "email was not normalized")
            updated = client.patch("/api/profile", headers={"Origin": ORIGIN}, json={"name": "Updated Smoke"})
            check(updated.status_code == 200, "profile update failed")
            check(client.get("/api/profile").json()["name"] == "Updated Smoke", "profile update did not persist")

            writer = SerializedDatabaseWriter(sessions, sample_interval_seconds=5)
            check(writer.ingest(IngestionRecord(
                camera_id="cam_001", observed_at=now + timedelta(seconds=1),
                raw_occupancy=85, occupancy=85, status="online", source_event_id="smoke-crossing",
            )), "occupancy ingestion failed")
            listed = client.get("/api/notifications").json()
            check(len(listed["items"]) == 1, "high-occupancy notification was not generated")
            notification = listed["items"][0]
            check(notification["suggested_room_id"] == "room_recommended", "recommendation was incorrect")
            marked = client.post(
                f"/api/notifications/{notification['id']}/read", headers={"Origin": ORIGIN}
            )
            check(marked.status_code == 200 and marked.json()["read_at"], "read state was not stored")

            check(client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 204, "logout failed")
            login = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
                "email": "smoke@aust.edu", "password": PASSWORD,
            })
            check(login.status_code == 200, "login failed")
            check(client.get("/api/profile").json()["name"] == "Updated Smoke", "profile did not survive login")
            restored = client.get("/api/notifications").json()["items"][0]
            check(restored["id"] == notification["id"] and restored["read_at"], "notification did not survive login")

            client.post("/api/auth/logout", headers={"Origin": ORIGIN})
            other = client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
                "name": "Other Student", "email": "other-smoke@aust.edu", "password": PASSWORD,
            })
            check(other.status_code == 201, "second signup failed")
            check(client.get("/api/notifications").json()["items"] == [], "notification ownership leaked")
        engine.dispose()
    print("Account smoke passed: profile, persistence, isolation, alert, read state, recommendation")


if __name__ == "__main__":
    main()
