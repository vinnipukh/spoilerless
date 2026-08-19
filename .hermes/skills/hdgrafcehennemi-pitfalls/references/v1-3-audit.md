# v1.3 Milestone Audit Findings (HEAD cdef4bb, 2026-08-14)

Milestone audit of phases 8–10. Audit file: `.planning/v1.3-MILESTONE-AUDIT.md`
(status: gaps_found). Facts below are state at HEAD; re-verify before acting.

## 1. Frontend is NOT wired to the Phase-10 visualization/expand routes (GAP-1)

The phase verifications re-ran unit tests but never checked production call sites.

- `frontend/src/api/graph.ts` defines `fetchVisualization` + `fetchExpansion`, but
  **zero modules import or call them** (only `getGraph` + `findPath` have consumers).
- `App.tsx` renders `<GraphCanvas graph={activeGraph} …/>` from the legacy
  `GET /api/series/{id}/graph` via `useGraph`. GraphCanvas's `visualization` prop
  (line ~325, `activeVisualization`/`toCytoscapeElements` path) is fed **only in
  GraphCanvas.test.tsx**.
- The four-tab Story/Characters/Evidence/Advanced hierarchy is **navigation-only**
  ("workspace stays mounted across tab switches"): tab state swaps auxiliary panels
  (Event Timeline rail, EvidenceChain, AnswerGraph, hint copy) but never changes the
  canvas content or fetches a projection.
- Production Episode Overview = client-side `overviewProjection(graph)`
  (`components/graph/graphElements.ts`, ~25–45 nodes) — NOT the backend Variant A
  projection (12–28 target, display_tier, projection_version 1.0.0) that the A/B
  Decision Log (`docs/decision-logs/phase-10-visualization.md`) and benchmark measured.
- No production semantic-expansion UI: `ADD_EXPANSION` is dispatched only in
  `useSceneState.test.ts`; no expansion button/panel; no `/graph/expand` call.
- `AnswerGraph.tsx` is presentation-only (renders scene-state focus id list — no
  `graphrag_focus` fetch, no 5–20-element graph). `EvidenceChain` + `TimelineView`
  derive client-side from the legacy GraphResponse payload.
- Consequence: VIZ-01/06/07/08 are backend-complete + unit-tested but not reachable
  end-to-end from the shipped UI. Spoiler safety is unaffected (legacy route boundary
  filtering, Phase 7/9). Not a security leak — an integration/feature-delivery gap.

If asked to wire it: fetch per tab mode via `fetchVisualization` → pass
`visualization` prop to GraphCanvas → expansion affordance dispatching
`ADD_EXPANSION` → re-run focused vitest + full gate.

## 2. OpenAPI inventory: live 52 ops / 39 templates; doc prose lags

- Locked green at HEAD by BOTH `spoilerless/tests/test_frontend_contract_doc.py`
  (asserts 52 ops / 39 templates, doc == OpenAPI == expected) and
  `spoilerless/tests/test_openapi_contract.py` (asserts `len(schema["paths"]) == 39`).
- `test_openapi_contract.py` is **NOT stale** — it was updated with the 10-03/10-06
  routes. (Its own comment "51 ops / 38 templates" is stale; the assertions are current.)
- Correct docs: `docs/API.md:10`, `docs/reference/frontend-api-contract.md` (test-locked).
- STALE prose still claiming 50 ops / 37 templates: `docs/README.md:25`,
  `docs/DEVELOPMENT.md:147`, `docs/TESTING.md:188`,
  `docs/architecture/spoiler-threat-model.md:208`. The last three also falsely claim
  `test_openapi_contract.py` "is stale / red / pins 32 templates".
- POLISH-03's stale-wording grep (prototype/no-deployment strings) does NOT catch
  count drift — a doc-claim sweep must re-check inventory counts separately.

## 3. REQUIREMENTS.md checkbox drift (known pattern)

Phase-10 rows were fixed 2026-08-14 (verification gap G1). Phase-9 rows
(PROB-01..13, PROB-16..22, PROB-24..32, FEAT-01..10) remain `[ ]` at HEAD despite
`09-VERIFICATION.md` passing 40/42 with code evidence (only PROB-14/15/23 + DOCS-04
are `[x]`). Lesson: for completion truth read the phase VERIFICATION.md, not
REQUIREMENTS.md checkboxes — checkboxes lag.

## 4. Offline spot-check commands (no ephemeral Neo4j needed)

```bash
# backend projection pipeline — expect 98 passed
unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_baseline.py \
  spoilerless/tests/test_visualization_projection.py \
  spoilerless/tests/test_visualization_cache.py \
  spoilerless/tests/test_visualization_graphrag.py -q --no-header

# coverage audit + test runner + both inventory contracts — expect 44 passed
uv run pytest spoilerless/tests/test_phase10_coverage_audit.py \
  spoilerless/tests/test_phase10_test_runner.py \
  spoilerless/tests/test_frontend_contract_doc.py \
  spoilerless/tests/test_openapi_contract.py -q --no-header

# frontend scene flow — expect 61 passed (one non-failing act() warning)
NODE_ENV=test CI=1 npm --prefix frontend test -- --run \
  src/lib/visualizationAdapter.test.ts src/hooks/useSceneState.test.ts \
  src/components/graph/GraphCanvas.test.tsx

# coverage audit verifier — expect "OK: 98/98"
uv run python scripts/verify_phase10_coverage.py docs/decision-logs/phase-10-visualization.md

# benchmark — expect Schema errors 0 / Hard-gate failures 0
uv run python scripts/benchmark_visualization.py --sizes 30x50,75x150,150x400,300x1000 \
  --output .planning/tmp/phase-10-benchmark.json
# measured: 30x50: 15n/13e ✓target; 75x150: 22n/37e; 150x400: 25n/46e; 300x1000: 28n/60e ✓target
# cumulative cap_raised at ≥75-node scales = D-09 fail-closed behavior, NOT a defect
```

Full backend suite needs the ephemeral-container runner
(`scripts/run_phase10_backend_tests.py`) — do not run the live-DB suite casually.

## 5. Audit technique that caught GAP-1: "green ≠ wired" call-site inventory

Phase verification re-ran unit tests only. To prove frontend↔backend wiring:

1. Grep every claimed frontend API function for imports/callers, e.g.
   `search_files(pattern='fetchVisualization|fetchExpansion|from .*api/graph', path='frontend/src')`.
2. Grep the full call-site inventory: `pattern='apiFetch'` across `frontend/src`
   (definitions in `api/*.ts` vs callers elsewhere).
3. Check whether component props are fed from production code or only from `.test.tsx`
   files (grep `propName=` — if only test files match, the path is test-only).
4. Check whether tab/mode state actually changes the rendered data (read the JSX).

## 6. Known open items (recorded in the audit, do not silently fix)

- `dexter-s01e01-enrichment` quick task incomplete (2026-08-04; Aura auth failure at
  the time — data/code/offline tests complete, live verification never done).
- STATE.md Deferred Items: full CI/CD, full observability, Person actor model,
  reviews/ratings, automated ingestion (+ multi-region hosting out of scope).
- UAT golden-path row 5 (BYOK external-provider chat) BLOCKED — zero-cost policy, no
  operator-approved key; recorded, not deferred silently.
