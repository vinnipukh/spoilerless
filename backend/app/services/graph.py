from __future__ import annotations

import asyncio
from typing import Any

from backend.app.domain.graph import (
    GraphClaim,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphResponse,
    GraphSource,
)
from backend.app.domain.series import SeriesResponse
from backend.app.graph.database import Neo4jDatabase
from backend.app.spoiler.filter import (
    BOUNDARY_QUERY,
    EVIDENCE_QUERY,
    NODES_QUERY,
    SERIES_QUERY,
    SOURCES_QUERY,
    STRUCTURAL_EDGES_QUERY,
    VISIBLE_CLAIMS_QUERY,
    VISIBLE_USER_RELATIONSHIPS_QUERY,
)


class GraphService:
    """Business logic for reading the spoiler-safe series graph."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def get_series_meta(self, series_id: str) -> dict[str, Any] | None:
        """Fetch series metadata; returns None if not found."""
        records = await self._database.execute_query(SERIES_QUERY, series_id=series_id)
        return records[0] if records else None

    async def resolve_boundary(
        self, series_id: str, visible_until_order: int
    ) -> dict[str, Any] | None:
        """Check that the boundary order corresponds to a persisted episode."""
        records = await self._database.execute_query(
            BOUNDARY_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
        )
        return records[0] if records else None

    async def fetch_graph(
        self,
        series_id: str,
        visible_until_order: int,
        node_labels: list[str],
        user_relationship_types: list[str],
    ) -> GraphResponse:
        """Fetch and project the full graph for a validated series and boundary."""
        parameters: dict[str, Any] = {
            "series_id": series_id,
            "visible_until_order": visible_until_order,
        }
        (
            series_rows,
            nodes_rows,
            structural_rows,
            claim_rows,
            user_edge_rows,
            source_rows,
            evidence_rows,
        ) = await asyncio.gather(
            self._database.execute_query(SERIES_QUERY, series_id=series_id),
            self._database.execute_query(
                NODES_QUERY, **parameters, node_labels=node_labels
            ),
            self._database.execute_query(STRUCTURAL_EDGES_QUERY, **parameters),
            self._database.execute_query(VISIBLE_CLAIMS_QUERY, **parameters),
            self._database.execute_query(
                VISIBLE_USER_RELATIONSHIPS_QUERY,
                **parameters,
                user_relationship_types=user_relationship_types,
            ),
            self._database.execute_query(SOURCES_QUERY, **parameters),
            self._database.execute_query(EVIDENCE_QUERY, **parameters),
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
            visible_until_order=visible_until_order,
            nodes=[GraphNode.model_validate(row) for row in nodes_rows],
            edges=[GraphEdge.model_validate(row) for row in structural_rows]
            + projected_edges
            + [GraphEdge.model_validate(row) for row in user_edge_rows],
            claims=claims,
            sources=[GraphSource.model_validate(row) for row in source_rows],
            evidence=[GraphEvidence.model_validate(row) for row in evidence_rows],
        )
