from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.domain.series import EpisodeResponse, SeriesResponse
from backend.app.graph.database import Neo4jDatabase, get_database

router = APIRouter(prefix="/api/series", tags=["series"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


@router.get("", response_model=list[SeriesResponse])
async def list_series(database: DatabaseDependency) -> list[SeriesResponse]:
    records = await database.execute_query(
        """
        MATCH (series:Series)
        RETURN series.id AS id,
               series.title AS title,
               series.slug AS slug
        ORDER BY series.title
        """
    )
    return [SeriesResponse(**record) for record in records]


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(series_id: str, database: DatabaseDependency) -> SeriesResponse:
    records = await database.execute_query(
        """
        MATCH (series:Series {id: $series_id})
        RETURN series.id AS id,
               series.title AS title,
               series.slug AS slug
        """,
        series_id=series_id,
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail={"code": "series_not_found", "message": "Series not found."},
        )
    return SeriesResponse(**records[0])


@router.get("/{series_id}/episodes", response_model=list[EpisodeResponse])
async def list_episodes(
    series_id: str,
    database: DatabaseDependency,
) -> list[EpisodeResponse]:
    records = await database.execute_query(
        """
        MATCH (episode:Episode)-[:PART_OF]->(series:Series {id: $series_id})
        RETURN episode.id AS id,
               episode.series_id AS series_id,
               episode.season_number AS season_number,
               episode.episode_number AS episode_number,
               episode.episode_order AS episode_order,
               episode.code AS code,
               episode.title AS title,
               episode.visible_from_order AS visible_from_order
        ORDER BY episode.episode_order
        """,
        series_id=series_id,
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail={"code": "series_not_found", "message": "Series not found."},
        )
    return [EpisodeResponse(**record) for record in records]
