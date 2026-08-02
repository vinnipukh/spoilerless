---
status: resolved
trigger: "While the answer streams, a Stop button is visible; when it completes (or fails) the Stop button disappears and no stuck loading/thinking indicator remains. actual: button doesnt dissappear. thinking thing still shows. generation stops."
created: 2026-08-02T00:00:00Z
updated: 2026-08-02T01:05:00Z
resolved_by: "06-13-PLAN.md (commit 8a396e0)"
---

## Current Focus

hypothesis: CONFIRMED — useChatMessages.stop() only calls abortControllerRef.current?.abort(); it never itself transitions `status` out of 'streaming'. The rejected streamMessage() promise (AbortError) is caught in sendChatMessage's `.catch`, which does `if (controller.signal.aborted) return` — a deliberate early-return that swallows the abort silently but leaves `status` frozen at `{status: 'streaming', streamingText: ...}` forever. ChatPanel's `isStreaming` (Stop-button visibility) and MessageList's Thinking/Streaming bubble are both derived solely from this `status`, so both stay stuck after Stop is clicked even though the backend generation has actually stopped.
test: Traced the full state path: ChatPanel.tsx isStreaming <- chatMessages.status === 'streaming' <- useChatMessages.ts Status union <- sendChatMessage's setStatus calls. Confirmed stop() (line 134-136) has no setStatus call, and the .catch handler (line 120-129) explicitly no-ops when signal.aborted is true (line 124: `if (controller.signal.aborted) return`).
expecting: n/a (root cause confirmed, find_root_cause_only mode — no fix applied)
next_action: none — return ROOT CAUSE FOUND to caller

## Symptoms

expected: While the answer streams, a Stop button is visible. When the answer completes (or fails), the Stop button disappears. It never stays stuck after the stream ends.
actual: Stop button doesn't disappear; the thinking/streaming indicator still shows even though generation has stopped.
errors: None reported
reproduction: UAT phase 06, Test 4 ("Stop generating button") — click Stop while an answer is streaming.
started: Discovered during UAT retest 2026-08-02 (phase 06 gap G-06-4, second symptom after the first premature-error symptom was fixed by commit 1cc2f74)

## Eliminated

(none — root cause found on first hypothesis, informed by direct code trace + a corroborating existing test gap)

## Evidence

- timestamp: 2026-08-02T00:10:00Z
  checked: frontend/src/components/chat/ChatPanel.tsx (full file)
  found: `isStreaming = chatMessages.status === 'streaming'` (line 213) is the sole driver of the Stop-button branch in the JSX (line 317: `{isStreaming ? <StopButton/> : <SendButton/>}`), and of what's passed to MessageList as `streamingText` (line 293: `isStreaming ? chatMessages.streamingText : null`). Stop button's onClick (line 321) calls `chatMessages.stop()` and nothing else.
  implication: Stop-button/thinking-indicator visibility is entirely a function of the hook's `status`; ChatPanel itself has no independent stuck-state bug — the defect must be in how/whether `status` ever leaves 'streaming' after stop() runs.

- timestamp: 2026-08-02T00:15:00Z
  checked: frontend/src/components/chat/MessageList.tsx (full file)
  found: `{streamingText != null && <StreamingMessageBubble .../>}` (line 107) and `{streamingText === '' && <ThinkingBubble/>}` (line 110) — both keyed off the same `streamingText` prop that ChatPanel only nulls out when `isStreaming` becomes false.
  implication: The "thinking thing still shows" part of the report is the same root cause, not a second bug — ThinkingBubble/StreamingMessageBubble are downstream of the identical `status` value as the Stop button.

- timestamp: 2026-08-02T00:20:00Z
  checked: frontend/src/hooks/useChatMessages.ts (full file)
  found: |
    `stop()` (lines 134-136): `const stop = useCallback(() => { abortControllerRef.current?.abort() }, [])` — no setStatus call at all.
    `sendChatMessage`'s streamMessage(...).catch handler (lines 120-129):
    ```
    .catch((error) => {
      // An AbortError from `stop()` is expected...
      if (controller.signal.aborted) return
      setStatus({ status: 'error', ... })
    })
    ```
    This is the ONLY place a rejected streamMessage promise is handled, and it explicitly no-ops (no setStatus of any kind) whenever the abort was the caller's own doing.
  implication: After stop() is clicked, there is no code path anywhere that moves `status` away from `{status: 'streaming', streamingText: ...}`. The state is architecturally stuck by design intent (avoid showing an error banner for a user-initiated stop) but the intent was implemented as "suppress the error" rather than "suppress the error AND still clear streaming state."

- timestamp: 2026-08-02T00:22:00Z
  checked: frontend/src/api/chat.ts streamMessage() (full function)
  found: The `for (;;) { const { done, value } = await reader.read(); ... }` read loop (lines 137-149) has no try/catch around `reader.read()`. Aborting the fetch's AbortSignal causes the pending `reader.read()` call to reject with a DOMException named 'AbortError' (standard Streams/Fetch spec behavior), which propagates out of `streamMessage` as a promise rejection — exactly the rejection caught (and no-op'd) in useChatMessages.ts's `.catch`.
  implication: Confirms the exact mechanism — clicking Stop reliably produces an AbortError rejection that reaches the no-op branch, which is why the backend generation genuinely stops (the fetch is aborted) while the frontend state does not update.

- timestamp: 2026-08-02T00:25:00Z
  checked: frontend/src/hooks/useChatMessages.test.tsx, test "stop() aborts the in-flight stream via AbortController without an unhandled rejection" (lines 93-122)
  found: The test only asserts `expect(capturedSignal?.aborted).toBe(true)` after calling `stop()` — it never asserts anything about `result.current.status` post-abort. There is no test anywhere in this file (or in ChatPanel's test suite, not separately re-checked here since the mechanism is already fully confirmed) that asserts the Stop button/streaming indicator clears after stop().
  implication: Corroborating evidence — the existing regression test's own scope silently stops short of the exact behavior the UAT gap is about, which is consistent with (and explains why nobody caught) this being unfixed: the test suite verifies "no crash on abort" but not "UI unstickers on abort."

## Resolution

root_cause: "useChatMessages.ts's stop() (frontend/src/hooks/useChatMessages.ts:134-136) only calls `abortControllerRef.current?.abort()`; it does not itself update `status`. The one place that handles the resulting rejected streamMessage() promise — the `.catch` in sendChatMessage (useChatMessages.ts:120-129) — deliberately no-ops (`if (controller.signal.aborted) return`) instead of transitioning `status` out of `{status: 'streaming', ...}` after a user-initiated stop. Since ChatPanel.tsx's Stop-button visibility (isStreaming) and MessageList.tsx's Thinking/Streaming bubble are both derived solely from that same `status` field, both remain stuck showing 'streaming' UI indefinitely after Stop is clicked, even though the underlying fetch/generation has actually been aborted."
fix: "(not attempted — find_root_cause_only mode)"
verification: "(not attempted — find_root_cause_only mode)"
files_changed: []
