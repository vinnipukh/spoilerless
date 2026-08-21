"""Standard view projections: overview, character network, plot threads, investigation, full."""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphResponse
from spoilerless.app.domain.visualization import (
    CHARACTER_NETWORK_VIEW_TYPE,
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EPISODE_OVERVIEW_MAX_EDGES,
    EPISODE_OVERVIEW_MAX_NODES,
    EPISODE_OVERVIEW_VIEW_TYPE,
    FULL_VIEW_TYPE,
    INVESTIGATION_VIEW_TYPE,
    PLOT_THREADS_VIEW_TYPE,
    SafeEventContext,
    SafePlotThread,
    VisualizationDTO,
    VisualizationEdge,
    VisualizationGroup,
    VisualizationNode,
)
from spoilerless.app.services.visualization.boundary import (
    build_metadata,
    to_timeline_item,
    validate_events,
    validate_safe_graph,
)
from spoilerless.app.services.visualization.constants import (
    CLAIM_STATUS_DISPLAY_TIER,
    CONTAINER_KINDS,
    EVENT_TIER_DISPLAY_TIER,
    FROM_SOURCE_EDGE_CLASS,
    FULL_EDGE_CLASSES,
    KEPT_NODE_KINDS,
    SUPPORTED_BY_EDGE_CLASS,
)
from spoilerless.app.services.visualization.node_builders import (
    project_narrative_edges,
    project_node,
)
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder, is_visible


def project_episode_overview(
    graph: GraphResponse,
    events: list[SafeEventContext] | None = None,
) -> VisualizationDTO:
    """Project the D-10 Variant A Episode Overview from a safe response."""
    events = list(events) if events is not None else []
    served, effective = validate_safe_graph(graph)
    event_by_id = validate_events(events, effective)
    node_by_id = {node.id: node for node in graph.nodes}

    kept_nodes: list[VisualizationNode] = []
    kept_ids: set[str] = set()
    for node in graph.nodes:
        if node.type in KEPT_NODE_KINDS:
            tier = (
                DISPLAY_TIER_SUPPORTING
                if node.type in CONTAINER_KINDS
                else DISPLAY_TIER_CORE
            )
        elif node.type == "Event":
            event = event_by_id.get(node.id)
            if event is None or event.tier != "major":
                continue
            tier = DISPLAY_TIER_CORE
        else:
            continue
        kept_nodes.append(project_node(node, node.type, tier))
        kept_ids.add(node.id)

    kept_edges = project_narrative_edges(graph, kept_ids)

    timeline = [
        to_timeline_item(event, node_by_id, effective)
        for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
    ]

    if len(kept_nodes) > EPISODE_OVERVIEW_MAX_NODES:
        raise ValueError(
            f"Episode Overview exceeds the hard node cap "
            f"({len(kept_nodes)} > {EPISODE_OVERVIEW_MAX_NODES}); refusing to "
            "serialize an unbounded projection (D-09)."
        )
    if len(kept_edges) > EPISODE_OVERVIEW_MAX_EDGES:
        raise ValueError(
            f"Episode Overview exceeds the hard edge cap "
            f"({len(kept_edges)} > {EPISODE_OVERVIEW_MAX_EDGES}); refusing to "
            "serialize an unbounded projection (D-09)."
        )

    return VisualizationDTO(
        metadata=build_metadata(graph, EPISODE_OVERVIEW_VIEW_TYPE),
        nodes=kept_nodes,
        edges=kept_edges,
        groups=[],
        timeline=timeline,
        focus=None,
    )


def project_character_network(graph: GraphResponse) -> VisualizationDTO:
    """Project the character network (D-17 Characters tab)."""
    served, effective = validate_safe_graph(graph)

    kept_nodes = [
        project_node(node, "Character", DISPLAY_TIER_CORE)
        for node in graph.nodes
        if node.type == "Character"
    ]
    kept_ids = {node.id for node in kept_nodes}
    kept_edges = project_narrative_edges(graph, kept_ids)

    return VisualizationDTO(
        metadata=build_metadata(graph, CHARACTER_NETWORK_VIEW_TYPE),
        nodes=kept_nodes,
        edges=kept_edges,
        groups=[],
        timeline=[],
        focus=None,
    )


def project_plot_threads(
    graph: GraphResponse,
    events: list[SafeEventContext] | None = None,
    threads: list[SafePlotThread] | None = None,
) -> VisualizationDTO:
    """Project the plot-thread story view (D-36/D-38)."""
    events = list(events) if events is not None else []
    served, effective = validate_safe_graph(graph)
    event_by_id = validate_events(events, effective)
    node_by_id = {node.id: node for node in graph.nodes}

    kept_nodes: list[VisualizationNode] = []
    kept_ids: set[str] = set()
    for node in graph.nodes:
        if node.type in CONTAINER_KINDS:
            tier = DISPLAY_TIER_SUPPORTING
        elif node.type == "Character":
            tier = DISPLAY_TIER_CORE
        elif node.type == "Event":
            event = event_by_id.get(node.id)
            if event is None:
                continue
            tier = EVENT_TIER_DISPLAY_TIER[event.tier]
        else:
            continue
        kept_nodes.append(project_node(node, node.type, tier))
        kept_ids.add(node.id)

    kept_edges = project_narrative_edges(graph, kept_ids)

    groups: list[VisualizationGroup] = []
    for thread in threads or []:
        unknown = [nid for nid in thread.node_ids if nid not in kept_ids]
        if unknown:
            raise InvalidVisibilityOrder(
                f"Plot thread {thread.id!r} references nodes outside the "
                f"projected view: {', '.join(sorted(unknown))} (fail closed, "
                "D-36)."
            )
        groups.append(
            VisualizationGroup(id=thread.id, label=thread.label, node_ids=thread.node_ids)
        )

    timeline = [
        to_timeline_item(event, node_by_id, effective)
        for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
    ]

    return VisualizationDTO(
        metadata=build_metadata(graph, PLOT_THREADS_VIEW_TYPE),
        nodes=kept_nodes,
        edges=kept_edges,
        groups=groups,
        timeline=timeline,
        focus=None,
    )


def project_investigation(graph: GraphResponse) -> VisualizationDTO:
    """Project the layered Investigation view (D-28/D-41)."""
    served, effective = validate_safe_graph(graph)
    for row in [*graph.claims, *graph.sources, *graph.evidence]:
        if not is_visible(row, effective):
            raise InvalidVisibilityOrder(
                f"Hidden investigation row {row.id!r} cannot be projected "
                f"at boundary {effective}."
            )

    evidence_by_id = {item.id: item for item in graph.evidence}
    sources_by_id = {item.id: item for item in graph.sources}

    nodes: list[VisualizationNode] = []
    edges: list[VisualizationEdge] = []
    for claim in graph.claims:
        try:
            tier = CLAIM_STATUS_DISPLAY_TIER[claim.status]
        except KeyError:
            raise ValueError(
                f"Claim {claim.id!r} has unknown status {claim.status!r}; "
                "refusing to classify investigation detail (D-15)."
            ) from None
        nodes.append(project_node(claim, "Claim", tier))
        for evidence_id in claim.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                raise ValueError(
                    f"Claim {claim.id!r} references evidence {evidence_id!r} "
                    "outside the safe payload (fail closed, D-04)."
                )
            edges.append(
                VisualizationEdge(
                    id=f"{claim.id}:supported_by:{evidence_id}",
                    source=claim.id,
                    target=evidence_id,
                    relation_class=SUPPORTED_BY_EDGE_CLASS,
                    order=claim.visible_from_order,
                    claim_id=claim.id,
                    origin=claim.origin,
                )
            )

    for evidence in graph.evidence:
        nodes.append(
            project_node(evidence, "Evidence", DISPLAY_TIER_DETAIL)
        )
        source = sources_by_id.get(evidence.source_id)
        if source is None:
            raise ValueError(
                f"Evidence {evidence.id!r} references source "
                f"{evidence.source_id!r} outside the safe payload (fail "
                "closed, D-04)."
            )
        edges.append(
            VisualizationEdge(
                id=f"{evidence.id}:from_source:{source.id}",
                source=evidence.id,
                target=source.id,
                relation_class=FROM_SOURCE_EDGE_CLASS,
                order=evidence.visible_from_order,
                claim_id=None,
                origin=evidence.origin,
            )
        )

    for source in graph.sources:
        nodes.append(project_node(source, "Source", DISPLAY_TIER_DETAIL))

    return VisualizationDTO(
        metadata=build_metadata(graph, INVESTIGATION_VIEW_TYPE),
        nodes=nodes,
        edges=edges,
        groups=[],
        timeline=[],
        focus=None,
    )


def project_full(
    graph: GraphResponse,
    events: list[SafeEventContext] | None = None,
) -> VisualizationDTO:
    """Project the complete safe graph (D-11 Advanced/full mode)."""
    events = list(events) if events is not None else []
    served, effective = validate_safe_graph(graph)
    event_by_id = validate_events(events, effective)

    kept_nodes: list[VisualizationNode] = []
    for node in graph.nodes:
        if node.type == "Character":
            tier = DISPLAY_TIER_CORE
        elif node.type == "Event":
            event = event_by_id.get(node.id)
            tier = (
                EVENT_TIER_DISPLAY_TIER[event.tier]
                if event is not None
                else DISPLAY_TIER_DETAIL
            )
        else:
            tier = DISPLAY_TIER_SUPPORTING
        kept_nodes.append(project_node(node, node.type, tier))

    kept_ids = {node.id for node in kept_nodes}
    kept_edges = project_narrative_edges(
        graph, kept_ids, edge_classes=FULL_EDGE_CLASSES, omit=frozenset()
    )

    node_by_id = {node.id: node for node in graph.nodes}
    timeline = [
        to_timeline_item(event, node_by_id, effective)
        for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
    ]

    return VisualizationDTO(
        metadata=build_metadata(graph, FULL_VIEW_TYPE),
        nodes=kept_nodes,
        edges=kept_edges,
        groups=[],
        timeline=timeline,
        focus=None,
    )
