from __future__ import annotations

import asyncio
from typing import Any

from spoilerless.app.cache.graph_cache import (
    get_cached_graph,
    invalidate_series,
    set_cached_graph,
)
from spoilerless.app.domain.graph import (
    USER_RELATIONSHIP_TYPES,
    VISIBLE_NODE_LABELS,
    GraphClaim,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphResponse,
    GraphSource,
)
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.spoiler.filter import (
    BOUNDARY_QUERY,
    EVIDENCE_QUERY,
    NODES_QUERY,
    SERIES_QUERY,
    SOURCES_QUERY,
    STRUCTURAL_EDGES_QUERY,
    VISIBLE_CLAIMS_QUERY,
    VISIBLE_USER_RELATIONSHIPS_QUERY,
)
from spoilerless.app.spoiler.policy import filter_public_metadata


class GraphService:
    """Business logic for reading the spoiler-safe series graph."""

    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def invalidate_series_cache(self, series_id: str) -> None:
        """Deep invalidation seam for every content-mutating write (D-30: epoch bump before key deletes; T-08-06-01 over-invalidation is safe; T-08-06-02 errors swallowed)."""
        await invalidate_series(series_id)

    async def read_visible_graph(
        self, series_id: str, effective: int, user_id: str | None
    ) -> GraphResponse:
        """Cache-aside (INFRA-02): check hit before Neo4j, write-through on miss (best-effort; swallows Redis errors)."""
        cached = await get_cached_graph(series_id, effective, user_id)
        if cached is not None:
            return GraphResponse.model_validate(cached)

        result = await self.fetch_graph(
            series_id,
            effective,
            node_labels=VISIBLE_NODE_LABELS,
            user_relationship_types=USER_RELATIONSHIP_TYPES,
            effective_view_order=effective,
        )

        await set_cached_graph(series_id, effective, user_id, result.model_dump(mode="json"))
        return result

    async def find_path(
        self,
        *,
        source_entity_id: str,
        target_entity_id: str,
        max_hops: int,
        series_id: str,
        visible_until_order: int,
    ) -> dict[str, Any]:
        """Allowlisted find_path wrapper delegating to retrieval.tools."""
        from spoilerless.app.retrieval.tools import find_path as find_path_tool

        return await find_path_tool(
            self._database,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            max_hops=max_hops,
            series_id=series_id,
            visible_until_order=visible_until_order,
        )

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
        effective_view_order: int | None = None,
    ) -> GraphResponse:
        """Fetch and project the full graph for a validated series and boundary."""
        parameters: dict[str, Any] = {
            "series_id": series_id,
            "visible_until_order": visible_until_order,
        }
        effective = (
            effective_view_order if effective_view_order is not None else visible_until_order
        )
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

        # D-14 (MEDIA-01): run every node row through the public-metadata
        # projection so image_url/image_source_url (and any other
        # spoiler-sensitive field) are dropped for records above the EFFECTIVE
        # boundary before serialization. NODES_QUERY already filters by the
        # effective boundary, so this is defense-in-depth (D-03 fail-closed):
        # a row that ever slips past the query can never serialize a future
        # portrait URL. Masking is backend-side, never CSS (D-08/D-14).
        nodes = [
            GraphNode.model_validate(filter_public_metadata(row, effective))
            for row in nodes_rows
        ]

        return GraphResponse(
            series=SeriesResponse.model_validate(series_rows[0]),
            visible_until_order=visible_until_order,
            effective_view_order=effective,
            nodes=nodes,
            edges=[GraphEdge.model_validate(row) for row in structural_rows]
            + projected_edges
            + [GraphEdge.model_validate(row) for row in user_edge_rows],
            claims=claims,
            sources=[GraphSource.model_validate(row) for row in source_rows],
            evidence=[GraphEvidence.model_validate(row) for row in evidence_rows],
        )
