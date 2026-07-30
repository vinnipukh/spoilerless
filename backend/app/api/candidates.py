from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.app.core.errors import error_responses, http_error
from backend.app.domain.extraction import ExtractionBatchEnvelope
from backend.app.domain.user_content import Identifier
from backend.app.graph.candidates import CandidateRepository

router = APIRouter(prefix="/api/series/{series_id}/candidates", tags=["candidates"])


def get_candidate_repo() -> CandidateRepository:
    return CandidateRepository()


CandidateRepoDependency = Annotated[CandidateRepository, Depends(get_candidate_repo)]
SeriesId = Annotated[Identifier, Path(description="Series identifier.")]
ClaimId = Annotated[Identifier, Path(description="Candidate claim identifier.", examples=["extracted:a1b2c3d4e5f6g7h8"])]


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
    """Ingest a batch of candidate claims from a future extractor.

    Each claim is validated against the extraction schema and ontology before
    storage. Claims with deterministic duplicate IDs are upserted (idempotent).

    Returns the list of created claim IDs and any per-item validation errors.
    The batch partially succeeds — individual claim errors don't fail the whole batch.
    """
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
        200: {
            "description": "List of candidate claims with evidence and source details.",
        },
    },
)
async def list_candidates(
    series_id: SeriesId,
    repo: CandidateRepoDependency,
    visible_until_order: int | None = Query(default=None, ge=1, description="Spoiler boundary for filtering."),
) -> list[dict]:
    """List all candidate claims for a series.

    Optionally filtered by visible_until_order spoiler boundary.
    Returns candidate claims with their linked sources and evidence fragments.
    """
    return await repo.list_candidate_claims(series_id, visible_until_order)


@router.get(
    "/{claim_id}",
    response_model=dict | None,
    summary="Get a single candidate claim by ID",
    responses={
        200: {
            "description": "Candidate claim with full details.",
        },
        404: {
            "description": "Candidate not found.",
            "content": {
                "application/json": {
                    "example": {"detail": {"code": "candidate_not_found", "message": "Candidate claim not found: extracted:a1b2c3d4"}}
                }
            },
        },
    },
)
async def get_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    repo: CandidateRepoDependency,
) -> dict:
    """Get a single candidate claim with full details including sources and evidence."""
    claim = await repo.get_candidate_claim(series_id, claim_id)
    if claim is None:
        raise http_error(
            status_code=404,
            code="candidate_not_found",
            message=f"Candidate claim not found: {claim_id}",
        )
    return claim
