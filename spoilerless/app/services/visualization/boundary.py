"""Boundary resolution, safety gates, metadata building, and timeline item mapping."""

from __future__ import annotations

from spoilerless.app.domain.graph import GraphNode, GraphResponse
from spoilerless.app.domain.visualization import (
    PROJECTION_VERSION,
    SafeEventContext,
    TimelineItem,
    VisualizationMetadata,
)
from spoilerless.app.services.visualization.constants import EVENT_TIER_DISPLAY_TIER
from spoilerless.app.spoiler.policy import (
    InvalidVisibilityOrder,
    is_visible,
    resolve_effective_boundary,
    validate_visibility_order,
)


def resolve_boundary(
    requested_view_order: int | None,
    watched_through_order: int | None,
    view_as_of_order: int | None = None,
) -> int:
    """Shared D-05 resolver (``policy.resolve_effective_boundary``)."""
    return resolve_effective_boundary(
        requested_view_order,
        watched_through_order,
        view_as_of_order=view_as_of_order,
    )


def validate_safe_graph(graph: GraphResponse) -> tuple[int, int]:
    """D-05/T10-LEAK-02 gate shared by every projection.

    Returns ``(served, effective)`` after refusing an inconsistent
    boundary (effective above served) and ANY hidden node/edge row.
    """
    served = graph.visible_until_order
    effective = graph.effective_view_order
    validate_visibility_order(served)
    validate_visibility_order(effective)

    if effective > resolve_effective_boundary(
        served, served, view_as_of_order=served
    ):
        raise InvalidVisibilityOrder(
            f"Effective view order {effective} exceeds the served boundary "
            f"{served}; refusing to project (D-05 min rule)."
        )

    for row in [*graph.nodes, *graph.edges]:
        if not is_visible(row, effective):
            raise InvalidVisibilityOrder(
                f"Hidden row {row.id!r} cannot be projected at boundary {effective}."
            )
    return served, effective


def build_metadata(graph: GraphResponse, view_type: str) -> VisualizationMetadata:
    """Build the versioned metadata block for a projection (T10-CACHE-02)."""
    return VisualizationMetadata(
        projection_version=PROJECTION_VERSION,
        view_type=view_type,
        series_id=graph.series.id,
        series_title=graph.series.title,
        episode_order=graph.visible_until_order,
        visible_until_order=graph.visible_until_order,
        effective_view_order=graph.effective_view_order,
    )


def validate_events(
    events: list[SafeEventContext] | None, effective: int
) -> dict[str, SafeEventContext]:
    """Validate safe editorial event metadata and return the id-keyed map."""
    event_by_id: dict[str, SafeEventContext] = {}
    for event in events or []:
        if event.id in event_by_id:
            raise ValueError(f"Duplicate event metadata id {event.id!r}.")
        event_by_id[event.id] = event
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


def to_timeline_item(
    event: SafeEventContext,
    node_by_id: dict[str, GraphNode],
    effective: int,
) -> TimelineItem:
    """Build one timeline entry with bounded, visible-only metadata."""
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
        episode_order=episode_node.visible_from_order,
        order=event.visible_from_order,
        display_tier=EVENT_TIER_DISPLAY_TIER[event.tier],
        participant_ids=participants,
        location_id=location_id,
        location_label=location_label,
    )
