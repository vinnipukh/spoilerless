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

import pytest
from pydantic import ValidationError

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
    VisualizationFocus,
    VisualizationNode,
)
from spoilerless.app.services.visualization import (
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
