from __future__ import annotations

from typing import Any

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.spoiler.filter import (
    SERIES_LIST_QUERY,
    SERIES_BY_ID_QUERY,
    SERIES_EPISODES_QUERY,
)
from spoilerless.app.spoiler.policy import mask_episode_metadata


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

    async def list_episodes(
        self, series_id: str, effective_view_order: int | None = None
    ) -> list[dict[str, Any]]:
        """List the series' episodes, masking spoiler-sensitive metadata.

        Masking is done HERE in the service — never in the UI (D-08). When
        ``effective_view_order`` is provided, every episode is run through
        ``policy.mask_episode_metadata`` so the returned dict carries the
        D-21 display shape (``id``, ``code``, ``display_title``,
        ``is_unlocked``, ``is_current_view``) and the legacy ``title`` is set
        to the masked display title (never the future title). No synopsis,
        runtime, or image is ever synthesized (META-02 — absent fields stay
        absent). Without a boundary the raw records are returned unchanged
        (backward compatibility for anonymous callers).
        """
        records = await self._database.execute_query(
            SERIES_EPISODES_QUERY, series_id=series_id
        )
        if effective_view_order is None:
            return records

        masked: list[dict[str, Any]] = []
        for episode in records:
            shape = mask_episode_metadata(episode, effective_view_order)
            merged = dict(episode)
            merged.update(shape)
            merged["title"] = shape["display_title"]
            masked.append(merged)
        return masked
