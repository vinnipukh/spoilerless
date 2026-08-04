from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from spoilerless.app.api.deps import OptionalUserDependency
from spoilerless.app.cache.graph_cache import (
    get_cached_graph,
    set_cached_graph,
)
from spoilerless.app.domain.graph import (
    GraphResponse,
)
from spoilerless.app.core.errors import error_responses
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.domain.user_content import VisibleUntilOrder
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.graph.ontology import load_ontology
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.spoiler.policy import effective_view_order

router = APIRouter(prefix="/api/series", tags=["graph"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
VISIBLE_NODE_LABELS = [
    "Series",
    "Episode",
    "Character",
    "Event",
    "Location",
    "Organization",
    "Object",
]
USER_RELATIONSHIP_TYPES = sorted(load_ontology().user_safe_relationship_types)


def get_graph_service(database: DatabaseDependency) -> GraphService:
    return GraphService(database)


def get_progress_service(database: DatabaseDependency) -> ProgressService:
    return ProgressService(database)


GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@router.get(
    "/{series_id}/graph",
    response_model=GraphResponse,
    summary="Read the spoiler-safe series graph",
    responses=error_responses(404, 422, 503),
)
async def get_graph(
    series_id: str,
    service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: VisibleUntilOrder,
) -> GraphResponse:
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "series_not_found", "Series not found.")

    # The REQUESTED order must still identify a persisted episode (a client may
    # request any persisted order), but the FILTERING boundary is the effective
    # one: when the caller has a session and a persisted split progress record,
    # effective = min(requested, view_as_of_order, watched_through_order) —
    # a request above the selected view never raises the boundary (D-05).
    boundary_episode = await service.resolve_boundary(series_id, visible_until_order)
    if boundary_episode is None:
        raise _error(
            422,
            "invalid_visible_until_order",
            "visible_until_order must identify a persisted episode order.",
        )

    effective = visible_until_order
    if user is not None:
        record = await progress_service.get(user["id"], series_id)
        if record is not None:
            requested_view = min(visible_until_order, record.view_as_of_order)
            effective = effective_view_order(
                requested_view, record.watched_through_order
            )

    # Cache-aside (INFRA-02): check hit before the Neo4j query. The
    # cache key encodes the effective boundary + user_id, so a boundary
    # change is always a cache miss with no need to invalidate (T-08-06-02).
    user_id = user["id"] if user is not None else None
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

    # Write-through on miss (best-effort; swallows Redis errors).
    await set_cached_graph(series_id, effective, user_id, result.model_dump(mode="json"))
    return result
