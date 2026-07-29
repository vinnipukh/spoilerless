---
phase: 03
slug: user-notes-and-manual-editing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-29
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for the backend-only Phase 3 slice. Overall Phase 3 remains incomplete until the separate frontend worktree verifies UI requirements.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest through `uv` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_openapi_contract.py` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~5 seconds at the 13-test baseline; remeasure after Phase 3 tests land |

---

## Sampling Rate

- **After every task commit:** Run the narrowest affected backend test file plus `git diff --check`.
- **After every plan wave:** Run `uv run pytest -q`.
- **Before `/gsd-verify-work`:** Full suite, live Neo4j setup/idempotency, OpenAPI generation, and backend smoke checks must be green.
- **Max feedback latency:** 30 seconds for targeted tests; live setup verification may take longer but must run at every persistence wave boundary.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | NOTE-03 | T-03-01 | Strict request/response models reject arbitrary fields and expose a stable error envelope | unit/contract | `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_openapi_contract.py` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | NOTE-03 | T-03-02 | Existing graph/series/health OpenAPI declares required positive boundaries and sanitized 404/422/503 responses | contract | `uv run pytest -q backend/tests/test_openapi_contract.py` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | NOTE-01 | T-03-03 | Note CRUD validates same-series visible Character/Claim targets and cannot mutate canonical targets | live integration | `uv run pytest -q backend/tests/test_user_content_api.py -k note` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | NOTE-01 | T-03-04 | Hidden/missing note targets, direct reads, errors, and lists fail closed without count/existence leaks | live integration | `uv run pytest -q backend/tests/test_user_content_api.py -k 'note and (spoiler or hidden or boundary)'` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | NOTE-02 | Custom node CRUD accepts only five locked labels, derives visibility, and blocks canonical/candidate mutation | live integration | `uv run pytest -q backend/tests/test_user_content_api.py -k custom_node` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | NOTE-02 | Custom relationship CRUD accepts only narrative/character predicates and enforces same-series endpoint closure | live integration | `uv run pytest -q backend/tests/test_user_content_api.py -k custom_relationship` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | NOTE-02, NOTE-03 | Visible user content appears in the existing graph while canonical evidence filtering and graph closure remain intact | live integration/regression | `uv run pytest -q backend/tests/test_graph_api.py` | ✅ existing, extend | ⬜ pending |
| 03-04-02 | 04 | 3 | NOTE-01, NOTE-02 | Setup remains idempotent and preserves existing `origin=user` content across reruns | live integration/regression | `uv run pytest -q backend/tests/test_seed_idempotency.py` | ✅ existing, extend | ⬜ pending |
| 03-04-03 | 04 | 3 | NOTE-01, NOTE-02, NOTE-03 | Entire backend contract remains green and no frontend file changed | full regression | `uv run pytest -q && git diff --check` | ✅ baseline | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_user_content_models.py` — strict Pydantic models, enums, immutable/server-owned field rejection.
- [ ] `backend/tests/test_openapi_contract.py` — route inventory, required positive boundary schema, success/error response declarations, and examples.
- [ ] `backend/tests/test_user_content_api.py` — live Neo4j CRUD, ownership, spoiler, same-series, hard-delete, and database-failure cases.
- [ ] Extend existing graph/idempotency fixtures without weakening exact canonical baseline assertions.
- Existing pytest/TestClient/live-Neo4j infrastructure is reused; no new test framework is required.

---

## Manual-Only Verifications

All backend behaviors have automated verification. Frontend visual behavior is explicitly outside this worktree and must be verified separately before overall Phase 3 completion.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verification or Wave 0 dependencies.
- [ ] Sampling continuity: no three consecutive tasks without automated verification.
- [ ] Wave 0 covers all missing test references.
- [ ] No watch-mode flags.
- [ ] Feedback latency remains under 30 seconds for targeted tests.
- [ ] Live Neo4j tests prove fail-closed spoiler behavior and canonical isolation.
- [ ] `nyquist_compliant: true` is set in frontmatter after the planner aligns final task IDs.

**Approval:** pending