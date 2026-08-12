from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from spoilerless.app.api.deps import CurrentUserDependency
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.revision import RevisionResponse
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.revisions import REVISION_GET_QUERY, revert_revision_work

router = APIRouter(prefix="/api/series", tags=["revisions"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
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
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
) -> list[RevisionResponse]:
    if resource_type is not None and resource_type.strip() == "":
        resource_type = None
    if resource_id is not None and resource_id.strip() == "":
        resource_id = None

    rows = await database.execute_query(
        REVISION_LIST_QUERY,
        series_id=series_id,
        visible_until_order=visible_until_order,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return [RevisionResponse.model_validate(row) for row in rows]


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
) -> RevisionResponse:
    rows = await database.execute_query(
        REVISION_GET_QUERY,
        revision_id=revision_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    if not rows:
        raise _not_found()
    return RevisionResponse.model_validate(rows[0])


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
    result = await database.execute_write(revert_revision_work, command)
    return RevisionResponse.model_validate(result)
