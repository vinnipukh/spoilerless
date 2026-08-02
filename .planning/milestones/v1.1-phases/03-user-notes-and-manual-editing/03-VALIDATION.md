---
phase: 03
slug: user-notes-and-manual-editing
status: backend-verified-overall-pending
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-29
updated: 2026-07-29
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for the backend-only Phase 3 slice. Overall Phase 3 remains incomplete until the separate frontend worktree verifies UI requirements.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest through `uv` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_user_content_repository.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py` |
| **Full suite command** | `uv run pytest -q` |
| **Live dependencies** | Local Neo4j credentials from `backend/tests/conftest.py`; user fixtures clean only `origin=user` |
| **Baseline verified while planning** | `13 passed, 1 warning in 2.97s` on branch `backend-work` |

---

## Sampling Rate

- **After every task:** run that task's narrowest `<automated>` command plus `git diff --check`.
- **After every plan wave:** run `uv run pytest -q`.
- **After persistence waves:** run `uv run python -m backend.app.graph.setup` and the setup/idempotency tests.
- **Before `/gsd-verify-work`:** run all targeted files, full suite, setup twice, OpenAPI assertions, `git diff --check`, and both diff/status assertions that no `frontend/` path changed.
- **Max feedback latency:** 30 seconds for targeted tests; live setup may exceed this but cannot be skipped.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Wave-0 Dependency | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------------|--------|
| 03-01-01 | 01 | 1 | NOTE-01, NOTE-02, NOTE-03 | T-03-01 | Strict explicit models reject spoofed server fields, arbitrary labels/predicates/properties, null/empty PATCH, and ontology drift | unit/schema | `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_graph_api.py -k 'model or dangling or ontology'` | creates `test_user_content_models.py` | ✅ green (24 passed, 9 deselected) |
| 03-01-02 | 01 | 1 | NOTE-03 | T-03-02 | Stable error envelope sanitizes validation/database failures; reusable OpenAPI and live-integration homes exist without skips; degraded startup/docs remain executable | unit/contract | `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_openapi_contract.py backend/tests/test_graph_api.py -k 'error or validation or model or dangling or degraded'` | creates `test_openapi_contract.py` and `test_user_content_api.py` fixtures | ✅ green (31 passed, 6 deselected) |
| 03-02-01 | 02 | 2 | NOTE-01, NOTE-02 | T-03-03 | Fake session/transaction tests prove database-scoped execute_write delegation, retry-stable command IDs/timestamps, parameter forwarding/static query selection, and pre-query unsafe-input rejection; live ontology/schema idempotency remains covered | unit/repository + live integration | `uv run pytest -q backend/tests/test_user_content_repository.py && uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_seed_idempotency.py -k 'ontology or constraint or idempotent'` | creates focused repository fake tests and consumes Wave-0 model fixtures | ✅ green (6 repository; 4 selected live/model) |
| 03-02-02 | 02 | 2 | NOTE-01 | T-03-04 | Note CRUD validates exactly one same-series Character/Claim target and hidden/missing reads/lists/errors fail closed | live integration | `uv run pytest -q backend/tests/test_user_content_api.py -k 'note'` | populates Wave-0 API file | ✅ green (2 selected; 33 full API) |
| 03-02-03 | 02 | 2 | NOTE-02, NOTE-03 | T-03-05 | Five node types and participation+character relationships enforce ownership, endpoint closure, derived visibility, hard delete, and typed routes | live integration/contract | `uv run pytest -q backend/tests/test_user_content_api.py backend/tests/test_openapi_contract.py -k 'custom_node or custom_relationship or user_route or health or series'` | completes CRUD/OpenAPI portions of Wave-0 files | ✅ green (31 passed, 8 deselected) |
| 03-03-01 | 03 | 3 | NOTE-02, NOTE-03 | T-03-06 | Explicitly disjoint canonical/candidate evidence and user-edge branches preserve provenance and graph closure; an evidence-bearing user-authored fixture is GraphEdge-only with zero claim/source/evidence presence | live integration/regression | `uv run pytest -q backend/tests/test_graph_api.py backend/tests/test_openapi_contract.py` | extends existing graph test + completes OpenAPI file | ✅ green (18 passed) |
| 03-03-02 | 03 | 3 | NOTE-01, NOTE-02, NOTE-03 | T-03-07 | Setup preserves origin=user content and exact canonical layer; executable doc test compares the exact 18 operation tuples and exact 11-template set with OpenAPI and verifies origin/boundary/error/compatibility/non-goal/pending-phase text | full integration/contract | `uv run pytest -q backend/tests/test_seed_idempotency.py backend/tests/test_user_content_api.py backend/tests/test_graph_api.py backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py` | creates `test_frontend_contract_doc.py` and extends existing setup test | ✅ green (58 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_user_content_models.py` — strict Pydantic contracts, enums, immutable/server-owned rejection, ontology drift, graph compatibility.
- [x] `backend/tests/test_openapi_contract.py` — exact 18 operation tuples and 11 templates, required positive boundaries, typed success/error/health schemas, examples, delete no-body.
- [x] `backend/tests/test_user_content_api.py` — user-only cleanup and live Neo4j CRUD/ownership/spoiler/hard-delete/database-failure acceptance.
- [x] `backend/tests/test_user_content_repository.py` — fake database-scoped transaction/retry/parameter/static-query safety coverage.
- [x] `backend/tests/test_frontend_contract_doc.py` — executable document/OpenAPI comparison plus origin, boundary/error, compatibility, non-goal, and pending-status assertions.
- [x] Existing `backend/tests/test_graph_api.py` extended while canonical baseline counts remain independent of temporary user data.
- [x] Existing `backend/tests/test_seed_idempotency.py` snapshots canonical and user layers separately.
- Existing pytest/TestClient/live-Neo4j infrastructure is reused; no new test framework, watch mode, skipped placeholder, or ORM/schema-push step is permitted.

---

## Threat References

- **T-03-01 — spoofed/unsafe public fields:** strict models, finite enums, ontology drift tests, length limits.
- **T-03-02 — validation/database disclosure:** shared envelope, sanitized handlers, no rejected values/Cypher/credentials.
- **T-03-03 — transaction/setup tampering:** one managed write callback, stable pre-retry IDs/timestamps, idempotent schema, no user cleanup.
- **T-03-04 — note visibility/existence leak:** target-rematching Cypher, persisted boundary, hidden=missing 404, no counts.
- **T-03-05 — canonical mutation/injection:** origin+namespace+series+representation matches, static query selection, explicit SET, dependency 409.
- **T-03-06 — evidence/closure bypass:** separate exact user-authored projection, mandatory canonical provenance, endpoint visibility, Pydantic closure.
- **T-03-07 — setup overwrite/resurrection and scope drift:** canonical/user snapshots, double setup, deleted-user check, no-frontend and no-out-of-scope source assertions.

All applicable spoofing, tampering, information-disclosure, and denial-of-service risks have a named code/test mitigation in each PLAN.md `<threat_model>`. Security enforcement is ASVS Level 1 and any HIGH finding blocks execution completion.

---

## Final Verification Sequence

```bash
uv run pytest -q backend/tests/test_user_content_models.py
uv run pytest -q backend/tests/test_user_content_repository.py
uv run pytest -q backend/tests/test_openapi_contract.py backend/tests/test_frontend_contract_doc.py
uv run pytest -q backend/tests/test_user_content_api.py
uv run pytest -q backend/tests/test_graph_api.py backend/tests/test_seed_idempotency.py
uv run pytest -q
uv run python -m backend.app.graph.setup
uv run python -m backend.app.graph.setup
uv run python -c "from backend.app.main import app; schema=app.openapi(); expected={'/health','/api/series','/api/series/{series_id}','/api/series/{series_id}/episodes','/api/series/{series_id}/graph','/api/series/{series_id}/notes','/api/series/{series_id}/notes/{note_id}','/api/series/{series_id}/custom-nodes','/api/series/{series_id}/custom-nodes/{node_id}','/api/series/{series_id}/custom-relationships','/api/series/{series_id}/custom-relationships/{relationship_id}'}; allowed={'get','put','post','delete','options','head','patch','trace'}; assert set(schema['paths']) == expected; assert sum(method in allowed for item in schema['paths'].values() for method in item) == 18; print('openapi-ok')"
git diff --check
test -z "$(git diff --name-only -- frontend/)"
test -z "$(git status --short -- frontend/)"
```

---

## Manual-Only Verifications

All backend behavior has automated verification. Frontend rendering, distinct visual treatment, and end-to-end UI CRUD are explicitly outside this worktree and must be verified in `frontend-work` before overall Phase 3 completion.

---

## Validation Sign-Off

- [x] Every final task has an `<automated>` command.
- [x] Sampling continuity has no uncovered task.
- [x] Every missing test reference is created by its owning task and populated before that task's acceptance criteria are evaluated.
- [x] No watch-mode flags or skipped placeholders are planned.
- [x] Repository fakes cover managed-write delegation/retries/parameter safety; live tests cover fail-closed spoiler behavior, explicitly disjoint provenance branches, canonical isolation, hard deletion, setup preservation, and database failures.
- [x] OpenAPI generation/assertions, executable handoff-document checks, setup/idempotency, full suite, `git diff --check`, and no-frontend source assertions are mandatory.
- [x] `nyquist_compliant: true` reflects aligned final task IDs and continuous automated coverage.

## Executed Evidence — Plan 03-03

- Task 03-03-01 exact command: **18 passed, 1 warning**.
- Task 03-03-02 exact command: **58 passed, 1 warning**.
- Final focused commands: models **23 passed**; OpenAPI/document **10 passed**; user-content API **33 passed**; graph/setup **15 passed**.
- Full suite: **87 passed, 1 unchanged third-party warning**.
- Setup executed twice: **41 canonical nodes, 26 canonical relationships** each time.
- Generated OpenAPI: **18 operations, 11 templates**, required positive integer graph boundary (`openapi-ok`).
- OS-temp ad-hoc endpoint-rematch probe: `hermes-ad-hoc-endpoint-rematch-ok`; file removed.
- Diff, frontend, and prohibited-scope checks: clean.

**Approval:** backend Plans 03-01 through 03-03 complete and verified; Phase 2, frontend acceptance, and overall Phase 03 remain pending.
