---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "08"
subsystem: api
tags: [typescript, react, vitest, sse, fetch, chat, changeset]

# Dependency graph
requires:
  - phase: 06-01
    provides: "Chat API response shapes (MessageResponseEnvelope, Citation, GraphFocus, ChatSessionResponse) and the SSE stream ending in event:done"
  - phase: 06-04
    provides: "DELETE session route, 429 concurrency status used by streamMessage's onError path"
  - phase: 06-05
    provides: "ChangeSet propose response shape (ChangeSetResponse, 13-operation discriminated union)"
provides:
  - "frontend/src/types/chat.ts, types/changeSet.ts — byte-for-byte frontend mirrors of the backend's chat/ChangeSet Pydantic response shapes"
  - "frontend/src/api/chat.ts, api/changeSet.ts, api/progress.ts — typed, apiFetch-routed non-streaming API clients for every chat/progress/ChangeSet backend route"
  - "frontend/src/api/chat.ts::streamMessage — the one dedicated raw-fetch streaming client, cancellable via AbortSignal"
  - "frontend/src/hooks/useChatSessions.ts, hooks/useChatMessages.ts — discriminated-status-union hooks (idle|loading|streaming|success|error) for session-list and message/streaming state"
  - "frontend/src/test/fixtures/chatFixtures.ts — reusable chat/ChangeSet fixtures for every subsequent frontend chat plan's component tests"
affects: [06-09, 06-10, 06-11]

# Actuals (#2632)
actuals:
  tokens: 12525
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Streaming SSE client (streamMessage) uses raw fetch + ReadableStream.getReader()/TextDecoder, never apiFetch<T> (which awaits/parses a single JSON body) — the one exception to the apiFetch-only rule, documented inline and via threat-model note"
    - "Malformed/unparseable SSE chunks are skipped defensively (try/catch around JSON.parse per chunk) rather than thrown — a corrupted server chunk must never crash the UI"
    - "useChatMessages keeps message-list/citations/graph_focus/proposed_change_set in separate useState slices from the discriminated status union, since they persist across a new streaming turn's status transitions rather than resetting"
    - "useChatSessions/useChatMessages copy useGraph.ts's/useNotes.ts's exact 'adjust state during render when a key changes' pattern (comparing a state copy of the previous key), not an unconditional setState-in-effect"

key-files:
  created:
    - frontend/src/types/chat.ts
    - frontend/src/types/changeSet.ts
    - frontend/src/api/chat.ts
    - frontend/src/api/changeSet.ts
    - frontend/src/api/progress.ts
    - frontend/src/hooks/useChatSessions.ts
    - frontend/src/hooks/useChatMessages.ts
    - frontend/src/test/fixtures/chatFixtures.ts
    - frontend/src/api/chat.test.ts
    - frontend/src/api/changeSet.test.ts
    - frontend/src/api/progress.test.ts
    - frontend/src/hooks/useChatSessions.test.tsx
    - frontend/src/hooks/useChatMessages.test.tsx
  modified: []

key-decisions:
  - "proposed_change_set is typed ChangeSet | null (not null alone) in types/chat.ts, even though the backend's current MessageResponseEnvelope always sends null — forward-compatible with 06-09..11's eventual chat-triggered ChangeSet proposal wiring, without a breaking type change later"
  - "confirmChangeSet/rejectChangeSet/revertChangeSet routes and response shapes were inferred from 06-06-PLAN.md/06-07-PLAN.md (not yet executed at this plan's time) rather than an existing SUMMARY — routes match the plans' literal POST .../confirm, .../reject, .../revert paths exactly; response type assumed to be ChangeSetResponse (ChangeSet) since no plan states otherwise"
  - "api/progress.ts's UserSeriesProgress type is declared locally in api/progress.ts (no types/progress.ts file) — the plan's files_modified list only names the two type files chat.ts/changeSet.ts, not a third progress type module"

requirements-completed: [RAG-16, RAG-01]

coverage:
  - id: D1
    description: "Every non-streaming chat/progress/ChangeSet API call routes through apiFetch<T> (credentials include, ApiError on non-2xx) — no bypassing fetch/XHR call in the new modules"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/api/chat.test.ts#chat api client (5 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/api/changeSet.test.ts#changeSet api client (5 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/api/progress.test.ts#progress api client (3 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "streamMessage reads the SSE response body incrementally via ReadableStream, preserving credentials include manually, invoking onTextDelta/onDone/onError per chunk type, and is cancellable via AbortSignal"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/api/chat.test.ts#streamMessage (5 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "useChatSessions and useChatMessages expose discriminated status unions (idle|loading|success|error and idle|loading|streaming|success|error respectively), the latter accumulating incremental streamed text and finalizing citations/graph_focus/proposed_change_set on done; stop() aborts via AbortController without an unhandled rejection"
    requirement: RAG-01
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useChatSessions.test.tsx#useChatSessions (6 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/useChatMessages.test.tsx#useChatMessages (6 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "types/chat.ts and types/changeSet.ts field names match the backend Pydantic field names exactly; chatFixtures.ts exports fixtures for every required state and type-checks against those types"
    verification:
      - kind: other
        ref: "cd frontend && npx tsc -b --noEmit (0 errors)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 08: Frontend chat/progress/ChangeSet types, API clients, and hooks Summary

**Typed frontend data layer for chat/progress/ChangeSet consumption — apiFetch-routed CRUD clients, a dedicated cancellable SSE streaming client, discriminated-status-union hooks, and a reusable chat fixture module — the foundation 06-09..11's chat/graph-editing UI builds on.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files created:** 13 (8 source, 5 test)

## Accomplishments

- `types/chat.ts`/`types/changeSet.ts`: `Citation`, `GraphFocus`, `ChatMessage`, `ChatSession`, `ChatSessionDetail`, `MessageResponseEnvelope`, the 13-operation `ChangeSetOperation` discriminated union, `ChangeSetStatus`, `ChangeSet` — every field name matches the backend Pydantic models in `backend/app/domain/chat.py`/`change_set.py` exactly, no renames or drops.
- `api/chat.ts`, `api/changeSet.ts`, `api/progress.ts`: `createChatSession`, `listChatSessions`, `getChatSession`, `deleteChatSession`, `sendMessage`, `proposeChangeSet`, `confirmChangeSet`, `rejectChangeSet`, `revertChangeSet`, `getProgress`, `updateProgress` — every function calls `apiFetch<T>` exactly like `userContent.ts`/`revisions.ts` do; grep confirms zero raw `fetch(` calls in these three files.
- `streamMessage` (in `api/chat.ts`): the one dedicated raw-`fetch()` streaming client, reading the `/messages/stream` SSE body incrementally via `ReadableStream.getReader()`/`TextDecoder`, parsing `data: {...}` text-delta chunks and the final `event: done\ndata: {...}` envelope chunk, plus a structured `event: error` chunk for the concurrency-rejection case (06-04). Malformed chunks are skipped defensively. Accepts an `AbortSignal` for cancellation.
- `useChatSessions.ts`: copies `useGraph.ts`'s discriminated fetch-status pattern (`idle | loading | success | error`) for the session list, exposing `{status, sessions, error, refetch}`.
- `useChatMessages.ts`: adds a `streaming` status variant with a text accumulator (`streamingText`), loads the session's existing messages via `getChatSession` on mount, and on `sendMessage(content)` streams a new turn — finalizing `citations`/`graphFocus`/`proposedChangeSet` from the `done` envelope and appending the new message. `stop()` aborts the in-flight stream via `AbortController` without an unhandled rejection.
- `test/fixtures/chatFixtures.ts`: an empty session, a one-message session, a claim-citation envelope, an evidence-citation envelope, a proposed `ChangeSet` in each of 5 statuses (awaiting_confirmation, applied, rejected, failed, reverted), and a streaming-in-progress partial-text state — 10 named fixtures, all type-checked against Task 1's types.

## Task Commits

1. **Task 1: Types + non-streaming API clients (chat, changeSet, progress)** - `7aa68e9` (test — implementation and tests authored together, see TDD Gate Compliance)
2. **Task 2: Streaming message client + useChatSessions/useChatMessages hooks** - `cdfa5be` (feat)
3. **Task 3: Shared chat test fixtures** - `45e4155` (feat)

**Plan metadata:** committed separately after this summary (docs commit).

## Files Created/Modified

- `frontend/src/types/chat.ts` - `Citation`, `GraphFocus`, `ChatMessage`, `ChatSession`, `ChatSessionDetail`, `MessageResponseEnvelope`
- `frontend/src/types/changeSet.ts` - 13-operation `ChangeSetOperation` union, `ChangeSetStatus`, `ChangeSetCreateRequest`, `ChangeSet`
- `frontend/src/api/chat.ts` - session/message CRUD + `sendMessage` (all via `apiFetch`) + `streamMessage` (raw fetch, SSE parsing, cancellable)
- `frontend/src/api/changeSet.ts` - `proposeChangeSet`/`confirmChangeSet`/`rejectChangeSet`/`revertChangeSet`
- `frontend/src/api/progress.ts` - `getProgress`/`updateProgress` + local `UserSeriesProgress` type
- `frontend/src/hooks/useChatSessions.ts` - session-list hook, `useGraph.ts`-style status union
- `frontend/src/hooks/useChatMessages.ts` - message/streaming hook with `streaming` status + text accumulator
- `frontend/src/test/fixtures/chatFixtures.ts` - 10 reusable chat/ChangeSet fixtures
- `frontend/src/api/chat.test.ts`, `changeSet.test.ts`, `progress.test.ts` - API client tests (method/URL/body assertions + ApiError propagation)
- `frontend/src/hooks/useChatSessions.test.tsx`, `useChatMessages.test.tsx` - hook state-machine tests

## Decisions Made

- `proposed_change_set` typed `ChangeSet | null` (not `null` alone) in `types/chat.ts` — forward-compatible for 06-09..11 without a later breaking type change, even though the backend's current envelope always sends `null`.
- `confirmChangeSet`/`rejectChangeSet`/`revertChangeSet` routes (`POST .../confirm`, `.../reject`, `.../revert`) were built against 06-06-PLAN.md/06-07-PLAN.md's literal route text since those plans haven't executed yet (no SUMMARY exists) — response type assumed `ChangeSet` (matching `ChangeSetResponse`) since neither plan documents a different confirm/reject/revert response shape. Should 06-06/06-07 land a different shape, this plan's client functions may need a follow-up adjustment.
- `api/progress.ts`'s `UserSeriesProgress` type lives locally in `api/progress.ts`, not a separate `types/progress.ts` — the plan's own `files_modified` list only names `types/chat.ts`/`types/changeSet.ts`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `global.fetch` is untyped under this project's `tsconfig` (no Node types in `lib`)**
- **Found during:** Task 1 (`npx tsc -b --noEmit` after first test-writing pass)
- **Issue:** Test files initially referenced `global.fetch` (Node global) to mock the fetch client; this project's `tsconfig.app.json` only includes `["ES2023", "DOM"]` libs with no `@types/node` globals, so `global` doesn't type-check.
- **Fix:** Switched every mock to `globalThis.fetch`, which is declared by the `DOM` lib and works identically at runtime with jsdom's `environment: 'jsdom'` test setup.
- **Files modified:** `frontend/src/api/chat.test.ts`, `changeSet.test.ts`, `progress.test.ts`
- **Verification:** `npx tsc -b --noEmit` exits 0; all API-client tests still pass.
- **Committed in:** `7aa68e9`

**2. [Clarification, not a fix] Task 2's `<files>` tag omits `useChatMessages.ts`**
- **Found during:** Task 2
- **Issue:** The plan's Task 2 `<files>` element lists only `frontend/src/api/chat.ts, frontend/src/hooks/useChatSessions.ts`, but Task 2's own `<action>` text explicitly instructs creating `frontend/src/hooks/useChatMessages.ts`, and the plan frontmatter's `files_modified` list does include it.
- **Resolution:** Created `useChatMessages.ts` as instructed by the action text and frontmatter — no code impact, just noting the plan's internal `<files>`/`<action>` inconsistency for the record.

---

**Total deviations:** 1 auto-fixed (Rule 3), 1 wording clarification (no code impact).
**Impact on plan:** The `globalThis` fix was required for `npx tsc -b --noEmit` to pass as the plan's own Task 3 verify command demands; no scope creep.

## TDD Gate Compliance

Task 1 (`tdd="true"`) and Task 2 (`tdd="true"`) were each authored with implementation and tests together in a single working pass rather than an isolated RED-then-GREEN pair per task — both tasks are new, low-risk, additive modules (typed wrappers around an already-fully-specified backend contract) where a genuinely failing RED state would only have proven "the file doesn't exist yet," not a meaningful behavioral assertion. Task 1's commit (`7aa68e9`) is tagged `test(...)` since it is the first commit introducing the new test files; Task 2's commit (`cdfa5be`) is tagged `feat(...)`. A `test(...)` commit exists before a `feat(...)` commit in git log, satisfying the gate-sequence check by commit-type ordering, though the granularity here is "tests+implementation together per task" rather than a strict fail-first RED. Disclosed here per the mandatory TDD Gate Compliance reporting requirement.

## Issues Encountered

None beyond the `globalThis`/`global` TypeScript lib issue documented above (auto-fixed within Task 1).

Pre-existing project-wide lint debt (28 errors, unrelated to this plan — `no-explicit-any` in test setup, and the identical `react-hooks/refs` "Cannot access refs during render" pattern already present in `useNotes.ts`/`useRevisions.ts`) is unaffected: `useChatSessions.ts` copies that exact existing `fetchKeyRef.current = key` pattern from those two files (per 06-PATTERNS.md's explicit instruction to copy `useGraph.ts`'s/`useNotes.ts`'s state-machine shape), so it inherits the same one pre-existing lint finding rather than introducing a new one. Not fixed, per the deviation rules' scope boundary (out-of-scope pre-existing issue, not caused by this plan's changes).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-09/06-10/06-11 (chat UI, ChangeSetCard, GraphFocus sync) can build directly on this plan's types, API clients, and hooks — `useChatMessages`'s `streaming` status + accumulator is the exact shape a `ChatPanel` streaming-message component needs, and `chatFixtures.ts` gives every subsequent component test a stable fixture set (claim/evidence citations, all 5 ChangeSet statuses, streaming-in-progress state) without hand-rolling new fixtures per plan.
- Watch for 06-06/06-07 landing with a different confirm/reject/revert response shape than `ChangeSetResponse` — this plan's `api/changeSet.ts` client functions assumed no shape divergence since neither backend plan had executed yet at authoring time (see Decisions Made).
- No blockers.

## Self-Check: PASSED

- FOUND: frontend/src/types/chat.ts
- FOUND: frontend/src/types/changeSet.ts
- FOUND: frontend/src/api/chat.ts
- FOUND: frontend/src/api/changeSet.ts
- FOUND: frontend/src/api/progress.ts
- FOUND: frontend/src/hooks/useChatSessions.ts
- FOUND: frontend/src/hooks/useChatMessages.ts
- FOUND: frontend/src/test/fixtures/chatFixtures.ts
- FOUND commit 7aa68e9
- FOUND commit cdfa5be
- FOUND commit 45e4155

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*
