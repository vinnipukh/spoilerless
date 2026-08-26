"""Library-neutral visualization DTOs (D-08).

These models are the backend presentation contract for the Phase 10
narrative-visualization redesign: versioned, library-neutral (no Cytoscape or
rendering-library types), and safe by construction. They are produced ONLY
from complete spoiler-safe graph detail (``GraphResponse``) by
``spoilerless/app/services/visualization.py`` — never from hidden rows and
never by the frontend (D-04/D-05).

Safety contract (threat model T10-LEAK-02 / T10-BOUND-02 / T10-CACHE-02 /
T10-FOCUS-02):

- ``projection_version`` + ``effective_view_order`` ride on every DTO
  (``VisualizationMetadata``) so a cached DTO can never cross a boundary or
  projection version (T10-CACHE-02). No cache is introduced here.
- Raw Neo4j relation names never appear; edges carry human semantic classes
  (D-14). Hidden totals, degrees, group counts, and restoration hints are
  absent by construction (D-06).
- ``focus`` (optional) may only reference a node present in the DTO —
  hidden focus IDs are rejected before serialization (T10-FOCUS-02).
- Reference closure is enforced at validation: dangling edges, group members
  that are not in the DTO, and focus IDs outside the node set all fail
  validation.

The DTO mirrors the D-08 shape exactly: ``metadata``, ``nodes``, ``edges``,
``groups``, ``timeline``, ``focus``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from spoilerless.app.domain.user_content import Origin

# D-10 / 10-01 decision log: Variant A (characters + major Events) is the
# production Episode Overview default at projection version 1.0.0. This value
# MUST stay in sync with the checked-in safe fixtures' ``projection_version``
# metadata (enforced by the projection contract tests).
PROJECTION_VERSION = "1.0.0"

EPISODE_OVERVIEW_VIEW_TYPE = "episode_overview"
CHARACTER_NETWORK_VIEW_TYPE = "character_network"
PLOT_THREADS_VIEW_TYPE = "plot_threads"
INVESTIGATION_VIEW_TYPE = "investigation"
FULL_VIEW_TYPE = "full"
GRAPHRAG_FOCUS_VIEW_TYPE = "graphrag_focus"

# D-29: the exact view vocabulary of
# ``GET /api/series/{series_id}/graph/visualization``.
VIEW_TYPES: tuple[str, ...] = (
    EPISODE_OVERVIEW_VIEW_TYPE,
    CHARACTER_NETWORK_VIEW_TYPE,
    PLOT_THREADS_VIEW_TYPE,
    INVESTIGATION_VIEW_TYPE,
    FULL_VIEW_TYPE,
    GRAPHRAG_FOCUS_VIEW_TYPE,
)

# D-29: repeated ``focus_id`` values are accepted only for ``graphrag_focus``
# and capped at 20 distinct ids after canonicalization (dedupe + sort).
GRAPHRAG_FOCUS_MAX_IDS = 20

# D-27: the Answer Graph targets 5-20 visual elements; this is the hard node
# cap for the ``graphrag_focus`` projection (focus nodes + visible narrative
# neighbors, deterministically bounded).
GRAPHRAG_FOCUS_MAX_NODES = 20

# D-21: the exact allowlisted expansion-key vocabulary of
# ``GET /api/series/{series_id}/graph/expand``. No arbitrary relation or
# concept input is ever accepted (T10-BOUND-06).
EXPANSION_KEY_FAMILY = "family"
EXPANSION_KEY_WORK = "work"
EXPANSION_KEY_CONFLICT = "conflict"
EXPANSION_KEY_EPISODE_EVENTS = "episode_events"
EXPANSION_KEY_CLUES = "clues"
EXPANSION_KEY_LOCATIONS = "locations"
EXPANSION_KEY_EVIDENCE = "evidence"

EXPANSION_KEYS: tuple[str, ...] = (
    EXPANSION_KEY_FAMILY,
    EXPANSION_KEY_WORK,
    EXPANSION_KEY_CONFLICT,
    EXPANSION_KEY_EPISODE_EVENTS,
    EXPANSION_KEY_CLUES,
    EXPANSION_KEY_LOCATIONS,
    EXPANSION_KEY_EVIDENCE,
)

# D-29: the exact view vocabulary of the visualization route. ``Literal``
# keeps the OpenAPI enum and the route's runtime validation in lockstep.
VisualizationView = Literal[
    "episode_overview",
    "character_network",
    "plot_threads",
    "investigation",
    "full",
    "graphrag_focus",
]

# D-21: the exact allowlisted expansion-key vocabulary of the expansion
# route. ``Literal`` keeps the OpenAPI enum and the route's runtime validation
# in lockstep.
ExpansionKey = Literal[
    "family",
    "work",
    "conflict",
    "episode_events",
    "clues",
    "locations",
    "evidence",
]

# D-21 bounds: expansions prefer 8-12 additions with a hard max of 25 — no
# request and no server result may ever exceed it (T10-BOUND-06).
EXPANSION_DEFAULT_LIMIT = 12
EXPANSION_MAX_LIMIT = 25

# D-21: an expansion delta carries its key in ``metadata.view_type`` under
# this prefix, so a delta is always distinguishable from a view projection
# and can never collide with the D-29 view vocabulary.
EXPANSION_VIEW_TYPE_PREFIX = "expansion:"

# D-15 display tiers: 1 core, 2 supporting, 3 detail. Classification is valid
# only at the resource's visible boundary; the projection derives it from
# safe-boundary editorial data (event tier), never from full-graph degree.
DISPLAY_TIER_CORE = 1
DISPLAY_TIER_SUPPORTING = 2
DISPLAY_TIER_DETAIL = 3

# D-09 hard caps for the bounded Episode Overview. The 12-28 node target is a
# design goal (sparse episodes are legitimate, D-44); these are the
# enforceable hard bounds.
EPISODE_OVERVIEW_MAX_NODES = 40
EPISODE_OVERVIEW_MAX_EDGES = 60


class VisualizationMetadata(BaseModel):
    """Versioned read context carried by every DTO (T10-CACHE-02)."""

    projection_version: str
    view_type: str
    series_id: str
    series_title: str
    episode_order: int = Field(ge=1)
    visible_until_order: int = Field(ge=1)
    effective_view_order: int = Field(ge=1)


class VisualizationNode(BaseModel):
    """One safe graph node in a neutral presentation shape.

    ``kind`` carries the domain node type (``Character``, ``Event``, ...) —
    the same vocabulary the existing frontend adapter already understands.
    ``order`` is the safe reveal/publication order (D-35): authoritative for
    ordering, never a display band invented from hidden data.
    """

    id: str
    kind: str
    label: str
    display_tier: int = Field(ge=DISPLAY_TIER_CORE, le=DISPLAY_TIER_DETAIL)
    order: int = Field(ge=1)
    episode_id: str | None = None
    image_url: str | None = None
    image_source_url: str | None = None
    origin: Origin | None = None


class VisualizationEdge(BaseModel):
    """One narrative edge with a human semantic class (D-14).

    Raw Neo4j relation names are never serialized; ``relation_class`` is the
    human wording the frontend label policy consumes. ``claim_id`` is the
    safe evidence reference (resolvable within the same safe payload —
    GraphRAG-independent source detail, D-04).
    """

    id: str
    source: str
    target: str
    relation_class: str
    order: int = Field(ge=1)
    claim_id: str | None = None
    origin: Origin | None = None


class VisualizationGroup(BaseModel):
    """Editorial plot-thread group (D-36).

    Membership lists VISIBLE node ids only and carries no count/total field —
    the count is derivable from the visible membership and nothing else. No
    future member totals ever appear.
    """

    id: str
    label: str
    node_ids: list[str] = Field(default_factory=list)


class TimelineItem(BaseModel):
    """One first-class timeline entry (D-38), ordered by reveal order.

    ``participant_ids`` and ``location_*`` are bounded event metadata: only
    entities visible at the effective boundary may appear (participants and
    locations that are not in the safe node set are dropped by the
    projection, never guessed).
    """

    id: str
    kind: Literal["event"] = "event"
    label: str
    episode_id: str
    episode_order: int = Field(ge=1)
    order: int = Field(ge=1)
    display_tier: int = Field(ge=DISPLAY_TIER_CORE, le=DISPLAY_TIER_DETAIL)
    participant_ids: list[str] = Field(default_factory=list)
    location_id: str | None = None
    location_label: str | None = None


class VisualizationFocus(BaseModel):
    """Optional focus reference (T10-FOCUS-02).

    A focus may only name a node present in the DTO; the DTO validator
    rejects hidden/unknown focus IDs before serialization.
    """

    node_id: str


class SafePlotThread(BaseModel):
    """Spoiler-safe editorial plot-thread group input (D-36).

    Plot threads are editorial story concepts, never automatic graph
    communities. Membership lists node ids that MUST be visible at the
    effective boundary — the projection refuses a hidden/unknown reference
    (fail closed) and never exposes future member totals.
    """

    id: str
    label: str
    node_ids: list[str] = Field(default_factory=list)


class VisualizationDTO(BaseModel):
    """The neutral, library-neutral visualization contract (D-08).

    Top-level shape is exactly ``metadata`` / ``nodes`` / ``edges`` /
    ``groups`` / ``timeline`` / ``focus`` so the frontend owns the Cytoscape
    and timeline adapters and the cache plan keys on metadata.
    """

    metadata: VisualizationMetadata
    nodes: list[VisualizationNode] = Field(default_factory=list)
    edges: list[VisualizationEdge] = Field(default_factory=list)
    groups: list[VisualizationGroup] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    focus: VisualizationFocus | None = None

    @model_validator(mode="after")
    def enforce_dto_references(self) -> "VisualizationDTO":
        """Reference closure + fail-closed focus contract.

        Mirrors ``GraphResponse.enforce_graph_closure``: dangling edges,
        group members outside the node set, and focus IDs outside the node
        set are rejected at validation time.
        """
        node_ids = {node.id for node in self.nodes}
        dangling = [
            edge.id
            for edge in self.edges
            if edge.source not in node_ids or edge.target not in node_ids
        ]
        if dangling:
            raise ValueError(
                f"Visualization DTO contains dangling edges: {', '.join(sorted(dangling))}"
            )
        for group in self.groups:
            unknown = [node_id for node_id in group.node_ids if node_id not in node_ids]
            if unknown:
                raise ValueError(
                    f"Group {group.id!r} references nodes outside the DTO: "
                    f"{', '.join(sorted(unknown))}"
                )
        if self.focus is not None and self.focus.node_id not in node_ids:
            raise ValueError(
                f"Focus references a node outside the DTO: {self.focus.node_id!r}."
            )
        return self


class SafeEventContext(BaseModel):
    """Spoiler-safe editorial event metadata consumed by projections (D-12).

    This is the safe-boundary editorial input that rides the same safe
    payload pipeline as the graph: tier (major/supporting/micro),
    participants, and location. A null/absent ``visible_from_order`` is
    HIDDEN — the projection refuses it (fail closed, D-03), never defaulting
    an event to visible.
    """

    id: str
    label: str
    episode_id: str
    tier: Literal["major", "supporting", "micro"]
    participant_ids: list[str] = Field(default_factory=list)
    location_id: str | None = None
    visible_from_order: int | None = Field(default=None, ge=1)
