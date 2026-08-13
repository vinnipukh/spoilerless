---
phase: 09-feature-expansion-full-audit-remediation
reviewed: 2026-08-13T00:00:00Z
depth: standard
files_reviewed: 149
files_reviewed_list:
  - .github/workflows/ci.yml
  - .github/workflows/release.yml
  - LICENSE
  - data/dexter/seed/characters.json
  - docker-compose.yml
  - docs/API.md
  - docs/ARCHITECTURE.md
  - docs/DEPLOYMENT.md
  - docs/ROADMAP.md
  - docs/ops/runbook.md
  - docs/reference/frontend-api-contract.md
  - frontend/index.html
  - frontend/package.json
  - frontend/src/App.test.tsx
  - frontend/src/App.tsx
  - frontend/src/api/client.test.ts
  - frontend/src/api/client.ts
  - frontend/src/api/export.test.ts
  - frontend/src/api/export.ts
  - frontend/src/api/graph.ts
  - frontend/src/api/progress.test.ts
  - frontend/src/api/share.ts
  - frontend/src/components/ErrorBoundary.tsx
  - frontend/src/components/auth/LoginPage.tsx
  - frontend/src/components/chat/ChangeSetCard.tsx
  - frontend/src/components/chat/ChatPanel.tsx
  - frontend/src/components/chat/ChatSheet.tsx
  - frontend/src/components/detail/BacklinksTab.tsx
  - frontend/src/components/detail/DetailPanel.tsx
  - frontend/src/components/detail/RevisionHistoryPanel.tsx
  - frontend/src/components/graph/GraphCanvas.test.tsx
  - frontend/src/components/graph/GraphCanvas.tsx
  - frontend/src/components/graph/GraphControls.tsx
  - frontend/src/components/graph/GraphFilterPanel.tsx
  - frontend/src/components/graph/GraphFocusIndicator.tsx
  - frontend/src/components/graph/GraphLegend.tsx
  - frontend/src/components/graph/NodeHoverCard.tsx
  - frontend/src/components/graph/NodeSearch.test.tsx
  - frontend/src/components/graph/NodeSearch.tsx
  - frontend/src/components/graph/PathFinder.test.tsx
  - frontend/src/components/graph/PathFinder.tsx
  - frontend/src/components/graph/filterState.ts
  - frontend/src/components/graph/focusReducer.ts
  - frontend/src/components/graph/graphElements.ts
  - frontend/src/components/graph/graphStylesheet.ts
  - frontend/src/components/graph/layoutConfig.ts
  - frontend/src/components/layout/AppShell.tsx
  - frontend/src/components/palette/CommandPalette.test.tsx
  - frontend/src/components/palette/CommandPalette.tsx
  - frontend/src/components/series/SeriesDashboard.test.tsx
  - frontend/src/components/series/SeriesDashboard.tsx
  - frontend/src/components/settings/SettingsPage.tsx
  - frontend/src/components/share/ShareDialog.tsx
  - frontend/src/components/share/ShareView.test.tsx
  - frontend/src/components/share/ShareView.tsx
  - frontend/src/components/timeline/TimelineEventRow.tsx
  - frontend/src/components/timeline/TimelineView.test.tsx
  - frontend/src/components/timeline/TimelineView.tsx
  - frontend/src/hooks/useChatSessions.ts
  - frontend/src/hooks/useFetchState.ts
  - frontend/src/hooks/useHotkey.test.ts
  - frontend/src/hooks/useHotkey.ts
  - frontend/src/hooks/useNotes.ts
  - frontend/src/hooks/useRevisions.ts
  - frontend/src/hooks/useWatchProgress.ts
  - frontend/src/lib/byok.test.ts
  - frontend/src/lib/byok.ts
  - frontend/src/lib/exportMarkdown.ts
  - frontend/src/lib/nodeTypes.ts
  - frontend/src/lib/searchIndex.test.ts
  - frontend/src/lib/searchIndex.ts
  - frontend/src/main.tsx
  - frontend/src/providers/AuthContext.ts
  - frontend/src/providers/AuthProvider.tsx
  - frontend/src/types/cytoscape-fcose.d.ts
  - frontend/src/types/graph.ts
  - frontend/src/types/share.ts
  - frontend/vite.config.ts
  - index.html
  - pyproject.toml
  - render.yaml
  - spoilerless/app/api/candidates.py
  - spoilerless/app/api/chat.py
  - spoilerless/app/api/deps.py
  - spoilerless/app/api/exceptions.py
  - spoilerless/app/api/graph.py
  - spoilerless/app/api/progress.py
  - spoilerless/app/api/revisions.py
  - spoilerless/app/api/series.py
  - spoilerless/app/api/settings.py
  - spoilerless/app/api/share.py
  - spoilerless/app/api/user_content.py
  - spoilerless/app/core/config.py
  - spoilerless/app/core/errors.py
  - spoilerless/app/core/tokens.py
  - spoilerless/app/domain/chat.py
  - spoilerless/app/domain/graph.py
  - spoilerless/app/domain/revision.py
  - spoilerless/app/domain/share.py
  - spoilerless/app/domain/user_content.py
  - spoilerless/app/graph/candidates.py
  - spoilerless/app/graph/ontology.py
  - spoilerless/app/graph/seed.py
  - spoilerless/app/graph/setup.py
  - spoilerless/app/llm/fallbacks.py
  - spoilerless/app/llm/provider.py
  - spoilerless/app/main.py
  - spoilerless/app/repository/change_set.py
  - spoilerless/app/repository/chat.py
  - spoilerless/app/repository/session.py
  - spoilerless/app/repository/share.py
  - spoilerless/app/repository/user_content.py
  - spoilerless/app/retrieval/pipeline.py
  - spoilerless/app/retrieval/tools.py
  - spoilerless/app/services/auth.py
  - spoilerless/app/services/change_set.py
  - spoilerless/app/services/graph.py
  - spoilerless/app/services/rate_limit.py
  - spoilerless/app/spoiler/filter.py
  - spoilerless/app/spoiler/policy.py
  - spoilerless/app/spoiler/visibility.py
  - spoilerless/scripts/smoke.sh
  - spoilerless/scripts/zombie_sweep.py
  - spoilerless/tests/conftest.py
  - spoilerless/tests/test_api_series.py
  - spoilerless/tests/test_auth.py
  - spoilerless/tests/test_candidate_review.py
  - spoilerless/tests/test_change_set_revision.py
  - spoilerless/tests/test_config.py
  - spoilerless/tests/test_database.py
  - spoilerless/tests/test_deps.py
  - spoilerless/tests/test_episode_masking.py
  - spoilerless/tests/test_frontend_contract_doc.py
  - spoilerless/tests/test_google_verifier.py
  - spoilerless/tests/test_graph_api.py
  - spoilerless/tests/test_main_lifespan.py
  - spoilerless/tests/test_ontology.py
  - spoilerless/tests/test_rate_limit.py
  - spoilerless/tests/test_revision_models.py
  - spoilerless/tests/test_revisions.py
  - spoilerless/tests/test_seed_idempotency.py
  - spoilerless/tests/test_series_service.py
  - spoilerless/tests/test_session_repository.py
  - spoilerless/tests/test_setup_schema_check.py
  - spoilerless/tests/test_share_api.py
  - spoilerless/tests/test_spoiler_policy.py
  - spoilerless/tests/test_user_content_models.py
  - spoilerless/tests/test_user_content_repository.py
  - spoilerless/tests/test_visibility.py
findings:
  critical: 2
  warning: 3
  info: 4
  total: 9
status: clean
resolved: 2026-08-13
resolution: "CR-01, CR-02, WR-02 fixed in 7dc6370 (share-create clamp + fail-closed boundary 1, sweep logger, share 404 guard); regression tests added (test_share_api_create_clamps_boundary_to_creator_progress, updated flow tests) — 10/10 green. WR-01/WR-03 and Info findings open, non-blocking."
---

# Phase 9: Code Review Report

**Reviewed:** 2026-08-13
**Depth:** standard (cross-file verification of security-critical paths)
**Files Reviewed:** 145 (scoped from the 18 plan SUMMARYs' key-files/artifact lists, cross-checked against the phase git diff `deebcd50^..51d69c5` per #2666)
**Status:** issues_found

## Summary

Phase 9 is a large remediation + feature wave (18 plans): REBRAND-01 rename to `spoilerless/`, auth/ownership hardening (09-03), read-path hardening (09-04), API hardening incl. security headers + uppercase error codes (09-05), chat/LLM correctness (09-06), frontend correctness + lint (09-07), test isolation + zombie sweep (09-08), search/palette/timeline/dashboard (09-09/09-10), path finder + Markdown export (09-11), share snapshots (09-12), mobile/second-brain/error boundaries (09-13), graph-density/fcose (09-14), docs (09-15), remote push (09-16), live-stack verification incl. Redis fail-open (09-17), and live reseed + zombie sweep (09-18).

The overall quality is high — the boundary-clamp invariants (D-05, PROB-04), the single-filter read path (D-09), fail-closed visibility rules, CSRF origin guards on every state-changing route, and the uppercase error-code registry are consistently applied across the phase, and the SUMMARY verification claims (test counts, grep gates) check out against the code on the key paths I traced. However, two Critical issues were found: (1) the new share-create route accepts a client-chosen `visible_until_order` **without clamping it to the creator's own progress**, which widens the spoiler window for unauthenticated viewers beyond the sharer's boundary — a direct violation of the phase's own D-05/PROB-04 invariant; (2) `main.py`'s session/share sweep loop references an undefined `logger` (only `log` exists), so the first database error raises `NameError` inside the except handler and **permanently kills the background sweep task**, contradicting the documented "per-iteration exception tolerance" shipped claim (09-04 Task 3). Also: the Neo4j `ClientError` masking intent documented in `core/errors.py` is not achieved (ClientError subclasses Neo4jError, so bad statements are still masked as 503), and the share read path can 500 instead of 404 when a token's series no longer exists.

## Critical Issues

### CR-01: Share-create route does not clamp `visible_until_order` to the creator's own progress (spoiler-window widening)

**File:** `spoilerless/app/api/share.py:51-66`
**Issue:** `create_share_link` validates the requested boundary only against persisted episodes (`service.resolve_boundary(...)`) and stores the **client-chosen** value as the token's frozen boundary. Unlike every other boundary-resolving route in the phase — `api/graph.py` `get_graph` (lines 92-98) and `_resolve_effective_boundary` (lines 155-187), which clamp with `min(requested_order, record.view_as_of_order)` + `effective_view_order(...)` — there is **no lookup of the creator's persisted progress** (`ProgressService.get`). An authenticated user who has only watched through order 1 can POST `visible_until_order=60` and mint a public token whose unauthenticated read (`get_share_graph`, lines 97-118) serves content **far beyond the sharer's own boundary**. This defeats the core spoiler-safety model this phase exists to enforce (PROB-04/#12 "client-chosen boundary must never widen the spoiler window"; plan 09-12 line 26: snapshot of the user's *current spoiler-safe view*; T-09-12-01 mitigation covers only the read route ignoring a client-chosen boundary, not the create route accepting one).
**Fix:** Resolve the creator's progress record and clamp before storing, mirroring `_resolve_effective_boundary`:

```python
async def create_share_link(payload, database, share_repo, user, _csrf):
    service = GraphService(database)
    progress_service = ProgressService(database)
    record = await progress_service.get(user["id"], payload.series_id)
    requested = payload.visible_until_order
    if record is not None:
        requested_view = min(requested, record.view_as_of_order)
        requested = effective_view_order(requested_view, record.watched_through_order)
    boundary_episode = await service.resolve_boundary(payload.series_id, requested)
    if boundary_episode is None:
        raise http_error(422, "INVALID_VISIBLE_UNTIL_ORDER", ...)
    raw_token, rec = await share_repo.create(
        created_by=user["id"], series_id=payload.series_id,
        visible_until_order=requested,
    )
    ...
```

(Add a regression test: creator with progress at order 1 cannot mint a token for order 60 — the stored boundary must equal the effective view.)

### CR-02: Undefined `logger` in sweep loop — first DB error permanently kills the session/share sweep task

**File:** `spoilerless/app/main.py:139`
**Issue:** The module defines `log = logging.getLogger(__name__)` (line 40) and uses `log.info` (line 93), but the sweep loop's exception handler calls `logger.exception(...)` (line 139). `logger` is **not defined anywhere in the module** (verified by grep — only line 139 references it; no import aliases it). The first time `sweep_expired()` raises (e.g., transient DB outage), the `except Exception:` block executes `logger.exception(...)` → `NameError: name 'logger' is not defined`, which propagates out of the `while True` loop and terminates `_session_sweep_loop` as a dead asyncio task ("Task exception was never retrieved"). The task never restarts until app redeploy. This directly contradicts the documented invariant at lines 129-130 ("a failed sweep iteration is logged, never fatal") and the 09-04 SUMMARY's shipped claim ("per-iteration exception tolerance, cancellation on shutdown"); `test_main_lifespan.py` only asserts start/stop, never the failure path, so the defect is untested.
**Fix:** One-line change — use the defined logger:

```python
except Exception:
    log.exception("session/share sweep iteration failed; will retry")
```

Add a test that injects a failing repo and asserts the loop survives (task still alive after an error iteration).

## Warnings

### WR-01: Documented ClientError "exclusion" is ineffective — bad Cypher is still masked as 503 DATABASE_ERROR

**File:** `spoilerless/app/core/errors.py:120-129, 239-240`
**Issue:** The comment claims `ClientError` is "deliberately EXCLUDED" so an invalid statement surfaces as the framework's plain 500 and app bugs are not hidden behind an infra excuse. But `ClientError` **is a subclass of `Neo4jError`** (verified: `issubclass(ClientError, Neo4jError) is True` in the installed neo4j 6.2.0), and `install_error_handlers` registers `app.add_exception_handler(Neo4jError, database_handler)` (line 240). Starlette/FastAPI resolve exception handlers by walking the exception's MRO, so a `ClientError` raised by invalid Cypher **will** be caught by the `Neo4jError` handler and returned as `503 DATABASE_ERROR` — exactly the masking the comment claims to prevent. The PROB-09/#81 intent is not achieved.
**Fix:** Register an explicit override that lets `ClientError` escape as 500 (or map it deliberately), e.g.:

```python
async def client_error_handler(_request: Request, exc: ClientError) -> JSONResponse:
    logger.error("client_error (invalid query/params)", exc_info=exc)
    raise exc  # or return a 500 JSONResponse without the DATABASE_* envelope

app.add_exception_handler(ClientError, client_error_handler)  # more specific than Neo4jError
```

### WR-02: Share read path can 500 (IndexError) instead of 404 when the token's series no longer exists

**File:** `spoilerless/app/api/share.py:106-113` (→ `spoilerless/app/services/graph.py:117-118`)
**Issue:** `get_share_graph` validates the token (exists/not expired/not revoked) but never checks the series still exists before calling `service.fetch_graph(...)`. `GraphService.fetch_graph` unconditionally indexes `series_rows[0]` (services/graph.py line 118) — if the series was deleted after token creation, `SERIES_QUERY` returns `[]` and `series_rows[0]` raises `IndexError` → unhandled 500, despite the route declaring only `error_responses(404, 503)`. The graph GET route guards this exact case with `get_series_meta` → 404 `SERIES_NOT_FOUND` (api/graph.py:73-75); the share route should do the same.
**Fix:** After resolving the token record, add:

```python
series = await service.get_series_meta(record.series_id)
if series is None:
    raise http_error(404, "RESOURCE_NOT_FOUND", "The shared series no longer exists.")
```

### WR-03: Stale `hdgraf:` prefix in rate-limit Redis bucket keys after REBRAND-01

**File:** `spoilerless/app/services/rate_limit.py:84`
**Issue:** `bucket_key` returns `f"hdgraf:rate_limit:{self.times}/{self.seconds}"`. Plan 09-01 (REBRAND-01) renamed all user-visible and repo-level branding to `spoilerless`, and the 09-01 verification gate (`git grep -il 'hdgrafcehennemi'` = 0) passes only because the gate greps the full string `hdgrafcehennemi`, not the `hdgraf:` prefix. The Redis key namespace retains the pre-rebrand brand — inconsistent with the phase's own rename contract and confusing for ops debugging shared Upstash keys.
**Fix:** `return f"spoilerless:rate_limit:{self.times}/{self.seconds}"` (note: this changes key namespaces; deploy alongside a one-time counter reset, which is harmless for rate limiting).

## Info

### IN-01: Stale docstring contradicts the 429 error code actually raised

**File:** `spoilerless/app/services/rate_limit.py:60-65`
**Issue:** `rate_limit_callback`'s docstring says it reuses "the exact lowercase `too_many_requests` code ... (ErrorDetail.code's regex is `^[a-z][a-z0-9_]*$`)" and "never a new uppercase code" — but the code raises `http_error(429, "TOO_MANY_REQUESTS", ...)` (uppercase, line 65), which is correct per the 09-05 uppercase sweep and the registry in `core/errors.py:34`. The docstring predates the sweep and is misleading.
**Fix:** Update the docstring to reference the uppercase `TOO_MANY_REQUESTS` and the `^[A-Z][A-Z0-9_]*$` pattern.

### IN-02: Stale docstring in `require_admin` ("lowercase FORBIDDEN")

**File:** `spoilerless/app/api/deps.py:107-110`
**Issue:** The docstring says the gate "Uses the existing lowercase `\"FORBIDDEN\"` error code ... do not add a new uppercase code" — but the 09-05 sweep made `FORBIDDEN` uppercase (it is in the canonical registry, `core/errors.py:29`). Stale documentation from before the sweep.
**Fix:** Drop the casing guidance; reference the canonical uppercase registry.

### IN-03: Hardcoded `max_hops: 4` in PathFinder duplicates the server ceiling

**File:** `frontend/src/components/graph/PathFinder.tsx:83`
**Issue:** The client sends `max_hops: 4`, which duplicates the backend constant `MAX_PATH_HOPS = 4` (`spoilerless/app/retrieval/tools.py:30`). The server clamps anyway (`max(1, min(int(max_hops), MAX_PATH_HOPS))`), so this is not a bug, but the duplicated literal will silently drift if the server ceiling changes.
**Fix:** Export the ceiling from the API contract (e.g., a constant in `frontend/src/api/graph.ts` with a comment tying it to the backend value), or drop the field and let the server default apply.

### IN-04: Debug `console.log` in frontend test setup

**File:** `frontend/src/test/setup.ts:37`
**Issue:** `console.log('[SETUP] before matchMedia polyfill, typeof:', typeof window.matchMedia)` is a leftover debug statement. Harmless (test-only), but the phase's own 09-13 PROB-21 work removed debug `console.log` from `GraphCanvas.tsx`; this one survives in the shared test setup.
**Fix:** Remove the line (or convert to a comment).

---

## Notes on verification

- **Scope cross-check:** SUMMARY-derived scope (145 existing files) was cross-checked against `git diff --name-only deebcd50^..51d69c5` per #2666; the diff additionally surfaces files changed by mechanical rename sweeps (09-01) that the summaries do not list individually — those were spot-checked via grep gates (no findings beyond those above).
- **Claims verified against code:** anonymous-boundary fix at order 1 (`api/graph.py:82`), path-route boundary from persisted progress (`api/graph.py:169-178`), fail-open Redis limiter (`services/rate_limit.py:92-103`), seed reveal-point materialization (`graph/seed.py:51-57`), zombie-sweep NEVER_DELETE set + dry-run-first (`scripts/zombie_sweep.py:31,131-167`), CSRF origin guard on all cookie-authenticated writes (`api/deps.py:150-210`), uppercase registry + field validator (`core/errors.py:27-99`). All match their SUMMARY claims.
- **Not reviewed at depth:** performance characteristics (out of scope v1), docs prose accuracy beyond contract tests, and the 09-16 pure-ops plan (remote push — no source changes).

_Reviewed: 2026-08-13_
_Reviewer: gsd-code-reviewer (subagent)_
_Depth: standard_
