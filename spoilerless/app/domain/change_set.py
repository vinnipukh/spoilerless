"""ChangeSet domain models — the Stage 1 (Propose) typed operation contract (RAG-11).

Every operation model below is deliberately closed: ``StrictModel``'s
``extra="forbid"`` plus a Pydantic discriminated union (``operation_type``)
means a payload naming an unlisted operation type, or carrying any field
beyond what is explicitly declared, is rejected by Pydantic before any
repository code — let alone Cypher — ever runs (06-PRD-SOURCE.md §9's
"the LLM must not directly execute writes").

No operation model EVER declares ``origin``, ``visible_from_order``, or
``id`` as a settable input field — these stay server-derived always
(06-RESEARCH.md Pitfall 5: don't rely on "just not using" a settable field,
don't declare it at all). ``ChangeSetResponse.visible_until_order_snapshot``
is the ChangeSet-level, server-owned analog of a resource's
``visible_from_order`` — it is likewise never accepted as client input on
any operation model.

Relationship types (``CustomRelationshipType``) and node types
(``CustomNodeType``) are reused unchanged from ``domain/user_content.py`` —
the same closed ontology allowlist already enforced there, not a forked
copy.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import Field, field_validator, model_validator

from spoilerless.app.domain.user_content import (
    CustomNodeType,
    CustomRelationshipType,
    Identifier,
    NoteTargetType,
    PlainText,
    StrictModel,
)

# Only these extra property keys are ever accepted on an operation's
# ``properties`` dict — an arbitrary/unlisted key is rejected by Pydantic
# validation, never silently dropped or passed through to Cypher.
ALLOWED_OPERATION_PROPERTY_KEYS = frozenset({"description"})

Summary = Annotated[
    str,
    Field(min_length=1, max_length=500, description="Human-readable ChangeSet summary."),
]

NodeLabel = Annotated[str, Field(min_length=1, max_length=200)]
Locator = Annotated[str, Field(min_length=1, max_length=200)]

OperationProperties = Annotated[
    dict[str, PlainText] | None,
    Field(default=None, description="Optional allowlisted extra properties."),
]


class ClaimType(StrEnum):
    EXPLICIT_FACT = "explicit_fact"
    OBSERVED_EVENT = "observed_event"
    INFERRED_STATE = "inferred_state"
    EXTERNAL_INTERPRETATION = "external_interpretation"
    USER_AUTHORED = "user_authored"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


def _check_property_keys(value: dict[str, str] | None) -> dict[str, str] | None:
    if value is None:
        return value
    disallowed = set(value) - ALLOWED_OPERATION_PROPERTY_KEYS
    if disallowed:
        raise ValueError(f"Unsupported property keys: {sorted(disallowed)}")
    return value


def _require_at_least_one_change(model: StrictModel, fields: tuple[str, ...]) -> StrictModel:
    if all(getattr(model, field) is None for field in fields):
        raise ValueError(f"At least one of {fields} must be set for an update operation.")
    return model


class CreateNodeOperation(StrictModel):
    operation_type: Literal["create_node"]
    node_type: CustomNodeType = Field(description="Ontology-locked custom node type.")
    label: NodeLabel
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive visibility."
    )
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)


class UpdateNodeOperation(StrictModel):
    operation_type: Literal["update_node"]
    node_id: Identifier
    label: NodeLabel | None = None
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)

    @model_validator(mode="after")
    def _require_change(self) -> "UpdateNodeOperation":
        return _require_at_least_one_change(self, ("label", "properties"))


class DeleteNodeOperation(StrictModel):
    operation_type: Literal["delete_node"]
    node_id: Identifier


class CreateRelationshipOperation(StrictModel):
    operation_type: Literal["create_relationship"]
    source_id: Identifier
    target_id: Identifier
    relationship_type: CustomRelationshipType = Field(
        description="Ontology-locked participation or character predicate."
    )
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive conservative visibility."
    )
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)


class UpdateRelationshipOperation(StrictModel):
    operation_type: Literal["update_relationship"]
    relationship_id: Identifier
    relationship_type: CustomRelationshipType | None = None
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)

    @model_validator(mode="after")
    def _require_change(self) -> "UpdateRelationshipOperation":
        return _require_at_least_one_change(self, ("relationship_type", "properties"))


class DeleteRelationshipOperation(StrictModel):
    operation_type: Literal["delete_relationship"]
    relationship_id: Identifier


class CreateClaimOperation(StrictModel):
    operation_type: Literal["create_claim"]
    subject_id: Identifier
    object_id: Identifier
    predicate: CustomRelationshipType = Field(
        description="Ontology-locked participation or character predicate."
    )
    claim_type: ClaimType
    confidence_level: ConfidenceLevel
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive conservative visibility."
    )
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)


class UpdateClaimOperation(StrictModel):
    operation_type: Literal["update_claim"]
    claim_id: Identifier
    predicate: CustomRelationshipType | None = None
    confidence_level: ConfidenceLevel | None = None
    properties: OperationProperties = None

    _check_properties = field_validator("properties")(_check_property_keys)

    @model_validator(mode="after")
    def _require_change(self) -> "UpdateClaimOperation":
        return _require_at_least_one_change(
            self, ("predicate", "confidence_level", "properties")
        )


class DeleteClaimOperation(StrictModel):
    operation_type: Literal["delete_claim"]
    claim_id: Identifier


class AttachEvidenceOperation(StrictModel):
    operation_type: Literal["attach_evidence"]
    claim_id: Identifier
    source_id: Identifier
    episode_id: Identifier = Field(
        description="Persisted episode used by the server to derive conservative visibility."
    )
    locator: Locator
    text: PlainText


class CreateNoteOperation(StrictModel):
    operation_type: Literal["create_note"]
    target_type: NoteTargetType = Field(description="Exactly one Character or Claim target.")
    target_id: Identifier
    content: PlainText


class UpdateNoteOperation(StrictModel):
    operation_type: Literal["update_note"]
    note_id: Identifier
    content: PlainText


class DeleteNoteOperation(StrictModel):
    operation_type: Literal["delete_note"]
    note_id: Identifier


# The full closed set of 13 operation types this ChangeSet flow ever accepts
# (06-PRD-SOURCE.md §9's "Suggested operation types" list, adapted to the
# existing domain APIs and ontology per that section's instruction). An
# ``operation_type`` outside this set is rejected at the discriminator level
# before any of the individual operation models are even considered.
ChangeSetOperation = Annotated[
    Union[
        CreateNodeOperation,
        UpdateNodeOperation,
        DeleteNodeOperation,
        CreateRelationshipOperation,
        UpdateRelationshipOperation,
        DeleteRelationshipOperation,
        CreateClaimOperation,
        UpdateClaimOperation,
        DeleteClaimOperation,
        AttachEvidenceOperation,
        CreateNoteOperation,
        UpdateNoteOperation,
        DeleteNoteOperation,
    ],
    Field(discriminator="operation_type"),
]

# Direct-mutation operation types the canonical/candidate protection
# invariant applies to (RAG-13) — creation operations are exempt because
# they never mutate an existing origin:canonical/candidate resource.
DIRECT_MUTATION_OPERATION_TYPES = frozenset(
    {
        "update_node",
        "delete_node",
        "update_relationship",
        "delete_relationship",
        "update_claim",
        "delete_claim",
    }
)


class ChangeSetCreateRequest(StrictModel):
    series_id: Identifier
    chat_session_id: Identifier
    summary: Summary
    operations: list[ChangeSetOperation] = Field(min_length=1, max_length=50)


class ChangeSetResponse(StrictModel):
    id: Identifier
    user_id: Identifier
    series_id: Identifier
    chat_session_id: Identifier
    status: Literal[
        "draft", "awaiting_confirmation", "applied", "rejected", "failed", "reverted"
    ]
    visible_until_order_snapshot: int = Field(
        ge=1,
        description="The exact persisted boundary used to validate this ChangeSet's targets.",
    )
    summary: Summary
    operations: list[ChangeSetOperation]
    created_at: datetime
    confirmed_at: datetime | None = None
    applied_at: datetime | None = None
    revision_id: Identifier | None = Field(
        default=None,
        description="The apply-time Revision id — preserved across revert (PROB-27, #51).",
    )
    revert_revision_id: Identifier | None = Field(
        default=None,
        description="The revert-time Revision id, set when the ChangeSet is reverted; "
        "kept alongside revision_id so both links survive (PROB-27, #51).",
    )
    idempotency_key: str | None = None
