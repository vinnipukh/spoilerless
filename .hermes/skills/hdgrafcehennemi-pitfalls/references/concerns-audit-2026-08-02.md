# HD Graf Cehennemi concerns-audit findings (2026-08-02)

Use this reference when refreshing `.planning/codebase/CONCERNS.md` or planning security/operations hardening. Re-verify line numbers and behavior against current source before relying on these findings.

## Mandatory audit shape

Investigate all six categories: Technical Debt, Security, Performance, Maintainability, Compatibility, and Missing Features. For each concern record files/lines, a short code excerpt, problem, practical risk, severity, scope, fix direction, and effort. Distinguish local-prototype limitations from internet-facing production severity.

## High-priority verified findings

### Candidate routes lack authentication and persisted-boundary enforcement

- `backend/app/api/candidates.py` routes do not accept `CurrentUserDependency`.
- List accepts optional `visible_until_order`; direct get has no boundary.
- Ingest/edit/approve/reject are callable without a session; `backend/tests/test_candidate_review.py` exercises them unauthenticated.
- `backend/app/graph/candidates.py` returns claim/evidence/source fields without per-hop spoiler predicates.
- Hardening direction: reviewer/admin authorization on every route, server-resolved progress, per-hop visibility, server-derived episode visibility, and unauth/foreign/hidden-equals-missing tests.

### Revision routes lack authentication and trust a caller boundary

- `backend/app/api/revisions.py` list/get/revert routes do not accept `CurrentUserDependency` or resolve progress through `ProgressService`.
- Revert performs writes from only series ID, revision ID, and a caller-supplied positive boundary.
- Revision snapshots contain user content.
- Hardening direction: authenticated user, server-resolved progress, ownership scoping enforced inside the write transaction, and direct security contract tests.

### Global LLM settings make every authenticated user an administrator

- `backend/app/api/settings.py` requires authentication but has no role/owner check.
- One shared `:AppSetting {key:'llm'}` controls provider, base URL, model, enabled state, and API key.
- `backend/app/domain/settings.py` permits arbitrary HTTP(S) hosts, including local endpoints by design.
- A user can redirect subsequent provider calls—and the shared credential—to another host.
- The full key is stored as plaintext JSON in Neo4j (`backend/app/repository/settings.py`); response masking is not encryption at rest.
- Hardening direction: admin-only or deployment-only settings, explicit local-provider mode, hosted allowlists/private-address blocking, per-user credentials if multi-user, and external/encrypted secret storage.

## Performance and scaling checks

- `GraphService.fetch_graph()` materializes seven full visible collections concurrently; graph queries have no limit/cursor and Cytoscape lays out the complete response. Severity is low for the 3-episode prototype and medium when content expands.
- `get_llm_provider()` constructs providers whose `httpx.AsyncClient` has no explicit `aclose()` lifecycle. Prefer lifespan-owned clients or a yielding dependency that closes request-owned clients.
- Chat generation concurrency is a module-level dictionary. It is effective only in one process and is not general rate limiting; use a shared TTL lease for workers/replicas.

## Technical debt and maintainability checks

- Root `main.py` is a PyCharm sample; `frontend/README.md` is Vite template prose; root `ROADMAP.md` completion state is stale relative to executable features.
- `SettingsRepository` claims an `AppSetting.key` uniqueness constraint exists, while executable DDL in `backend/app/graph/seed.py` does not create one.
- Schema evolution is bootstrap/seed-driven; there is no versioned migration ledger.
- Integration tests default to the same live Neo4j database as local application use. Preserve the existing save/restore and event-loop hygiene, but prefer an ephemeral test database.
- Production modules over roughly 750 lines include retrieval pipeline/tools, ChangeSet and user-content repositories, `DetailPanel.tsx`, and the system-prompt file. Do not rewrite user-owned prompt prose while decomposing executable composition/guards.
- Frontend lint baseline was 28 errors/0 warnings on 2026-08-02. Re-run before citing; fix behavior-affecting hook/ref issues first.

## Compatibility and missing operations

- Enforce the documented Node floor with `package.json` engines and frozen installs; Python requires 3.13+.
- Local Compose is development-specific: exposed Neo4j ports, bind mounts, local auth, and a broad `neo4j:2026-community` image tag.
- No tracked CI workflow, coverage threshold, browser E2E framework, production backend/frontend images, migration rollout, monitoring stack, or automated Neo4j backup/restore path was present.
- No general request limiter exists; the chat concurrency slot protects only one expensive operation class.
- Expired/revoked sessions are rejected at read time but have no scheduled retention cleanup.

## Mapping verification recipe

1. Read the mapper agent, six-category methodology, project README/architecture/state, and existing architecture/testing maps in the exact requested order.
2. Verify documentation claims against executable routes, dependencies, DDL, tests, and tracked-file inventory.
3. Do not read live environment or credential files; committed examples are safe.
4. Write only the scoped map document.
5. Verify file existence, all six headings, `git diff --check`, and line count.
6. Return only the standard `## Mapping Complete` confirmation.