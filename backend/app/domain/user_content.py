from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Identifier = Annotated[
    str,
    Field(
        min_length=1,
        max_length=255,
        description="Stable public identifier.",
        examples=["character:dexter"],
    ),
]
VisibleUntilOrder = Annotated[
    int,
    Field(
        gt=0,
        description="Persisted positive episode order used as a spoiler boundary.",
        examples=[1],
    ),
]
VisibilityOrder = Annotated[
    int,
    Field(
        ge=1,
        description="Earliest persisted episode order at which this resource is visible.",
        examples=[1],
    ),
]
PlainText = Annotated[
    str,
    Field(
        min_length=1,
        max_length=4000,
        description="Non-empty plain text; rich text and markup payloads are not supported.",
        examples=["Dexter keeps his blood slides hidden."],
    ),
]
Label = Annotated[
    str,
    Field(min_length=1, max_length=200, description="Display label.", examples=["Blood slide"]),
]


class Origin(StrEnum):
    CANONICAL = "canonical"
    CANDIDATE = "candidate"
    USER = "user"


class NoteTargetType(StrEnum):
    CHARACTER = "Character"
    CLAIM = "Claim"


class CustomNodeType(StrEnum):
    CHARACTER = "Character"
    EVENT = "Event"
    LOCATION = "Location"
    ORGANIZATION = "Organization"
    OBJECT = "Object"


class CustomRelationshipType(StrEnum):
    PARTICIPATED_IN = "PARTICIPATED_IN"
    WITNESSED = "WITNESSED"
    CAUSED = "CAUSED"
    AFFECTED = "AFFECTED"
    TARGETED = "TARGETED"
    MENTIONED = "MENTIONED"
    KNOWS = "KNOWS"
    FAMILY_OF = "FAMILY_OF"
    WORKS_WITH = "WORKS_WITH"
    TRUSTS = "TRUSTS"
    DISTRUSTS = "DISTRUSTS"
    HELPS = "HELPS"
    OPPOSES = "OPPOSES"
    THREATENS = "THREATENS"
    ATTACKS = "ATTACKS"
    KILLS = "KILLS"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserResponseModel(StrictModel):
    @field_validator("created_at", "updated_at", check_fields=False)
    @classmethod
    def require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a UTC offset")
        return value.astimezone(timezone.utc)


class NoteCreate(StrictModel):
    target_type: NoteTargetType = Field(description="Exactly one Character or Claim target.")
    target_id: Identifier
    content: PlainText

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "target_type": "Character",
                    "target_id": "character:dexter",
                    "content": "Remember this detail.",
                }
            ]
        },
    )


class NoteUpdate(StrictModel):
    content: PlainText

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"content": "Updated plain-text note."}]},
    )


class NoteResponse(UserResponseModel):
    id: Identifier
    series_id: Identifier
    target_type: NoteTargetType
    target_id: Identifier
    content: PlainText
    origin: Literal[Origin.USER] = Origin.USER
    visible_from_order: VisibilityOrder
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "user-note:2a1f4c7e",
                    "series_id": "series:dexter",
                    "target_type": "Character",
                    "target_id": "character:dexter",
                    "content": "Remember this detail.",
                    "origin": "user",
                    "visible_from_order": 1,
                    "created_at": "2026-07-29T10:00:00Z",
                    "updated_at": "2026-07-29T10:00:00Z",
                }
            ]
        },
    )


class CustomNodeCreate(StrictModel):
    node_type: CustomNodeType = Field(description="Ontology-locked custom node type.")
    label: Label
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive visibility."
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"node_type": "Object", "label": "Blood slide", "episode_id": "dexter:s01e01"}
            ]
        },
    )


class CustomNodeUpdate(StrictModel):
    label: Label

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"label": "Updated display label"}]},
    )


class CustomNodeResponse(UserResponseModel):
    id: Identifier
    series_id: Identifier
    type: CustomNodeType
    label: Label
    visible_from_order: VisibilityOrder
    origin: Literal[Origin.USER] = Origin.USER
    episode_id: Identifier
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "user-node:2a1f4c7e",
                    "series_id": "series:dexter",
                    "type": "Object",
                    "label": "Blood slide",
                    "visible_from_order": 1,
                    "origin": "user",
                    "episode_id": "dexter:s01e01",
                    "created_at": "2026-07-29T10:00:00Z",
                    "updated_at": "2026-07-29T10:00:00Z",
                }
            ]
        },
    )


class CustomRelationshipCreate(StrictModel):
    source_id: Identifier
    target_id: Identifier
    predicate: CustomRelationshipType = Field(
        description="Ontology-locked participation or character predicate."
    )
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive conservative visibility."
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "source_id": "character:dexter",
                    "target_id": "character:debra",
                    "predicate": "FAMILY_OF",
                    "episode_id": "dexter:s01e01",
                }
            ]
        },
    )


class CustomRelationshipUpdate(StrictModel):
    predicate: CustomRelationshipType

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"predicate": "TRUSTS"}]},
    )


class CustomRelationshipResponse(UserResponseModel):
    id: Identifier
    series_id: Identifier
    source: Identifier
    target: Identifier
    type: CustomRelationshipType
    visible_from_order: VisibilityOrder
    origin: Literal[Origin.USER] = Origin.USER
    episode_id: Identifier
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "user-rel:2a1f4c7e",
                    "series_id": "series:dexter",
                    "source": "character:dexter",
                    "target": "character:debra",
                    "type": "FAMILY_OF",
                    "visible_from_order": 1,
                    "origin": "user",
                    "episode_id": "dexter:s01e01",
                    "created_at": "2026-07-29T10:00:00Z",
                    "updated_at": "2026-07-29T10:00:00Z",
                }
            ]
        },
    )
