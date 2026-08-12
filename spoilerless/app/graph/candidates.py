from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from spoilerless.app.domain.extraction import ExtractionBatchEnvelope, ExtractionClaim
from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.domain.user_content import Origin
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.core.errors import http_error
from spoilerless.app.revisions import RevisionRepository


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
                "code": "INGEST_ERROR",
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

    async def approve_claim(
        self,
        *,
        series_id: str,
        claim_id: str,
        user_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Promote a candidate claim to ``canonical`` inside one transaction.

        PROB-10/#60: the approve business flow (read -> origin guard ->
        status write -> revision log) lives here, not in a route closure.
        Returns the claim id + the revision id actually persisted. Admin
        gating (AUTH-03) stays at the route.
        """
        command = {
            "series_id": series_id,
            "claim_id": claim_id,
            "user_id": user_id,
            "now": now,
        }
        return await self._db.execute_write(_approve_claim_work, command)

    async def reject_claim(
        self,
        *,
        series_id: str,
        claim_id: str,
        user_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Set a candidate claim's status to ``rejected`` inside one transaction."""
        command = {
            "series_id": series_id,
            "claim_id": claim_id,
            "user_id": user_id,
            "now": now,
        }
        return await self._db.execute_write(_reject_claim_work, command)

    async def edit_claim(
        self,
        *,
        series_id: str,
        claim_id: str,
        updates: dict[str, Any],
        user_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        """Apply mutable-field edits to a candidate claim + log a revision."""
        command = {
            "series_id": series_id,
            "claim_id": claim_id,
            "updates": updates,
            "user_id": user_id,
            "now": now,
        }
        return await self._db.execute_write(_edit_claim_work, command)

    async def get_candidate_claim(
        self,
        series_id: str,
        claim_id: str,
        *,
        visible_until_order: int,
    ) -> dict[str, Any] | None:
        """Fetch a single candidate claim by ID, filtered by the spoiler
        boundary (PROB-05/#13): an above-boundary claim reads as missing
        (D-15 — hidden and missing are indistinguishable).
        """
        query = """
        MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
        WHERE claim.visible_from_order <= $visible_until_order
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
        result = await self._db.execute_query(
            query,
            series_id=series_id,
            claim_id=claim_id,
            visible_until_order=visible_until_order,
        )
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


# ── Review-flow transactions (PROB-10/#60) ────────────────────────────────────
# The approve/reject/edit business flows live here as module-level work
# functions (same shape as _ingest_candidate_claims), NOT as route closures —
# the API layer shrinks to try/except + invalidate_series.

_READ_CANDIDATE_CLAIM_QUERY = """
    MATCH (claim:Claim {id: $claim_id, series_id: $series_id})
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
           claim.origin AS origin,
           claim.schema_version AS schema_version,
           claim.created_at AS created_at
"""


async def _read_candidate_claim(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Fetch a candidate claim row or raise 404 if it does not exist."""
    result = await tx.run(
        _READ_CANDIDATE_CLAIM_QUERY,
        claim_id=command["claim_id"],
        series_id=command["series_id"],
    )
    record = await result.single()
    if record is None:
        raise http_error(
            404,
            "CANDIDATE_NOT_FOUND",
            f"Candidate claim not found: {command['claim_id']}",
        )
    return dict(record.data())


async def _log_claim_revision(
    tx: Any,
    command: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Append one Claim revision and return it (persisted uuid id — #34)."""
    return await RevisionRepository.log_revision(
        tx,
        series_id=command["series_id"],
        resource_type="Claim",
        resource_id=command["claim_id"],
        action=RevisionAction.UPDATED,
        before=before,
        after=after,
        visible_from_order=before.get("visible_from_order", 1),
        created_at=command["now"],
        user_id=command["user_id"],
    )


async def _approve_claim_work(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Read -> origin guard -> canonical write -> revision (one transaction)."""
    row = await _read_candidate_claim(tx, command)
    if row["origin"] != "candidate":
        raise http_error(
            409,
            "CANNOT_APPROVE_NON_CANDIDATE",
            f"Claim '{command['claim_id']}' origin is '{row['origin']}', not 'candidate'.",
        )

    before = dict(row)
    after = dict(before)
    after["status"] = "canonical"

    await tx.run(
        """
        MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
        SET claim.status = 'canonical'
        """,
        claim_id=command["claim_id"],
        series_id=command["series_id"],
    )

    revision = await _log_claim_revision(tx, command, before, after)
    # Return the id RevisionRepository.log_revision actually persisted
    # (PROB-12, #34) — never a fabricated hash. GET /revisions/{id} resolves it.
    return {
        "id": command["claim_id"],
        "status": "canonical",
        "origin": "candidate",
        "revision_id": revision["id"],
    }


async def _reject_claim_work(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Read -> status write -> revision (one transaction)."""
    row = await _read_candidate_claim(tx, command)

    before = dict(row)
    after = dict(before)
    after["status"] = "rejected"

    await tx.run(
        """
        MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
        SET claim.status = 'rejected'
        """,
        claim_id=command["claim_id"],
        series_id=command["series_id"],
    )

    revision = await _log_claim_revision(tx, command, before, after)
    return {
        "id": command["claim_id"],
        "status": "rejected",
        "origin": "candidate",
        "revision_id": revision["id"],
    }


async def _edit_claim_work(tx: Any, command: dict[str, Any]) -> dict[str, Any]:
    """Read -> mutable-field SET -> revision (one transaction)."""
    row = await _read_candidate_claim(tx, command)
    before = dict(row)

    set_items = [f"claim.{key} = ${key}" for key in command["updates"]]
    set_expr = ", ".join(set_items)
    await tx.run(
        f"""
        MATCH (claim:Claim {{id: $claim_id, series_id: $series_id, origin: 'candidate'}})
        SET {set_expr}
        RETURN claim.id AS id
        """,
        claim_id=command["claim_id"],
        series_id=command["series_id"],
        **command["updates"],
    )

    after = {**before, **command["updates"]}
    revision = await _log_claim_revision(tx, command, before, after)
    return {
        "id": command["claim_id"],
        "status": "edited",
        "origin": "candidate",
        "revision_id": revision["id"],
        "updates_applied": list(command["updates"].keys()),
    }
