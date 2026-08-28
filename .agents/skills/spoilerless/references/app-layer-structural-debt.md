# App-layer structural debt — thermo-nuclear review findings (2026-08)

Read-only review of `spoilerless/app` (api/ services/ core/ main.py domain/). Known
code-judo targets; future refactor sessions should hit these first. Line numbers as
of the review date.

## Callback-transaction anti-pattern (BLOCKER-grade layering)
- `api/candidates.py:253-399` — `approve_candidate` / `reject_candidate` / `edit_candidate`
  author full Cypher transactions inside route handlers as closures (`_approve(tx, cmd)`,
  `_reject`, `_edit`): raw `tx.run()` + `RevisionRepository.log_revision`.
- `graph/candidates.py:182-202` — the "repository" methods `approve_claim(work, command)`
  etc. are literal pass-throughs: `return await self._db.execute_write(work, command)`.
- `api/revisions.py:126-310` — `revert_revision` embeds the entire revert flow in a nested
  `_revert_work(tx, _cmd)` closure (ownership checks, CANNOT_REVERT_* guards, UserNote
  REFERS_TO restore, REVERTED-revision logging) driven by a `command` dict; also
  `RevisionRepository._from_json` private reach-in (line 162) and module-level raw Cypher
  (`REVISION_LIST_QUERY`/`REVISION_GET_QUERY` lines 22-47).
- Fix pattern: move the transaction into the repository as a real method taking
  `(ids, user_id, now)`; delete the `work`/`command` plumbing; routes become
  try/except + cache invalidation.

## Category error (correctness)
- `api/graph.py:185-195` — `find_shortest_path` passes `MAX_PATH_HOPS` (a hop-count cap)
  as the requested *episode order* to `_resolve_effective_boundary`; any authenticated user
  with `view_as_of_order < MAX_PATH_HOPS` gets clamped to `min(5, view)`. Also reaches
  `service._database` (private) instead of going through `GraphService`.

## Duplication map (verify-before-refactor checklist)
- `DatabaseDependency` redefined: deps.py:26 canonical + graph.py:28, revisions.py:15,
  series.py:17, user_content.py:30. `Boundary` redefined: revisions.py:16, user_content.py:31.
- `_not_found` defined 4× (change_set.py:46, chat.py:50, revisions.py:50, user_content.py:38) —
  half `raise`, half `return` (inconsistent). `_invalid` 2×, `_conflict` 2×.
- LLM fallback chain (`stored.get(k) or settings.llm_k` + provider dispatch) duplicated:
  services/chat.py:77-178 `get_llm_provider` vs services/settings.py:30-49 `get_llm`.
- Cache-aside block copy-pasted: api/graph.py:100-118 → api/share.py:126-142.
- Boundary math duplicated: api/graph.py:82-98 (inline in `get_graph`) vs 129-158
  (`_resolve_effective_boundary` — extracted but original call site never converted).
- `api/series.py:76-97` — `list_episodes` called twice (first result discarded) because the
  service's `effective_view_order: int | None = None` "backward compat" mode
  (services/series.py:47-48) exists only to serve the probe call.
- Error idioms: `http_error` (raises) vs router-local `_error` (returns, api/graph.py:53-57)
  vs inline `HTTPException(detail={...})` (api/series.py:42-45).
- Constants in api layer imported api→api: `VISIBLE_NODE_LABELS`/`USER_RELATIONSHIP_TYPES`
  (api/graph.py:29-38) imported by api/share.py:14-17.

## Exception-handling boilerplate
- `api/user_content.py:59-304` — 9 handlers × identical 4-clause try/except
  (ValidationError→422, Conflict→409, NotFound→404, Forbidden→403); `_invalid(exc)` /
  `_conflict(exc)` take `exc` and never use it. Fix: one global FastAPI exception handler
  per repo exception; every handler collapses to a one-liner.
- `api/candidates.py:155-163, 281-286, 333-338, 391-398` — catch-all `except Exception`
  → 422 `INVALID_EXTRACTION_PAYLOAD` with `f"...{exc}"` leaked into the client message
  (wrong code for approve/reject/edit failures; info disclosure).
- `core/errors.py:121-126` — `ClientError` in `_SAFE_ERRORS` → any Neo4j client error
  becomes 503 DATABASE_UNAVAILABLE (masks server bugs as infra outages).

## Dead code
- `domain/graph.py:98-99` `model_records` (zero references).
- `domain/chat.py:116` `ChatEventPayload = dict[str, Any]` (never imported) — legitimizes the
  loose `chunk["type"]`/`chunk['envelope']` dict contract from `answer_stream`.
- `core/errors.py:240-242` `install_database_error_handlers` compat alias.
- `services/rate_limit.py:49-61, 90` — `rate_limit_callback` `pexpire` param never used;
  docstrings say "lowercase too_many_requests code" while code raises uppercase.

## Model/type drift
- `domain/graph.py:41` `GraphClaim.relationship_effect: float` vs string enum everywhere
  else (extraction.py:110 RelationshipEffect, candidates.py:96) — a stored "strengthens"
  fails `model_validate`.
- `services/auth.py:119-127` — `session_repo or InMemorySessionRepository()` /
  `verifier or ProductionGoogleVerifier()` silent fallbacks hide a production hazard if DI
  ever misses (deps.py always passes both — the fallbacks are dead code hiding the invariant).
- `services/auth.py:94-106` — Google error classification by substring-matching error
  messages (`"audience" in lower_msg`) — fragile coupling to google-auth internals.

## Tooling note (Windows host)
`search_files` with a glob (`*.py`) + native Windows path returned 0 results for a
known-nonempty directory; `terminal` `find /c/Users/... -name "*.py"` (MSYS path) worked.
If a file search comes back empty on a directory you know has files, fall back to `find`
via terminal rather than trusting the 0.
