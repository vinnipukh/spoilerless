from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.domain.graph import (
    GraphClaim,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphResponse,
    GraphSource,
)
from backend.app.domain.series import SeriesResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.spoiler.filter import (
    BOUNDARY_QUERY,
    EVIDENCE_QUERY,
    NODES_QUERY,
    SERIES_QUERY,
    SOURCES_QUERY,
    STRUCTURAL_EDGES_QUERY,
    VISIBLE_CLAIMS_QUERY,
)

router = APIRouter(prefix="/api/series", tags=["graph"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
VISIBLE_NODE_LABELS = ["Series", "Episode", "Character", "Event", "Location"]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _parse_boundary(raw_boundary: str | None) -> int:
    if raw_boundary is None or not raw_boundary.isascii() or not raw_boundary.isdigit():
        raise _error(
            422,
            "invalid_visible_until_order",
            "visible_until_order must identify a persisted episode order.",
        )
    boundary = int(raw_boundary)
    if boundary < 1:
        raise _error(
            422,
            "invalid_visible_until_order",
            "visible_until_order must identify a persisted episode order.",
        )
    return boundary


@router.get("/{series_id}/graph", response_model=GraphResponse)
async def get_graph(
    series_id: str,
    database: DatabaseDependency,
    visible_until_order: str | None = Query(default=None),
) -> GraphResponse:
    series_rows = await database.execute_query(SERIES_QUERY, series_id=series_id)
    if not series_rows:
        raise _error(404, "series_not_found", "Series not found.")

    boundary = _parse_boundary(visible_until_order)
    boundary_rows = await database.execute_query(
        BOUNDARY_QUERY,
        series_id=series_id,
        visible_until_order=boundary,
    )
    if not boundary_rows:
        raise _error(
            422,
            "invalid_visible_until_order",
            "visible_until_order must identify a persisted episode order.",
        )

    parameters = {
        "series_id": series_id,
        "visible_until_order": boundary,
    }
    nodes_rows, structural_rows, claim_rows, source_rows, evidence_rows = (
        await asyncio.gather(
            database.execute_query(
                NODES_QUERY,
                **parameters,
                node_labels=VISIBLE_NODE_LABELS,
            ),
            database.execute_query(STRUCTURAL_EDGES_QUERY, **parameters),
            database.execute_query(VISIBLE_CLAIMS_QUERY, **parameters),
            database.execute_query(SOURCES_QUERY, **parameters),
            database.execute_query(EVIDENCE_QUERY, **parameters),
        )
    )

    claims = [GraphClaim.model_validate(row) for row in claim_rows]
    projected_edges = [
        GraphEdge(
            id=f"{claim.id}:edge",
            source=claim.subject_id,
            target=claim.object_id,
            type=claim.predicate,
            visible_from_order=claim.visible_from_order,
            origin=claim.origin,
            claim_id=claim.id,
        )
        for claim in claims
    ]

    return GraphResponse(
        series=SeriesResponse.model_validate(series_rows[0]),
        visible_until_order=boundary,
        nodes=[GraphNode.model_validate(row) for row in nodes_rows],
        edges=[GraphEdge.model_validate(row) for row in structural_rows]
        + projected_edges,
        claims=claims,
        sources=[GraphSource.model_validate(row) for row in source_rows],
        evidence=[GraphEvidence.model_validate(row) for row in evidence_rows],
    )
