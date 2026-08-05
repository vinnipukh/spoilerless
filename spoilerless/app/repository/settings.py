"""Persistence for the single ``:AppSetting {key: 'llm'}`` configuration node.

Follows the neo4j-data-patterns convention: the payload is a JSON string
property (Neo4j cannot store dict values directly), serialized here at the
repository boundary. There is no uniqueness constraint on ``key`` — the
MERGE upsert keeps the node set single-row by construction and is idempotent.
"""

from __future__ import annotations

import json
from typing import Any

from spoilerless.app.domain.settings import SETTINGS_KEY_LLM
from spoilerless.app.graph.database import Neo4jDatabase

SETTINGS_GET_QUERY = "MATCH (s:AppSetting {key: $key}) RETURN s.value AS value"
SETTINGS_UPSERT_QUERY = "MERGE (s:AppSetting {key: $key}) SET s.value = $value"


class SettingsRepository:
    """Read/write access to the ``:AppSetting`` configuration nodes."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def get_llm(self) -> dict[str, Any] | None:
        rows = await self._database.execute_query(SETTINGS_GET_QUERY, key=SETTINGS_KEY_LLM)
        if not rows or not rows[0].get("value"):
            return None
        try:
            parsed = json.loads(rows[0]["value"])
        except (TypeError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    async def set_llm(self, payload: dict[str, Any]) -> None:
        await self._database.execute_query(
            SETTINGS_UPSERT_QUERY,
            key=SETTINGS_KEY_LLM,
            value=json.dumps(payload),
        )
