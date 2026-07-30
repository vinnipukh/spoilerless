from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, model_validator

from backend.app.core.errors import error_responses, http_error
from backend.app.domain.extraction import ExtractionBatchEnvelope
from backend.app.domain.revision import RevisionAction
from backend.app.domain.user_content import Identifier
from backend.app.graph.candidates import CandidateRepository
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.revisions import RevisionRepository

router = APIRouter(prefix="/api/series/{series_id}/candidates", tags=["candidates"])


async def get_candidate_repo(db: Neo4jDatabase = Depends(get_database)) -> CandidateRepository:
    return CandidateRepository(db)


CandidateRepoDependency = Annotated[CandidateRepository, Depends(get_candidate_repo)]
SeriesId = Annotated[Identifier, Path(description="Series identifier.")]
ClaimId = Annotated[Identifier, Path(description="Candidate claim identifier.", examples=["extracted:a1b2c3d4e5f6g7h8"])]


# --- Shared helpers ---


def _read_claim_query() -> str:
    return """
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


class EditCandidateRequest(BaseModel):
    """Fields that can be edited on a candidate claim."""
    model_config = ConfigDict(extra="forbid")
    label: str | None = None
    predicate: str | None = None
    claim_type: str | None = None
    confidence_level: str | None = None
    relationship_effect: str | None = None
    valid_from_order: int | None = None
    valid_until_order: int | None = None
    evidence_text: str | None = None
    evidence_locator: str | None = None
    source_type: str | None = None
    source_locator: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> EditCandidateRequest:
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for edit.")
        return self


# --- Ingest, List, Get ---


@router.post(
    "/ingest",
    response_model=dict,
    summary="Ingest a batch of extraction claims as candidate claims",
    responses={
        200: {
            "description": "Batch ingested — some claims may have errors.",
            "content": {
                "application/json": {
                    "example": {
                        "created": ["extracted:a1b2c3d4e5f6g7h8", "extracted:i9j0k1l2m3n4o5p6"],
                        "errors": [],
                    }
                }
            },
        },
        422: {
            "description": "Invalid extraction payload.",
            "content": {
                "application/json": {
                    "example": {"detail": {"code": "invalid_extraction_payload", "message": "Validation failed at index 2: claim_type 'unknown' not in ontology"}}
                }
            },
        },
    },
)
async def ingest_candidates(
    series_id: SeriesId,
    envelope: ExtractionBatchEnvelope,
    repo: CandidateRepoDependency,
) -> dict:
    """Ingest a batch of candidate claims from a future extractor."""
    try:
        result = await repo.ingest_batch(series_id, envelope)
        return result
    except Exception as exc:
        raise http_error(
            status_code=422,
            code="invalid_extraction_payload",
            message=f"Batch validation error: {exc}",
        )


@router.get(
    "",
    response_model=list[dict],
    summary="List all candidate claims for a series",
    responses={
        200: {"description": "List of candidate claims with evidence and source details."},
    },
)
async def list_candidates(
    series_id: SeriesId,
    repo: CandidateRepoDependency,
    visible_until_order: int | None = Query(default=None, ge=1, description="Spoiler boundary for filtering."),
) -> list[dict]:
    """List all candidate claims for a series, optionally filtered by spoiler boundary."""
    return await repo.list_candidate_claims(series_id, visible_until_order)


@router.get(
    "/{claim_id}",
    response_model=dict | None,
    summary="Get a single candidate claim by ID",
    responses={
        200: {"description": "Candidate claim details with evidence and source."},
        404: {"description": "Candidate claim not found."},
    },
)
async def get_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    repo: CandidateRepoDependency,
) -> dict | None:
    """Get a single candidate claim by ID."""
    claim = await repo.get_candidate_claim(series_id, claim_id)
    if claim is None:
        raise http_error(404, "candidate_not_found", f"Candidate claim not found: {claim_id}")
    return claim


# --- Approve ---


@router.post(
    "/{claim_id}/approve",
    response_model=dict,
    summary="Approve a candidate claim (promote to canonical)",
    responses={
        200: {"description": "Candidate approved and promoted to canonical."},
        404: {"description": "Candidate claim not found."},
        409: {"description": "Claim is not a candidate (cannot approve)."},
    },
)
async def approve_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    repo: CandidateRepoDependency,
) -> dict:
    """Approve a candidate claim, promoting it from 'candidate' to 'canonical' status."""
    db = repo._db

    async def _approve(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "candidate_not_found", f"Candidate claim not found: {cmd['claim_id']}")
        row = dict(record.data())
        if row["origin"] != "candidate":
            raise http_error(409, "cannot_approve_non_candidate", f"Claim '{cmd['claim_id']}' origin is '{row['origin']}', not 'candidate'.")

        before = dict(row)
        after = dict(before)
        after["status"] = "canonical"

        await tx.run("""
            MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
            SET claim.status = 'canonical'
        """, claim_id=cmd["claim_id"], series_id=cmd["series_id"])

        now = cmd["now"]
        cid = cmd["claim_id"]
        rev_id = f"revision:{hashlib.sha256(f'approve:{cid}:{now.isoformat()}'.encode()).hexdigest()[:12]}"
        await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1), created_at=now)
        return {"id": cmd["claim_id"], "status": "canonical", "origin": "candidate", "revision_id": rev_id}

    try:
        return await db.execute_write(_approve, {"series_id": series_id, "claim_id": claim_id, "now": datetime.now(timezone.utc)})
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(422, "invalid_extraction_payload", f"Approve error: {exc}")


# --- Reject ---


@router.post(
    "/{claim_id}/reject",
    response_model=dict,
    summary="Reject a candidate claim",
    responses={200: {"description": "Candidate rejected."}, 404: {"description": "Candidate claim not found."}},
)
async def reject_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    repo: CandidateRepoDependency,
) -> dict:
    """Reject a candidate claim, setting its status to 'rejected'."""
    db = repo._db

    async def _reject(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "candidate_not_found", f"Candidate claim not found: {cmd['claim_id']}")

        row = dict(record.data())
        before = dict(row)
        after = dict(before)
        after["status"] = "rejected"

        await tx.run("""
            MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
            SET claim.status = 'rejected'
        """, claim_id=cmd["claim_id"], series_id=cmd["series_id"])

        now = cmd["now"]
        cid = cmd["claim_id"]
        rev_id = f"revision:{hashlib.sha256(f'reject:{cid}:{now.isoformat()}'.encode()).hexdigest()[:12]}"
        await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1), created_at=now)
        return {"id": cmd["claim_id"], "status": "rejected", "origin": "candidate", "revision_id": rev_id}

    try:
        return await db.execute_write(_reject, {"series_id": series_id, "claim_id": claim_id, "now": datetime.now(timezone.utc)})
    except HTTPException:
        raise
    except Exception as exc:
        raise http_error(422, "invalid_extraction_payload", f"Reject error: {exc}")


# --- Edit ---


@router.patch(
    "/{claim_id}",
    response_model=dict,
    summary="Edit a candidate claim's mutable fields",
    responses={200: {"description": "Candidate updated."}, 404: {"description": "Candidate claim not found."}},
)
async def edit_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    body: EditCandidateRequest,
    repo: CandidateRepoDependency,
) -> dict:
    """Edit a candidate claim's mutable fields. Creates a revision with before/after snapshots."""
    db = repo._db
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    async def _edit(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "candidate_not_found", f"Candidate claim not found: {cmd['claim_id']}")

        row = dict(record.data())
        before = dict(row)

        set_items = [f"claim.{k} = ${k}" for k in cmd["updates"]]
        set_expr = ", ".join(set_items)
        update_query = f"""
            MATCH (claim:Claim {{id: $claim_id, series_id: $series_id, origin: 'candidate'}})
            SET {set_expr}
            RETURN claim.id AS id
        """
        params = {"claim_id": cmd["claim_id"], "series_id": cmd["series_id"], **cmd["updates"]}
        await tx.run(update_query, **params)

        now = cmd["now"]
        cid = cmd["claim_id"]
        rev_id = f"revision:{hashlib.sha256(f'edit:{cid}:{now.isoformat()}'.encode()).hexdigest()[:12]}"
        after = {**before, **cmd["updates"]}
        await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1), created_at=now)
        return {"id": cmd["claim_id"], "status": "edited", "origin": "candidate", "revision_id": rev_id, "updates_applied": list(cmd["updates"].keys())}

    try:
        return await db.execute_write(_edit, {"series_id": series_id, "claim_id": claim_id, "updates": updates, "now": datetime.now(timezone.utc)})
    except HTTPException:
        raise
    except ValueError as exc:
        raise http_error(422, "invalid_extraction_payload", str(exc))
    except Exception as exc:
        raise http_error(422, "invalid_extraction_payload", f"Edit error: {exc}")
