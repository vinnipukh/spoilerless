from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from neo4j import ManagedTransaction

from backend.app.domain.extraction import ExtractionBatchEnvelope, ExtractionClaim
from backend.app.domain.user_content import Origin
from backend.app.graph.database import Neo4jDatabase
from backend.app.core.errors import http_error


def _derive_candidate_id(claim: ExtractionClaim) -> str:
    """Derive deterministic candidate ID from payload content (D-11)."""
    normalized = (
        f"{claim.subject_id}:{claim.predicate}:{claim.object_id}:"
        f"{claim.evidence_text}:{claim.evidence_locator}:{claim.episode_id}"
    )
    return f"extracted:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


def _derive_source_id(claim: ExtractionClaim) -> str:
    """Derive deterministic source ID from source locator."""
    return f"extracted:source:{hashlib.sha256(claim.source_locator.encode()).hexdigest()[:16]}"


def _derive_evidence_id(claim: ExtractionClaim) -> str:
    """Derive deterministic evidence ID from evidence text + locator."""
    raw = f"{claim.evidence_text}:{claim.evidence_locator}:{claim.episode_id}"
    return f"extracted:evidence:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


INGEST_CANDIDATE_QUERY = """
// Create or update the Source node
MERGE (source:Source {id: $source_id, series_id: $series_id})
ON CREATE SET
  source.source_type = $source_type,
  source.locator = $source_locator,
  source.visible_from_order = $visible_from_order,
  source.origin = 'candidate',
  source.created_at = $now
ON MATCH SET
  source.source_type = $source_type,
  source.locator = $source_locator

// Create or update the EvidenceFragment node
MERGE (evidence:EvidenceFragment {id: $evidence_id, series_id: $series_id})
ON CREATE SET
  evidence.text = $evidence_text,
  evidence.locator = $evidence_locator,
  evidence.visible_from_order = $visible_from_order,
  evidence.origin = 'candidate',
  evidence.created_at = $now
ON MATCH SET
  evidence.text = $evidence_text,
  evidence.locator = $evidence_locator

// Create the EvidenceFragment -> Source relationship
MERGE (evidence)-[:REFERS_TO {
  id: $evidence_id + ':refers_to',
  series_id: $series_id,
  visible_from_order: $visible_from_order,
  origin: 'candidate'
}]->(source)

// Create or upsert the Claim node
MERGE (claim:Claim {id: $claim_id, series_id: $series_id})
ON CREATE SET
  claim.label = $predicate,
  claim.subject_id = $subject_id,
  claim.predicate = $predicate,
  claim.object_id = $object_id,
  claim.claim_type = $claim_type,
  claim.status = 'candidate',
  claim.confidence_level = $confidence_level,
  claim.relationship_effect = $relationship_effect,
  claim.visible_from_order = $visible_from_order,
  claim.valid_from_order = $valid_from_order,
  claim.valid_until_order = $valid_until_order,
  claim.origin = 'candidate',
  claim.schema_version = $schema_version,
  claim.created_at = $now
ON MATCH SET
  claim.confidence_level = $confidence_level,
  claim.relationship_effect = $relationship_effect,
  claim.valid_from_order = $valid_from_order,
  claim.valid_until_order = $valid_until_order

// Link claim to evidence
MERGE (claim)-[:SUPPORTED_BY {
  id: $claim_id + ':supported_by',
  series_id: $series_id,
  visible_from_order: $visible_from_order,
  origin: 'candidate'
}]->(evidence)
"""


async def _ingest_candidate_claims(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
    """Ingest a batch of extraction claims within a single transaction (D-12).

    Returns dict with 'created' (list of claim IDs) and 'errors' (list of errors).
    """
    now = datetime.now(timezone.utc).isoformat()
    created_ids: list[str] = []
    errors: list[dict[str, Any]] = []
    claims: list[ExtractionClaim] = cmd["claims"]
    series_id: str = cmd["series_id"]

    for i, claim in enumerate(claims):
        try:
            claim_id = _derive_candidate_id(claim)
            source_id = _derive_source_id(claim)
            evidence_id = _derive_evidence_id(claim)

            valid_from = claim.valid_from_order
            valid_until = claim.valid_until_order

            parameters = {
                "series_id": series_id,
                "claim_id": claim_id,
                "source_id": source_id,
                "evidence_id": evidence_id,
                "subject_id": claim.subject_id,
                "predicate": claim.predicate,
                "object_id": claim.object_id,
                "claim_type": claim.claim_type,
                "confidence_level": claim.confidence_level,
                "relationship_effect": claim.relationship_effect,
                "visible_from_order": claim.visible_from_order,
                "valid_from_order": valid_from,
                "valid_until_order": valid_until,
                "evidence_text": claim.evidence_text,
                "evidence_locator": claim.evidence_locator,
                "source_type": claim.source_type,
                "source_locator": claim.source_locator,
                "schema_version": claim.schema_version,
                "now": now,
            }

            await tx.run(INGEST_CANDIDATE_QUERY, parameters)
            created_ids.append(claim_id)

        except Exception as exc:
            errors.append({
                "index": i,
                "claim_id": claim.candidate_id,
                "code": "ingest_error",
                "message": str(exc),
            })

    return {"created": created_ids, "errors": errors}


class CandidateRepository:
    """Persistence layer for candidate claims (origin: 'candidate')."""

    def __init__(self, db: Neo4jDatabase | None = None) -> None:
        self._db = db or Neo4jDatabase()

    async def ingest_batch(
        self,
        series_id: str,
        envelope: ExtractionBatchEnvelope,
    ) -> dict[str, Any]:
        """Ingest a batch of candidate claims atomically (D-12).

        Returns dict with 'created' (list[str]) and 'errors' (list[dict]).
        """
        command = {
            "series_id": series_id,
            "claims": envelope.claims,
            "extractor_name": envelope.extractor_name,
            "extractor_version": envelope.extractor_version,
            "run_timestamp": envelope.run_timestamp,
        }
        result = await self._db.execute_write(_ingest_candidate_claims, command)
        return result

    async def get_candidate_claim(self, series_id: str, claim_id: str) -> dict[str, Any] | None:
        """Fetch a single candidate claim by ID."""
        query = """
        MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
        OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:EvidenceFragment)
        OPTIONAL MATCH (evidence)-[:REFERS_TO]->(source:Source)
        RETURN claim.id AS id,
               claim.label AS label,
               claim.subject_id AS subject_id,
               claim.predicate AS predicate,
               claim.object_id AS object_id,
               claim.claim_type AS claim_type,
               claim.status AS status,
               claim.confidence_level AS confidence_level,
               claim.relationship_effect AS relationship_effect,
               claim.visible_from_order AS visible_from_order,
               claim.valid_from_order AS valid_from_order,
               claim.valid_until_order AS valid_until_order,
               claim.schema_version AS schema_version,
               claim.created_at AS created_at,
               collect(DISTINCT {
                   id: evidence.id,
                   text: evidence.text,
                   locator: evidence.locator,
                   visible_from_order: evidence.visible_from_order
               }) AS evidence_fragments,
               collect(DISTINCT {
                   id: source.id,
                   source_type: source.source_type,
                   locator: source.locator,
                   visible_from_order: source.visible_from_order
               }) AS sources
        """
        result = await self._db.execute_query(query, series_id=series_id, claim_id=claim_id)
        return result[0] if result else None

    async def list_candidate_claims(
        self,
        series_id: str,
        visible_until_order: int | None = None,
    ) -> list[dict[str, Any]]:
        """List all candidate claims for a series, optionally filtered by spoiler boundary."""
        where_clause = "WHERE claim.origin = 'candidate'"
        params: dict[str, Any] = {"series_id": series_id}

        if visible_until_order is not None:
            where_clause += " AND claim.visible_from_order <= $visible_until_order"
            params["visible_until_order"] = visible_until_order

        query = f"""
        MATCH (claim:Claim {{series_id: $series_id}})
        {where_clause}
        OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:EvidenceFragment)
        OPTIONAL MATCH (evidence)-[:REFERS_TO]->(source:Source)
        RETURN claim.id AS id,
               claim.label AS label,
               claim.subject_id AS subject_id,
               claim.predicate AS predicate,
               claim.object_id AS object_id,
               claim.claim_type AS claim_type,
               claim.status AS status,
               claim.confidence_level AS confidence_level,
               claim.relationship_effect AS relationship_effect,
               claim.visible_from_order AS visible_from_order,
               claim.valid_from_order AS valid_from_order,
               claim.valid_until_order AS valid_until_order,
               claim.schema_version AS schema_version,
               claim.created_at AS created_at,
               collect(DISTINCT {{
                   id: evidence.id,
                   text: evidence.text,
                   locator: evidence.locator
               }}) AS evidence_fragments,
               collect(DISTINCT {{
                   id: source.id,
                   source_type: source.source_type,
                   locator: source.locator
               }}) AS sources
        ORDER BY claim.created_at DESC
        """
        result = await self._db.execute_query(query, **params)
        return list(result)
