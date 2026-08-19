# 09-06 — chat/LLM cluster: PROB-13/#35, PROB-24/#48, PROB-28/#52

Executed 2026-08-05 on main; commits `539a583` (Task 1), `1de9eb0` (Task 2),
`15649cb` (Task 3). All verification FakeLLMProvider / httpx.MockTransport —
zero live LLM spend. Test counts: test_chat_api.py 29 passed (~2.5–3 min, live
local Neo4j with per-run env overrides), test_retrieval_pipeline.py 15,
test_llm_provider.py 12, test_conversational_tone.py 10 (2 dead detect_language
tests deleted), fast combined suite (pipeline+llm+tone+citations+prompt_injection)
59 passed, test_chat_persistence.py 6. Frontend: chat vitest 11 files / 85 tests
green (`NODE_ENV=test CI=1`), `npm run build` typecheck green. Grep gates:
`rg -n detect_language spoilerless/` = 0, `rg -n "notes=\[\]" pipeline.py` = 0.

## Task 1 — failure status + logged exceptions (PROB-13/#35)

Files: domain/chat.py, graph/chat.py, repository/chat.py, services/chat.py,
api/chat.py, tests/test_chat_api.py.

- `MessageStatus(StrEnum)` in domain/chat.py: PENDING="pending",
  COMPLETED="completed", FAILED="failed". NOTE: the plan suggested "complete"
  but the repository had hardcoded `status="completed"` for every message —
  inspect the persisted convention first and keep the existing value so
  legacy rows validate. `ChatMessageResponse.status` defaults to COMPLETED
  (old rows without the property still validate).
- graph/chat.py: `message.status AS status` must be added to the RETURN of
  CHAT_MESSAGE_LIST_QUERY AND CHAT_MESSAGE_CREATE_QUERY — the response model
  needs it; a missing RETURN column = ValidationError on list/validate.
  New CHAT_MESSAGE_STATUS_UPDATE_QUERY: owner-scoped MATCH + SET (zero rows =
  silent no-op for foreign/missing messages).
- services/chat.py `answer_stream` lifecycle:
  1. persist user message with `status=MessageStatus.PENDING` before generation;
  2. after assistant message persists, `update_message_status(..., COMPLETED)`,
     build envelope, set `turn_completed = True`, THEN `yield done`;
  3. `except BaseException` (NOT Exception — must catch GeneratorExit on client
     disconnect): if `user_message is not None and not turn_completed` → mark
     FAILED, swallow that write's errors (`# noqa: BLE001`), re-raise;
  4. `if final_done is None: raise LLMProviderUnavailable(...)` after the
     pipeline loop (was `AttributeError` on `final_done.citations`).
  - The `turn_completed` flag is the subtle bit: `aclose()` after the done
    chunk was yielded raises GeneratorExit AT the done yield — without the
    flag a successfully completed turn gets wrongly marked failed.
- api/chat.py `event_stream`: `logger = logging.getLogger(__name__)`; BOTH
  `except LLMProviderUnavailable as exc` and `except Exception as exc` call
  `logger.exception("Chat stream failed mid-turn (session=%s): %s: %s",
  session_id, type(exc).__name__, exc)` BEFORE yielding the generic error
  event. caplog captures these across TestClient's portal thread (ERROR level
  propagates to the root handler).
- Test pattern: `MidStreamCrashProvider` yields one text_delta then raises
  RuntimeError. Assert: (a) session detail shows ONLY the user message with
  `status == "failed"`, (b) `caplog.text` contains exception class + message,
  (c) SSE `event: error` with code LLM_STREAM_FAILED and no done event.
  Happy path: both messages `status == "completed"` (added to the existing
  citation test).

## Task 2 — notes bucket (PROB-24/#48)

Files: retrieval/pipeline.py, tests/test_retrieval_pipeline.py. tools.py
UNCHANGED — user_id threading already existed in `_execute_tool_call`.

Root cause: `get_user_notes` returns a bare list; `_accumulate`'s list branch
wraps ANY bare list as `{"nodes": result}` → note rows were mis-bucketed into
the entities section and `<notes>` always rendered "(none)".

- `retrieved` init gains `"notes": []`.
- `_execute_tool_call` get_user_notes branch: `result = {"notes": notes}`
  (wrap at the call site, NOT in tools.py — keeps the tool's public shape and
  test_retrieval_tools.py untouched).
- `_accumulate`: `seen_notes` set + append into `retrieved["notes"]` mirroring
  the other buckets (reads `result.get("notes")`).
- `_finalize`: `notes=retrieved["notes"]` (was hardcoded `notes=[]`).
- `_StubDatabase` routing: USER_NOTES_QUERY contains "REFERS_TO" which already
  routes source_rows — routing is FIRST MATCH by dict insertion order, so add
  the distinctive marker `"note.user_id = $user_id": note_rows or []` BEFORE
  "SUPPORTED_BY"/"REFERS_TO" in `self._rows`.
- Note-row shape from USER_NOTES_QUERY: {id, target_type, target_id, content,
  visible_from_order}; `_note_line` renders `- {content or id}`.

## Task 3 — provider edges + dead code + bounded replay (PROB-28/#52)

Files: llm/provider.py, llm/fallbacks.py, retrieval/pipeline.py,
tests/test_llm_provider.py, tests/test_retrieval_pipeline.py,
tests/test_conversational_tone.py.

- provider.py: `chunk = json.loads(data)` wrapped in try/except
  json.JSONDecodeError → `continue` (parity with GeminiProvider, which already
  skipped malformed chunks). Unit test: MockTransport body = valid chunk +
  `data: {this is not valid json` + `data: [DONE]` → events ==
  [text_delta, done], no exception escapes.
- fallbacks.py: deleted `detect_language` AND `_TURKISH_CHARS` (only used by
  it); rewrote the module docstring (the old text described the dead heuristic).
  Removed the import from retrieval/pipeline.py AND deleted the two
  detect_language tests in test_conversational_tone.py.
- GREP-GATE PITFALL: `rg -n "detect_language" spoilerless/ | wc -l` must be 0 —
  my replacement docstring saying "(``detect_language``) was deleted" kept the
  gate at 1. Gate literals must not appear anywhere in new code, docstrings
  and comments included. Reword to "the language-detection helper".
- pipeline.py bounded replay: `_MAX_TOOL_RESULT_CHARS = 4000` +
  `_bounded_tool_result(result)` = `json.dumps(result, default=str)` truncated
  to the cap + `"...[truncated]"`. Used ONLY for the model-visible tool message
  in the loop; `retrieved` keeps full rows so `_citation_survives` /
  `_enrich_citation` and assemble_context are unaffected (citation validation
  reads `retrieved`, never the messages).
- Bounded-replay test: 6000-char evidence row via get_neighborhood → final
  call's tool message ≤ cap+marker and endswith marker, evidence id still in
  the replay head, full text still in assembled context, citation validates.

## Verification commands

```bash
unset PYTHONPATH
# live-DB suite (local docker Neo4j; container is hdgrafcehennemi-neo4j):
NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j uv run pytest spoilerless/tests/test_chat_api.py -q
# stub-based fast suites:
uv run pytest spoilerless/tests/test_retrieval_pipeline.py spoilerless/tests/test_llm_provider.py spoilerless/tests/test_conversational_tone.py -q
# frontend:
cd frontend && NODE_ENV=test CI=1 npx vitest run src/components/chat src/hooks/useChatMessages.test.tsx src/hooks/useChatSessions.test.tsx src/api/chat.test.ts
cd frontend && npm run build   # canonical typecheck (tsc -b + vite build)
# grep gates:
rg -n "detect_language" spoilerless/ | wc -l   # must be 0
rg -n "notes=\[\]" spoilerless/app/retrieval/pipeline.py | wc -l   # must be 0
```
