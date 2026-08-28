---
last_mapped: 2026-08-26
focus: quality
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---
<!-- refreshed: 2026-08-26 -->
# Testing Patterns

**Analysis Date:** 2026-08-26

## Test Framework

**Backend runner:**
- Pytest `>=9.1.1` with pytest-asyncio `>=1.4.0`, HTTPX, and FastAPI `TestClient`, declared in `pyproject.toml`.
- Root config in `pyproject.toml` sets `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope = "module"`, and `testpaths = ["spoilerless/tests"]`; Python `>=3.13` is required.
- The tracked backend suite contains **53 `test_*.py` files (~23.4k lines)** plus `spoilerless/tests/conftest.py` and `spoilerless/tests/fixtures/`.
- Phase 12 added and expanded suites:
  - `spoilerless/tests/test_revisions.py` (270 lines) covering the decomposed revision repository and service, ownership enforcement, and safe revert.
  - `spoilerless/tests/test_rate_limit.py` (112 lines) covering rate limiter lazy re-initialization on startup Redis outage and uppercase error codes.
  - `spoilerless/tests/test_share_api.py` (118 lines) covering share token hashing, boundary-resolved snapshot sharing, and anonymous access.
  - `spoilerless/tests/test_visualization_cache.py` (expanded) covering focus-set capacity bounding and cache invalidation behind `GraphService`.
  - `spoilerless/tests/test_security_boundary.py` (expanded) covering anonymous `visible_until_order=999` clamping and fail-closed resolution.
  - `spoilerless/tests/test_user_content_api.py` (expanded) covering privacy-scrubbed `user_id: null` reads and note attachments across all custom node types.

**Frontend runner:**
- Vitest `^4.1.10`, Testing Library, jest-dom, user-event, and jsdom are declared in `frontend/package.json`.
- `frontend/vite.config.ts` sets `environment: 'jsdom'`, enables Vitest globals, and loads `frontend/src/test/setup.ts`.
- 438+ tests across 29 test files pass reliably.
- Decomposed frontend components have targeted test suites: `DetailPanel.test.tsx`, `GraphCanvas.test.tsx`, `GraphFilterPanel.test.tsx`, `useSceneState.test.ts`, `cytoscapeReconciler.test.ts`, `graphElements.test.ts`.

**Assertion libraries:**
- Backend uses plain pytest `assert`, `pytest.raises`, and parametrization in `spoilerless/tests/`.
- Frontend uses Vitest `expect` plus `@testing-library/jest-dom/vitest` matchers registered by `frontend/src/test/setup.ts`.

**Run commands:**
```bash
uv run pytest                                           # run all backend tests from repository root
uv run pytest spoilerless/tests/test_openapi_contract.py    # one backend test file
uv run pytest spoilerless/tests/test_security_boundary.py   # fail-closed boundary test suite
uv run pytest spoilerless/tests/test_revisions.py          # revision and revert test suite
uv run pytest spoilerless/tests/test_rate_limit.py         # rate limiter resilience suite

uv run python scripts/run_phase10_backend_tests.py      # canonical full backend suite (ephemeral Neo4j)
uv run python scripts/run_backend_tests.py --list       # list 11 test chunks
uv run python scripts/run_backend_tests.py --chunk graph # run specific test chunk

cd frontend
NODE_ENV=test CI=1 npm run test                         # reliable one-shot frontend test suite
NODE_ENV=test npm run test                              # interactive watch mode
NODE_ENV=test CI=1 npm run test -- src/App.test.tsx     # run single frontend test file
npm run build                                           # canonical frontend typecheck & bundle verification
```

## Test File Organization

**Backend structure:**
```text
spoilerless/tests/
├── conftest.py                         # shared fixtures, scratch-series factories, test doubles
├── fixtures/visualization/             # checked-in safe JSON baselines (s01e01_safe.json, etc.)
├── test_auth.py                        # Google OAuth, session lifecycle, CSRF guards
├── test_candidates.py                  # candidate review and extraction staging
├── test_candidate_ingest.py            # candidate ingestion, single-query Cypher checks
├── test_change_set_api.py              # ChangeSet propose, confirm, apply, revert
├── test_chat_api.py                    # streaming chat, SSE, provider integration
├── test_graph_api.py                   # graph endpoints, node/edge visibility, filters
├── test_rate_limit.py                  # RateLimiter lazy re-init and fail-closed behavior
├── test_revisions.py                   # RevisionService, RevisionRepository, revert ownership
├── test_security_boundary.py           # single fail-closed boundary enforcement matrix
├── test_share_api.py                   # share link creation, token hashing, read-only views
├── test_user_content_api.py            # user notes, custom nodes, privacy scrubbing
├── test_visualization_projection.py    # multi-view projection logic (offline suite)
├── test_visualization_cache.py         # visualization caching, focus caps, invalidation
└── ... (53 test modules total)
```

**Frontend structure:**
```text
frontend/src/
├── App.test.tsx
├── api/
│   ├── chat.test.ts
│   ├── client.test.ts
│   ├── export.test.ts
│   └── progress.test.ts
├── components/
│   ├── auth/LoginPage.test.tsx
│   ├── chat/ChatPanel.test.tsx
│   ├── detail/DetailPanel.test.tsx
│   ├── graph/
│   │   ├── GraphCanvas.test.tsx
│   │   ├── GraphFilterPanel.test.tsx
│   │   ├── cytoscapeReconciler.test.ts
│   │   ├── graphElements.test.ts
│   │   └── overviewTiers.test.ts
│   ├── series/SeriesDashboard.test.tsx
│   ├── settings/SettingsPage.test.tsx
│   └── share/ShareView.test.tsx
├── hooks/
│   ├── useCandidates.test.ts
│   ├── useGraph.test.ts
│   ├── useNotes.test.ts
│   ├── useRevisions.test.ts
│   ├── useSceneState.test.ts
│   └── useWatchProgress.test.ts
└── lib/
    ├── byok.test.ts
    ├── searchIndex.test.ts
    └── visualizationAdapter.test.ts
```

## Testing Patterns & Best Practices

**1. Scratch-Series Isolation:**
- Graph mutation tests bootstrap an ephemeral scratch series (`SCRATCH = "series_scratch_*"`) using `bootstrap_scratch_series(series_id, episodes)` in `spoilerless/tests/conftest.py`.
- Teardown executes via `teardown_scratch_series(series_id)` in a `finally` block or fixture teardown.
- Never pollute the canonical `series_dexter` dataset with temporary test nodes.

**2. Privacy-Scrubbing Verification:**
- Tests verify that anonymous and non-owner reads on user content endpoints return 200 with `user_id: null` rather than 500 Pydantic `ValidationError`.
- Assert that sensitive metadata (`user_id`, `before`, `after` snapshots) are stripped for unauthenticated or non-owning callers.

**3. Boundary Enforcement Matrix:**
- Test all four boundary cases:
  1. Anonymous request with no order parameter → returns episode 1 data.
  2. Anonymous request with `visible_until_order=999` → clamped to episode 1 data (200 OK, not 422).
  3. Authenticated request with watched progress 2 requesting view order 3 → clamped to order 2.
  4. Authenticated request requesting unpersisted episode 999 → returns 422 `INVALID_VISIBLE_UNTIL_ORDER`.

**4. Rate Limiter Testing:**
- Verify both the normal Redis-backed path and the disconnected recovery path.
- Test lazy re-initialization when Redis becomes available after a startup failure.
- Ensure error responses return registered uppercase error codes (`RATE_LIMIT_UNAVAILABLE`).

**5. Frontend Component & Contract Alignment:**
- Verify frontend TypeScript DTOs against backend Pydantic models.
- Mock API clients accurately; avoid asserting obsolete wire shapes in tests.
- Always verify frontend changes with `npm run build` (`tsc -b && vite build`) to catch TypeScript discriminated-union narrowing errors.

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **New Backend Test Suites:**
  - `spoilerless/tests/test_revisions.py` (270 lines) covering decomposed revision service/repo and revert permissions.
  - `spoilerless/tests/test_rate_limit.py` (112 lines) covering lazy re-init retry paths.
  - `spoilerless/tests/test_share_api.py` (118 lines) covering share endpoints and token resolution.
- **Updated Regression Test Matrices:**
  - `test_security_boundary.py`: added anonymous `visible_until_order=999` clamping regressions across notes, revisions, and custom nodes (THERMO-P1-01).
  - `test_user_content_api.py`: added D-02 privacy scrubbing assertions (`user_id: null`) and note attachment support for all custom node types (THERMO-P0-01, THERMO-P1-05).
  - `test_graph_api.py`: updated for `GraphService.read_visible_graph` facade and `effective_view_order` DTO fields.
- **Frontend Test Suite Updates:**
  - Updated test fixtures for decomposed components (`DetailPanel.test.tsx`, `GraphFilterPanel.test.tsx`).
  - Added test assertions for `effective_view_order` in `graphResponse.ts` fixtures.

---

*Testing analysis: 2026-08-26*
