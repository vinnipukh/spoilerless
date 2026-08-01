---
status: complete
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
source: [06-01-SUMMARY.md ... 06-12-SUMMARY.md, 06-MANUAL-ACCEPTANCE.md]
started: 2026-08-01T22:40:00Z
updated: 2026-08-01T19:45:58Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 9
name: Settings persistence
expected: |
  After saving provider/API key/config and logging out and back in, Settings still shows the stored config with the masked key ("••••1234 (stored — leave blank to keep)") — no re-entry needed.
awaiting: user response

## Tests

### 1. Login and authed endpoints
expected: Signing in with Google returns you to the app; chat, settings, and graph progress endpoints no longer return 401. Opening the chat sheet and the Settings page shows live data instead of auth errors.
result: pass

### 2. Chat session auto-creation
expected: In the chat sheet, sending a first message (or clicking "New conversation") creates a session titled "New conversation". No 422 validation error appears; the session appears in the session list.
result: issue
reported: "UI said there was a problem until I sent 3 messages; the first messages errored, the 3rd worked."
severity: major

### 3. Send a message, get an answer
expected: Sending a question like "Who is Dexter Morgan?" streams a real answer from the LLM (DeepSeek) into the chat — no "Failed to load/save LLM settings", no silent empty reply.
result: issue
reported: "Got \"Something went wrong answering that. Try rephrasing your question.\" AND an answer came in. Hypothesis: while the app waits for the API to respond, the frontend shows a wrong (premature) error message."
severity: major
artifacts: [frontend/src/components/chat/MessageBubble.tsx:103 FailedMessageBubble non-retryable copy]

### 4. Stop generating button
expected: While the answer streams, a Stop button is visible. When the answer completes (or fails), the Stop button disappears. It never stays stuck after the stream ends.
result: issue
reported: "Stop button works but the premature error persists — the \"Something went wrong answering that. Try rephrasing your question.\" message shows for ~5s while the previous turn is still being answered."
severity: blocker
artifacts: [frontend/src/components/chat/ChatPanel.tsx:40-45 classifyChatError, ChatPanel.tsx:154-179 handleSend, api/chat.py ConcurrentGenerationLimitExceeded]

### 5. Conversational tone
expected: Asking "How do you feel about Dexter's future?" returns a warm, friendly interpretation grounded in watched content (visible events/relationships), with clearly marked speculation. It never returns the robotic "The watched graph does not contain enough information to answer that."
result: pass

### 6. Assistant language selector
expected: Settings → Assistant language → "Türkçe (Turkish)" → Save → chat answers in Turkish. Switching back to English → chat answers in English. The choice persists after reload.
result: pass

### 7. Resizable chat sheet
expected: Dragging the chat panel's left edge resizes it (wider/narrower, clamped). The chosen width persists after reload; double-clicking the edge restores the default width.
result: pass

### 8. Graph refresh after relationship creation
expected: In the node inspector, Create relationship → pick target + predicate → Create. The new edge appears on the graph immediately (dashed) without a manual page reload.
result: pass

### 9. Settings persistence
expected: After saving provider/API key/config and logging out and back in, Settings still shows the stored config with the masked key ("••••1234 (stored — leave blank to keep)") — no re-entry needed.
result: pass

## Summary

total: 9
passed: 6
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "In the chat sheet, sending a first message (or clicking New conversation) creates a session titled New conversation. No 422 validation error appears; the session appears in the session list."
  status: failed
  reason: "User reported: UI said there was a problem until I sent 3 messages; the first messages errored, the 3rd worked."
  severity: major
  test: 2
  artifacts: []
  missing: []
- truth: "Sending a question streams a real answer from the LLM into the chat — no failure message, no silent empty reply."
  status: failed
  reason: "User reported: Got \"Something went wrong answering that. Try rephrasing your question.\" AND an answer came in. Hypothesis: while the app waits for the API to respond, the frontend shows a wrong (premature) error message."
  severity: major
  test: 3
  artifacts: [frontend/src/components/chat/MessageBubble.tsx:103]
  missing: []
- truth: "While the answer streams, a Stop button is visible; when it completes the button disappears and no spurious error appears."
  status: failed
  reason: "User reported: premature \"Something went wrong answering that. Try rephrasing your question.\" shown ~5s while the previous turn is still being answered (concurrent-slot 429 misclassified as non-retryable; no waiting feedback so users resend)."
  severity: blocker
  test: 4
  artifacts: [frontend/src/components/chat/ChatPanel.tsx:40-45, ChatPanel.tsx:154-179, backend/app/api/chat.py ConcurrentGenerationLimitExceeded]
  missing: []
- truth: "User-created edges appear on the right part of the screen after creation (placement looks off)."
  status: failed
  reason: "User reported: Though it shows up on the right part of the screen (user created edges)"
  severity: minor
  test: 8
  artifacts: []
  missing: []
