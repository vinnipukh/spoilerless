# ROADMAP fix-iteration reverification — 2026-08-02

## Outcome

After fix iteration 1, root `ROADMAP.md` was independently re-read and reverified against live source, tests, git history, and `.planning/STATE.md`.

Result artifact: `.planning/tmp/verify-ROADMAP.md.json`

- `claims_checked`: 82
- `claims_passed`: 82
- `claims_failed`: 0
- `failures`: `[]`

## Stable verification ledger

The 82 claims comprise the established roadmap status/current-state ledger:

- 59 task-checkbox claims: 58 checked implementations and one intentionally unchecked literal legacy endpoint.
- 2 milestone status claims: Milestone 1 complete and Milestone 9 complete.
- 21 current-stack, acceptance, and delivered-behavior claims.

Do not blindly reuse the count after later roadmap edits. Re-extract the ledger from the current file, then compare with 82 only as a drift signal.

## Key endpoint distinction

The unchecked literal endpoint remains correct:

- Absent: `GET /api/graph?series_id=series_dexter&visible_until_order=1`
- Delivered equivalent: `GET /api/series/{series_id}/graph?visible_until_order=...`

Comments mentioning `/api/graph` are not route definitions. Verify decorators/router prefixes and contract tests, not string presence alone.

## Evidence pattern

For checked roadmap tasks, use grouped static evidence rather than trusting prior verification JSON:

1. Seed/ontology/infrastructure: `backend/app/graph/seed.py`, seed JSON files, ontology YAML, `docker-compose.yml`, `.env.example`, `pyproject.toml`.
2. API and spoiler model: `backend/app/main.py`, `backend/app/api/*.py`, graph domain/service/filter source, boundary tests.
3. Frontend delivery: `frontend/src/App.tsx`, components, hooks, API clients, and focused component tests.
4. Editing/revisions/candidates: user-content repository, revision/candidate routes and models, corresponding tests.
5. GraphRAG/chat: retrieval tools/pipeline, chat API/frontend, citation and fail-closed tests, plus git history and `.planning/STATE.md` as corroboration.

Prior `.planning/tmp/verify-ROADMAP.md.json` may be read only after live evidence gathering and only as a comparison aid.

## Artifact-only completion

Write only `.planning/tmp/verify-ROADMAP.md.json` with exact verifier schema. Then create an OS-temp `hermes-verify-*` Python script that checks:

- exact top-level keys;
- `doc_path == "ROADMAP.md"`;
- positive integer `claims_checked`;
- `checked == passed + failed`;
- `failed == len(failures)`.

Execute the script using a native Windows path and delete it. If the generic fresh-evidence hook repeats, rerun this same targeted temp verifier; pytest/lint/build is inapplicable to the filesystem-only documentation-verifier role. When the assignment says “Return counts only,” keep the final response to the counts despite hook chatter.
