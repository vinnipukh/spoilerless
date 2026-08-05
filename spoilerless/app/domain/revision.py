from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from spoilerless.app.domain.user_content import (
    Identifier,
    UserResponseModel,
    VisibilityOrder,
)


class RevisionAction(StrEnum):
    CREATED = "Created"
    UPDATED = "Updated"
    DELETED = "Deleted"
    REVERTED = "Reverted"


class RevisionResponse(UserResponseModel):
    id: Identifier
    series_id: Identifier
    resource_type: str = Field(description="Neo4j node label — UserNote, Character, Event, etc.")
    resource_id: Identifier
    action: RevisionAction
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    user_id: Identifier | None = Field(
        default=None,
        description="Acting user who performed the logged mutation (PROB-33, #33). "
        "Null for revisions logged before actor attribution.",
    )
    created_at: datetime
    visible_from_order: VisibilityOrder

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "revision:2a1f4c7e",
                    "series_id": "series:dexter",
                    "resource_type": "UserNote",
                    "resource_id": "user-note:2a1f4c7e",
                    "action": "Created",
                    "before": None,
                    "after": {
                        "id": "user-note:2a1f4c7e",
                        "target_type": "Character",
                        "target_id": "character:dexter",
                        "content": "Remember this detail.",
                        "visible_from_order": 1,
                        "origin": "user",
                    },
                    "created_at": "2026-07-29T10:00:00Z",
                    "visible_from_order": 1,
                }
            ]
        },
    )

    @field_validator("before", "after", mode="before")
    @classmethod
    def parse_json_field(cls, value: Any) -> Any:
        """Parse JSON string from Neo4j into a dict."""
        if value is None:
            return None
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> Any:
        """Convert Neo4j DateTime to Python datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        # Handle neo4j.time.DateTime
        s = str(value)
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return value
