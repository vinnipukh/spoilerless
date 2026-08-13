"""Phase 10-01 baseline tracer: safe fixtures -> GraphResponse -> evidence.

This module is the production-quality tracer contract for plan 10-01
(``.planning/phases/10-polish-finishing-touches/10-01-PLAN.md``).  It freezes
the safe S01E01 and cumulative S01E02 visualization baselines and provides the
deterministic evidence object that Task 2 consumes for the Variant A/B
Episode-Overview decision gate (D-10, VIZ-03, VIZ-10).

Pipeline (no mock seam anywhere in the runnable path):

    checked-in JSON fixture
      -> ``GraphResponse.model_validate`` (real Pydantic validation + closure)
      -> effective-boundary assertion via ``spoiler.app.spoiler.policy``
      -> baseline metric calculation (counts / latency / payload / layout inputs)
      -> Variant A/B projections with omissions, crossings approximation,
         procedural-label count and stability
      -> ``build_evidence()`` — the exact object Task 2 consumes

Safety contract (threat model T10-LEAK-01 / T10-BOUND-01 / T10-CACHE-01 /
T10-FOCUS-01): fixtures contain ONLY rows visible at their effective boundary
(no hidden rows), carry explicit episode + projection-version metadata, and
reject hidden IDs, group totals and restoration hints.  No live Neo4j access
and no LLM calls are made anywhere in this module.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from spoilerless.app.domain.graph import GraphResponse
from spoilerless.app.spoiler.policy import effective_view_order, is_visible

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visualization"

PROJECTION_VERSION = "1.0.0"
FIXTURE_FILES = ("s01e01_safe.json", "s01e02_cumulative_safe.json")

# D-09 / VIZ-03 Episode Overview bounds — single source of truth for the tracer.
TARGET_MIN_NODES = 12
TARGET_MAX_NODES = 28
HARD_MAX_NODES = 40
PREFERRED_MAX_EDGES = 35
HARD_MAX_EDGES = 60

# D-13: Episode Overview omits participation/occurrence/location edges; they
# surface as timeline metadata, avatars/chips or Inspector detail instead.
OMITTED_EDGE_TYPES = frozenset({"OCCURRED_IN", "PARTICIPATED_IN", "LOCATED_IN"})
CONTAINER_NODE_TYPES = frozenset({"Series", "Episode"})

# T10-FOCUS-01 / T10-LEAK-01: metadata that must never appear in a safe
# baseline payload (hidden IDs/counts, group totals, restoration hints).
_FORBIDDEN_KEY_RE = re.compile(
    r"\b(hidden|hidden_count|group_total|total_hidden|restoration|focus_hint)\b",
    re.IGNORECASE,
)
_PROCEDURAL_LABEL_RE = re.compile(r"^(Ep #|Group|Cluster|Community)", re.IGNORECASE)

NARRATIVE_NOTES: dict[str, str] = {
    "A": (
        "Major Events are drawn as graph nodes beside characters. With 1-2 major "
        "Events per episode the graph stays sparse, but event meaning "
        "(participants, location) competes with character topology for attention; "
        "OCCURRED_IN participation edges are omitted (D-13), so event nodes float "
        "without in-graph links to their participants and rely on the Inspector."
    ),
    "B": (
        "The graph is character-led; every Event renders as a timeline card with "
        "participants and location metadata (D-13/D-38), matching the Story "
        "two-region composition (graph + timeline rail). Event comprehension comes "
        "from the coordinated timeline rather than graph topology; the graph stays "
        "stable across episode switches (only character additions change it)."
    ),
}


# ---------------------------------------------------------------------------
# Fixture loading and GraphResponse-shaped validation
# ---------------------------------------------------------------------------


def load_fixture(name: str) -> dict[str, Any]:
    """Load a checked-in safe fixture (JSON text -> dict)."""
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _forbidden_metadata_keys(obj: Any, path: str = "") -> list[str]:
    """Recursively find keys matching the T10-FOCUS-01 forbidden vocabulary."""
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            full = f"{path}.{key}" if path else key
            if _FORBIDDEN_KEY_RE.search(key):
                found.append(full)
            found.extend(_forbidden_metadata_keys(value, full))
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            found.extend(_forbidden_metadata_keys(item, f"{path}[{index}]"))
    return found


# ---------------------------------------------------------------------------
# Baseline metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaselineMetrics:
    episode: str
    episode_order: int
    effective_view_order: int
    node_count: int
    edge_count: int
    claim_count: int
    source_count: int
    evidence_count: int
    node_kinds: dict[str, int]
    edge_types: dict[str, int]
    payload_bytes: int
    load_validate_ms: float


@dataclass(frozen=True)
class VariantMetrics:
    variant: str
    episode: str
    node_count: int
    edge_count: int
    node_kinds: dict[str, int]
    edge_types: dict[str, int]
    kept_node_ids: list[str]
    omitted_node_ids: list[str]
    omitted_edge_ids: list[str]
    crossings_approx: int
    procedural_labels: int
    within_target_range: bool
    within_hard_bounds: bool


def measure_baseline(name: str) -> tuple[dict[str, Any], BaselineMetrics]:
    """Load + validate + count one fixture; returns (fixture, metrics).

    The elapsed time covers JSON load, Pydantic validation (including the
    ``GraphResponse`` closure validator) and the count computation — the
    runnable end-to-end tracer path, not a mock.
    """
    started = time.perf_counter()
    fixture = load_fixture(name)
    metadata = fixture["fixture_metadata"]
    graph = GraphResponse.model_validate(fixture["graph"])
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    metrics = BaselineMetrics(
        episode=metadata["episode"],
        episode_order=metadata["episode_order"],
        effective_view_order=graph.effective_view_order,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        claim_count=len(graph.claims),
        source_count=len(graph.sources),
        evidence_count=len(graph.evidence),
        node_kinds=dict(sorted(Counter(node.type for node in graph.nodes).items())),
        edge_types=dict(sorted(Counter(edge.type for edge in graph.edges).items())),
        payload_bytes=(FIXTURES_DIR / name).stat().st_size,
        load_validate_ms=round(elapsed_ms, 3),
    )
    return fixture, metrics


# ---------------------------------------------------------------------------
# Variant projections (D-10) and deterministic layout metrics
# ---------------------------------------------------------------------------


def _select_nodes(graph: GraphResponse, events: list[dict[str, Any]], variant: str) -> list[Any]:
    """Variant A: characters + major Events + containers.

    Variant B: character-led graph — Events go to the timeline, never in-graph.
    """
    major_event_ids = {event["id"] for event in events if event.get("tier") == "major"}
    selected: list[Any] = []
    for node in graph.nodes:
        if node.type in CONTAINER_NODE_TYPES or node.type == "Character":
            selected.append(node)
        elif variant == "A" and node.type == "Event" and node.id in major_event_ids:
            selected.append(node)
    return selected


def approximate_crossings(edges: list[Any], order: dict[str, int]) -> int:
    """Deterministic approximation of edge crossings (D-32 permits approximation).

    Nodes are placed in the deterministic id-order ``order``; every pair of
    edges whose four endpoints interleave in that order counts as one
    approximate crossing.  Documented limitation: this is a layout-order
    proxy, not a real geometric crossing count.
    """
    crossings = 0
    for i, first in enumerate(edges):
        for second in edges[i + 1 :]:
            ends1 = {first.source, first.target}
            ends2 = {second.source, second.target}
            if ends1 == ends2 or len(ends1 | ends2) < 4:
                continue
            a, b = sorted((order[first.source], order[first.target]))
            c, d = sorted((order[second.source], order[second.target]))
            if (a < c < b < d) or (c < a < d < b):
                crossings += 1
    return crossings


def project_variant(
    graph: GraphResponse,
    events: list[dict[str, Any]],
    variant: str,
    episode: str,
) -> VariantMetrics:
    """Project one Episode Overview variant over the safe graph."""
    if variant not in {"A", "B"}:
        raise ValueError(f"Unknown variant {variant!r}; expected 'A' or 'B'.")
    kept = _select_nodes(graph, events, variant)
    kept_ids = {node.id for node in kept}
    kept_edges = [
        edge
        for edge in graph.edges
        if edge.type not in OMITTED_EDGE_TYPES
        and edge.source in kept_ids
        and edge.target in kept_ids
    ]
    order = {node_id: index for index, node_id in enumerate(sorted(kept_ids))}
    node_count = len(kept)
    edge_count = len(kept_edges)
    return VariantMetrics(
        variant=variant,
        episode=episode,
        node_count=node_count,
        edge_count=edge_count,
        node_kinds=dict(sorted(Counter(node.type for node in kept).items())),
        edge_types=dict(sorted(Counter(edge.type for edge in kept_edges).items())),
        kept_node_ids=sorted(kept_ids),
        omitted_node_ids=sorted({n.id for n in graph.nodes} - kept_ids),
        omitted_edge_ids=sorted({e.id for e in graph.edges} - {e.id for e in kept_edges}),
        crossings_approx=approximate_crossings(kept_edges, order),
        procedural_labels=sum(1 for node in kept if _PROCEDURAL_LABEL_RE.search(node.label)),
        within_target_range=TARGET_MIN_NODES <= node_count <= TARGET_MAX_NODES,
        within_hard_bounds=node_count <= HARD_MAX_NODES and edge_count <= HARD_MAX_EDGES,
    )


# ---------------------------------------------------------------------------
# Stability between episodes (D-31)
# ---------------------------------------------------------------------------


def _character_retention() -> dict[str, Any]:
    """Shared-character retention per variant across S01E01 -> cumulative S01E02."""
    result: dict[str, Any] = {}
    for variant in ("A", "B"):
        chars: dict[str, list[str]] = {}
        for name in FIXTURE_FILES:
            fixture = load_fixture(name)
            graph = GraphResponse.model_validate(fixture["graph"])
            chars[fixture["fixture_metadata"]["episode"]] = sorted(
                node.id for node in _select_nodes(graph, fixture.get("events", []), variant)
                if node.type == "Character"
            )
        e01, e02 = chars["S01E01"], chars["S01E02"]
        shared = sorted(set(e01) & set(e02))
        result[variant] = {
            "shared_character_ids": shared,
            "shared_character_count": len(shared),
            "e01_character_count": len(e01),
            "e02_character_count": len(e02),
            "retention_ratio": round(len(shared) / len(e01), 4) if e01 else 0.0,
            "displacement": 0.0,
            "displacement_note": (
                "Deterministic id-order layout produces identical positions for "
                "shared ids by construction; real fCoSE displacement is measured "
                "by the 10-08 benchmark harness."
            ),
        }
    return result


# ---------------------------------------------------------------------------
# The evidence object consumed by Task 2 (the A/B decision gate)
# ---------------------------------------------------------------------------


def build_evidence() -> dict[str, Any]:
    """Deterministic evidence bundle: baselines + variant metrics + stability.

    This is the exact object Task 2 consumes when it records the measured
    A/B comparison in ``docs/decision-logs/phase-10-visualization.md``.
    """
    episodes: dict[str, Any] = {}
    for name in FIXTURE_FILES:
        fixture, baseline = measure_baseline(name)
        metadata = fixture["fixture_metadata"]
        graph = GraphResponse.model_validate(fixture["graph"])
        events = fixture.get("events", [])
        episodes[metadata["episode"]] = {
            "fixture": name,
            "episode_order": metadata["episode_order"],
            "effective_view_order": metadata["effective_view_order"],
            "baseline": asdict(baseline),
            "variants": {
                variant: asdict(project_variant(graph, events, variant, metadata["episode"]))
                for variant in ("A", "B")
            },
        }
    return {
        "projection_version": PROJECTION_VERSION,
        "fixture_files": list(FIXTURE_FILES),
        "bounds": {
            "target_min_nodes": TARGET_MIN_NODES,
            "target_max_nodes": TARGET_MAX_NODES,
            "hard_max_nodes": HARD_MAX_NODES,
            "preferred_max_edges": PREFERRED_MAX_EDGES,
            "hard_max_edges": HARD_MAX_EDGES,
            "persistent_procedural_labels": 0,
        },
        "episodes": episodes,
        "stability": _character_retention(),
        "narrative_notes": NARRATIVE_NOTES,
    }


# ---------------------------------------------------------------------------
# Task 1 — deterministic contract tests (fixture schema, hidden rows, image
# fields, baseline counts/latency/payload/layout inputs)
# ---------------------------------------------------------------------------


def test_fixture_schema_and_closure_s01e01() -> None:
    fixture, metrics = measure_baseline("s01e01_safe.json")
    metadata = fixture["fixture_metadata"]
    assert metadata["fixture_type"] == "episode_safe"
    assert metadata["episode"] == "S01E01"
    assert metadata["episode_order"] == 1
    assert metadata["effective_view_order"] == 1
    assert metadata["projection_version"] == PROJECTION_VERSION
    assert metadata["immutable"] is True
    # GraphResponse.model_validate already ran (closure validator rejects
    # dangling edges); re-validate to prove determinism of the shape.
    graph = GraphResponse.model_validate(fixture["graph"])
    assert graph.visible_until_order == 1
    assert graph.effective_view_order == 1
    assert metrics.node_count == len(graph.nodes)


def test_fixture_schema_and_closure_s01e02_cumulative() -> None:
    fixture, metrics = measure_baseline("s01e02_cumulative_safe.json")
    metadata = fixture["fixture_metadata"]
    assert metadata["fixture_type"] == "episode_safe"
    assert metadata["scope"] == "cumulative_safe"
    assert metadata["episode"] == "S01E02"
    assert metadata["episode_order"] == 2
    assert metadata["effective_view_order"] == 2
    assert metadata["projection_version"] == PROJECTION_VERSION
    graph = GraphResponse.model_validate(fixture["graph"])
    assert graph.visible_until_order == 2
    assert graph.effective_view_order == 2
    assert metrics.node_count == len(graph.nodes)


def test_effective_boundary_semantics_and_no_hidden_rows() -> None:
    """T10-BOUND-01 / T10-LEAK-01: boundary before projection, fail closed.

    Every row in every fixture must be visible at the fixture's effective
    boundary (fixtures contain ONLY boundary-filtered rows — no hidden rows,
    no future rows that could influence counts or layout).
    """
    for name in FIXTURE_FILES:
        fixture, metrics = measure_baseline(name)
        metadata = fixture["fixture_metadata"]
        order = metadata["episode_order"]
        effective = metadata["effective_view_order"]
        # The policy min-rule reproduces the fixture boundary, and requesting a
        # future episode while watched progress stays at the fixture clamps down.
        assert effective_view_order(order, order) == effective
        assert effective_view_order(order + 1, order) == order
        graph = GraphResponse.model_validate(fixture["graph"])
        rows = [*graph.nodes, *graph.edges, *graph.claims, *graph.sources, *graph.evidence]
        assert rows, f"{name}: fixture must contain rows"
        for row in rows:
            assert is_visible(row, effective), (
                f"{name}: hidden row {row.id!r} (visible_from_order="
                f"{row.visible_from_order}) present at effective boundary {effective}"
            )
            assert row.visible_from_order <= effective, f"{name}: row {row.id!r} above boundary"


def test_no_forbidden_technical_or_hidden_metadata() -> None:
    """T10-FOCUS-01: payload rejects hidden IDs, group totals, restoration hints."""
    for name in FIXTURE_FILES:
        fixture = load_fixture(name)
        forbidden = _forbidden_metadata_keys(fixture)
        assert forbidden == [], f"{name}: forbidden metadata keys found: {forbidden}"
        graph = GraphResponse.model_validate(fixture["graph"])
        for node in graph.nodes:
            assert "hidden" not in node.id.lower()
        # No aggregate counts beyond the visible rows exist anywhere in the payload.
        assert "counts" not in fixture["graph"]


def test_episode_safe_image_fields() -> None:
    """D-43: images cannot reveal future costume/injury/identity; fallback-safe."""
    for name in FIXTURE_FILES:
        fixture, _ = measure_baseline(name)
        graph = GraphResponse.model_validate(fixture["graph"])
        episode_ids = {node.id for node in graph.nodes if node.type == "Episode"}
        for node in graph.nodes:
            if node.image_url is None and node.image_source_url is None:
                continue
            assert node.episode_id is not None, f"{name}: image on {node.id} without episode binding"
            assert node.episode_id in episode_ids, (
                f"{name}: {node.id} image bound to episode {node.episode_id!r} "
                "which is not in the safe graph"
            )
            assert node.visible_from_order <= graph.effective_view_order
            assert node.image_url is not None and node.image_url.startswith("https://")
            if node.image_source_url is not None:
                assert node.image_source_url.startswith("https://")


def test_baseline_counts_s01e01() -> None:
    """Exact safe node/edge-kind sets for S01E01 (mirrors frontend fixture)."""
    _, metrics = measure_baseline("s01e01_safe.json")
    assert metrics.node_count == 11
    assert metrics.edge_count == 7
    assert metrics.claim_count == 4
    assert metrics.source_count == 1
    assert metrics.evidence_count == 3
    assert metrics.node_kinds == {
        "Series": 1,
        "Episode": 1,
        "Character": 6,
        "Event": 1,
        "Location": 2,
    }
    assert metrics.edge_types == {
        "PART_OF": 1,
        "OCCURRED_IN": 3,
        "WORKS_WITH": 1,
        "FAMILY_OF": 1,
        "KNOWS": 1,  # user-origin edge preserved in the safe payload
    }


def test_baseline_counts_s01e02_cumulative() -> None:
    """Exact safe node/edge-kind sets for cumulative S01E02."""
    _, metrics = measure_baseline("s01e02_cumulative_safe.json")
    assert metrics.node_count == 17
    assert metrics.edge_count == 14
    assert metrics.claim_count == 6
    assert metrics.source_count == 2
    assert metrics.evidence_count == 5
    assert metrics.node_kinds == {
        "Series": 1,
        "Episode": 2,
        "Character": 8,
        "Event": 2,
        "Location": 4,
    }
    assert metrics.edge_types == {
        "PART_OF": 2,
        "PRECEDES": 1,
        "OCCURRED_IN": 6,
        "WORKS_WITH": 2,
        "FAMILY_OF": 2,
        "KNOWS": 1,
    }


def test_baseline_latency_payload_and_layout_inputs() -> None:
    """Latency/payload are measured (bounded, not mocked); layout inputs pass."""
    evidence = build_evidence()
    for episode_key in ("S01E01", "S01E02"):
        baseline = evidence["episodes"][episode_key]["baseline"]
        assert baseline["payload_bytes"] > 0
        assert baseline["load_validate_ms"] >= 0
        assert baseline["load_validate_ms"] < 5000.0, "fixture load+validate should be fast"
        for variant in ("A", "B"):
            metrics = evidence["episodes"][episode_key]["variants"][variant]
            assert metrics["node_count"] <= HARD_MAX_NODES
            assert metrics["edge_count"] <= HARD_MAX_EDGES
            assert metrics["procedural_labels"] == 0
    assert evidence["bounds"]["persistent_procedural_labels"] == 0


# ---------------------------------------------------------------------------
# Task 2 — measured Variant A/B comparison and the evidence object consumed by
# the A/B decision gate (D-10, VIZ-03).  All numbers below are the measured,
# deterministic values over the checked-in fixed fixtures.
# ---------------------------------------------------------------------------


def test_variant_a_metrics_and_omissions() -> None:
    """Variant A = characters + major Events; participation edges omitted."""
    evidence = build_evidence()
    e01 = evidence["episodes"]["S01E01"]["variants"]["A"]
    e02 = evidence["episodes"]["S01E02"]["variants"]["A"]
    assert e01["node_count"] == 9
    assert e01["edge_count"] == 4
    assert e01["node_kinds"] == {"Series": 1, "Episode": 1, "Character": 6, "Event": 1}
    assert e01["edge_types"] == {"PART_OF": 1, "WORKS_WITH": 1, "FAMILY_OF": 1, "KNOWS": 1}
    assert e01["omitted_node_ids"] == ["loc_dexters_apartment", "loc_miami_metro"]
    assert e01["omitted_edge_ids"] == ["edge_2", "edge_5", "edge_6"]
    assert e01["crossings_approx"] == 0
    assert e01["procedural_labels"] == 0
    assert e02["node_count"] == 13
    assert e02["edge_count"] == 7
    assert e02["node_kinds"] == {"Series": 1, "Episode": 2, "Character": 8, "Event": 2}
    assert e02["edge_types"] == {
        "PART_OF": 2,
        "PRECEDES": 1,
        "WORKS_WITH": 1,
        "FAMILY_OF": 2,
        "KNOWS": 1,
    }
    assert e02["omitted_node_ids"] == [
        "loc_dexters_apartment",
        "loc_everglades",
        "loc_miami_metro",
        "loc_ritas_house",
    ]
    assert e02["omitted_edge_ids"] == [
        "edge_10",
        "edge_11",
        "edge_12",  # WORKS_WITH dropped: its location endpoint is not kept
        "edge_13",
        "edge_4",
        "edge_7",
        "edge_8",
    ]
    assert e02["crossings_approx"] == 0
    assert e02["procedural_labels"] == 0


def test_variant_b_metrics_and_omissions() -> None:
    """Variant B = character-led graph; every Event is timeline-only."""
    evidence = build_evidence()
    e01 = evidence["episodes"]["S01E01"]["variants"]["B"]
    e02 = evidence["episodes"]["S01E02"]["variants"]["B"]
    assert e01["node_count"] == 8
    assert e01["edge_count"] == 4
    assert e01["node_kinds"] == {"Series": 1, "Episode": 1, "Character": 6}
    assert e01["edge_types"] == {"PART_OF": 1, "WORKS_WITH": 1, "FAMILY_OF": 1, "KNOWS": 1}
    assert e01["omitted_node_ids"] == [
        "event_first_kill",
        "loc_dexters_apartment",
        "loc_miami_metro",
    ]
    assert e01["omitted_edge_ids"] == ["edge_2", "edge_5", "edge_6"]
    assert e02["node_count"] == 11
    assert e02["edge_count"] == 7
    assert e02["node_kinds"] == {"Series": 1, "Episode": 2, "Character": 8}
    assert e02["edge_types"] == {
        "PART_OF": 2,
        "PRECEDES": 1,
        "WORKS_WITH": 1,
        "FAMILY_OF": 2,
        "KNOWS": 1,
    }
    assert e02["omitted_node_ids"] == [
        "event_croc_discovery",
        "event_first_kill",
        "loc_dexters_apartment",
        "loc_everglades",
        "loc_miami_metro",
        "loc_ritas_house",
    ]
    assert e02["omitted_edge_ids"] == [
        "edge_10",
        "edge_11",
        "edge_12",
        "edge_13",
        "edge_4",
        "edge_7",
        "edge_8",
    ]
    assert e02["crossings_approx"] == 0
    assert e02["procedural_labels"] == 0


def test_variant_hard_bounds_both_episodes() -> None:
    """VIZ-03 hard caps: max 40 nodes / max 60 edges / zero procedural labels."""
    evidence = build_evidence()
    for episode_key in ("S01E01", "S01E02"):
        for variant in ("A", "B"):
            metrics = evidence["episodes"][episode_key]["variants"][variant]
            assert metrics["within_hard_bounds"] is True
            assert metrics["node_count"] <= HARD_MAX_NODES
            assert metrics["edge_count"] <= HARD_MAX_EDGES
            assert metrics["procedural_labels"] == 0
    assert evidence["bounds"]["persistent_procedural_labels"] == 0


def test_variant_target_range_assessment() -> None:
    """D-09 target 12-28 nodes: measured, including the honest sparse misses."""
    evidence = build_evidence()
    # Cumulative S01E02: Variant A lands inside the 12-28 target (13 nodes);
    # Variant B falls one node short of the floor (11 nodes).
    assert evidence["episodes"]["S01E02"]["variants"]["A"]["within_target_range"] is True
    assert evidence["episodes"]["S01E02"]["variants"]["B"]["within_target_range"] is False
    # S01E01 is a sparse episode: both variants sit below the floor by honest
    # measurement (9 and 8 nodes) — the sparse-episode empty-state policy
    # (D-44) applies, and the target is a design goal, not a hard bound.
    assert evidence["episodes"]["S01E01"]["variants"]["A"]["within_target_range"] is False
    assert evidence["episodes"]["S01E01"]["variants"]["B"]["within_target_range"] is False


def test_variant_stability_between_episodes() -> None:
    """D-31: shared characters stay stable S01E01 -> cumulative S01E02."""
    evidence = build_evidence()
    for variant in ("A", "B"):
        stability = evidence["stability"][variant]
        assert stability["retention_ratio"] == 1.0
        assert stability["shared_character_count"] == 6
        assert stability["e01_character_count"] == 6
        assert stability["e02_character_count"] == 8
        assert stability["displacement"] == 0.0
        assert stability["displacement_note"]


def test_variant_evidence_object_shape() -> None:
    """The evidence object Task 2 consumes is complete and deterministic."""
    evidence = build_evidence()
    assert evidence["projection_version"] == PROJECTION_VERSION
    assert set(evidence["fixture_files"]) == set(FIXTURE_FILES)
    assert set(evidence["episodes"]) == {"S01E01", "S01E02"}
    for episode in evidence["episodes"].values():
        assert set(episode) == {
            "fixture",
            "episode_order",
            "effective_view_order",
            "baseline",
            "variants",
        }
        assert set(episode["variants"]) == {"A", "B"}
        for metrics in episode["variants"].values():
            assert {
                "node_count",
                "edge_count",
                "node_kinds",
                "edge_types",
                "omitted_node_ids",
                "omitted_edge_ids",
                "crossings_approx",
                "procedural_labels",
                "within_target_range",
                "within_hard_bounds",
            } <= set(metrics)
    assert set(evidence["stability"]) == {"A", "B"}
    assert set(evidence["narrative_notes"]) == {"A", "B"}
    assert evidence["bounds"]["target_min_nodes"] == 12
    assert evidence["bounds"]["target_max_nodes"] == 28
    assert evidence["bounds"]["hard_max_nodes"] == 40
    assert evidence["bounds"]["preferred_max_edges"] == 35
    assert evidence["bounds"]["hard_max_edges"] == 60
    assert evidence["bounds"]["persistent_procedural_labels"] == 0
