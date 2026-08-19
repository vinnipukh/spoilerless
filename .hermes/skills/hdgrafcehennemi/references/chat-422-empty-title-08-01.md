# Chat 422 root cause — empty session title (08-01)

Symptom: user cannot send chat messages. Backend log: ~14× `POST
/api/series/series_dexter/chat/sessions` → 422 Unprocessable Content while
`GET .../sessions` → 200 and NO message-stream POSTs ever appear.

## Payload vs model

- Frontend sends `{"title": ""}` — `frontend/src/components/chat/ChatPanel.tsx`
  line 124 (`handleNewConversation`) and line 162 (`handleSend` create-first
  path): `createChatSession(seriesId, '')`; serialized by
  `frontend/src/api/chat.ts` (`body: { title }`) via `apiFetch`.
- Backend requires non-empty: `backend/app/domain/chat.py` lines 76-77
  (`ChatSessionCreateRequest.title: Field(min_length=1, max_length=200)` on
  `StrictModel`, whose config is `extra="forbid", str_strip_whitespace=True`
  at `backend/app/domain/user_content.py:88-89`). Route binds it at
  `backend/app/api/chat.py:54-70`.

## Empirical validation (run from REPO ROOT, read-only)

```
{'title': ''}    -> 422: string_too_short | loc=('title',) | msg=String should have at least 1 character
{'title': '   '} -> 422: string_too_short   (stripped to empty)
{'title': 'probe'} -> OK
```

Command: `uv run --project backend python -c "from backend.app.domain.chat
import ChatSessionCreateRequest; ChatSessionCreateRequest.model_validate({'title':''})"`

## Why it repeats & why CI was green

- Live DB had 0 `ChatSession` nodes → list GET returns 200 `[]` → every send
  takes the create-first branch (ChatPanel.tsx:160-173) → 422 → the catch at
  ChatPanel.tsx:167-171 silently restores the draft. User retries; each retry
  is one more 422.
- Backend tests POST real titles (`test_chat_api.py` `_create_session`,
  lines 199-204); frontend `ChatPanel.test.tsx:11` MOCKS `createChatSession`
  and line 124 asserts `toHaveBeenCalledWith('series_dexter', '')` — the
  mocked assertion enshrines the contract violation. Neither side exercises
  the real empty-title round-trip.

## Second wall behind the 422

- Live DB had 0 `UserSeriesProgress` nodes → `/messages/stream` pre-check
  `service.ensure_progress_exists` (api/chat.py:204-208) raises
  `ProgressNotFoundError` → 404 `resource_not_found` until the user picks an
  episode (App.tsx:216-220 → `updateProgress`); `useWatchProgress` never
  auto-creates it.
- LLM was NOT the blocker: stored `:AppSetting {key:'llm'}` =
  `{provider: openai_compatible, base_url: https://api.deepseek.com,
  model: deepseek-v4-flash, enabled: true}`. Proof the real provider path
  works: `test_disabled_provider_returns_503_never_401` returned **200**
  in that live-DB state (it performed a real DeepSeek round-trip).

## Tests run

- `cd backend && uv run pytest tests/test_chat_api.py tests/test_chat_persistence.py -q`
  → 28 passed, 1 failed (`test_disabled_provider_returns_503_never_401`,
  live-DB settings contamination — see runbook Live-DB hygiene).
- `cd frontend && NODE_ENV=test CI=1 npm run test -- ChatPanel useChatSessions`
  → 18/18 passed (all mocked — does not cover the real payload).

## Minimal fixes

- FE (required): non-empty title at ChatPanel.tsx:124 + :162; update the
  assertion at ChatPanel.test.tsx:124.
- BE (defensive): `title: str = Field(default='', max_length=200)` in
  domain/chat.py + `title.strip() or 'New conversation'` in
  `ChatRepository.create_session` (repository/chat.py:56-68).
- Progress wall: user must select an episode first; optionally auto-create
  progress at order 1 (product decision).

## Fix status (08-01, ALL LANDED — supercedes the above)

- FE: `ChatPanel.tsx` now sends `'New conversation'` at both call sites;
  `ChatPanel.test.tsx` mock title + `toHaveBeenCalledWith('series_dexter',
  'New conversation')` updated.
- BE model: `title: str = Field(default='', max_length=200)`; repo
  `create_session` persists `title.strip() or "New conversation"`.
- BE progress: `ChatService._resolve_or_create_progress()` (resolve, else
  `upsert(..., 1)` + return 1) replaces the fail-closed `resolve` on the
  chat message paths; `ensure_progress_exists` renamed
  `ensure_progress_for_chat` (SSE pre-check call site updated). Session
  not-found/foreign-session stays the only 404.
- BE tests: `test_message_without_progress_returns_generic_404` →
  `..._auto_creates_order_1_progress` and
  `test_stream_message_without_progress_returns_404_not_a_broken_stream` →
  `..._auto_creates_order_1_progress` (assert 200 + `GET /progress` shows 1);
  new `test_empty_title_creates_session_with_default_title` (empty +
  whitespace → 201 'New conversation').
- FE papercut: `ApiError` constructor (api/client.ts) normalizes FastAPI's
  array-shaped 422 `detail` (code `'invalid_request'`, message from
  `detail[0].msg`) — covers both throw sites (client.ts, api/chat.ts stream).

### Verification (all green on 08-01)

- `NODE_ENV=test CI=1 npm run test -- ChatPanel useChatSessions` → 18/18;
  full frontend suite → 165 passed / 23 files; `npx tsc -b` clean.
- `uv run pytest tests/test_chat_api.py tests/test_chat_persistence.py
  tests/test_settings_api.py -q` → 32 passed, 1 failed (the documented
  live-DB `test_disabled_provider_returns_503_never_401` — settings
  contamination, not a regression).
- Full backend suite (stash technique): baseline 321 passed / 5 failed /
  7 errors → with changes 322 / 5 / 7; failure/error NAME SETS identical
  (+1 passed = the new title test).
- Note: full-suite runs are order/state-dependent on the live DB — one run
  showed 40 errors (`test_user_content_api.py` parametrized tests erroring
  while passing in isolation); re-run once before investigating; the stash
  technique is the arbiter.
