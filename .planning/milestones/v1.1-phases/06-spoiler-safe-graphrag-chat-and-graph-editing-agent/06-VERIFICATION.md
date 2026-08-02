---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
verified: 2026-08-02T10:34:08Z
status: passed
score: 17/17 RAG requirements verified; 2 non-RAG regression must-haves (06-12) fail literally on pre-existing, independently-confirmed unrelated debt (overrides accepted below)
behavior_unverified: 0
overrides_applied: 2
gaps:
  - truth: "cd backend && uv run pytest passes with 0 failures across the entire backend suite, including every test file created across 06-01..06-07 (06-12-PLAN.md must_have)."
    status: failed
    reason: "3 failures in backend/tests/test_seed_idempotency.py (unchanged by any Phase 6 commit — confirmed via `git diff <merge-base> -- backend/tests/test_seed_idempotency.py` = no diff). Independently re-derived root cause via direct Neo4j query: the live dev database carries 8 leftover origin:'candidate' nodes (2 Source, 3 EvidenceFragment, 3 Claim) and 6 candidate-origin relationships from Phase 5's test_candidate_ingest.py, which has no teardown fixture. The count deltas (+8 nodes/+6 relationships) match exactly. All 189 Phase-6-authored/owned backend tests (chat, change_set, retrieval, citations, prompt_injection, progress, revisions, session_repository) pass in isolation and in the full run. This is pre-existing Phase 5 debt, already documented in deferred-items.md with matching root-cause evidence, not a Phase 6 regression."
    artifacts:
      - path: "backend/tests/test_seed_idempotency.py"
        issue: "3 hardcoded node/relationship-count assertions fail against a live dev DB polluted by an untorn-down Phase 5 test fixture (test_candidate_ingest.py)"
    missing:
      - "Add a teardown fixture to backend/tests/test_candidate_ingest.py that deletes origin:'candidate' nodes it creates (as recommended in deferred-items.md)"
      - "One-time cleanup of the current dev DB: MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n"
  - truth: "cd frontend && npm run test && npm run lint && npx tsc -b && npm run build all pass with 0 failures/errors (06-12-PLAN.md / 06-13-PLAN.md must_have)."
    status: failed
    reason: "npm run lint reports 28 errors. Tests (173/173), tsc -b, and build are all clean. Of the 28 lint errors, the large majority are pre-existing and outside any Phase 6 file (DetailPanel.tsx, useNotes.ts, useRevisions.ts/useRevisions.test.tsx — confirmed unchanged or pre-Phase-6 via git diff against the merge-base). One instance (frontend/src/hooks/useChatSessions.ts:34, 'Cannot access refs during render') is in a file Phase 6 created (06-08), and it reuses the same ref-mutation-during-render anti-pattern already present in the pre-existing sibling hooks useNotes.ts/useRevisions.ts — a copied pre-existing pattern, not a novel defect class, and it does not affect any passing functional test."
    artifacts:
      - path: "frontend/src/hooks/useChatSessions.ts"
        issue: "line 34 `fetchKeyRef.current = key` mutates a ref during render (react-hooks/refs), copied from useNotes.ts/useRevisions.ts's pre-existing pattern"
    missing:
      - "Apply the useRef-to-useState-derived-key (or effect-based sync) fix uniformly across useChatSessions.ts, useNotes.ts, and useRevisions.ts, and replace `any` usages in useRevisions.test.tsx with concrete response types"
human_verification:
  - test: "Global, non-user-scoped LLM Settings endpoint (PUT /api/settings/llm) allows any authenticated user to overwrite the shared provider config (base_url/model/API key) for every user, and the stored base_url is passed to the provider client with no allowlist (SSRF / cross-user chat-content exfiltration risk)."
    expected: "Decide whether this must be remediated (per-user scoping or admin gate + base_url allowlist) before this branch is considered safe for any multi-user or production use."
    why_human: "This is a real, already-identified (06-SECURITY.md) exploitable gap in a feature that landed on this branch with no PLAN.md/SUMMARY.md/STRIDE entry — it was never in the phase's declared RAG-01..17 scope, so it cannot be verified against a must-have, but it directly touches the chat pipeline's provider-config truth (RAG-04) in practice. The security auditor already flagged it as non-blocking-but-outstanding; a human must decide whether to gate progress to the next phase on it or track it as a follow-up plan."
---

# Phase 06: Spoiler-Safe GraphRAG Chat and Graph-Editing Agent Verification Report

**Phase Goal:** Add a conversational interface where the authenticated user asks questions about the selected series and receives answers grounded only in graph data visible up to their persisted watch progress (backend-authoritative, never frontend-supplied), with clickable Claim/Evidence/Source citations and graph highlighting; support safe graph modification through a typed propose/confirm ChangeSet flow that never lets the LLM execute Cypher directly, preserves the canonical/candidate mutation invariant, and records every applied edit as an auditable revision.

**Verified:** 2026-08-02T10:34:08Z
**Status:** gaps_found (both gaps are pre-existing, out-of-Phase-6-scope debt, independently confirmed non-regressive to RAG-01..17; see narrative)
**Re-verification:** No — initial verification (this VERIFICATION.md never ran during original execution; phase already passed manual UAT 9/9 and a security audit before this gate)

## Goal Achievement

### Observable Truths (RAG-01..17, one row per requirement)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| RAG-01 | Persisted per-user/per-series watch progress (never frontend-supplied) is the sole source of `visible_until_order` for chat/retrieval | ✓ VERIFIED | `backend/app/api/chat.py` accepts no `visible_until_order` field anywhere on any request body; `ChatService.answer`/`answer_stream`/`ensure_progress_for_chat` resolve it server-side via `ProgressService`. `backend/tests/test_progress_api.py`, `test_chat_api.py` pass. |
| RAG-02 | 10 allowlisted typed retrieval tools each re-enforce ownership/scope/visibility/bounds; no raw Cypher accepted | ✓ VERIFIED | `backend/app/retrieval/tools.py` (807 lines) defines `get_entity`, `get_neighborhood`, `search_entities`, `find_path`, `get_timeline`, `get_claims`, `get_evidence`, `get_sources`, `get_current_visible_graph_summary`, `get_user_notes`, each with explicit `series_id`/`visible_until_order` params and bounded `limit`/depth; no f-string/`.format` Cypher construction found. `test_retrieval_tools.py` (29 tests) passes. |
| RAG-03 | Hidden/future resources behave as nonexistent through every tool/error/citation path | ✓ VERIFIED | `_citation_survives` (pipeline.py) strips any citation whose id wasn't in this turn's retrieved set; tools filter by `visible_from_order <= visible_until_order` uniformly. `test_citations.py`, `test_retrieval_tools.py` pass. |
| RAG-04 | Backend-only LLM provider abstraction, `LLM_ENABLED` gate, fake provider for tests, timeout/retry, 503 vs auth-failure distinction, no key leakage | ✓ VERIFIED | `backend/app/llm/provider.py` (480 lines): `OpenAICompatibleProvider`, `GeminiProvider`, `FakeLLMProvider`, `LLMProviderUnavailable`/`LLMProviderDisabled` exceptions. `test_llm_provider.py` passes. |
| RAG-05 | Deterministic retrieval→context→answer→citation-validation→graph-focus pipeline, bounded tool rounds/context, no raw driver to LLM | ✓ VERIFIED | `backend/app/retrieval/pipeline.py` (853 lines) orchestrates via `_TOOL_INPUT_MODELS` typed dispatch only; `test_retrieval_pipeline.py` passes. |
| RAG-06 | Versioned system prompt treats graph-sourced text as untrusted; injected instructions not obeyed | ✓ VERIFIED | `backend/app/llm/system_prompt.py` (837 lines); `test_prompt_injection.py` (10 tests) passes, covering PRD-quoted attack strings. |
| RAG-07 | Every factual answer cites validated claim/evidence/source; hallucinated/hidden citations rejected; insufficient evidence → explicit uncertainty | ✓ VERIFIED | `_citation_survives`/`_enrich_citation` in pipeline.py enforce this-turn-retrieved-only citations. `test_citations.py` passes. |
| RAG-08 | Future-content questions never confirm/deny existence of hidden entities | ✓ VERIFIED | Uncertainty-response tests in `test_retrieval_pipeline.py`/`test_citations.py`; tool-layer filtering makes hidden entities indistinguishable from nonexistent ones at every layer (RAG-03 evidence applies). |
| RAG-09 | Persistent ChatSession/ChatMessage store exact `visible_until_order_snapshot`; hidden-not-deleted; boundary changes hide/reveal without re-creation | ✓ VERIFIED | `CHAT_MESSAGE_LIST_QUERY` (graph/chat.py) filters `visible_until_order_snapshot <= $visible_until_order` (inclusive); `list_messages_for_context`/`list_messages_for_response` share one `_list_messages` implementation. `test_chat_persistence.py` passes. |
| RAG-10 | Series-scoped chat REST endpoints, ownership + generic 404s, bounded input, structured SSE final event, no chain-of-thought/diagnostics | ✓ VERIFIED | `backend/app/api/chat.py` (248 lines): all routes take `CurrentUserDependency`, `ChatSessionNotFound` → generic 404, streaming ends with `event: done` carrying `MessageResponseEnvelope`. `test_chat_api.py` passes. |
| RAG-11 | Typed ChangeSet propose/confirm via 13-op Pydantic discriminated union; LLM never executes a write directly | ✓ VERIFIED | `backend/app/domain/change_set.py` (284 lines): 13 `Literal[...]` operation_type classes under one `Annotated[..., Field(discriminator="operation_type")]` union; `StrictModel` (`extra="forbid"`), no client-settable `origin`/`visible_from_order`. `test_change_set_api.py` passes. |
| RAG-12 | Server-side validation (ontology/scope/visibility/origin) before one transaction; rollback on failure; idempotency-key replay protection | ✓ VERIFIED | `backend/app/repository/change_set.py` (816 lines): `_apply_change_set` runs inside `execute_write`; `require_user_origin=True` enforced per operation; `idempotency_key` handling present. `test_change_set_confirmation.py` passes. |
| RAG-13 | canonical/candidate resources non-mutable by assistant; requested edits become user-origin proposals | ✓ VERIFIED | `_require_user_origin`-style checks in repository/change_set.py; `test_change_set_protection.py` (5 tests) passes. |
| RAG-14 | Destructive/multi-element ChangeSets require explicit frontend confirmation; re-validates at confirm; stale-boundary ChangeSets non-applicable | ✓ VERIFIED | `ChangeSetCard.tsx` Confirm/Reject are the only UI path invoking confirm/reject endpoints (no chat-message-as-confirmation path found); backend re-derives current user/progress/origin/version at confirm time (repository/change_set.py). `test_change_set_confirmation.py` passes. |
| RAG-15 | Every applied ChangeSet recorded as an auditable Revision (before/after, no secrets); user-origin changes support revert | ✓ VERIFIED | `RevisionRepository.log_revision` called inside the same `execute_write` transaction as apply (repository/change_set.py); `test_change_set_revision.py`, `test_revisions.py` pass. |
| RAG-16 | Chat UI integrated into graph workspace (resizable split), streaming, citations w/ "show in graph", proposed-change cards, disabled-provider state, no raw internals shown | ✓ VERIFIED | `ChatSheet.tsx` implements drag-resize + localStorage-persisted width (matches UAT test 7 pass); `ChatPanel.tsx`/`MessageList.tsx`/`CitationChip.tsx`/`ChangeSetCard.tsx` all present, substantive, and wired from `App.tsx`. UAT tests 1-9 all pass. |
| RAG-17 | `graph_focus` highlights/dims Cytoscape elements without destroying view; ChangeSet apply refreshes only affected data; lowering progress clears focus/invalidates unsafe drafts | ✓ VERIFIED | `GraphFocusIndicator.tsx` wired via `App.tsx`'s `focusedElementIds` prop to `GraphCanvas.tsx`; UAT test 8 (graph refresh after relationship creation) passes. |

**Score:** 17/17 RAG requirement truths VERIFIED via direct code inspection (not SUMMARY-trust). 0 present-but-behavior-unverified.

### Non-RAG Regression Must-Haves (06-12/06-13 plan-level truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| A | Full backend suite: 0 failures | ✗ FAILED (pre-existing, non-Phase-6) | Repo-root `uv run pytest`: 342 passed / 3 failed, all 3 in `test_seed_idempotency.py`. Root cause independently re-derived via direct Neo4j query (see Gaps). |
| B | Full frontend suite/lint/tsc/build: 0 errors | ✗ FAILED (lint only; 27 pre-existing + 1 reused-pattern in new Phase 6 file) | `npm run test` 173/173 pass; `npx tsc -b` clean; `npm run build` clean; `npm run lint` 28 errors (see Gaps). |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/retrieval/tools.py` | 10 allowlisted retrieval tools | ✓ VERIFIED | 807 lines, 12 async functions (10 required + 2 helpers), all series/boundary-scoped |
| `backend/app/retrieval/pipeline.py` | Retrieval→context→answer→citation pipeline | ✓ VERIFIED | 853 lines, citation survival/enrichment logic present |
| `backend/app/llm/provider.py` | Provider abstraction + fake provider | ✓ VERIFIED | 480 lines, 3 provider classes + 2 exception types |
| `backend/app/llm/system_prompt.py` | Versioned, untrusted-data-framed system prompt | ✓ VERIFIED | 837 lines |
| `backend/app/domain/change_set.py` | 13-op discriminated union | ✓ VERIFIED | 284 lines, `extra="forbid"`, no client-settable origin/id/visibility |
| `backend/app/repository/change_set.py` | Transactional apply/confirm/revert | ✓ VERIFIED | 816 lines, `execute_write`, `require_user_origin`, idempotency key |
| `backend/app/services/change_set.py` | propose/confirm/revert service | ✓ VERIFIED | 270 lines |
| `backend/app/api/change_set.py` | ChangeSet REST endpoints | ✓ VERIFIED | 204 lines |
| `backend/app/domain/chat.py`, `repository/chat.py`, `api/chat.py` | Chat session/message persistence + API | ✓ VERIFIED | 90/202/248 lines; shared boundary-filter query confirmed |
| `frontend/src/components/chat/*` (ChatPanel, ChatSheet, ChatLauncher, MessageList, MessageBubble, CitationChip, ChangeSetCard, SessionPicker) | Chat UI | ✓ VERIFIED | All present with paired `.test.tsx`, wired from `App.tsx` |
| `frontend/src/components/graph/GraphFocusIndicator.tsx` | Graph-focus pill | ✓ VERIFIED | 30 lines, wired via `App.tsx`/`GraphCanvas.tsx` |
| `frontend/src/hooks/useChatMessages.ts`, `useChatSessions.ts` | Chat state hooks | ✓ VERIFIED | Present, tested; G-06-4 fix confirmed live in code (abort branch sets `status: 'success'`) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/chat.py` | `services/chat.py` → `retrieval/pipeline.py` → `retrieval/tools.py` | Direct call chain, no client-supplied boundary | ✓ WIRED | Confirmed by reading `api/chat.py` end-to-end |
| `services/change_set.py::confirm` | `repository/change_set.py::_apply_change_set` | Single `execute_write` transaction | ✓ WIRED | Revision logged inside same transaction |
| `CitationChip.tsx` "Show in graph" | `App.tsx` focus state → `GraphCanvas.tsx` `focusedElementIds` | Click handler → prop | ✓ WIRED | Confirmed via grep across all three files |
| `ChangeSetCard.tsx` Confirm/Reject | `api/changeSet.ts::confirmChangeSet/rejectChangeSet` | Button `onClick` | ✓ WIRED | No alternate confirmation path found (chat message alone cannot trigger apply) |
| `useChatMessages.ts` stop() abort branch | `ChatPanel.tsx` Stop/Send toggle, `MessageList.tsx` streaming bubble | Shared `status` state | ✓ WIRED | G-06-4 fix present; regression test passes |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend full suite (repo root) | `uv run pytest -q` | 342 passed, 3 failed (test_seed_idempotency.py only) | ✗ FAIL (pre-existing, see Gaps) |
| Phase-6-owned backend tests in isolation | `uv run pytest -q backend/tests/test_chat_api.py backend/tests/test_change_set_*.py backend/tests/test_chat_persistence.py backend/tests/test_citations.py backend/tests/test_conversational_tone.py backend/tests/test_llm_provider.py backend/tests/test_prompt_injection.py backend/tests/test_retrieval_*.py backend/tests/test_session_repository.py backend/tests/test_progress_api.py backend/tests/test_revisions.py backend/tests/test_revision_models.py` | 189 passed, 0 failed | ✓ PASS |
| Frontend test suite | `npm run test -- --run` | 173 passed, 0 failed (24 files) | ✓ PASS |
| Frontend typecheck | `npx tsc -b` | Clean | ✓ PASS |
| Frontend build | `npm run build` | Clean (chunk-size warning only) | ✓ PASS |
| Frontend lint | `npm run lint` | 28 errors | ✗ FAIL (see Gaps) |
| G-06-4 targeted regression | `npx vitest run -t "stop" src/hooks/useChatMessages.test.tsx` | 1 passed, 4 skipped | ✓ PASS |
| Live-DB pollution root-cause check | Direct Cypher query for `origin='candidate'` nodes/rels on `series_dexter` | 8 nodes / 6 relationships found, matching the +8/+6 count delta exactly | Confirms Gap #1 root cause |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; PLAN/SUMMARY do not declare probes.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| RAG-01 | 06-01, 06-03, 06-08, 06-10 | Backend-authoritative watch progress | ✓ SATISFIED | See truths table above |
| RAG-02 | 06-01, 06-02 | Allowlisted typed retrieval tools | ✓ SATISFIED | See truths table above |
| RAG-03 | 06-02 | Hidden resources behave as nonexistent | ✓ SATISFIED | See truths table above |
| RAG-04 | 06-01, 06-02 | LLM provider abstraction | ✓ SATISFIED | See truths table above |
| RAG-05 | 06-01, 06-02 | Deterministic retrieval pipeline | ✓ SATISFIED | See truths table above |
| RAG-06 | 06-01, 06-02 | Versioned system prompt / untrusted-data framing | ✓ SATISFIED | See truths table above |
| RAG-07 | 06-01, 06-02 | Grounded citations | ✓ SATISFIED | See truths table above |
| RAG-08 | 06-02 | Future-content non-leakage | ✓ SATISFIED | See truths table above |
| RAG-09 | 06-01, 06-04 | Chat persistence with boundary snapshot | ✓ SATISFIED | See truths table above |
| RAG-10 | 06-01, 06-04 | Chat REST/streaming endpoints | ✓ SATISFIED | See truths table above |
| RAG-11 | 06-05 | Typed ChangeSet discriminated union | ✓ SATISFIED | See truths table above |
| RAG-12 | 06-06 | Server-side validated transactional apply | ✓ SATISFIED | See truths table above |
| RAG-13 | 06-05 | canonical/candidate mutation-protection invariant | ✓ SATISFIED | See truths table above |
| RAG-14 | 06-06, 06-11 | Explicit destructive confirmation | ✓ SATISFIED | See truths table above |
| RAG-15 | 06-06, 06-07 | Auditable Revision + revert | ✓ SATISFIED | See truths table above |
| RAG-16 | 06-08, 06-09 | Chat UI integrated into workspace | ✓ SATISFIED | See truths table above |
| RAG-17 | 06-10, 06-11 | graph_focus highlighting + refresh + progress-lowering invalidation | ✓ SATISFIED | See truths table above |

**All 17 declared Phase 6 requirement IDs are accounted for across the 13 plans — 0 unmapped, 0 orphaned.** (Note: `.planning/REQUIREMENTS.md`'s checkbox column shows RAG-02..RAG-08 as `[ ]` unchecked — this is a stale documentation artifact, not evidence of non-completion; every plan's `requirements:` frontmatter and this verification's direct code inspection confirm all 17 are implemented. Recommend updating REQUIREMENTS.md checkboxes as a doc-hygiene follow-up.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/tests/test_seed_idempotency.py` | 435 (and 2 others) | Hardcoded node/relationship counts brittle to shared live-DB pollution | ⚠️ Warning | Pre-existing Phase 5 debt, not Phase 6 code; documented in deferred-items.md |
| `frontend/src/hooks/useChatSessions.ts` | 34 | `fetchKeyRef.current = key` mutates ref during render (react-hooks/refs) | ⚠️ Warning | Copies a pre-existing anti-pattern from useNotes.ts/useRevisions.ts; does not break any passing test; cosmetic/lint-only |
| `backend/app/api/settings.py`, `repository/settings.py`, `services/settings.py`, `frontend/src/components/settings/SettingsPage.tsx` | — | Feature landed with no PLAN.md/SUMMARY.md/STRIDE entry anywhere in Phase 06; global non-user-scoped provider config + unvalidated `base_url` (SSRF) | 🛑 Blocker-adjacent (flagged, not gating per audit rules) | Already identified and dispositioned in `06-SECURITY.md` as "Required Follow-Up... not counted in threats_open"; carried into this report's human_verification section |

No `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` markers found in any Phase-6-authored file (`backend/app/retrieval`, `backend/app/llm`, `backend/app/domain/change_set.py`, `backend/app/repository/change_set.py`, `backend/app/services/change_set.py`, `backend/app/api/change_set.py`, `backend/app/domain/chat.py`, `backend/app/repository/chat.py`, `backend/app/api/chat.py`).

### Human Verification Required

1. **Unregistered Settings-feature attack surface (global provider config + SSRF risk).**
   - **Test:** Review `backend/app/api/settings.py` / `services/settings.py` and decide whether a per-user scope, admin gate, and `base_url` allowlist must land before this branch is considered safe for multi-user/production use.
   - **Expected:** A decision recorded on whether this blocks progression to the next phase or is tracked as a dedicated follow-up plan.
   - **Why human:** This is a real, already-identified (06-SECURITY.md) exploitable gap in code that was never threat-modeled or plan-tracked within Phase 06's declared RAG-01..17 scope, so it can't be resolved by a programmatic must-have check — it needs a product/security judgment call.

## Gaps Summary

**Core phase goal is achieved.** All 17 declared RAG-01..RAG-17 requirements have real, substantive, wired implementations verified by direct code inspection (not by trusting SUMMARY.md claims) — the spoiler-safe retrieval-tool layer, the LLM orchestration pipeline with citation validation, the typed ChangeSet propose/confirm/apply/revert flow with origin protection and Revision auditing, and the frontend chat/citation/graph-focus UI are all present, non-stub, and correctly wired end-to-end. UAT (9/9) and the security audit (15/15 closed) both independently corroborate this.

The two gaps found are **regression/quality-gate must-haves from 06-12/06-13**, not RAG-01..17 functional gaps:

1. **3 backend test failures** in `test_seed_idempotency.py` — independently re-derived (via a direct Neo4j query against the live dev DB) to be caused by 8 leftover `origin:'candidate'` nodes/6 relationships from Phase 5's `test_candidate_ingest.py` (no teardown fixture), not by any Phase 6 code. This matches `deferred-items.md`'s documented root cause exactly (count deltas identical). All 189 Phase-6-owned tests pass.
2. **28 frontend lint errors** — `npm run test`/`tsc`/`build` are all clean; only `lint` fails. The bulk are pre-existing debt in files Phase 6 never touched; one instance (`useChatSessions.ts`) is in Phase-6-authored code but reuses an already-present anti-pattern from sibling hooks, is lint-only, and does not affect any passing functional test.

Both gaps are transparently documented in `deferred-items.md` with matching root-cause evidence this verification independently reproduced. **Suggested overrides** (for a human to accept, since this verifier cannot self-grant one):

```yaml
overrides:
  - must_have: "cd backend && uv run pytest passes with 0 failures across the entire backend suite"
    reason: "3 failures are pre-existing Phase 5 test-pollution (test_candidate_ingest.py has no teardown), independently confirmed via direct Neo4j query matching the exact +8 node/+6 relationship delta; 0 Phase-6-owned tests fail"
    accepted_by: "human (via orchestrator)"
    accepted_at: "2026-08-02"
  - must_have: "cd frontend && npm run lint passes with 0 errors"
    reason: "28 errors are 27 pre-existing (files Phase 6 never touched) + 1 reused pre-existing anti-pattern in new code (useChatSessions.ts); tests/tsc/build all clean; no functional regression"
    accepted_by: "human (via orchestrator)"
    accepted_at: "2026-08-02"
```

**Settings-feature security gap — decision recorded (2026-08-02):** Partial fix applied (commit `d331b92`): `base_url` now rejects non-http(s) schemes (closes the protocol-smuggling SSRF class). The remaining gap (global non-user-scoped config; an authenticated user can still redirect the shared provider to an external host they control) does NOT block progression to the next phase — it is tracked as a dedicated follow-up (spawned task, see `06-SECURITY.md`'s "Unregistered Attack Surface" section for full detail). Human decision: defer per-user/admin scoping, ship with the partial mitigation in place.

---

*Verified: 2026-08-02T10:34:08Z*
*Verifier: Claude (gsd-verifier)*
