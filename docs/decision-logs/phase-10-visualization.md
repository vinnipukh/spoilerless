# Decision Log — Phase 10 Episode Overview Variant (VIZ-03 / VIZ-10, D-03/D-10)

**Date:** 2026-08-13
**Plan:** 10-01 (tracer) — `.planning/phases/10-polish-finishing-touches/10-01-PLAN.md`
**Projection version:** `1.0.0` (recorded in both safe fixture metadata envelopes)
**Evidence source:** `spoilerless/tests/test_visualization_baseline.py::build_evidence()` over the
checked-in immutable fixtures `spoilerless/tests/fixtures/visualization/s01e01_safe.json` and
`s01e02_cumulative_safe.json`. No live Neo4j, no live users, no `series_dexter`, no LLM access —
all measurements are deterministic over synthetic safe rows.
**Verification:** `uv run pytest spoilerless/tests/test_visualization_baseline.py -q` (14 passed);
`uv run pytest spoilerless/tests/test_visualization_baseline.py -q -k "variant or bound"` (7 passed).

---

## 1. Observed problem

Before any production projection behavior changes (D-31), the Episode Overview needs a fixed-data
A/B comparison so the production default is chosen from measured evidence, not preference. The
previous UI used a single client-side `overview` reduction over the full safe graph
(`frontend/src/components/graph/graphElements.ts::graphToElements`), which is neither bounded to
D-09's target nor compared against an alternative. D-10 requires evaluating two fixed-data
variants on counts, crossings, clarity, stability and episode comprehension before choosing.

## 2. Alternatives considered

| Variant | Definition (D-10) |
|---|---|
| **A** | Characters plus major Events (major = editorial tier from fixture event metadata) |
| **B** | Character-led graph; Events surface primarily in the coordinated Event Timeline |
| **Full Graph** | Complete safe graph — **not a candidate**: kept as Advanced/debug only per D-11 |

Both variants omit `OCCURRED_IN` / `PARTICIPATED_IN` / `LOCATED_IN` edges from the graph per D-13
(participation becomes avatars/chips/Inspector/timeline metadata; `LOCATED_IN` becomes Event-card
metadata).

## 3. Repository evidence (measured, fixed data)

### Baseline snapshot (D-31)

| Metric | S01E01 | Cumulative S01E02 |
|---|---|---|
| Fixture | `s01e01_safe.json` | `s01e02_cumulative_safe.json` |
| Effective boundary | 1 | 2 |
| Nodes (total) | 11 | 17 |
| Edges (total) | 7 | 14 |
| Claims / Sources / Evidence | 4 / 1 / 3 | 6 / 2 / 5 |
| Node kinds | Character 6, Episode 1, Event 1, Location 2, Series 1 | Character 8, Episode 2, Event 2, Location 4, Series 1 |
| Edge types | `FAMILY_OF` 1, `KNOWS` 1 (user), `OCCURRED_IN` 3, `PART_OF` 1, `WORKS_WITH` 1 | `FAMILY_OF` 2, `KNOWS` 1 (user), `OCCURRED_IN` 6, `PART_OF` 2, `PRECEDES` 1, `WORKS_WITH` 2 |
| Payload (fixture bytes) | 7,692 | 12,386 |
| Load + validate + count latency | 1.9 ms (measured) | 0.7 ms (measured) |

### Variant comparison (measured)

| Metric | A · S01E01 | B · S01E01 | A · S01E02 | B · S01E02 |
|---|---|---|---|---|
| Nodes | 9 | 8 | **13** | 11 |
| Edges | 4 | 4 | 7 | 7 |
| Node kinds | Char 6, Ep 1, Event 1, Series 1 | Char 6, Ep 1, Series 1 | Char 8, Ep 2, Event 2, Series 1 | Char 8, Ep 2, Series 1 |
| Omitted nodes | 2 Locations | 1 Event + 2 Locations | 4 Locations | 2 Events + 4 Locations |
| Omitted edges | 3 `OCCURRED_IN` | 3 `OCCURRED_IN` | 6 `OCCURRED_IN` + 1 `WORKS_WITH` (location endpoint) | 6 `OCCURRED_IN` + 1 `WORKS_WITH` (location endpoint) |
| Crossings (approx.) | 0 | 0 | 0 | 0 |
| Persistent procedural labels | 0 | 0 | 0 | 0 |
| In 12–28 target range | No (sparse) | No (sparse) | **Yes** | No (11 < 12) |
| Within hard bounds (≤40 nodes / ≤60 edges) | Yes | Yes | Yes | Yes |

### Stability S01E01 → cumulative S01E02 (D-31)

- Shared characters: 6 of 6 (retention 1.0) for both variants; E01 6 → E02 8 characters.
- Displacement: 0.0 by construction under the deterministic id-order layout; real fCoSE
  displacement is measured by the 10-08 benchmark harness.
- Edge family stability: identical kept edge-type sets between variants (only node membership
  differs — Event nodes for A).

### Narrative comprehension notes (D-10)

- **A:** major Events are visible in the graph beside characters; with 1–2 major Events per
  episode the graph stays sparse, but event meaning (participants, location) competes with
  character topology for attention; participation edges are absent (D-13), so event nodes rely
  on the Inspector/timeline for connection detail.
- **B:** the graph is purely character-led; every Event renders as a timeline card with
  participants and location metadata (D-13/D-38), matching the Story two-region composition
  (graph + timeline rail) in the UI-SPEC; event comprehension comes from the coordinated
  timeline, and the graph is maximally stable across episode switches.

## 4. Selected default

**Variant A — characters plus major Events** — is the production Episode Overview default at
projection version `1.0.0`.

Reason (evidence, not preference):

1. **Target range:** on the only fixture that can reach the 12-node floor (cumulative S01E02),
   A measures 13 nodes — inside the D-09 target 12–28 — while B measures 11, one node below the
   floor. A is the only variant that satisfies the VIZ-03 target on the fixed data.
2. **No measured trade-off against B:** edges (4/7), crossings (0), stability (1.0 retention,
   0 displacement) and procedural labels (0) are identical between variants; A adds Event nodes
   without violating any hard bound.
3. **Contract fit:** the UI-SPEC Episode Overview contract says "Prefer characters and
   major/supporting Events", with participation as avatars/chips and `LOCATED_IN` as Event-card
   metadata — A's node set is exactly that, and D-38's first-class Event Timeline remains in the
   Story tab regardless (B's timeline-first treatment informs the Story composition, not the
   projection node set).
4. **Sparse episode honesty:** S01E01 measures 8–9 nodes for both variants — below the target
   floor because the source graph itself is sparse. This is accepted per D-44 (sparse episodes
   show an explanatory state); the enforceable cap is the hard 40-node maximum, which both
   variants respect everywhere.

Bounds proof for the selected default (VIZ-03 acceptance):

| Bound | Requirement | A measured (S01E01 / S01E02) | Status |
|---|---|---|---|
| Nodes | target 12–28; hard max 40 | 9 / 13; max 13 ≤ 40 | Target met on cumulative S01E02; S01E01 sparse (accepted, D-44); hard max proven |
| Edges | preferred <35; hard max 60 | 4 / 7; max 7 < 35 | Proven |
| Persistent procedural labels | 0 | 0 / 0 | Proven |

## 5. Rejection

- **Variant B as production default — rejected.** It measures 11 nodes on cumulative S01E02,
  missing the 12-node target floor, with no measured advantage over A on edges, crossings,
  stability, or labels. Its Event-in-timeline treatment is preserved as the Story tab
  composition (timeline stays first-class per D-38), so nothing B offers is lost by the choice.
- **Full Graph as default — rejected per D-11:** remains Advanced/debug/deep-exploration only;
  it is the complete safe graph, not a bounded Episode Overview.

## 6. Remaining risk

| Risk | Mitigation / owner |
|---|---|
| Editorial tier (major/supporting/micro) is currently hand-encoded in fixture event metadata; the real safe `display_tier` source must be audited before production projection (RESEARCH open question 1). | 10-02/10-03 audit existing `overviewTiers`/seed metadata; do not add parallel priority fields. |
| Fixtures are synthetic safe snapshots; live S01E01/cumulative S01E02 counts may differ. | Re-measure against disposable scratch Neo4j data in 10-08/10-09; re-verify bounds before ship. |
| Crossings metric is a deterministic id-order approximation, not a geometric count (D-32 permits approximation); trivially 0 at this scale. | Benchmark harness (10-08) measures crossings at 30/50 … 300/1000 scales. |
| A/B clarity/comprehension judgment is machine-measured here; human comprehension remains a manual UAT item. | Operator UAT (10-10) compares the deployed default against the recorded narrative notes. |

## 7. Traceability

- Fixtures: `spoilerless/tests/fixtures/visualization/s01e01_safe.json`,
  `spoilerless/tests/fixtures/visualization/s01e02_cumulative_safe.json` (immutable, episode +
  projection-version metadata).
- Tracer + evidence object: `spoilerless/tests/test_visualization_baseline.py`.
- Requirements: VIZ-03, VIZ-10 (this log is the D-03 evidence record consumed by 10-02+).
- Related decisions: D-09 (bounds), D-10 (variant evaluation), D-11 (Full Graph Advanced),
  D-13 (edge omission), D-31 (baselines), D-38 (timeline first-class), D-44 (sparse states).
