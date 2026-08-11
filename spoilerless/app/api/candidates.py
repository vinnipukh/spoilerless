from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, model_validator

from spoilerless.app.api.deps import CurrentUserDependency, RequireAdminDependency
from spoilerless.app.cache.graph_cache import invalidate_series
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.extraction import ExtractionBatchEnvelope
from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.domain.user_content import Identifier
from spoilerless.app.graph.candidates import CandidateRepository
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.revisions import RevisionRepository
from spoilerless.app.services.graph import GraphService

router = APIRouter(prefix="/api/series/{series_id}/candidates", tags=["candidates"])


async def get_candidate_repo(db: Neo4jDatabase = Depends(get_database)) -> CandidateRepository:
    return CandidateRepository(db)


async def get_graph_service(db: Neo4jDatabase = Depends(get_database)) -> GraphService:
    return GraphService(db)


CandidateRepoDependency = Annotated[CandidateRepository, Depends(get_candidate_repo)]
GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
SeriesId = Annotated[Identifier, Path(description="Series identifier.")]
ClaimId = Annotated[Identifier, Path(description="Candidate claim identifier.", examples=["extracted:a1b2c3d4e5f6g7h8"])]


# --- Shared helpers ---


async def _require_resolved_boundary(
    graph_service: GraphService, series_id: str, visible_until_order: int | None
) -> None:
    """PROB-05/#13: a candidate read requires a RESOLVED spoiler boundary.

    An omitted boundary never defaults to everything — the server rejects it
    with the 422 envelope. A present boundary must identify a persisted
    episode of the series, mirroring the graph read path (D-09); the
    visibility filter is then applied by the repository query.
    """
    if visible_until_order is None:
        raise http_error(
            422,
            "INVALID_REQUEST",
            "visible_until_order is required to read candidates — an omitted "
            "boundary must never default to every visibility level.",
        )
    boundary_episode = await graph_service.resolve_boundary(
        series_id, visible_until_order
    )
    if boundary_episode is None:
        raise http_error(
            422,
            "INVALID_VISIBLE_UNTIL_ORDER",
            "visible_until_order must identify a persisted episode order.",
        )


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
    return await repo.ingest_batch(series_id, envelope)


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
    visible_until_order: int | None = Query(
        default=None,
        ge=1,
        description="Spoiler boundary for filtering (REQUIRED since PROB-05/#13).",
    ),
) -> list[dict]:
    """List candidate claims for a series, filtered by a RESOLVED boundary.

    PROB-05/#13: the boundary is resolved server-side — an omitted
    ``visible_until_order`` returns 422 (never a default-to-everything dump),
    and a present boundary must identify a persisted episode of the series.
    """
    await _require_resolved_boundary(graph_service, series_id, visible_until_order)
    return await repo.list_candidate_claims(series_id, visible_until_order)


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
    """
    await _require_resolved_boundary(graph_service, series_id, visible_until_order)
    claim = await repo.get_candidate_claim(
        series_id, claim_id, visible_until_order=visible_until_order
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
) -> dict:
    """Approve a candidate claim, promoting it from 'candidate' to 'canonical'
    status. Admin-only since 08-03 (AUTH-03, T-08-03-01) — a non-admin gets 403."""

    async def _approve(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "CANDIDATE_NOT_FOUND", f"Candidate claim not found: {cmd['claim_id']}")
        row = dict(record.data())
        if row["origin"] != "candidate":
            raise http_error(409, "CANNOT_APPROVE_NON_CANDIDATE", f"Claim '{cmd['claim_id']}' origin is '{row['origin']}', not 'candidate'.")

        before = dict(row)
        after = dict(before)
        after["status"] = "canonical"

        await tx.run("""
            MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
            SET claim.status = 'canonical'
        """, claim_id=cmd["claim_id"], series_id=cmd["series_id"])

        now = cmd["now"]
        revision = await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1),
            created_at=now, user_id=cmd["user_id"])
        # Return the id RevisionRepository.log_revision actually persisted
        # (PROB-12, #34) — never a fabricated hash. GET /revisions/{id} resolves it.
        return {"id": cmd["claim_id"], "status": "canonical", "origin": "candidate", "revision_id": revision["id"]}

    # PROB-09/#71: no catch-all 422 — the closure raises HTTPException
    # (404/409) which propagates, and any Neo4j/driver error reaches the
    # global error handlers. A DB failure must never be mislabeled as an
    # extraction-payload problem, and raw str(exc) is never interpolated
    # into the client response.
    result = await repo.approve_claim(_approve, {"series_id": series_id, "claim_id": claim_id, "now": datetime.now(timezone.utc), "user_id": _admin["id"]})
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
) -> dict:
    """Reject a candidate claim, setting its status to 'rejected'.
    Admin-only since 08-03 (AUTH-03, T-08-03-01) — a non-admin gets 403."""

    async def _reject(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "CANDIDATE_NOT_FOUND", f"Candidate claim not found: {cmd['claim_id']}")

        row = dict(record.data())
        before = dict(row)
        after = dict(before)
        after["status"] = "rejected"

        await tx.run("""
            MATCH (claim:Claim {id: $claim_id, series_id: $series_id, origin: 'candidate'})
            SET claim.status = 'rejected'
        """, claim_id=cmd["claim_id"], series_id=cmd["series_id"])

        now = cmd["now"]
        revision = await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1),
            created_at=now, user_id=cmd["user_id"])
        return {"id": cmd["claim_id"], "status": "rejected", "origin": "candidate", "revision_id": revision["id"]}

    # PROB-09/#71: no catch-all 422 (see approve_candidate).
    result = await repo.reject_claim(_reject, {"series_id": series_id, "claim_id": claim_id, "now": datetime.now(timezone.utc), "user_id": _admin["id"]})
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
) -> dict:
    """Edit a candidate claim's mutable fields. Creates a revision with
    before/after snapshots. Admin-only since 08-03 (AUTH-03, T-08-03-01)."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    async def _edit(tx: Any, cmd: dict[str, Any]) -> dict[str, Any]:
        read_query = _read_claim_query()
        result = await tx.run(read_query, claim_id=cmd["claim_id"], series_id=cmd["series_id"])
        record = await result.single()
        if record is None:
            raise http_error(404, "CANDIDATE_NOT_FOUND", f"Candidate claim not found: {cmd['claim_id']}")

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
        after = {**before, **cmd["updates"]}
        revision = await RevisionRepository.log_revision(tx, series_id=cmd["series_id"], resource_type="Claim",
            resource_id=cmd["claim_id"], action=RevisionAction.UPDATED,
            before=before, after=after, visible_from_order=before.get("visible_from_order", 1),
            created_at=now, user_id=cmd["user_id"])
        return {"id": cmd["claim_id"], "status": "edited", "origin": "candidate", "revision_id": revision["id"], "updates_applied": list(cmd["updates"].keys())}

    # PROB-09/#71: only ValueError (mutable-field validation) maps to 422;
    # HTTPException (404) and driver/Neo4j errors propagate — no catch-all.
    try:
        result = await repo.edit_claim(_edit, {"series_id": series_id, "claim_id": claim_id, "updates": updates, "now": datetime.now(timezone.utc), "user_id": _admin["id"]})
    except ValueError as exc:
        raise http_error(422, "INVALID_EXTRACTION_PAYLOAD", str(exc))
    await invalidate_series(series_id)
    return result
