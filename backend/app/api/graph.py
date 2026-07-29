from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.domain.graph import (
    GraphResponse,
)
from backend.app.core.errors import error_responses
from backend.app.domain.series import SeriesResponse
from backend.app.domain.user_content import VisibleUntilOrder
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.graph.ontology import load_ontology
from backend.app.services.graph import GraphService

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


GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]


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
    visible_until_order: VisibleUntilOrder,
) -> GraphResponse:
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "series_not_found", "Series not found.")

    boundary = visible_until_order
    boundary_episode = await service.resolve_boundary(series_id, boundary)
    if boundary_episode is None:
        raise _error(
            422,
            "invalid_visible_until_order",
            "visible_until_order must identify a persisted episode order.",
        )

    return await service.fetch_graph(
        series_id,
        boundary,
        node_labels=VISIBLE_NODE_LABELS,
        user_relationship_types=USER_RELATIONSHIP_TYPES,
    )
