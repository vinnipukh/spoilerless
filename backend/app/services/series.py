from __future__ import annotations

from typing import Any

from backend.app.graph.database import Neo4jDatabase
from backend.app.spoiler.filter import (
    SERIES_LIST_QUERY,
    SERIES_BY_ID_QUERY,
    SERIES_EPISODES_QUERY,
)


class SeriesService:
    """Business logic for series and episode resources."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def list_series(self) -> list[dict[str, Any]]:
        return await self._database.execute_query(SERIES_LIST_QUERY)

    async def get_series(self, series_id: str) -> dict[str, Any] | None:
        records = await self._database.execute_query(
            SERIES_BY_ID_QUERY, series_id=series_id
        )
        return records[0] if records else None

    async def list_episodes(self, series_id: str) -> list[dict[str, Any]]:
        return await self._database.execute_query(
            SERIES_EPISODES_QUERY, series_id=series_id
        )
