---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "09"
subsystem: frontend
tags: [typescript, react, vitest, shadcn, chat, radix-ui]

# Dependency graph
requires:
  - phase: 06-08
    provides: "Typed chat/ChangeSet API clients and useChatSessions/useChatMessages hooks"
  - phase: 06-UI-SPEC.md
    provides: "Chat & Panel Architecture contract, Copywriting Contract, Color/Spacing tokens"
provides:
  - "frontend/src/components/detail/DetailPanel.tsx — stateful Sheet open/mode toggle (Inspector/Chat), exported CLAIM_ACCENT_COLOR/EVIDENCE_ACCENT_COLOR constants"
  - "frontend/src/components/chat/ChatLauncher.tsx, ChatPanel.tsx, SessionPicker.tsx, MessageList.tsx, MessageBubble.tsx, CitationChip.tsx"
  - "frontend/src/components/ui/textarea.tsx, scroll-area.tsx (shadcn official registry)"
affects: [06-10, 06-11]

# Actuals (#2632)
actuals:
  tokens: 21846
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added:
    - "shadcn textarea (official @shadcn registry, radix-nova style)"
    - "shadcn scroll-area (official @shadcn registry, radix-nova style)"
  patterns:
    - "DetailPanel's Sheet open/mode state lifted to App.tsx, derived via three independent, non-overlapping handlers (node-select-opens-Inspector, ChatLauncher-toggles-Chat, pill-toggle-switches-mode-only) rather than one combined reducer"
    - "'Adjust state during render by comparing a state copy of the previous key' (useGraph.ts/useNotes.ts's established pattern) used for ChatPanel's default-session-selection and retry-target-clearing, instead of an effect + setState (avoids react-hooks/set-state-in-effect)"
    - "A ref-based one-shot guard (mutate a ref inside an effect, not state) used to flush a queued first-message send once a just-created session's own useChatMessages hook instance mounts — refs are exempt from the set-state-in-effect lint rule"
    - "CitationChip.tsx imports CLAIM_ACCENT_COLOR/EVIDENCE_ACCENT_COLOR from DetailPanel.tsx, creating a deliberate one-directional-safe circular import (DetailPanel -> ChatPanel -> MessageList -> CitationChip -> DetailPanel) that resolves correctly under ESM live bindings since the constants are only read inside function bodies, never at module top-level"

key-files:
  created:
    - frontend/src/components/ui/textarea.tsx
    - frontend/src/components/ui/scroll-area.tsx
    - frontend/src/components/chat/ChatLauncher.tsx
    - frontend/src/components/chat/ChatLauncher.test.tsx
    - frontend/src/components/chat/ChatPanel.tsx
    - frontend/src/components/chat/ChatPanel.test.tsx
    - frontend/src/components/chat/SessionPicker.tsx
    - frontend/src/components/chat/SessionPicker.test.tsx
    - frontend/src/components/chat/MessageList.tsx
    - frontend/src/components/chat/MessageList.test.tsx
    - frontend/src/components/chat/MessageBubble.tsx
    - frontend/src/components/chat/MessageBubble.test.tsx
    - frontend/src/components/chat/CitationChip.tsx
    - frontend/src/components/chat/CitationChip.test.tsx
  modified:
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/components/detail/DetailPanel.test.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/hooks/useChatMessages.ts

key-decisions:
  - "Node/edge selection never touches panelMode at all (not even a no-op setPanelMode('inspector')) — mode only changes via the pill toggle or ChatLauncher, which is what makes 'selecting a node while in Chat mode doesn't force-switch' trivially true rather than requiring a guarded branch"
  - "DetailPanel's Sheet `open` is a single independent boolean (not derived from `selected != null`) — once opened by any trigger it stays open until the one explicit ChatLauncher-collapse action, preserving the pre-phase-6 'always visible, content varies' feel for Inspector mode while adding real collapsibility for Chat mode"
  - "ChatErrorKind classification (disabled / provider-unavailable / recoverable / non-retryable) is planner discretion, not specified by 06-CONTEXT.md/06-UI-SPEC.md at the error-code level: LLM_DISABLED and LLM_PROVIDER_UNAVAILABLE map to the two named page-level banners; any other LLM_-prefixed code is treated as recoverable (assumed transient); any non-LLM_-prefixed code (including the hook's own `unknown_error` catch-all) is non-retryable"
  - "useChatMessages.sendMessage now optimistically appends the user's own message to local `messages` state immediately on send (Rule 1 bug fix, not part of 06-08's original file list) — previously only the assistant's `done` envelope message was ever appended, so a just-sent question would not render until the next full session refetch, which is a broken chat UX by definition"
  - "FailedMessageBubble renders only the destructive assistant-slot copy (no duplicate user-message bubble) since the user's own message is already visible via the optimistic-append fix above"
  - "A brand-new session created from the empty-state's first message (no prior session) queues its content via a ref-guarded effect that fires once useChatMessages rebinds to the new session id on the next render, rather than requiring the user to click 'New conversation' before their first question"

requirements-completed: [RAG-16]

coverage:
  - id: D1
    description: "DetailPanel's Sheet open/mode props are fully controlled from App.tsx; defaults closed/Inspector on mount; ChatLauncher opens (Chat)/collapses; node-select-in-Chat-mode never force-switches mode; existing Inspector tab/tests regression-free"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx#collapsible Sheet + Inspector/Chat mode toggle (4 tests) + 11 pre-existing regression tests"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#ChatLauncher open/collapse + chat-mode-survives-node-selection (2 tests) + regression update"
        status: pass
    human_judgment: false
  - id: D2
    description: "ChatPanel/SessionPicker render every documented empty state (no session, zero-message session, zero sessions), the series+episode badge, and the three suggestion chips"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/ChatPanel.test.tsx (12 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/chat/SessionPicker.test.tsx (5 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Streaming text renders incrementally with a reduced-motion-aware pulsing indicator and swaps Send for Stop-generating; recoverable/non-retryable failed turns and the disabled-provider/transient-503 banners render distinct, documented copy"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/MessageBubble.test.tsx (7 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/chat/ChatPanel.test.tsx#streaming / error states (5 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Citation chips reuse DetailPanel.tsx's CLAIM_ACCENT_COLOR/EVIDENCE_ACCENT_COLOR (no redefined literal), omit the Eye action when related IDs are empty, and render identically at any count with no special-case layout"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "frontend/src/components/chat/CitationChip.test.tsx (8 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/chat/MessageList.test.tsx (7 tests)"
        status: pass
      - kind: other
        ref: "grep -c \"D946EF\\|FB923C\" frontend/src/components/chat/CitationChip.tsx (0 matches — imported, never redefined)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full RAG-16 state-coverage matrix (chat open/close, new-conversation, initial history render, streaming, stop generation, error+retry both kinds, disabled-provider, empty states, citation zero/one/many, long-text, existing-Inspector regression) has at least one corresponding test"
    requirement: RAG-16
    verification:
      - kind: unit
        ref: "132/132 frontend tests pass (npx vitest run); npx tsc -b --noEmit clean; npm run build clean"
        status: pass
    human_judgment: false

duration: 1h 10min
completed: 2026-08-01
status: complete
---

# Phase 06 Plan 09: Chat surface — DetailPanel mode toggle, ChatLauncher, ChatPanel, MessageList, CitationChip Summary

**DetailPanel's Sheet becomes genuinely collapsible for the first time in this codebase (stateful open + Inspector/Chat mode toggle), with a full streaming chat surface — session picker, message bubbles, citation chips, retry, and disabled-provider/transient-503 banners — mounted as its Chat-mode content.**

## Performance

- **Duration:** ~1h 10min
- **Tasks:** 3
- **Files created:** 14 (8 source, 6 test) · **Files modified:** 5

## Accomplishments

- `DetailPanel.tsx`: `<Sheet open modal={false}>`'s hardcoded `open` literal replaced with a real controlled prop (lifted to `App.tsx`); adds a two-segment "Inspector"/"Chat" pill toggle in `SheetHeader` (visual pattern copied from `EpisodeSelector`); `CLAIM_ACCENT_COLOR`/`EVIDENCE_ACCENT_COLOR` promoted to exported module-level constants for `CitationChip.tsx` to reuse.
- `App.tsx`: owns `panelOpen`/`panelMode` state via three independent handlers — node selection (opens in Inspector, only when not already in Chat), `ChatLauncher` click (opens in Chat / collapses if already open in Chat), and the pill toggle (switches mode only, panel stays open) — with zero overlap between them.
- `ChatLauncher.tsx`: topBar icon+label button, `aria-label` toggling "Open chat"/"Close chat".
- `ChatPanel.tsx`: session picker + series/episode badge + empty-state (heading/body/3 suggestion chips) or `MessageList`; wires Send/Stop-generating swap, disabled-provider banner ("Chat is turned off"), transient-503 banner ("...temporarily unavailable" + Retry), and a `classifyChatError` helper distinguishing four error treatments; a first message sent with zero existing sessions transparently creates one and queues the send.
- `SessionPicker.tsx`: compact shadcn `Select` (explicit `SelectValue` children to avoid Radix's item-text-mirroring portal duplicating the hover-reveal delete button into the trigger), "New conversation" button, delete via a `ConfirmAdvanceModal`-style Dialog.
- `MessageList.tsx`/`MessageBubble.tsx`: `scroll-area`-based auto-scroll-unless-user-scrolled-up list; user (`--elevated`, right) vs. assistant (`--card`, left, `Sparkles`) bubbles; reduced-motion-aware streaming pulse; destructive-accented failed-turn slot (recoverable-with-Retry vs. non-retryable).
- `CitationChip.tsx`: claim/evidence accent reuse, muted border for source-only, `Eye` "Show in graph" only when `related_node_ids`/`related_edge_ids` are non-empty.

## Task Commits

1. **Task 1: shadcn components, stateful DetailPanel mode toggle, ChatLauncher, ChatPanel shell** - `06dce8a` (feat)
2. **Task 2: MessageList, MessageBubble, CitationChip — streaming render, retry, citation accents** - `3d3a0eb` (feat)
3. **Task 3: Component tests — full RAG-16 state-coverage matrix** - `994cd7a` (test)

**Plan metadata:** committed separately after this summary (docs commit).

## Files Created/Modified

- `frontend/src/components/ui/textarea.tsx`, `scroll-area.tsx` — official `@shadcn` registry components
- `frontend/src/components/chat/ChatLauncher.tsx`, `ChatPanel.tsx`, `SessionPicker.tsx`, `MessageList.tsx`, `MessageBubble.tsx`, `CitationChip.tsx` — new chat UI
- `frontend/src/components/detail/DetailPanel.tsx` — stateful open/mode props, exported accent constants
- `frontend/src/App.tsx` — panel open/mode state + `ChatLauncher` wiring
- `frontend/src/hooks/useChatMessages.ts` — Rule 1 fix: optimistic user-message append
- 8 new test files + `DetailPanel.test.tsx`/`App.test.tsx` updates

## Decisions Made

- Node/edge selection never touches `panelMode` — only the pill toggle and `ChatLauncher` do, making the "no force-switch while in Chat" truth structurally true rather than a guarded exception.
- `open` is one independent boolean covering both modes (not derived from `selected != null`), preserving Inspector's pre-phase-6 "always visible once opened" feel while adding real Chat-mode collapsibility.
- `ChatErrorKind` classification is a documented planner-discretion convention (not specified at the error-code level by 06-CONTEXT.md/06-UI-SPEC.md): `LLM_DISABLED`/`LLM_PROVIDER_UNAVAILABLE` are the two named banners; other `LLM_`-prefixed codes are recoverable; anything else (including the hook's `unknown_error` fallback) is non-retryable.
- `useChatMessages.sendMessage` now optimistically appends the user's own message locally (Rule 1 fix, file outside this plan's stated list) — see Deviations.
- A brand-new session's first message queues via a ref-guarded effect rather than requiring an explicit "New conversation" click first.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `useChatMessages.sendMessage` never appended the user's own message locally**
- **Found during:** Task 2, while designing `MessageList`'s turn rendering.
- **Issue:** The hook (06-08) only pushes `envelope.message` (the assistant's reply) on `done`; the user's own outgoing question was never added to local `messages` state, so it would vanish from the UI until the next full `getChatSession` refetch — a chat where your own sent question disappears is broken by definition.
- **Fix:** `sendChatMessage` now optimistically appends a synthetic user `ChatMessage` (placeholder id/timestamp, `visible_until_order_snapshot: 0`) immediately on send.
- **Files modified:** `frontend/src/hooks/useChatMessages.ts`
- **Verification:** `useChatMessages.test.tsx`'s existing assertions (which use `toContainEqual`, not exact-length checks) still pass unmodified; full suite green.
- **Committed in:** `3d3a0eb`

**2. [Rule 3 - Blocking] `react-hooks/set-state-in-effect` flagged two originally effect-based state derivations**
- **Found during:** Task 1 (`ChatPanel`'s default-session-selection) and Task 2 (`ChatPanel`'s queued-first-send).
- **Issue:** Both were first written as `useEffect(() => { ...; setState(...) }, [...])`, which the project's React Compiler ESLint rule rejects.
- **Fix:** Session-selection defaulting was rewritten using the codebase's established "adjust state during render, comparing a state copy of the previous key" pattern (`useGraph.ts`/`useNotes.ts`/`DetailPanel.tsx`'s existing convention). The queued-first-send flush genuinely needs an effect (it calls an imperative `chatMessages.sendMessage`, a real side effect against a hook instance only available after the session-creating render) — its "already flushed" bookkeeping was moved from `setState` to a plain `useRef` mutation, which the lint rule doesn't flag.
- **Files modified:** `frontend/src/components/chat/ChatPanel.tsx`
- **Verification:** `npx eslint` clean; `npx tsc -b --noEmit` clean; full suite green.
- **Committed in:** `06dce8a`, `3d3a0eb`

**3. [Clarification, not a fix] Plan's `<files>`/acceptance criteria vs. actual test-file needs**
- **Issue:** Task 1/Task 2's `<files>` tags list only source files, not the test files their own `tdd="true"`/`<verify>` mandates require (`ChatLauncher.test.tsx`, `SessionPicker.test.tsx`, `CitationChip.test.tsx`, `MessageBubble.test.tsx` are not in either task's `<files>` list, though `ChatPanel.test.tsx`/`MessageList.test.tsx` are explicitly listed as Task 3 "add" targets despite Task 1/2 needing to create/extend them first to satisfy their own `<verify>` commands). Consistent with the same pattern documented in `06-08-SUMMARY.md`.
- **Resolution:** Created all test files each task's own TDD mandate and `<verify>` command required; Task 3 extended `ChatPanel.test.tsx` (created in Task 1) with the remaining state-matrix rows rather than creating it fresh.
- **No code impact** — purely a plan-document bookkeeping note.

**4. [Interpretive] `components.json` has no "installed components" list to update**
- **Issue:** Task 1's acceptance criteria states "`frontend/components.json` lists `textarea` and `scroll-area` under installed components" — this project's `components.json` schema (confirmed via the shadcn CLI's own actual write behavior) has no such list field; installed-component tracking is implicit in `src/components/ui/` file presence only. Running `npx shadcn@latest add textarea scroll-area` produced zero diff to `components.json`.
- **Resolution:** Verified via `git diff components.json` (empty) that this is the CLI's genuine, correct behavior, not a tooling failure — `textarea.tsx`/`scroll-area.tsx` exist in `src/components/ui/` as the actual signal of installation.

**5. [Known limitation, out of scope] Chat mode is inaccessible while a structural edge is selected**
- **Issue:** `App.tsx`'s existing branch renders `StructuralEdgeCard` *instead of* `DetailPanel` when the selected element is a structural (non-claim-backed) edge — a pre-existing architectural pattern this plan's `files_modified` list does not touch (`StructuralEdgeCard.tsx` is untouched). Since `ChatLauncher`/Chat mode only exist inside `DetailPanel`, selecting a structural edge while Chat mode is open would visually replace the chat panel with the structural-edge card.
- **Not fixed:** No truth in this plan addresses structural-edge + Chat-mode interaction, and `StructuralEdgeCard.tsx` is out of this plan's declared scope. Flagged here for a future plan (06-10/06-11 graph-focus wiring) to resolve if it becomes user-visible friction.

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3), 2 documentation clarifications (no code impact), 1 known out-of-scope limitation (flagged, not fixed).
**Impact on plan:** No scope creep — both auto-fixes were required for correct behavior (Rule 1) or a clean lint pass already mandated by this codebase's tooling (Rule 3).

## Issues Encountered

- Radix `Select`'s `SelectItemText` portals its children into the trigger's `SelectValue` display for the currently-selected item whenever `SelectValue` has no explicit `children` — this silently duplicated `SessionPicker`'s hover-reveal delete button into the trigger as an inert, `pointer-events:none` copy. Fixed by passing an explicit `children` expression to `SelectValue` (computed from the active session's title), which Radix's own `valueNodeHasChildren` check uses to skip the portal entirely.
- Radix `Select`/`ToggleGroup` commit their action on `pointerup` for mouse input (not `click`) — `SessionPicker`'s delete-icon `stopPropagation` needed to intercept both `onPointerDown` *and* `onPointerUp`, not just `onClick`, or clicking delete also selected the row underneath it.
- Pre-existing project-wide lint debt (9 `react-hooks/refs`/`preserve-manual-memoization` findings, all inside `DetailPanel.tsx`'s pre-existing Notes-tab code, unrelated to this plan's changes) is unaffected — confirmed identical error count/location via `git stash` diff before/after this plan's edits.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 06-10 (graph-focus wiring) can wire `CitationChip`'s `onShowInGraph` prop and `ChatPanel`'s/`MessageList`'s `onOpenDetail` prop (both already accepted, currently unwired no-ops) into `GraphCanvas.tsx`'s new `focusedElementIds` prop and the Inspector-mode switch, per 06-UI-SPEC.md's "Graph synchronization" section.
- 06-11 (ChangeSet preview card) can mount inline in `MessageList.tsx` alongside the assistant message it was proposed by, reusing `ChatPanel`'s already-resolved `chatMessages.proposedChangeSet` value (currently read but not yet rendered).
- Known limitation: Chat mode is inaccessible while a structural edge is selected (see Deviations #5) — worth a look during 06-10/06-11 if it surfaces as user-visible friction.
- No blockers.

## Self-Check: PASSED

- FOUND: frontend/src/components/ui/textarea.tsx
- FOUND: frontend/src/components/ui/scroll-area.tsx
- FOUND: frontend/src/components/chat/ChatLauncher.tsx
- FOUND: frontend/src/components/chat/ChatPanel.tsx
- FOUND: frontend/src/components/chat/SessionPicker.tsx
- FOUND: frontend/src/components/chat/MessageList.tsx
- FOUND: frontend/src/components/chat/MessageBubble.tsx
- FOUND: frontend/src/components/chat/CitationChip.tsx
- FOUND commit 06dce8a
- FOUND commit 3d3a0eb
- FOUND commit 994cd7a

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*
