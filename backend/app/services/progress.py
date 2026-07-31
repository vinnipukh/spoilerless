"""Watch-progress service — resolves the spoiler boundary server-side (RAG-01).

``resolve`` raises ``ProgressNotFoundError`` when no persisted record exists;
callers must fail closed (empty/fail-closed GraphRAG results) rather than
silently defaulting to a nonzero boundary.
"""

from __future__ import annotations

from backend.app.domain.progress import UserSeriesProgressResponse
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.progress import ProgressRepository


class ProgressNotFoundError(LookupError):
    """No persisted watch-progress record exists for (user, series).

    Callers must fail closed — never leak whether the series exists or
    silently default to a boundary.
    """


class ProgressService:
    """Thin orchestration over :class:`ProgressRepository`."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._repository = ProgressRepository(database)

    async def get(
        self, user_id: str, series_id: str
    ) -> UserSeriesProgressResponse | None:
        return await self._repository.get(user_id, series_id)

    async def upsert(
        self, user_id: str, series_id: str, visible_until_order: int
    ) -> UserSeriesProgressResponse:
        return await self._repository.upsert(user_id, series_id, visible_until_order)

    async def resolve(self, user_id: str, series_id: str) -> int:
        """Resolve the persisted boundary; raises ``ProgressNotFoundError``."""
        record = await self._repository.get(user_id, series_id)
        if record is None:
            raise ProgressNotFoundError(
                f"No watch progress for user {user_id} on series {series_id}."
            )
        return record.visible_until_order
