# TWENTIETH-PASS docs-update run (2026-08-14) — verified facts & pipeline lessons

Full gsd-docs-update run (9 canonical docs updated + 24 review docs verified). Facts verified against live source; reuse next run.

## Current live facts (verified this run)
- **API surface: 52 ops / 39 path templates** — `spoilerless/tests/test_frontend_contract_doc.py` asserts `len(documented) == len(generated) == 52`, `len(EXPECTED_TEMPLATES) == 39`. The 08-12 ref's 50/37 is STALE; never trust old doc numbers — re-derive from routers + the contract test.
- **render.yaml service name = `spoilerless-api`** (renamed from `hdgrafcehennemi-api`, commit a0aa33a); `/health` `SERVICE_NAME="spoilerless-backend"` (main.py:38). Render dashboard service name may differ ('spoilerless') — probe spoilerless.onrender.com/health.
- PROBLEMS.md newest pass: **NINETEENTH** (2026-08-13, "guarded ephemeral-container runner retires the seven-red baseline"). This run appends TWENTIETH.
- `.python-version` = **3.13**. CI exists: `.github/workflows/ci.yml` (backend+frontend jobs, DB-pollution gate) + `release.yml` (skeleton: `contents: read`, echo-only gate).
- **NODE_LABELS (12)**: Series, Episode, Character, Event, Location, Organization, Object, Claim, Source, EvidenceFragment, UserNote, Revision — NO `Season`/`Scene` labels (those names appear only in ontology YAML/data keys). Component diagrams listing Season/Scene as graph labels = FAIL.
- **CSRF**: `CsrfGuardDependency = Annotated[None, Depends(verify_origin)]` in `api/deps.py` (~line 210); fail-closed 403 `AUTH_ORIGIN_NOT_ALLOWED`; `*` disables; wired on every cookie-authenticated write (google/logout/settings/candidates/change_set/chat/progress/share/user_content); `POST /graph/path` (optional session) is the only unguarded write-shaped route.
- **Rate limiting fully fail-open in BOTH paths** (PROB-23 / SEVENTEENTH PASS) — `RedisBucket.init()` wrapped; limits 10/300 login, 20/60 chat, 30/60 content-write (services/rate_limit.py verbatim).
- **LLM disabled-provider 503 code = `LLM_DISABLED`** (not LLM_PROVIDER_DISABLED).
- `services/settings.py` strips api_key/base_url/model before persisting (#30 whitespace-key issue fixed).
- `.env.example`: `SESSION_COOKIE_SECURE=true` now at **line 16** (moved from line 10) — RESOLVED-banner line-pins drift.
- CONTRIBUTING.md heading: `## Branches, Commits, and the Issue Ledger` (slug `branches-commits-and-the-issue-ledger`; old `#branches-and-commits` anchor broken).
- **Visitor mode**: `DetailPanel.tsx:759-763` hides Notes/History tabs + write affordances when `readOnly` (visitor) — docs claiming the inspector still shows them = stale.
- Revision revert (`revert_revision_work` in `revisions/__init__.py`) does **NOT** call `invalidate_series` — known live omission; DEPLOYMENT.md documents it as known-bug phrasing.
- VERIFY marker counts (08-14): DEPLOYMENT **14**, CONFIGURATION **5**, README **4**, API **1**.

## Pipeline lessons (docs-update orchestration)
- **Verifier tool-cap backfill**: verifier subagents can exhaust their tool-iteration budget AFTER completing checks but BEFORE writing `.planning/tmp/verify-<doc>.json` (API.md 88/88 case). Parent backfills the artifact from the reported counts; contract: `claims_passed + claims_failed == claims_checked`, `len(failures) == claims_failed`, exact key set.
- **PROBLEMS.md ledger semantics**: verifiers flag historical entries as failures. Classify: RESOLVED/FIXED banners are LIVE claims (stale line-pins, overclaiming fix records = real fixes); description text below banners is audit-trail history — never rewrite it. This run: 11 flagged → 2 real fixes (L54 line-pin 10→16; #60 FIXED record overclaiming revert invalidation), 9 historical skips.
- **`hermes verify` on this repo**: detected recipe = `pytest` (T10-LEAK-09 violation — unguarded shared-DB run). Safe evidence channel: `hermes verify --phase bootstrap --json` (uv sync only, no DB touch). Fixing the recipe via `.hermes/environment.json` needs user approval (approval prompt can time out in AFK runs — record blocker, don't retry).
- **Guarded runner ops**: refuses when shared container `spoilerless-neo4j` is live (T10-LEAK-09) and when `python` lacks neo4j (hermes terminal PYTHONPATH shadow). Correct invocation: stop shared container → `unset PYTHONPATH; .venv/Scripts/python.exe scripts/run_phase10_backend_tests.py` → restart container (volume-persisted, zero data risk). Docker Desktop down → `Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'`, poll `docker info` (~30-60s).
- **Wave pairing (max 2 parallel writers)**: readme+architecture, configuration+getting_started, development+testing, api+deployment, contributing. Agent prompt recipe: required_reading (role file + `doc-claim-verification.md` + dated facts ref) + `<doc_assignment>` + orientation bullet hints; omit `model` param when doc_writer_model empty.
