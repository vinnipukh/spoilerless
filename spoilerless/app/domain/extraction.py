from __future__ import annotations

import hashlib
import warnings
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spoilerless.app.domain.user_content import Identifier, PlainText, VisibilityOrder
from spoilerless.app.graph.ontology import load_ontology


# Load ontology once at module level for validation
_ONTOLOGY = load_ontology()


ConfidenceLevel = Annotated[
    str,
    Field(description="Confidence level per ontology allowlist.", examples=["high", "medium", "low"]),
]

RelationshipEffect = Annotated[
    str,
    Field(description="Effect this claim has on the subject-object relationship.", examples=["strengthens", "weakens", "neutral"]),
]

ClaimType = Annotated[
    str,
    Field(description="Claim type per ontology allowlist.", examples=["explicit_fact", "observed_event", "inferred_state"]),
]


class EvidencePayload(BaseModel):
    """Contract for a single evidence fragment from a future extractor.

    Part of the source-connector interface (PREP-04). Not a running service —
    this model validates the shape any future connector must produce.
    """

    text: PlainText
    locator: str = Field(description="Exact location within the source (timestamp, page number, scene marker).")
    episode_id: Identifier
    content_hash: str | None = Field(default=None, description="Optional content hash for deduplication.")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "text": "Dexter keeps his blood slides in a hidden box.",
                    "locator": "S01E01:12:34",
                    "episode_id": "episode:dexter:s01e01",
                    "content_hash": "sha256:abc123...",
                }
            ]
        },
    )


class SourcePayload(BaseModel):
    """Contract for a source record from a future extractor.

    Part of the source-connector interface (PREP-04). Defines what a source
    record looks like without implementing any retrieval or parsing.
    """

    source_type: str = Field(description="Type of source — e.g., 'transcript', 'podcast', 'script', 'article'.")
    locator: str = Field(description="Stable locator for the source — URL, DOI, file path, or episode reference.")
    retrieved_at: datetime | None = Field(default=None, description="When the source was retrieved.")
    episode_id: Identifier
    content_hash: str | None = Field(default=None, description="Optional content hash for deduplication.")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "source_type": "transcript",
                    "locator": "https://opensubtitles.org/dexter-s01e01",
                    "retrieved_at": "2026-07-30T10:00:00Z",
                    "episode_id": "episode:dexter:s01e01",
                    "content_hash": "sha256:def456...",
                }
            ]
        },
    )


class ExtractionClaim(BaseModel):
    """One atomic candidate claim as produced by a future LLM-powered extractor.

    This model is the extraction-output JSON schema contract (PREP-01). It
    represents everything a future extractor must output for one claim.

    Not a Neo4j label — ingested ExtractionClaims become Claim nodes with
    origin: 'candidate'.
    """

    schema_version: str = Field(
        default="0.1",
        description="Schema version identifier. Future extractors declare which version they produce.",
        examples=["0.1"],
    )
    subject_id: Identifier
    predicate: str = Field(description="Relationship predicate connecting subject to object.")
    object_id: Identifier
    claim_type: ClaimType
    confidence_level: ConfidenceLevel = Field(default="medium")
    relationship_effect: RelationshipEffect = Field(default="neutral")
    # Server-derived since Phase 11 (D-03): the persisted visible_from_order is
    # computed from the resolved episode/endpoint orders via
    # spoiler/visibility.derive_visible_from_order. A non-None client value is
    # accepted for extractor compatibility but validated: if it disagrees with
    # the server derivation the claim is rejected (422 INVALID_EXTRACTION_PAYLOAD)
    # — the client can never choose visibility.
    visible_from_order: VisibilityOrder | None = None
    valid_from_order: VisibilityOrder | None = Field(default=None)
    valid_until_order: VisibilityOrder | None = Field(default=None)
    evidence_text: PlainText
    evidence_locator: str = Field(description="Exact location within the source for this evidence text.")
    source_type: str = Field(description="Type of source this claim was extracted from.")
    source_locator: str = Field(description="Location of the source this claim was extracted from.")
    episode_id: Identifier

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "schema_version": "0.1",
                    "subject_id": "character:dexter",
                    "predicate": "conceals",
                    "object_id": "object:blood_slides",
                    "claim_type": "observed_event",
                    "confidence_level": "high",
                    "relationship_effect": "strengthens",
                    "visible_from_order": 1,
                    "valid_from_order": 1,
                    "valid_until_order": None,
                    "evidence_text": "Dexter keeps his blood slides carefully organized in a hidden box.",
                    "evidence_locator": "S01E01:12:34",
                    "source_type": "transcript",
                    "source_locator": "https://opensubtitles.org/dexter-s01e01",
                    "episode_id": "episode:dexter:s01e01",
                }
            ]
        },
    )

    @field_validator("claim_type")
    @classmethod
    def validate_claim_type(cls, value: str) -> str:
        _ONTOLOGY.require_claim_type(value)
        return value

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: str) -> str:
        _ONTOLOGY.require_confidence_level(value)
        return value

    @model_validator(mode="after")
    def validate_episode_references(self) -> ExtractionClaim:
        """Validate that episode references are internally consistent.

        The evidence_locator should reference the same episode as episode_id
        for basic sanity checking. This is a structural check, not a DB lookup.
        """
        episode_prefix = self.episode_id.split(":")[-1].upper()
        if not self.evidence_locator.startswith(episode_prefix):
            warnings.warn(
                f"evidence_locator '{self.evidence_locator}' does not start with "
                f"episode prefix '{episode_prefix}' — possible episode mismatch."
            )
        return self

    @property
    def candidate_id(self) -> str:
        """Deterministic candidate ID derived from payload content.

        Format: extracted:{sha256_prefix_of_normalized_content}
        Enables idempotent ingest (D-11).
        """
        normalized = (
            f"{self.subject_id}:{self.predicate}:{self.object_id}:"
            f"{self.evidence_text}:{self.evidence_locator}:{self.episode_id}"
        )
        return f"extracted:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


class ExtractionBatchEnvelope(BaseModel):
    """Envelope for a batch of extraction claims submitted to the ingest API.

    Carries the extractor metadata block (D-13) and a list of extraction claims.
    """

    extractor_name: str = Field(description="Name/identifier of the extractor that produced these claims.")
    extractor_version: str = Field(description="Version of the extractor software.")
    run_timestamp: datetime = Field(description="When this extraction run completed.")
    claims: list[ExtractionClaim] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "extractor_name": "dexter-extractor-v0",
                    "extractor_version": "0.1.0",
                    "run_timestamp": "2026-07-30T10:00:00Z",
                    "claims": [
                        {
                            "schema_version": "0.1",
                            "subject_id": "character:dexter",
                            "predicate": "conceals",
                            "object_id": "object:blood_slides",
                            "claim_type": "observed_event",
                            "confidence_level": "high",
                            "relationship_effect": "strengthens",
                            "visible_from_order": 1,
                            "valid_from_order": 1,
                            "valid_until_order": None,
                            "evidence_text": "Dexter keeps his blood slides carefully organized in a hidden box.",
                            "evidence_locator": "S01E01:12:34",
                            "source_type": "transcript",
                            "source_locator": "https://opensubtitles.org/dexter-s01e01",
                            "episode_id": "episode:dexter:s01e01",
                        }
                    ],
                }
            ]
        },
    )
