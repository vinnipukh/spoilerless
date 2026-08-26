from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, model_validator

from spoilerless.app.api.boundary import resolve_effective_boundary
from spoilerless.app.api.deps import (
    CsrfGuardDependency,
    CurrentUserDependency,
    OptionalUserDependency,
    RequireAdminDependency,
)
from spoilerless.app.cache.graph_cache import invalidate_series
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.extraction import ExtractionBatchEnvelope
from spoilerless.app.domain.user_content import Identifier
from spoilerless.app.graph.candidates import CandidateRepository
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.services.rate_limit import content_write_rate_limiter

router = APIRouter(prefix="/api/series/{series_id}/candidates", tags=["candidates"])


async def get_candidate_repo(db: Neo4jDatabase = Depends(get_database)) -> CandidateRepository:
    return CandidateRepository(db)


async def get_graph_service(db: Neo4jDatabase = Depends(get_database)) -> GraphService:
    return GraphService(db)


async def get_progress_service(db: Neo4jDatabase = Depends(get_database)) -> ProgressService:
    return ProgressService(db)


CandidateRepoDependency = Annotated[CandidateRepository, Depends(get_candidate_repo)]
GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]
SeriesId = Annotated[Identifier, Path(description="Series identifier.")]
ClaimId = Annotated[Identifier, Path(description="Candidate claim identifier.", examples=["extracted:a1b2c3d4e5f6g7h8"])]


# --- Shared helpers ---


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
                    "example": {"detail": {"code": "INVALID_EXTRACTION_PAYLOAD", "message": "Validation failed at index 2: claim_type 'unknown' not in ontology"}}
                }
            },
        },
    },
)
async def ingest_candidates(
    series_id: SeriesId,
    envelope: ExtractionBatchEnvelope,
    repo: CandidateRepoDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> dict:
    """Ingest a batch of candidate claims from a future extractor.

    Auth-gated since 09-03 (PROB-01, #1) — anonymous ingestion is the
    first half of the graph-poisoning chain (#2) and is now forbidden.
    ``user`` is intentionally unused beyond the gate: candidate claims
    are review-workflow artifacts whose lifecycle (approve/reject/edit)
    stays admin-gated; actor attribution lands on the revisions those
    actions log (PROB-33, #33).
    """
    # PROB-09/#71: no catch-all 422 — the envelope is pydantic-validated at
    # the route boundary (malformed payloads already 422 there), and a
    # driver/Neo4j failure inside the transaction must reach the global
    # error handlers, not be relabeled as a payload problem with raw
    # str(exc) interpolated into the response.
    result = await repo.ingest_batch(series_id, envelope)
    await invalidate_series(series_id)
    return result


@router.get(
    "",
    response_model=list[dict],
    summary="List candidate claims for a series within a spoiler boundary",
    responses={
        200: {"description": "List of candidate claims with evidence and source details."},
        422: error_responses(422)[422],
    },
)
async def list_candidates(
    series_id: SeriesId,
    repo: CandidateRepoDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: int | None = Query(
        default=None,
        ge=1,
        description="Spoiler boundary for filtering (REQUIRED since PROB-05/#13).",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    after_created_at: datetime | None = Query(default=None),
    after_id: str | None = Query(default=None),
) -> list[dict]:
    """List candidate claims for a series, filtered by a RESOLVED boundary.

    PROB-05/#13: the boundary is resolved server-side — an omitted
    ``visible_until_order`` returns 422 (never a default-to-everything dump),
    and a present boundary must identify a persisted episode of the series.
    D-01: the EFFECTIVE boundary replaces the client-chosen order — anonymous
    and record-less callers are fixed at 1.
    """
    if visible_until_order is None:
        raise http_error(
            422,
            "INVALID_REQUEST",
            "visible_until_order is required to read candidates — an omitted "
            "boundary must never default to every visibility level.",
        )
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    return await repo.list_candidate_claims(
        series_id, effective, limit=limit, after_created_at=after_created_at, after_id=after_id
    )


@router.get(
    "/{claim_id}",
    response_model=dict | None,
    summary="Get a single candidate claim by ID within a spoiler boundary",
    responses={
        200: {"description": "Candidate claim details with evidence and source."},
        404: {"description": "Candidate claim not found (or hidden above the boundary)."},
        422: error_responses(422)[422],
    },
)
async def get_candidate(
    series_id: SeriesId,
    claim_id: ClaimId,
    repo: CandidateRepoDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: int | None = Query(
        default=None,
        ge=1,
        description="Spoiler boundary for filtering (REQUIRED since PROB-05/#13).",
    ),
) -> dict | None:
    """Get a single candidate claim by ID, within the resolved boundary.

    PROB-05/#13: like the list endpoint, the boundary is required and
    validated against a persisted episode; an above-boundary claim reads as
    missing (D-15 — hidden and missing are indistinguishable).
    D-01: effective boundary clamped via shared resolver.
    """
    if visible_until_order is None:
        raise http_error(
            422,
            "INVALID_REQUEST",
            "visible_until_order is required to read candidates — an omitted "
            "boundary must never default to every visibility level.",
        )
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    claim = await repo.get_candidate_claim(
        series_id, claim_id, visible_until_order=effective
    )
    if claim is None:
        raise http_error(404, "CANDIDATE_NOT_FOUND", f"Candidate claim not found: {claim_id}")
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
    _admin: RequireAdminDependency,
    _csrf: CsrfGuardDependency,
) -> dict:
    """Approve a candidate claim, promoting it from 'candidate' to 'canonical'
    status. Admin-only since 08-03 (AUTH-03, T-08-03-01) — a non-admin gets 403.

    PROB-10/#60: the transaction (read -> origin guard -> status write ->
    revision log) lives in ``CandidateRepository.approve_claim``; the route
    only builds the command and invalidates the graph cache.
    """
    # PROB-09/#71: no catch-all 422 — the repository raises HTTPException
    # (404/409) which propagates, and any Neo4j/driver error reaches the
    # global error handlers. A DB failure must never be mislabeled as an
    # extraction-payload problem, and raw str(exc) is never interpolated
    # into the client response.
    result = await repo.approve_claim(
        series_id=series_id,
        claim_id=claim_id,
        user_id=_admin["id"],
        now=datetime.now(timezone.utc),
    )
    await invalidate_series(series_id)
    return result


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
    _admin: RequireAdminDependency,
    _csrf: CsrfGuardDependency,
) -> dict:
    """Reject a candidate claim, setting its status to 'rejected'.
    Admin-only since 08-03 (AUTH-03, T-08-03-01) — a non-admin gets 403.

    PROB-10/#60: the transaction lives in ``CandidateRepository.reject_claim``.
    """
    # PROB-09/#71: no catch-all 422 (see approve_candidate).
    result = await repo.reject_claim(
        series_id=series_id,
        claim_id=claim_id,
        user_id=_admin["id"],
        now=datetime.now(timezone.utc),
    )
    await invalidate_series(series_id)
    return result


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
    _admin: RequireAdminDependency,
    _csrf: CsrfGuardDependency,
) -> dict:
    """Edit a candidate claim's mutable fields. Creates a revision with
    before/after snapshots. Admin-only since 08-03 (AUTH-03, T-08-03-01).

    PROB-10/#60: the transaction lives in ``CandidateRepository.edit_claim``.
    """
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # PROB-09/#71: only ValueError (mutable-field validation) maps to 422;
    # HTTPException (404) and driver/Neo4j errors propagate — no catch-all.
    try:
        result = await repo.edit_claim(
            series_id=series_id,
            claim_id=claim_id,
            updates=updates,
            user_id=_admin["id"],
            now=datetime.now(timezone.utc),
        )
    except ValueError as exc:
        raise http_error(422, "INVALID_EXTRACTION_PAYLOAD", str(exc))
    await invalidate_series(series_id)
    return result
