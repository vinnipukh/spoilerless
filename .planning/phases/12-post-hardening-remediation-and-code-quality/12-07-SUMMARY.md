---
phase: 12-post-hardening-remediation-and-code-quality
plan: 07
subagent: orchestrator-inline (executor died at 50-call cap mid-Task-2; takeover completed Tasks 2–4)
---

# Plan 12-07 Summary — FE/full-stack contract bugs (7 THERMO findings)

## What was built

All four plan tasks landed:

1. **THERMO-P1-03/P1-04/P1-06 + note targets** (commit `feat(12-07): extend NoteTargetType...` + `feat(12-07): fix episode_order comparison...`):
   - `CreateRelationshipDialog` now compares numeric `episode_order`, not lexicographic UUID ids.
   - `api/export.ts` wraps seriesId in `encodeURIComponent`.
   - Backend `NoteTargetType` extended with Event/Location/Organization/Object; `NOTE_CREATE_QUERIES` regenerated per-label from the enum at module load (single f-string template — no duplicated Cypher). DetailPanel maps `selectedNode.type` straight through for the five custom labels.
   - TS `NoteTargetType` union mirrored in `types/changeSet.ts` + re-exported from `types/userContent.ts`.

2. **THERMO-P1-05 TS contract sync**: `GraphClaim.relationship_effect: string | number | null`; `GraphResponse.effective_view_order: number` (required — backend always serializes it); `GraphEvidence.content_hash?: string | null`; `ChatMessage.status?`; `ChangeSet.revert_revision_id?: string | null`. Five inline GraphResponse test fixtures updated with `effective_view_order: 1`.

3. **THERMO-P3-08/09/10**: PathFinder clear button = `RotateCcw` + title "Clear path selection" (X stays exit); ChatPanel splits `TOO_MANY_REQUESTS` into `busy` (concurrent lock, message-matched `/concurrent/i`) vs new `rate-limited` banner ("exceeded the message rate limit"); SeriesDashboard arrow-key nav scrollIntoView via cardRefs effect; RevisionHistoryPanel refocuses panel container after revert; DetailPanel refocuses SheetContent after note delete.

4. **12-02 fallout fix (deviation, in-scope)**: two stale pins in `test_user_content_api.py` expected 422 for positive unpersisted order 4 — since 12-02 removed the raw persistence pre-checks the resolver clamps instead. Updated: malformed boundaries (0/-1/"bad"/"nope") stay 422; order 4 → 200 (notes list) / 404 hidden≡missing (custom node get).

## Verification

- Frontend: `NODE_ENV=test CI=1 npm run test` → **44 files / 404 tests passed**; `npm run build` (tsc strict) clean.
- Backend: `pytest spoilerless/tests/test_user_content_api.py -q` → **38 passed**.

## Deviations

- Executor subagent hit the 50-tool-call cap mid-Task-2 (upstream 503 during summary); orchestrator completed Tasks 2–4 inline from the verified working tree.
- ChatPanel distinguishes the two 429 conditions by error MESSAGE (backend emits identical code `TOO_MANY_REQUESTS` for both paths) — documented in-code until codes diverge.

## Self-Check: PASSED

Key files:
- frontend/src/components/detail/DetailPanel.tsx
- frontend/src/components/graph/PathFinder.tsx · ChatPanel.tsx · SeriesDashboard.tsx · RevisionHistoryPanel.tsx
- frontend/src/types/{graph,chat,changeSet,userContent}.ts · frontend/src/api/export.ts
- spoilerless/app/domain/user_content.py · spoilerless/app/repository/user_content.py
