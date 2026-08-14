---
phase: 10-polish-finishing-touches
plan: 01
subsystem: testing
tags: [fixtures, baseline, tracer, decision-log, visualization, spoiler-safe]

requires:
  - phase: 09-feature-expansion-full-audit-remediation
    provides: graph/timeline/GraphRAG foundations the visualization redesign builds on
provides:
  - Immutable safe S01E01 + cumulative S01E02 visualization baseline fixtures (projection_version 1.0.0)
  - Production-quality baseline tracer (JSON -> GraphResponse -> effective boundary -> metrics -> evidence)
  - Measured Variant A/B Episode Overview comparison and the evidence-based A/B Decision Log
affects: [10-02, 10-03, 10-08, 10-10, visualization projection implementation]

actuals:
  tokens: 14070
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - Safe-fixture envelope: fixture_metadata (episode, order, scope, projection_version, immutable) + events metadata + GraphResponse-shaped graph payload
    - Evidence-object contract: build_evidence() dict consumed by the decision gate; variant metrics carry omissions, crossings approximation, procedural labels, target/hard bounds
    - Deterministic id-order layout metrics (crossings approximation, zero-displacement stability by construction); real fCoSE metrics deferred to the 10-08 benchmark harness

key-files:
  created:
    - spoilerless/tests/fixtures/visualization/s01e01_safe.json
    - spoilerless/tests/fixtures/visualization/s01e02_cumulative_safe.json
    - spoilerless/tests/test_visualization_baseline.py
    - docs/decision-logs/phase-10-visualization.md
  modified: []

key-decisions:
  - "Episode Overview production default = Variant A (characters + major Events) at projection_version 1.0.0, selected from measured fixed-data evidence: 13 nodes inside the 12-28 target on cumulative S01E02 vs Variant B's 11 (one below the floor); edges/crossings/stability/procedural labels identical between variants; Full Graph remains Advanced per D-11."
  - "Safe baselines frozen as immutable checked-in JSON fixtures with explicit episode + projection-version metadata (T10-CACHE-01); the tracer pipeline has no mock seam: JSON load -> GraphResponse.model_validate -> spoiler policy effective boundary -> baseline metrics -> evidence."

patterns-established:
  - "Pattern 1: safe-fixture envelope (fixture_metadata + events + graph payload) that later plans extend without touching frozen baselines."
  - "Pattern 2: one deterministic evidence object (build_evidence) feeds both the contract tests and the D-03 decision record, so the log quotes measured values only."

requirements-completed: [VIZ-03, VIZ-10]

coverage:
  - id: D1
    description: "Immutable safe S01E01 and cumulative S01E02 visualization fixtures with episode + projection-version metadata, containing only boundary-filtered rows"
    requirement: VIZ-10
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_fixture_schema_and_closure_s01e01"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_fixture_schema_and_closure_s01e02_cumulative"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_effective_boundary_semantics_and_no_hidden_rows"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_no_forbidden_technical_or_hidden_metadata"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_episode_safe_image_fields"
        status: pass
    human_judgment: false
  - id: D2
    description: "Production-quality baseline tracer and deterministic contract suite (fixture schema, no hidden rows, safe image fields, exact baseline counts/latency/payload/layout inputs)"
    requirement: VIZ-10
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_baseline_counts_s01e01"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_baseline_counts_s01e02_cumulative"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_baseline_latency_payload_and_layout_inputs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Measured Variant A/B comparison on fixed data: counts, omissions, crossings approximation, stability, target/hard bounds, zero persistent procedural labels"
    requirement: VIZ-03
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_variant_a_metrics_and_omissions"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_variant_b_metrics_and_omissions"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_variant_hard_bounds_both_episodes"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_variant_target_range_assessment"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_baseline.py#test_variant_stability_between_episodes"
        status: pass
    human_judgment: false
  - id: D4
    description: "Evidence-based A/B Decision Log selecting one production default (Variant A, projection_version 1.0.0) with measured evidence, rejection rationale, and remaining risk"
    requirement: VIZ-03
    verification: []
    human_judgment: true
    rationale: "The measurements are automated (D3), but the final production-default selection and narrative-comprehension judgment (clarity of the chosen variant for a human viewer) require human sign-off; 10-10 operator UAT compares the deployed default against the recorded narrative notes per 10-VALIDATION.md Manual-Only Verifications."

duration: 48min
completed: 2026-08-13
status: complete
---

# Phase 10 Plan 1: Baseline Tracer & A/B Gate Summary

**Safe S01E01 + cumulative S01E02 fixtures frozen with a production tracer, and Variant A (characters + major Events) selected as the Episode Overview default from measured A/B evidence at projection_version 1.0.0**

## Performance

- **Duration:** 48 min
- **Started:** 2026-08-13T14:01:00Z
- **Completed:** 2026-08-13T14:49:16Z
- **Tasks:** 2
- **Files modified:** 4 created (+3 planning/docs files)

## Accomplishments

- Immutable checked-in safe fixtures `s01e01_safe.json` (11 nodes / 7 edges / 4 claims / 1 source / 3 evidence) and `s01e02_cumulative_safe.json` (17 / 14 / 6 / 2 / 5), each with explicit episode + projection-version metadata and event metadata (tier, participants, location).
- Production-quality tracer `test_visualization_baseline.py`: JSON load → `GraphResponse` validation → effective-boundary assertion via `spoiler.app.spoiler.policy` → baseline metrics (counts/latency/payload/layout inputs) → deterministic evidence object (`build_evidence()`). No mock seam; no Neo4j or LLM access anywhere.
- Deterministic contract suite (14 tests): fixture schema/closure, no hidden rows, no forbidden technical/hidden metadata (T10-LEAK-01/T10-FOCUS-01), episode-safe image fields (D-43), exact baseline counts, latency/payload/layout inputs, plus measured Variant A/B metrics, omissions, crossings approximation, stability, and target/hard bounds.
- Evidence-based Decision Log at `docs/decision-logs/phase-10-visualization.md` (D-03 format): **Variant A selected** (13 nodes inside 12–28 target on cumulative S01E02; B measures 11, one below the floor; identical edges 4/7, crossings 0, stability 1.0, procedural labels 0). Full Graph stays Advanced (D-11).

## Task Commits

Each task was committed atomically:

1. **Task 1: Trace safe fixture through baseline measurement** - `3cec852` (test(10-01): freeze safe S01E01/S01E02 fixtures and baseline tracer)
2. **Task 2: Compare Episode Overview variants and record the gate** - `4903b23` (docs(10-01): record measured A/B Episode Overview decision gate)

**Plan metadata:** committed as `docs(10-01): complete baseline tracer and A/B decision gate plan` (SUMMARY + STATE.md + ROADMAP.md; hash reported in the executor completion notes)

## Files Created/Modified

- `spoilerless/tests/fixtures/visualization/s01e01_safe.json` - Immutable safe S01E01 fixture (fixture_metadata + events + GraphResponse payload)
- `spoilerless/tests/fixtures/visualization/s01e02_cumulative_safe.json` - Immutable cumulative S01E02 fixture
- `spoilerless/tests/test_visualization_baseline.py` - Production tracer + 14 deterministic contract/variant tests
- `docs/decision-logs/phase-10-visualization.md` - D-03 evidence-based A/B decision record (measured table, selection, rejection, risk)
- `.planning/phases/10-polish-finishing-touches/10-01-SUMMARY.md` - This summary
- `.planning/STATE.md` / `.planning/ROADMAP.md` - Plan position/progress updates (metadata commit)

## Decisions Made

- **Episode Overview production default = Variant A (characters + major Events)** at `projection_version 1.0.0`. Evidence: only A lands inside the D-09 12–28 target on the fixed cumulative S01E02 data (13 vs 11); edges (4/7), crossings (0), stability (retention 1.0, displacement 0) and procedural labels (0) are identical between variants; UI-SPEC contract prefers characters and major/supporting Events. B's timeline-first treatment is preserved via the first-class Event Timeline (D-38).
- **Sparse-episode honesty:** S01E01 measures 8–9 nodes — below the 12-node target floor for both variants because the source graph is sparse; accepted per D-44, hard max 40 still proven.
- **Full Graph remains Advanced/debug** (D-11), never the default.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Initial S01E02 cumulative node-count expectation (18) was corrected to 17 during Task 1: cumulative-through-S01E02 has 8 Characters (Paul Bennett appears only in S01E03, per the existing E03 fixture math 20 − episode − event − character). Fixture unchanged; the test expectation was fixed and all counts re-verified. No plan change.
- Evidence extraction via `importlib` required registering the test module in `sys.modules` (dataclass module registration) — tooling detail only, no repository impact.
- Git reported harmless LF→CRLF warnings on Windows for the new files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for **10-02 (neutral DTO + boundary)**: fixtures, tracer, and the A/B decision are the gate inputs; `projection_version 1.0.0` is the recorded projection version the DTO/cache must carry.
- 10-03/10-08 must audit the real `display_tier` source (currently hand-encoded major tier in fixture event metadata) and re-measure live counts against disposable scratch data before ship.
- Blockers/concerns: none. VIZ-03/VIZ-10 not yet marked Complete in REQUIREMENTS.md — shared-ID gate (#2388): siblings 10-03 and 10-08 also declare them and have no SUMMARY yet; they flip Complete when the last declaring plan finishes.

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*

## Self-Check: PASSED

- All 5 plan files exist on disk (2 fixtures, tracer test suite, decision log, this summary).
- Both task commits exist: `3cec852` (Task 1), `4903b23` (Task 2).
- Task 1 `<verify>` re-run on committed state: `uv run pytest spoilerless/tests/test_visualization_baseline.py -q` → 14 passed.
- Task 2 `<verify>` re-run on committed state: `uv run pytest spoilerless/tests/test_visualization_baseline.py -q -k "variant or bound"` → 7 passed, 7 deselected.
- Plan-level `<verification>`: focused baseline suite green; Decision Log inspected for D-03 evidence completeness (problem/alternatives/evidence/choice/rejection/risk present) and the explicit A/B gate (Variant A selected at projection_version 1.0.0).
- No live Neo4j, no live users, no `series_dexter`, no LLM access used.
