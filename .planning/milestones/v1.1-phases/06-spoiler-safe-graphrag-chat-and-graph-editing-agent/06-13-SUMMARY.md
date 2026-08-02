---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 13
subsystem: chat-ui
tags: [react, hooks, vitest, abort-controller, chat-status]

# Dependency graph
requires:
  - phase: 06-09
    provides: sendChatMessage optimistic user-message append and the streaming status machine this fix corrects
  - phase: 06-10
    provides: the no-error-on-abort intent this fix preserves without regressing
provides:
  - "useChatMessages.ts's stop() flow now always resolves status to a terminal 'success' value after an aborted stream, instead of leaving it stuck at 'streaming'"
affects: [06-UAT, chat-ui, ChatPanel, MessageList]

# Actuals (#2632)
actuals:
  tokens: 442
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns: ["Aborted-fetch catch branches must always drive status to a terminal value, never a silent no-op, even when suppressing an error banner"]

key-files:
  created: []
  modified:
    - frontend/src/hooks/useChatMessages.ts
    - frontend/src/hooks/useChatMessages.test.tsx

key-decisions:
  - "Reused the existing 'success' status value for the post-abort terminal state instead of introducing a new Status union member — every existing consumer (ChatPanel.tsx, MessageList.tsx) already treats 'success' as 'not streaming, no error', which is exactly what Stop should produce"
  - "Fix lives entirely in sendChatMessage's streamMessage(...).catch aborted branch, not in stop() itself — stop() only owns triggering the abort; the catch branch is the only code path that observes the abort actually completing"

patterns-established:
  - "Aborted-catch branches that intentionally suppress error UI must still transition status to a terminal value — silently returning early leaves status frozen indefinitely"

requirements-completed: [RAG-16]

coverage:
  - id: D1
    description: "stop() transitions chat status off 'streaming' to 'success' as soon as the aborted fetch's rejection is caught, clearing the Stop button and Thinking/Streaming bubble immediately (closes gap G-06-4)"
    requirement: "RAG-16"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useChatMessages.test.tsx#stop() aborts the in-flight stream via AbortController without an unhandled rejection"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-08-02
status: complete
---

# Phase 06 Plan 13: Fix Stop button/Thinking indicator stuck after abort (G-06-4) Summary

**`useChatMessages.ts`'s aborted-stream catch branch now sets `status: 'success'` instead of no-oping, so the Stop button and Thinking/Streaming bubble clear immediately after a user clicks Stop.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-02T12:10:00Z (approx, first commit 2026-08-02T12:15:52+03:00)
- **Completed:** 2026-08-02T12:16:30+03:00 (approx)
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Closed UAT gap G-06-4 (severity major): Stop button and Thinking/Streaming indicator no longer stay stuck forever after a user-initiated stop
- Extended the existing `stop()` regression test to assert the post-abort `status` value in addition to the pre-existing abort-signal assertion, in the same test body
- Confirmed zero regressions across the full frontend suite (173/173 tests), typecheck, and production build with the fix in place

## Task Commits

Each task was committed atomically:

1. **Task 1: stop() transitions status off 'streaming' after abort** - `8a396e0` (fix)
2. **Task 2: Full frontend regression** - verification-only task, no file changes to commit (test/lint/typecheck/build all run against Task 1's commit)

**Plan metadata:** (this commit, pending)

## Files Created/Modified
- `frontend/src/hooks/useChatMessages.ts` - `sendChatMessage`'s aborted-catch branch (`streamMessage(...).catch`) now calls `setStatus({ status: 'success' })` before returning when `controller.signal.aborted` is true, instead of a bare no-op `return`
- `frontend/src/hooks/useChatMessages.test.tsx` - extended the existing "stop() aborts the in-flight stream via AbortController without an unhandled rejection" test with an assertion that `result.current.status` equals `'success'` after the abort's microtask queue flushes

## Decisions Made
- Reused the existing `'success'` status value for the post-abort terminal state rather than adding a new `Status` union member — `ChatPanel.tsx` and `MessageList.tsx` both already derive Stop-button/Thinking-bubble visibility solely from `status`, and every consumer already treats `'success'` as "not streaming, no error." No changes to `ChatPanel.tsx` or `MessageList.tsx` were needed or made, per the plan's explicit constraint.
- Fix placed in the `.catch` branch (the only code path that observes the abort's rejection), not in `stop()` itself, matching the plan's root-cause diagnosis in `.planning/debug/stop-button-thinking-indicator-stuck.md`.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were met without needing any Rule 1-4 deviations to `useChatMessages.ts`, `useChatMessages.test.tsx`, `ChatPanel.tsx`, or `MessageList.tsx`.

### Out-of-scope discoveries (logged, not fixed)

Task 2's `npm run lint` run surfaced 28 pre-existing lint errors in files this plan does not modify (`react-hooks/refs` "Cannot access refs during render" in `useChatSessions.ts`/`useNotes.ts`/`useRevisions.ts`, `@typescript-eslint/no-explicit-any` in `useRevisions.test.tsx`, and one `react-hooks/set-state-in-effect`). None involve `useChatMessages.ts`/`useChatMessages.test.tsx`. Per the executor's SCOPE BOUNDARY rule, these are out of scope for this gap-closure plan and are logged in `.planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/deferred-items.md` rather than fixed here. `npm run test` (173/173), `npx tsc -b` (clean), and `npm run build` all pass with the G-06-4 fix in place — only `npm run lint`'s unrelated pre-existing errors remain, consistent with the plan's success criteria which required test/lint/typecheck/build to "remain green" for files this plan touches.

## TDD Gate Compliance

Task 1 carried `tdd="true"`. The plan's `<action>` described extending an *existing* test (not writing a wholly new RED test) alongside the implementation fix, and both changes were small enough to verify together in a single `npm run test -- useChatMessages` pass before committing. The change was landed as a single `fix(06-13):` commit rather than separate `test(...)` (RED) then `fix(...)` (GREEN) commits. This deviates from the standard RED/GREEN/REFACTOR commit-splitting convention — flagged here per the plan-level TDD gate validation requirement. The test was manually verified to fail against the pre-fix code (the `.catch` branch's bare `return` leaves `status` at `'streaming'`) before the fix was applied, confirming genuine RED->GREEN behavior even though it was not captured as two separate commits.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- G-06-4 is closed; the Stop button and Thinking/Streaming indicator now clear immediately and reliably after a user-initiated stop
- Full frontend suite (173/173), typecheck, and production build all remain green with the fix in place
- Pre-existing lint errors in `useChatSessions.ts`/`useNotes.ts`/`useRevisions.ts`/`useRevisions.test.tsx` remain open in `deferred-items.md` for a future cleanup plan; they do not block this gap closure

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-02*

## Self-Check: PASSED
- FOUND: frontend/src/hooks/useChatMessages.ts
- FOUND: frontend/src/hooks/useChatMessages.test.tsx
- FOUND: .planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/06-13-SUMMARY.md
- FOUND: commit 8a396e0
