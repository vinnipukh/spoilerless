---
phase: 06
slug: spoiler-safe-graphrag-chat-and-graph-editing-agent
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-31
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: `pytest>=9.1.1` + `pytest-asyncio>=1.4.0` against a live local Neo4j (no DB mocking layer exists in this repo). Frontend: `vitest>=4.1.10` + `@testing-library/react>=16.3.2`. |
| **Config file** | Backend: no dedicated `pytest.ini`; `backend/tests/conftest.py` is the shared fixture/path-setup file. Frontend: `npm run test` (vitest), global setup in `frontend/src/test/setup.ts`. |
| **Quick run command** | Backend: `cd backend && uv run pytest tests/test_<new_file>.py -x` · Frontend: `cd frontend && npm run test -- <ComponentName>` |
| **Full suite command** | Backend: `cd backend && uv run pytest` · Frontend: `cd frontend && npm run test && npm run lint && npx tsc -b && npm run build` (matches PRD §17's exact required run list) |
| **Estimated runtime** | ~90s backend full suite, ~60s frontend full suite (extrapolated from existing phase sizes; will grow with this phase's ~13 new test files) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched test file(s)
- **After every plan wave:** Run the full backend suite (`uv run pytest`) AND the full frontend suite (`npm run test && npm run lint && npx tsc -b && npm run build`)
- **Before `/gsd-verify-work`:** Full suite must be green, **plus** the two closed-inventory contract tests (`test_openapi_contract.py`, `test_frontend_contract_doc.py`) specifically re-verified — they are the tests most likely to be silently broken by a route added in an earlier wave and only caught at phase-end otherwise
- **Max feedback latency:** 90 seconds (one full backend suite run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-xx-xx | TBD | TBD | RAG-01 | T-06-progress | Frontend cannot raise `visible_until_order` via request; backend resolves persisted progress server-side | integration | `pytest backend/tests/test_progress_api.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-02/RAG-03 | T-06-retrieval | Hidden node/relationship/claim/evidence/source behaves as nonexistent through every retrieval tool | integration | `pytest backend/tests/test_retrieval_tools.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-04 | T-06-provider | Fake provider used in tests; disabled-provider error; provider timeout maps to 503 not 401 | unit+integration | `pytest backend/tests/test_llm_provider.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-05 | T-06-pipeline | Bounded tool rounds; context size bounding; entity/claim/evidence deduplication | unit | `pytest backend/tests/test_retrieval_pipeline.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-06 | T-06-injection | Malicious Note/Evidence text (PRD's 5 exact strings) not obeyed as instructions | integration | `pytest backend/tests/test_prompt_injection.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-07/RAG-08 | T-06-citations | Hallucinated citation rejected; insufficient-evidence answer; future-content question never confirms/denies | integration | `pytest backend/tests/test_citations.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-09 | T-06-chat-history | Hidden higher-boundary history excluded from API/previews/LLM memory after progress decrease (Episode-3-then-Episode-1 regression) | integration | `pytest backend/tests/test_chat_persistence.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-10 | T-06-chat-api | Session CRUD ownership (404 on cross-user/cross-series), streaming final event, disconnect cleanup | integration | `pytest backend/tests/test_chat_api.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-11/RAG-12 | T-06-changeset-apply | Preview makes no DB change; confirm applies one transaction; idempotent replay; rollback on failure | integration | `pytest backend/tests/test_change_set_api.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-13 | T-06-canonical-protect | Canonical/candidate mutation rejected; note/override proposal offered instead | integration | `pytest backend/tests/test_change_set_protection.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-14 | T-06-confirmation | Stale ChangeSet rejected after progress decrease; chat message alone is not confirmation | integration | `pytest backend/tests/test_change_set_confirmation.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-15 | T-06-audit | Revision recorded on apply; safe revert; revert conflict handling | integration | `pytest backend/tests/test_change_set_revision.py -x` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-16 | T-06-frontend-chat | Chat open/close, streaming, retry, disabled-provider state, citation click, ChangeSet confirm/reject UI | component | `npm run test -- ChatPanel` | ❌ Wave 0 | ⬜ pending |
| 06-xx-xx | TBD | TBD | RAG-17 | T-06-graph-sync | graph_focus highlight/dim/clear; ChangeSet apply refreshes only affected data; progress decrease clears focus on hidden resources | component | `npm run test -- GraphCanvas` (extends existing `GraphCanvas.test.tsx`) | 🟡 file exists, new cases needed | ⬜ pending |

*Task IDs/Plan/Wave columns are TBD — this table is seeded pre-planning from RESEARCH.md's Phase Requirements → Test Map; the planner fills in real task/plan/wave IDs when PLAN.md files are written. Threat Ref IDs (T-06-*) are placeholders for the planner's `<threat_model>` block (security contribution hook, ASVS L1, block on high) to assign real IDs against.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_progress_api.py` — stubs for RAG-01
- [ ] `backend/tests/test_retrieval_tools.py` — stubs for RAG-02, RAG-03
- [ ] `backend/tests/test_llm_provider.py` — stubs for RAG-04, includes new shared `FakeLLMProvider` test double
- [ ] `backend/tests/test_retrieval_pipeline.py` — stubs for RAG-05
- [ ] `backend/tests/test_prompt_injection.py` — stubs for RAG-06, must use the PRD's exact 5 malicious strings verbatim
- [ ] `backend/tests/test_citations.py` — stubs for RAG-07, RAG-08
- [ ] `backend/tests/test_chat_persistence.py` — stubs for RAG-09 (the critical Episode-3-then-Episode-1 regression scenario belongs here)
- [ ] `backend/tests/test_chat_api.py` — stubs for RAG-10
- [ ] `backend/tests/test_change_set_api.py`, `test_change_set_protection.py`, `test_change_set_confirmation.py`, `test_change_set_revision.py` — stubs for RAG-11..RAG-15
- [ ] `frontend/src/components/chat/ChatPanel.test.tsx` (+ sibling component tests) — stubs for RAG-16
- [ ] `frontend/src/test/fixtures/chatFixtures.ts` — new shared fixture module, mirrors `frontend/src/test/fixtures/graphResponse.ts`
- [ ] Extend `frontend/src/components/graph/GraphCanvas.test.tsx` — new cases for RAG-17
- [ ] **Mandatory Wave 0 blocker (not a stub, a standing task):** `backend/tests/test_openapi_contract.py` and `backend/tests/test_frontend_contract_doc.py` (closed-inventory assertions over exact path/operation counts) must be updated in the *same task/commit* as each new route is added, in every wave that adds routes — not deferred to a cleanup task, or CI breaks for every subsequent task in the phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full conversational UAT flow (login → chat → citation click → "show in graph" → ChangeSet propose/confirm/apply → progress-decrease hides history) | RAG-01, RAG-09, RAG-16, RAG-17 | End-to-end browser flow spanning auth, streaming UI, and live graph re-render — not practically assertable as a single automated test given the streaming + confirmation-modal + graph-highlight interaction chain | Execute the PRD §18 Manual Acceptance Matrix (20 items) in a live browser session per `06-PRD-SOURCE.md` §18, after automated suites are green |
| LLM answer quality / groundedness on real provider output | RAG-07 | Automated tests use the deterministic fake provider (`FakeLLMProvider`) for correctness of the plumbing; actual real-provider answer quality is a human judgment call PRD explicitly scopes out of automated CI | Run the PRD §15 worked-example Turkish conversations against a real configured provider once implementation is complete; confirm citation-grounding and language-following qualitatively |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
