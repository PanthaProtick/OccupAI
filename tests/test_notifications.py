from __future__ import annotations

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app import create_app
from backend.config import Settings
from backend.database import Base, NotificationPreferenceRow, UserNotificationRow, UserRow
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "notifications.db"
        self.url = f"sqlite:///{database.as_posix()}"
        engine = create_engine(self.url)
        Base.metadata.create_all(engine)
        engine.dispose()
        settings = Settings(
            database_url=self.url,
            auth_session_pepper="test-pepper-that-is-long-enough",
        )
        self.client = TestClient(create_app(settings, MockOccupancyRepository(settings.mock_data_dir)))

    def tearDown(self):
        engine = self.client.app.state.auth_engine
        if engine is not None:
            engine.dispose()
        self.client.close()
        self.temp.cleanup()

    def signup(self, email: str = "student@aust.edu", name: str = "AUST Student") -> str:
        response = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": name, "email": email, "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 201)
        return response.json()["data"]["id"]

    def login(self, email: str = "student@aust.edu") -> None:
        response = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": email, "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)

    def add_notification(
        self,
        user_id: str,
        *,
        created_at: datetime,
        read_at: datetime | None = None,
        dismissed_at: datetime | None = None,
        title: str = "Room occupancy warning",
    ) -> str:
        notification_id = str(uuid.uuid4())
        engine = create_engine(self.url)
        with Session(engine) as db:
            db.add(UserNotificationRow(
                id=notification_id,
                user_id=user_id,
                type="high_occupancy",
                category="occupancy",
                title=title,
                message="This room is currently 85% occupied.",
                occupancy_percentage=85,
                created_at=created_at.isoformat(),
                read_at=read_at.isoformat() if read_at else None,
                dismissed_at=dismissed_at.isoformat() if dismissed_at else None,
            ))
            db.commit()
        engine.dispose()
        return notification_id

    def test_list_is_newest_first_filtered_paginated_and_bounded(self):
        user_id = self.signup()
        start = datetime(2026, 9, 5, tzinfo=timezone.utc)
        oldest = self.add_notification(user_id, created_at=start, title="Oldest")
        self.add_notification(user_id, created_at=start + timedelta(minutes=1),
                              read_at=start + timedelta(minutes=2), title="Already read")
        self.add_notification(user_id, created_at=start + timedelta(minutes=2),
                              dismissed_at=start + timedelta(minutes=3), title="Dismissed")
        newest = self.add_notification(user_id, created_at=start + timedelta(minutes=3), title="Newest")

        first = self.client.get("/api/notifications", params={"limit": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers.get("cache-control"), "no-store")
        self.assertEqual([item["title"] for item in first.json()["items"]], ["Newest", "Already read"])
        self.assertEqual(first.json()["unread_count"], 2)
        self.assertIsNotNone(first.json()["next_cursor"])
        self.assertEqual(set(first.json()["items"][0]), {
            "id", "type", "category", "title", "message", "room_id", "suggested_room_id",
            "occupancy_percentage", "created_at", "read_at", "dismissed_at",
        })

        second = self.client.get("/api/notifications", params={
            "limit": 2, "cursor": first.json()["next_cursor"],
        })
        self.assertEqual([item["id"] for item in second.json()["items"]], [oldest])
        self.assertIsNone(second.json()["next_cursor"])

        unread = self.client.get("/api/notifications", params={"unread_only": True})
        self.assertEqual([item["id"] for item in unread.json()["items"]], [newest, oldest])
        included = self.client.get("/api/notifications", params={"include_dismissed": True})
        self.assertEqual(len(included.json()["items"]), 4)
        self.assertEqual(included.json()["unread_count"], 2)
        self.assertEqual(self.client.get("/api/notifications", params={"limit": 101}).status_code, 400)
        invalid = self.client.get("/api/notifications", params={"cursor": "not-a-cursor"})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["error"]["code"], "invalid_cursor")

    def test_read_dismiss_and_read_all_are_idempotent_and_user_isolated(self):
        first_user = self.signup()
        start = datetime(2026, 9, 5, tzinfo=timezone.utc)
        first_read_id = self.add_notification(first_user, created_at=start)
        first_untouched_id = self.add_notification(first_user, created_at=start + timedelta(minutes=1))

        self.client.cookies.clear()
        second_user = self.signup("other@aust.edu", "Other Student")
        second_id = self.add_notification(second_user, created_at=start + timedelta(minutes=2))

        for suffix in ("read", "dismiss"):
            forbidden = self.client.post(
                f"/api/notifications/{first_read_id}/{suffix}", headers={"Origin": ORIGIN}
            )
            self.assertEqual(forbidden.status_code, 404)
            self.assertEqual(forbidden.json()["error"]["code"], "notification_not_found")

        self.assertEqual(
            self.client.post("/api/notifications/read-all", headers={"Origin": ORIGIN}).status_code,
            204,
        )
        engine = create_engine(self.url)
        with Session(engine) as db:
            self.assertIsNone(db.get(UserNotificationRow, first_untouched_id).read_at)
            self.assertIsNotNone(db.get(UserNotificationRow, second_id).read_at)

        self.client.cookies.clear()
        self.login()
        first_read = self.client.post(
            f"/api/notifications/{first_read_id}/read", headers={"Origin": ORIGIN}
        )
        self.assertEqual(first_read.status_code, 200)
        read_at = first_read.json()["read_at"]
        second_read = self.client.post(
            f"/api/notifications/{first_read_id}/read", headers={"Origin": ORIGIN}
        )
        self.assertEqual(second_read.json()["read_at"], read_at)

        self.assertEqual(
            self.client.post(
                f"/api/notifications/{first_read_id}/dismiss", headers={"Origin": ORIGIN}
            ).status_code,
            204,
        )
        with Session(engine) as db:
            dismissed_at = db.get(UserNotificationRow, first_read_id).dismissed_at
        self.assertEqual(
            self.client.post(
                f"/api/notifications/{first_read_id}/dismiss", headers={"Origin": ORIGIN}
            ).status_code,
            204,
        )
        with Session(engine) as db:
            row = db.get(UserNotificationRow, first_read_id)
            self.assertEqual(row.dismissed_at, dismissed_at)
            self.assertEqual(
                db.scalar(select(func.count()).select_from(UserNotificationRow)),
                3,
            )
        engine.dispose()

    def test_notifications_and_read_state_survive_logout_and_login(self):
        user_id = self.signup()
        notification_id = self.add_notification(
            user_id, created_at=datetime.now(timezone.utc)
        )
        dismissed_id = self.add_notification(
            user_id, created_at=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        read = self.client.post(
            f"/api/notifications/{notification_id}/read", headers={"Origin": ORIGIN}
        )
        self.assertEqual(read.status_code, 200)
        read_at = read.json()["read_at"]
        self.assertEqual(
            self.client.post(
                f"/api/notifications/{dismissed_id}/dismiss", headers={"Origin": ORIGIN}
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/notifications").status_code, 401)
        self.login()
        restored = self.client.get("/api/notifications")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["items"][0]["id"], notification_id)
        self.assertEqual(restored.json()["items"][0]["read_at"], read_at)
        self.assertEqual(restored.json()["unread_count"], 0)
        restored_with_dismissed = self.client.get(
            "/api/notifications", params={"include_dismissed": True}
        )
        dismissed = next(
            item for item in restored_with_dismissed.json()["items"]
            if item["id"] == dismissed_id
        )
        self.assertIsNotNone(dismissed["dismissed_at"])

    def test_notification_endpoints_require_authentication_and_mutations_require_origin(self):
        self.assertEqual(self.client.get("/api/notifications").status_code, 401)
        self.assertEqual(
            self.client.post("/api/notifications/read-all", headers={"Origin": ORIGIN}).status_code,
            401,
        )
        user_id = self.signup()
        notification_id = self.add_notification(user_id, created_at=datetime.now(timezone.utc))
        no_origin = self.client.post(f"/api/notifications/{notification_id}/read")
        self.assertEqual(no_origin.status_code, 403)
        self.assertEqual(no_origin.json()["error"]["code"], "invalid_origin")

    def test_preference_defaults_updates_and_logout_login_persistence(self):
        user_id = self.signup()
        defaults = self.client.get("/api/notification-preferences")
        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(defaults.headers.get("cache-control"), "no-store")
        self.assertEqual(defaults.json(), {
            "in_app_enabled": True,
            "high_occupancy_enabled": True,
            "high_occupancy_threshold": 80,
            "cooldown_minutes": 30,
        })
        engine = create_engine(self.url)
        with Session(engine) as db:
            self.assertIsNotNone(db.get(NotificationPreferenceRow, user_id))
        engine.dispose()

        updated = self.client.patch(
            "/api/notification-preferences",
            headers={"Origin": ORIGIN},
            json={
                "in_app_enabled": False,
                "high_occupancy_threshold": 75,
                "cooldown_minutes": 45,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json(), {
            "in_app_enabled": False,
            "high_occupancy_enabled": True,
            "high_occupancy_threshold": 75,
            "cooldown_minutes": 45,
        })
        self.client.post("/api/auth/logout", headers={"Origin": ORIGIN})
        self.login()
        self.assertEqual(self.client.get("/api/notification-preferences").json(), updated.json())

    def test_preference_validation_origin_and_user_isolation(self):
        first_user = self.signup()
        first = self.client.patch(
            "/api/notification-preferences",
            headers={"Origin": ORIGIN},
            json={"high_occupancy_threshold": 75},
        )
        self.assertEqual(first.status_code, 200)
        invalid_payloads = (
            {},
            {"high_occupancy_threshold": 49},
            {"high_occupancy_threshold": 101},
            {"cooldown_minutes": 0},
            {"cooldown_minutes": 10_081},
            {"in_app_enabled": 1},
            {"high_occupancy_enabled": None},
            {"unknown": True},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    "/api/notification-preferences", headers={"Origin": ORIGIN}, json=payload
                )
                self.assertEqual(response.status_code, 422)

        no_origin = self.client.patch(
            "/api/notification-preferences", json={"high_occupancy_threshold": 90}
        )
        self.assertEqual(no_origin.status_code, 403)
        self.client.cookies.clear()
        second_user = self.signup("other@aust.edu", "Other Student")
        self.assertNotEqual(first_user, second_user)
        self.assertEqual(
            self.client.get("/api/notification-preferences").json()["high_occupancy_threshold"],
            80,
        )
        engine = create_engine(self.url)
        with Session(engine) as db:
            self.assertEqual(db.get(NotificationPreferenceRow, first_user).high_occupancy_threshold, 75)
            self.assertEqual(db.get(NotificationPreferenceRow, second_user).high_occupancy_threshold, 80)
        engine.dispose()

    def test_preferences_require_authentication(self):
        self.assertEqual(self.client.get("/api/notification-preferences").status_code, 401)
        self.assertEqual(
            self.client.patch(
                "/api/notification-preferences",
                headers={"Origin": ORIGIN},
                json={"high_occupancy_threshold": 75},
            ).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
