from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from backend.app.domain.revision import RevisionAction

REVISION_CREATE_QUERY = """
CREATE (revision:Revision {
  id: $id,
  series_id: $series_id,
  resource_type: $resource_type,
  resource_id: $resource_id,
  action: $action,
  before: $before_json,
  after: $after_json,
  visible_from_order: $visible_from_order,
  created_at: $created_at
})
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.created_at AS created_at
"""


class RevisionRepository:
    """Append-only revision log for user-content mutations.

    Every public method is a static method designed to be called inside
    a managed Neo4j transaction callback (``execute_write``).
    """

    @staticmethod
    def _to_json(value: dict[str, Any] | None) -> str | None:
        """Serialize a dict to JSON string for Neo4j storage."""
        if value is None:
            return None
        # Convert datetime to ISO string for JSON-safe storage
        cleaned = {}
        for k, v in value.items():
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = v
        return json.dumps(cleaned, ensure_ascii=False, default=str)

    @staticmethod
    def _from_json(value: Any) -> dict[str, Any] | None:
        """Deserialize a JSON string back to a dict."""
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        # Already a dict (from older/alternative path)
        if isinstance(value, dict):
            return value
        return None

    @staticmethod
    async def log_revision(
        tx: Any,
        *,
        series_id: str,
        resource_type: str,
        resource_id: str,
        action: RevisionAction,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        visible_from_order: int,
        created_at: datetime,
    ) -> dict[str, Any]:
        result = await tx.run(
            REVISION_CREATE_QUERY,
            id=f"revision:{uuid4()}",
            series_id=series_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action.value,
            before_json=RevisionRepository._to_json(before),
            after_json=RevisionRepository._to_json(after),
            visible_from_order=visible_from_order,
            created_at=created_at,
        )
        record = await result.single()
        assert record is not None, "Revision creation must succeed on existing resource"
        return dict(record.data())

    @staticmethod
    def take_snapshot(row: dict[str, Any]) -> dict[str, Any]:
        """Create a clean, ordered snapshot dict from a Neo4j result row.

        Includes only the fields meaningful for reconstructing what the
        resource looked like at the time of the revision.
        """
        keys = [
            "id",
            "series_id",
            "type",
            "label",
            "content",
            "target_type",
            "target_id",
            "source",
            "target",
            "predicate",
            "visible_from_order",
            "origin",
            "episode_id",
            "subject_id",
            "object_id",
            "created_at",
            "updated_at",
        ]
        return {k: row[k] for k in keys if k in row and row[k] is not None}
