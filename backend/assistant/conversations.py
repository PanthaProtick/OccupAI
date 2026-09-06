from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from backend.auth import AuthError
from backend.database import AssistantConversationRow, AssistantMessageRow
from backend.models import (
    AssistantConversation,
    AssistantConversationListResponse,
    AssistantConversationSummary,
    AssistantMessage,
)


MAX_CONVERSATIONS_PER_USER = 100
MAX_MESSAGES_PER_CONVERSATION = 200


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _message(row: AssistantMessageRow) -> AssistantMessage:
    structured = json.loads(row.structured_results) if row.structured_results else None
    return AssistantMessage(
        id=row.id,
        role=row.role,
        content=row.content,
        structured_results=structured,
        created_at=_datetime(row.created_at),
    )


class AssistantConversationService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def record_exchange(
        self,
        user_id: str,
        conversation_id: uuid.UUID | None,
        user_content: str,
        assistant_content: str,
        structured_results: dict,
    ) -> uuid.UUID:
        user_time = datetime.now(timezone.utc)
        assistant_time = user_time + timedelta(microseconds=1)
        now = user_time.isoformat()
        assistant_timestamp = assistant_time.isoformat()
        with self.session_factory() as db:
            conversation = None
            if conversation_id is not None:
                conversation = db.scalar(select(AssistantConversationRow).where(
                    AssistantConversationRow.id == str(conversation_id),
                    AssistantConversationRow.user_id == user_id,
                ))
                if conversation is None:
                    raise AuthError(404, "conversation_not_found", "Conversation was not found.")
            else:
                count = db.scalar(
                    select(func.count()).select_from(AssistantConversationRow).where(
                        AssistantConversationRow.user_id == user_id
                    )
                ) or 0
                if count >= MAX_CONVERSATIONS_PER_USER:
                    raise AuthError(
                        409, "conversation_limit_reached",
                        "The conversation limit has been reached. Delete an older conversation and try again.",
                    )
                conversation_id = uuid.uuid4()
                title = " ".join(user_content.split())[:80].rstrip() or None
                conversation = AssistantConversationRow(
                    id=str(conversation_id), user_id=user_id, title=title,
                    created_at=now, updated_at=now,
                )
                db.add(conversation)
                db.flush()

            message_count = db.scalar(
                select(func.count()).select_from(AssistantMessageRow).where(
                    AssistantMessageRow.conversation_id == conversation.id
                )
            ) or 0
            if message_count + 2 > MAX_MESSAGES_PER_CONVERSATION:
                raise AuthError(
                    409, "conversation_message_limit_reached",
                    "This conversation is full. Start a new conversation.",
                )

            db.add_all([
                AssistantMessageRow(
                    id=str(uuid.uuid4()), conversation_id=conversation.id, role="user",
                    content=user_content, structured_results=None, created_at=now,
                ),
                AssistantMessageRow(
                    id=str(uuid.uuid4()), conversation_id=conversation.id, role="assistant",
                    content=assistant_content,
                    structured_results=json.dumps(structured_results, separators=(",", ":")),
                    created_at=assistant_timestamp,
                ),
            ])
            conversation.updated_at = assistant_timestamp
            db.commit()
            return uuid.UUID(conversation.id)

    def list_conversations(
        self, user_id: str, *, page: int, limit: int
    ) -> AssistantConversationListResponse:
        with self.session_factory() as db:
            rows = db.execute(
                select(AssistantConversationRow, func.count(AssistantMessageRow.id))
                .outerjoin(
                    AssistantMessageRow,
                    AssistantMessageRow.conversation_id == AssistantConversationRow.id,
                )
                .where(AssistantConversationRow.user_id == user_id)
                .group_by(AssistantConversationRow.id)
                .order_by(
                    AssistantConversationRow.updated_at.desc(),
                    AssistantConversationRow.id.desc(),
                )
                .offset((page - 1) * limit)
                .limit(limit + 1)
            ).all()
            has_more = len(rows) > limit
            items = [
                AssistantConversationSummary(
                    id=conversation.id, title=conversation.title,
                    created_at=_datetime(conversation.created_at),
                    updated_at=_datetime(conversation.updated_at), message_count=count,
                )
                for conversation, count in rows[:limit]
            ]
            return AssistantConversationListResponse(
                items=items, page=page, limit=limit,
                next_page=page + 1 if has_more else None,
            )

    def get_conversation(self, user_id: str, conversation_id: uuid.UUID) -> AssistantConversation:
        with self.session_factory() as db:
            conversation = db.scalar(select(AssistantConversationRow).where(
                AssistantConversationRow.id == str(conversation_id),
                AssistantConversationRow.user_id == user_id,
            ))
            if conversation is None:
                raise AuthError(404, "conversation_not_found", "Conversation was not found.")
            messages = list(db.scalars(
                select(AssistantMessageRow)
                .where(AssistantMessageRow.conversation_id == conversation.id)
                .order_by(AssistantMessageRow.created_at, AssistantMessageRow.id)
            ))
            return AssistantConversation(
                id=conversation.id, title=conversation.title,
                created_at=_datetime(conversation.created_at),
                updated_at=_datetime(conversation.updated_at),
                messages=[_message(message) for message in messages],
            )

    def delete_conversation(self, user_id: str, conversation_id: uuid.UUID) -> None:
        with self.session_factory() as db:
            conversation = db.scalar(select(AssistantConversationRow).where(
                AssistantConversationRow.id == str(conversation_id),
                AssistantConversationRow.user_id == user_id,
            ))
            if conversation is None:
                raise AuthError(404, "conversation_not_found", "Conversation was not found.")
            db.delete(conversation)
            db.commit()
