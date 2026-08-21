"""Bounded GraphRAG Answer Graph projection (D-26/D-27/D-48)."""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphResponse
from spoilerless.app.domain.visualization import (
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_SUPPORTING,
    GRAPHRAG_FOCUS_MAX_IDS,
    GRAPHRAG_FOCUS_MAX_NODES,
    GRAPHRAG_FOCUS_VIEW_TYPE,
    SafeEventContext,
    TimelineItem,
    VisualizationDTO,
    VisualizationFocus,
)
from spoilerless.app.services.visualization.boundary import (
    build_metadata,
    to_timeline_item,
    validate_events,
    validate_safe_graph,
)
from spoilerless.app.services.visualization.constants import OMITTED_EDGE_TYPES
from spoilerless.app.services.visualization.node_builders import (
    project_narrative_edges,
    project_node,
)
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder


def project_graphrag_focus(
    graph: GraphResponse,
    focus_ids: list[str] | None = None,
    events: list[SafeEventContext] | None = None,
) -> VisualizationDTO:
    """Project the bounded GraphRAG Answer Graph (D-26/D-27/D-48)."""
    events = list(events) if events is not None else []
    served, effective = validate_safe_graph(graph)
    event_by_id = validate_events(events, effective)
    canonical: list[str] = []
    seen: set[str] = set()
    for focus_id in focus_ids or []:
        if not isinstance(focus_id, str) or not focus_id:
            raise InvalidVisibilityOrder(
                f"Invalid focus id {focus_id!r}; focus ids must be non-empty."
            )
        if focus_id not in seen:
            seen.add(focus_id)
            canonical.append(focus_id)

    if not canonical:
        raise InvalidVisibilityOrder(
            "graphrag_focus requires at least one focus id."
        )
    if len(canonical) > GRAPHRAG_FOCUS_MAX_IDS:
        raise InvalidVisibilityOrder(
            f"graphrag_focus accepts at most {GRAPHRAG_FOCUS_MAX_IDS} "
            f"distinct focus ids, got {len(canonical)}."
        )
    canonical.sort()

    node_by_id = {node.id: node for node in graph.nodes}
    for focus_id in canonical:
        if focus_id not in node_by_id:
            raise InvalidVisibilityOrder(
                f"Focus id {focus_id!r} is not a visible graph resource at "
                f"boundary {effective}."
            )

    inspector_timeline: list[TimelineItem] = []
    substituted: dict[str, str] = {}
    focus_ids_for_kept: list[str] = []
    for focus_id in canonical:
        node = node_by_id[focus_id]
        if node.type != "Event":
            focus_ids_for_kept.append(focus_id)
            continue
        event = event_by_id.get(focus_id)
        if event is None or event.tier == "major":
            focus_ids_for_kept.append(focus_id)
            continue

        major_events = sorted(
            (
                other
                for other_id, other in event_by_id.items()
                if other.tier == "major"
                and other.episode_id == event.episode_id
            ),
            key=lambda item: (item.visible_from_order, item.id),
        )
        inspector_timeline.append(
            to_timeline_item(event, node_by_id, effective)
        )
        if major_events:
            for major in major_events:
                if major.id not in focus_ids_for_kept:
                    focus_ids_for_kept.append(major.id)
                substituted.setdefault(focus_id, major.id)
        else:
            focus_ids_for_kept.append(focus_id)

    focus_set = set(focus_ids_for_kept)
    neighbor_ids: set[str] = set()
    for edge in graph.edges:
        if edge.type in OMITTED_EDGE_TYPES:
            continue
        if edge.source in focus_set and edge.target in node_by_id:
            neighbor_ids.add(edge.target)
        if edge.target in focus_set and edge.source in node_by_id:
            neighbor_ids.add(edge.source)

    kept_ids: list[str] = list(dict.fromkeys(focus_ids_for_kept))
    kept_ids.extend(sorted(neighbor_ids - focus_set))
    kept_ids = kept_ids[:GRAPHRAG_FOCUS_MAX_NODES]
    kept_set = set(kept_ids)
    focus_set = set(canonical)
    core_focus = focus_set | set(substituted.values())

    nodes = [
        project_node(
            node_by_id[nid],
            node_by_id[nid].type,
            DISPLAY_TIER_CORE if nid in core_focus else DISPLAY_TIER_SUPPORTING,
        )
        for nid in kept_ids
    ]
    edges = project_narrative_edges(graph, kept_set)

    primary = next(
        (fid for fid in canonical if fid in kept_set),
        next(
            (
                substituted[fid]
                for fid in canonical
                if fid in substituted and substituted[fid] in kept_set
            ),
            kept_ids[0],
        ),
    )

    return VisualizationDTO(
        metadata=build_metadata(graph, GRAPHRAG_FOCUS_VIEW_TYPE),
        nodes=nodes,
        edges=edges,
        groups=[],
        timeline=inspector_timeline,
        focus=VisualizationFocus(node_id=primary),
    )
