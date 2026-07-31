"""Persistence for the ChangeSet Stage 1 (Propose) draft resource (RAG-11).

Every query is user-scoped through the authenticated ``(:AppUser)`` node —
a foreign or missing ``chat_session_id`` is indistinguishable from a missing
one (generic not-found), the same convention ``repository/chat.py`` uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.app.domain.change_set import ChangeSetOperation, ChangeSetResponse
from backend.app.graph.change_set import CHANGE_SET_CREATE_QUERY, TARGET_VISIBILITY_QUERY
from backend.app.graph.database import Neo4jDatabase


class ChangeSetSessionNotFound(LookupError):
    """The chat session is missing, or belongs to another user (indistinguishable)."""


@dataclass(frozen=True)
class ProposeChangeSetCommand:
    id: str
    user_id: str
    series_id: str
    chat_session_id: str
    summary: str
    operations: list[Any]
    visible_until_order_snapshot: int
    created_at: datetime


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


def _to_response(record: dict[str, Any]) -> ChangeSetResponse:
    normalized = _normalize(record)
    operations_json = normalized.pop("operations_json")
    normalized["operations"] = json.loads(operations_json)
    return ChangeSetResponse.model_validate(normalized)


class ChangeSetRepository:
    """Read/write access to the ChangeSet draft resource."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def get_visible_target(
        self, target_id: str, series_id: str, visible_until_order: int
    ) -> dict[str, Any] | None:
        """Return the target's ``{id, origin, node_labels}`` if visible, else ``None``.

        Hidden, cross-series, and genuinely nonexistent targets are all
        indistinguishable — every case yields ``None`` (RAG-03).
        """
        records = await self._database.execute_query(
            TARGET_VISIBILITY_QUERY,
            target_id=target_id,
            series_id=series_id,
            visible_until_order=visible_until_order,
        )
        return records[0] if records else None

    async def propose(self, command: ProposeChangeSetCommand) -> ChangeSetResponse:
        """Persist the draft ChangeSet, or raise ``ChangeSetSessionNotFound``.

        Writes ONLY the ``ChangeSet`` node itself plus its linking
        relationships — no target node/relationship/claim is ever touched
        here (Stage 1 propose has zero graph-target mutation, RAG-11).
        """
        records = await self._database.execute_query(
            CHANGE_SET_CREATE_QUERY,
            id=command.id,
            user_id=command.user_id,
            series_id=command.series_id,
            chat_session_id=command.chat_session_id,
            summary=command.summary,
            operations_json=json.dumps(
                [op.model_dump(mode="json") for op in command.operations]
            ),
            visible_until_order_snapshot=command.visible_until_order_snapshot,
            created_at=command.created_at,
        )
        if not records:
            raise ChangeSetSessionNotFound(
                f"Chat session {command.chat_session_id} not found for this user."
            )
        return _to_response(records[0])
