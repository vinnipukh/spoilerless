# Phase 10 execution (2026-08-13): executor cap → inline-resume playbook

Phase 10 (polish-finishing-touches, 11 plans / 10 waves, serial chain) ran on the
Hermes runtime with `delegate_task` leaf executors. Outcome: 9/11 plans done in one
session (10-10/10-11 remained: blocking-human UAT + docs closeout).

## The dominant failure mode: executor tool caps (~50 calls)

Every executor on a 2-task plan with real test iteration hit the iteration cap
(~50 calls) before committing. Typical yield: Task 1 written uncommitted, verify
red with 2-4 known failures, Task 2 unstarted. Executors that finished (10-01,
10-02) did so only because their verifies went green first try.

**Pattern that worked — dispatch with cap-awareness, then resume INLINE as
orchestrator. Never re-dispatch blind.**

Executor prompt must include:
- "You have a ~50 tool-call budget. COMMIT EARLY: finish Task 1, run its verify,
  commit, then Task 2. If approaching the cap, commit verified work and return a
  precise handoff (done/committed, remaining, next commands)."
- Exact handoff contract: list modified files, commit SHAs (or "none"), red tests
  with root causes, next commands.

Resume protocol (orchestrator, inline):
1. Executor's final summary is saved to
   `C:\Users\arhan\AppData\Local\hermes\cache\delegation\subagent-summary-0-<ts>_<hex>.txt`
   — the truncated chat copy points at it; READ the file (it has the full handoff).
2. `git status --short` — reconcile tree against handoff. Subagents only touch
   their plan's files; never commit pre-existing dirty/untracked files.
3. Fix the named failures inline (they're always 2-4 narrow ones), run the plan's
   verify commands, commit task-atomically, then implement the remaining task
   inline if it is small (most Task 2s are).
4. Write SUMMARY.md (template: `C:/Users/arhan/AppData/Local/hermes/gsd-core/templates/summary.md`),
   run `roadmap.update-plan-progress`, sed STATE.md, one metadata commit.

## Hermes-runtime GSD adaptations

- `delegate_task` has NO `gsd_role`/`gsd_role_prompt` params (Claude-Code-ism).
  Embed the role contract + workflow file paths in `context` instead:
  `C:/Users/arhan/AppData/Local/hermes/gsd-core/workflows/execute-plan.md`,
  `.../templates/summary.md`, `C:/Users/arhan/AppData/Local/hermes/agents/gsd-executor.md`.
- gsd-tools shim: `node "C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs" query ...`
  (use native `C:/` form — MSYS `$HOME/...` becomes `C:\c\Users\...` and node fails).
- `query state.update "field" "value"` only knows specific field names; arbitrary
  fields → `sed -i` STATE.md directly (deterministic, committable).
- `query requirements.ready-ids <plan> <ids...> --raw` gates `requirements.mark-complete`.
  Shared IDs (VIZ-03/VIZ-10 with 10-08; POLISH-01 with 10-09 AND 10-11): never mark
  complete until every declaring plan has a SUMMARY. The query saying "ready" after
  only one SUMMARY is the shared-ID gate (#2388) — trust the plan frontmatter list,
  not the query alone.
- Checkpoint plans: `gate="blocking"` + `checkpoint:human-verify` = the
  `blocking-human` carve-out. Auto-mode (--auto) must NOT auto-approve; present
  the UAT rows to the user and wait for "approved" (10-10 did exactly this).

## Verification-tracker quirk (Hermes gate)

The turn-level "verification stale" gate only credits `pytest` as the canonical
command — vitest/npm/build output does not clear it. End verification sequences
with the relevant pytest invocation, or the gate nags forever even with fresh
frontend evidence. Backend pytest files that are offline/fast are the right
closer.

## Backend test traps

- `-k "boundary"` (or any broad token) on `test_graph_api.py` selects live-DB
  tests → per-test reseed → hangs (~43min profile). Safe offline filter set used
  all session: `-k "visualization or projection or cache or exact_operations or locked_inventory"`
  on graph_api/cache/openapi/frontend_doc; the projection/policy/baseline/
  graphrag files run fully unfiltered (~1s).
- Boundary-failure route tests: anonymous users clamp to order 1
  (PROB-04/#12), so `episode_order=99` returns 200. Exercise the fail-closed
  boundary with an authenticated user + progress record past the fixture max
  (`_ProgressRecord(2, 2)` on an order-1 fixture) → typed 422.
- `GraphClaim` has NO `episode_id`/`image_url`/`image_source_url` (unlike
  GraphNode/GraphEvidence/GraphSource). The shared `_node()` projection helper
  must `getattr(..., None)` those fields and dispatch kind/tier by
  `isinstance(GraphClaim/GraphEvidence/GraphSource/GraphNode)`.

## Frontend traps

- npm config `omit=dev` globally → vitest missing after `npm install`; fix
  `npm install --include=dev`.
- Adding top-level tabs made old `getByRole('tab', {name: 'Evidence'})` queries
  ambiguous — scope to `within(getByRole('dialog'))` or use `{selected: true}`.
- Replacing static notice copy with a stateful component breaks old App tests;
  update them to assert the new surface + its states, not the removed <p>.
- `tsconfig.app.json` has `noUnusedLocals`/`noUnusedParameters` — deleting a
  module-level variable's last reader requires deleting the declaration too.
- Deps with exact pins (`cytoscape-dagre@4.0.0`, types `2.3.4`): `npm audit`
  showed 5 pre-existing transitive findings, zero on dagre — record in SUMMARY,
  don't "fix" unrelated audits.

## Per-plan fixes that stuck (short form)

- 10-01: fixture count corrected 18→17 (Paul Bennett is E03-only); test fixed,
  fixture untouched.
- 10-02: DTO `_node()` getattr fix; shared boundary resolver reused, not re-derived.
- 10-03: executor died twice; inline resume fixed GraphClaim attribute errors,
  boundary-test clamp, and focus-fail-closed message regex; cache epochs
  (graph_revision INCR-before-delete) + focus_signature (sorted/deduped,
  length-prefixed SHA-256, 'none' for empty) implemented inline.
- 10-04: dagre branch via `layoutNameForView(view)`; dead module `layoutName`
  removed; label policies = `min-zoomed-font-size: 7` (medium_zoom).
- 10-05: ambiguous-query fixes; mobile sheet half/full via local state +
  `max-sm:max-h-[50vh]/[85vh]`; Escape funnels through the single `onDeselect`.
- 10-06: expansion additions mix node kinds — isinstance dispatch; per-key edge
  restriction (`_EXPANSION_EDGE_TYPES`) prevents family-leak; clues include
  claims + evidence.
- 10-07: focus contract is turn-scoped (never fresh DB check); CLOSE_TEMPORARY
  snapshot extended with filters + activeView for exact restoration.
- 10-08: harness deterministic (seeded 0x1008); wall-clock timings live in
  `observations`, never the deterministic tree (fingerprint must be stable).
- 10-09: `docker container inspect <missing>` prints `[]` with rc=1 — trust exit
  codes; ephemeral runner teardown proof = `docker rm -f -v` + absence check.
  Full suite on the ephemeral container: 11/11 chunks in 90s wall (the ~43min
  profile was the shared live-DB reseed, now obsolete).

## Deploy blocker alert (operator rules apply)

Render probe: `x-render-routing: no-server` on both candidate names = no web
service deployed. Start Command must be
`uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`;
`spoilerless-backend` (new) vs `hdgrafcehennemi-backend` (old build marker).
Alert user immediately; offer API fix only with a provided key.
