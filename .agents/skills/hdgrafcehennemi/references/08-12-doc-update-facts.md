# 08-12 doc-writer corrections — stale claims in THIS skill

Verified 2026-08-12 during the docs/DEVELOPMENT.md update (gsd-doc-writer).
These correct stale claims still sitting in this skill's SKILL.md and in
`references/local-docker-test-workflow.md`; fold them in on the next full
SKILL.md edit (this review turn could not patch SKILL.md — deduped).

## docker-compose password: NOT hardcoded
SKILL.md says "docker-compose.yml hardcodes Neo4j auth neo4j/hdgraf-local-password"
— STALE. Live file (08-12):
- `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` — env fallback, not hardcoded.
- Image pinned `neo4j:2026.06.0-community` (same tag as CI's service), container
  name `spoilerless-neo4j`.
- `.env.example` ships `NEO4J_PASSWORD=change-me`, but `scripts/env-local.sh`
  pins `NEO4J_PASSWORD=hdgraf-local-password`. A compose container created with
  the fallback password REJECTS test connections (tests source env-local.sh).
- Fix: `NEO4J_PASSWORD=hdgraf-local-password docker compose up -d` (or set it in
  root `.env` before first `up`) so one DB serves app + tests.
- This machine's live shared local container is `spoilerless-neo4j`
  (docker-compose `container_name`, 2026.06.0-community); the legacy
  `hdgraf-neo4j` / `hdgrafcehennemi-neo4j` containers are retired/exited.

## `--project spoilerless`: pyproject.toml is at the REPO ROOT
`references/local-docker-test-workflow.md` says "--project spoilerless required
— pyproject.toml lives in spoilerless/, repo root has none" — STALE. Verified:
pyproject.toml is at the repo root; `uv run --project spoilerless python -c ...`
still works (uv discovers the project from the directory). CI uses
`uv run --project spoilerless python -m spoilerless.app.graph.setup` and
`uv run pytest` from root.

## API surface: 50 ops / 37 path templates (not 45/33)
SKILL.md's "Pre-public-deployment audit" section quotes the 08-04 audit's
"45 ops / 33 paths" (HEAD 9caa85b) — that is a historical snapshot, not the
current surface. Verified 08-12: `spoilerless/tests/test_frontend_contract_doc.py`
locks **50 operations / 37 path templates** (asserts `len(documented) ==
len(generated) == 50` and `len(EXPECTED_TEMPLATES) == 37`).
**Superseded 08-14** (re-verified during the ARCHITECTURE.md update): the same
test now asserts **52 operations / 39 path templates** (`len(documented) ==
len(generated) == 52`, `len(EXPECTED_TEMPLATES) == 39`) — the surface grew with
the visualization/expansion endpoints. This repo's API surface moves fast:
never cite ANY count (including this file's) without reading the test's live
asserts first.
**CORRECTION (08-14):** `spoilerless/tests/test_openapi_contract.py` is NO
LONGER stale — it now locks the 39-template surface (`assert
len(schema["paths"]) == 39`; comment: "current inventory instead of the stale
45-op/32-path set") with typed operations (every DELETE 204 or 200-with-body)
and is a GREEN member of the zero-failure baseline alongside
test_frontend_contract_doc.py. The "still asserts 32 / never cite" claim below
was true 08-12 but wrong by 08-14 — re-grep before repeating it.

## PROBLEMS.md: NINETEENTH PASS (2026-08-13) is the newest pass
`docs/PROBLEMS.md` is maintained in numbered passes. NINETEENTH PASS
(2026-08-13) retired the old seven-red baseline via the guarded
ephemeral-container runner (`scripts/run_phase10_backend_tests.py`); the
next ledger append after any docs/verify session = TWENTIETH PASS.
(As of 2026-08-14; pass numbers move — grep `## ... PASS` in PROBLEMS.md for
the live newest before citing.) README's docs index calls PROBLEMS.md the
"Audit ledger — findings and fixes across passes".

## LICENSE and CONTRIBUTING.md now EXIST
SKILL.md says "NO LICENSE and NO CONTRIBUTING.md in the repo → do not fabricate
a license type or a contributing link" — STALE as of 08-12. Repo root has
`LICENSE` (1010 B, MIT) and `CONTRIBUTING.md` (10 KB, "Contributing to
Spoilerless", updated 08-10, with Branches-and-Commits + Pull-Request-Checklist
sections). Docs may link them.

## Other doc-writing path fixes (09-01 rename fallout)
- SKILL.md "Verify every API-table row by grepping `prefix=` in
  `backend/app/api/*.py`" — use `spoilerless/app/api/*.py`; `[project.scripts]`
  is `spoilerless-setup = spoilerless.app.graph.setup:main`; app at
  `spoilerless/app/main.py`.
- Backend package layout (verified 08-12): `spoilerless/app/` =
  api, domain, graph, repository, retrieval, services, llm, core, spoiler,
  revisions, cache + main.py. No `backend.app.*` paths in live source (only
  stale hits in `.planning/`).
- Frontend API-prefix consumers (for the `/api/api` pitfall): `client.ts`,
  `chat.ts`, AND `export.ts` all prepend `VITE_API_BASE_URL` ('' by default).
- `test_frontend_contract_doc.py` is the live inventory gate; the closed
  inventory sync rule (52 ops / 39 templates as of 08-14) must be kept in sync
  with it — re-read its asserts before citing any count.
