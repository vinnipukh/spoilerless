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

## 8. Benchmark evidence (10-08, D-32/D-39)

Harness: `scripts/benchmark_visualization.py` (seeded `random.Random(0x1008)`, in-memory,
stdlib + repository code only — zero network/database/provider access) + schema
`scripts/benchmark_visualization_schema.json`. Four required sizes, rerun at zero cost:

| Scale | Overview (Variant A) | Cumulative | Hard gates |
|---|---|---|---|
| 30n/50e | 15n/13e — target 12–28 ✓ | 27n/28e | 16/16 |
| 75n/150e | 22n/37e | cap raised (D-09 fail-closed) | 16/16 |
| 150n/400e | 25n/46e | cap raised (D-09 fail-closed) | 16/16 |
| 300n/1000e | 28n/60e — target 12–28 ✓ | cap raised (D-09 fail-closed) | 16/16 |

- The cumulative-overview cap raise at ≥75-node scales is the D-09 bounded-view
  behavior (refuse >40 nodes), not a defect.
- Deterministic fingerprint is byte-identical across reruns; wall-clock timings
  (graph validation, projections — all <2 ms even at 300n/1000e on this machine)
  live in `observations` as environment-sensitive per D-32.

**Refinement decision (D-03/D-39):** no product-code change.
- Evidence: every hard gate passed at every size (payload bounds, adapter input,
  focus ≤20 + resolves-inside-DTO, expansion ≤25 + allowlist, view-switch cache
  identity, episode-switch displacement 0, zero procedural labels, human edge
  vocabulary, hidden-row fail-closed + byte-identity, schema validity, determinism).
- Alternatives considered: micro-optimize projection dict-building (rejected —
  sub-2 ms at the largest required size; adds risk to the fail-closed paths for
  no measurable product gain); cache view switches (rejected — expansion and
  focus are deliberately uncached in Phase 10 per T10-CACHE-06).
- Remaining risk: synthetic datasets are not live payloads — real browser
  render/layout cost and live-count re-measurement are deferred to the
  disposable-container regression gate (10-09) and operator UAT (10-10).

## Phase 10 Source Coverage Audit (10-11)

Machine-readable multi-source coverage audit — verifier: `scripts/verify_phase10_coverage.py` (exact inventory: 98 source ids). Evidence refs name real repository artifacts/tests only; parser rejects duplicates, missing/extra ids, malformed rows, empty fields, and self-referencing evidence.

<!-- PHASE10-COVERAGE:START -->
| source_id | plan_id | artifact_or_test | evidence_ref |
|---|---|---|---|
| GOAL:PHASE-10 | 10-01..10-11 | .planning/ROADMAP.md Phase 10 goal + success criteria (D-01 scope amendment) | .planning/ROADMAP.md |
| REQ:VIZ-01 | 10-02 | Neutral VisualizationDTO + projection routes (D-08/D-29) | spoilerless/tests/test_visualization_projection.py |
| REQ:VIZ-02 | 10-02 | effective_view_order = min(requested, watched) before projection; fail-closed (D-05/D-06) | spoilerless/tests/test_visualization_projection.py |
| REQ:VIZ-03 | 10-01 | A/B fixed-data variant selection + 12-28 target / 40 hard node bounds (D-09/D-10) | spoilerless/tests/test_visualization_baseline.py |
| REQ:VIZ-04 | 10-05 | Four top-level views Story/Characters/Evidence/Advanced (D-17) | frontend/src/App.test.tsx |
| REQ:VIZ-05 | 10-05 | Desktop top tabs; mobile scrollable tabs + half/full Inspector sheet (D-18/D-19/D-20) | frontend/src/components/detail/DetailPanel.test.tsx |
| REQ:VIZ-06 | 10-06 | Allowlisted semantic expansion, 8-12 default / hard max 25, collapse/undo/reset (D-21) | spoilerless/tests/test_visualization_projection.py |
| REQ:VIZ-07 | 10-04 | Cytoscape stable scene, batched diffs, fCoSE/preset/Dagre layouts (D-23/D-24) | frontend/src/components/graph/GraphCanvas.test.tsx |
| REQ:VIZ-08 | 10-07 | GraphRAG Answer Graph 5-20 + Evidence Chain + scene restoration (D-26/D-27/D-28) | spoilerless/tests/test_visualization_graphrag.py |
| REQ:VIZ-09 | 10-03 | Projection cache separation dimensions + leak channels (D-30) | spoilerless/tests/test_visualization_cache.py |
| REQ:VIZ-10 | 10-08 | Fixed baselines + benchmark harness 30/50..300/1000 (D-31/D-32) | scripts/benchmark_visualization.py |
| REQ:POLISH-01 | 10-09 | Full green regression gate on isolated ephemeral Neo4j | scripts/run_phase10_backend_tests.py |
| REQ:POLISH-02 | 10-10 | Operator-approved golden-path UAT (12 rows + 7 backstop rows) | docs/uat/phase-10-golden-path.md |
| REQ:POLISH-03 | 10-11 | Shipped-state README/root docs — no stale prototype/deployment wording | README.md |
| DEC:D-01 | 10-01 | 10-CONTEXT.md decision D-01 — Phase 10 scope amendment | .planning/phases/10-polish-finishing-touches/10-10-01-SUMMARY.md |
| DEC:D-02 | 10-01 | 10-CONTEXT.md decision D-02 — Incremental work order | .planning/phases/10-polish-finishing-touches/10-10-01-SUMMARY.md |
| DEC:D-03 | 10-01 | 10-CONTEXT.md decision D-03 — Evidence-based Decision Log requirement | docs/decision-logs/phase-10-visualization.md |
| DEC:D-04 | 10-02 | 10-CONTEXT.md decision D-04 — Storage/retrieval/projection separation | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-05 | 10-02 | 10-CONTEXT.md decision D-05 — Mandatory filter-before-projection order | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-06 | 10-02 | 10-CONTEXT.md decision D-06 — Indirect leak audit (counts/forces/space/hints) | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-07 | 10-04 | 10-CONTEXT.md decision D-07 — Keep Cytoscape; NVL isolated only | .planning/phases/10-polish-finishing-touches/10-10-04-SUMMARY.md |
| DEC:D-08 | 10-02 | 10-CONTEXT.md decision D-08 — Library-neutral visualization DTO | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-09 | 10-01 | 10-CONTEXT.md decision D-09 — Episode Overview bounds 12-28/40, <35/60 edges | docs/decision-logs/phase-10-visualization.md |
| DEC:D-10 | 10-01 | 10-CONTEXT.md decision D-10 — Two fixed-data variants A/B before choice | docs/decision-logs/phase-10-visualization.md |
| DEC:D-11 | 10-01 | 10-CONTEXT.md decision D-11 — Full Graph Advanced/debug only | docs/decision-logs/phase-10-visualization.md |
| DEC:D-12 | 10-02 | 10-CONTEXT.md decision D-12 — Major/supporting/micro event distinction | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-13 | 10-02 | 10-CONTEXT.md decision D-13 — Omit PARTICIPATED_IN/OCCURRED_IN from overview | docs/decision-logs/phase-10-visualization.md |
| DEC:D-14 | 10-02 | 10-CONTEXT.md decision D-14 — Narrative vs procedural edge classification | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-15 | 10-02 | 10-CONTEXT.md decision D-15 — display_tier editorial importance | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-16 | 10-05 | 10-CONTEXT.md decision D-16 — Desktop top-level tabs | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-17 | 10-05 | 10-CONTEXT.md decision D-17 — Four top-level tab hierarchy | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-18 | 10-05 | 10-CONTEXT.md decision D-18 — Mobile scrollable top tabs | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-19 | 10-05 | 10-CONTEXT.md decision D-19 — Mobile Inspector half/full bottom sheet | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-20 | 10-05 | 10-CONTEXT.md decision D-20 — Never squeeze graph/timeline/Inspector on narrow screens | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-21 | 10-06 | 10-CONTEXT.md decision D-21 — Semantic expansion keys/allowlist/max 25 | .planning/phases/10-polish-finishing-touches/10-10-06-SUMMARY.md |
| DEC:D-22 | 10-04 | 10-CONTEXT.md decision D-22 — Expansion preserves scene; local constrained layout | .planning/phases/10-polish-finishing-touches/10-10-04-SUMMARY.md |
| DEC:D-23 | 10-04 | 10-CONTEXT.md decision D-23 — fCoSE -> preset; Evidence Dagre; timeline React/CSS | .planning/phases/10-polish-finishing-touches/10-10-04-SUMMARY.md |
| DEC:D-24 | 10-04 | 10-CONTEXT.md decision D-24 — Stable Cytoscape instance + batched diffs | .planning/phases/10-polish-finishing-touches/10-10-04-SUMMARY.md |
| DEC:D-25 | 10-04 | 10-CONTEXT.md decision D-25 — Semantic zoom never fetches/expands | .planning/phases/10-polish-finishing-touches/10-10-04-SUMMARY.md |
| DEC:D-26 | 10-07 | 10-CONTEXT.md decision D-26 — GraphRAG visible-in-place focus; hidden-safe Answer Graph | .planning/phases/10-polish-finishing-touches/10-10-07-SUMMARY.md |
| DEC:D-27 | 10-07 | 10-CONTEXT.md decision D-27 — Answer Graph 5-20 elements + full restoration | .planning/phases/10-polish-finishing-touches/10-10-07-SUMMARY.md |
| DEC:D-28 | 10-07 | 10-CONTEXT.md decision D-28 — Investigation layered Claim/Evidence/Source | .planning/phases/10-polish-finishing-touches/10-10-07-SUMMARY.md |
| DEC:D-29 | 10-03 | 10-CONTEXT.md decision D-29 — Exact read contracts visualization + expand | .planning/phases/10-polish-finishing-touches/10-10-03-SUMMARY.md |
| DEC:D-30 | 10-03 | 10-CONTEXT.md decision D-30 — Projection cache key dimensions + expansion uncached | .planning/phases/10-polish-finishing-touches/10-10-03-SUMMARY.md |
| DEC:D-31 | 10-01 | 10-CONTEXT.md decision D-31 — Fixed safe baseline snapshots S01E01/S01E02 | docs/decision-logs/phase-10-visualization.md |
| DEC:D-32 | 10-08 | 10-CONTEXT.md decision D-32 — Benchmark sizes 30/50..300/1000 + metrics | docs/decision-logs/phase-10-visualization.md |
| DEC:D-33 | 10-09 | 10-CONTEXT.md decision D-33 — Automated coverage list (spoiler/cache/focus/restore/...)  | .planning/phases/10-polish-finishing-touches/10-10-09-SUMMARY.md |
| DEC:D-34 | 10-09 | 10-CONTEXT.md decision D-34 — Finish original Phase 10 obligations incl. golden-path UAT | docs/uat/phase-10-golden-path.md |
| DEC:D-35 | 10-02 | 10-CONTEXT.md decision D-35 — Reveal/publication order authoritative | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-36 | 10-02 | 10-CONTEXT.md decision D-36 — Plot threads editorial, never automatic communities | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-37 | 10-02 | 10-CONTEXT.md decision D-37 — Visual aggregation never invents canonical facts | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-38 | 10-05 | 10-CONTEXT.md decision D-38 — First-class Event Timeline grouped by plot thread | docs/decision-logs/phase-10-visualization.md |
| DEC:D-39 | 10-08 | 10-CONTEXT.md decision D-39 — episode_difference deferred (secondary) | docs/decision-logs/phase-10-visualization.md |
| DEC:D-40 | 10-02 | 10-CONTEXT.md decision D-40 — Phase is polish/projection, not backend rewrite | .planning/phases/10-polish-finishing-touches/10-10-02-SUMMARY.md |
| DEC:D-41 | 10-07 | 10-CONTEXT.md decision D-41 — Claims/Evidence/Sources stay off main story graph | .planning/phases/10-polish-finishing-touches/10-10-07-SUMMARY.md |
| DEC:D-42 | 10-05 | 10-CONTEXT.md decision D-42 — Restrained origin styling | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-43 | 10-05 | 10-CONTEXT.md decision D-43 — Episode-safe character images + fallbacks | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-44 | 10-07 | 10-CONTEXT.md decision D-44 — Graceful loading/error/sparse states | docs/decision-logs/phase-10-visualization.md |
| DEC:D-45 | 10-07 | 10-CONTEXT.md decision D-45 — Accessibility must not regress | .planning/phases/10-polish-finishing-touches/10-10-07-SUMMARY.md |
| DEC:D-46 | 10-05 | 10-CONTEXT.md decision D-46 — General polish audits; reuse Tailwind language | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-47 | 10-05 | 10-CONTEXT.md decision D-47 — Views and Filters stay separate | .planning/phases/10-polish-finishing-touches/10-10-05-SUMMARY.md |
| DEC:D-48 | 10-06 | 10-CONTEXT.md decision D-48 — Spoiler-safe search + GraphRAG focus narrowing | .planning/phases/10-polish-finishing-touches/10-10-06-SUMMARY.md |
| DEC:D-49 | 10-11 | 10-CONTEXT.md decision D-49 — Exploration recovery Back/Undo/Collapse/Clear/Reset | .planning/phases/10-polish-finishing-touches/10-10-11-SUMMARY.md |
| UI:DESIGN-SYSTEM | 10-05 | shadcn radix-nova preset + existing token language | frontend/components.json |
| UI:INFORMATION-ARCHITECTURE | 10-05 | Four-tab hierarchy + nested modes contract | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:COPYWRITING | 10-05 | Primary copy table (empty/loading/error/recovery strings) | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:VISUALS | 10-05 | Visual composition, node treatment, Inspector surface | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:COLOR | 10-05 | Existing color tokens; accent semantic roles | frontend/src/index.css |
| UI:TYPOGRAPHY | 10-05 | Four sizes / two weights; human labels | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:SPACING | 10-05 | 4px-based spacing scale + touch targets | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:ACCESSIBILITY | 10-05 | Keyboard focus/ring/Escape/return-focus/reduced motion | docs/uat/phase-10-golden-path.md |
| UI:INTERACTION | 10-04 | Interaction and Scene Contract (1-7) | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:CONSIDERATION-ZERO-ONE-MANY | 10-05 | Zero/one/many content states matrix | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:CONSIDERATION-LONG-TEXT | 10-05 | Long-text wrapping contract | docs/uat/phase-10-golden-path.md |
| UI:STATE-ROWS | 10-05 | UI considerations matrix — 32 covered / 8 backstop | .planning/phases/10-polish-finishing-touches/10-UI-SPEC.md |
| UI:ACCEPTANCE-EVIDENCE | 10-11 | Acceptance Evidence checklist | docs/uat/phase-10-golden-path.md |
| UI:BACKSTOP-OVERFLOW | 10-10 | Dense Advanced graph / long labels backstop (UI-DENSE-01) | docs/uat/phase-10-golden-path.md |
| UI:BACKSTOP-MOBILE-INSPECTOR | 10-10 | Half/full sheet backstop (UI-GESTURE-01) | docs/uat/phase-10-golden-path.md |
| UI:BACKSTOP-RESPONSIVE | 10-10 | Desktop/tablet/narrow backstop (UI-RESP-01) | docs/uat/phase-10-golden-path.md |
| UI:BACKSTOP-CYTOSCAPE-A11Y | 10-10 | Readable node access backstop (UI-A11Y-01) | docs/uat/phase-10-golden-path.md |
| RESEARCH:FILE-MAP | 10-02 | 10-RESEARCH.md — responsibility map / code seams | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:ARCHITECTURE | 10-02 | 10-RESEARCH.md — architecture patterns (safe read pipeline, DTO boundary, projections) | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:DONT-HAND-ROLL | 10-02 | 10-RESEARCH.md — don't hand-roll findings | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:PITFALLS | 10-04 | 10-RESEARCH.md — seven common pitfalls | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:VALIDATION | 10-09 | 10-RESEARCH.md — validation architecture | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:SECURITY | 10-02 | 10-RESEARCH.md — spoiler/security research | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:CONSTRAINTS | 10-02 | 10-RESEARCH.md — constraints (zero-cost, stack locks) | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| RESEARCH:ASSUMPTIONS | 10-01 | 10-RESEARCH.md — assumptions | .planning/phases/10-polish-finishing-touches/10-RESEARCH.md |
| PATTERNS:FILE-CLASSIFICATION | 10-02 | 10-PATTERNS.md — file classification | .planning/phases/10-polish-finishing-touches/10-PATTERNS.md |
| PATTERNS:ASSIGNMENTS | 10-02 | 10-PATTERNS.md — pattern assignments per layer | .planning/phases/10-polish-finishing-touches/10-PATTERNS.md |
| PATTERNS:SHARED | 10-02 | 10-PATTERNS.md — shared patterns | .planning/phases/10-polish-finishing-touches/10-PATTERNS.md |
| PATTERNS:PITFALLS | 10-04 | 10-PATTERNS.md — spoiler/test pitfalls to preserve | .planning/phases/10-polish-finishing-touches/10-PATTERNS.md |
| PATTERNS:SAFETY | 10-02 | 10-PATTERNS.md — backend-first fail-closed safety | .planning/phases/10-polish-finishing-touches/10-PATTERNS.md |
| VALIDATION:INFRASTRUCTURE | 10-09 | Ephemeral Neo4j runner + mock guard tests | scripts/run_phase10_backend_tests.py |
| VALIDATION:SAMPLING | 10-01..10-11 | Sampling gates (per-task, per-plan, per-wave) | .planning/phases/10-polish-finishing-touches/10-VALIDATION.md |
| VALIDATION:PER-PLAN-MAP | 10-01..10-11 | Per-plan verification map | .planning/phases/10-polish-finishing-touches/10-VALIDATION.md |
| VALIDATION:MANUAL-ONLY | 10-10 | Manual-only verifications (comprehension, mobile, UAT, docs) | docs/uat/phase-10-golden-path.md |
| VALIDATION:SIGN-OFF | 10-11 | Validation sign-off + wave-0 completeness | .planning/phases/10-polish-finishing-touches/10-VALIDATION.md |
<!-- PHASE10-COVERAGE:END -->
