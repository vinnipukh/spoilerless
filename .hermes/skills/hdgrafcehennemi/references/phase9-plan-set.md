# Phase 9 Plan Set — HD Graf Cehennemi (planning run 2026-08-05)

> Status: **PLANNING INCONCLUSIVE** — 15 of 18 PLAN.md files written in
> `.planning/phases/09-feature-expansion-full-audit-remediation/`.
> The THREE operator-wave plans (09-16/09-17/09-18) are UNWRITTEN; the parent
> instructed resuming with a fresh subagent using the same PLAN.md template.
> Read this before resuming or executing Phase 9.

## Plan table (09-01 .. 09-15 written; 09-16..09-18 MISSING)

| Plan | Wave | Requirements | Focus | Autonomous |
|---|---|---|---|---|
| 09-01 | 0 | REBRAND-01 | Full rename sweep: `git mv backend spoilerless` import root, pyproject/render/docker names, /health SERVICE_NAME + test_graph_api.py:101, UI strings, byok.ts + useWatchProgress storage keys (migrated), docs (PROBLEMS.md kept). Grep gate excludes .planning/ + docs/PROBLEMS.md | yes |
| 09-02 | 0 | PROB-14,15,23 | test_google_verifier.py (garbage token + MockTransport, never NameError) + progress wire-shape tests (fetch stub, no client mock) | yes |
| 09-03 | 1 | PROB-01,02,12,25,26,27 | Write-path: CurrentUserDependency on ALL mutations, owner-scoped update/delete, created_by, single visibility rule (spoiler/visibility.py, max(episode,progress)), real persisted revision ids, dual revert links | yes |
| 09-04 | 1 | PROB-03,04,05,16 | Anonymous boundary=1, candidates boundary required, None-order→422, uuid4 sessions + sweep + no slide-on-read | yes |
| 09-05 | 1 | PROB-09,17,19,29,30 | Uppercase error-code registry, security headers + narrowed CORS, trust nits, series_id on SOURCES/EVIDENCE MATCH, envDir:'..' + client-id equality | yes |
| 09-06 | 1 | PROB-13,24,28 | Chat failure status + logged exceptions, notes→context bucket, provider JSONDecodeError parity + dead code + bounded tool replay | yes |
| 09-07 | 2 | PROB-31,07,08 + FEAT-03 | useWatchProgress no-op/hydration fixes, newly-revealed highlight, stale-ref lint fixes (no new warn exemptions), deterministic App e2e | yes |
| 09-08 | 2 | PROB-06,18,20,22 | Scratch-series + teardown, state-independent seed asserts, zombie_sweep.py (dry-run first), CI pollution gate + dep scan + artifacts, RUNBOOK.md, core-module tests, startup schema check | yes |
| 09-09 | 3 | FEAT-01,07,08 | searchIndex.ts (zero-dep), NodeSearch, CommandPalette ⌘K, useHotkey | yes |
| 09-10 | 3 | FEAT-02,04 | TimelineView tab, SeriesDashboard dialog (augments dropdown) | yes |
| 09-11 | 3 | FEAT-05,06 | GET /export (Markdown, D-11) + POST /graph/path (find_path executor), PathFinder mode, Blob download | yes |
| 09-12 | 3 | FEAT-09 | ShareToken (hash at rest, secrets.token_urlsafe(32), 30d expiry, revoke), SAME fetch_graph path, ShareView read-only shell, seed constraints + superset assertion | yes |
| 09-13 | 3 | FEAT-10,11 + PROB-21 | Mobile breakpoints, BacklinksTab, NodeHoverCard, properties dl, revision before/after values, ErrorBoundary root+chat, debug log removal | yes |
| 09-14 | 3 | PROB-32 | fcose@2.2.0 (ONLY new dep), layoutConfig/filterState/focusReducer extraction, GraphFilterPanel, culling, deterministic positions, count-independent tests | yes |
| 09-15 | 4 | DOCS-04, PROB-10 | API.md regen from openapi + doc-contract test, ARCHITECTURE/ROADMAP fixes, MIT LICENSE, junk removal, Fandom images self-host/drop | yes |
| **09-16** | **5** | **PROB-11** | **MISSING: 09-02 push local main (4 ahead of origin/main @ 288743e, ci-smoke-test GONE) + confirm Actions green + REBRAND operator steps (GitHub repo rename + remote set-url, Render service rename, UptimeRobot rename). checkpoint:human-action, autonomous:false** |
| **09-17** | **5** | **PROB-01** | **MISSING: 09-03 operator sets ADMIN_EMAILS on Render + live admin check (candidate approve/reject/edit + ChangeSet confirm gated, non-admin 403). checkpoint:human-action** |
| **09-18** | **5** | **PROB-06,20,22** | **MISSING: 09-04 operator sets REDIS_URL rediss:// + live 429/cache checks (bounded) + PROB-20 live AuraDB reseed + PROB-22 sweep EXECUTION (dry-run → sign-off → run; aura_graph_integrity.sh before/after; never delete ae8a41b7-...). checkpoint:human-action** |

Requirement coverage: all 32 PROB + FEAT-01..11 + DOCS-04 + REBRAND-01 appear
in at least one plan's `requirements`. 09-01 (UptimeRobot) dropped per D-13.
09-05/09-06 carry-overs folded into 09-08 (PROB-22/PROB-08); 09-07/09-08
carry-overs folded into 09-08's CI/runbook artifacts. POLISH-01..03 → Phase 10.

## Design decisions to preserve on resume

- **Rename EARLY (D-12)**: every plan except 09-01 uses `spoilerless/...`
  paths and depends_on 09-01. Full import-root rename chosen (RESEARCH Open
  Q1); metadata-only is the documented fallback.
- **Wave 3 is effectively sequential** (GraphCanvas.tsx + App.tsx shared-file
  churn): 09-09 → 09-10 → 09-11 → 09-12 → 09-13 → 09-14 (PROB-32 LAST per
  constraint).
- **Operator wave ordering 09-16 → 09-17 → 09-18** (each depends_on previous);
  all autonomous work precedes it (09-16 depends_on 09-15).
- Zero-cost: only cytoscape-fcose@2.2.0; fuse.js/jspdf forbidden; all chat
  verification via FakeLLMProvider; full suite NEVER against live AuraDB.

## Verified anchors discovered during this planning run

- **No `backend/pyproject.toml` exists** — root pyproject.toml is the single
  project; CI still runs `uv run --project backend python -m
  backend.app.graph.setup` (ci.yml:24) and `uv run uvicorn
  backend.app.main:app` (render.yaml:10); smoke.sh uses `python -m
  backend.app.graph.setup`. The rename sweep must rewrite these strings.
- Rename surface (`rg -l 'hdgrafcehennemi|HD Graf Cehennemi'`, excl.
  node_modules/.planning): backend/app/main.py, backend/requirements.txt
  (delete), backend/scripts/smoke.sh, backend/tests/test_graph_api.py,
  docker-compose.yml, 14 docs files (PROBLEMS.md kept), frontend/index.html,
  App.test.tsx, LoginPage.tsx, AppShell.tsx, index.css, index.html,
  pyproject.toml, README.md, render.yaml.
- `useWatchProgress.ts:33` `STORAGE_KEY = 'hdgraf.watchProgress'`
  (sessionStorage) is a SECOND key beyond byok.ts:9 — both need migration.
- Comment-text discipline: the rename plan's negative grep gates on the old
  name literals → the plan MUST carry `<!-- planner-discipline-allow:
  hdgrafcehennemi -->` / `<!-- planner-discipline-allow: HD Graf Cehennemi -->`
  markers (they were added in 09-01-PLAN.md).
- seed-idempotency constraint-set assertion must become superset/additive in
  the SAME plan that adds the :ShareToken constraints (09-12) — RESEARCH
  Pitfall 2.
