---
phase: 09-feature-expansion-full-audit-remediation
plan: 06
type: execute
status: complete
executed_by: gsd-executor (deleg_f4428cbb) + orchestrator closeout (SUMMARY/tracking after executor budget-death)
---

# Phase 09 — Plan 09-06 Summary: Chat/LLM correctness cluster

## Objective

PROB-13/#35 (mid-stream failures orphan messages + invisible in logs),
PROB-24/#48 (get_user_notes results never enter assembled context),
PROB-28/#52 (provider JSON parity, dead code, bounded tool replay).
ZERO-COST: FakeLLMProvider only, zero live LLM calls, zero new dependencies.

## Commits

| Task | SHA | Message |
|------|-----|---------|
| 1 | `539a583` | feat(09-06): chat failure status + logged mid-stream exceptions (PROB-13/#35) |
| 2 | `1de9eb0` | feat(09-06): notes accumulator bucket feeds assemble_context (PROB-24/#48) |
| 3 | `15649cb` | feat(09-06): provider JSON parity + dead code removal + bounded tool replay (PROB-28/#52) |

## What shipped

### Task 1 — chat failure status + logged exceptions (`539a583`)
- `MessageStatus` StrEnum (pending/completed/failed) in `domain/chat.py`;
  `status` field on `ChatMessageResponse`
- `CHAT_MESSAGE_STATUS_UPDATE_QUERY` + `ChatRepository.update_message_status`
- `answer_stream` persists user message as `pending`, flips `completed` after
  the done envelope, marks `failed` on any `BaseException` (incl.
  GeneratorExit disconnect) before re-raising; raises `LLMProviderUnavailable`
  on missing `done` instead of old `AttributeError`
- `api/chat.py` logs exception class + message via `logger.exception` before
  emitting `LLM_STREAM_FAILED`/`LLM_PROVIDER_UNAVAILABLE`
- New test: `test_mid_stream_failure_marks_user_message_failed_logs_and_emits_error`
  (MidStreamCrashProvider). Deviation noted: all-success turns assert
  `status=completed`; frontend doesn't consume per-message status — no FE change.

### Task 2 — notes → context bridge (`1de9eb0`)
- `notes: []` accumulator bucket in `_accumulate` with `seen_notes` dedupe
- `_execute_tool_call` wraps `get_user_notes` results as `{"notes": [...]}` so
  the bare list is never mis-bucketed as node rows
- `_finalize` passes `notes=retrieved["notes"]` (hardcoded `notes=[]` gone)
- Two new pipeline tests incl. empty/anonymous → `(none)` section

### Task 3 — provider parity + dead code + bounded replay (`15649cb`)
- `OpenAICompatibleProvider` catches `json.JSONDecodeError` on SSE chunks
  (skip+continue, parity with GeminiProvider);
  `test_openai_provider_skips_malformed_sse_chunks`
- `detect_language` deleted from `llm/fallbacks.py`; imports removed from
  `pipeline.py` + `test_conversational_tone.py` (2 dead tests deleted)
- `_bounded_tool_result` caps replayed tool-result messages at 4000 chars with
  `...[truncated]` marker — full rows still accumulate in `retrieved` for
  context/citation validation. Bound-replay test asserts cap + intact ids +
  citations still validate.

## Verification (real runs)

- `test_chat_api.py`: 29 passed (incl. new mid-stream test)
- `test_retrieval_pipeline.py`: 15 passed (2 notes + 1 bounded-replay new)
- `test_llm_provider.py`: 12 passed (incl. malformed-chunk parity)
- `test_conversational_tone.py`: 10 passed (dead-language tests removed)
- Combined fast suite (pipeline+llm+tone+citations+prompt_injection): 59 passed
- `test_chat_persistence.py`: 6 passed
- Grep gates: `rg detect_language spoilerless/` = 0; `rg "notes=\[\]" pipeline.py` = 0
- Frontend: `NODE_ENV=test CI=1 npx vitest run` = 11 files, 85 tests passed;
  `npm run build` = typecheck + build green (pre-existing chunk-size warning only)
- All FakeLLMProvider / MockTransport — zero live LLM calls, zero new deps

## Self-Check

✅ PASS — all 3 tasks executed and committed, verification green, grep gates
clean, zero-cost respected, no `.planning/config.json` or `.env` touched.

*Completed: 2026-08-05 (executor + orchestrator closeout)*
