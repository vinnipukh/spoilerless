from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from spoilerless.app.api.boundary import resolve_effective_boundary
from spoilerless.app.api.deps import (
    CsrfGuardDependency,
    CurrentUserDependency,
    DatabaseDependency,
    ShareRepoDependency,
)
from spoilerless.app.api.graph import (
    USER_RELATIONSHIP_TYPES,
    VISIBLE_NODE_LABELS,
    ProgressServiceDependency,
)
from spoilerless.app.cache.graph_cache import (
    get_cached_graph,
    set_cached_graph,
)
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.graph import GraphResponse
from spoilerless.app.domain.share import (
    ShareCreateRequest,
    ShareCreateResponse,
    ShareItemResponse,
    ShareTokenRecord,
)
from spoilerless.app.services.graph import GraphService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/share", tags=["share"])


@router.post(
    "",
    response_model=ShareCreateResponse,
    status_code=201,
    summary="Create a shareable snapshot link of current view",
    responses=error_responses(401, 422, 503),
)
async def create_share_link(
    payload: ShareCreateRequest,
    database: DatabaseDependency,
    share_repo: ShareRepoDependency,
    progress_service: ProgressServiceDependency,
    user: CurrentUserDependency,
    _csrf: CsrfGuardDependency,
) -> ShareCreateResponse:
    service = GraphService(database)

    # CR-01 (09-REVIEW): a share snapshot must never widen the creator's own
    # spoiler-safe window (PROB-04/D-05). The single fail-closed boundary
    # authority owns the whole clamp: progress lookup, min/effective_view
    # math, fail-closed-to-1 without a record, and the persisted-episode
    # validation (422 INVALID_VISIBLE_UNTIL_ORDER otherwise). 12-10 closed
    # the last bypass (Candidate C2) that re-implemented this inline.
    effective = await resolve_effective_boundary(
        service, progress_service, payload.series_id, user, payload.visible_until_order
    )

    raw_token, record = await share_repo.create(
        created_by=user["id"],
        series_id=payload.series_id,
        visible_until_order=effective,
    )

    return ShareCreateResponse(
        token=raw_token,
        expires_at=record.expires_at,
        url=f"/share/{raw_token}",
        series_id=record.series_id,
        visible_until_order=record.visible_until_order,
        created_at=record.created_at,
    )


@router.get(
    "/{token}/graph",
    response_model=GraphResponse,
    summary="Read-only token-gated snapshot graph (unauthenticated)",
    responses=error_responses(404, 503),
)
async def get_share_graph(
    token: str,
    database: DatabaseDependency,
    share_repo: ShareRepoDependency,
) -> GraphResponse:
    record = await share_repo.get_by_raw_token(token)
    if record is None or not record.is_valid:
        raise http_error(
            404,
            "TOKEN_NOT_FOUND",
            "Snapshot link is invalid, expired, or revoked.",
        )

    series_id = record.series_id
    effective = record.visible_until_order
    user_id = None

    service = GraphService(database)
    # WR-02 (09-REVIEW): a token whose series was deleted must 404, not 500
    # (IndexError in fetch_graph's series_rows[0]).
    series = await service.get_series_meta(series_id)
    if series is None:
        raise http_error(
            404,
            "RESOURCE_NOT_FOUND",
            "The shared series no longer exists.",
        )

    # NO-SECOND-FILTER (D-09): Reuses exact fetch_graph assembly as api/graph.py
    cached = await get_cached_graph(series_id, effective, user_id)
    if cached is not None:
        return GraphResponse.model_validate(cached)

    result = await service.fetch_graph(
        series_id,
        effective,
        node_labels=VISIBLE_NODE_LABELS,
        user_relationship_types=USER_RELATIONSHIP_TYPES,
        effective_view_order=effective,
    )

    await set_cached_graph(
        series_id, effective, user_id, result.model_dump(mode="json")
    )
    return result


@router.get(
    "",
    response_model=list[ShareItemResponse],
    summary="List active share tokens created by current user",
    responses=error_responses(401, 503),
)
async def list_share_links(
    share_repo: ShareRepoDependency,
    user: CurrentUserDependency,
) -> list[ShareItemResponse]:
    records = await share_repo.list_active(user["id"])
    return [
        ShareItemResponse(
            id=rec.id,
            token_hash=rec.token_hash,
            series_id=rec.series_id,
            visible_until_order=rec.visible_until_order,
            created_at=rec.created_at,
            expires_at=rec.expires_at,
        )
        for rec in records
    ]


@router.delete(
    "/{token}",
    summary="Revoke a share token",
    responses=error_responses(401, 403, 404, 503),
)
async def revoke_share_link(
    token: str,
    share_repo: ShareRepoDependency,
    user: CurrentUserDependency,
    _csrf: CsrfGuardDependency,
) -> dict[str, str]:
    # Support revoking by raw token, hash, or token id
    record = await share_repo.get_by_raw_token(token)
    if record is None:
        record = await share_repo.get_by_token_hash(token)

    if record is None:
        raise http_error(
            404,
            "TOKEN_NOT_FOUND",
            "Snapshot link not found or already revoked.",
        )

    if record.created_by != user["id"] and user.get("role") != "admin":
        raise http_error(
            403,
            "FORBIDDEN",
            "This share token belongs to another user.",
        )

    await share_repo.revoke(record.token_hash)
    return {"status": "revoked"}
