from fastapi import APIRouter, HTTPException

from app.domain.series import EpisodeResponse, SeriesResponse
from app.graph.database import neo4j_db


router = APIRouter(
    prefix="/api/series",
    tags=["series"],
)


@router.get("", response_model=list[SeriesResponse])
def list_series() -> list[SeriesResponse]:
    query = """
    MATCH (series:Series)
    RETURN series.id AS id,
           series.title AS title,
           series.slug AS slug
    ORDER BY series.title
    """

    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        records = session.run(query)

        return [
            SeriesResponse(**record.data())
            for record in records
        ]


@router.get(
    "/{series_id}/episodes",
    response_model=list[EpisodeResponse],
)
def list_episodes(series_id: str) -> list[EpisodeResponse]:
    query = """
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
    """

    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        records = list(
            session.run(
                query,
                series_id=series_id,
            )
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="Dizi bulunamadı veya bölümü yok.",
        )

    return [
        EpisodeResponse(**record.data())
        for record in records
    ]