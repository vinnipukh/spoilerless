---
phase: 08-production-deployment-automated-ci-cd
plan: 02
subsystem: ui
tags: [byok, llm, localStorage, react, vitest, chat]

# Dependency graph
requires:
  - phase: 07-spoiler-safety-hardening
    provides: GraphRAG chat endpoints (sessions/messages/stream) that the X-LLM-* header attachment targets
provides:
  - Browser-held LLM provider settings (localStorage) with per-request X-LLM-* headers (frontend BYOK, D-06)
  - SettingsPage rewritten to localStorage-only persistence (no network save, no settings-persistence endpoint call)
  - streamMessage raw fetch URL prefixed with VITE_API_BASE_URL
affects: [08-03 (admin gating of /api/settings/llm), 08-01 (client.ts VITE_API_BASE_URL wiring), chat UX]

# Tech tracking
tech-stack:
  added: []
  patterns: [BYOK settings module with typed localStorage read/write + header builder]

key-files:
  created: [frontend/src/lib/byok.ts]
  modified: [frontend/src/components/settings/SettingsPage.tsx, frontend/src/api/chat.ts, frontend/src/types/settings.ts, frontend/src/components/settings/SettingsPage.test.tsx, frontend/src/api/chat.test.ts, frontend/src/App.test.tsx]
  deleted: [frontend/src/api/settings.ts]

key-decisions:
  - "LLM settings are browser-only: localStorage key 'hdgraf:byok-llm-settings', the frontend never calls a settings-persistence endpoint"
  - "getLLMHeaders() emits X-LLM-Api-Key always and X-LLM-Base-URL/X-LLM-Model only when non-blank (backend treats blank header values as absent)"
  - "Deleted frontend/src/api/settings.ts (getLLMSettings/updateLLMSettings) - no remaining references after the rewrite"

patterns-established:
  - "BYOK: typed localStorage module (getStoredLLMSettings/saveLLMSettings) + getLLMHeaders() spread into request headers"

requirements-completed: [AI-01, AI-02, AI-03]

# Coverage metadata (#1602) - per-deliverable traceability for verify-work routing.
coverage:
  - id: D1
    description: "BYOK settings stored in browser localStorage; SettingsPage save is localStorage-only with no network request"
    requirement: AI-01
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/SettingsPage.test.tsx#saves provider + api key to localStorage only - no network request fires"
        status: pass
    human_judgment: false
  - id: D2
    description: "Chat requests (send + stream) carry X-LLM-Api-Key/X-LLM-Base-URL/X-LLM-Model headers when a key is stored, omitted otherwise"
    requirement: AI-01
    verification:
      - kind: unit
        ref: "frontend/src/api/chat.test.ts#sendMessage attaches X-LLM-* headers when a key is stored"
        status: pass
      - kind: unit
        ref: "frontend/src/api/chat.test.ts#streamMessage attaches X-LLM-* headers when a key is stored"
        status: pass
    human_judgment: false
  - id: D3
    description: "Backend builds the LLM provider per-request from X-LLM-* headers with env fallback (Task 1)"
    requirement: AI-01
    verification:
      - kind: unit
        ref: "backend/tests/test_chat_api.py (28/28, Task 1, verified by orchestrator)"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-08-04
status: complete
---

# Phase 08: Production Deployment & Automated CI/CD — Plan 08-02 Summary

**BYOK LLM chat shipped end-to-end: request-scoped backend provider from X-LLM-* headers (Task 1) plus browser-only localStorage settings and header attachment in the frontend (Task 2) — the browser-held key never touches a persistence endpoint, log line, or datastore.**

## Performance

- **Duration:** ~45 min (Task 1 by prior executor; Task 2 ~30 min)
- **Started:** 2026-08-04 (phase)
- **Completed:** 2026-08-04
- **Tasks:** 2
- **Files modified:** 8 (+1 deleted)

## Accomplishments
- Backend: request-scoped BYOK LLM provider built exclusively from X-LLM-Api-Key / X-LLM-Base-URL / X-LLM-Model headers with env fallback; header-supplied key never persisted or logged (Task 1, 28/28 chat API tests)
- Frontend: `frontend/src/lib/byok.ts` localStorage module (key `hdgraf:byok-llm-settings`) with `getStoredLLMSettings()` (never throws) / `saveLLMSettings()` (trims all fields) and `getLLMHeaders()`
- SettingsPage rewritten to localStorage-only: populates the form from stored settings on mount, Save writes localStorage and shows "Saved to this browser." with no network call; dropped `system_prompt_language` and enable-chat-assistant fields; added privacy copy ("key never leaves this browser except as a per-request header")
- sendMessage and streamMessage now spread `getLLMHeaders()` into request headers; streamMessage's raw fetch URL is prefixed with `import.meta.env.VITE_API_BASE_URL` (default '')
- types/settings.ts reduced to BYOK-only `LLMProvider` + `StoredLLMSettings`; `frontend/src/api/settings.ts` deleted (no remaining references)

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend BYOK provider (prior executor)** - `29642ab` (test) + `cf2f685` (feat)
2. **Task 2: Frontend BYOK** - `7665168` (feat) + `7e7e025` (test)
3. **Plan metadata** - `d3a6f9c` (docs: create plan)

## Files Created/Modified
- `frontend/src/lib/byok.ts` - NEW: localStorage BYOK settings module + getLLMHeaders()
- `frontend/src/components/settings/SettingsPage.tsx` - Rewritten: localStorage-only read/save, no network, dropped stale fields, privacy copy
- `frontend/src/api/chat.ts` - sendMessage/streamMessage attach X-LLM-* headers; streamMessage URL prefixed with VITE_API_BASE_URL
- `frontend/src/types/settings.ts` - Trimmed to LLMProvider + StoredLLMSettings (BYOK-only)
- `frontend/src/api/settings.ts` - DELETED (getLLMSettings/updateLLMSettings had no remaining references)
- `frontend/src/components/settings/SettingsPage.test.tsx` - Rewritten to the localStorage contract
- `frontend/src/api/chat.test.ts` - Added X-LLM-* header attach/omit tests; stream URL expectations track VITE_API_BASE_URL
- `frontend/src/App.test.tsx` - Seeds BYOK localStorage for the settings-toggle test (form no longer GETs /api/settings/llm)

## Decisions Made
- Blank base_url/model headers are omitted rather than sent empty — the backend treats blank header values as absent (`(x or "").strip()` + truthiness), preserving env fallback while matching the "when present" contract
- Kept the provider select field in SettingsPage (informational UI + stored provider) even though getLLMHeaders() sends no provider header (backend fixes the BYOK provider type to openai_compatible)

## Deviations from Plan

### Test-infra repair (specified in task scope)

**1. [Rule 3 - Blocking] Frontend tests rewritten to the new BYOK contract**
- **Found during:** Task 2
- **Issue:** SettingsPage.test.tsx mocked @/api/settings and asserted the old PUT flow; chat.test.ts had no header expectations and pinned the un-prefixed stream URL; App.test.tsx's settings-toggle test relied on the server GET stub
- **Fix:** Rewrote SettingsPage.test.tsx (localStorage save, no fetch fires, key never echoed into a network call, stale fields absent, trim behavior, privacy copy); extended chat.test.ts (X-LLM-* attached when key stored, omitted when none or whitespace-only, blank base_url/model omitted, stream URL computed from the same VITE_API_BASE_URL expression the source uses); App.test.tsx settings-toggle test seeds localStorage
- **Files modified:** frontend/src/components/settings/SettingsPage.test.tsx, frontend/src/api/chat.test.ts, frontend/src/App.test.tsx
- **Verification:** full frontend vitest suite 192/192 pass (NODE_ENV=test CI=1)
- **Committed in:** 7e7e025

### Auto-fixed Issues

**2. [Rule 3 - Blocking] `mockStreamResponse` was scoped inside a describe while the new BYOK tests needed it**
- **Found during:** Task 2 test updates
- **Issue:** helper not visible to the BYOK header tests
- **Fix:** hoisted to module scope in chat.test.ts
- **Verification:** targeted + full vitest suites pass
- **Committed in:** 7e7e025 (part of test commit)

---

**Total deviations:** 2 auto-fixed (both test-infra)
**Impact on plan:** Test updates are exactly the new-contract repairs the task specified; no production-code deviation, no scope creep.

## Issues Encountered
- `frontend/src/api/settings.ts` existed only as an untracked working-tree file (HEAD's SettingsPage.tsx imported '@/api/settings' but git never tracked the module) — deleting it and dropping the import in the rewrite resolves the pre-existing inconsistency
- `frontend/.env.example` still sets `VITE_API_BASE_URL=/api` while `frontend/src/api/client.ts` ignores the variable entirely. streamMessage now reads it, so with the current `/api` value the stream URL would double-prefix. Plan 08-01 owns client.ts and the deploy env wiring — it must normalize VITE_API_BASE_URL to an origin (e.g. https://api.<domain>) or empty. sendMessage (via apiFetch/client.ts) is intentionally NOT prefixed and remains dependent on 08-01's client.ts work.

## User Setup Required
None - no external service configuration required (keys are entered by end users in the browser Settings UI).

## Next Phase Readiness
- 08-03 (admin role) can gate or retire the still-live backend GET/PUT /api/settings/llm endpoint; the frontend no longer calls it
- 08-01 must wire VITE_API_BASE_URL into client.ts and normalize .env.example so hosted frontend/backend origins match the streamMessage prefix

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
