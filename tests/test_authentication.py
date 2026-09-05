from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app import create_app
from backend.config import Settings
from backend.database import AuthenticationSessionRow, Base, UserRow
from backend.repositories import MockOccupancyRepository


ORIGIN = "http://localhost:5173"
PASSWORD = "Strong-password-42!"


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "auth.db"
        url = f"sqlite:///{database.as_posix()}"
        self.url = url
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        engine.dispose()
        settings = Settings(database_url=url, auth_session_pepper="test-pepper-that-is-long-enough")
        repository = MockOccupancyRepository(settings.mock_data_dir)
        self.client = TestClient(create_app(settings, repository))

    def tearDown(self):
        engine = self.client.app.state.auth_engine
        if engine is not None:
            engine.dispose()
        self.client.close()
        self.temp.cleanup()

    def signup(self, email="student@aust.edu"):
        return self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "AUST Student", "email": email, "password": PASSWORD,
        })

    def test_signup_accepts_exact_aust_domain_case_insensitively(self):
        response = self.signup("Student@AUST.EDU")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["email"], "student@aust.edu")
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)

    def test_signup_accepts_six_character_password_and_rejects_five(self):
        accepted = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Short Password", "email": "short@aust.edu", "password": "abcdef",
        })
        self.assertEqual(accepted.status_code, 201)
        rejected = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Too Short", "email": "tiny@aust.edu", "password": "abcde",
        })
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(rejected.json()["error"]["message"], "Use at least 6 characters.")

    def test_signup_rejects_deceptive_and_non_aust_domains(self):
        for email in (
            "user@aust.edu.example.com", "user@fakeaust.edu",
            "user+aust.edu@example.com", "user@example.com",
        ):
            with self.subTest(email=email):
                response = self.signup(email)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["code"], "aust_email_required")
                self.assertEqual(response.json()["error"]["message"],
                                 "Use your AUST email address ending in @aust.edu.")

    def test_login_me_logout_session_lifecycle(self):
        self.assertEqual(self.signup().status_code, 201)
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "STUDENT@AUST.EDU", "password": PASSWORD,
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        logout = self.client.post("/api/auth/logout", headers={"Origin": ORIGIN})
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_duplicate_weak_password_bad_credentials_and_csrf(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup().status_code, 409)
        weak = self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "Weak User", "email": "weak@aust.edu", "password": "short",
        })
        self.assertIn(weak.status_code, (400, 422))
        bad = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": "wrong",
        })
        self.assertEqual(bad.status_code, 401)
        no_origin = self.client.post("/api/auth/login", json={
            "email": "student@aust.edu", "password": PASSWORD,
        })
        self.assertEqual(no_origin.status_code, 403)

    def test_duplicate_is_case_insensitive_and_login_errors_are_generic(self):
        self.assertEqual(self.signup("Student@AUST.EDU").status_code, 201)
        self.assertEqual(self.signup("student@aust.edu").status_code, 409)
        self.client.cookies.clear()
        unknown = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "unknown@aust.edu", "password": PASSWORD})
        incorrect = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": "Incorrect-password-42!"})
        self.assertEqual(unknown.json(), incorrect.json())

    def test_secrets_are_hashed_and_invalid_revoked_expired_sessions_fail(self):
        response = self.signup()
        self.assertNotIn("password", response.text.lower())
        self.assertNotIn("token", response.text.lower())
        raw_cookie = self.client.cookies.get("occupai_session")
        engine = create_engine(self.url)
        with Session(engine) as db:
            user = db.scalar(select(UserRow))
            session = db.scalar(select(AuthenticationSessionRow))
            assert user is not None and session is not None
            self.assertNotEqual(user.password_hash, PASSWORD)
            self.assertNotEqual(session.token_hash, raw_cookie)
            session.expires_at = "2000-01-01T00:00:00+00:00"
            db.commit()
        engine.dispose()
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.cookies.set("occupai_session", "invalid-token")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_inactive_account_cannot_login(self):
        self.signup()
        self.client.cookies.clear()
        engine = create_engine(self.url)
        with engine.begin() as db:
            db.execute(UserRow.__table__.update().values(is_active=False))
        engine.dispose()
        response = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": PASSWORD})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")

    def test_cors_allows_credentials_only_for_configured_origin(self):
        allowed = self.client.options("/api/auth/login", headers={
            "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers.get("access-control-allow-credentials"), "true")
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), ORIGIN)
        rejected = self.client.options("/api/auth/login", headers={
            "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
        })
        self.assertNotEqual(rejected.headers.get("access-control-allow-origin"), "https://evil.example")

    def test_rate_limit_returns_standard_error_envelope(self):
        for _ in range(10):
            response = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
                "email": "limited@aust.edu", "password": "wrong!"})
            self.assertEqual(response.status_code, 401)
        blocked = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "limited@aust.edu", "password": "wrong!"})
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "rate_limit_exceeded")

    def test_production_rejects_insecure_cookie_and_default_pepper(self):
        with self.assertRaisesRegex(ValueError, "AUTH_COOKIE_SECURE"):
            Settings(app_environment="production")
        with self.assertRaisesRegex(ValueError, "AUTH_SESSION_PEPPER"):
            Settings(app_environment="production", auth_cookie_secure=True)

    def test_startup_rejects_unmigrated_authentication_schema(self):
        empty_url = f"sqlite:///{(Path(self.temp.name) / 'empty.db').as_posix()}"
        app = create_app(Settings(database_url=empty_url))
        with self.assertRaisesRegex(RuntimeError, "Authentication schema is not migrated"):
            with TestClient(app):
                pass


if __name__ == "__main__":
    unittest.main()
