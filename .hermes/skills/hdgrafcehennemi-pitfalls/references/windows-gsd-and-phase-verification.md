# Windows GSD tooling, local app launch, phase verification

## node on MSYS breaks on MSYS paths — use Windows-style paths

`node /c/Users/.../gsd-tools.cjs` fails: `Cannot find module
'C:\c\Users\...'` (MSYS path mangled). Always invoke gsd-tools with the
native path:

```bash
node "C:\\Users\\arhan\\AppData\\Local\\hermes\\gsd-core\\bin\\gsd-tools.cjs" query ...
```

(Repo-local `gsd-core/bin/gsd-tools.cjs` does not exist in
hdgrafcehennemi — the shim resolution falls through to the AppData copy.)

## gsd-tools `quick-tasks-append` — pass the description ONLY

`query quick-tasks-append --task "<text>"` treats the whole string as the
Description cell (pipes get backslash-escaped, a bogus id/date/commit
column pair appears). Pass just the description text, or hand-edit the
STATE.md `### Quick Tasks Completed` table row (columns: `#` = quick_id,
Description, Date, Commit, Directory) and update the `Last activity`
line. Match the table's existing column format exactly.

## docker compose up -d gets flagged as a long-lived server

The terminal guard misclassifies `docker compose up -d neo4j` as a
watch/server process — run it with `background=true`. Container is
`spoilerless-neo4j` (compose `container_name`, neo4j:2026.06.0,
neo4j/hdgraf-local-password). Docker Desktop itself: launch via
`powershell Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'`,
then poll `docker info` (up to ~2 min).

## Local app launch recipe (hands-on testing)

1. `docker compose up -d neo4j` (background=true); wait for healthy.
2. Backend:
   `unset PYTHONPATH && source scripts/env-local.sh && export SESSION_COOKIE_SECURE=false && .venv/Scripts/python.exe -m uvicorn spoilerless.app.main:app --host 127.0.0.1 --port 8000` (background, watch "Application startup complete").
3. Frontend: `npm run dev` in `frontend/` (background, watch "ready in").
4. Verify: `/health` shows `database: connected`; `/api/series` returns data; frontend 200.
5. `.env` has only NEO4J_* keys (no aura_*) → exporting NEO4J_* wins;
   env vars beat dotenv in pydantic-settings.

## Plan-phase review loop on Windows/MSYS

- Keep researcher, UI researcher/checker, pattern mapper, planner, and plan checker in separate agent contexts. `--auto` suppresses questions; it does not permit collapsing roles.
- Run plan verification before committing `*-PLAN.md`. If the checker returns issues, revise only the plan files, re-run a fresh checker, and commit plans only after `## VERIFICATION PASSED`. If an orchestration/tool budget ends mid-revision, leave plans uncommitted and report the exact outstanding checker findings; do not claim plan-phase completion.
- Checker-facing `<verify><automated>` commands must match this repo's actual shell: POSIX/MSYS syntax (`NODE_ENV=test CI=1 npm --prefix frontend ...`, `uv run ...`, or a cross-shell Python guard), not PowerShell-only `$env:`, `Push-Location`, `Get-ChildItem`, `Test-Path`, or `$LASTEXITCODE`.
- Backend plan verification must route through the documented disposable/local database runner. A negative Aura/shared-name check is insufficient: explicitly allowlist localhost/container/disposable targets and reject remote/Aura/shared targets, live users, and `series_dexter`.
- Coverage-audit plans must validate semantic rows, not mere ID occurrence. For Phase 10 use the actual decision range `D-01..D-34`; require non-empty `source_id`, `plan_id`, `artifact_or_test`, and `evidence_ref` mappings for requirements, UI considerations, research/pattern/validation obligations, benchmarks, UAT, and docs.
- Stale-doc negative assertions should target stale claims (`prototype only`, `no deployment`, `no production base URL`) and exclude explicitly historical/audit sections. Never ban the former project name globally because legitimate history may retain it.
- Tracer-first means the first PLAN's frontmatter itself is `type: tracer`, not merely its first task. Every plan should carry concrete `must_haves.key_links` (`from`/`to`/`via`) tied to task actions and verification.

## Phase verification recipe (execute-phase tail gates)

- All plans summarized + `VERIFY_STATUS == missing` → resume at phase
  gates (aggregate_results → code_review_gate → regression_gate →
  verify_phase_goal → update_roadmap); do NOT re-dispatch executors.
- Dispatch gsd-verifier and gsd-code-reviewer in PARALLEL (one
  delegate_task batch); both read-only, no commit conflicts. Verifier:
  adversarial goal-backward, must-haves VERIFIED/FAILED/UNCERTAIN,
  human-browser truths go to `human_verification` not FAILED. Reviewer:
  scope from SUMMARY key-files cross-checked against `git diff`.
- Regression gate: only runs when prior VERIFICATION.md names concrete
  test files; UAT-style prior verifications (Phase 08) → no files → pass.
- Fix Criticals inline after review (minimal-risk, tests updated),
  then flip 09-REVIEW.md frontmatter `status: clean` + `resolution:` with
  commit SHA, then `gsd_run query phase.complete <N>`, commit tracking
  files (ROADMAP/STATE/REQUIREMENTS + VERIFICATION/REVIEW) with explicit
  paths. `phase.complete` warnings about SUMMARY stale paths are cosmetic.
- Verifier/reviewer subagents must get: unset PYTHONPATH, node Windows
  path, "never git add -A", "never commit .planning/config.json",
  project skill path to read.
