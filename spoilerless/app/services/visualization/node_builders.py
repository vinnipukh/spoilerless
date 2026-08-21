"""Node and narrative edge projection helpers."""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphNode, GraphResponse
from spoilerless.app.domain.visualization import (
    VisualizationEdge,
    VisualizationNode,
)
from spoilerless.app.services.visualization.constants import (
    HUMAN_EDGE_CLASSES,
    OMITTED_EDGE_TYPES,
)


def project_node(
    node: GraphNode, kind: str, tier: int, *, order: int | None = None
) -> VisualizationNode:
    """Project one safe graph node into the neutral shape."""
    return VisualizationNode(
        id=node.id,
        kind=kind,
        label=node.label,
        display_tier=tier,
        order=order if order is not None else node.visible_from_order,
        episode_id=getattr(node, "episode_id", None),
        image_url=getattr(node, "image_url", None),
        image_source_url=getattr(node, "image_source_url", None),
        origin=node.origin,
    )


def project_narrative_edges(
    graph: GraphResponse,
    kept_ids: set[str],
    edge_classes: dict[str, str] = HUMAN_EDGE_CLASSES,
    omit: frozenset[str] = OMITTED_EDGE_TYPES,
) -> list[VisualizationEdge]:
    """Project edges between kept nodes as human semantic classes."""
    kept_edges: list[VisualizationEdge] = []
    for edge in graph.edges:
        if edge.type in omit:
            continue
        try:
            relation_class = edge_classes[edge.type]
        except KeyError:
            raise ValueError(
                f"Unmapped relationship type {edge.type!r}: refusing to expose "
                "a raw technical edge label (D-14)."
            ) from None
        if edge.source not in kept_ids or edge.target not in kept_ids:
            continue
        kept_edges.append(
            VisualizationEdge(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                relation_class=relation_class,
                order=edge.visible_from_order,
                claim_id=edge.claim_id,
                origin=edge.origin,
            )
        )
    return kept_edges
