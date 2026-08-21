"""Semantic expansion delta projections (D-21/D-22)."""

from __future__ import annotations

from spoilerless.app.domain.graph import (
    GraphClaim,
    GraphEvidence,
    GraphNode,
    GraphResponse,
    GraphSource,
)
from spoilerless.app.domain.visualization import (
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EXPANSION_DEFAULT_LIMIT,
    EXPANSION_KEY_CLUES,
    EXPANSION_KEY_EPISODE_EVENTS,
    EXPANSION_KEY_EVIDENCE,
    EXPANSION_KEY_LOCATIONS,
    EXPANSION_KEYS,
    EXPANSION_MAX_LIMIT,
    EXPANSION_VIEW_TYPE_PREFIX,
    VisualizationDTO,
    VisualizationEdge,
    VisualizationNode,
)
from spoilerless.app.services.visualization.boundary import (
    build_metadata,
    validate_safe_graph,
)
from spoilerless.app.services.visualization.constants import (
    CLAIM_STATUS_DISPLAY_TIER,
    EXPANSION_EDGE_TYPES,
    EXPANSION_NEIGHBOR_KEYS,
    FROM_SOURCE_EDGE_CLASS,
    FULL_EDGE_CLASSES,
    SUPPORTED_BY_EDGE_CLASS,
)
from spoilerless.app.services.visualization.node_builders import project_node
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder, is_visible


def project_expansion(
    graph: GraphResponse,
    node_id: str,
    expansion_key: str,
    limit: int = EXPANSION_DEFAULT_LIMIT,
) -> VisualizationDTO:
    """Project one allowlisted semantic expansion as a DTO delta (D-21)."""
    if expansion_key not in EXPANSION_KEYS:
        raise ValueError(f"Unknown expansion key {expansion_key!r}.")
    if not isinstance(node_id, str) or not node_id:
        raise InvalidVisibilityOrder("node_id must be a non-empty resource id.")
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError(f"limit must be an integer in 1..{EXPANSION_MAX_LIMIT}.")
    if not 1 <= limit <= EXPANSION_MAX_LIMIT:
        raise ValueError(
            f"limit must be within 1..{EXPANSION_MAX_LIMIT}, got {limit}."
        )

    served, effective = validate_safe_graph(graph)

    node_by_id = {node.id: node for node in graph.nodes}
    anchor = node_by_id.get(node_id)
    if anchor is None:
        raise InvalidVisibilityOrder(
            f"Node {node_id!r} is not a visible graph resource at "
            f"boundary {effective}."
        )

    additions_by_id: dict[str, GraphNode] = {}
    investigation_order: dict[str, int] = {}
    claim_refs: list = []

    if expansion_key in EXPANSION_NEIGHBOR_KEYS:
        edge_types = EXPANSION_EDGE_TYPES[expansion_key]
        for edge in graph.edges:
            if edge.type not in edge_types:
                continue
            other_id = None
            if edge.source == node_id:
                other_id = edge.target
            elif edge.target == node_id:
                other_id = edge.source
            if other_id is None:
                continue
            other = node_by_id.get(other_id)
            if other is not None and other.type == "Character":
                additions_by_id[other_id] = other

    elif expansion_key == EXPANSION_KEY_LOCATIONS:
        edge_types = EXPANSION_EDGE_TYPES[EXPANSION_KEY_LOCATIONS]
        for edge in graph.edges:
            if edge.type not in edge_types:
                continue
            other_id = None
            if edge.source == node_id:
                other_id = edge.target
            elif edge.target == node_id:
                other_id = edge.source
            if other_id is None:
                continue
            other = node_by_id.get(other_id)
            if other is not None and other.type == "Location":
                additions_by_id[other_id] = other

    elif expansion_key == EXPANSION_KEY_EPISODE_EVENTS:
        if anchor.type != "Episode":
            raise InvalidVisibilityOrder(
                f"episode_events requires an Episode anchor; {node_id!r} "
                f"is a {anchor.type}."
            )
        for node in graph.nodes:
            if node.type == "Event" and node.episode_id == node_id:
                additions_by_id[node.id] = node

    elif expansion_key in (EXPANSION_KEY_CLUES, EXPANSION_KEY_EVIDENCE):
        for claim in graph.claims:
            if claim.subject_id == node_id or claim.object_id == node_id:
                if not is_visible(claim, effective):
                    raise InvalidVisibilityOrder(
                        f"Hidden claim {claim.id!r} cannot be expanded at "
                        f"boundary {effective}."
                    )
                claim_refs.append(claim)
        evidence_by_id = {item.id: item for item in graph.evidence}
        sources_by_id = {item.id: item for item in graph.sources}
        for claim in claim_refs:
            if expansion_key == EXPANSION_KEY_CLUES:
                additions_by_id[claim.id] = claim
                investigation_order[claim.id] = claim.visible_from_order
            for evidence_id in claim.evidence_ids:
                evidence = evidence_by_id.get(evidence_id)
                if evidence is None:
                    raise ValueError(
                        f"Claim {claim.id!r} references evidence "
                        f"{evidence_id!r} outside the safe payload "
                        "(fail closed, D-04)."
                    )
                if not is_visible(evidence, effective):
                    raise InvalidVisibilityOrder(
                        f"Hidden evidence {evidence.id!r} cannot be "
                        f"expanded at boundary {effective}."
                    )
                additions_by_id[evidence.id] = evidence
                investigation_order[evidence.id] = evidence.visible_from_order
                if expansion_key == EXPANSION_KEY_EVIDENCE:
                    source = sources_by_id.get(evidence.source_id)
                    if source is None:
                        raise ValueError(
                            f"Evidence {evidence.id!r} references source "
                            f"{evidence.source_id!r} outside the safe "
                            "payload (fail closed, D-04)."
                        )
                    if not is_visible(source, effective):
                        raise InvalidVisibilityOrder(
                            f"Hidden source {source.id!r} cannot be "
                            f"expanded at boundary {effective}."
                        )
                    additions_by_id[source.id] = source
                    investigation_order[source.id] = source.visible_from_order

    def _addition_sort_key(nid: str) -> tuple[int, str]:
        node = node_by_id.get(nid)
        if node is not None:
            return (node.visible_from_order, nid)
        return (investigation_order[nid], nid)

    addition_ids = sorted(additions_by_id.keys(), key=_addition_sort_key)[:limit]
    kept_ids: set[str] = {node_id}
    kept_ids.update(addition_ids)

    nodes: list[VisualizationNode] = [project_node(anchor, anchor.type, DISPLAY_TIER_CORE)]
    for nid in addition_ids:
        node = additions_by_id[nid]
        if isinstance(node, GraphClaim):
            kind = "Claim"
            try:
                tier = CLAIM_STATUS_DISPLAY_TIER[node.status]
            except KeyError:
                raise ValueError(
                    f"Claim {node.id!r} has unknown status "
                    f"{node.status!r}; refusing to classify expansion "
                    "detail (D-15)."
                ) from None
        elif isinstance(node, GraphEvidence):
            kind = "Evidence"
            tier = DISPLAY_TIER_DETAIL
        elif isinstance(node, GraphSource):
            kind = "Source"
            tier = DISPLAY_TIER_DETAIL
        else:
            kind = node.type
            tier = (
                DISPLAY_TIER_CORE
                if node.type == "Character"
                else DISPLAY_TIER_SUPPORTING
            )
        nodes.append(project_node(node, kind, tier))

    edges: list[VisualizationEdge] = []
    restricted = EXPANSION_EDGE_TYPES.get(expansion_key)
    for edge in graph.edges:
        if edge.source not in kept_ids or edge.target not in kept_ids:
            continue
        if restricted is not None and edge.type not in restricted:
            continue
        try:
            relation_class = FULL_EDGE_CLASSES[edge.type]
        except KeyError:
            raise ValueError(
                f"Unmapped relationship type {edge.type!r}: refusing to "
                "expose a raw technical edge label (D-14)."
            ) from None
        edges.append(
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

    if expansion_key == EXPANSION_KEY_CLUES:
        for claim in claim_refs:
            if claim.id not in kept_ids:
                continue
            for evidence_id in claim.evidence_ids:
                if evidence_id not in kept_ids:
                    continue
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
    elif expansion_key == EXPANSION_KEY_EVIDENCE:
        for evidence in [additions_by_id[nid] for nid in addition_ids]:
            if not isinstance(evidence, GraphEvidence):
                continue
            source_id = evidence.source_id
            if source_id not in kept_ids:
                continue
            edges.append(
                VisualizationEdge(
                    id=f"{evidence.id}:from_source:{source_id}",
                    source=evidence.id,
                    target=source_id,
                    relation_class=FROM_SOURCE_EDGE_CLASS,
                    order=evidence.visible_from_order,
                    claim_id=None,
                    origin=evidence.origin,
                )
            )
    edges.sort(key=lambda edge: edge.id)

    return VisualizationDTO(
        metadata=build_metadata(
            graph, f"{EXPANSION_VIEW_TYPE_PREFIX}{expansion_key}"
        ),
        nodes=nodes,
        edges=edges,
        groups=[],
        timeline=[],
        focus=None,
    )
