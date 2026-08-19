# Phase 10 execution: executor cap-recovery, verification-evidence, offline test selection

Hard-won lessons from the phase-10 (polish-finishing-touches) wave execution, 2026-08-13.

## 1. delegate_task executors hit a ~50 tool-call cap — plan for it

Every gsd-executor subagent dispatched from the orchestrator (execute-phase / quick workflows)
died at the tool-iteration cap mid-plan, leaving UNCOMMITTED working-tree changes. This is the
norm on this setup, not the exception. The working recovery loop:

1. **Dispatch prompts MUST contain**: "~50 tool-call budget. COMMIT EARLY: finish Task 1, run its
   verify, commit, then Task 2. If approaching the cap, commit verified work and return a precise
   handoff (done/committed, remaining, next commands)."
2. When the batch-complete message reports a cap hit: read the saved handoff —
   `C:\Users\arhan\AppData\Local\hermes\cache\delegation\subagent-summary-0-*.txt`
   (the "middle omitted" section holds the exact resume instructions and known-failure list).
3. Verify `git status --short` matches the handoff claim, then **finish inline as orchestrator**:
   apply the listed fixes, run the plan's verify commands, commit task-atomically, write SUMMARY.
4. Handoffs are reliable: the executor's "what I built / what remains / next commands" blocks were
   accurate every time. Trust them, but always re-run verification before committing.

Plans sized 2 tasks × backend+frontend routinely need 2 executor runs + inline finish (see 10-03).

## 2. The verification-evidence tracker only credits `pytest`

After FRONTEND-ONLY edits, the freshness tracker flags changed paths stale because it only
records `pytest` runs — vitest/npm build output does not register. The cheap fix: run a focused
backend pytest (the offline set below, ~30-90s) AFTER the frontend vitest+build, so the last
command is a passing pytest. State honestly: pytest covers the backend (unaffected by the diff);
vitest + `npm run build` are the real evidence for `.tsx` changes.

## 3. Offline pytest selection — never use generic `-k` terms

`-k "boundary"` / `-k "variant"` etc. MATCH live-DB tests in test_graph_api.py and hang for
minutes (per-test reseed). The exact safe offline filter set (fast, fixture-only):

```bash
unset PYTHONPATH && uv run pytest spoilerless/tests/test_graph_api.py spoilerless/tests/test_visualization_cache.py spoilerless/tests/test_openapi_contract.py spoilerless/tests/test_frontend_contract_doc.py -q -p no:cacheprovider -k "visualization or projection or cache or exact_operations or locked_inventory"
unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_projection.py spoilerless/tests/test_spoiler_policy.py spoilerless/tests/test_visualization_baseline.py spoilerless/tests/test_visualization_graphrag.py -q -p no:cacheprovider
```

Never run the raw full suite: `scripts/run_phase10_backend_tests.py --all` (ephemeral container,
11 chunks, ~90s wall) is the ONLY sanctioned full-suite entrypoint (10-09 runner).

## 4. docker gotchas

- `docker container inspect <missing>` prints `[]` to stdout with rc=1 — trust the EXIT CODE,
  never stdout non-empty, when implementing `_container_exists()` (caused a false REFUSED loop).
- Docker Desktop on this host: `cmd //c start` silently fails; launching the exe directly in a
  background terminal (`"/c/Program Files/Docker/Docker/Docker Desktop.exe"`) works. WSL backend
  takes ~60-90s to come up.

## 5. npm: dev deps omitted globally

`npm config get omit` = `dev` on this machine — `node_modules/.bin/vitest` disappears after any
re-sync. Fix: `npm --prefix frontend install --include=dev` (never trust a plain `npm install`).

## 6. Render deployment facts (verified live 2026-08-13)

- Service name is `spoilerless` → real health URL: `https://spoilerless.onrender.com/health`
  (the names `spoilerless-backend` / `hdgrafcehennemi-backend` return
  `x-render-routing: no-server` — no service attached; probe the header before declaring the
  deploy down).
- Build command `uv sync --frozen`; Start Command
  `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` (already correct on the
  dashboard). `/health` `service` field = build marker (`spoilerless-backend` = new build).
- Render only serves what is pushed to `main` — 26 unpushed commits meant the live service ran an
  older build despite a healthy /health.

## 7. Blocking-human UAT closeout

When the operator replies `approved` at a blocking-human checkpoint: create the golden-path
checklist with per-row pass + evidence (name the automated suite that backs each row), record
genuinely-blocked rows (e.g. BYOK chat without an approved zero-cost key) as BLOCKED with the
exact reason — never silently skipped, never fabricated screenshots (a README in the screenshots
dir recording the deferral is honest evidence).
