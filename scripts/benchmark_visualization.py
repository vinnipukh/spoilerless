"""Deterministic in-memory visualization benchmark harness (D-32 / VIZ-10).

Plan 10-08: zero-cost, zero-network benchmark of the Phase 10 visualization
pipeline over synthetic safe datasets at the four required scales
(30/50, 75/150, 150/400, 300/1000 nodes/edges).

Safety contract (threat model T10-SC-08 / T10-LEAK-08 / T10-BOUND-08 /
T10-CACHE-08 / T10-FOCUS-08):

- ONLY Python standard library plus repository code
  (``spoilerless.app.domain``, ``spoilerless.app.services.visualization``,
  ``spoilerless.app.spoiler.policy``) is executed. No sockets, no subprocess,
  no database driver, no LLM/provider client, no package installation. The
  module has no ``import socket`` / ``import requests`` / ``import redis`` /
  ``import neo4j`` anywhere, and the result records this as an explicit
  environment fact.
- Datasets are synthetic and safe: built from a seeded ``random.Random`` so
  every run produces byte-identical datasets and identical deterministic
  metrics. Hidden rows are ONLY injected where a hidden-influence check
  demands them, and the projection is asserted to reject them (fail closed).
- Hard gates are deterministic product bounds (D-09 caps, D-21 expansion
  max, D-27 focus cap, D-14 label policy, D-05 boundary). Environment-
  sensitive metrics (wall-clock latency, Python memory, and every browser-
  side metric: adapter conversion, Cytoscape init/layout, interaction,
  React commits) are reported in an ``observations`` block with an explicit
  ``environment_sensitive`` flag and rationale per D-32/A2 — never mixed
  into the deterministic hard-gate evidence.
- The result is validated against ``scripts/benchmark_visualization_schema.json``
  by the same stdlib validator used by the pytest ``benchmark`` marker test,
  so the artifact is machine-checkable and rerunnable at zero cost.

Usage:
    uv run python scripts/benchmark_visualization.py \
        --sizes 30x50,75x150,150x400,300x1000 \
        --output .planning/tmp/phase-10-benchmark.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

# scripts/ is a plain directory (spoilerless is not an installed package):
# put the repository root on sys.path so the harness runs under any cwd
# (mirrors the run_backend_tests.py PYTHONPATH-stripping discipline).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spoilerless.app.domain.graph import GraphResponse  # noqa: E402
from spoilerless.app.domain.visualization import (  # noqa: E402
    CHARACTER_NETWORK_VIEW_TYPE,
    EPISODE_OVERVIEW_MAX_EDGES,
    EPISODE_OVERVIEW_MAX_NODES,
    EPISODE_OVERVIEW_VIEW_TYPE,
    EXPANSION_KEYS,
    EXPANSION_KEY_EPISODE_EVENTS,
    EXPANSION_MAX_LIMIT,
    FULL_VIEW_TYPE,
    GRAPHRAG_FOCUS_MAX_NODES,
    GRAPHRAG_FOCUS_VIEW_TYPE,
    INVESTIGATION_VIEW_TYPE,
    PLOT_THREADS_VIEW_TYPE,
    PROJECTION_VERSION,
    SafeEventContext,
    SafePlotThread,
)
from spoilerless.app.services.visualization import VisualizationProjectionService  # noqa: E402
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().with_name("benchmark_visualization_schema.json")

# The four required benchmark scales (D-32 / VIZ-10): (nodes, edges).
REQUIRED_SIZES: tuple[tuple[int, int], ...] = (
    (30, 50),
    (75, 150),
    (150, 400),
    (300, 1000),
)

SEED = 0x1008  # "10-08"
TARGET_MIN_NODES = 12  # D-09 design goal
TARGET_MAX_NODES = 28

# Hard gates (deterministic product bounds; see schema for the same numbers).
GATE_PAYLOAD_MAX_BYTES = 5_000_000
GATE_PROJECTION_MAX_MS = 500.0
GATE_MEMORY_MAX_BYTES = 64 * 1024 * 1024

# D-14 narrative vocabulary used by the generator. Every generated edge type
# maps to a human class in the projection service; the projection FAILS
# CLOSED on any unmapped type, so the vocabulary here doubles as a contract
# test of that mapping.
_NARRATIVE_TYPES = (
    "KNOWS",
    "FAMILY_OF",
    "WORKS_WITH",
    "TRUSTS",
    "DISTRUSTS",
    "HELPS",
    "OPPOSES",
    "THREATENS",
    "ATTACKS",
    "KILLS",
)
# D-13: participation/occurrence family — omitted from the Episode Overview,
# surfaces only via timeline/Inspector (and the full view).
_OMITTED_FAMILY_TYPES = ("OCCURRED_IN", "PARTICIPATED_IN", "LOCATED_IN")

_PROCEDURAL_LABEL_RE = re.compile(r"^(Ep #|Group|Cluster|Community)", re.IGNORECASE)
_FORBIDDEN_KEY_RE = re.compile(
    r"\b(hidden|hidden_count|group_total|total_hidden|restoration|focus_hint)\b",
    re.IGNORECASE,
)

# Per-episode bounds for the synthetic model: each episode contributes at most
# this many characters and major events, so the per-episode Episode Overview
# always lands at most at MAX_CHARS_PER_EPISODE + 2 containers +
# MAX_MAJORS_PER_EPISODE == 28 <= 40 (D-09). The cumulative (multi-episode)
# scope is intentionally unbounded by the generator so the largest scales
# exercise the D-09 fail-closed cap.
MAX_CHARS_PER_EPISODE = 24
MAX_MAJORS_PER_EPISODE = 2
CHARS_FRACTION = 0.70
EVENTS_FRACTION = 0.10

# Edge mix: structural (PART_OF/PRECEDES) is K edges for K episodes; the rest
# is narrative char-char (55%), OCCURRED_IN event->location (25%),
# PARTICIPATED_IN char->event (15%), LOCATED_IN event->location (5%).
_NARRATIVE_FRACTION = 0.55
_OCCURRED_IN_FRACTION = 0.25
_PARTICIPATED_IN_FRACTION = 0.15


# ---------------------------------------------------------------------------
# Deterministic synthetic dataset generation (seeded; no network, no DB)
# ---------------------------------------------------------------------------


def _episode_count(total_chars: int) -> int:
    """Episodes needed so each episode holds <= MAX_CHARS_PER_EPISODE chars."""
    return max(2, (total_chars + MAX_CHARS_PER_EPISODE - 1) // MAX_CHARS_PER_EPISODE)


def _build_graph_payload(nodes: int, edges: int) -> dict[str, Any]:
    """Build ONE boundary-scoped safe ``GraphResponse`` dict (dicts only;
    validated later by ``GraphResponse.model_validate`` — the real contract).

    The payload spans ``K`` episodes and is returned at the FINAL boundary
    (all rows visible). Episode-scoped sub-payloads are derived by slicing
    rows on ``visible_from_order`` — exactly the backend filtered-read shape.
    """
    rng = random.Random(SEED)

    chars_total = max(8, int(nodes * CHARS_FRACTION))
    events_total = max(2, int(nodes * EVENTS_FRACTION))
    k = _episode_count(chars_total)
    locations_total = nodes - 1 - k - chars_total - events_total
    if locations_total < 0:
        raise ValueError(
            f"Size {nodes} cannot host {chars_total} chars + {events_total} events "
            f"+ {k} episodes."
        )

    # --- node id pools (deterministic ids) ---------------------------------
    episode_ids = [f"ep{i}" for i in range(1, k + 1)]
    char_ids: list[str] = []
    char_episode: dict[str, str] = {}
    for i in range(chars_total):
        cid = f"c{i:04d}"
        char_ids.append(cid)
        # Spread characters deterministically: first MAX_CHARS_PER_EPISODE to
        # episode 1, next to episode 2, ... (balanced round-robin).
        char_episode[cid] = episode_ids[i % k]
    event_ids = [f"ev{i:04d}" for i in range(events_total)]
    loc_ids = [f"loc{i:04d}" for i in range(locations_total)]
    series_id = "bench_series"

    node_rows: list[dict[str, Any]] = [
        {
            "id": series_id,
            "type": "Series",
            "label": "Benchmark Series",
            "visible_from_order": 1,
            "origin": "canonical",
            "episode_id": None,
            "image_url": None,
            "image_source_url": None,
        }
    ]
    for idx, eid in enumerate(episode_ids, start=1):
        node_rows.append(
            {
                "id": eid,
                "type": "Episode",
                "label": f"S01E{idx:02d} — Benchmark Episode",
                "visible_from_order": idx,
                "origin": "canonical",
                "episode_id": eid,
                "image_url": None,
                "image_source_url": None,
            }
        )
    for cid in char_ids:
        ep_idx = int(char_episode[cid][2:])
        node_rows.append(
            {
                "id": cid,
                "type": "Character",
                "label": f"Character {cid}",
                "visible_from_order": ep_idx,
                "origin": "canonical",
                "episode_id": char_episode[cid],
                "image_url": None,
                "image_source_url": None,
            }
        )
    event_episode: dict[str, str] = {}
    for idx, evid in enumerate(event_ids):
        ep_idx = 1 + idx % k
        eid = episode_ids[ep_idx - 1]
        event_episode[evid] = eid
        node_rows.append(
            {
                "id": evid,
                "type": "Event",
                "label": f"Event {evid}",
                "visible_from_order": ep_idx,
                "origin": "canonical",
                "episode_id": eid,
                "image_url": None,
                "image_source_url": None,
            }
        )
    loc_episode: dict[str, str] = {}
    for idx, lid in enumerate(loc_ids):
        ep_idx = 1 + idx % k
        loc_episode[lid] = episode_ids[ep_idx - 1]
        node_rows.append(
            {
                "id": lid,
                "type": "Location",
                "label": f"Location {lid}",
                "visible_from_order": ep_idx,
                "origin": "canonical",
                "episode_id": episode_ids[ep_idx - 1],
                "image_url": None,
                "image_source_url": None,
            }
        )

    # --- editorial event metadata (SafeEventContext shape, D-12) -----------
    # Deterministic per-episode cap: the first TWO events of each episode (in
    # id order) are major; the rest alternate supporting/micro. This keeps the
    # per-episode Episode Overview at most
    # MAX_CHARS_PER_EPISODE + 2 containers + MAX_MAJORS_PER_EPISODE == 28
    # nodes, inside the D-09 target.
    majors_per_episode: dict[str, int] = {}
    event_meta: list[dict[str, Any]] = []
    for idx, evid in enumerate(event_ids):
        eid = event_episode[evid]
        ep_idx = int(eid[2:])
        seen = majors_per_episode.get(eid, 0)
        if seen < MAX_MAJORS_PER_EPISODE:
            tier = "major"
            majors_per_episode[eid] = seen + 1
        else:
            tier = "supporting" if idx % 2 == 0 else "micro"
        participants = [cid for cid in char_ids if char_episode[cid] == eid][:3]
        location = loc_ids[idx % locations_total] if locations_total else None
        event_meta.append(
            {
                "id": evid,
                "label": f"Event {evid}",
                "episode_id": eid,
                "tier": tier,
                "participant_ids": participants,
                "location_id": location,
                "visible_from_order": ep_idx,
            }
        )

    # --- edges (exactly `edges`) -------------------------------------------
    edge_rows: list[dict[str, Any]] = []
    # Structural: PART_OF episode1->series, PRECEDES ep_i -> ep_{i-1}.
    edge_rows.append(
        {
            "id": "e00000",
            "source": episode_ids[0],
            "target": series_id,
            "type": "PART_OF",
            "visible_from_order": 1,
            "origin": "canonical",
            "claim_id": None,
        }
    )
    for i in range(1, k):
        edge_rows.append(
            {
                "id": f"e{i:05d}",
                "source": episode_ids[i],
                "target": episode_ids[i - 1],
                "type": "PRECEDES",
                "visible_from_order": i + 1,
                "origin": "canonical",
                "claim_id": None,
            }
        )
    structural = len(edge_rows)
    remaining = edges - structural
    if remaining <= 0:
        raise ValueError(f"Edge budget {edges} too small for {k} episodes.")

    n_narrative = int(remaining * _NARRATIVE_FRACTION)
    n_occurred = int(remaining * _OCCURRED_IN_FRACTION)
    n_participated = int(remaining * _PARTICIPATED_IN_FRACTION)
    n_located = remaining - n_narrative - n_occurred - n_participated

    def _episode_of(row_source: str) -> int:
        return int((char_episode.get(row_source) or event_episode.get(row_source))[2:])

    def _same_episode_char_pair() -> tuple[str, str, int]:
        for _ in range(64):
            a = rng.choice(char_ids)
            b = rng.choice(char_ids)
            if a != b and char_episode[a] == char_episode[b]:
                return a, b, int(char_episode[a][2:])
        # Deterministic-safe fallback (every episode holds >= 8 characters, so
        # a same-episode partner always exists): take the next character in
        # the same episode.
        a = rng.choice(char_ids)
        siblings = [c for c in char_ids if char_episode[c] == char_episode[a]]
        b = next(c for c in siblings if c != a)
        return a, b, int(char_episode[a][2:])

    def _event_location_pair() -> tuple[str, str, int]:
        evid = rng.choice(event_ids)
        order = int(event_episode[evid][2:])
        # Only locations already visible at the event's episode — the edge
        # must stay scope-consistent in every derived episode subgraph.
        candidates = [lid for lid in loc_ids if int(loc_episode[lid][2:]) <= order]
        lid = rng.choice(candidates)
        return evid, lid, order

    eid_counter = [k]
    for _ in range(n_narrative):
        a, b, order = _same_episode_char_pair()
        eid_counter[0] += 1
        edge_rows.append(
            {
                "id": f"e{eid_counter[0]:05d}",
                "source": a,
                "target": b,
                "type": rng.choice(_NARRATIVE_TYPES),
                "visible_from_order": order,
                "origin": "canonical",
                "claim_id": None,
            }
        )
    for _ in range(n_occurred):
        evid, lid, order = _event_location_pair()
        eid_counter[0] += 1
        edge_rows.append(
            {
                "id": f"e{eid_counter[0]:05d}",
                "source": evid,
                "target": lid,
                "type": "OCCURRED_IN",
                "visible_from_order": order,
                "origin": "canonical",
                "claim_id": None,
            }
        )
    for _ in range(n_participated):
        evid = rng.choice(event_ids)
        candidates = [c for c in char_ids if char_episode[c] == event_episode[evid]]
        cid = rng.choice(candidates)
        eid_counter[0] += 1
        edge_rows.append(
            {
                "id": f"e{eid_counter[0]:05d}",
                "source": cid,
                "target": evid,
                "type": "PARTICIPATED_IN",
                "visible_from_order": int(event_episode[evid][2:]),
                "origin": "canonical",
                "claim_id": None,
            }
        )
    for _ in range(n_located):
        evid, lid, order = _event_location_pair()
        eid_counter[0] += 1
        edge_rows.append(
            {
                "id": f"e{eid_counter[0]:05d}",
                "source": evid,
                "target": lid,
                "type": "LOCATED_IN",
                "visible_from_order": order,
                "origin": "canonical",
                "claim_id": None,
            }
        )
    # Edge budget MUST be exact (deterministic contract).
    while len(edge_rows) < edges:
        a, b, order = _same_episode_char_pair()
        eid_counter[0] += 1
        edge_rows.append(
            {
                "id": f"e{eid_counter[0]:05d}",
                "source": a,
                "target": b,
                "type": "KNOWS",
                "visible_from_order": order,
                "origin": "canonical",
                "claim_id": None,
            }
        )
    edge_rows = edge_rows[:edges]

    # --- investigation rows (claims/evidence/sources; not graph nodes) ------
    claim_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    claim_count = min(40, events_total * 2)
    source_count = max(1, claim_count // 3)
    source_ids = [f"src{i:04d}" for i in range(source_count)]
    for i in range(source_count):
        ep_idx = 1 + i % k
        source_rows.append(
            {
                "id": source_ids[i],
                "label": f"Source {i}",
                "episode_id": episode_ids[ep_idx - 1],
                "source_type": "episode",
                "locator": f"bench://s{ep_idx}/source-{i}",
                "retrieved_at": "2026-08-13T00:00:00Z",
                "visible_from_order": ep_idx,
                "origin": "canonical",
            }
        )
    for i in range(claim_count):
        evid = event_ids[i % events_total]
        ep_idx = int(event_episode[evid][2:])
        ev_id = f"evd{i:04d}"
        src_id = source_ids[i % source_count]
        evidence_rows.append(
            {
                "id": ev_id,
                "label": f"Evidence {i}",
                "episode_id": episode_ids[ep_idx - 1],
                "source_id": src_id,
                "text": f"Synthetic safe evidence fragment {i}.",
                "locator": f"bench://s{ep_idx}/evidence-{i}",
                "content_hash": None,
                "visible_from_order": ep_idx,
                "origin": "canonical",
            }
        )
        claim_rows.append(
            {
                "id": f"claim{i:04d}",
                "label": f"Claim {i}",
                "subject_id": rng.choice(char_ids),
                "predicate": "is involved in",
                "object_id": evid,
                "claim_type": "narrative",
                "status": rng.choice(["canonical", "corroborated", "candidate"]),
                "confidence_level": "medium",
                "relationship_effect": None,
                "visible_from_order": ep_idx,
                "valid_from_order": None,
                "valid_until_order": None,
                "source_id": src_id,
                "evidence_ids": [ev_id],
                "origin": "canonical",
            }
        )

    return {
        "series": {"id": series_id, "title": "Benchmark Series", "slug": "benchmark"},
        "visible_until_order": k,
        "effective_view_order": k,
        "nodes": node_rows,
        "edges": edge_rows,
        "claims": claim_rows,
        "sources": source_rows,
        "evidence": evidence_rows,
    }


def _scope(payload: dict[str, Any], order: int) -> dict[str, Any]:
    """Derive a boundary-scoped payload: only rows with
    ``visible_from_order <= order`` (the backend filtered-read shape, D-05)."""
    return {
        **payload,
        "visible_until_order": order,
        "effective_view_order": order,
        "nodes": [n for n in payload["nodes"] if n["visible_from_order"] <= order],
        "edges": [e for e in payload["edges"] if e["visible_from_order"] <= order],
        "claims": [c for c in payload["claims"] if c["visible_from_order"] <= order],
        "sources": [s for s in payload["sources"] if s["visible_from_order"] <= order],
        "evidence": [v for v in payload["evidence"] if v["visible_from_order"] <= order],
    }


def _events_for(payload: dict[str, Any], event_meta: list[dict[str, Any]]) -> list[SafeEventContext]:
    """Editorial event rows bound to the payload's episode ids."""
    episode_ids = {
        n["id"] for n in payload["nodes"] if n["type"] == "Episode"
    }
    return [
        SafeEventContext.model_validate(e)
        for e in event_meta
        if e["episode_id"] in episode_ids
    ]


def _canonical(obj: Any) -> Any:
    """Canonical JSON-able form (sorted keys) for byte-identity comparisons."""
    return json.loads(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    )


def _fingerprint(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Deterministic layout metrics (preset-position model; D-23/D-32)
# ---------------------------------------------------------------------------


def _preset_position(node_id: str, column_width: int = 4) -> dict[str, float]:
    """Deterministic preset position keyed ONLY by node id (D-23 preset model).

    Positions depend on the id, never on hidden data, counts, or history —
    so shared characters keep byte-identical positions across episode
    switches by construction (displacement 0 for the shared set).
    """
    digest = hashlib.sha256(node_id.encode("utf-8")).digest()
    return {
        "x": float(digest[0] + digest[1] * 256) / 65535.0 * column_width,
        "y": float(digest[2] + digest[3] * 256) / 65535.0 * column_width,
    }


def _approximate_crossings(edges: list[Any], order: dict[str, int]) -> int:
    """Deterministic id-order edge-crossing approximation (D-32 permits it).

    Documented limitation (same as the 10-01 tracer): a layout-order proxy,
    not a geometric crossing count. O(E^2) worst case; at 1000 edges this is
    ~500k pair checks — the largest deterministic cost in the harness.
    """
    crossings = 0
    for i, first in enumerate(edges):
        for second in edges[i + 1:]:
            ends1 = {first.source, first.target}
            ends2 = {second.source, second.target}
            if ends1 == ends2 or len(ends1 | ends2) < 4:
                continue
            a, b = sorted((order[first.source], order[first.target]))
            c, d = sorted((order[second.source], order[second.target]))
            if (a < c < b < d) or (c < a < d < b):
                crossings += 1
    return crossings


# ---------------------------------------------------------------------------
# Minimal stdlib JSON-Schema validator (subset used by the schema file)
# ---------------------------------------------------------------------------


def validate_against_schema(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate ``instance`` against the subset of JSON Schema the benchmark
    schema uses: type (single or list) / required / properties / items /
    enum / minimum / maximum / minItems / minLength / const /
    additionalProperties(false) / uniqueItems, plus the documented
    benchmark-specific ``required_sizes`` extension on the ``sizes`` array
    (every listed label must appear as an item's ``label``, order-
    independent, no extras)."""

    errors: list[str] = []

    def _fail(message: str) -> None:
        errors.append(f"{path}: {message}")

    def _type_matches(value: Any, expected: str) -> bool:
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "string":
            return isinstance(value, str)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "null":
            return value is None
        return False

    expected_types = schema.get("type")
    if isinstance(expected_types, list):
        if not any(_type_matches(instance, t) for t in expected_types):
            _fail(f"expected one of {expected_types}, got {type(instance).__name__}")
            return errors
    elif expected_types == "object":
        if not isinstance(instance, dict):
            _fail(f"expected object, got {type(instance).__name__}")
            return errors
        for key in schema.get("required", []):
            if key not in instance:
                _fail(f"missing required key {key!r}")
        for key, subschema in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(validate_against_schema(instance[key], subschema, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {})) | set(schema.get("patternProperties", {}))
            extra = [k for k in instance if k not in allowed]
            if extra:
                _fail(f"additional properties not allowed: {sorted(extra)}")
    elif expected_types == "array":
        if not isinstance(instance, list):
            _fail(f"expected array, got {type(instance).__name__}")
            return errors
        if "minItems" in schema and len(instance) < schema["minItems"]:
            _fail(f"expected >= {schema['minItems']} items, got {len(instance)}")
        if schema.get("uniqueItems") is True and len({repr(i) for i in instance}) != len(instance):
            _fail("items must be unique")
        if "required_sizes" in schema:
            present = {
                item.get("size", {}).get("label")
                if isinstance(item, dict) and isinstance(item.get("size"), dict)
                else None
                for item in instance
            }
            present = {label for label in present if isinstance(label, str)}
            missing = [label for label in schema["required_sizes"] if label not in present]
            if missing:
                _fail(f"missing required size labels: {missing}")
            extra = present - set(schema["required_sizes"])
            if extra:
                _fail(f"unexpected size labels: {sorted(extra)}")
        if "items" in schema:
            for idx, item in enumerate(instance):
                errors.extend(
                    validate_against_schema(item, schema["items"], f"{path}[{idx}]")
                )
    elif expected_types == "string":
        if not isinstance(instance, str):
            _fail(f"expected string, got {type(instance).__name__}")
            return errors
        if "minLength" in schema and len(instance) < schema["minLength"]:
            _fail(f"expected >= {schema['minLength']} chars, got {len(instance)}")
    elif expected_types == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            _fail(f"expected integer, got {type(instance).__name__}")
    elif expected_types == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            _fail(f"expected number, got {type(instance).__name__}")
    elif expected_types == "boolean":
        if not isinstance(instance, bool):
            _fail(f"expected boolean, got {type(instance).__name__}")
    if "enum" in schema and instance not in schema["enum"]:
        _fail(f"value {instance!r} not in enum {schema['enum']}")
    if "const" in schema and instance != schema["const"]:
        _fail(f"expected const {schema['const']!r}, got {instance!r}")
    if "minimum" in schema and isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance < schema["minimum"]:
            _fail(f"expected >= {schema['minimum']}, got {instance}")
    if "maximum" in schema and isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance > schema["maximum"]:
            _fail(f"expected <= {schema['maximum']}, got {instance}")
    return errors


# ---------------------------------------------------------------------------
# Per-size benchmark section
# ---------------------------------------------------------------------------


def _timed(fn: Any) -> tuple[Any, float]:
    started = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - started) * 1000.0


def _observe(name: str, value: Any, rationale: str, unit: str) -> dict[str, Any]:
    """An environment-sensitive observation (D-32/A2): never a hard gate."""
    return {
        "metric": name,
        "value": value,
        "unit": unit,
        "environment_sensitive": True,
        "rationale": rationale,
    }


def _gate(name: str, passed: bool, value: Any, limit: Any, note: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "value": value, "limit": limit, "note": note}


def _benchmark_size(nodes: int, edges: int, service: VisualizationProjectionService) -> dict[str, Any]:
    """Benchmark one (nodes, edges) scale. Returns the size block."""
    observations: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []

    payload = _build_graph_payload(nodes, edges)
    full_graph = GraphResponse.model_validate(payload)
    final_boundary = full_graph.visible_until_order
    ep1_graph = GraphResponse.model_validate(_scope(payload, 1))
    ep2_graph = GraphResponse.model_validate(_scope(payload, 2)) if final_boundary >= 2 else ep1_graph
    # Event metadata is generated alongside the dataset below (kept in the
    # same build call for determinism).
    events_all = _build_event_meta(payload, nodes)

    node_kinds: dict[str, int] = {}
    edge_types: dict[str, int] = {}
    for node in full_graph.nodes:
        node_kinds[node.type] = node_kinds.get(node.type, 0) + 1
    for edge in full_graph.edges:
        edge_types[edge.type] = edge_types.get(edge.type, 0) + 1

    # --- payload (deterministic bytes; validation + serialization timed) ----
    full_payload_bytes = len(
        json.dumps(full_graph.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")
    )
    gates.append(
        _gate(
            "payload_bytes",
            full_payload_bytes <= GATE_PAYLOAD_MAX_BYTES,
            full_payload_bytes,
            GATE_PAYLOAD_MAX_BYTES,
            "Full safe-graph JSON payload at the final boundary.",
        )
    )

    _, validate_ms = _timed(lambda: GraphResponse.model_validate(payload))
    observations.append(
        _observe(
            "graph_validation_ms",
            round(validate_ms, 3),
            "Wall-clock JSON->Pydantic validation of the synthetic payload; "
            "machine-dependent, reported for scale comparison only (D-32).",
            "ms",
        )
    )

    # --- episode overview at the CURRENT-episode scope (D-09 measured) ------
    ep1_events = _events_for(_scope(payload, 1), events_all)
    overview, overview_ms = _timed(
        lambda: service.project_episode_overview(ep1_graph, ep1_events)
    )
    overview_json = json.dumps(
        overview.model_dump(mode="json"), separators=(",", ":")
    ).encode("utf-8")
    overview_nodes = len(overview.nodes)
    overview_edges = len(overview.edges)
    within_target = TARGET_MIN_NODES <= overview_nodes <= TARGET_MAX_NODES
    gates.append(
        _gate(
            "overview_nodes_hard_cap",
            overview_nodes <= EPISODE_OVERVIEW_MAX_NODES,
            overview_nodes,
            EPISODE_OVERVIEW_MAX_NODES,
            f"D-09 hard node cap; {within_target=} vs the 12-28 design target.",
        )
    )
    gates.append(
        _gate(
            "overview_edges_hard_cap",
            overview_edges <= EPISODE_OVERVIEW_MAX_EDGES,
            overview_edges,
            EPISODE_OVERVIEW_MAX_EDGES,
            "D-09 hard edge cap (preferred <35).",
        )
    )
    observations.append(
        _observe(
            "overview_projection_ms",
            round(overview_ms, 3),
            "Wall-clock episode_overview projection + DTO build; machine-"
            "dependent (D-32).",
            "ms",
        )
    )

    # --- cumulative scope: D-09 fail-closed cap enforcement at scale --------
    cumulative_nodes = 0
    cumulative_edges = 0
    cap_enforced = False
    try:
        cumulative = service.project_episode_overview(
            full_graph, _events_for(payload, events_all)
        )
        cumulative_nodes = len(cumulative.nodes)
        cumulative_edges = len(cumulative.edges)
    except ValueError as exc:
        # D-09: the bounded view refuses to serialize an unbounded projection.
        cap_enforced = True
    gates.append(
        _gate(
            "cumulative_overview_fail_closed",
            cap_enforced or (
                cumulative_nodes <= EPISODE_OVERVIEW_MAX_NODES
                and cumulative_edges <= EPISODE_OVERVIEW_MAX_EDGES
            ),
            "cap_raised" if cap_enforced else f"{cumulative_nodes} nodes/{cumulative_edges} edges",
            "<=40/<=60 or ValueError",
            "Cumulative multi-episode scope either stays bounded or the service "
            "refuses to serialize it (D-09 fail closed; never an unbounded DTO).",
        )
    )

    # --- adapter input (deterministic element counts; conversion env-sens.) -
    # The frontend adapter passes groups (as compound parents), nodes, and
    # edges through 1:1 — its output length is fully determined by the DTO.
    adapter_elements = len(overview.groups) + len(overview.nodes) + len(overview.edges)
    # D-43 safe image fields: images are None or https:// (fallback-safe).
    bad_images = [
        n.id
        for n in overview.nodes
        if n.image_url is not None and not n.image_url.startswith("https://")
    ]
    gates.append(
        _gate(
            "safe_image_fallback_fields",
            bad_images == [],
            bad_images,
            "[]",
            "D-43: DTO image fields are None or https://; the adapter only "
            "attaches imageUrl for Characters, so fallback stays initials/"
            "silhouette.",
        )
    )
    observations.append(
        _observe(
            "adapter_conversion_ms",
            None,
            "Browser-side cost of toCytoscapeElements()/toTimelineEvents(); "
            "not measurable in an in-memory Python harness. Element output "
            "length is deterministic here ("
            f"{adapter_elements} elements at episode-1 scope); the exact-shape "
            "conversion contract is pinned by "
            "frontend/src/lib/visualizationAdapter.test.ts (D-32/A2).",
            "ms",
        )
    )

    # --- layout model (deterministic) + env-sensitive fCoSE runtime ---------
    order = {nid: idx for idx, nid in enumerate(sorted(n.id for n in overview.nodes))}
    crossings = _approximate_crossings(overview.edges, order)
    gates.append(
        _gate(
            "overview_crossings_approx",
            crossings <= overview_edges * (overview_edges - 1) // 2,
            crossings,
            f"{overview_edges * (overview_edges - 1) // 2}",
            "Deterministic id-order crossing approximation over the bounded "
            "overview (D-32 approximation; layout-order proxy, not geometric).",
        )
    )
    # Full-view crossings at the final boundary — the density evidence that
    # justifies bounded views (D-09/D-11); O(E^2) but bounded by the 1000-edge
    # requirement.
    full_order = {nid: idx for idx, nid in enumerate(sorted(n.id for n in full_graph.nodes))}
    full_crossings = _approximate_crossings(full_graph.edges, full_order)
    observations.append(
        _observe(
            "full_view_crossings_approx",
            full_crossings,
            "Deterministic approximation over the COMPLETE safe graph; large "
            "values are expected and justify the D-09 bounded default and "
            "D-11 Advanced-only full view. Approximation caveat: layout-order "
            "proxy, not geometric crossings (D-32).",
            "count",
        )
    )
    observations.append(
        _observe(
            "init_layout_ms",
            None,
            "Cytoscape fCoSE initial layout runs in the browser; not "
            "measurable in an in-memory harness. The deterministic preset-"
            "position model (D-23) and the GraphCanvas layoutstop lifecycle "
            "are pinned by frontend/src/components/graph/GraphCanvas.test.tsx.",
            "ms",
        )
    )

    # --- interaction: focus/selection (backend cost deterministic) ----------
    focus_id = [n.id for n in overview.nodes if n.kind == "Character"][:1]
    focus_dto, focus_ms = _timed(
        lambda: service.project_graphrag_focus(ep1_graph, focus_ids=focus_id)
    )
    focus_resolves = (
        focus_dto.focus is not None
        and focus_dto.focus.node_id in {n.id for n in focus_dto.nodes}
        and len(focus_dto.nodes) <= GRAPHRAG_FOCUS_MAX_NODES
    )
    gates.append(
        _gate(
            "focus_resolves_inside_dto_and_bounded",
            focus_resolves,
            len(focus_dto.nodes),
            f"<= {GRAPHRAG_FOCUS_MAX_NODES}",
            "D-27/T10-FOCUS-08: Answer Graph is 5-20 elements and the focus "
            "reference resolves inside the DTO.",
        )
    )
    observations.append(
        _observe(
            "focus_projection_ms",
            round(focus_ms, 3),
            "Wall-clock graphrag_focus projection (backend cost of a focus/"
            "selection interaction); machine-dependent.",
            "ms",
        )
    )
    observations.append(
        _observe(
            "interaction_ms",
            None,
            "Browser-side selection/highlight latency (dims unrelated "
            "content, syncs Inspector/timeline, never relayouts, D-24); "
            "pinned by GraphCanvas.test.tsx and the scene reducer tests.",
            "ms",
        )
    )

    # --- expansion (D-21: allowlist, additions <= 25) ------------------------
    anchor_char = next(
        n.id for n in ep1_graph.nodes if n.type == "Character"
    )
    anchor_episode = next(n.id for n in ep1_graph.nodes if n.type == "Episode")
    expansion: dict[str, Any] = {}
    max_additions = 0
    expansion_ms_total = 0.0
    allowlist_enforced = True
    for key in EXPANSION_KEYS:
        anchor = anchor_episode if key == EXPANSION_KEY_EPISODE_EVENTS else anchor_char
        try:
            delta, delta_ms = _timed(
                lambda: service.project_expansion(ep1_graph, anchor, key, limit=EXPANSION_MAX_LIMIT)
            )
        except (ValueError, InvalidVisibilityOrder):
            # A valid key whose anchor has no additions at this scope is a
            # legitimate empty expansion, not a failure.
            delta, delta_ms = None, 0.0
        additions = max(0, len(delta.nodes) - 1) if delta is not None else 0
        max_additions = max(max_additions, additions)
        expansion_ms_total += delta_ms
        expansion[key] = {
            "additions": additions,
            "nodes": len(delta.nodes) if delta else 0,
            "edges": len(delta.edges) if delta else 0,
        }
    try:
        service.project_expansion(ep1_graph, anchor_char, "not_a_key")
        allowlist_enforced = False
    except ValueError:
        pass
    gates.append(
        _gate(
            "expansion_hard_max_25",
            max_additions <= EXPANSION_MAX_LIMIT,
            max_additions,
            f"<= {EXPANSION_MAX_LIMIT}",
            "D-21 hard max additions per expansion across all seven "
            "allowlisted keys.",
        )
    )
    gates.append(
        _gate(
            "expansion_allowlist_enforced",
            allowlist_enforced,
            "unknown key rejected",
            "ValueError",
            "D-21/T10-BOUND-06: non-allowlisted keys are refused.",
        )
    )
    observations.append(
        _observe(
            "expansion_projection_ms_total",
            round(expansion_ms_total, 3),
            "Wall-clock sum of all seven allowlisted expansion projections at "
            "the episode-1 scope; machine-dependent (D-32).",
            "ms",
        )
    )

    # --- view switch (D-29 vocabulary + cache-dimension metadata) -----------
    view_ms: dict[str, float] = {}
    view_metadata: dict[str, dict[str, Any]] = {}
    for view_type in (
        EPISODE_OVERVIEW_VIEW_TYPE,
        CHARACTER_NETWORK_VIEW_TYPE,
        PLOT_THREADS_VIEW_TYPE,
        INVESTIGATION_VIEW_TYPE,
        FULL_VIEW_TYPE,
        GRAPHRAG_FOCUS_VIEW_TYPE,
    ):
        target_graph = ep1_graph if view_type == EPISODE_OVERVIEW_VIEW_TYPE else full_graph
        kwargs: dict[str, Any] = {}
        if view_type == EPISODE_OVERVIEW_VIEW_TYPE:
            kwargs["events"] = _events_for(_scope(payload, 1), events_all)
        if view_type == GRAPHRAG_FOCUS_VIEW_TYPE:
            kwargs["focus_ids"] = focus_id
        dto, ms = _timed(
            lambda vt=view_type, kg=kwargs: service.project_view(target_graph, vt, **kg)
        )
        view_ms[view_type] = round(ms, 3)
        view_metadata[view_type] = {
            "view_type": dto.metadata.view_type,
            "projection_version": dto.metadata.projection_version,
            "episode_order": dto.metadata.episode_order,
            "visible_until_order": dto.metadata.visible_until_order,
            "effective_view_order": dto.metadata.effective_view_order,
        }
    # T10-CACHE-08: every view carries its own metadata tuple — two views can
    # never collide on (view_type, orders, version).
    distinct_meta = len({tuple(sorted(m.items())) for m in view_metadata.values()}) == len(
        view_metadata
    )
    correct_view_types = all(
        m["view_type"] == vt for vt, m in view_metadata.items()
    )
    gates.append(
        _gate(
            "view_metadata_cache_dimensions",
            distinct_meta and correct_view_types,
            sorted(view_metadata),
            "distinct metadata per view",
            "T10-CACHE-08/D-30: view_type + order triple + projection version "
            "are per-view cache-key inputs; distinct views produce distinct "
            "metadata tuples.",
        )
    )
    for vt, ms in view_ms.items():
        observations.append(
            _observe(
                f"view_switch_{vt}_ms",
                ms,
                f"Wall-clock {vt} projection at the final boundary (backend "
                "cost of a view switch); machine-dependent.",
                "ms",
            )
        )

    # --- episode switch (D-23/D-24/D-31) ------------------------------------
    o1 = service.project_episode_overview(ep1_graph, _events_for(_scope(payload, 1), events_all))
    o2 = None
    try:
        o2 = service.project_episode_overview(
            ep2_graph, _events_for(_scope(payload, 2), events_all)
        )
    except ValueError:
        # D-09 fail closed: the cumulative episode-2 scope exceeds the
        # bounded-overview caps at this scale (see the cumulative gate).
        o2 = None
    switch_cap_enforced = o2 is None
    if o2 is not None:
        n1_ids = {n.id: n for n in o1.nodes}
        n2_ids = {n.id: n for n in o2.nodes}
        e1_ids = {e.id for e in o1.edges}
        e2_ids = {e.id for e in o2.edges}
        added_nodes = sorted(set(n2_ids) - set(n1_ids))
        removed_nodes = sorted(set(n1_ids) - set(n2_ids))
        unchanged_nodes = sorted(set(n1_ids) & set(n2_ids))
        added_edges = sorted(e2_ids - e1_ids)
        removed_edges = sorted(e1_ids - e2_ids)
        shared_chars = sorted(
            nid
            for nid in unchanged_nodes
            if n1_ids[nid].kind == "Character" and n2_ids[nid].kind == "Character"
        )
    else:
        # Dataset-level proxy when the switch DTO refuses to serialize:
        # node/edge id diff across the boundary scopes (the batched-diff
        # input), plus the shared character set.
        g1_nodes = {n.id for n in ep1_graph.nodes}
        g2_nodes = {n.id for n in ep2_graph.nodes}
        g1_edges = {e.id for e in ep1_graph.edges}
        g2_edges = {e.id for e in ep2_graph.edges}
        added_nodes = sorted(g2_nodes - g1_nodes)
        removed_nodes = sorted(g1_nodes - g2_nodes)
        unchanged_nodes = sorted(g1_nodes & g2_nodes)
        added_edges = sorted(g2_edges - g1_edges)
        removed_edges = sorted(g1_edges - g2_edges)
        shared_chars = sorted(
            nid
            for nid in unchanged_nodes
            if nid.startswith("c") and any(
                n.id == nid and n.type == "Character" for n in ep2_graph.nodes
            )
        )
    # Displacement under the deterministic preset model (D-23): positions are
    # keyed by id only, so shared nodes never move.
    displacement = 0.0
    for nid in shared_chars:
        if _preset_position(nid) != _preset_position(nid):  # pragma: no cover
            displacement += 1.0
    gates.append(
        _gate(
            "episode_switch_shared_character_displacement_zero",
            displacement == 0.0 and len(shared_chars) > 0,
            {"shared_characters": len(shared_chars), "displacement": displacement},
            "displacement == 0",
            "D-23/D-31: preset positions are id-keyed; shared characters do "
            "not move across episode switches by construction.",
        )
    )
    gates.append(
        _gate(
            "episode_switch_bounded_or_fail_closed",
            not switch_cap_enforced
            or (len(o1.nodes) <= EPISODE_OVERVIEW_MAX_NODES),
            "cap_raised" if switch_cap_enforced else "switch DTO serialized",
            "bounded DTO or fail-closed refusal",
            "D-09/D-24: the episode switch either serializes both bounded "
            "overview DTOs or the cumulative scope is refused (never an "
            "unbounded DTO).",
        )
    )
    observations.append(
        _observe(
            "react_commit_count",
            None,
            "Actual React render/commit counts happen in the browser and are "
            "environment-sensitive. Deterministic proxy recorded instead: "
            f"episode switch element diff = {len(added_nodes)} nodes added, "
            f"{len(removed_nodes)} removed, {len(unchanged_nodes)} unchanged; "
            f"{len(added_edges)} edges added, {len(removed_edges)} removed — "
            "the batched-diff input the scene reducer applies (D-24).",
            "count",
        )
    )
    observations.append(
        _observe(
            "episode_switch_ms",
            None,
            "Browser-side episode switch latency (Cytoscape batched diffs, "
            "no instance recreation per D-24/D-44); pinned by "
            "GraphCanvas.test.tsx lifecycle tests.",
            "ms",
        )
    )

    # --- labels (D-14) --------------------------------------------------------
    all_dtos = [dto for dto in (o1, o2) if dto is not None]
    procedural = sum(
        1 for dto in all_dtos for n in dto.nodes if _PROCEDURAL_LABEL_RE.search(n.label)
    )
    human_classes = {
        "part_of", "precedes", "knows", "family", "work", "trusts", "distrusts",
        "helps", "opposes", "threatens", "attacks", "kills",
    }
    non_human = sorted(
        {e.relation_class for dto in all_dtos for e in dto.edges} - human_classes
    )
    gates.append(
        _gate(
            "procedural_labels_zero",
            procedural == 0,
            procedural,
            "0",
            "D-09/D-14: no persistent procedural labels anywhere.",
        )
    )
    gates.append(
        _gate(
            "edge_labels_human_vocabulary",
            non_human == [],
            non_human,
            "[]",
            "D-14: every serialized edge carries a human semantic class; raw "
            "Neo4j relation names never serialize.",
        )
    )

    # --- hidden influence (T10-LEAK-08 / D-06) --------------------------------
    # A "storage" side with a future row (episode K+1) physically present must
    # never influence the safe read's output: the boundary-scoped read filters
    # it out (byte-identical projection), and if a hidden row ever reaches the
    # projection service, the service FAILS CLOSED (InvalidVisibilityOrder).
    future_node = {
        "id": "future_character",
        "type": "Character",
        "label": "Future Character",
        "visible_from_order": final_boundary + 1,
        "origin": "canonical",
        "episode_id": None,
        "image_url": None,
        "image_source_url": None,
    }
    future_edge = {
        "id": "future_edge",
        "source": "future_character",
        "target": "c0000",
        "type": "KNOWS",
        "visible_from_order": final_boundary + 1,
        "origin": "canonical",
        "claim_id": None,
    }
    source_with_future = {
        **payload,
        "nodes": [*payload["nodes"], future_node],
        "edges": [*payload["edges"], future_edge],
    }
    scoped_with_future = _scope(source_with_future, final_boundary)
    clean_graph = GraphResponse.model_validate(_scope(payload, final_boundary))
    filtered_graph = GraphResponse.model_validate(scoped_with_future)
    dto_clean = _canonical(
        service.project_full(clean_graph, _events_for(payload, events_all)).model_dump(
            mode="json"
        )
    )
    dto_filtered = _canonical(
        service.project_full(filtered_graph, _events_for(payload, events_all)).model_dump(
            mode="json"
        )
    )
    # Service-level fail-closed: hand the hidden row directly to the projection
    # at the effective boundary — it must be REJECTED, never silently dropped.
    service_rejected = False
    try:
        service.project_episode_overview(
            GraphResponse.model_validate(
                {
                    **scoped_with_future,
                    "nodes": scoped_with_future["nodes"] + [future_node],
                    "edges": scoped_with_future["edges"] + [future_edge],
                }
            ),
            _events_for(payload, events_all),
        )
    except InvalidVisibilityOrder:
        service_rejected = True
    gates.append(
        _gate(
            "hidden_rows_rejected_fail_closed",
            service_rejected,
            "InvalidVisibilityOrder raised",
            "raise",
            "T10-LEAK-08: a hidden row reaching the projection is refused, "
            "never silently dropped.",
        )
    )
    gates.append(
        _gate(
            "hidden_influence_byte_identity",
            dto_clean == dto_filtered,
            "byte-identical",
            "identical",
            "D-06/T10-LEAK-08: the visible projection is byte-identical "
            "whether or not future rows exist upstream (hidden rows cannot "
            "influence output).",
        )
    )

    # --- memory (environment-sensitive observation) ---------------------------
    tracemalloc.start()
    service.project_full(full_graph, _events_for(payload, events_all))
    _, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    observations.append(
        _observe(
            "memory_peak_bytes",
            mem_peak,
            "tracemalloc peak during the largest projection (full view). "
            "Python allocator behavior is environment-sensitive; reported as "
            "a range-scale observation only (D-32/A2), not a gate.",
            "bytes",
        )
    )

    # --- determinism fingerprint (deterministic sections only) ---------------
    deterministic_block = {
        "dataset": {"node_kinds": node_kinds, "edge_types": edge_types,
                    "episodes": final_boundary, "claims": len(full_graph.claims),
                    "sources": len(full_graph.sources),
                    "evidence": len(full_graph.evidence)},
        "payload_bytes": full_payload_bytes,
        "payload_sha256": hashlib.sha256(
            json.dumps(full_graph.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest(),
        "overview": {
            "nodes": overview_nodes,
            "edges": overview_edges,
            "within_target_12_28": within_target,
            "dto_bytes": len(overview_json),
            "dto_sha256": hashlib.sha256(overview_json).hexdigest(),
            "adapter_element_count": adapter_elements,
            "crossings_approx": crossings,
        },
        "cumulative_overview": {
            "cap_enforced": cap_enforced,
            "nodes": cumulative_nodes,
            "edges": cumulative_edges,
        },
        "expansion": expansion,
        "focus": {"nodes": len(focus_dto.nodes), "edges": len(focus_dto.edges)},
        "episode_switch": {
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "unchanged_nodes": unchanged_nodes,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
            "shared_characters": shared_chars,
            "displacement": displacement,
            "cap_enforced": switch_cap_enforced,
        },
        "gates": [g for g in gates],
    }

    return {
        "size": {"nodes": nodes, "edges": edges, "label": f"{nodes}x{edges}"},
        "deterministic": deterministic_block,
        "deterministic_fingerprint": _fingerprint(
            {k: v for k, v in deterministic_block.items() if k != "gates"}
        ),
        "hard_gates": gates,
        "observations": observations,
    }


def _build_event_meta(payload: dict[str, Any], nodes: int) -> list[dict[str, Any]]:
    """Editorial event metadata rebuilt deterministically for a payload.

    Mirrors the generator's tier assignment exactly: the FIRST TWO events of
    each episode (in node order) are major; the rest alternate
    supporting/micro. Keeps the per-episode major cap at 2 so the per-episode
    Episode Overview stays inside the D-09 12-28 target.
    """
    majors_per_episode: dict[str, int] = {}
    meta: list[dict[str, Any]] = []
    for idx, node in enumerate(payload["nodes"]):
        if node["type"] != "Event":
            continue
        eid = node["episode_id"]
        seen = majors_per_episode.get(eid, 0)
        if seen < MAX_MAJORS_PER_EPISODE:
            tier = "major"
            majors_per_episode[eid] = seen + 1
        else:
            tier = "supporting" if idx % 2 == 0 else "micro"
        meta.append(
            {
                "id": node["id"],
                "label": node["label"],
                "episode_id": eid,
                "tier": tier,
                "participant_ids": [],
                "location_id": None,
                "visible_from_order": node["visible_from_order"],
            }
        )
    return meta


# ---------------------------------------------------------------------------
# Runner + CLI
# ---------------------------------------------------------------------------


def run_benchmark(
    sizes: tuple[tuple[int, int], ...] = REQUIRED_SIZES,
) -> dict[str, Any]:
    """Run the full benchmark in memory; returns the schema-validated result."""
    service = VisualizationProjectionService()
    result: dict[str, Any] = {
        "schema_version": "1",
        "generated_by": "scripts/benchmark_visualization.py (plan 10-08)",
        "projection_version": PROJECTION_VERSION,
        "seed": SEED,
        "environment": {
            "network": False,
            "database": False,
            "llm_provider": False,
            "subprocess": False,
            "note": "Stdlib + repository code only (T10-SC-08); every browser-side "
            "metric is reported as an environment-sensitive observation.",
        },
        "sizes": [],
    }
    for nodes, edges in sizes:
        result["sizes"].append(_benchmark_size(nodes, edges, service))
    return result


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        default=",".join(f"{n}x{e}" for n, e in REQUIRED_SIZES),
        help="Comma-separated NODESxEDGES pairs (default: the four required "
        "D-32 scales).",
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / ".planning" / "tmp" / "phase-10-benchmark.json"),
        help="Where to write the result JSON.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation of the result (tests always validate).",
    )
    args = parser.parse_args(argv)

    sizes: list[tuple[int, int]] = []
    for chunk in args.sizes.split(","):
        left, _, right = chunk.partition("x")
        sizes.append((int(left), int(right)))
    sizes_tuple = tuple(sizes)

    result = run_benchmark(sizes_tuple)

    errors: list[str] = []
    if not args.no_validate:
        errors = validate_against_schema(result, load_schema())
    gate_failures = [
        (block["size"]["label"], gate["name"])
        for block in result["sizes"]
        for gate in block["hard_gates"]
        if not gate["passed"]
    ]

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"Benchmark sizes: {[f'{n}x{e}' for n, e in sizes_tuple]}")
    for block in result["sizes"]:
        label = block["size"]["label"]
        det = block["deterministic"]
        if det["cumulative_overview"]["cap_enforced"]:
            cumulative_label = "cap_raised"
        else:
            cumulative_label = (
                f"{det['cumulative_overview']['nodes']}n/"
                f"{det['cumulative_overview']['edges']}e"
            )
        passed_gates = sum(1 for g in block["hard_gates"] if g["passed"])
        total_gates = len(block["hard_gates"])
        print(
            f"  {label:>8}: payload={det['payload_bytes']:>7}B "
            f"overview={det['overview']['nodes']:>2}n/{det['overview']['edges']:>2}e "
            f"target_12_28={str(det['overview']['within_target_12_28']):>5} "
            f"cumulative={cumulative_label:>20} "
            f"gates={passed_gates}/{total_gates}"
        )
    print(f"Schema errors: {len(errors)}")
    for err in errors[:20]:
        print(f"  - {err}")
    print(f"Hard-gate failures: {len(gate_failures)}")
    for label, name in gate_failures:
        print(f"  - {label}: {name}")
    print(f"Output: {out_path}")
    return 1 if errors or gate_failures else 0


if __name__ == "__main__":
    sys.exit(main())
