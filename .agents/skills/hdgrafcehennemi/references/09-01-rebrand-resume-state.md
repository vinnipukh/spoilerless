# 09-01 (REBRAND-01) resume state — budget handoff 2026-08-05

Continuation context for the executor taking over plan 09-01 after tool-budget
exhaustion. All three task commits are LANDED on `main`; one auto-fix is on
disk but uncommitted; SUMMARY.md + STATE/ROADMAP tracking unwritten.

## Committed SHAs (git log on main)
- `a0aa33a` feat(09-01): rename package metadata + deploy names to spoilerless
- `b94ac6f` feat(09-01): rename backend import root to spoilerless + health service field
- `2dfc826` feat(09-01): rename UI strings, storage keys (migrated), and docs to spoilerless

## Uncommitted on disk (Rule 3 auto-fix, applied but NOT committed)
- `spoilerless/tests/test_revisions.py` — lines 8 and ~616:
  `from backend.tests.test_user_content_api import ...` →
  `from spoilerless.tests.test_user_content_api import ...`
  (dots-form `backend.tests` import broke collection:
  `ModuleNotFoundError: No module named 'backend'`).

## Verified so far (real runs, this session)
- `git grep -n 'backend\.app'` = zero hits outside .lock/.planning/PROBLEMS.md;
  `git ls-files | grep '^backend/'` = 0; all renames detected by git (history kept).
- `uv run python -c "import spoilerless.app.main"` OK (SERVICE_NAME =
  spoilerless-backend); `from spoilerless.app.graph.setup import main` OK.
- `uv run pytest spoilerless/tests/test_graph_api.py -x -q` = **24 passed** (95s,
  local docker). Frontend: vitest byok 11 + watchProgress 14 + App 15 = **40
  passed** (NODE_ENV=test CI=1); `npm run build` green.
- Grep gates: `git grep -il 'hdgrafcehennemi'` and `'HD Graf Cehennemi'` (excl.
  `.planning/` + `docs/PROBLEMS.md`) = **0 / 0**.
- Intentional remaining `hdgraf` strings: `hdgraf-local-password`,
  `hdgraf:rate_limit`, legacy storage-key migration constants.

## Next steps
1. Re-run the FULL backend suite (backgrounded + notify_on_complete; docker
   container `hdgrafcehennemi-neo4j` is up, .env points at AuraDB — override
   per-run, NEVER edit .env):
   `unset PYTHONPATH && export NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j NEO4J_PASSWORD=hdgraf-local-password
   NEO4J_DATABASE=neo4j && uv run pytest`
   (~10-15 min; pre-existing seed-pollution failures = 09-05 scope, not the rename).
2. Commit the fix: `fix(09-01): sweep backend.tests imports in test_revisions.py`
3. Write `.planning/phases/09-feature-expansion-full-audit-remediation/
   09-01-SUMMARY.md` (template `~/AppData/Local/hermes/gsd-core/templates/summary.md`),
   commit `docs(09): summary for 09-01` + STATE.md/ROADMAP.md tracking via
   EXPLICIT paths only — NEVER `.planning/config.json`. docs/ROADMAP.md carries
   a pre-existing sibling diff (FEATURE-IDEAS link) that rides along by necessity
   (staging the file is required for the grep gate).
4. Final plan verification: re-run both grep gates, `git log --oneline -3` shows
   the three rename commits, no leftover legacy paths.
