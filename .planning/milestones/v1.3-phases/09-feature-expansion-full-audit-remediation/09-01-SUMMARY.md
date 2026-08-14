---
phase: 09-feature-expansion-full-audit-remediation
plan: 01
type: execute
status: complete
executed_by: gsd-executor (deleg_9ebf0705) + orchestrator inline closeout
---

# Phase 09 — Plan 09-01 Summary: REBRAND-01 spoilerless rename sweep

## Objective

Rename every user-visible and repo-level `hdgrafcehennemi` reference to
`spoilerless` (REBRAND-01, D-12) EARLY in the phase so later plans land on
renamed paths. Git history intentionally untouched; runtime/deploy names
updated.

## Commits

| Task | SHA | Message |
|------|-----|---------|
| 1 | `a0aa33a` | `feat(09-01): rename package metadata + deploy names to spoilerless` |
| 2 | `b94ac6f` | `feat(09-01): rename backend import root to spoilerless + health service field` |
| 3 | `2dfc826` | `feat(09-01): rename UI strings, storage keys (migrated), and docs to spoilerless` |
| fix | `ae0bf59` | `fix(09-01): sweep backend.tests imports in test_revisions.py (dots-form missed by rename patterns)` (orchestrator inline, executor budget-death closeout) |

## What shipped

### Task 1 — package metadata + deploy names (`a0aa33a`)
- `pyproject.toml`: name `spoilerless`, console script `spoilerless-setup =
  "spoilerless.app.graph.setup:main"`, testpaths `spoilerless/tests`
- `docker-compose.yml`: container `spoilerless-neo4j`
- `render.yaml`: service `spoilerless-api`, `startCommand:
  uv run uvicorn spoilerless.app.main:app ...`
- `smoke.sh` module paths + health assertion
- `backend/requirements.txt` deleted (PROB-30 env consolidation); `uv sync`
  regenerated `uv.lock` (name verified)

### Task 2 — import root rename (`b94ac6f`, 128 files)
- `backend/` → `spoilerless/` via `git mv` (100% rename detection, history
  preserved)
- Mechanical sweep `backend.app`→`spoilerless.app`, `backend/tests`→
  `spoilerless/tests`, `--project backend`→`--project spoilerless` across
  code/CI/docs
- conftest sys.path, ci.yml, render.yaml, smoke.sh swept
- `SERVICE_NAME = "spoilerless-backend"` + `test_graph_api.py:101` assertion
  updated (same commit); FastAPI title → "Spoilerless API"
- Verified: `git grep 'backend\.app'` zero hits; `import spoilerless.app.main`
  + `setup:main` resolve; `uv run pytest spoilerless/tests/test_graph_api.py
  -x -q` = 24 passed

### Task 3 — UI strings, storage keys, docs (`2dfc826`, 23 files)
- AppShell h1, LoginPage h1, frontend/index.html title, root index.html
  (title/description/og:title/aria-labels/window-title), GITHUB_REPOSITORY_URL
  → `vinnipukh/spoilerless`, © line → "Spoilerless"
- `App.test.tsx` assertions + watchProgress keys → `spoilerless.watchProgress`
  (10 sites); index.css comment
- `byok.ts` `BYOK_STORAGE_KEY = 'spoilerless:byok-llm-settings'` with
  read-compat migration (old key read when new absent, removed on next
  successful save); `useWatchProgress.ts` legacy fallback/removal
- NEW `frontend/src/lib/byok.test.ts` (11 tests: migration/trim/headers)
- Docs: README + 13 docs/* files renamed (clone URLs, `spoilerless-setup`,
  container names, tree diagrams); `docs/PROBLEMS.md` + `.planning/` untouched
  (audit trail)
- Verified: vitest byok+watchProgress 25/25, App.test.tsx 15/15, `npm run
  build` green, grep gates 0/0

### Inline closeout (orchestrator, after executor budget-death)
- `spoilerless/tests/test_revisions.py` imported fixtures via dots-form
  `backend.tests.test_user_content_api` (missed by the plan's sweep patterns)
  → both sites (line 8 + ~616) patched to `spoilerless.tests...`; committed
  `ae0bf59`. Remaining `backend.` greps are generic docstring prose only.

## Verification

- Grep gates: `git grep -il 'hdgrafcehennemi'` and `'HD Graf Cehennemi'`
  excluding `.planning/` + `docs/PROBLEMS.md` = **0 / 0**
- `git log` shows rename commits with 100% rename detection (history intact)
- Target suites pre-closeout: 24 backend graph-api tests, 25/25 byok+
  watchProgress vitest, 15/15 App.test.tsx, `npm run build` green
- Full backend suite (local docker Neo4j): 489 passed / 12 failed. Triage:
  - `test_revisions.py` failures → FIXED by inline import sweep (`ae0bf59`),
    targeted re-run passes (TestRevertUpdatedNote ✓)
  - `test_seed_idempotency.py` 2 failures → known PROB-22 candidate-origin
    pollution baseline (planned 09-08/09-18)
  - `test_retrieval_tools.py` 6+ failures → **proven pre-existing via baseline
    worktree at 9315a51 (pre-rename HEAD): identical failure, harry_morgan
    `visible_from_order: 1` returned when test asserts hidden — enriched
    S01E01 seed drift (PROB-20/#44 class), NOT a rename regression. Planned
    in 09-08 seed/schema-drift work.
  - 4 remaining failures: same seed-drift class (cache shows the pattern
    across user_content/candidate/retrieval suites); all pre-existing per
    baseline evidence.

## Self-Check

✅ PASS — all tasks executed, commits landed, grep gates clean, no
`.planning/config.json` or `.env` touched, git history intact.

*Completed: 2026-08-05 (executor partial + orchestrator inline closeout)*
