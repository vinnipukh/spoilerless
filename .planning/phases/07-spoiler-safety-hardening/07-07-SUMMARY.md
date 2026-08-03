---
phase: 07-spoiler-safety-hardening
plan: 7
subsystem: full-stack
tags: [spoiler-safety, chat, graphrag, changeset, propose-tool]

# Dependency graph
requires:
  - phase: 07-02
    provides: effective-boundary progress resolution (ProgressService.resolve)
  - phase: 07-04
    provides: defense-in-depth _visible_at context drop (pipeline)
  - phase: 07-03
    provides: view_as_of_order frontend model
provides:
  - 12th allowlisted tool `propose_changeset` (pipeline.py, schema + executor + model registration — 10 references): reuses domain/change_set.py op models + summary; persists a ChangeSet DRAFT via ChangeSetService.propose at the effective boundary (D-13, never LLM-chosen visibility); nothing applies until the user confirms via the existing ChangeSetCard flow
  - services/chat.py done-envelope: proposed_change_set carries the tool result (hardcoded None removed — grep == 0)
  - Stale ChangeSet apply compares against the CURRENT effective boundary -> 409 changeset_stale (EDIT-02); hidden/cross-series targets rejected (EDIT-01); payload schema gains no client visibility field (grep-verified)
  - get_session_detail already resolves the effective boundary server-side and filters messages; frontend now refetches on view change (useChatMessages boundary key, threaded App -> ChatSheet -> ChatPanel) — above-boundary messages hide on earlier-view, return on re-view, session never destroyed (CHAT-02, D-12)
  - App clear-focus effect already fires on view-only changes (confirmedOrder == view since 07-03) — stale graph/citation focus cleared
affects: [07-08 regression]

# Tech tracking
tech-stack:
  added: []
  changed: [backend/app/retrieval/pipeline.py, backend/app/services/chat.py, backend/app/repository/change_set.py, backend/app/services/change_set.py, backend/tests/test_chat_persistence.py, backend/tests/test_prompt_injection.py, frontend/src/hooks/useChatMessages.ts, frontend/src/components/chat/ChatPanel.tsx, frontend/src/components/chat/ChatSheet.tsx, frontend/src/App.tsx, frontend/src/components/detail/DetailPanel.tsx]
  removed: []
  pinned: []

# Summary
The chat surface now runs entirely at the effective boundary and the
assistant can finally propose graph edits. The new propose_changeset tool
(reused the existing ChangeSet op models, never new shapes) persists a draft
stamped at the effective view; the done-envelope carries it and the existing
ChangeSetCard confirm flow renders it — the missing capability from the
user's "can you add relationships?" test. ChangeSet staleness fails closed
against the effective boundary (409 changeset_stale) and the frontend
refetches chat messages whenever the view changes, hiding above-boundary
messages without destroying sessions. The system prompt prose was never
touched — the capability is advertised via the tool description only.

# Tests
## New / modified
- test_chat_persistence.py: upsert calls updated for the 07-02 progress-split signature (b041033)
- test_prompt_injection.py: framing-test fixtures carry visible_from_order 1 (07-04 defense-in-depth drop compat)
- Backend suites (117 passed combined): test_change_set_api (incl. D-13 snapshot == 1 at boundary 1, line 359), test_change_set_confirmation, test_chat_api, test_chat_persistence, test_retrieval_pipeline, test_prompt_injection, test_retrieval_tools

## Verification (canonical invocations)
- Backend: unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_change_set_api.py backend/tests/test_change_set_confirmation.py backend/tests/test_chat_api.py backend/tests/test_chat_persistence.py backend/tests/test_retrieval_pipeline.py backend/tests/test_prompt_injection.py -q => 77 passed (117 with retrieval_tools)
- Frontend: NODE_ENV=test CI=1 npx vitest run => 186 passed (26 files); npx tsc -b clean
- Acceptance greps: `grep -c "propose_changeset" backend/app/retrieval/pipeline.py` = 10 (>= 2); `grep -c "proposed_change_set=None" backend/app/services/chat.py` = 0; `grep -c "ChangeSetStale" backend/app/repository/change_set.py` = 8 (>= 1); system_prompt.py prose untouched; contract suites green

# Status
Complete. Commits: 67f4a58 (propose_changeset tool + envelope wiring), b041033 (test fix), cf59fa3 (effective-boundary staleness), plus orchestrated completion (frontend boundary refetch + prompt-injection fixture fix + DetailPanel type fix). Executor died at 429 twice; orchestrator finished Tasks 1/3 verification + SUMMARY.
