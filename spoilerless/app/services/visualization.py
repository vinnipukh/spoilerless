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
    CHARACTER_NETWORK_VIEW_TYPE,
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EPISODE_OVERVIEW_MAX_EDGES,
    EPISODE_OVERVIEW_MAX_NODES,
    EPISODE_OVERVIEW_VIEW_TYPE,
    FULL_VIEW_TYPE,
    GRAPHRAG_FOCUS_MAX_IDS,
    GRAPHRAG_FOCUS_MAX_NODES,
    GRAPHRAG_FOCUS_VIEW_TYPE,
    INVESTIGATION_VIEW_TYPE,
    PLOT_THREADS_VIEW_TYPE,
    PROJECTION_VERSION,
    SafeEventContext,
    SafePlotThread,
    TimelineItem,
    VisualizationDTO,
    VisualizationEdge,
    VisualizationFocus,
    VisualizationGroup,
    VisualizationMetadata,
    VisualizationNode,
    VIEW_TYPES,
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

# D-14: the ``full`` view (D-11 Advanced mode) maps the participation family
# to human wording too — raw Neo4j relation names never serialize in ANY
# normal DTO. The Episode Overview keeps omitting these edge families
# (D-13); this extended vocabulary is used only by the ``full`` projection.
FULL_EDGE_CLASSES: dict[str, str] = {
    **HUMAN_EDGE_CLASSES,
    "PARTICIPATED_IN": "participated_in",
    "OCCURRED_IN": "occurred_in",
    "LOCATED_IN": "located_in",
    "WITNESSED": "witnessed",
    "CAUSED": "caused",
    "AFFECTED": "affected",
    "TARGETED": "targeted",
    "MENTIONED": "mentioned",
}

# D-15 claim-status tiers for the ``investigation`` view (D-28 layered
# Claim/Evidence/Source path): the safest editorial classification available
# at the visible boundary. Unknown statuses FAIL CLOSED.
_CLAIM_STATUS_DISPLAY_TIER = {
    "canonical": DISPLAY_TIER_CORE,
    "corroborated": DISPLAY_TIER_SUPPORTING,
    "candidate": DISPLAY_TIER_DETAIL,
}

# Investigation-layer edge wording (D-28/D-41): claims are supported by
# evidence fragments, which are sourced from sources. The claim reference
# rides the edge so evidence resolution stays inside the safe payload
# (GraphRAG-independent source detail, D-04).
SUPPORTED_BY_EDGE_CLASS = "supported_by"
FROM_SOURCE_EDGE_CLASS = "from_source"


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

    @staticmethod
    def _validate_safe_graph(graph: GraphResponse) -> tuple[int, int]:
        """D-05/T10-LEAK-02 gate shared by every projection.

        Returns ``(served, effective)`` after refusing an inconsistent
        boundary (effective above served) and ANY hidden node/edge row —
        hidden rows are rejected, never silently dropped (a hidden row that
        "disappears" from a projection would still be an indirect leak).
        """
        served = graph.visible_until_order
        effective = graph.effective_view_order
        validate_visibility_order(served)
        validate_visibility_order(effective)

        # D-05 resolver-before-projection: the effective boundary is
        # min(requested, watched) via the shared resolver — it can never
        # exceed the served/requested order. A response whose effective
        # boundary is above its served boundary violates the resolver
        # contract and is refused before any row is projected.
        if effective > resolve_effective_boundary(
            served, served, view_as_of_order=served
        ):
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
        return served, effective

    @staticmethod
    def _metadata(graph: GraphResponse, view_type: str) -> VisualizationMetadata:
        """Build the versioned metadata block for a projection (T10-CACHE-02).

        ``episode_order`` is the served order (the current episode for a
        bounded view read), ``visible_until_order`` the served boundary, and
        ``effective_view_order`` the D-05 clamped boundary — the three values
        any cache key must round-trip.
        """
        return VisualizationMetadata(
            projection_version=PROJECTION_VERSION,
            view_type=view_type,
            series_id=graph.series.id,
            series_title=graph.series.title,
            episode_order=graph.visible_until_order,
            visible_until_order=graph.visible_until_order,
            effective_view_order=graph.effective_view_order,
        )

    @staticmethod
    def _node(
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

    def _narrative_edges(
        self,
        graph: GraphResponse,
        kept_ids: set[str],
        edge_classes: dict[str, str] = HUMAN_EDGE_CLASSES,
        omit: frozenset[str] = OMITTED_EDGE_TYPES,
    ) -> list[VisualizationEdge]:
        """Project edges between kept nodes as human semantic classes.

        Raw Neo4j relation names never serialize (D-14): every edge type is
        mapped to human wording and any unmapped type raises (fail closed).
        Edges with an endpoint outside the kept set are omitted — endpoint
        selection is the view's node-reduction decision, never a hidden-row
        drop (rows were already validated safe by ``_validate_safe_graph``).
        """
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

    @staticmethod
    def _validate_events(
        events: list[SafeEventContext] | None, effective: int
    ) -> dict[str, SafeEventContext]:
        """Validate safe editorial event metadata (dup ids, fail-closed
        visibility) and return the id-keyed map.``"""
        event_by_id: dict[str, SafeEventContext] = {}
        for event in events or []:
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
        return event_by_id

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
        served, effective = self._validate_safe_graph(graph)
        event_by_id = self._validate_events(events, effective)

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
            kept_nodes.append(self._node(node, node.type, tier))
            kept_ids.add(node.id)

        # --- Edges (narrative classes only, endpoints kept) ---
        kept_edges = self._narrative_edges(graph, kept_ids)

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
            metadata=self._metadata(graph, EPISODE_OVERVIEW_VIEW_TYPE),
            nodes=kept_nodes,
            edges=kept_edges,
            groups=[],
            timeline=timeline,
            focus=None,
        )

    def project_character_network(self, graph: GraphResponse) -> VisualizationDTO:
        """Project the character network (D-17 Characters tab).

        Characters only: every visible Character is a node; edges are the
        narrative classes (family/work/knows/trusts/...) between characters.
        Participation and occurrence edges stay omitted (D-13); the timeline
        is empty — this view answers "who is connected to whom", not "what
        happened". No auto-communities are ever derived (D-36).
        """
        served, effective = self._validate_safe_graph(graph)

        kept_nodes = [
            self._node(node, "Character", DISPLAY_TIER_CORE)
            for node in graph.nodes
            if node.type == "Character"
        ]
        kept_ids = {node.id for node in kept_nodes}
        kept_edges = self._narrative_edges(graph, kept_ids)

        return VisualizationDTO(
            metadata=self._metadata(graph, CHARACTER_NETWORK_VIEW_TYPE),
            nodes=kept_nodes,
            edges=kept_edges,
            groups=[],
            timeline=[],
            focus=None,
        )

    def project_plot_threads(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
        threads: list[SafePlotThread] | None = None,
    ) -> VisualizationDTO:
        """Project the plot-thread story view (D-36/D-38).

        Characters, containers, and every declared safe event (any tier) are
        nodes; narrative edges connect them; the timeline carries every safe
        event (D-38). ``threads`` are the editorial plot-thread groups: a
        thread member outside the kept/visible node set FAILS CLOSED (never
        guessed or dropped), and no future member totals ever appear. Without
        editorial thread data the view still projects the safe payload in
        plot-thread shape with empty groups — thread membership is an
        editorial input, not a graph-derived community.
        """
        events = list(events) if events is not None else []
        served, effective = self._validate_safe_graph(graph)
        event_by_id = self._validate_events(events, effective)

        node_by_id = {node.id: node for node in graph.nodes}

        kept_nodes: list[VisualizationNode] = []
        kept_ids: set[str] = set()
        for node in graph.nodes:
            if node.type in _CONTAINER_KINDS:
                tier = DISPLAY_TIER_SUPPORTING
            elif node.type == "Character":
                tier = DISPLAY_TIER_CORE
            elif node.type == "Event":
                event = event_by_id.get(node.id)
                if event is None:
                    continue
                tier = _EVENT_TIER_DISPLAY_TIER[event.tier]
            else:
                continue
            kept_nodes.append(self._node(node, node.type, tier))
            kept_ids.add(node.id)

        kept_edges = self._narrative_edges(graph, kept_ids)

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
            self._to_timeline_item(event, node_by_id, effective)
            for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
        ]

        return VisualizationDTO(
            metadata=self._metadata(graph, PLOT_THREADS_VIEW_TYPE),
            nodes=kept_nodes,
            edges=kept_edges,
            groups=groups,
            timeline=timeline,
            focus=None,
        )

    def project_investigation(self, graph: GraphResponse) -> VisualizationDTO:
        """Project the layered Investigation view (D-28/D-41).

        "Why do we know this?" — a dedicated Claim/Evidence/Source layer that
        never appears on the main story graph: one Claim node per visible
        claim, one Evidence node per referenced safe evidence fragment, one
        Source node per referenced safe source, with ``supported_by`` claim→
        evidence and ``from_source`` evidence→source edges. A claim referencing
        evidence outside the safe payload, an evidence referencing a missing
        source, or an unknown claim status FAILS CLOSED (the projection never
        guesses provenance). Timeline/groups stay empty — this is a layered
        path, not a story timeline.
        """
        served, effective = self._validate_safe_graph(graph)
        # The investigation layer additionally consumes claim/evidence/source
        # rows: every one of them must be visible at the effective boundary.
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
                tier = _CLAIM_STATUS_DISPLAY_TIER[claim.status]
            except KeyError:
                raise ValueError(
                    f"Claim {claim.id!r} has unknown status {claim.status!r}; "
                    "refusing to classify investigation detail (D-15)."
                ) from None
            nodes.append(self._node(claim, "Claim", tier))
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
                self._node(evidence, "Evidence", DISPLAY_TIER_DETAIL)
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
            nodes.append(self._node(source, "Source", DISPLAY_TIER_DETAIL))

        return VisualizationDTO(
            metadata=self._metadata(graph, INVESTIGATION_VIEW_TYPE),
            nodes=nodes,
            edges=edges,
            groups=[],
            timeline=[],
            focus=None,
        )

    def project_full(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
    ) -> VisualizationDTO:
        """Project the complete safe graph (D-11 Advanced/full mode).

        Every safe node (all kinds) and every safe edge, mapped to human
        semantic classes including the participation family (D-14). No D-09
        caps apply — full mode is the explicit deep-exploration view, never
        the default. Timeline carries every declared safe event.
        """
        events = list(events) if events is not None else []
        served, effective = self._validate_safe_graph(graph)
        event_by_id = self._validate_events(events, effective)

        kept_nodes: list[VisualizationNode] = []
        for node in graph.nodes:
            if node.type == "Character":
                tier = DISPLAY_TIER_CORE
            elif node.type == "Event":
                event = event_by_id.get(node.id)
                # Undeclared events still appear in full mode (the complete
                # graph is the point); without editorial context the least
                # assuming safe tier is detail (3).
                tier = (
                    _EVENT_TIER_DISPLAY_TIER[event.tier]
                    if event is not None
                    else DISPLAY_TIER_DETAIL
                )
            else:
                tier = DISPLAY_TIER_SUPPORTING
            kept_nodes.append(self._node(node, node.type, tier))

        kept_ids = {node.id for node in kept_nodes}
        kept_edges = self._narrative_edges(
            graph, kept_ids, edge_classes=FULL_EDGE_CLASSES, omit=frozenset()
        )

        node_by_id = {node.id: node for node in graph.nodes}
        timeline = [
            self._to_timeline_item(event, node_by_id, effective)
            for event in sorted(events, key=lambda e: (e.visible_from_order, e.id))
        ]

        return VisualizationDTO(
            metadata=self._metadata(graph, FULL_VIEW_TYPE),
            nodes=kept_nodes,
            edges=kept_edges,
            groups=[],
            timeline=timeline,
            focus=None,
        )

    def project_graphrag_focus(
        self,
        graph: GraphResponse,
        focus_ids: list[str] | None = None,
    ) -> VisualizationDTO:
        """Project the bounded GraphRAG Answer Graph (D-26/D-27/D-48).

        Focus ids are validated (non-empty), deduplicated, and lexically
        sorted; every focus node must exist and be visible in the safe payload
        (hidden and unknown are indistinguishable and both fail closed,
        T10-FOCUS-02). The projection keeps the focus nodes plus their visible
        narrative neighbors, deterministically bounded to
        ``GRAPHRAG_FOCUS_MAX_NODES`` (D-27: 5-20 visual elements). The DTO
        ``focus`` field references the primary focus node (first in canonical
        order) — a focus reference always resolves inside the DTO.
        """
        served, effective = self._validate_safe_graph(graph)
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
                # Hidden and unknown are indistinguishable by design — the
                # route maps this to a sanitized 422 INVALID_REQUEST.
                raise InvalidVisibilityOrder(
                    f"Focus id {focus_id!r} is not a visible graph resource at "
                    f"boundary {effective}."
                )

        # Visible narrative neighbors (both endpoints visible; participation
        # family excluded — the Answer Graph highlights relationships, D-26).
        neighbor_ids: set[str] = set()
        for edge in graph.edges:
            if edge.type in OMITTED_EDGE_TYPES:
                continue
            if edge.source in seen and edge.target in node_by_id:
                neighbor_ids.add(edge.target)
            if edge.target in seen and edge.source in node_by_id:
                neighbor_ids.add(edge.source)

        kept_ids: list[str] = list(canonical)
        kept_ids.extend(sorted(neighbor_ids - set(canonical)))
        # D-27 bound: focus nodes always survive; neighbors are truncated
        # deterministically (stable id order), never randomly.
        kept_ids = kept_ids[:GRAPHRAG_FOCUS_MAX_NODES]
        kept_set = set(kept_ids)
        focus_set = set(canonical)

        nodes = [
            self._node(
                node_by_id[nid],
                node_by_id[nid].type,
                DISPLAY_TIER_CORE if nid in focus_set else DISPLAY_TIER_SUPPORTING,
            )
            for nid in kept_ids
        ]
        edges = self._narrative_edges(graph, kept_set)

        return VisualizationDTO(
            metadata=self._metadata(graph, GRAPHRAG_FOCUS_VIEW_TYPE),
            nodes=nodes,
            edges=edges,
            groups=[],
            timeline=[],
            focus=VisualizationFocus(node_id=canonical[0]),
        )

    def project_view(
        self,
        graph: GraphResponse,
        view_type: str,
        events: list[SafeEventContext] | None = None,
        threads: list[SafePlotThread] | None = None,
        focus_ids: list[str] | None = None,
    ) -> VisualizationDTO:
        """Typed dispatch for every D-29 visualization view.

        Each branch is a concrete projection with its own nodes/edges/groups/
        timeline/focus semantics — dispatch-only stubs are never acceptable.
        An unknown view type is refused (fail closed) so the route's enum and
        the service vocabulary cannot drift apart.
        """
        if view_type == EPISODE_OVERVIEW_VIEW_TYPE:
            return self.project_episode_overview(graph, events)
        if view_type == CHARACTER_NETWORK_VIEW_TYPE:
            return self.project_character_network(graph)
        if view_type == PLOT_THREADS_VIEW_TYPE:
            return self.project_plot_threads(graph, events, threads)
        if view_type == INVESTIGATION_VIEW_TYPE:
            return self.project_investigation(graph)
        if view_type == FULL_VIEW_TYPE:
            return self.project_full(graph, events)
        if view_type == GRAPHRAG_FOCUS_VIEW_TYPE:
            return self.project_graphrag_focus(graph, focus_ids)
        raise ValueError(f"Unknown visualization view type {view_type!r}.")

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
