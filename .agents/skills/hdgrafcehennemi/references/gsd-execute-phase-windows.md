# GSD execute-phase on Windows (learned running Phase 10, 2026-08-13)

Orchestrating `/gsd-execute-phase` from Hermes TUI on this Windows host. Complements the bundled gsd-execute-phase workflow; these are repo/host-specific traps.

## Executor subagent tool-cap (hit 7× in Phase 10: 10-03 ×2, 10-04, 10-05, 10-06, 10-07, 10-08)

Hermes `delegate_task` children die at ~50 tool calls mid-plan, leaving **uncommitted working-tree changes** and no SUMMARY (10-03 twice, 10-04 once). The plan is NOT lost — resume, don't restart:

1. Read the child's handoff: `C:/Users/arhan/AppData/Local/hermes/cache/delegation/subagent-summary-*.txt` (it writes done/remaining/next-commands precisely).
2. Verify against `git status` + `git diff --stat` — the tree is the truth.
3. Either dispatch a **continuation executor** whose context pins the handoff file path + exact remaining steps, or take over **inline** (orchestrator executes directly) when the remaining scope is narrow — inline was faster and deterministic for the second half.
4. Prevention: put "~50 tool-call budget. COMMIT EARLY: finish Task 1, verify, commit, THEN Task 2. If approaching the cap, commit verified work and return a precise handoff" in every dispatch prompt. Bigger plans (2 large backend tasks) still died; plan for it.
5. **Inline takeover is the default, not re-dispatch.** Re-dispatching a continuation executor ALSO caps out (~50 calls) when the remaining scope includes test iteration (10-03 needed 2 executor runs + inline; every later cap was closed inline). Inline recipe: read handoff → `git status`/`git diff --stat` → apply the listed fixes → run plan's verify → task-atomic commits → SUMMARY/tracking. Orchestrator context stays lean because the handoff lists exact next commands.

## pytest -k filter trap (live-DB hang)

`-k "boundary"` or `-k "variant"` in this repo matches **live-Neo4j tests** (per-test reseed → ~43 min). A filtered run that previously passed in 29 s suddenly times out when you add those terms. Use ONLY the exact `<verify>` strings from the plan; the safe fast filters seen:
- `-k "visualization or projection or cache or exact_operations or locked_inventory"` (offline, ~30–100 s)
- Full-file runs of `test_visualization_projection.py` + `test_spoiler_policy.py` + `test_visualization_baseline.py` are offline (~0.3 s) — safe unfiltered.

Also: `uv run pytest --timeout=120` REJECTS the flag (pytest-timeout not installed under uv); plain `pytest` flags only. The full live suite's `--timeout` works with `.venv/Scripts/python.exe -m pytest`.

## npm config omit=dev (machine-wide)

This host's npm config has `omit=dev` globally → after any node_modules re-sync, vitest/tsc binaries are missing and `npm test` fails with "'vitest' is not recognized". Fix: `npm --prefix frontend install --include=dev`. Check with `npm config get omit`.

## gsd-tools.cjs path from git-bash

`node "$HOME/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"` FAILS: MSYS expands `$HOME` to `/c/Users/...`, node re-parses it as `C:\c\Users\...` → MODULE_NOT_FOUND. Always pass the literal `C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs` (forward slashes work in node).

## STATE.md / ROADMAP.md verbs

- `gsd_run query roadmap.update-plan-progress <phase> <plan> complete` — works; updates ROADMAP.
- `gsd_run query state.update stopped_at ...` — **rejects** unknown fields ("Field stopped_at not found in STATE.md"). Patch STATE.md frontmatter/body manually (sed) for `stopped_at`/`last_activity_desc`/`Current Position`; the executors themselves also left the body stale — orchestrator should refresh it once per plan.
- Sequential mode: executors own STATE/ROADMAP; worktree mode: orchestrator does. With inline takeover, the orchestrator must do both.

## Post-merge gate scoping (serial, USE_WORKTREES=false)

Per-wave full-suite gate is impractical (~43 min live-DB). Run the focused pytest union (safe -k filter above + offline files) per wave; the full suite belongs to plan 10-09 ("run and close the complete automated Phase 10 regression gate") and the final regression gate. NOTE: the hermes verification tracker credits only `pytest` as the last command — vitest runs do not clear "stale" flags on frontend paths, and full `hermes verify` mid-phase conflicts with running executors. Say so honestly; the vitest+build evidence is what matters.

## OpenAPI inventory bumps (D-29 pattern)

Each new route bumps counts in THREE places in the same commit: `test_openapi_contract.py` (path set + `len(schema["paths"])`), `test_frontend_contract_doc.py` (EXPECTED_OPERATIONS + counts), `docs/reference/frontend-api-contract.md` (inventory table + count text). Phase 10: 50/37 → 51/38 (10-03 visualization route) → 52/39 (10-06 expand route).

## Shared requirement IDs

VIZ-03/VIZ-10 span plans 10-01 and 10-08: do NOT mark shared IDs complete in REQUIREMENTS.md until ALL owning plans have SUMMARYs (the shared-ID gate blocks it; 10-01 executor documented this correctly).

## blocking-human checkpoints stop --auto --chain

Plan 10-10 is `checkpoint:human-verify gate=blocking` — the auto-mode carve-out suspends auto-approval even under `--auto --chain`. The orchestrator must halt at wave 9 and present UAT to the user; do not auto-approve.

## Scene-key / layout lessons (10-04 frontend)

- View-scoped stored positions key `viz:<view>`; layout engine routed per view via `layoutNameForView` (dagre rankDir LR only for `investigation`; fcose otherwise). Removing the module-level `layoutName` var was required (noUnusedLocals).
- medium_zoom label policy via `min-zoomed-font-size: 7` on node + interaction-driven edge label selectors — pure stylesheet, no JS zoom listeners.
- Vitest command: `NODE_ENV=test CI=1 npm --prefix frontend test -- --run <files>`; typecheck = `npm --prefix frontend run build`.

## 10-05 four-tab strip: ambiguous role queries + tsc + Escape

- The new top-level tab strip shares labels with DetailPanel's inner tabs (`Evidence`) and nested mode tabs (`Answer Graph`) → unscoped `getByRole('tab', {name})` / `getByText` queries in OLD tests become ambiguous and fail. Fixes: scope inspector assertions with `within(screen.getByRole('dialog'))`; assert the selected nested tab with `getByRole('tab', { name, selected: true })`. Any future UI that adds a top-level navigation surface will re-trigger this class of failure in pre-existing tests.
- `tsc -b` (npm run build) compiles TEST files too: unused vars in `App.test.tsx` (TS6133, `noUnusedLocals`/`noUnusedParameters`) break the build even when all tests pass. Unused test helpers/params are build errors — clean them up, don't ignore.
- Escape close of the Inspector must funnel through `onDeselect` (`e.preventDefault(); closeInspector()`) — NEVER let Radix auto-close: the left inspector + right ChatSheet are two non-modal sheets that coexist, and Radix DismissableLayer would close the other one. Same contract as `onInteractOutside` preventDefault.
- GraphClaim has NO `episode_id`/`image_url`/`image_source_url` fields (unlike GraphNode/Source/Evidence). Shared projection helpers that build VisualizationNode from mixed node kinds must use `getattr(node, "episode_id", None)` etc. — 10-03 investigation view crashed on `claim.episode_id` until fixed.

## 10-06/10-07 backend test traps

- `additions_by_id` in `project_expansion` mixes GraphNode + GraphClaim + GraphEvidence + GraphSource. Dispatch the tier/kind decision by `isinstance(...)`, never `node.type` (GraphClaim has no `.type`; evidence/source neither) and never `node_by_id[nid]` for additions.
- Per-key edge restriction (`_EXPANSION_EDGE_TYPES`): family expansion must NOT surface KNOWS/work edges between kept nodes — tests assert exact edge-class lists.
- `TimelineItem` exposes `id`, NOT `node_id` — two 10-07 tests crashed on `item.node_id`.
- `LLMEvent` imports from `spoilerless.app.llm.provider` (module `llm.events` does NOT exist).
- Offline pipeline test harness is importable: `from spoilerless.tests.test_retrieval_pipeline import _StubDatabase, _StubProgressService, _CallScriptedProvider, NODE_N1, CLAIM_C1, ...`. Citation survival only checks `claim_id`/`evidence_id`/`source_id` membership — a done event with `citations=[{"claim_id": ...}]` is enough for end-to-end focus tests.
- Boundary-failure route tests need an AUTHENTICATED user + `_ProgressRecord(2, 2)` — anonymous users clamp to order 1 (PROB-04/#12), so `episode_order=99` returns 200, not the typed 422.
- Micro-event focus substitution (10-07): synthetic micro Event must be appended to BOTH `graph.nodes` (GraphNode) and the `SafeEventContext` list — focus validation checks the node set first.

## 10-07 frontend: temporary-scene restoration

- `TemporarySnapshot` must capture filters (`nodeKindFilters`/`edgeClassFilters`) + `activeView` too — plan acceptance says "exact" restoration (D-41). Extend `takeSnapshot` AND `CLOSE_TEMPORARY` together; the snapshot test asserts each field.
- Replacing a static notice `<p>` with a real component breaks the old notice-copy test: assert the component's real state-dependent copy (empty focus → "No focus resources are visible at the current boundary.") and Close→Investigation-mode behavior instead.

## 10-09 prerequisite: Docker Desktop daemon

The regression gate plan provisions an ephemeral Neo4j container and REFUSES the developer container. Before executing 10-09, check `docker ps`; if the daemon is down start it from git-bash: `cmd //c start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"` then wait for `docker ps` to succeed.
