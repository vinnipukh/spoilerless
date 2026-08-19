from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from spoilerless.app.api.boundary import resolve_effective_boundary
from spoilerless.app.api.deps import OptionalUserDependency
from spoilerless.app.domain.series import EpisodeResponse, SeriesResponse
from spoilerless.app.domain.user_content import VisibleUntilOrder
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.core.errors import error_responses
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.services.series import SeriesService

router = APIRouter(prefix="/api/series", tags=["series"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


def get_series_service(database: DatabaseDependency) -> SeriesService:
    return SeriesService(database)


def get_progress_service(database: DatabaseDependency) -> ProgressService:
    return ProgressService(database)


def get_graph_service(database: DatabaseDependency) -> GraphService:
    return GraphService(database)


SeriesServiceDependency = Annotated[SeriesService, Depends(get_series_service)]
ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]
GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]


@router.get("", response_model=list[SeriesResponse], summary="List series", responses=error_responses(503))
async def list_series(service: SeriesServiceDependency) -> list[SeriesResponse]:
    records = await service.list_series()
    return [SeriesResponse(**record) for record in records]


@router.get("/{series_id}", response_model=SeriesResponse, summary="Read a series", responses=error_responses(404, 503))
async def get_series(series_id: str, service: SeriesServiceDependency) -> SeriesResponse:
    record = await service.get_series(series_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SERIES_NOT_FOUND", "message": "Series not found."},
        )
    return SeriesResponse(**record)


@router.get(
    "/{series_id}/episodes",
    response_model=list[EpisodeResponse],
    summary="List series episodes",
    responses=error_responses(404, 503),
)
async def list_episodes(
    series_id: str,
    service: SeriesServiceDependency,
    progress_service: ProgressServiceDependency,
    graph_service: GraphServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: VisibleUntilOrder = 1,
) -> list[EpisodeResponse]:
    """List episodes with server-side spoiler masking (META-01..03, D-21).

    ``visible_until_order`` is an OPTIONAL query parameter (default 1 —
    fail-closed for anonymous callers with no persisted record). When the
    caller has a session and a persisted split progress record, the effective
    boundary is the D-05 fail-closed min::

        requested_view = min(visible_until_order, persisted view_as_of_order)
        effective     = policy.effective_view_order(requested_view, persisted watched_through_order)

    so a request above the selected view never widens the boundary. Masking
    happens in the service (never the UI, D-08); synopsis/runtime/image are
    never returned above the boundary (META-02).
    """
    records = await service.list_episodes(series_id)
    if not records:
        raise HTTPException(
            status_code=404,
            detail={"code": "SERIES_NOT_FOUND", "message": "Series not found."},
        )

    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    masked = await service.list_episodes(series_id, effective_view_order=effective)
    return [EpisodeResponse(**record) for record in masked]
