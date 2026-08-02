# Phase 06 — Manual Acceptance Matrix

**Source:** `06-PRD-SOURCE.md` section 18 (verbatim items below) and section 22 (Final Report).

**Status:** ⏳ **PENDING HUMAN VERIFICATION** — the 20 live-browser items below must be executed
in a real browser session against the running local stack (backend + frontend). This file was
prepared by the 06-12 executor with automated-evidence notes per item; the pass/fail marks are
the human gate's job (GSD `checkpoint:human-verify`, blocking).

**Preconditions for the live session:**
1. Neo4j running (`docker compose up -d neo4j`), backend seeded and started (`cd backend && uv run uvicorn app.main:app --reload`).
2. Frontend started (`cd frontend && npm run dev`).
3. LLM provider configured in root `.env` (`LLM_ENABLED=true`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) **if a real provider is available**. If no real provider is available, items that need qualitative answer-quality checks must be marked with the fake-provider substitution noted as a known limitation — never skipped silently.
4. Google OAuth configured (`GOOGLE_CLIENT_ID` backend, `VITE_GOOGLE_CLIENT_ID` frontend).

---

## Checklist (PRD §18 — 20 items)

| # | Item (verbatim) | Automated evidence (where applicable) | Pass/Fail | Notes |
|---|---|---|---|---|
| 1 | Login succeeds. | `backend/tests/test_auth_api.py` (session-cookie flow) | ⬜ | Live browser: sign in with Google |
| 2 | Series and progress are restored. | `useWatchProgress` backend-authoritative hydration tests (06-10, 16 tests); `backend/tests/test_progress_api.py` | ⬜ | Live: reload page, confirm progress persists |
| 3 | Chat session can be created. | `backend/tests/test_chat_api.py`; `ChatPanel.test.tsx` session picker | ⬜ | Live: open Chat, create session |
| 4 | User asks a visible-content question. | — | ⬜ | Live: needs real provider |
| 5 | Answer streams. | `ChatPanel`/streaming tests (06-09); SSE handler tests | ⬜ | Live: verify token-by-token rendering |
| 6 | Citations open relevant evidence. | `CitationChip.test.tsx`; App-level citation wiring tests (06-10) | ⬜ | Live: click chip body → Inspector |
| 7 | "Show in graph" highlights relevant nodes/edges. | `App.test.tsx` citation focus tests (06-10/06-11); `GraphCanvas.test.tsx` focusedElementIds | ⬜ | Live: expect `.selected-dominant` + "Highlighting N from chat" |
| 8 | Future-content question returns a safe insufficient-information response. | `backend/tests/test_prompt_injection.py` / retrieval boundary tests | ⬜ | Live: needs real provider |
| 9 | Episode 3 chat response is hidden after returning to Episode 1. | `backend/tests/test_chat_api.py` (visible_until_order_snapshot filtering) | ⬜ | Live: lower progress, verify message hidden |
| 10 | Hidden response does not enter later model context. | history-loading boundary tests (snapshot <= boundary) | ⬜ | Live: hard to observe directly; backend test is the evidence |
| 11 | User requests a valid user-origin node creation. | `backend/tests/test_change_set_api.py` Stage 1 propose; `ChangeSetCard.test.tsx` | ⬜ | Live: ask chat to create a note/node |
| 12 | Preview appears without changing graph. | `ChangeSetCard.test.tsx` preview rendering; propose does not write (transaction tests) | ⬜ | Live: confirm graph unchanged before confirm |
| 13 | Reject leaves graph unchanged. | `ChangeSetCard.test.tsx` Reject → terminal badge; backend reject is no-op write | ⬜ | Live |
| 14 | Confirm applies change. | `App.test.tsx` apply test (confirmChangeSet called once); `backend/tests/test_change_set_api.py` Stage 2 | ⬜ | Live |
| 15 | Graph updates. | `App.test.tsx` incremental-refresh test (refetch, no relayout, focus) | ⬜ | Live: newly-created element appears + focused |
| 16 | Refresh preserves the change and chat. | persistence tests (ChangeSet applied_at/revision_id; chat session survives reload) | ⬜ | Live: browser refresh |
| 17 | Canonical deletion is refused. | `backend/tests/test_change_set_api.py` protection tests; `ChangeSetCard.test.tsx` Protected badge | ⬜ | Live: try to delete canonical node via chat |
| 18 | Logout removes access to chats. | `backend/tests/test_auth_api.py` (logout clears session) | ⬜ | Live |
| 19 | Backend-off and LLM-provider-off states are understandable. | `ChatPanel` disabled/provider-unavailable banner tests (06-09) | ⬜ | Live: stop backend / unset LLM_ENABLED |
| 20 | No secret or token appears in browser storage or logs. | secret scan in 06-12 docs task (no key-shaped values in docs); session cookie is HttpOnly | ⬜ | Live: DevTools → Application/Storage + network logs |

---

## Final Report (PRD §22)

Filled from automated evidence by the 06-12 plan; the two PENDING lines (19, 22) are the
human gate's verdict.

### 1. Architecture implemented
Spoiler-safe GraphRAG-lite chat + graph-editing agent: persisted watch progress
(`UserSeriesProgress`), ten allowlisted retrieval tools over visibility-gated Cypher,
streamed grounded answers with validated citations, `ChatSession`/`ChatMessage` persistence
with hide-not-delete spoiler filtering, and a typed two-stage `ChangeSet`
propose → confirm/apply (plus revert) graph-editing flow with canonical/candidate
protection. Full diagram and invariants: `docs/ARCHITECTURE.md` §4.8–4.10.

### 2. Files changed
See the phase's per-plan SUMMARY.md files (06-01..06-12) for the authoritative per-plan
file lists. High-level: `backend/app/` (llm/, retrieval/, graph/chat.py + progress.py +
change_set.py, api/, domain/, repository/, services/, core/config.py), `backend/tests/`
(8+ new test files), `frontend/src/` (api/, hooks/, components/chat/ incl. ChatPanel,
MessageList, MessageBubble, CitationChip, ChangeSetCard, GraphFocusIndicator,
components/detail/DetailPanel, App.tsx), `docs/` (API, ARCHITECTURE, CONFIGURATION,
GETTING-STARTED, frontend-api-contract), `.env.example`, `README.md`.

### 3. Dependencies added
Backend: none beyond the existing stack (chat uses `httpx`/stdlib SSE; no new third-party
runtime deps — LLM calls use `httpx` against OpenAI-compatible endpoints). Frontend: none
new; chat UI built on existing shadcn/ui + lucide-react + react-router primitives.

### 4. Environment variables added
Eleven `LLM_*` vars (see `docs/CONFIGURATION.md`): `LLM_ENABLED`, `LLM_PROVIDER`,
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`,
`LLM_TEMPERATURE`, `LLM_MAX_TOOL_ROUNDS`, `LLM_MAX_CONTEXT_ITEMS`, `LLM_MAX_CONTEXT_CHARACTERS`.
All default to safe values; `.env.example` ships with empty key/base-url.

### 5. Final API contracts
Locked in `docs/frontend-api-contract.md` and enforced by
`backend/tests/test_openapi_contract.py` + `test_frontend_contract_doc.py` (10/10 pass).
New route families: `progress.py` (GET/POST `/api/series/{id}/progress`), `chat.py`
(sessions CRUD + messages + SSE stream), `change_set.py` (propose/confirm/reject/revert).

### 6. LLM provider abstraction
`backend/app/llm/provider.py` — `LLMProvider` protocol + `OpenAICompatibleProvider`
(httpx-based, async, temperature/timeout/token caps from settings). `LLM_ENABLED=false`
returns typed `LLM_DISABLED` errors; unreachable provider returns `LLM_PROVIDER_UNAVAILABLE`.
Tests use `FakeLLMProvider` exclusively (no live API in CI).

### 7. Retrieval tools
Ten allowlisted tools in `backend/app/retrieval/tools.py` (get_entity, get_neighborhood,
search_entities, find_path, get_timeline, get_claims, get_evidence, fetch_episode_codes,
+ 2) — every tool runs visibility-gated Cypher (server-side templates, `$parameter` bindings,
`visible_from_order <= boundary` on every hop) and result bounds. No text-to-Cypher surface.
See `docs/ARCHITECTURE.md` §4.8.

### 8. Spoiler enforcement points
Backend-only filtering: graph read path (`graph.py`), every retrieval tool, chat-history
loading (`visible_until_order_snapshot <= boundary`), and `graph_focus`/candidate visibility.
The frontend never receives data to hide (core invariant, `docs/ARCHITECTURE.md` §4.10).

### 9. Chat-history spoiler behavior
Messages carry `visible_until_order_snapshot`; history/session-preview loading filters
below the current boundary. Lowering progress hides previously generated future-boundary
messages WITHOUT deleting them (they reappear if progress advances again).

### 10. System-prompt version and injection defenses
`SYSTEM_PROMPT_VERSION = "v1"` (`backend/app/llm/system_prompt.py`). Retrieval content is
wrapped in strict delimiters with explicit instruction-ignore language; graph content
treated as untrusted prompt data; `test_prompt_injection.py` asserts injected instructions
stay contained. Text2Cypher does not exist, so prompt-injection cannot escalate to query
execution.

### 11. Citation model
Every answer is grounded: the pipeline records the tool calls that produced the answer and
returns validated citations (claim/evidence/source + locator + excerpt). Frontend renders
`CitationChip`s; chips carry `related_node_ids`/`related_edge_ids` for "Show in graph"
focusing; the frontend validates citations against the fetched graph before applying focus.

### 12. ChangeSet operation model
Typed operation union (`create_node`, `update_node`, `delete_node`, `create_relationship`,
`update_relationship`, `delete_relationship`, `create_claim`, `update_claim`, `create_note`,
`update_note`, `delete_note`, `attach_evidence`). Two-stage: propose (Stage 1, no write) →
confirm (Stage 2, single transaction + `Revision` audit row) → revert (Stage 3). Statuses:
draft → awaiting_confirmation → applied/rejected/failed/reverted.

### 13. Canonical/candidate protection
ChangeSet validation refuses mutation operations targeting `origin: canonical` or
`origin: candidate` content; the pipeline substitutes a confirmable `create_note` annotation
and the frontend renders the "Protected" badge (Lock, `--destructive` accent line) with
honest copy that never claims the canonical record changed. Deletion of canonical nodes is
refused server-side.

### 14. Transaction and revision behavior
Confirm/apply runs in a single Neo4j transaction (mutation + `Revision` log row created in
the same tx); revert creates a compensating revision. Append-only `Revision` series with
`before`/`after` JSON snapshots (see `neo4j-data-patterns` audit-log pattern). Revert of a
deleted resource requires the `REFERS_TO` chain.

### 15. Frontend chat UX
DetailPanel Chat mode: session picker, message bubbles, streaming text, citation chips,
retry, disabled-provider/transient-503 banners, ChangeSetCard preview with Confirm/Reject
controls (the ONLY UI path into the confirm/reject endpoints), terminal status badges,
stale-proposal banner. Panel collapses; graph stays interactive.

### 16. Graph synchronization
Citation "Show in graph" → `GraphCanvas focusedElementIds` (`.selected-dominant`/`.faded` +
gentle `cy.fit(focused, 48)`); ChangeSet apply → incremental `useGraph.refresh()` (no
loading flash, no destructive relayout) + focus on the newly-created resource; progress
decrease auto-clears a stale focus referencing a now-hidden element.

### 17. Backend test results
`cd backend && uv run pytest` → **311 passed, 5 failed, 7 errors**. The 5 failures + 7
errors are the pre-existing Phase-5 test-pollution issue documented in
`.planning/phases/06-.../deferred-items.md` (present at HEAD before Phase 06 started;
unrelated to Phase 06 changes — confirmed by 06-03/06-07/06-12 runs). Contract tests
10/10.

### 18. Frontend test/lint/typecheck/build results
`NODE_ENV=test CI=1 npm run test` → **161/161 passed (22 files)**. `npx tsc -b` → clean.
`npm run build` → clean. `npm run lint` → 28 errors, **all pre-existing** (verified via
`git stash` baseline: identical at HEAD before Phase 06; DetailPanel/GraphCanvas
react-hooks findings + useChatSessions/useNotes/useRevisions/useRevisions.test/
RevisionHistoryPanel.test findings). Phase 06 introduced 0 new lint errors.

### 19. Manual acceptance checks
⏳ **PENDING** — the 20 items above await the live browser session.

### 20. Known limitations
- Qualitative answer-quality/language-following items (4, 5, 8) require a real provider;
  if none is available they must be marked as verified with `FakeLLMProvider` substitution
  and flagged, not silently skipped.
- Chat mode is inaccessible while a structural edge (claim_id === null) is selected —
  `App.tsx` renders `StructuralEdgeCard` instead of `DetailPanel` (pre-existing, documented
  since 06-09).
- Pre-existing lint debt (28 findings) and pre-existing backend test pollution (5 failed /
  7 errors) are tracked in `deferred-items.md`.
- Bundle chunk >500 kB warning (pre-existing, code-splitting is a future task).

### 21. Security caveats
- Graph content is untrusted prompt data; injection defenses tested (containment, not
  execution). No text-to-Cypher anywhere.
- Secrets: `LLM_API_KEY` read only inside the provider; session cookie HttpOnly; manual
  item 20 checks browser storage/logs.
- Write path: only ChangeSet confirm/reject endpoints mutate the graph; the chat message
  itself can never trigger a write (T-06-05 tested).

### 22. Whether the branch is safe to commit
⏳ **PENDING** — per PRD §22 "Do not commit until implementation, automated verification
and the manual acceptance checklist are complete" and §22's own final question. Automated
verification is green (with the documented pre-existing exceptions); the manual acceptance
gate (items 1–20) must pass before the safe-to-commit verdict.

---

*Prepared by: 06-12 executor (automated-evidence sections) — awaiting human verification.*
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent · Date: 2026-08-01*
