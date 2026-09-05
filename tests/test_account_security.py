from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.app import create_app
from backend.config import Settings
from backend.database import AuthenticationSessionRow, Base
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class AccountSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "security.db"
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

    def signup(self) -> None:
        response = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Security Student",
            "email": "security@aust.edu",
            "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 201)

    def test_logout_revokes_only_the_presented_session(self):
        self.signup()
        first_token = self.client.cookies.get("occupai_session")
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "security@aust.edu", "password": PASSWORD,
        })
        self.assertEqual(login.status_code, 200)
        second_token = self.client.cookies.get("occupai_session")

        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", first_token)
        self.assertEqual(
            self.client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code,
            204,
        )
        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", first_token)
        self.assertEqual(self.client.get("/api/profile").status_code, 401)
        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", second_token)
        self.assertEqual(self.client.get("/api/profile").status_code, 200)

    def test_expired_session_cannot_access_any_account_endpoint(self):
        self.signup()
        engine = create_engine(self.url)
        with engine.begin() as db:
            db.execute(AuthenticationSessionRow.__table__.update().values(
                expires_at="2000-01-01T00:00:00+00:00"
            ))
        engine.dispose()
        requests = (
            ("GET", "/api/profile", None),
            ("PATCH", "/api/profile", {"name": "Blocked"}),
            ("POST", "/api/profile/change-password", {
                "current_password": PASSWORD, "new_password": "New-password-84!",
            }),
            ("GET", "/api/notifications", None),
            ("POST", "/api/notifications/read-all", None),
            ("GET", "/api/notification-preferences", None),
            ("PATCH", "/api/notification-preferences", {"high_occupancy_threshold": 75}),
        )
        for method, path, body in requests:
            with self.subTest(path=path):
                response = self.client.request(
                    method, path, headers={"Origin": ORIGIN}, json=body
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "authentication_required")

    def test_cors_exposes_only_required_methods_to_configured_origin(self):
        response = self.client.options("/api/profile", headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        methods = set(response.headers["access-control-allow-methods"].split(", "))
        self.assertEqual(methods, {"GET", "POST", "PATCH"})
        self.assertEqual(response.headers["access-control-allow-origin"], ORIGIN)
        rejected = self.client.options("/api/profile", headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "PATCH",
        })
        self.assertNotEqual(rejected.headers.get("access-control-allow-origin"), "https://evil.example")

    def test_passwords_tokens_and_hashes_are_absent_from_logs_and_responses(self):
        with self.assertLogs("backend.app", level="INFO") as captured:
            signup = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
                "name": "Log Safety",
                "email": "logs@aust.edu",
                "password": PASSWORD,
            })
            token = self.client.cookies.get("occupai_session")
            changed = self.client.post(
                "/api/profile/change-password",
                headers={"Origin": ORIGIN},
                json={"current_password": PASSWORD, "new_password": "New-password-84!"},
            )
        combined = signup.text + changed.text + "\n".join(captured.output)
        self.assertNotIn(PASSWORD, combined)
        self.assertNotIn("New-password-84!", combined)
        self.assertNotIn(token, combined)
        self.assertNotIn("password_hash", combined)


if __name__ == "__main__":
    unittest.main()
