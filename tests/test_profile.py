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


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "profile.db"
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

    def signup(self):
        return self.client.post("/api/auth/signup", headers={"Origin": ORIGIN}, json={
            "name": "AUST Student",
            "email": "Student@AUST.EDU",
            "password": PASSWORD,
        })

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")

    def test_profile_returns_fresh_safe_database_fields_and_no_store(self):
        self.assertEqual(self.signup().status_code, 201)
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        self.assertEqual(set(response.json()), {"id", "name", "email", "created_at", "updated_at"})
        self.assertEqual(response.json()["name"], "AUST Student")
        self.assertEqual(response.json()["email"], "student@aust.edu")
        self.assertNotIn("password", response.text.lower())
        self.assertNotIn("token", response.text.lower())

    def test_profile_name_update_is_trimmed_and_persisted(self):
        self.signup()
        response = self.client.patch(
            "/api/profile",
            headers={"Origin": ORIGIN},
            json={"name": "  Updated   Student  "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated Student")
        self.assertEqual(response.json()["email"], "student@aust.edu")
        self.assertEqual(response.headers.get("cache-control"), "no-store")

        engine = create_engine(self.url)
        with Session(engine) as db:
            user = db.scalar(select(UserRow))
            assert user is not None
            self.assertEqual(user.name, "Updated Student")
            self.assertEqual(user.normalized_email, "student@aust.edu")
        engine.dispose()

        self.assertEqual(
            self.client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/profile").status_code, 401)
        login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "STUDENT@AUST.EDU",
            "password": PASSWORD,
        })
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/profile").json()["name"], "Updated Student")

    def test_profile_update_rejects_invalid_names_without_changing_database(self):
        self.signup()
        for name in ("   ", "x" * 121):
            with self.subTest(name_length=len(name)):
                response = self.client.patch(
                    "/api/profile", headers={"Origin": ORIGIN}, json={"name": name}
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["code"], "invalid_name")
        self.assertEqual(self.client.get("/api/profile").json()["name"], "AUST Student")

    def test_profile_update_rejects_missing_origin_and_unsupported_fields(self):
        self.signup()
        no_origin = self.client.patch("/api/profile", json={"name": "Changed Name"})
        self.assertEqual(no_origin.status_code, 403)
        self.assertEqual(no_origin.json()["error"]["code"], "invalid_origin")

        for payload in (
            {"name": "Changed Name", "email": "other@aust.edu"},
            {"name": "Changed Name", "role": "admin"},
            {"name": "Changed Name", "password_hash": "unsafe"},
            {"name": "Changed Name", "id": "other-user"},
            {"name": "Changed Name", "updated_at": "2000-01-01T00:00:00Z"},
        ):
            with self.subTest(field=set(payload) - {"name"}):
                response = self.client.patch(
                    "/api/profile", headers={"Origin": ORIGIN}, json=payload
                )
                self.assertEqual(response.status_code, 400)
        profile = self.client.get("/api/profile").json()
        self.assertEqual(profile["name"], "AUST Student")
        self.assertEqual(profile["email"], "student@aust.edu")

    def test_password_change_replaces_hash_rotates_current_and_revokes_other_sessions(self):
        self.signup()
        first_token = self.client.cookies.get("occupai_session")
        self.client.cookies.clear()
        second_login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": PASSWORD,
        })
        self.assertEqual(second_login.status_code, 200)
        second_token = self.client.cookies.get("occupai_session")
        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", first_token)

        engine = create_engine(self.url)
        with Session(engine) as db:
            original_hash = db.scalar(select(UserRow.password_hash))

        changed = self.client.post(
            "/api/profile/change-password",
            headers={"Origin": ORIGIN},
            json={"current_password": PASSWORD, "new_password": "New-password-84!"},
        )
        self.assertEqual(changed.status_code, 204)
        rotated_token = changed.cookies.get("occupai_session")
        self.assertNotIn(rotated_token, {first_token, second_token})
        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", rotated_token)
        self.assertEqual(self.client.get("/api/profile").status_code, 200)

        with Session(engine) as db:
            user = db.scalar(select(UserRow))
            sessions = list(db.scalars(select(AuthenticationSessionRow)))
            assert user is not None
            self.assertNotEqual(user.password_hash, original_hash)
            self.assertTrue(user.password_hash.startswith("$argon2id$"))
            self.assertNotIn(PASSWORD, user.password_hash)
            self.assertNotIn("New-password-84!", user.password_hash)
            self.assertEqual(sum(session.revoked_at is None for session in sessions), 1)
            token_hash = self.client.app.state.get_auth_service()._token_hash
            by_token = {session.token_hash: session for session in sessions}
            self.assertIsNotNone(by_token[token_hash(first_token)].revoked_at)
            self.assertIsNotNone(by_token[token_hash(second_token)].revoked_at)
            self.assertIsNone(by_token[token_hash(rotated_token)].revoked_at)
        engine.dispose()

        self.client.cookies.clear()
        self.client.cookies.set("occupai_session", second_token)
        self.assertEqual(self.client.get("/api/profile").status_code, 401)
        self.client.cookies.clear()
        old_login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": PASSWORD,
        })
        self.assertEqual(old_login.status_code, 401)
        new_login = self.client.post("/api/auth/login", headers={"Origin": ORIGIN}, json={
            "email": "student@aust.edu", "password": "New-password-84!",
        })
        self.assertEqual(new_login.status_code, 200)

        # A fresh application/engine proves that the new hash is durable rather than
        # held only in the process that handled the password change.
        restarted_settings = Settings(
            database_url=self.url,
            auth_session_pepper="test-pepper-that-is-long-enough",
        )
        with TestClient(create_app(
            restarted_settings,
            MockOccupancyRepository(restarted_settings.mock_data_dir),
        )) as restarted:
            persisted_login = restarted.post(
                "/api/auth/login",
                headers={"Origin": ORIGIN},
                json={"email": "student@aust.edu", "password": "New-password-84!"},
            )
            self.assertEqual(persisted_login.status_code, 200)

    def test_password_change_rejects_wrong_weak_long_and_unchanged_passwords(self):
        self.signup()
        engine = create_engine(self.url)
        with Session(engine) as db:
            original_hash = db.scalar(select(UserRow.password_hash))

        cases = (
            ({"current_password": "incorrect", "new_password": "New-password-84!"}, 400,
             "invalid_current_password"),
            ({"current_password": PASSWORD, "new_password": "short"}, 422, "weak_password"),
            ({"current_password": PASSWORD, "new_password": "x" * 129}, 422, "weak_password"),
            ({"current_password": PASSWORD, "new_password": PASSWORD}, 422, "password_unchanged"),
        )
        for payload, status, code in cases:
            with self.subTest(code=code, new_length=len(payload["new_password"])):
                response = self.client.post(
                    "/api/profile/change-password", headers={"Origin": ORIGIN}, json=payload
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["error"]["code"], code)
                self.assertNotIn(payload["current_password"], response.text)
                self.assertNotIn(payload["new_password"], response.text)

        with Session(engine) as db:
            self.assertEqual(db.scalar(select(UserRow.password_hash)), original_hash)
        engine.dispose()
        self.assertEqual(self.client.get("/api/profile").status_code, 200)

    def test_password_change_requires_authentication_and_origin(self):
        payload = {"current_password": PASSWORD, "new_password": "New-password-84!"}
        unauthenticated = self.client.post(
            "/api/profile/change-password", headers={"Origin": ORIGIN}, json=payload
        )
        self.assertEqual(unauthenticated.status_code, 401)
        self.signup()
        missing_origin = self.client.post("/api/profile/change-password", json=payload)
        self.assertEqual(missing_origin.status_code, 403)
        self.assertEqual(missing_origin.json()["error"]["code"], "invalid_origin")

    def test_password_change_is_rate_limited(self):
        self.signup()
        payload = {"current_password": "incorrect", "new_password": "New-password-84!"}
        for _ in range(10):
            response = self.client.post(
                "/api/profile/change-password", headers={"Origin": ORIGIN}, json=payload
            )
            self.assertEqual(response.status_code, 400)
        blocked = self.client.post(
            "/api/profile/change-password", headers={"Origin": ORIGIN}, json=payload
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "rate_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
