from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.domain.series import EpisodeResponse, SeriesResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.core.errors import error_responses
from backend.app.services.series import SeriesService

router = APIRouter(prefix="/api/series", tags=["series"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


def get_series_service(database: DatabaseDependency) -> SeriesService:
    return SeriesService(database)


SeriesServiceDependency = Annotated[SeriesService, Depends(get_series_service)]


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
            detail={"code": "series_not_found", "message": "Series not found."},
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
) -> list[EpisodeResponse]:
    records = await service.list_episodes(series_id)
    if not records:
        raise HTTPException(
            status_code=404,
            detail={"code": "series_not_found", "message": "Series not found."},
        )
    return [EpisodeResponse(**record) for record in records]
