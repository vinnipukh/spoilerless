# Onboarding/contributor doc regeneration audit

Use this when a regeneration commit replaced large onboarding or contributor guides and the task is to recover useful information without reverting wholesale.

## Proven workflow

1. Establish the exact owned files and confirm the starting revision/status.
2. For every file, inspect the complete `HEAD^..HEAD` diff and read both `HEAD^:<path>` and the current file. Count diff hunks so the final ledger can prove full coverage.
3. Classify removed material before editing:
   - **obsolete/duplicated** — stale counts, paths, commands, component inventories, historical milestone lists;
   - **useful-current** — working demo flow, contributor workflow, testing hazards, troubleshooting;
   - **useful-normative/future** — architecture invariants and clearly labeled production requirements;
   - **unsafe/inaccurate** — destructive reset advice, unverified pass claims, outdated auth/session/deployment assumptions.
4. Verify retained/restored claims against current source and representative tests. For project intent, use the coding-agent specification and roadmap, but distinguish historical scope, live state, and future direction.
5. Supplement surgically. Do not restore a long pre-regeneration document wholesale. Typical high-value recoveries in this repo:
   - README: product direction plus spec/roadmap links with a current-status warning;
   - Getting Started: current demo walkthrough, runtime Settings precedence, API-only candidate review, proxy troubleshooting;
   - Development: API→service→repository/graph rationale, route/contract synchronization, frontend layers, refresh/reveal invariants, ontology/ChangeSet extension rules;
   - Testing: shared-live-Neo4j hazards, interrupted-run contamination, spoiler/contract checks, React/jsdom/Cytoscape troubleshooting;
   - Deployment: explicit future production gaps for secrets, authorization, backups, CI, observability, rollback.
6. Remove any inherited claim that a suite/build/lint passes unless it was run during the current task. For this repo, broad backend pytest is not doc-only verification: it mutates the configured Neo4j database. Prefer static evidence and clearly say tests were not run.
7. Create the required audit ledger with one row per owned artifact: hunk coverage, classification, exact supplementation, evidence, and intentionally omitted material. End with the required completion marker.
8. Verify:
   - generated marker remains line 1 where present;
   - every relative Markdown link and every newly cited repository path exists;
   - `git diff --check -- <owned tracked docs>` passes;
   - for an ignored/untracked ledger, also run `git diff --no-index --check -- /dev/null <ledger>`;
   - changed tracked names are limited to owned docs; report concurrent unrelated changes without touching them;
   - report final line counts.

## Project-specific evidence anchors

- Product intent: `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md`, `ROADMAP.md`.
- API inventory: `backend/tests/test_frontend_contract_doc.py` (re-extract counts; do not hard-code historical values blindly).
- Shared DB hazard: `backend/tests/conftest.py`, `backend/tests/test_graph_api.py`, `backend/tests/test_settings_api.py`.
- Frontend test/runtime patterns: `frontend/vite.config.ts`, `frontend/src/test/setup.ts`, `frontend/src/App.test.tsx`, `frontend/src/components/graph/GraphCanvas.test.tsx`.
- Deployment facts: `docker-compose.yml`, `frontend/package.json`, `frontend/package-lock.json`, `backend/app/main.py`, `.env.example`.

## Pitfalls

- A generated-document marker does not justify discarding accurate user-authored operational knowledge; preserve it as a concise supplement.
- A roadmap can be useful for intent while stale for status. Link it with an explicit “verify against live source/tests” qualification.
- `git status` can change during multi-agent work. Compare against the initial status and edit only assigned files; do not clean up or incorporate concurrent changes.
- `.planning/tmp/` may be ignored, so a normal `git diff --check` does not validate its ledger. Use the no-index check above.
