"""Library-neutral visualization projections (D-04/D-08).

Consumes ONLY complete safe graph detail (``GraphResponse``) plus the safe
editorial event context that rides the same safe payload pipeline. The
projection is a read-only, bounded presentation reduction over already-safe
rows: it never deletes or narrows GraphRAG retrieval detail (D-04), and the
complete safe ``GraphResponse`` remains the canonical read contract for
GraphRAG and Advanced/full mode.

Boundary-before-projection (D-05): every row consumed must be visible at the
response's effective boundary, and an effective order above the served
boundary is refused before any row is projected. Hidden rows are rejected,
never silently dropped — a hidden row that "disappears" from a projection
would still be an indirect leak vector; rejecting the payload makes the
contract executable.
"""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphNode, GraphResponse
from spoilerless.app.domain.visualization import (
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EPISODE_OVERVIEW_MAX_EDGES,
    EPISODE_OVERVIEW_MAX_NODES,
    EPISODE_OVERVIEW_VIEW_TYPE,
    PROJECTION_VERSION,
    SafeEventContext,
    TimelineItem,
    VisualizationDTO,
    VisualizationEdge,
    VisualizationMetadata,
    VisualizationNode,
)
from spoilerless.app.spoiler.policy import (
    InvalidVisibilityOrder,
    is_visible,
    resolve_effective_boundary,
    validate_visibility_order,
)

# D-13: Episode Overview omits participation/occurrence/location edges; they
# surface as timeline metadata, avatars/chips, or Inspector detail instead.
# The participation family (WITNESSED/CAUSED/AFFECTED/TARGETED/MENTIONED) is
# omitted the same way: participation is event metadata, never in-graph edges.
OMITTED_EDGE_TYPES = frozenset(
    {
        "PARTICIPATED_IN",
        "OCCURRED_IN",
        "LOCATED_IN",
        "WITNESSED",
        "CAUSED",
        "AFFECTED",
        "TARGETED",
        "MENTIONED",
    }
)

# D-14: raw Neo4j relation names stay hidden outside explicit debug mode; the
# Episode Overview carries human semantic edge classes only. Every mapped
# type is a narrative/structural edge with human wording; any unmapped type
# FAILS CLOSED (the projection never invents a label for an unknown
# relationship).
HUMAN_EDGE_CLASSES: dict[str, str] = {
    "PART_OF": "part_of",
    "PRECEDES": "precedes",
    "KNOWS": "knows",
    "FAMILY_OF": "family",
    "WORKS_WITH": "work",
    "TRUSTS": "trusts",
    "DISTRUSTS": "distrusts",
    "HELPS": "helps",
    "OPPOSES": "opposes",
    "THREATENS": "threatens",
    "ATTACKS": "attacks",
    "KILLS": "kills",
}

# D-10: Variant A keeps characters plus major Events; Episode/Series
# containers stay as structural context. Locations/Objects/Organizations are
# Inspector/timeline metadata, not Episode Overview nodes (D-13).
_KEPT_NODE_KINDS = frozenset({"Series", "Episode", "Character"})
_CONTAINER_KINDS = frozenset({"Series", "Episode"})

# D-12: major/supporting/micro event tiers map to D-15 display tiers.
_EVENT_TIER_DISPLAY_TIER = {
    "major": DISPLAY_TIER_CORE,
    "supporting": DISPLAY_TIER_SUPPORTING,
    "micro": DISPLAY_TIER_DETAIL,
}


class VisualizationProjectionService:
    """Produces library-neutral visualization DTOs over safe graph detail."""

    def resolve_boundary(
        self,
        requested_view_order: int | None,
        watched_through_order: int | None,
        view_as_of_order: int | None = None,
    ) -> int:
        """Shared D-05 resolver (``policy.resolve_effective_boundary``).

        Every projection read path — graph, projection, expansion-ready
        contracts, path/search/focus/restoration inputs — computes
        ``min(requested_view_order, watched_progress)`` through this one
        function and fails closed when progress is absent (boundary 1).
        """
        return resolve_effective_boundary(
            requested_view_order,
            watched_through_order,
            view_as_of_order=view_as_of_order,
        )

    def project_episode_overview(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
    ) -> VisualizationDTO:
        """Project the D-10 Variant A Episode Overview from a safe response.

        :param graph: complete safe ``GraphResponse`` — the ONLY graph input.
            Every consumed row must be visible at ``graph.effective_view_order``
            (fail closed, T10-LEAK-02).
        :param events: safe editorial event metadata bound to the same
            boundary (default: no event metadata — all events are omitted).
        :raises InvalidVisibilityOrder: a hidden/missing-visibility row or an
            inconsistent boundary (effective order above the served order).
        :raises ValueError: an unmapped technical edge type (D-14) or a D-09
            hard-cap breach.
        """
        events = list(events) if events is not None else []
        served = graph.visible_until_order
        effective = graph.effective_view_order
        validate_visibility_order(served)
        validate_visibility_order(effective)

        # D-05 resolver-before-projection: the effective boundary is
        # min(requested, watched) via the shared resolver — it can never
        # exceed the served/requested order. A response whose effective
        # boundary is above its served boundary violates the resolver
        # contract and is refused before any row is projected.
        if effective > self.resolve_boundary(served, served, view_as_of_order=served):
            raise InvalidVisibilityOrder(
                f"Effective view order {effective} exceeds the served boundary "
                f"{served}; refusing to project (D-05 min rule)."
            )

        # T10-LEAK-02: fail closed on ANY hidden row. Hidden rows must never
        # reach the projection — rejecting the payload (rather than skipping
        # the row) keeps the contract executable.
        for row in [*graph.nodes, *graph.edges]:
            if not is_visible(row, effective):
                raise InvalidVisibilityOrder(
                    f"Hidden row {row.id!r} cannot be projected at boundary {effective}."
                )

        event_by_id: dict[str, SafeEventContext] = {}
        for event in events:
            if event.id in event_by_id:
                raise ValueError(f"Duplicate event metadata id {event.id!r}.")
            event_by_id[event.id] = event
            # Missing visibility fails closed (D-03) — never defaulted visible.
            if event.visible_from_order is None:
                raise InvalidVisibilityOrder(
                    f"Event {event.id!r} has no visibility order; refusing to "
                    "project hidden metadata."
                )
            if event.visible_from_order > effective:
                raise InvalidVisibilityOrder(
                    f"Event {event.id!r} is not visible at boundary {effective}."
                )

        node_by_id = {node.id: node for node in graph.nodes}

        # --- Nodes (Variant A: characters + major Events + containers) ---
        kept_nodes: list[VisualizationNode] = []
        kept_ids: set[str] = set()
        for node in graph.nodes:
            if node.type in _KEPT_NODE_KINDS:
                tier = (
                    DISPLAY_TIER_SUPPORTING
                    if node.type in _CONTAINER_KINDS
                    else DISPLAY_TIER_CORE
                )
            elif node.type == "Event":
                event = event_by_id.get(node.id)
                # Fail closed: only events explicitly declared major are drawn
                # in-graph; supporting/micro and undeclared events are
                # timeline-only (Variant A, D-10/D-12).
                if event is None or event.tier != "major":
                    continue
                tier = DISPLAY_TIER_CORE
            else:
                # Locations/Objects/Organizations: metadata surfaces, not
                # Episode Overview nodes (D-13).
                continue
            kept_nodes.append(
                VisualizationNode(
                    id=node.id,
                    kind=node.type,
                    label=node.label,
                    display_tier=tier,
                    order=node.visible_from_order,
                    episode_id=node.episode_id,
                    image_url=node.image_url,
                    image_source_url=node.image_source_url,
                    origin=node.origin,
                )
            )
            kept_ids.add(node.id)

        # --- Edges (narrative classes only, endpoints kept) ---
        kept_edges: list[VisualizationEdge] = []
        for edge in graph.edges:
            if edge.type in OMITTED_EDGE_TYPES:
                continue
            try:
                relation_class = HUMAN_EDGE_CLASSES[edge.type]
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

        # --- Timeline (all safe events, reveal/publication order, D-35/D-38) ---
        timeline = [
            self._to_timeline_item(event, node_by_id, effective)
            for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
        ]

        # D-09 hard caps: the bounded Episode Overview refuses to serialize an
        # unbounded projection (Full Graph remains Advanced, D-11).
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
            metadata=VisualizationMetadata(
                projection_version=PROJECTION_VERSION,
                view_type=EPISODE_OVERVIEW_VIEW_TYPE,
                series_id=graph.series.id,
                series_title=graph.series.title,
                # The served boundary IS the current episode for an
                # episode_overview read.
                episode_order=served,
                visible_until_order=served,
                effective_view_order=effective,
            ),
            nodes=kept_nodes,
            edges=kept_edges,
            groups=[],
            timeline=timeline,
            focus=None,
        )

    @staticmethod
    def _to_timeline_item(
        event: SafeEventContext,
        node_by_id: dict[str, GraphNode],
        effective: int,
    ) -> TimelineItem:
        """Build one timeline entry with bounded, visible-only metadata.

        Participants and location are dropped (never guessed) when they are
        not in the safe node set — hidden/future entities cannot influence
        the timeline.
        """
        episode_node = node_by_id.get(event.episode_id)
        if episode_node is None or episode_node.type != "Episode":
            raise InvalidVisibilityOrder(
                f"Event {event.id!r} references unknown episode {event.episode_id!r}."
            )
        participants = [pid for pid in event.participant_ids if pid in node_by_id]
        location_id = event.location_id if event.location_id in node_by_id else None
        location_label = (
            node_by_id[location_id].label if location_id is not None else None
        )
        return TimelineItem(
            id=event.id,
            label=event.label,
            episode_id=event.episode_id,
            # The Episode node's reveal order IS its publication order in the
            # safe payload (deterministic; no hidden ordering data).
            episode_order=episode_node.visible_from_order,
            order=event.visible_from_order,
            display_tier=_EVENT_TIER_DISPLAY_TIER[event.tier],
            participant_ids=participants,
            location_id=location_id,
            location_label=location_label,
        )
