"""Tests for extraction schema and source-connector interface models (PREP-01, PREP-04)."""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.domain.extraction import (
    ExtractionClaim,
    ExtractionBatchEnvelope,
    SourcePayload,
    EvidencePayload,
)


def make_claim(
    subject_id: str = "character:dexter",
    predicate: str = "conceals",
    object_id: str = "object:blood_slides",
    evidence_text: str = "Dexter hides his blood slides.",
    **overrides,
) -> dict:
    base = {
        "schema_version": "0.1",
        "subject_id": subject_id,
        "predicate": predicate,
        "object_id": object_id,
        "claim_type": "observed_event",
        "confidence_level": "medium",
        "relationship_effect": "neutral",
        "visible_from_order": 1,
        "valid_from_order": 1,
        "valid_until_order": None,
        "evidence_text": evidence_text,
        "evidence_locator": "S01E01:10:00",
        "source_type": "transcript",
        "source_locator": "https://example.com",
        "episode_id": "episode:dexter:s01e01",
    }
    base.update(overrides)
    return base


class TestExtractionClaim:
    """PREP-01: Extraction claim schema validation."""

    def test_valid_claim(self):
        claim = ExtractionClaim(**make_claim())
        assert claim.schema_version == "0.1"
        assert claim.claim_type == "observed_event"
        assert claim.candidate_id.startswith("extracted:")

    def test_extra_fields_forbidden(self):
        data = make_claim(extra_field="should_not_exist")
        with pytest.raises(ValidationError, match="extra"):
            ExtractionClaim(**data)

    def test_ontology_claim_type_validation(self):
        data = make_claim(claim_type="invalid_claim_type")
        with pytest.raises(ValidationError, match="claim_type"):
            ExtractionClaim(**data)

    def test_ontology_confidence_level_validation(self):
        data = make_claim(confidence_level="extremely_high")
        with pytest.raises(ValidationError, match="confidence"):
            ExtractionClaim(**data)
    def test_ontology_relationship_effect_is_free_text(self):
        """relationship_effect in extraction schema is free text, not validated."""
        claim = ExtractionClaim(**make_claim(relationship_effect="any_value_works"))
        assert claim.relationship_effect == "any_value_works"

    def test_deterministic_candidate_id(self):
        c1 = ExtractionClaim(**make_claim())
        c2 = ExtractionClaim(**make_claim())
        assert c1.candidate_id == c2.candidate_id

    def test_different_payload_different_id(self):
        c1 = ExtractionClaim(**make_claim(evidence_text="First evidence."))
        c2 = ExtractionClaim(**make_claim(evidence_text="Different evidence."))
        assert c1.candidate_id != c2.candidate_id

    def test_confidence_defaults_to_medium(self):
        data = make_claim()
        del data["confidence_level"]
        claim = ExtractionClaim(**data)
        assert claim.confidence_level == "medium"

    def test_schema_version_default(self):
        claim = ExtractionClaim(**make_claim())
        assert claim.schema_version == "0.1"


class TestExtractionBatchEnvelope:
    """Envelope validation tests."""

    def test_valid_batch(self):
        envelope = ExtractionBatchEnvelope(
            extractor_name="test-extractor",
            extractor_version="0.1.0",
            run_timestamp=datetime.now(timezone.utc),
            claims=[ExtractionClaim(**make_claim())],
        )
        assert len(envelope.claims) == 1

    def test_empty_claims_rejected(self):
        with pytest.raises(ValidationError, match="claims"):
            ExtractionBatchEnvelope(
                extractor_name="test-extractor",
                extractor_version="0.1.0",
                run_timestamp=datetime.now(timezone.utc),
                claims=[],
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            ExtractionBatchEnvelope(
                extractor_name="test-extractor",
                extractor_version="0.1.0",
                run_timestamp=datetime.now(timezone.utc),
                claims=[ExtractionClaim(**make_claim())],
                extra_field="nope",
            )


class TestSourcePayload:
    """PREP-04: Source-connector interface — SourcePayload validation."""

    def test_valid_source(self):
        source = SourcePayload(
            source_type="transcript",
            locator="https://example.com",
            retrieved_at=datetime.now(timezone.utc),
            episode_id="episode:dexter:s01e01",
        )
        assert source.source_type == "transcript"

    def test_optional_content_hash(self):
        source = SourcePayload(
            source_type="transcript",
            locator="https://example.com",
            episode_id="episode:dexter:s01e01",
        )
        assert source.content_hash is None

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            SourcePayload(
                source_type="transcript",
                locator="https://example.com",
                episode_id="episode:dexter:s01e01",
                extra="nope",
            )


class TestEvidencePayload:
    """PREP-04: Source-connector interface — EvidencePayload validation."""

    def test_valid_evidence(self):
        evidence = EvidencePayload(
            text="Dexter hides his blood slides.",
            locator="S01E01:10:00",
            episode_id="episode:dexter:s01e01",
        )
        assert evidence.text == "Dexter hides his blood slides."

    def test_optional_content_hash(self):
        evidence = EvidencePayload(
            text="Evidence text.",
            locator="S01E01:10:00",
            episode_id="episode:dexter:s01e01",
        )
        assert evidence.content_hash is None

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError, match="extra"):
            EvidencePayload(
                text="Evidence.",
                locator="S01E01:10:00",
                episode_id="episode:dexter:s01e01",
                extra="nope",
            )


class TestSchemaArtifact:
    """D-05: The JSON Schema artifact is valid and complete."""

    def test_artifact_exists(self):
        with open("docs/extraction-schema.json") as f:
            schema = json.load(f)
        assert "extraction_claim" in schema
        assert "extraction_batch_envelope" in schema
        assert "source_payload" in schema
        assert "evidence_payload" in schema

    def test_extraction_claim_has_required_fields(self):
        with open("docs/extraction-schema.json") as f:
            schema = json.load(f)
        claim_schema = schema["extraction_claim"]
        props = claim_schema["properties"]
        assert "subject_id" in props
        assert "predicate" in props
        assert "object_id" in props
        assert "claim_type" in props
        assert "schema_version" in props
        assert props["schema_version"]["default"] == "0.1"
