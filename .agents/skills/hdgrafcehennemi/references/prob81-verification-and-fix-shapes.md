# PROB-09 open-#NN sweep — verification protocol & #81-tail fix shapes (2026-08-12)

Session: read all of PROBLEMS.md, verified every "still open" item live, fixed the
safe #81-tail items. **COMPLETED + COMMITTED** (commits `ff65c50`, `76aa215`,
`59cd9ce`); FOURTEENTH PASS appended to PROBLEMS.md. Verification results below.

## Ledger verification protocol (extend THIRTEENTH-pass ledger-staleness)

The "Still open" list is stale in BOTH directions:

1. **Sibling commits pre-fix items without appending passes.** #81 tail "FE
   export-fallback dedup" was ALREADY DONE — both GraphCanvas.tsx and
   DetailPanel.tsx import `renderGraphMarkdown`/`exportFilename` from
   `@/lib/exportMarkdown` + `downloadMarkdownBlob` from `@/api/export`. No
   inline fallback remains.
2. **Finding identifiers drift from live names.** The #81 "operationTargetRefs"
   duplication exists but under DIFFERENT names: `focusTargetsForAppliedChangeSet`
   (App.tsx) + `affectedRefsFor` (ChangeSetCard.tsx). Grep the finding's CONCEPT
   (operation→ids switch shape, file:line behaviors), not its identifiers — a
   zero-hit grep on the finding's name proves nothing.

Verification order that worked: `git log --oneline -5` (unrecorded sibling
commits) → `git status --short` (expect uncommitted docs/sibling work — don't
commit it) → `wc -l` on named god-files → grep by concept across
`spoilerless/app` + `frontend/src` (use terminal `grep -rn` from repo cwd;
search_files tool failed on absolute Windows paths this session).

Also check BOTH directions of each deferred item: `verify_origin "*"` bypass is
deliberate (documented) — skip; DEXTER tier table deferred (backend payload
change, cross-stack); settings blank-key already handled in services/settings.py.

## #81-tail fix shapes (applied, uncommitted)

1. **operationTargetRefs** — `frontend/src/types/changeSet.ts`: shared
   `OperationRef = {id, kind}` + `operationTargetRefs(op): OperationRef[]`
   (superset incl. create_relationship endpoints). ChangeSetCard:
   `current.operations.flatMap(operationTargetRefs)`. App's
   focusTargetsForAppliedChangeSet: one-line `create_relationship` skip +
   kind-based split (`kind === 'Relationship'` → edgeIds else nodeIds).
   KEY: the two original switches had DIFFERENT semantics (App excluded
   create_relationship endpoints, ChangeSetCard included them). Shared superset
   + per-site filter preserves 1:1 behavior. Before dedup, read the
   count-asserting test fixtures ("Highlighting 1" with a single create_note op
   → safe; a create_relationship fixture would have changed the count).
2. **CitationChip lean variant** — discriminated union props:
   `{label, onOpenDetail?} | {citation, onShowInGraph?, onOpenDetail?}`; render
   branches on `'label' in props`. ChangeSetCard passes `label={`${kind} · ${id}`}`
   — kills the fake Citation (`episode_code: ref.id`) contract abuse. Renders
   identical text, zero tests touched.
3. **nodeTypes single registry** — `lib/nodeTypes.ts`:
   `CUSTOM_NODE_TYPE_NAMES as const` → `type CustomNodeType`; `ALLOWED_NODE_TYPES`
   filtered from `NODE_TYPES`; `types/userContent.ts` re-exports the type
   (import path preserved). GraphCanvas: delete local ALLOWED_NODE_TYPES (import
   it), `allNodeTypes = NODE_TYPES.map(nt => nt.type)` (adds UserNote key
   default-true — SAFE: the prune iterates map entries only, missing keys stay
   visible). GraphFilterPanel already consumed NODE_TYPES directly.
4. **share models → domain** — `ShareCreateRequest/Response` + `ShareItemResponse`
   moved to `domain/share.py`; `api/share.py` imports them (Annotated/pydantic
   imports dropped); dead `ShareTokenCreate` deleted (1 unused test import —
   fix test_share_api.py import line). Note: the #81 "tri-mode revoke" claim is
   half-false at HEAD — only raw-token + hash lookups exist (no get_by_id).

## Verification gotchas (discovered completing this sweep)

- **TS re-export does NOT bind locally.** `export type { X } from '../lib/foo'`
  alone → `TS2304: Cannot find name 'X'` at local uses. Need BOTH
  `import type { X } from ...` AND `export type { X } from ...`. Conversely,
  deleting a local type while a same-name re-export exists → `TS2484: Export
  declaration conflicts` — delete the old definition, keep one re-export.
- **Unused type-only import** → `TS6196` (`'OperationRef' is declared but never
  used`) — drop the type import when the shared helper's return type is
  inferred (flatMap result).
- **Docker engine can die mid-session** (Docker Desktop restarts/shuts down):
  `docker ps` fails or shows `hdgraf-neo4j Exited (137)`. Live-DB tests then
  error at fixture setup with `ConnectionRefusedError ... ::1:7687` — NOT a
  code failure. Recovery: relaunch Docker Desktop (Windows GUI), wait for the
  daemon, `docker start hdgraf-neo4j`, re-run. In-memory-repo route tests pass
  either way — use them to prove a failure is environmental before restarting.
- Doc-claim checkers exist OUTSIDE pytest: `run_doc_verification.py` +
  `verify_arch.py` (repo root, untracked). After ANY docs/ARCHITECTURE.md edit,
  run `unset PYTHONPATH && .venv/Scripts/python.exe run_doc_verification.py` —
  this session: 276/276 claims passed post-edit.

## Results (all verified, then committed)

- FE: `tsc -b` clean, eslint clean on touched files, full vitest **333/333**
  (incl. App "Highlighting 1" post-apply focus + CitationChip suite).
- BE: `test_share_api.py` 5/5; full local-docker suite **591 passed / 1
  skipped / 0 failed** (~2m) — documented green baseline unchanged.
- Docs: ARCHITECTURE.md 3 stale route-layer claims rewritten post-#60/#70
  (verified against live `api/candidates.py` `graph/candidates.py`
  `api/revisions.py` first); API.md had no stale text.
- Commits: `ff65c50` (FE: operationTargetRefs + CitationChip + nodeTypes),
  `76aa215` (share models → domain), `59cd9ce` (docs + FOURTEENTH PASS).

## Ledger append (FOURTEENTH PASS, docs/PROBLEMS.md)

Recorded: 4 fixes + corrections (exportMarkdown dedup already landed by sibling
commit; `ShareTokenCreate` dead — revoke lookup is 2-mode at HEAD not tri-mode;
nodeTypes UserNote default-true safe because the prune iterates map entries
only). Deferred w/ rationale: #19, #79 remainder, #29/#36 operator-touch,
DEXTER tier, useNotes provider, settings typed fields, verify_origin `"*"`
deliberate.
