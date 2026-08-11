"""Persistence for the per-user, per-series watch-progress record (RAG-01).

The MERGE-based upsert is atomic: concurrent updates for the same
(user, series) resolve to one row with no torn/partial state, and setting a
value equal to the current persisted value is an idempotent update (same row,
same resulting value), never an error.

The D-05 split (07-02) persists ``watched_through_order`` and
``view_as_of_order``; ``effective_view_order`` is computed here via the policy
service (D-04 — the min rule lives in exactly one place).  ``ensure_migrated``
is the D-07 lossless, idempotent backfill for pre-split records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from spoilerless.app.domain.progress import UserSeriesProgressResponse
from spoilerless.app.graph.database import Neo4jDatabase, neo4j_row_to_python

# Single row-normalization definition (PROB-09/#68): the driver returns
# ``neo4j.time.DateTime`` for properties stored as Python ``datetime``;
# Pydantic's strict datetime validators reject that type, so rows are
# normalized to ISO-8601 strings at the repository boundary (same pattern
# as repository/user.py).
_normalize = neo4j_row_to_python
from spoilerless.app.graph.progress import (
    PROGRESS_GET_QUERY,
    PROGRESS_MIGRATE_QUERY,
    PROGRESS_UPSERT_QUERY,
)
from spoilerless.app.spoiler.policy import effective_view_order


class ProgressRepository:
    """Read/write access to ``(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)``."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    @staticmethod
    def _build(record: dict[str, Any]) -> UserSeriesProgressResponse:
        """Project a persisted row into the D-21 response shape.

        ``effective_view_order`` is the D-05 min rule, computed via the policy
        service (D-04) — never re-derived inline.
        """
        normalized = _normalize(record)
        normalized["effective_view_order"] = effective_view_order(
            normalized["view_as_of_order"], normalized["watched_through_order"]
        )
        return UserSeriesProgressResponse.model_validate(normalized)

    async def upsert(
        self,
        user_id: str,
        series_id: str,
        *,
        watched_through_order: int,
        view_as_of_order: int,
    ) -> UserSeriesProgressResponse:
        """Create or update the progress record; returns the persisted row."""
        now = datetime.now(timezone.utc)
        records = await self._database.execute_query(
            PROGRESS_UPSERT_QUERY,
            user_id=user_id,
            series_id=series_id,
            id=f"progress:{uuid4()}",
            now=now,
            watched_through_order=watched_through_order,
            view_as_of_order=view_as_of_order,
        )
        return self._build(records[0])

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
        return self._build(records[0])

    async def ensure_migrated(self) -> None:
        """D-07 backfill: seed the split fields from the legacy boundary.

        The WHERE guard (``watched_through_order IS NULL``) makes the
        statement idempotent — re-running it changes nothing — and it only
        touches ``UserSeriesProgress`` records missing the new property;
        nothing is ever deleted or reset.
        """
        await self._database.execute_query(PROGRESS_MIGRATE_QUERY)
