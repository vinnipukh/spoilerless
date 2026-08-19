# THIRTEENTH wave (PROB-10, 2026-08-12) — ledger staleness + baseline closure

Session: "solve all remaining problems in PROBLEMS.md" → discovered most were
already fixed by sibling sessions with NO pass entries. Full re-verification
of all 81 items required before fixing anything.

## Ledger-staleness protocol (use before ANY PROBLEMS.md drive)

1. `git log --oneline --grep="PROB"` + `--grep="#3[0-9]|#4[0-9]|#5[0-9]"` — enumerate
   unrecorded fix commits (siblings commit `fix(...): ... (PROBLEMS #NN)` /
   `PROB-xx/#NN` without appending a pass).
2. Grep each candidate item against live code — many "open" findings are stale
   (e.g. #32 uuid4 session id, #37 None guard, #42 `google` bound in scope,
   #50 created_by on direct API, #51 revert_revision_id, #38 security headers,
   #45 ErrorBoundary — all fixed, none recorded in the ledger).
3. Only then touch code. Ledger pass entry records BOTH the unrecorded fixes
   (verified) and the new work.

## Baseline closed: 584/7 → 591 passed / 1 skipped / 0 failed

Old documented baseline (3 doc-contract + 2 seed-image + 2 seed_idempotency)
is GONE. Fixes:
- **Engine-version constraint types**: AuraDB reports `NODE_PROPERTY_UNIQUENESS`
  / `NODE_KEY`; local Neo4j 5.x Community reports `UNIQUENESS` / `KEY` for the
  same objects. Normalize: `ct["type"].replace("NODE_PROPERTY_", "") in
  ("UNIQUENESS", "KEY")`; `WHERE type IN ['NODE_PROPERTY_UNIQUENESS',
  'UNIQUENESS']` in SHOW CONSTRAINTS filters. (EIGHTH-PASS class, finally fixed.)
- **openapi_contract stale inventory**: live surface 50 ops / 37 path templates
  (was asserting 32 paths). DELETE typing rule: every DELETE is 204-no-content
  OR 200-with-body (share revoke returns `{"revoked": true}` inline schema, not
  a `$ref`). Assert `"schema" in content`, not `$ref` presence.
- **non-goal rot**: doc-contract non-goals lists rot when features ship —
  roles/permissions were phase-03 non-goals, now implemented (#5 admin gates).
  Doc asserted "Roles **are** implemented" positively; test updated to match,
  with positive assertions replacing removed non-goals.
- **#28 no-hotlink contract**: seed characters.json has ZERO image_url values
  (hotlink sweep). Tests must assert projection keys present + no external-CDN
  values (self-host only), never "core cast has portraits".

## Async work-function pitfall (route-closure → repository moves, #60)

The DB wrapper is ASYNC (`AsyncGraphDatabase`): `session.execute_write(work,
command)` requires **`async def` work functions with `await tx.run(...)` /
`await result.single()`**. Even though the driver API accepts sync work fns,
mixing sync `tx.run()` with the async driver fails at runtime. `log_revision`
and all repo helpers are async — every work fn that calls them must be async.
Pattern that works: module-level `async def _approve_claim_work(tx, command)`
+ repo method `approve_claim(*, series_id, claim_id, user_id, now)` building
the command dict; routes shrink to command build + `invalidate_series`.

## Boundary threading (#78)

Pipeline resolves progress ONCE per turn (`answer()` → `boundary`), dispatcher
injects it into every executor kwarg. Service methods that re-resolve progress
internally should accept `visible_until_order: int | None = None` to
short-circuit (kills a 2nd DB read + draft/context drift). Never interpolate
`str(exc)` into model-visible tool results — exception TYPE only.

## React 19 refs-in-render (#16)

Last-good-value ref read in render body (`activeGraph = graphData ??
lastGoodGraphRef.current`) = `react-hooks/refs` violation (39 lint warnings).
Sanctioned replacement: guarded render-phase `setState` mirror —
`if (graphData && activeGraph !== graphData) setActiveGraph(graphData)`.
Identical single-paint semantics, no stale flash, lint-clean (0 warnings).
Effect-based mirroring causes a 1-frame stale flash on success→success
in-place refresh; render-phase update avoids it.

## Full-suite command (local docker, ~2m)

`source scripts/env-local.sh && unset PYTHONPATH && .venv/Scripts/python.exe -m
pytest spoilerless/tests -q -p no:cacheprovider`
Docker Desktop on Windows: start exe in background, wait-loop `docker info`,
`docker start hdgraf-neo4j` (exited container starts in seconds).

## execute_code write_file may NOT persist — verify before relying on it

`execute_code`'s `hermes_tools.write_file` reported success but the file on
disk was UNCHANGED (mtime/git status confirmed; read_file via the same tool
resolved the file fine). Do not trust execute_code writes for real edits:
verify with `terminal` (`wc -l`, `git status`, mtime) immediately after, or
prefer the `patch` tool with exact text for code changes. For large
mechanical rewrites (route-body extraction), a single big exact-text patch
worked reliably; do not chain re-verification on an unverified splice.

## FastAPI sentinel→envelope exception registry (#70) — pattern + open tail

Pattern (VALIDATED for user_content + chat, 45/45 tests): one registry in
`api/exceptions.py` — the **api layer**, NOT `core/errors.py` (avoids
core→repository imports). Register uniform repo-sentinel mappings
(NotFound→404, Validation→422, Conflict→409, Forbidden→403,
Stale→409 CHANGESET_STALE, Limit→429) as FastAPI exception handlers with
byte-identical envelope texts; routes collapse to bare awaits. Exceptions
whose message varies by context (`ChangeSetConflict`: confirm/reject/revert
wording) keep their explicit one-line catches. Handlers return
`JSONResponse(status_code=..., content={"detail": {"code", "message"}})`.

OPEN TAIL (uncommitted at session end): change_set_api regressed 422→500
with the registry — sentinels escaping to the 500 handler means FastAPI did
not match the registered class. Suspect class-identity mismatch between the
registry's import path and the raise site (services/change_set.py re-exports
repository classes — aliases should be identical objects, NOT confirmed).
Lesson regardless: run **every** router's own test file after wiring the
registry, not just one — and verify exception handler registration against
the exact app instance (`app.add_exception_handler` on the same app that
serves the routes).
