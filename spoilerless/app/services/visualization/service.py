"""Library-neutral visualization projections service facade."""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphNode, GraphResponse
from spoilerless.app.domain.visualization import (
    CHARACTER_NETWORK_VIEW_TYPE,
    EPISODE_OVERVIEW_VIEW_TYPE,
    EXPANSION_DEFAULT_LIMIT,
    FULL_VIEW_TYPE,
    GRAPHRAG_FOCUS_VIEW_TYPE,
    INVESTIGATION_VIEW_TYPE,
    PLOT_THREADS_VIEW_TYPE,
    SafeEventContext,
    SafePlotThread,
    TimelineItem,
    VisualizationDTO,
    VisualizationEdge,
    VisualizationMetadata,
    VisualizationNode,
)
from spoilerless.app.services.visualization.boundary import (
    build_metadata,
    resolve_boundary,
    to_timeline_item,
    validate_events,
    validate_safe_graph,
)
from spoilerless.app.services.visualization.constants import (
    HUMAN_EDGE_CLASSES,
    OMITTED_EDGE_TYPES,
)
from spoilerless.app.services.visualization.expansion import project_expansion
from spoilerless.app.services.visualization.focus import project_graphrag_focus
from spoilerless.app.services.visualization.node_builders import (
    project_narrative_edges,
    project_node,
)
from spoilerless.app.services.visualization.views import (
    project_character_network,
    project_episode_overview,
    project_full,
    project_investigation,
    project_plot_threads,
)


class VisualizationProjectionService:
    """Produces library-neutral visualization DTOs over safe graph detail."""

    def resolve_boundary(
        self,
        requested_view_order: int | None,
        watched_through_order: int | None,
        view_as_of_order: int | None = None,
    ) -> int:
        """Shared D-05 resolver (``policy.resolve_effective_boundary``)."""
        return resolve_boundary(
            requested_view_order,
            watched_through_order,
            view_as_of_order=view_as_of_order,
        )

    @staticmethod
    def _validate_safe_graph(graph: GraphResponse) -> tuple[int, int]:
        """D-05/T10-LEAK-02 gate shared by every projection."""
        return validate_safe_graph(graph)

    @staticmethod
    def _metadata(graph: GraphResponse, view_type: str) -> VisualizationMetadata:
        """Build the versioned metadata block for a projection (T10-CACHE-02)."""
        return build_metadata(graph, view_type)

    @staticmethod
    def _node(
        node: GraphNode, kind: str, tier: int, *, order: int | None = None
    ) -> VisualizationNode:
        """Project one safe graph node into the neutral shape."""
        return project_node(node, kind, tier, order=order)

    def _narrative_edges(
        self,
        graph: GraphResponse,
        kept_ids: set[str],
        edge_classes: dict[str, str] = HUMAN_EDGE_CLASSES,
        omit: frozenset[str] = OMITTED_EDGE_TYPES,
    ) -> list[VisualizationEdge]:
        """Project edges between kept nodes as human semantic classes."""
        return project_narrative_edges(graph, kept_ids, edge_classes=edge_classes, omit=omit)

    @staticmethod
    def _validate_events(
        events: list[SafeEventContext] | None, effective: int
    ) -> dict[str, SafeEventContext]:
        """Validate safe editorial event metadata."""
        return validate_events(events, effective)

    def project_episode_overview(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
    ) -> VisualizationDTO:
        """Project the D-10 Variant A Episode Overview from a safe response."""
        return project_episode_overview(graph, events=events)

    def project_character_network(self, graph: GraphResponse) -> VisualizationDTO:
        """Project the character network (D-17 Characters tab)."""
        return project_character_network(graph)

    def project_plot_threads(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
        threads: list[SafePlotThread] | None = None,
    ) -> VisualizationDTO:
        """Project the plot-thread story view (D-36/D-38)."""
        return project_plot_threads(graph, events=events, threads=threads)

    def project_investigation(self, graph: GraphResponse) -> VisualizationDTO:
        """Project the layered Investigation view (D-28/D-41)."""
        return project_investigation(graph)

    def project_full(
        self,
        graph: GraphResponse,
        events: list[SafeEventContext] | None = None,
    ) -> VisualizationDTO:
        """Project the complete safe graph (D-11 Advanced/full mode)."""
        return project_full(graph, events=events)

    def project_graphrag_focus(
        self,
        graph: GraphResponse,
        focus_ids: list[str] | None = None,
        events: list[SafeEventContext] | None = None,
    ) -> VisualizationDTO:
        """Project the bounded GraphRAG Answer Graph (D-26/D-27/D-48)."""
        return project_graphrag_focus(graph, focus_ids=focus_ids, events=events)

    def project_view(
        self,
        graph: GraphResponse,
        view_type: str,
        events: list[SafeEventContext] | None = None,
        threads: list[SafePlotThread] | None = None,
        focus_ids: list[str] | None = None,
    ) -> VisualizationDTO:
        """Typed dispatch for every D-29 visualization view."""
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
            return self.project_graphrag_focus(graph, focus_ids, events)
        raise ValueError(f"Unknown visualization view type {view_type!r}.")

    def project_expansion(
        self,
        graph: GraphResponse,
        node_id: str,
        expansion_key: str,
        limit: int = EXPANSION_DEFAULT_LIMIT,
    ) -> VisualizationDTO:
        """Project one allowlisted semantic expansion as a DTO delta (D-21)."""
        return project_expansion(graph, node_id, expansion_key, limit=limit)

    @staticmethod
    def _to_timeline_item(
        event: SafeEventContext,
        node_by_id: dict[str, GraphNode],
        effective: int,
    ) -> TimelineItem:
        """Build one timeline entry with bounded, visible-only metadata."""
        return to_timeline_item(event, node_by_id, effective)
