# GSD Phase Verification (gsd-verifier role) — hdgrafcehennemi

Validated workflow for verifying a completed GSD phase against the codebase and
writing `<NN>-VERIFICATION.md`. Proven on phase 10 (v1.3, 2026-08-14); the two
gaps it caught are repo-wide traps that will recur on later phases.

## Workflow (order matters)

1. **Read in this order**: all `<NN>-PLAN.md` frontmatter (must_haves, requirements),
   all `*SUMMARY.md`, `.planning/REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, the
   phase UAT doc (`docs/uat/`), the phase decision log, and `docs/PROBLEMS.md`
   tail (last pass = authoritative "nothing new open" signal).
2. **Verify REQUIREMENTS.md checkboxes yourself — never trust task-context
   claims** like "all requirements Complete". In this repo, plan summaries
   self-report `Plan metadata: pending (… REQUIREMENTS.md commit)` when the
   metadata commit was skipped; REQUIREMENTS.md can lag plan completion by
   several plans. Count `[x]` vs `[ ]` per requirement ID and report staleness
   as a docs-level gap, not a code gap. (Phase 10: VIZ-01/02/04/05/06/08 +
   POLISH-02 were still `[ ]` while all 11 plans were complete.)
3. **Re-run the offline suites** (no Neo4j/LLM needed — ~130 tests in ~2 s):
   `unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_baseline.py spoilerless/tests/test_visualization_projection.py spoilerless/tests/test_visualization_cache.py spoilerless/tests/test_visualization_graphrag.py spoilerless/tests/test_phase10_coverage_audit.py spoilerless/tests/test_phase10_test_runner.py -q`
   Do NOT run `run_phase10_backend_tests.py --all` or `test_seed_idempotency.py`
   (they provision/need Neo4j; the phase already ran the full gate on an
   ephemeral container — re-running is out of scope for a verifier).
4. **Benchmark rerun** (zero-cost, in-memory):
   `unset PYTHONPATH && uv run python scripts/benchmark_visualization.py --sizes 30x50,75x150,150x400,300x1000`
   Expect `Schema errors: 0`, `Hard-gate failures: 0`, gates 16/16 per size,
   overview within the 12-28 target, and cumulative `cap_raised` at ≥75-node
   scales — the cap raise is D-09 fail-closed behavior, NOT a defect.
5. **Coverage audit: "OK: 98/98" is STRUCTURAL ONLY.** `scripts/verify_phase10_coverage.py`
   never checks that `evidence_ref` paths exist. Known bug (phase 10): all 38
   `DEC:D-*` rows reference `.planning/phases/10-polish-finishing-touches/10-10-0X-SUMMARY.md`
   — those files NEVER existed (real names are `10-0X-SUMMARY.md`; proven via
   `git log --all --oneline -- <path>` = empty). Always run a ref-existence
   loop over the `<!-- PHASE10-COVERAGE:START/END -->` block and report broken
   refs as a docs gap even when the parser passes.
6. **Stale-wording gate** (POLISH-03-style claims) — python one-liner over
   README.md + `docs/*.md`: split on `(?m)(?=^#{1,6} )`, exclude blocks whose
   heading matches `historical|audit|archive|changelog`, search
   `prototype only|no deployment|no production base url` (case-insensitive).
   Phase 10 result: HITS [].
7. **UAT rows**: an explicit `⏸ BLOCKED (operator-touch)` row (e.g. BYOK chat
   with zero-cost-policy rationale) is an ACCEPTED outcome — the requirement is
   "recorded, not silently skipped". Do not turn it into a failure; do list it
   under human_verification.
8. **Frontmatter shape** for `<NN>-VERIFICATION.md`:
   ```yaml
   ---
   status: passed|gaps_found
   phase: <phase-slug>
   milestone: v1.3
   date: YYYY-MM-DD
   verifier: gsd-verifier (subagent)
   must_haves_verified: N/M
   requirements_verified: N/M
   human_verification:
     - "operator UAT approval <date> (rows/backstops, blocked rows noted)"
   ---
   ```
   Sections: `## Verified Claims` (table of plan → must-have → evidence),
   `## Gaps` (each: id, severity, what/where/why, fix), `## Requirement Traceability`
   (per-ID: plans, checkbox state, evidence), plus re-run evidence list.

## Spot-check inventory (phase 10 era)

- Fixtures: `spoilerless/tests/fixtures/visualization/s01e01_safe.json` +
  `s01e02_cumulative_safe.json` — must carry `fixture_metadata{episode,
  projection_version: 1.0.0, scope, immutable: true}`.
- Backend: `app/domain/visualization.py` (VisualizationDTO),
  `app/services/visualization.py` (`project_episode_overview`, `project_view`,
  `project_expansion`, `project_graphrag_focus`), `app/spoiler/policy.py`
  (`resolve_effective_boundary`), `app/api/graph.py` (visualization route 6
  views, expand route 7 keys/1-25/uncached), `app/cache/graph_cache.py`
  (graph_revision epoch, focus SHA-256), `app/retrieval/pipeline.py`
  (GraphRagFocusContract + `done.graph_focus`).
- Frontend: `lib/visualizationAdapter.ts` exports `toCytoscapeElements`/
  `toTimelineEvents` (PLANS may name the target `graphToElements` — the actual
  export differs; trust tests, not plan labels), `hooks/useSceneState.ts`
  (OPEN/CLOSE_TEMPORARY, ADD_EXPANSION/UNDO), `App.tsx` four tabs
  (Story/Characters/Evidence/Advanced), `DetailPanel.tsx` half/full sheet
  (`max-h-[50vh]`/`max-h-[85vh]`), `components/graph/AnswerGraph.tsx`,
  `components/evidence/EvidenceChain.tsx`.
- Runner inventory: `scripts/run_backend_tests.py` must list every
  `test_*.py` exactly once (phase 10: 51/51, asserted at startup).

## Tooling quirk

`from hermes_tools import read_file` inside an execute_code sandbox returns a
dict WITHOUT a `'content'` key (keys: status/message/path/dedup/
content_returned). Use plain `open(path, encoding='utf-8').read()` in sandbox
scripts instead.
