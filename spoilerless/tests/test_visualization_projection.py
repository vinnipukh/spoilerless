"""Phase 10-02 Task 1 contract tests: neutral VisualizationDTO + projection.

Covers the library-neutral DTO contract (D-08) and the production
``episode_overview`` projection (D-10 Variant A) over the checked-in safe
fixtures from plan 10-01:

- exact DTO shape, stable IDs, deterministic output
- 0 / 1 / many payloads
- schema validation and reference closure
- omission of PARTICIPATED_IN/OCCURRED_IN (and the participation family)
- human semantic edge classes only — no raw Neo4j relation names
- GraphRAG-independent source detail (claim refs resolve inside the safe
  payload; the projection never touches retrieval/evidence rows)

Safety contract (T10-LEAK-02 / T10-BOUND-02 / T10-CACHE-02 / T10-FOCUS-02):
hidden rows, missing visibility, inconsistent boundaries, and focus IDs
outside the DTO are rejected; the DTO carries the effective order +
projection version contract. No live Neo4j, no LLM, no retrieval calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from spoilerless.app.api.deps import get_optional_current_user
from spoilerless.app.api.exceptions import install_repository_error_handlers
from spoilerless.app.api.graph import (
    get_graph_service,
    get_progress_service,
    router as graph_router,
)
import spoilerless.app.api.graph as graph_api_module
from spoilerless.app.cache import graph_cache
from spoilerless.app.core.errors import (
    install_database_error_handlers,
    install_error_handlers,
)
from spoilerless.app.domain.graph import (
    GraphClaim,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphResponse,
    GraphSource,
)
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.domain.visualization import (
    CHARACTER_NETWORK_VIEW_TYPE,
    DISPLAY_TIER_CORE,
    DISPLAY_TIER_DETAIL,
    DISPLAY_TIER_SUPPORTING,
    EPISODE_OVERVIEW_MAX_EDGES,
    EPISODE_OVERVIEW_MAX_NODES,
    EPISODE_OVERVIEW_VIEW_TYPE,
    EXPANSION_KEYS,
    EXPANSION_MAX_LIMIT,
    EXPANSION_VIEW_TYPE_PREFIX,
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
    VisualizationFocus,
    VisualizationGroup,
    VisualizationNode,
)
from spoilerless.app.services.visualization import (
    FULL_EDGE_CLASSES,
    HUMAN_EDGE_CLASSES,
    OMITTED_EDGE_TYPES,
    VisualizationProjectionService,
)
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visualization"

service = VisualizationProjectionService()

# Raw Neo4j relation names that must NEVER appear in a normal DTO (D-14).
_RAW_RELATION_NAMES = (
    "PARTICIPATED_IN",
    "OCCURRED_IN",
    "LOCATED_IN",
    "WITNESSED",
    "CAUSED",
    "AFFECTED",
    "TARGETED",
    "MENTIONED",
    "PART_OF",
    "PRECEDES",
    "WORKS_WITH",
    "FAMILY_OF",
    "KNOWS",
    "TRUSTS",
    "DISTRUSTS",
    "HELPS",
    "OPPOSES",
    "THREATENS",
    "ATTACKS",
    "KILLS",
)

# T10-FOCUS-01 / D-06 vocabulary that must not appear as DTO keys.
_FORBIDDEN_DTO_KEYS = ("hidden", "count", "total", "degree", "restoration")


# ---------------------------------------------------------------------------
# Fixture helpers (checked-in safe baselines only)
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> tuple[GraphResponse, list[SafeEventContext]]:
    """Load a checked-in safe fixture into (GraphResponse, SafeEventContexts)."""
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    graph = GraphResponse.model_validate(fixture["graph"])
    events = [SafeEventContext.model_validate(event) for event in fixture.get("events", [])]
    return graph, events


def _project(name: str) -> VisualizationDTO:
    graph, events = _load_fixture(name)
    return service.project_episode_overview(graph, events)


# ---------------------------------------------------------------------------
# Exact DTO shape on the safe fixtures (Variant A, D-10)
# ---------------------------------------------------------------------------


def test_episode_overview_s01e01_exact_shape() -> None:
    """S01E01: 9 nodes / 4 edges / 1 timeline item / no focus / no groups."""
    dto = _project("s01e01_safe.json")
    assert dto.metadata.projection_version == PROJECTION_VERSION == "1.0.0"
    assert dto.metadata.view_type == EPISODE_OVERVIEW_VIEW_TYPE
    assert dto.metadata.series_id == "series_dexter"
    assert dto.metadata.series_title == "Dexter"
    assert dto.metadata.episode_order == 1
    assert dto.metadata.visible_until_order == 1
    assert dto.metadata.effective_view_order == 1

    assert [node.id for node in dto.nodes] == [
        "series_dexter",
        "dexter_s01e01",
        "char_dexter_morgan",
        "char_debra_morgan",
        "char_james_doakes",
        "char_rita_bennett",
        "char_angel_batista",
        "char_ice_truck_killer",
        "event_first_kill",
    ]
    assert {node.kind for node in dto.nodes} == {
        "Series",
        "Episode",
        "Character",
        "Event",
    }
    # D-13: locations are metadata surfaces, not overview nodes.
    assert not any(node.kind == "Location" for node in dto.nodes)

    assert {edge.id for edge in dto.edges} == {
        "edge_1",
        "edge_3",
        "edge_4",
        "user-rel:test-1",
    }
    assert {edge.relation_class for edge in dto.edges} == {
        "part_of",
        "work",
        "family",
        "knows",
    }

    assert dto.groups == []
    assert dto.focus is None
    assert [item.id for item in dto.timeline] == ["event_first_kill"]
    item = dto.timeline[0]
    assert item.kind == "event"
    assert item.episode_id == "dexter_s01e01"
    assert item.episode_order == 1
    assert item.order == 1
    assert item.display_tier == DISPLAY_TIER_CORE
    assert item.participant_ids == ["char_dexter_morgan"]
    assert item.location_id is None
    assert item.location_label is None


def test_episode_overview_s01e02_cumulative_exact_shape() -> None:
    """Cumulative S01E02: 13 nodes / 7 edges / 2 timeline items (Variant A)."""
    dto = _project("s01e02_cumulative_safe.json")
    assert dto.metadata.episode_order == 2
    assert dto.metadata.effective_view_order == 2
    assert len(dto.nodes) == 13
    assert len(dto.edges) == 7
    assert {edge.id for edge in dto.edges} == {
        "edge_1",
        "edge_2",
        "edge_3",
        "edge_5",
        "edge_6",
        "edge_9",
        "user-rel:test-1",
    }
    # Human semantic classes only; WORKS_WITH -> "work", FAMILY_OF -> "family",
    # PRECEDES -> "precedes", PART_OF -> "part_of", KNOWS -> "knows".
    assert {edge.relation_class for edge in dto.edges} == {
        "part_of",
        "precedes",
        "work",
        "family",
        "knows",
    }
    # edge_12 (WORKS_WITH with a location endpoint) is dropped: its endpoint
    # loc_miami_metro is not kept in the overview (matches the 10-01 measured
    # Variant A: 7 edges).
    assert "edge_12" not in {edge.id for edge in dto.edges}

    # Timeline ordered by reveal/publication order (D-35/D-38).
    assert [item.id for item in dto.timeline] == [
        "event_first_kill",
        "event_croc_discovery",
    ]
    croc = dto.timeline[1]
    assert croc.episode_id == "dexter_s01e02"
    assert croc.episode_order == 2
    assert croc.order == 2
    assert croc.participant_ids == ["char_vince_masuka"]
    assert croc.location_id == "loc_everglades"
    assert croc.location_label == "Everglades crime scene"


def test_node_display_tiers_and_orders_preserved() -> None:
    """D-15 tiers + D-35 reveal orders ride the DTO unchanged."""
    dto = _project("s01e02_cumulative_safe.json")
    by_id = {node.id: node for node in dto.nodes}
    # Characters are core (1), containers supporting (2), major events core (1).
    assert by_id["char_dexter_morgan"].display_tier == DISPLAY_TIER_CORE
    assert by_id["char_vince_masuka"].display_tier == DISPLAY_TIER_CORE
    assert by_id["series_dexter"].display_tier == DISPLAY_TIER_SUPPORTING
    assert by_id["dexter_s01e01"].display_tier == DISPLAY_TIER_SUPPORTING
    assert by_id["event_first_kill"].display_tier == DISPLAY_TIER_CORE
    # Reveal/publication orders are preserved exactly.
    assert by_id["char_vince_masuka"].order == 2
    assert by_id["char_dexter_morgan"].order == 1
    assert by_id["dexter_s01e02"].order == 2
    # Episode-safe image fields pass through for visible rows only.
    assert by_id["char_dexter_morgan"].image_url.startswith("https://")
    assert by_id["char_dexter_morgan"].episode_id == "dexter_s01e01"


# ---------------------------------------------------------------------------
# Omission of technical edges + no raw relation names (D-13/D-14)
# ---------------------------------------------------------------------------


def test_participation_and_occurrence_edges_omitted() -> None:
    """OCCURRED_IN / PARTICIPATED_IN / LOCATED_IN + participation family are
    never projected as edges (D-13)."""
    for name in ("s01e01_safe.json", "s01e02_cumulative_safe.json"):
        graph, events = _load_fixture(name)
        raw_types = {edge.type for edge in graph.edges}
        assert OMITTED_EDGE_TYPES & raw_types, f"{name}: fixture must contain omitted types"
        dto = service.project_episode_overview(graph, events)
        projected_types = {edge.relation_class for edge in dto.edges}
        # Every projected edge maps to a human class; nothing technical leaks.
        assert projected_types <= set(HUMAN_EDGE_CLASSES.values())


def test_serialized_dto_contains_no_raw_relation_names() -> None:
    """D-14: raw Neo4j relation names never appear in the normal DTO JSON."""
    dto = _project("s01e02_cumulative_safe.json")
    serialized = json.dumps(dto.model_dump(mode="json"))
    for raw in _RAW_RELATION_NAMES:
        assert raw not in serialized, f"raw relation name {raw!r} leaked into the DTO"


def test_serialized_dto_has_no_hidden_technical_keys() -> None:
    """D-06: no hidden counts, degrees, totals, or restoration hints as keys."""
    dto = _project("s01e02_cumulative_safe.json")

    def _walk(obj: object, path: str = "") -> list[str]:
        found: list[str] = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                full = f"{path}.{key}" if path else key
                lowered = key.lower()
                if any(term in lowered for term in _FORBIDDEN_DTO_KEYS):
                    found.append(full)
                found.extend(_walk(value, full))
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                found.extend(_walk(item, f"{path}[{index}]"))
        return found

    forbidden = _walk(dto.model_dump(mode="json"))
    assert forbidden == [], f"forbidden DTO keys found: {forbidden}"


def test_unmapped_edge_type_fails_closed() -> None:
    """An unknown technical edge type is refused, never labeled by invention."""
    graph, events = _load_fixture("s01e01_safe.json")
    graph.edges.append(
        GraphEdge(
            id="edge_future_tech",
            source="char_dexter_morgan",
            target="char_debra_morgan",
            type="SOME_NEW_RELATION",
            visible_from_order=1,
            origin="canonical",
        )
    )
    with pytest.raises(ValueError, match="Unmapped relationship type"):
        service.project_episode_overview(graph, events)


# ---------------------------------------------------------------------------
# Stable IDs + determinism
# ---------------------------------------------------------------------------


def test_stable_ids_match_source_graph() -> None:
    """DTO node/edge ids are the source GraphResponse ids (selection/cache
    stability), and timeline ids are the safe event ids."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_episode_overview(graph, events)
    assert {node.id for node in dto.nodes} <= {node.id for node in graph.nodes}
    source_edges = {edge.id: edge for edge in graph.edges}
    dto_edge_ids = {edge.id for edge in dto.edges}
    assert dto_edge_ids <= set(source_edges)
    for edge_id in dto_edge_ids:
        source = source_edges[edge_id]
        # Id stability: DTO ids are the source ids, never re-minted.
        assert source.id == edge_id
        # Only non-omitted technical types may project at all.
        assert source.type not in OMITTED_EDGE_TYPES
    assert {item.id for item in dto.timeline} == {event.id for event in events}


def test_projection_is_deterministic() -> None:
    """Same safe payload -> byte-identical DTO (cache/version contract)."""
    first = _project("s01e02_cumulative_safe.json")
    second = _project("s01e02_cumulative_safe.json")
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_projection_does_not_mutate_inputs() -> None:
    """D-04: the projection is a pure reduction; source detail is unchanged."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    graph_before = graph.model_dump(mode="json")
    events_before = [event.model_dump(mode="json") for event in events]
    service.project_episode_overview(graph, events)
    assert graph.model_dump(mode="json") == graph_before
    assert [event.model_dump(mode="json") for event in events] == events_before


# ---------------------------------------------------------------------------
# 0 / 1 / many payloads (UI-SPEC zero/one/many contract)
# ---------------------------------------------------------------------------


def _empty_graph() -> GraphResponse:
    return GraphResponse(
        series=SeriesResponse(id="series_dexter", title="Dexter", slug="dexter"),
        visible_until_order=1,
        effective_view_order=1,
        nodes=[],
        edges=[],
        claims=[],
        sources=[],
        evidence=[],
    )


def test_zero_payload_produces_valid_empty_dto() -> None:
    """0 rows: the DTO stays valid and empty — never a hidden-total signal."""
    dto = service.project_episode_overview(_empty_graph())
    assert dto.nodes == []
    assert dto.edges == []
    assert dto.groups == []
    assert dto.timeline == []
    assert dto.focus is None
    assert dto.metadata.effective_view_order == 1
    assert dto.metadata.projection_version == PROJECTION_VERSION


def test_one_node_payload_produces_single_node_dto() -> None:
    """1 row: the single visible node projects with its safe metadata."""
    graph = _empty_graph()
    graph.nodes.append(
        GraphNode(
            id="char_dexter_morgan",
            type="Character",
            label="Dexter Morgan",
            visible_from_order=1,
            origin="canonical",
        )
    )
    dto = service.project_episode_overview(graph)
    assert [node.id for node in dto.nodes] == ["char_dexter_morgan"]
    assert dto.nodes[0].kind == "Character"
    assert dto.nodes[0].display_tier == DISPLAY_TIER_CORE
    assert dto.nodes[0].order == 1


def test_many_payload_projection_is_bounded() -> None:
    """The full fixture payloads stay inside the D-09 hard caps."""
    for name in ("s01e01_safe.json", "s01e02_cumulative_safe.json"):
        dto = _project(name)
        assert len(dto.nodes) <= EPISODE_OVERVIEW_MAX_NODES
        assert len(dto.edges) <= EPISODE_OVERVIEW_MAX_EDGES


def test_hard_caps_enforced() -> None:
    """D-09: the bounded overview refuses to serialize an unbounded payload."""
    graph = _empty_graph()
    graph.nodes.append(
        GraphNode(
            id="dexter_s01e01",
            type="Episode",
            label="S01E01",
            visible_from_order=1,
            origin="canonical",
        )
    )
    for index in range(EPISODE_OVERVIEW_MAX_NODES):  # 40 more => 41 total
        graph.nodes.append(
            GraphNode(
                id=f"char_{index}",
                type="Character",
                label=f"Character {index}",
                visible_from_order=1,
                origin="canonical",
            )
        )
    with pytest.raises(ValueError, match="hard node cap"):
        service.project_episode_overview(graph)

    # Edge cap: 40 nodes, 61 kept edges (all endpoints kept, all mapped).
    edge_graph = _empty_graph()
    edge_graph.nodes.append(
        GraphNode(
            id="series_dexter",
            type="Series",
            label="Dexter",
            visible_from_order=1,
            origin="canonical",
        )
    )
    for index in range(EPISODE_OVERVIEW_MAX_NODES - 1):
        edge_graph.nodes.append(
            GraphNode(
                id=f"char_{index}",
                type="Character",
                label=f"Character {index}",
                visible_from_order=1,
                origin="canonical",
            )
        )
    chars = [f"char_{index}" for index in range(EPISODE_OVERVIEW_MAX_NODES - 1)]
    edge_graph.edges.extend(
        GraphEdge(
            id=f"edge_{index}",
            source=chars[index % len(chars)],
            target=chars[(index + 1) % len(chars)],
            type="FAMILY_OF",
            visible_from_order=1,
            origin="canonical",
        )
        for index in range(EPISODE_OVERVIEW_MAX_EDGES + 1)
    )
    with pytest.raises(ValueError, match="hard edge cap"):
        service.project_episode_overview(edge_graph)


# ---------------------------------------------------------------------------
# Timeline tier semantics (D-12)
# ---------------------------------------------------------------------------


def test_supporting_and_micro_events_are_timeline_only() -> None:
    """Supporting/micro events never enter the graph; they surface on the
    timeline with their D-15 tier."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    events = [
        *events,
        SafeEventContext(
            id="event_supporting",
            label="Masuka tells a crime-scene joke",
            episode_id="dexter_s01e02",
            tier="supporting",
            participant_ids=["char_vince_masuka"],
            location_id="loc_miami_metro",
            visible_from_order=2,
        ),
        SafeEventContext(
            id="event_micro",
            label="Dexter checks his phone",
            episode_id="dexter_s01e02",
            tier="micro",
            participant_ids=["char_dexter_morgan"],
            location_id=None,
            visible_from_order=2,
        ),
    ]
    dto = service.project_episode_overview(graph, events)
    assert [node.id for node in dto.nodes if node.kind == "Event"] == [
        "event_first_kill",
        "event_croc_discovery",
    ]
    assert [item.id for item in dto.timeline] == [
        "event_first_kill",
        "event_croc_discovery",
        "event_micro",
        "event_supporting",
    ]
    by_id = {item.id: item for item in dto.timeline}
    assert by_id["event_supporting"].display_tier == DISPLAY_TIER_SUPPORTING
    assert by_id["event_supporting"].location_id == "loc_miami_metro"
    assert by_id["event_supporting"].location_label == "Miami Metro Police Department"
    assert by_id["event_micro"].display_tier == DISPLAY_TIER_DETAIL
    assert by_id["event_micro"].participant_ids == ["char_dexter_morgan"]


def test_event_without_editorial_context_is_omitted() -> None:
    """An Event node with no safe event metadata cannot be declared major —
    it is omitted from nodes and timeline (fail closed, no invented tier)."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    graph.nodes.append(
        GraphNode(
            id="event_undeclared",
            type="Event",
            label="An undeclared event",
            visible_from_order=2,
            origin="canonical",
        )
    )
    dto = service.project_episode_overview(graph, events)
    assert "event_undeclared" not in {node.id for node in dto.nodes}
    assert "event_undeclared" not in {item.id for item in dto.timeline}


# ---------------------------------------------------------------------------
# Schema validation + reference closure (Task 1 schema contract)
# ---------------------------------------------------------------------------


def test_dto_rejects_invalid_display_tier_and_orders() -> None:
    """Strict schema: tiers outside 1..3 and non-positive orders fail."""
    dto = _project("s01e01_safe.json")
    payload = dto.model_dump(mode="json")
    payload["nodes"][0]["display_tier"] = 4
    with pytest.raises(ValidationError):
        VisualizationDTO.model_validate(payload)
    payload = dto.model_dump(mode="json")
    payload["nodes"][0]["display_tier"] = 0
    with pytest.raises(ValidationError):
        VisualizationDTO.model_validate(payload)
    payload = dto.model_dump(mode="json")
    payload["nodes"][0]["order"] = 0
    with pytest.raises(ValidationError):
        VisualizationDTO.model_validate(payload)
    payload = dto.model_dump(mode="json")
    payload["metadata"]["effective_view_order"] = 0
    with pytest.raises(ValidationError):
        VisualizationDTO.model_validate(payload)


def test_dto_rejects_dangling_edges() -> None:
    """Reference closure mirrors GraphResponse.enforce_graph_closure."""
    dto = _project("s01e01_safe.json")
    payload = dto.model_dump(mode="json")
    payload["edges"][0]["source"] = "char_does_not_exist"
    with pytest.raises(ValidationError, match="dangling edges"):
        VisualizationDTO.model_validate(payload)


def test_dto_rejects_group_members_outside_node_set() -> None:
    """Groups may only reference visible DTO members (D-36)."""
    dto = _project("s01e01_safe.json")
    payload = dto.model_dump(mode="json")
    payload["groups"] = [
        {"id": "thread_family", "label": "Family", "node_ids": ["char_future_killer"]}
    ]
    with pytest.raises(ValidationError, match="outside the DTO"):
        VisualizationDTO.model_validate(payload)


def test_focus_contract_rejects_hidden_focus_id() -> None:
    """T10-FOCUS-02: a focus referencing a node outside the DTO is rejected
    at validation; a focus on a present node validates."""
    dto = _project("s01e01_safe.json")
    payload = dto.model_dump(mode="json")
    payload["focus"] = {"node_id": "char_future_killer"}
    with pytest.raises(ValidationError, match="outside the DTO"):
        VisualizationDTO.model_validate(payload)

    payload["focus"] = {"node_id": "char_dexter_morgan"}
    validated = VisualizationDTO.model_validate(payload)
    assert validated.focus == VisualizationFocus(node_id="char_dexter_morgan")


# ---------------------------------------------------------------------------
# GraphRAG-independent source detail (D-04)
# ---------------------------------------------------------------------------


def test_edge_evidence_refs_resolve_within_safe_payload() -> None:
    """claim_id refs on DTO edges resolve inside the safe claims payload —
    the projection's source detail never depends on a retrieval service."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_episode_overview(graph, events)
    claim_ids = {claim.id for claim in graph.claims}
    for edge in dto.edges:
        if edge.claim_id is not None:
            assert edge.claim_id in claim_ids, (
                f"edge {edge.id!r} references claim {edge.claim_id!r} outside the safe payload"
            )
    assert {edge.id for edge in dto.edges if edge.claim_id} == {
        "edge_5",
        "edge_6",
        "edge_9",
    }


def test_projection_ignores_evidence_and_source_rows() -> None:
    """GraphRAG independence: the DTO is byte-identical whether or not the
    safe response carries evidence/source rows — retrieval detail is never
    consumed or narrowed by the projection (D-04)."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    with_evidence = service.project_episode_overview(graph, events)

    stripped = graph.model_copy(
        update={
            "sources": [],
            "evidence": [],
            "claims": [
                GraphClaim(
                    id=claim.id,
                    label=claim.label,
                    subject_id=claim.subject_id,
                    predicate=claim.predicate,
                    object_id=claim.object_id,
                    claim_type=claim.claim_type,
                    status=claim.status,
                    confidence_level=claim.confidence_level,
                    relationship_effect=claim.relationship_effect,
                    visible_from_order=claim.visible_from_order,
                    valid_from_order=claim.valid_from_order,
                    valid_until_order=claim.valid_until_order,
                    source_id=claim.source_id,
                    evidence_ids=[],
                    origin=claim.origin,
                )
                for claim in graph.claims
            ],
        }
    )
    without_evidence = service.project_episode_overview(stripped, events)
    assert without_evidence.model_dump(mode="json") == with_evidence.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Boundary-before-projection (Task 1 gate; Task 2 adds the shared resolver)
# ---------------------------------------------------------------------------


def test_effective_boundary_above_served_order_is_refused() -> None:
    """D-05: an effective boundary above the served order violates the min
    rule and is refused before any row is projected."""
    graph, events = _load_fixture("s01e01_safe.json")
    graph.effective_view_order = 2
    with pytest.raises(InvalidVisibilityOrder, match="exceeds the served boundary"):
        service.project_episode_overview(graph, events)


# ---------------------------------------------------------------------------
# Task 2 — boundary-before-projection via the shared resolver (D-05/D-06)
# ---------------------------------------------------------------------------


def test_service_resolve_boundary_clamps_requested_to_watched() -> None:
    """The projection read path computes min(requested, watched) through the
    shared resolver (policy.resolve_effective_boundary), fail closed."""
    assert service.resolve_boundary(9, 3, view_as_of_order=3) == 3
    assert service.resolve_boundary(2, 5, view_as_of_order=2) == 2
    assert service.resolve_boundary(None, 5, view_as_of_order=5) == 5
    assert service.resolve_boundary(None, None, view_as_of_order=None) == 1
    assert service.resolve_boundary(9, None, view_as_of_order=None) == 1
    with pytest.raises(InvalidVisibilityOrder):
        service.resolve_boundary(0, 5, view_as_of_order=3)


def test_clamped_request_projects_safe_dto_metadata() -> None:
    """End-to-end boundary->projection: an unsafe requested order is clamped
    upstream (resolver), and the DTO carries the clamped effective order with
    no row above it — hidden data has no observable effect."""
    # Requested S01E09 while the reader has watched through S01E02: the
    # resolver clamps to 2, and the served response (as fetch_graph would
    # build it) carries effective 2.
    assert service.resolve_boundary(9, 2, view_as_of_order=2) == 2

    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_episode_overview(graph, events)
    assert dto.metadata.effective_view_order == 2
    assert dto.metadata.visible_until_order == 2
    for node in dto.nodes:
        assert node.order <= dto.metadata.effective_view_order
    for item in dto.timeline:
        assert item.order <= dto.metadata.effective_view_order


def test_hidden_node_rejected_before_projection() -> None:
    """T10-LEAK-02: a hidden node above the effective boundary is refused —
    it can never influence DTO shape, counts, or topology."""
    graph, events = _load_fixture("s01e01_safe.json")
    graph.nodes.append(
        GraphNode(
            id="char_future_killer",
            type="Character",
            label="A future character",
            visible_from_order=9,
            origin="canonical",
        )
    )
    with pytest.raises(InvalidVisibilityOrder, match="Hidden row"):
        service.project_episode_overview(graph, events)


def test_hidden_edge_rejected_before_projection() -> None:
    """A hidden edge is refused — hidden topology cannot influence the DTO."""
    graph, events = _load_fixture("s01e01_safe.json")
    graph.edges.append(
        GraphEdge(
            id="edge_future",
            source="char_dexter_morgan",
            target="char_debra_morgan",
            type="FAMILY_OF",
            visible_from_order=9,
            origin="canonical",
        )
    )
    with pytest.raises(InvalidVisibilityOrder, match="Hidden row"):
        service.project_episode_overview(graph, events)


def test_hidden_event_metadata_rejected() -> None:
    """Events above the boundary are refused — hidden events cannot shape
    the timeline or group membership."""
    graph, events = _load_fixture("s01e01_safe.json")
    events = [
        *events,
        SafeEventContext(
            id="event_future",
            label="Season finale twist",
            episode_id="dexter_s01e01",
            tier="major",
            participant_ids=["char_future_killer"],
            location_id=None,
            visible_from_order=9,
        ),
    ]
    with pytest.raises(InvalidVisibilityOrder, match="not visible at boundary"):
        service.project_episode_overview(graph, events)


def test_missing_event_visibility_fails_closed() -> None:
    """D-03: an event with no visibility order is HIDDEN — never defaulted
    visible — and the projection refuses it."""
    graph, events = _load_fixture("s01e01_safe.json")
    events = [
        *events,
        SafeEventContext(
            id="event_no_order",
            label="An event without a reveal point",
            episode_id="dexter_s01e01",
            tier="major",
            participant_ids=[],
            location_id=None,
            visible_from_order=None,
        ),
    ]
    with pytest.raises(InvalidVisibilityOrder, match="no visibility order"):
        service.project_episode_overview(graph, events)


def test_hidden_participants_and_location_cannot_influence_timeline() -> None:
    """D-06: participants/locations outside the safe node set are dropped —
    hidden names and places have no observable effect on the timeline."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    poisoned = [
        SafeEventContext(
            id=event.id,
            label=event.label,
            episode_id=event.episode_id,
            tier=event.tier,
            # Hidden participant appended to every event; hidden location only
            # where no valid location exists (a valid one is preserved).
            participant_ids=[*event.participant_ids, "char_future_killer"],
            location_id=event.location_id or "loc_future_warehouse",
            visible_from_order=event.visible_from_order,
        )
        for event in events
    ]
    clean_dto = service.project_episode_overview(graph, events)
    poisoned_dto = service.project_episode_overview(graph, poisoned)
    assert poisoned_dto.model_dump(mode="json") == clean_dto.model_dump(mode="json")
    for item in poisoned_dto.timeline:
        assert "char_future_killer" not in item.participant_ids
        assert item.location_id != "loc_future_warehouse"
    # The valid location still resolves on the timeline.
    croc = next(item for item in poisoned_dto.timeline if item.id == "event_croc_discovery")
    assert croc.location_id == "loc_everglades"


def test_hidden_claim_reference_cannot_leak() -> None:
    """Evidence refs stay bounded: a DTO edge may only reference claims that
    exist in the safe payload — no hidden source detail rides along."""
    graph, events = _load_fixture("s01e01_safe.json")
    dto = service.project_episode_overview(graph, events)
    claim_ids = {claim.id for claim in graph.claims}
    for edge in dto.edges:
        assert edge.claim_id is None or edge.claim_id in claim_ids
    # The projection never synthesizes claim refs for edges that have none.
    assert dto.edges[0].id == "edge_1"
    assert dto.edges[0].claim_id is None


# ---------------------------------------------------------------------------
# 10-03 Task 1: concrete semantics for the remaining D-29 views
# (character_network / plot_threads / investigation / full / graphrag_focus)
# ---------------------------------------------------------------------------


def test_character_network_projects_characters_only() -> None:
    """D-17: characters only; narrative edges between characters; no
    timeline, no groups, no focus."""
    graph, _events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_character_network(graph)

    assert dto.metadata.view_type == CHARACTER_NETWORK_VIEW_TYPE
    assert dto.metadata.effective_view_order == 2
    assert {node.kind for node in dto.nodes} == {"Character"}
    assert len(dto.nodes) == 8
    assert "char_dexter_morgan" in {node.id for node in dto.nodes}
    # Locations/Episodes/Events never enter the character network.
    assert not any(node.id.startswith("loc_") for node in dto.nodes)
    assert not any(node.id.startswith("dexter_s") for node in dto.nodes)

    # Narrative edges between characters only — the WORKS_WITH edge whose
    # endpoint is a Location (edge_12) is dropped by endpoint selection.
    assert {edge.id for edge in dto.edges} == {
        "edge_5",
        "edge_6",
        "edge_9",
        "user-rel:test-1",
    }
    assert {edge.relation_class for edge in dto.edges} == {
        "work",
        "family",
        "knows",
    }
    assert dto.groups == []
    assert dto.timeline == []
    assert dto.focus is None


def test_character_network_rejects_hidden_rows() -> None:
    """Boundary safety: a hidden character above the effective boundary is
    refused before projection (shared T10-LEAK-02 gate)."""
    graph, _events = _load_fixture("s01e01_safe.json")
    graph.nodes.append(
        GraphNode(
            id="char_future_killer",
            type="Character",
            label="A future character",
            visible_from_order=9,
            origin="canonical",
        )
    )
    with pytest.raises(InvalidVisibilityOrder, match="Hidden row"):
        service.project_character_network(graph)


def test_plot_threads_projects_events_groups_and_timeline() -> None:
    """D-36/D-38: containers + characters + every declared safe event; the
    timeline carries all events; editorial thread groups ride the DTO."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    threads = [
        SafePlotThread(
            id="thread_family",
            label="Morgan family",
            node_ids=["char_dexter_morgan", "char_debra_morgan"],
        ),
        SafePlotThread(
            id="thread_croc",
            label="Crocodile case",
            node_ids=["char_vince_masuka", "event_croc_discovery"],
        ),
    ]
    dto = service.project_plot_threads(graph, events, threads)

    assert dto.metadata.view_type == PLOT_THREADS_VIEW_TYPE
    # All events (any tier) appear as nodes in plot-thread shape.
    assert "event_first_kill" in {node.id for node in dto.nodes}
    assert "event_croc_discovery" in {node.id for node in dto.nodes}
    assert {node.kind for node in dto.nodes} >= {"Series", "Episode", "Character", "Event"}
    # Narrative edges with both endpoints kept.
    assert {edge.id for edge in dto.edges} == {
        "edge_1",
        "edge_2",
        "edge_3",
        "edge_5",
        "edge_6",
        "edge_9",
        "user-rel:test-1",
    }
    # Editorial groups, visible members only.
    assert [(g.id, g.node_ids) for g in dto.groups] == [
        ("thread_family", ["char_dexter_morgan", "char_debra_morgan"]),
        ("thread_croc", ["char_vince_masuka", "event_croc_discovery"]),
    ]
    # Timeline carries every safe event (D-38).
    assert [item.id for item in dto.timeline] == [
        "event_first_kill",
        "event_croc_discovery",
    ]
    assert dto.focus is None


def test_plot_threads_without_editorial_threads_projects_empty_groups() -> None:
    """No thread data: the view still projects in plot-thread shape with
    empty groups — membership is editorial input, never graph-derived."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_plot_threads(graph, events)
    assert dto.groups == []
    assert [item.id for item in dto.timeline] == [
        "event_first_kill",
        "event_croc_discovery",
    ]
    assert dto.metadata.view_type == PLOT_THREADS_VIEW_TYPE


def test_plot_threads_rejects_hidden_or_unknown_members() -> None:
    """D-36 fail closed: a thread referencing a node outside the visible
    kept set is refused — never guessed or dropped."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    threads = [
        SafePlotThread(
            id="thread_bad",
            label="Bad thread",
            node_ids=["char_dexter_morgan", "loc_future_warehouse"],
        )
    ]
    with pytest.raises(InvalidVisibilityOrder, match="outside the projected view"):
        service.project_plot_threads(graph, events, threads)


def test_investigation_projects_claim_evidence_source_layers() -> None:
    """D-28/D-41: one Claim node per visible claim, one Evidence node per
    referenced evidence fragment, one Source node per referenced source;
    supported_by / from_source edges only."""
    graph, _events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_investigation(graph)

    assert dto.metadata.view_type == INVESTIGATION_VIEW_TYPE
    assert {node.kind for node in dto.nodes} == {"Claim", "Evidence", "Source"}
    # 6 claims + 5 evidence + 2 sources.
    assert len(dto.nodes) == 13
    assert len([n for n in dto.nodes if n.kind == "Claim"]) == 6
    assert len([n for n in dto.nodes if n.kind == "Evidence"]) == 5
    assert len([n for n in dto.nodes if n.kind == "Source"]) == 2

    # One supported_by edge per claim->evidence reference; one from_source
    # edge per evidence->source reference.
    assert {edge.relation_class for edge in dto.edges} == {
        "supported_by",
        "from_source",
    }
    assert len([e for e in dto.edges if e.relation_class == "supported_by"]) == 6
    assert len([e for e in dto.edges if e.relation_class == "from_source"]) == 5
    # Every edge is a deterministic id derived from the safe refs.
    assert "claim_4:supported_by:evidence_1" in {e.id for e in dto.edges}
    assert "evidence_4:from_source:source_2" in {e.id for e in dto.edges}
    # Claim display tiers follow D-15 claim status.
    by_id = {node.id: node for node in dto.nodes}
    assert by_id["claim_1"].display_tier == DISPLAY_TIER_CORE  # canonical
    assert by_id["claim_2"].display_tier == DISPLAY_TIER_SUPPORTING  # corroborated
    assert by_id["claim_4"].display_tier == DISPLAY_TIER_DETAIL  # candidate
    assert dto.groups == []
    assert dto.timeline == []
    assert dto.focus is None


def test_investigation_fails_closed_on_missing_provenance() -> None:
    """D-04: a claim referencing evidence outside the safe payload is
    refused — the projection never guesses provenance."""
    graph, _events = _load_fixture("s01e01_safe.json")
    claim = graph.claims[0]
    graph.claims[0] = GraphClaim(
        id=claim.id,
        label=claim.label,
        subject_id=claim.subject_id,
        predicate=claim.predicate,
        object_id=claim.object_id,
        claim_type=claim.claim_type,
        status=claim.status,
        confidence_level=claim.confidence_level,
        relationship_effect=claim.relationship_effect,
        visible_from_order=claim.visible_from_order,
        valid_from_order=claim.valid_from_order,
        valid_until_order=claim.valid_until_order,
        source_id=claim.source_id,
        evidence_ids=["evidence_missing"],
        origin=claim.origin,
    )
    with pytest.raises(ValueError, match="outside the safe payload"):
        service.project_investigation(graph)


def test_full_projects_every_safe_node_and_edge() -> None:
    """D-11: the complete safe graph — every node kind and every edge
    (including the participation family) with human classes; no D-09 caps."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_full(graph, events)

    assert dto.metadata.view_type == FULL_VIEW_TYPE
    assert {node.id for node in dto.nodes} == {node.id for node in graph.nodes}
    assert {node.kind for node in dto.nodes} >= {
        "Series",
        "Episode",
        "Character",
        "Event",
        "Location",
    }
    # Every source edge projects, participation family included, mapped to
    # human wording (D-14).
    assert {edge.id for edge in dto.edges} == {edge.id for edge in graph.edges}
    assert "occurred_in" in {edge.relation_class for edge in dto.edges}
    assert {edge.relation_class for edge in dto.edges} <= set(FULL_EDGE_CLASSES.values())
    # Timeline still carries the safe editorial events.
    assert [item.id for item in dto.timeline] == [
        "event_first_kill",
        "event_croc_discovery",
    ]
    assert dto.groups == []
    assert dto.focus is None


def test_full_projects_undeclared_events_at_detail_tier() -> None:
    """Full mode keeps every Event node; without editorial context the least
    assuming safe tier is detail (3) — never an invented tier."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    graph.nodes.append(
        GraphNode(
            id="event_undeclared",
            type="Event",
            label="An undeclared event",
            visible_from_order=2,
            origin="canonical",
        )
    )
    dto = service.project_full(graph, events)
    by_id = {node.id: node for node in dto.nodes}
    assert by_id["event_undeclared"].display_tier == DISPLAY_TIER_DETAIL


def test_graphrag_focus_projects_focus_and_visible_neighbors() -> None:
    """D-26/D-27: focus node + visible narrative neighbors, bounded; focus
    reference resolves inside the DTO (T10-FOCUS-02)."""
    graph, _events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_graphrag_focus(graph, ["char_dexter_morgan"])

    assert dto.metadata.view_type == GRAPHRAG_FOCUS_VIEW_TYPE
    assert dto.focus == VisualizationFocus(node_id="char_dexter_morgan")
    node_ids = {node.id for node in dto.nodes}
    assert dto.focus.node_id in node_ids
    # Dexter's visible narrative neighbors (participation family excluded):
    # edge_5 -> batista, edge_6 -> debra, edge_9 -> rita, user-rel -> debra.
    assert node_ids == {
        "char_dexter_morgan",
        "char_angel_batista",
        "char_debra_morgan",
        "char_rita_bennett",
    }
    # Only narrative edges between kept nodes.
    assert {edge.id for edge in dto.edges} == {
        "edge_5",
        "edge_6",
        "edge_9",
        "user-rel:test-1",
    }
    # Focus node is core; neighbors are supporting.
    by_id = {node.id: node for node in dto.nodes}
    assert by_id["char_dexter_morgan"].display_tier == DISPLAY_TIER_CORE
    assert by_id["char_angel_batista"].display_tier == DISPLAY_TIER_SUPPORTING
    assert dto.groups == []
    assert dto.timeline == []


def test_graphrag_focus_canonicalizes_deduplicates_and_bounds() -> None:
    """D-30 canonical form: reordered/duplicated focus sets produce the same
    deterministic DTO; the primary focus is the first canonical id."""
    graph, _events = _load_fixture("s01e02_cumulative_safe.json")

    plain = service.project_graphrag_focus(graph, ["char_dexter_morgan"])
    duplicated = service.project_graphrag_focus(
        graph, ["char_dexter_morgan", "char_dexter_morgan"]
    )
    assert duplicated.model_dump(mode="json") == plain.model_dump(mode="json")

    multi = service.project_graphrag_focus(
        graph, ["char_rita_bennett", "char_dexter_morgan", "char_rita_bennett"]
    )
    assert multi.focus == VisualizationFocus(node_id="char_dexter_morgan")
    assert {node.id for node in multi.nodes} >= {
        "char_dexter_morgan",
        "char_rita_bennett",
    }

    # D-27 hard cap on distinct ids.
    with pytest.raises(InvalidVisibilityOrder, match="at most 20"):
        service.project_graphrag_focus(graph, [f"char_{i}" for i in range(21)])

    # Empty focus is refused by the service too (route-level 422 as well).
    with pytest.raises(InvalidVisibilityOrder, match="at least one focus id"):
        service.project_graphrag_focus(graph, [])


def test_graphrag_focus_hidden_or_unknown_id_fails_closed() -> None:
    """T10-FOCUS-02: hidden and unknown focus ids are indistinguishable and
    both refused — the projection never leaks existence."""
    graph, _events = _load_fixture("s01e01_safe.json")
    # Unknown id: not in the safe payload at all.
    with pytest.raises(InvalidVisibilityOrder, match="not a visible graph resource"):
        service.project_graphrag_focus(graph, ["char_does_not_exist"])
    # Hidden id: present in payload but above the effective boundary.
    graph.nodes.append(
        GraphNode(
            id="char_future_killer",
            type="Character",
            label="A future character",
            visible_from_order=9,
            origin="canonical",
        )
    )
    with pytest.raises(InvalidVisibilityOrder, match="cannot be projected at boundary"):
        service.project_graphrag_focus(graph, ["char_future_killer"])


def test_project_view_dispatches_all_six_views() -> None:
    """D-29: the typed dispatcher routes each view to its concrete
    projection; unknown view types fail closed."""
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    assert (
        service.project_view(graph, EPISODE_OVERVIEW_VIEW_TYPE, events).metadata.view_type
        == EPISODE_OVERVIEW_VIEW_TYPE
    )
    assert (
        service.project_view(graph, CHARACTER_NETWORK_VIEW_TYPE).metadata.view_type
        == CHARACTER_NETWORK_VIEW_TYPE
    )
    assert (
        service.project_view(graph, PLOT_THREADS_VIEW_TYPE, events).metadata.view_type
        == PLOT_THREADS_VIEW_TYPE
    )
    assert (
        service.project_view(graph, INVESTIGATION_VIEW_TYPE).metadata.view_type
        == INVESTIGATION_VIEW_TYPE
    )
    assert (
        service.project_view(graph, FULL_VIEW_TYPE, events).metadata.view_type
        == FULL_VIEW_TYPE
    )
    assert (
        service.project_view(
            graph, GRAPHRAG_FOCUS_VIEW_TYPE, focus_ids=["char_dexter_morgan"]
        ).metadata.view_type
        == GRAPHRAG_FOCUS_VIEW_TYPE
    )
    with pytest.raises(ValueError, match="Unknown visualization view type"):
        service.project_view(graph, "banana")


# ---------------------------------------------------------------------------
# 10-06 (D-21): allowlisted semantic expansion — delta projection + route.
# No live Neo4j: the service runs over the checked-in safe fixtures, and the
# route runs against a stub app serving the same fixtures (the
# test_graph_api.py _FakeGraphService pattern). No cache call exists on the
# expansion path (T10-CACHE-06) — the route tests prove it by poisoning every
# cache function.
# ---------------------------------------------------------------------------


def _expand(
    name: str, node_id: str, key: str, limit: int = 12
) -> VisualizationDTO:
    graph, _ = _load_fixture(name)
    return service.project_expansion(graph, node_id, key, limit=limit)


def _iter_all_keys(obj: Any):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _iter_all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_all_keys(item)


def test_expansion_family_delta_exact_shape_and_no_hidden_totals() -> None:
    """Family expansion is a strict delta: anchor first, then additions and
    edges only — no groups/timeline/focus, and no hidden total/count keys
    anywhere in the serialized payload (T10-LEAK-06)."""
    dto = _expand("s01e01_safe.json", "char_dexter_morgan", "family")

    assert dto.metadata.view_type == f"{EXPANSION_VIEW_TYPE_PREFIX}family"
    assert dto.metadata.projection_version == PROJECTION_VERSION
    assert [node.id for node in dto.nodes] == [
        "char_dexter_morgan",
        "char_debra_morgan",
    ]
    assert dto.nodes[0].display_tier == DISPLAY_TIER_CORE
    assert [edge.id for edge in dto.edges] == ["edge_4"]
    assert dto.edges[0].relation_class == "family"
    assert dto.groups == []
    assert dto.timeline == []
    assert dto.focus is None
    for key in _iter_all_keys(dto.model_dump(mode="json")):
        assert not any(word in key for word in ("total", "count", "degree", "restoration"))


@pytest.mark.parametrize(
    ("fixture", "node_id", "key", "addition_ids", "edge_classes"),
    [
        (
            "s01e02_cumulative_safe.json",
            "char_dexter_morgan",
            "family",
            ["char_debra_morgan", "char_rita_bennett"],
            ["family", "family"],
        ),
        (
            "s01e01_safe.json",
            "char_dexter_morgan",
            "work",
            ["char_angel_batista"],
            ["work"],
        ),
        ("s01e01_safe.json", "char_dexter_morgan", "conflict", [], []),
        (
            "s01e02_cumulative_safe.json",
            "char_dexter_morgan",
            "locations",
            ["loc_miami_metro"],
            ["occurred_in"],
        ),
        (
            "s01e02_cumulative_safe.json",
            "dexter_s01e01",
            "episode_events",
            ["event_first_kill"],
            [],
        ),
        (
            "s01e02_cumulative_safe.json",
            "char_dexter_morgan",
            "clues",
            [
                "claim_1",
                "claim_2",
                "claim_3",
                "claim_4",
                "evidence_1",
                "evidence_2",
                "evidence_3",
                "claim_5",
                "evidence_4",
            ],
            ["supported_by", "supported_by", "supported_by", "supported_by", "supported_by"],
        ),
        (
            "s01e02_cumulative_safe.json",
            "char_dexter_morgan",
            "evidence",
            [
                "evidence_1",
                "evidence_2",
                "evidence_3",
                "source_1",
                "evidence_4",
                "source_2",
            ],
            ["from_source", "from_source", "from_source", "from_source"],
        ),
    ],
)
def test_expansion_all_seven_keys_return_deterministic_deltas(
    fixture: str,
    node_id: str,
    key: str,
    addition_ids: list[str],
    edge_classes: list[str],
) -> None:
    """D-21: every allowlisted key produces a valid, deterministic delta
    (anchor + additions ordered by (reveal order, id) + human-class edges)."""
    dto = _expand(fixture, node_id, key)
    assert dto.metadata.view_type == f"{EXPANSION_VIEW_TYPE_PREFIX}{key}"
    assert dto.nodes[0].id == node_id
    assert [node.id for node in dto.nodes[1:]] == addition_ids
    assert [edge.relation_class for edge in dto.edges] == edge_classes
    assert {edge.source for edge in dto.edges} <= {node.id for node in dto.nodes}
    assert {edge.target for edge in dto.edges} <= {node.id for node in dto.nodes}
    # Deterministic: byte-identical on repeat (cache/version contract).
    again = _expand(fixture, node_id, key)
    assert dto.model_dump(mode="json") == again.model_dump(mode="json")


def test_expansion_limit_bounded_deterministic_and_fail_closed() -> None:
    """D-21: limit truncates additions deterministically; the hard max of
    EXPANSION_MAX_LIMIT is enforced; unknown keys and out-of-range limits
    fail closed (T10-BOUND-06)."""
    graph, _ = _load_fixture("s01e02_cumulative_safe.json")

    capped = service.project_expansion(
        graph, "char_dexter_morgan", "family", limit=1
    )
    assert [node.id for node in capped.nodes] == [
        "char_dexter_morgan",
        "char_debra_morgan",
    ]

    full = service.project_expansion(
        graph, "char_dexter_morgan", "family", limit=EXPANSION_MAX_LIMIT
    )
    assert [node.id for node in full.nodes] == [
        "char_dexter_morgan",
        "char_debra_morgan",
        "char_rita_bennett",
    ]

    for bad_limit in (0, EXPANSION_MAX_LIMIT + 1, -1):
        with pytest.raises(ValueError, match="limit"):
            service.project_expansion(graph, "char_dexter_morgan", "family", limit=bad_limit)
    with pytest.raises(ValueError, match="Unknown expansion key"):
        service.project_expansion(graph, "char_dexter_morgan", "banana")


def test_expansion_hidden_or_unknown_anchor_fails_closed() -> None:
    """Hidden and unknown anchors are indistinguishable and both refused
    (T10-LEAK-06); a hidden payload row is refused before projection."""
    graph, _ = _load_fixture("s01e01_safe.json")
    with pytest.raises(InvalidVisibilityOrder, match="not a visible graph resource"):
        service.project_expansion(graph, "char_future_killer", "family")

    hidden_graph = _empty_graph()
    hidden_graph.nodes.append(
        GraphNode(
            id="hidden_char",
            type="Character",
            label="Hidden",
            visible_from_order=2,
            origin="canonical",
            episode_id=None,
            image_url=None,
            image_source_url=None,
        )
    )
    with pytest.raises(InvalidVisibilityOrder, match="Hidden row"):
        service.project_expansion(hidden_graph, "hidden_char", "family")


def test_expansion_episode_events_requires_episode_anchor() -> None:
    """episode_events is episode-scoped: a non-Episode anchor fails closed."""
    graph, _ = _load_fixture("s01e01_safe.json")
    with pytest.raises(InvalidVisibilityOrder, match="Episode anchor"):
        service.project_expansion(graph, "char_dexter_morgan", "episode_events")


def test_expansion_conflict_relation_family() -> None:
    """The conflict key expands through the conflict relation family and the
    delta carries the human class — never the raw relation name (D-14)."""
    graph = _empty_graph()
    graph.nodes.append(
        GraphNode(
            id="char_a",
            type="Character",
            label="A",
            visible_from_order=1,
            origin="canonical",
            episode_id=None,
            image_url=None,
            image_source_url=None,
        )
    )
    graph.nodes.append(
        GraphNode(
            id="char_b",
            type="Character",
            label="B",
            visible_from_order=1,
            origin="canonical",
            episode_id=None,
            image_url=None,
            image_source_url=None,
        )
    )
    graph.edges.append(
        GraphEdge(
            id="edge_opposes",
            source="char_a",
            target="char_b",
            type="OPPOSES",
            visible_from_order=1,
            origin="canonical",
        )
    )
    dto = service.project_expansion(graph, "char_a", "conflict")
    assert [node.id for node in dto.nodes] == ["char_a", "char_b"]
    assert dto.edges[0].relation_class == "opposes"
    assert "OPPOSES" not in json.dumps(dto.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Expansion route (stub app — no live Neo4j, no cache)
# ---------------------------------------------------------------------------


class _StubGraphService:
    """GraphService stand-in serving a checked-in safe fixture (no Neo4j)."""

    def __init__(self, fixture_name: str = "s01e01_safe.json") -> None:
        with (FIXTURES_DIR / fixture_name).open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)
        self._graph = GraphResponse.model_validate(fixture["graph"])
        self._max_episode_order = max(
            (
                node.visible_from_order
                for node in self._graph.nodes
                if node.type == "Episode"
            ),
            default=0,
        )

    async def get_series_meta(self, series_id: str) -> dict[str, Any] | None:
        if series_id != self._graph.series.id:
            return None
        return self._graph.series.model_dump()

    async def resolve_boundary(self, series_id: str, visible_until_order: int):
        if series_id != self._graph.series.id:
            return None
        if 1 <= visible_until_order <= self._max_episode_order:
            return {"id": f"{series_id}:episode:{visible_until_order}"}
        return None

    async def fetch_graph(
        self,
        series_id: str,
        visible_until_order: int,
        node_labels: list[str],
        user_relationship_types: list[str],
        effective_view_order: int | None = None,
    ) -> GraphResponse:
        effective = (
            effective_view_order
            if effective_view_order is not None
            else visible_until_order
        )
        node_ids = {
            node.id
            for node in self._graph.nodes
            if node.visible_from_order <= effective and node.type in node_labels
        }
        return GraphResponse(
            series=self._graph.series,
            visible_until_order=visible_until_order,
            effective_view_order=effective,
            nodes=[
                node
                for node in self._graph.nodes
                if node.visible_from_order <= effective and node.type in node_labels
            ],
            edges=[
                edge
                for edge in self._graph.edges
                if edge.visible_from_order <= effective
                and edge.source in node_ids
                and edge.target in node_ids
            ],
            claims=[
                claim
                for claim in self._graph.claims
                if claim.visible_from_order <= effective
            ],
            sources=[
                source
                for source in self._graph.sources
                if source.visible_from_order <= effective
            ],
            evidence=[
                item
                for item in self._graph.evidence
                if item.visible_from_order <= effective
            ],
        )


class _StubProgressService:
    def __init__(self, record: Any = None) -> None:
        self._record = record

    async def get(self, user_id: str, series_id: str):
        return self._record


class _ProgressRecord:
    def __init__(self, view_as_of_order: int, watched_through_order: int) -> None:
        self.view_as_of_order = view_as_of_order
        self.watched_through_order = watched_through_order


def _expansion_app(
    *,
    user: dict[str, Any] | None = None,
    progress: Any = None,
    fixture_name: str = "s01e01_safe.json",
) -> FastAPI:
    app = FastAPI()
    # The main-app handlers give the stub the same sanitized validation
    # envelope the production app serves (INVALID_REQUEST, never echoes
    # request input).
    install_error_handlers(app)
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.include_router(graph_router)
    app.dependency_overrides[get_optional_current_user] = lambda: user
    app.dependency_overrides[get_graph_service] = lambda: _StubGraphService(fixture_name)
    app.dependency_overrides[get_progress_service] = lambda: _StubProgressService(progress)
    return app


def _expand_url(
    node_id: str,
    key: str,
    episode_order: int = 1,
    limit: int | None = None,
) -> str:
    url = (
        f"/api/series/series_dexter/graph/expand?node_id={node_id}"
        f"&expansion_key={key}&episode_order={episode_order}"
    )
    if limit is not None:
        url += f"&limit={limit}"
    return url


def test_expansion_route_family_validated_end_to_end() -> None:
    """One family expansion request returns a validated delta DTO."""
    client = TestClient(_expansion_app())
    response = client.get(_expand_url("char_dexter_morgan", "family"))

    assert response.status_code == 200, response.text
    dto = VisualizationDTO.model_validate(response.json())
    assert dto.metadata.view_type == "expansion:family"
    assert dto.metadata.series_id == "series_dexter"
    assert [node.id for node in dto.nodes] == [
        "char_dexter_morgan",
        "char_debra_morgan",
    ]
    assert [edge.relation_class for edge in dto.edges] == ["family"]


def test_expansion_route_rejects_unknown_keys_and_out_of_range_limits() -> None:
    """T10-BOUND-06: the server enum and strict limit validation refuse
    arbitrary concepts and anything above the hard max of 25."""
    client = TestClient(_expansion_app())

    for query in (
        _expand_url("char_dexter_morgan", "banana"),
        _expand_url("char_dexter_morgan", "family", limit=0),
        _expand_url("char_dexter_morgan", "family", limit=26),
        "/api/series/series_dexter/graph/expand?expansion_key=family&episode_order=1",
    ):
        response = client.get(query)
        assert response.status_code == 422, response.text
        assert response.json() == {
            "detail": {"code": "INVALID_REQUEST", "message": "Request validation failed."}
        }


def test_expansion_route_unknown_series_is_404() -> None:
    client = TestClient(_expansion_app())
    response = client.get(
        "/api/series/unknown/graph/expand?node_id=x&expansion_key=family&episode_order=1"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERIES_NOT_FOUND"


def test_expansion_route_invalid_boundary_is_typed_422() -> None:
    # PROB-04/#12: anonymous users clamp to order 1, so episode_order=99 is
    # ignored. An AUTHENTICATED user with persisted progress past the
    # fixture's max order exercises the fail-closed boundary path.
    client = TestClient(
        _expansion_app(
            user={"id": "user:test", "email": "t@example.com"},
            progress=_ProgressRecord(2, 2),
        )
    )
    response = client.get(_expand_url("char_dexter_morgan", "family", episode_order=2))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_VISIBLE_UNTIL_ORDER"


def test_expansion_route_hidden_anchor_is_sanitized_422() -> None:
    """Unknown/hidden anchors are indistinguishable; the id is never echoed."""
    client = TestClient(_expansion_app())
    response = client.get(_expand_url("char_future_killer", "family"))
    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "INVALID_REQUEST",
            "message": "The requested expansion is not visible at the effective boundary.",
        }
    }
    assert "char_future_killer" not in response.text


def test_expansion_route_bypasses_cache_entirely(monkeypatch) -> None:
    """T10-CACHE-06: every cache get/set is poisoned — expansion still serves
    (and therefore never crossed the cache boundary for any request tuple)."""

    def _no_cache(*_args, **_kwargs):
        raise AssertionError("expansion route must never touch the cache")

    for cache_fn in (
        "get_cached_graph",
        "set_cached_graph",
        "get_cached_visualization",
        "set_cached_visualization",
    ):
        # Both import styles are poisoned: the cache module's own attribute
        # and the bound name inside spoilerless.app.api.graph — a cache call
        # through either binding fails the test.
        monkeypatch.setattr(graph_cache, cache_fn, _no_cache)
        monkeypatch.setattr(graph_api_module, cache_fn, _no_cache)

    client = TestClient(
        _expansion_app(fixture_name="s01e02_cumulative_safe.json")
    )
    for key in EXPANSION_KEYS:
        anchor = "dexter_s01e01" if key == "episode_events" else "char_dexter_morgan"
        response = client.get(_expand_url(anchor, key))
        assert response.status_code == 200, response.text
        VisualizationDTO.model_validate(response.json())


def test_expansion_distinct_request_tuples_compute_independently(monkeypatch) -> None:
    """D-21/T10-CACHE-06: with no cache anywhere on the path, distinct
    (node_id, expansion_key, limit) tuples return independently computed
    results — a limit change or key change changes the delta itself."""
    monkeypatch.setattr(graph_cache, "get_cached_graph", lambda *a, **k: None)
    client = TestClient(
        _expansion_app(
            user={"id": "user:test"},
            progress=_ProgressRecord(2, 2),
            fixture_name="s01e02_cumulative_safe.json",
        )
    )

    capped = client.get(
        _expand_url("char_dexter_morgan", "family", episode_order=2, limit=1)
    ).json()
    full = client.get(
        _expand_url("char_dexter_morgan", "family", episode_order=2, limit=2)
    ).json()
    work = client.get(
        _expand_url("char_dexter_morgan", "work", episode_order=2)
    ).json()

    assert [node["id"] for node in capped["nodes"]] == [
        "char_dexter_morgan",
        "char_debra_morgan",
    ]
    assert [node["id"] for node in full["nodes"]] == [
        "char_dexter_morgan",
        "char_debra_morgan",
        "char_rita_bennett",
    ]
    assert [node["id"] for node in work["nodes"]] == [
        "char_dexter_morgan",
        "char_angel_batista",
    ]
    # No hidden totals on the wire.
    for payload in (capped, full, work):
        assert not any(word in key for key in _iter_all_keys(payload) for word in ("total", "count"))
