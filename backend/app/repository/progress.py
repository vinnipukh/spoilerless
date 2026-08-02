"""Persistence for the per-user, per-series watch-progress record (RAG-01).

The MERGE-based upsert is atomic: concurrent updates for the same
(user, series) resolve to one row with no torn/partial state, and setting a
value equal to the current persisted value is an idempotent update (same row,
same resulting value), never an error.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.domain.progress import UserSeriesProgressResponse
from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.progress import PROGRESS_GET_QUERY, PROGRESS_UPSERT_QUERY


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Convert Neo4j temporal types to Pydantic-compatible values.

    The Neo4j Python driver returns ``neo4j.time.DateTime`` for properties
    stored as Python ``datetime`` values; Pydantic's strict datetime
    validators reject that type, so we normalise to ISO-8601 strings here at
    the repository boundary (same pattern as ``repository/user.py``).
    """
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


class ProgressRepository:
    """Read/write access to ``(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)``."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def upsert(
        self, user_id: str, series_id: str, visible_until_order: int
    ) -> UserSeriesProgressResponse:
        """Create or update the progress record; returns the persisted row."""
        now = datetime.now(timezone.utc)
        records = await self._database.execute_query(
            PROGRESS_UPSERT_QUERY,
            user_id=user_id,
            series_id=series_id,
            id=f"progress:{uuid4()}",
            now=now,
            visible_until_order=visible_until_order,
        )
        return UserSeriesProgressResponse.model_validate(_normalize(records[0]))

    async def get(
        self, user_id: str, series_id: str
    ) -> UserSeriesProgressResponse | None:
        """Return the persisted row, or ``None`` when the user has no record."""
        records = await self._database.execute_query(
            PROGRESS_GET_QUERY,
            user_id=user_id,
            series_id=series_id,
        )
        if not records:
            return None
        return UserSeriesProgressResponse.model_validate(_normalize(records[0]))
