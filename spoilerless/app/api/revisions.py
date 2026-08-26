from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from spoilerless.app.api.boundary import resolve_effective_boundary
from spoilerless.app.api.deps import (
    CsrfGuardDependency,
    CurrentUserDependency,
    DatabaseDependency,
    GraphServiceDependency,
    OptionalUserDependency,
    ProgressServiceDependency,
)
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.revision import RevisionResponse
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.repository.user_content import UserContentRepository
from spoilerless.app.revisions.repository import REVISION_GET_QUERY
from spoilerless.app.revisions.service import RevisionInvalidAction, revert_revision_work
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService

router = APIRouter(prefix="/api/series", tags=["revisions"])
Boundary = Annotated[
    int, Query(gt=0, description="Persisted positive spoiler boundary.", examples=[1])
]

REVISION_LIST_QUERY = """
MATCH (revision:Revision {series_id: $series_id})
WHERE revision.visible_from_order IS NOT NULL
  AND revision.visible_from_order >= 1
  AND revision.visible_from_order <= $visible_until_order
  AND ($resource_type IS NULL OR revision.resource_type = $resource_type)
  AND ($resource_id IS NULL OR revision.resource_id = $resource_id)
RETURN revision.id AS id, revision.series_id AS series_id,
  revision.resource_type AS resource_type, revision.resource_id AS resource_id,
  revision.action AS action, revision.before AS before,
  revision.after AS after, revision.visible_from_order AS visible_from_order,
  revision.user_id AS user_id, revision.created_at AS created_at
ORDER BY revision.created_at DESC, revision.id ASC
"""


def _not_found() -> Exception:
    return http_error(404, "RESOURCE_NOT_FOUND", "Resource not found.")


def _shape_revision_response(revision: dict, user: dict | None) -> dict:
    """D-02: non-owner responses never expose before/after snapshots or user_id."""
    owner = user["id"] if user is not None else None
    is_admin = bool(user and user.get("role") == "admin")
    if revision.get("user_id") != owner and not is_admin:
        for key in ("before", "after", "user_id"):
            revision.pop(key, None)
    return revision


# ---------------------------------------------------------------------------
# GET /api/series/{series_id}/revisions
# ---------------------------------------------------------------------------


@router.get(
    "/{series_id}/revisions",
    response_model=list[RevisionResponse],
    summary="List visible revisions for a series",
    responses=error_responses(422, 503),
)
async def list_revisions(
    series_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
) -> list[RevisionResponse]:
    if resource_type is not None and resource_type.strip() == "":
        resource_type = None
    if resource_id is not None and resource_id.strip() == "":
        resource_id = None
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    rows = await database.execute_query(
        REVISION_LIST_QUERY,
        series_id=series_id,
        visible_until_order=effective,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    shaped = [_shape_revision_response(dict(row), user) for row in rows]
    return [RevisionResponse.model_validate(row) for row in shaped]


# ---------------------------------------------------------------------------
# GET /api/series/{series_id}/revisions/{revision_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{series_id}/revisions/{revision_id}",
    response_model=RevisionResponse,
    summary="Get a single revision by ID",
    responses=error_responses(404, 422, 503),
)
async def get_revision(
    series_id: str,
    revision_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
) -> RevisionResponse:
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    rows = await database.execute_query(
        REVISION_GET_QUERY,
        revision_id=revision_id,
        series_id=series_id,
        visible_until_order=effective,
    )
    if not rows:
        raise _not_found()
    shaped = _shape_revision_response(dict(rows[0]), user)
    return RevisionResponse.model_validate(shaped)


# ---------------------------------------------------------------------------
# POST /api/series/{series_id}/revisions/{revision_id}/revert
# ---------------------------------------------------------------------------


@router.post(
    "/{series_id}/revisions/{revision_id}/revert",
    response_model=RevisionResponse,
    summary="Revert a resource to the state captured in a revision",
    responses=error_responses(404, 409, 422, 503),
)
async def revert_revision(
    series_id: str,
    revision_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    user: CurrentUserDependency,
    _csrf: CsrfGuardDependency,
) -> RevisionResponse:
    now = datetime.now(timezone.utc)
    actor_id = user["id"]
    is_admin = user.get("role") == "admin"

    # PROB-10/#60: the revert business flow (fetch revision -> action guards ->
    # owner checks -> snapshot restore / re-create -> REVERTED log) lives in
    # revisions.revert_revision_work; the route only builds the command and
    # validates the response. Envelope behavior is unchanged.
    command = {
        "series_id": series_id,
        "revision_id": revision_id,
        "visible_until_order": visible_until_order,
        "now": now,
        "user_id": actor_id,
        "is_admin": is_admin,
    }
    try:
        result = await database.execute_write(revert_revision_work, command)
    except RevisionInvalidAction as exc:
        raise http_error(422, "INVALID_ACTION", str(exc))
    return RevisionResponse.model_validate(result)
