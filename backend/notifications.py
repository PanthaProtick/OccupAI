from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select, update

from backend.auth import AuthError
from backend.database import NotificationPreferenceRow, UserNotificationRow
from backend.models import (
    Notification,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationsResponse,
)


def _as_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _notification(row: UserNotificationRow) -> Notification:
    return Notification(
        id=row.id,
        type=row.type,
        category=row.category,
        title=row.title,
        message=row.message,
        room_id=row.room_id,
        suggested_room_id=row.suggested_room_id,
        occupancy_percentage=row.occupancy_percentage,
        created_at=datetime.fromisoformat(row.created_at),
        read_at=_as_datetime(row.read_at),
        dismissed_at=_as_datetime(row.dismissed_at),
    )


def _encode_cursor(row: UserNotificationRow) -> str:
    payload = json.dumps([row.created_at, row.id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if not isinstance(payload, list) or len(payload) != 2:
            raise ValueError
        created_at, notification_id = payload
        parsed = datetime.fromisoformat(created_at)
        if parsed.utcoffset() is None or not isinstance(notification_id, str) or not notification_id:
            raise ValueError
        return created_at, notification_id
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        raise AuthError(400, "invalid_cursor", "The notification cursor is invalid.")


class NotificationService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def list_notifications(
        self,
        user_id: str,
        *,
        limit: int,
        cursor: str | None,
        unread_only: bool,
        include_dismissed: bool,
    ) -> NotificationsResponse:
        filters = [UserNotificationRow.user_id == user_id]
        if unread_only:
            filters.append(UserNotificationRow.read_at.is_(None))
        if not include_dismissed:
            filters.append(UserNotificationRow.dismissed_at.is_(None))
        if cursor:
            created_at, notification_id = _decode_cursor(cursor)
            filters.append(or_(
                UserNotificationRow.created_at < created_at,
                and_(
                    UserNotificationRow.created_at == created_at,
                    UserNotificationRow.id < notification_id,
                ),
            ))

        with self.session_factory() as db:
            rows = list(db.scalars(
                select(UserNotificationRow)
                .where(*filters)
                .order_by(UserNotificationRow.created_at.desc(), UserNotificationRow.id.desc())
                .limit(limit + 1)
            ))
            unread_count = db.scalar(
                select(func.count())
                .select_from(UserNotificationRow)
                .where(
                    UserNotificationRow.user_id == user_id,
                    UserNotificationRow.read_at.is_(None),
                    UserNotificationRow.dismissed_at.is_(None),
                )
            ) or 0
            has_more = len(rows) > limit
            page = rows[:limit]
            return NotificationsResponse(
                items=[_notification(row) for row in page],
                unread_count=unread_count,
                next_cursor=_encode_cursor(page[-1]) if has_more and page else None,
            )

    def mark_read(self, user_id: str, notification_id: str) -> Notification:
        with self.session_factory() as db:
            row = db.scalar(select(UserNotificationRow).where(
                UserNotificationRow.id == notification_id,
                UserNotificationRow.user_id == user_id,
            ))
            if row is None:
                raise AuthError(404, "notification_not_found", "Notification was not found.")
            if row.read_at is None:
                row.read_at = datetime.now(timezone.utc).isoformat()
                db.commit()
            return _notification(row)

    def mark_all_read(self, user_id: str) -> None:
        with self.session_factory() as db:
            db.execute(
                update(UserNotificationRow)
                .where(
                    UserNotificationRow.user_id == user_id,
                    UserNotificationRow.read_at.is_(None),
                )
                .values(read_at=datetime.now(timezone.utc).isoformat())
            )
            db.commit()

    def dismiss(self, user_id: str, notification_id: str) -> None:
        with self.session_factory() as db:
            row = db.scalar(select(UserNotificationRow).where(
                UserNotificationRow.id == notification_id,
                UserNotificationRow.user_id == user_id,
            ))
            if row is None:
                raise AuthError(404, "notification_not_found", "Notification was not found.")
            if row.dismissed_at is None:
                row.dismissed_at = datetime.now(timezone.utc).isoformat()
                db.commit()

    @staticmethod
    def _preferences(row: NotificationPreferenceRow) -> NotificationPreferences:
        return NotificationPreferences(
            in_app_enabled=row.in_app_enabled,
            high_occupancy_enabled=row.high_occupancy_enabled,
            high_occupancy_threshold=row.high_occupancy_threshold,
            cooldown_minutes=row.cooldown_minutes,
        )

    def get_preferences(self, user_id: str) -> NotificationPreferences:
        with self.session_factory() as db:
            row = db.get(NotificationPreferenceRow, user_id)
            if row is None:
                now = datetime.now(timezone.utc).isoformat()
                row = NotificationPreferenceRow(
                    user_id=user_id,
                    in_app_enabled=True,
                    high_occupancy_enabled=True,
                    high_occupancy_threshold=80,
                    cooldown_minutes=30,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                db.commit()
            return self._preferences(row)

    def update_preferences(
        self,
        user_id: str,
        payload: NotificationPreferencesUpdate,
    ) -> NotificationPreferences:
        with self.session_factory() as db:
            row = db.get(NotificationPreferenceRow, user_id)
            now = datetime.now(timezone.utc).isoformat()
            if row is None:
                row = NotificationPreferenceRow(
                    user_id=user_id,
                    in_app_enabled=True,
                    high_occupancy_enabled=True,
                    high_occupancy_threshold=80,
                    cooldown_minutes=30,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(row, field, value)
            row.updated_at = now
            db.commit()
            return self._preferences(row)
