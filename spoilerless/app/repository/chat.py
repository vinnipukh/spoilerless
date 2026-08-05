"""Persistence for chat sessions and messages (RAG-09, RAG-10).

All queries are user-scoped: every read/write starts from the authenticated
``(:AppUser)`` node, so a foreign session is indistinguishable from a missing
one (generic not-found — hidden and missing behave identically, by design).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from spoilerless.app.domain.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    MessageStatus,
)
from spoilerless.app.graph.chat import (
    CHAT_MESSAGE_CREATE_QUERY,
    CHAT_MESSAGE_LIST_QUERY,
    CHAT_MESSAGE_STATUS_UPDATE_QUERY,
    CHAT_SESSION_CREATE_QUERY,
    CHAT_SESSION_DELETE_QUERY,
    CHAT_SESSION_GET_QUERY,
    CHAT_SESSION_LIST_QUERY,
)
from spoilerless.app.graph.database import Neo4jDatabase


class ChatSessionNotFound(LookupError):
    """The session is missing, or belongs to another user (indistinguishable)."""


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Convert Neo4j temporal types to Pydantic-compatible values."""
    result: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, bytes):
            result[key] = value
        elif hasattr(value, "iso_format"):
            result[key] = value.iso_format()
        elif hasattr(value, "to_native"):
            native = value.to_native()
            result[key] = native.isoformat() if hasattr(native, "isoformat") else str(native)
        else:
            result[key] = value
    return result


class ChatRepository:
    """Read/write access to chat sessions and messages."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def create_session(
        self, user_id: str, series_id: str, title: str
    ) -> ChatSessionResponse:
        now = datetime.now(timezone.utc)
        records = await self._database.execute_query(
            CHAT_SESSION_CREATE_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=f"chat-session:{uuid4()}",
            # Normalize so no client payload shape can brick session
            # creation: empty/whitespace titles (the frontend's default)
            # persist as the app's default conversation label.
            title=title.strip() or "New conversation",
            created_at=now,
        )
        return ChatSessionResponse.model_validate(_normalize(records[0]))

    async def get_session(
        self, user_id: str, series_id: str, session_id: str
    ) -> ChatSessionResponse:
        """Return the user-scoped session, or raise ``ChatSessionNotFound``.

        A single user-scoped query suffices: foreign and missing sessions both
        produce the identical generic not-found (the two-query ownership
        pattern in 06-PATTERNS.md exists for mutation paths that must decide
        404-vs-409 internally; reads have only one public outcome).
        """
        records = await self._database.execute_query(
            CHAT_SESSION_GET_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=session_id,
        )
        if not records:
            raise ChatSessionNotFound(
                f"Chat session {session_id} not found for this user."
            )
        return ChatSessionResponse.model_validate(_normalize(records[0]))

    async def list_sessions(
        self, user_id: str, series_id: str
    ) -> list[ChatSessionResponse]:
        records = await self._database.execute_query(
            CHAT_SESSION_LIST_QUERY,
            user_id=user_id,
            series_id=series_id,
        )
        return [ChatSessionResponse.model_validate(_normalize(r)) for r in records]

    async def delete_session(
        self, user_id: str, series_id: str, session_id: str
    ) -> None:
        """Hard-delete the user's session and every message it owns.

        Raises ``ChatSessionNotFound`` for foreign, cross-series, or missing
        sessions — the identical generic not-found used everywhere else in
        this module (cross-user and missing are indistinguishable by design).
        """
        records = await self._database.execute_query(
            CHAT_SESSION_DELETE_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=session_id,
        )
        if not records:
            raise ChatSessionNotFound(
                f"Chat session {session_id} not found for this user."
            )

    async def create_message(
        self,
        user_id: str,
        series_id: str,
        session_id: str,
        *,
        role: str,
        content: str,
        visible_until_order_snapshot: int,
        status: MessageStatus = MessageStatus.COMPLETED,
        citations: list[dict[str, Any]] | None = None,
        graph_focus: dict[str, Any] | None = None,
    ) -> ChatMessageResponse:
        """Append a message to the user's session (ownership-scoped CREATE).

        Raises ``ChatSessionNotFound`` when the session does not exist for
        this user — before any message is created.
        """
        records = await self._database.execute_query(
            CHAT_MESSAGE_CREATE_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=session_id,
            message_id=f"chat-message:{uuid4()}",
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
            visible_until_order_snapshot=visible_until_order_snapshot,
            status=status,
            citations_json=json.dumps(citations or []),
            graph_focus_json=json.dumps(graph_focus or {}),
        )
        if not records:
            raise ChatSessionNotFound(
                f"Chat session {session_id} not found for this user."
            )
        return ChatMessageResponse.model_validate(_normalize(records[0]))

    async def update_message_status(
        self,
        user_id: str,
        series_id: str,
        session_id: str,
        message_id: str,
        status: MessageStatus,
    ) -> None:
        """Flip one persisted message's status (owner-scoped SET, PROB-13/#35).

        Used by the service to mark a turn's user message ``failed`` when
        the generation dies mid-stream (never an orphaned pending message)
        or ``completed`` once the done envelope is delivered. A foreign or
        missing message simply matches zero rows — no error, no disclosure.
        """
        await self._database.execute_query(
            CHAT_MESSAGE_STATUS_UPDATE_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=session_id,
            message_id=message_id,
            status=status,
        )

    async def _list_messages(
        self,
        user_id: str,
        series_id: str,
        session_id: str,
        visible_until_order: int,
    ) -> list[dict[str, Any]]:
        records = await self._database.execute_query(
            CHAT_MESSAGE_LIST_QUERY,
            user_id=user_id,
            series_id=series_id,
            session_id=session_id,
            visible_until_order=visible_until_order,
        )
        return [_normalize(r) for r in records]

    async def list_messages_for_context(
        self,
        user_id: str,
        series_id: str,
        session_id: str,
        visible_until_order: int,
    ) -> list[dict[str, Any]]:
        """Prior-turn messages for LLM conversation memory (same filter as
        :meth:`list_messages_for_response` — one shared query)."""
        return await self._list_messages(
            user_id, series_id, session_id, visible_until_order
        )

    async def list_messages_for_response(
        self,
        user_id: str,
        series_id: str,
        session_id: str,
        visible_until_order: int,
    ) -> list[ChatMessageResponse]:
        """Messages visible at the current boundary for the API response."""
        rows = await self._list_messages(
            user_id, series_id, session_id, visible_until_order
        )
        return [ChatMessageResponse.model_validate(row) for row in rows]
