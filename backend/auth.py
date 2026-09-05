from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, Request
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.database import AuthenticationSessionRow, UserRow
from backend.models import Profile, PublicUser

AUST_EMAIL_MESSAGE = "Use your AUST email address ending in @aust.edu."
MAX_PASSWORD_LENGTH = 128
_EMAIL_LOCAL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_DUMMY_HASHER = PasswordHasher()
_DUMMY_HASH = _DUMMY_HASHER.hash("not-a-real-password-Only4Timing!")


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def normalize_email(value: str, *, require_aust: bool = False) -> str:
    email = value.strip()
    if email.count("@") != 1:
        raise AuthError(422, "aust_email_required" if require_aust else "invalid_credentials",
                        AUST_EMAIL_MESSAGE if require_aust else "Email or password is incorrect.")
    local, domain = email.rsplit("@", 1)
    domain = domain.lower()
    if not local or not _EMAIL_LOCAL.fullmatch(local) or not domain:
        raise AuthError(422, "aust_email_required" if require_aust else "invalid_credentials",
                        AUST_EMAIL_MESSAGE if require_aust else "Email or password is incorrect.")
    if require_aust and domain != "aust.edu":
        raise AuthError(422, "aust_email_required", AUST_EMAIL_MESSAGE)
    return f"{local.lower()}@{domain}"


def validate_password(password: str) -> None:
    if len(password) < 6:
        raise AuthError(422, "weak_password", "Use at least 6 characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise AuthError(
            422,
            "weak_password",
            f"Password must be {MAX_PASSWORD_LENGTH} characters or fewer.",
        )


class AuthService:
    def __init__(self, session_factory, pepper: str, ttl_seconds: int):
        self.session_factory = session_factory
        self.pepper = pepper.encode()
        self.ttl_seconds = ttl_seconds
        self.passwords = PasswordHasher()

    def _token_hash(self, token: str) -> str:
        return hmac.new(self.pepper, token.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _public(user: UserRow) -> PublicUser:
        return PublicUser(id=user.id, name=user.name, email=user.normalized_email,
                          role=user.role, created_at=datetime.fromisoformat(user.created_at))

    @staticmethod
    def _profile(user: UserRow) -> Profile:
        return Profile(
            id=user.id,
            name=user.name,
            email=user.normalized_email,
            created_at=datetime.fromisoformat(user.created_at),
            updated_at=datetime.fromisoformat(user.updated_at),
        )

    def _new_session(self, db, user: UserRow, user_agent: str | None) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expired_ids = list(db.scalars(select(AuthenticationSessionRow.id).where(
            AuthenticationSessionRow.expires_at <= now.isoformat()).limit(100)))
        if expired_ids:
            db.execute(delete(AuthenticationSessionRow).where(AuthenticationSessionRow.id.in_(expired_ids)))
        db.add(AuthenticationSessionRow(
            id=str(uuid.uuid4()), user_id=user.id, token_hash=self._token_hash(token),
            created_at=now.isoformat(), expires_at=(now + timedelta(seconds=self.ttl_seconds)).isoformat(),
            user_agent=(user_agent or "")[:512] or None,
        ))
        return token

    def signup(self, name: str, email: str, password: str, user_agent: str | None):
        normalized = normalize_email(email, require_aust=True)
        validate_password(password)
        clean_name = " ".join(name.split())
        if len(clean_name) < 2:
            raise AuthError(422, "invalid_name", "Enter your full name.")
        now = datetime.now(timezone.utc).isoformat()
        with self.session_factory() as db:
            user = UserRow(id=str(uuid.uuid4()), name=clean_name, email=normalized,
                           normalized_email=normalized, password_hash=self.passwords.hash(password),
                           role="user", is_active=True, created_at=now, updated_at=now)
            db.add(user)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise AuthError(409, "email_already_registered", "An account already exists for this email.")
            token = self._new_session(db, user, user_agent)
            db.commit()
            return self._public(user), token

    def login(self, email: str, password: str, user_agent: str | None):
        try:
            normalized = normalize_email(email)
        except AuthError:
            normalized = "invalid@invalid"
        with self.session_factory() as db:
            user = db.scalar(select(UserRow).where(UserRow.normalized_email == normalized))
            password_hash = user.password_hash if user else _DUMMY_HASH
            try:
                valid = self.passwords.verify(password_hash, password)
            except (VerifyMismatchError, InvalidHashError):
                valid = False
            if not user or not valid or not user.is_active:
                raise AuthError(401, "invalid_credentials", "Email or password is incorrect.")
            if self.passwords.check_needs_rehash(user.password_hash):
                user.password_hash = self.passwords.hash(password)
            user.last_login_at = datetime.now(timezone.utc).isoformat()
            user.updated_at = user.last_login_at
            token = self._new_session(db, user, user_agent)
            db.commit()
            return self._public(user), token

    def authenticate(self, token: str | None) -> PublicUser:
        if not token:
            raise AuthError(401, "authentication_required", "Authentication is required.")
        now = datetime.now(timezone.utc)
        with self.session_factory() as db:
            session = db.scalar(select(AuthenticationSessionRow).where(
                AuthenticationSessionRow.token_hash == self._token_hash(token)))
            if (not session or session.revoked_at is not None
                    or datetime.fromisoformat(session.expires_at) <= now):
                raise AuthError(401, "authentication_required", "Authentication is required.")
            user = db.get(UserRow, session.user_id)
            if not user or not user.is_active:
                raise AuthError(401, "authentication_required", "Authentication is required.")
            session.last_used_at = now.isoformat()
            db.commit()
            return self._public(user)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self.session_factory() as db:
            session = db.scalar(select(AuthenticationSessionRow).where(
                AuthenticationSessionRow.token_hash == self._token_hash(token)))
            if session and session.revoked_at is None:
                session.revoked_at = datetime.now(timezone.utc).isoformat()
                db.commit()

    def get_profile(self, user_id: str) -> Profile:
        with self.session_factory() as db:
            user = db.get(UserRow, user_id)
            if not user or not user.is_active:
                raise AuthError(401, "authentication_required", "Authentication is required.")
            return self._profile(user)

    def update_profile_name(self, user_id: str, name: str) -> Profile:
        clean_name = " ".join(name.split())
        if not clean_name:
            raise AuthError(422, "invalid_name", "Name cannot be empty.")
        if len(clean_name) > 120:
            raise AuthError(422, "invalid_name", "Name must be 120 characters or fewer.")
        with self.session_factory() as db:
            user = db.get(UserRow, user_id)
            if not user or not user.is_active:
                raise AuthError(401, "authentication_required", "Authentication is required.")
            user.name = clean_name
            user.updated_at = datetime.now(timezone.utc).isoformat()
            db.commit()
            return self._profile(user)

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        user_agent: str | None,
    ) -> str:
        with self.session_factory() as db:
            user = db.get(UserRow, user_id)
            if not user or not user.is_active:
                raise AuthError(401, "authentication_required", "Authentication is required.")
            try:
                current_is_valid = self.passwords.verify(user.password_hash, current_password)
            except (VerifyMismatchError, InvalidHashError):
                current_is_valid = False
            if not current_is_valid:
                raise AuthError(400, "invalid_current_password", "Password could not be changed.")

            validate_password(new_password)
            try:
                password_is_unchanged = self.passwords.verify(user.password_hash, new_password)
            except (VerifyMismatchError, InvalidHashError):
                password_is_unchanged = False
            if password_is_unchanged:
                raise AuthError(422, "password_unchanged", "Choose a different password.")

            now = datetime.now(timezone.utc).isoformat()
            user.password_hash = self.passwords.hash(new_password)
            user.updated_at = now
            db.execute(
                update(AuthenticationSessionRow)
                .where(
                    AuthenticationSessionRow.user_id == user.id,
                    AuthenticationSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            token = self._new_session(db, user, user_agent)
            db.commit()
            return token


def get_current_user(request: Request) -> PublicUser:
    """Reusable authentication dependency for future private API routes."""
    settings = request.app.state.settings
    service = request.app.state.get_auth_service()
    return service.authenticate(request.cookies.get(settings.auth_cookie_name))


def require_admin(user: PublicUser = Depends(get_current_user)) -> PublicUser:
    if user.role != "admin":
        raise AuthError(403, "admin_required", "Administrator access is required.")
    return user
