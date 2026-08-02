---
phase: 2
slug: polished-cytoscape-graph-experience
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-29
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.10 + @testing-library/react 16.3.2 (none currently installed — Wave 0 installs) |
| **Config file** | none — Wave 0 creates `vitest.config.ts` (or a `test` block in `vite.config.ts`) |
| **Quick run command** | `npm run test -- --run <file>` (once configured) |
| **Full suite command** | `npm run test -- --run` |
| **Estimated runtime** | ~10-15 seconds (estimate — small component-test surface, no baseline yet) |

---

## Sampling Rate

- **After every task commit:** Run `npm run test -- --run <changed-file-test>` + `npm run lint`
- **After every plan wave:** Run `npm run build && npm run lint && npm run test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01/T2 | 02-01 | 1 | UI-01, UI-02 | T-02-04 | React auto-escaping only; no `dangerouslySetInnerHTML` | component (tracer, RTL + user-event) | `npm run test -- --run src/App.test.tsx` | ✅ exists | ✅ passed (part of full-suite run below) |
| 02-04/T1 | 02-04 | 3 | UI-02 | T-02-02 | Defensive `sessionStorage` JSON.parse in try/catch with D-01 fallback | unit (`renderHook`) + component (RTL + user-event) | `npm run test -- --run src/hooks/useWatchProgress.test.ts src/components/episode/ConfirmAdvanceModal.test.tsx` | ✅ created (commit 70a9c66) | ✅ passed — 12/12 tests (2 files) |
| 02-02/T2 | 02-02 | 2 | UI-03 | T-02-06 | Backend is sole authority on visibility; frontend never client-side filters by `visible_from_order` | component (mount `GraphCanvas` w/ fixture `GraphResponse`) | `npm run test -- --run src/components/graph/GraphCanvas.test.tsx` | ✅ exists | ✅ passed (part of full-suite run below) |
| 02-03/T1, 02-03/T2 | 02-03 | 2 | UI-04 | T-02-09 | Render evidence/claim text via JSX interpolation only | component | `npm run test -- --run src/components/detail/DetailPanel.test.tsx src/components/detail/StructuralEdgeCard.test.tsx` | ✅ exists | ✅ passed (part of full-suite run below) |
| 02-04/T2 | 02-04 | 3 | UI-05 | T-02-12, T-02-13 | Tree-wide grep audit (no `dangerouslySetInnerHTML`, no client-side `visible_from_order` filtering) + full suite | build/lint (existing) + full test suite + manual/conversational UAT | `npm run build && npm run lint && npm run test -- --run` | ✅ existing scripts | ✅ passed — manual UAT completed 2026-07-29 (see below) |

**02-04/T2 automated sub-check results (run 2026-07-29):**

1. `npm run test -- --run` (full suite, all 4 plans together for the first time): **6 test files, 25 tests, all passed.** (`App.test.tsx`, `GraphCanvas.test.tsx`, `DetailPanel.test.tsx`, `StructuralEdgeCard.test.tsx`, `useWatchProgress.test.ts`, `ConfirmAdvanceModal.test.tsx`)
2. `npm run build && npm run lint`: **both exit 0.** (`tsc -b && vite build` succeeded with one non-fatal chunk-size-warning notice, no errors; `eslint .` produced zero output/warnings.)
3. Grep audit for `dangerouslySetInnerHTML` across `frontend/src`: **zero matches.**
4. Grep audit for `visible_from_order` in `graphElements.ts` and `GraphCanvas.tsx`: **`graphElements.ts` has one match, a comment (not a filter/exclude condition) explaining why the function must never re-filter by this field; `GraphCanvas.tsx` has zero matches.** No client-side filter/exclude pattern found in either file.
5. Manual Definition-of-Done demo script against `npm run dev` + live backend: **completed 2026-07-29** (see Manual-Only Verifications below for the full run and a real bug found + fixed along the way).

Task ID / Plan / Wave columns filled in by `/gsd-planner` (4 plans, waves 1/2/2/3); the Requirement → Test mapping is locked from `02-RESEARCH.md`'s Validation Architecture section. Actual pass/fail status is recorded by `/gsd-execute-phase` and `/gsd-verify-work`.

---

## Wave 0 Requirements

All Wave 0 gaps are assigned to 02-01 (Wave 1), Task 2, gated by 02-01 Task 1's blocking-human package-legitimacy checkpoint:

- [ ] `test` block inside `frontend/vite.config.ts` — test environment `jsdom`, globals enabled (02-01/T2)
- [ ] `frontend/src/test/setup.ts` — imports `@testing-library/jest-dom` matchers (02-01/T2)
- [ ] `package.json` `"test"` script — `vitest` (02-01/T2)
- [ ] Fixture data — hand-written `GraphResponse` fixtures (order 1 in 02-01/T2, order 3 added in 02-02/T2) mirroring the live shapes from RESEARCH.md `## Code Examples` / Pitfall 3
- [ ] `checkpoint:human-verify` task before installing `vitest`, `@testing-library/jest-dom`, `jsdom` (02-01/T1, per Package Legitimacy Audit `SUS` verdicts in RESEARCH.md)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full demo flow (select Dexter + S01E01 → explore graph → confirm advance → see unlocked data) works end-to-end | UI-05 | Cross-cutting UX/visual flow spanning graph, modal, and detail panel together; automated component tests cover pieces, not the felt experience | Conversational UAT per phase success criteria: select Dexter/S01E01, confirm only allowed elements render, open character/claim/evidence details, confirm the advance-confirmation gate fires, confirm newly unlocked data appears after confirming |

**Run 2026-07-29 — result: PASS, with one real bug found and fixed along the way.**

Environment setup required before the demo could even load (none of this was a Phase 2 code defect):
- A stray dev server from an unrelated old checkout (`hdgrafcehennemi`, pre-Phase-2 commit) was bound to port 5173, masking the real app. Killed it, started the correct one from `frontend/`.
- Neo4j and the backend `uvicorn` process were not running; started both.
- `frontend/vite.config.ts` had no dev-server proxy for `/api/*` — requests silently returned Vite's own `index.html` (200 OK, wrong content) instead of reaching the backend. Added `server.proxy` for `/api` → `http://127.0.0.1:8000`.

Real bug found in Plan 02-02's `GraphCanvas.tsx`: `elements` was recomputed as a new array/object identity on every render instead of memoized. `react-cytoscapejs` re-applies its declarative `layout` whenever the `elements` prop reference changes, so any unrelated parent re-render restarted the async `cose-bilkent` layout mid-flight, racing with itself and occasionally locking the viewport onto a mid-computation zoom (nodes rendered as a tiny overlapping cluster, or one node zoomed in enormously, depending on timing). Fixed with `useMemo(() => graphToElements(graph), [graph])`. Verified: `tsc -b` clean, all 25 tests still pass, and the graph now self-fits correctly within a few seconds of `cose-bilkent`'s convergence with no manual zoom needed.

Demo steps, all confirmed:
1. Select Dexter → S01E01: graph renders correctly (11 nodes, correct shapes/edges, only S01E01-visible content — no S01E02/S01E03 leakage).
2. Character node (Dexter Morgan): Overview/Claims/Evidence tabs populate; tap-driven neighbor highlight/fade works.
3. Claim-backed edge (TRUSTS): same tabbed detail, filtered to that claim.
4. Structural edge (PART_OF): distinct `StructuralEdgeCard`, no tabs, as specified.
5. Advance to S01E02: confirmation modal appears with correct forward copy ("Unlock S01E02?").
6. Confirm: new S01E02 nodes/relationships appear that were not visible before confirmation. No console errors throughout.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-29 (conversational UAT run via browser automation, reviewed and accepted by user)
