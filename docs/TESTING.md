# HD Graf Cehennemi — Testing Guide

> **Version:** 0.1.0
> **Last updated:** 2026-07-29
> **Project:** Spoiler-aware TV series knowledge graph

---

## Table of Contents

1. [Test Suite Overview](#1-test-suite-overview)
2. [Prerequisites](#2-prerequisites)
3. [Running Tests](#3-running-tests)
   - [Backend Tests (pytest)](#31-backend-tests-pytest)
   - [Frontend Tests (Vitest)](#32-frontend-tests-vitest)
4. [Backend Test Reference](#4-backend-test-reference)
   - [Test Inventory](#41-test-inventory)
   - [Key Testing Patterns](#42-key-testing-patterns)
   - [Fixtures & Factories](#43-fixtures--factories)
5. [Frontend Test Reference](#5-frontend-test-reference)
   - [Test Inventory](#51-test-inventory)
   - [Key Testing Patterns](#52-key-testing-patterns)
6. [Spoiler Safety Testing](#6-spoiler-safety-testing)
7. [OpenAPI Contract Testing](#7-openapi-contract-testing)
8. [Writing New Tests](#8-writing-new-tests)
9. [Troubleshooting](#9-troubleshooting)
10. [Roadmap & CI Plans](#10-roadmap--ci-plans)

---

## 1. Test Suite Overview

The project has **53 test files** across two test suites:

| Suite | Framework | Tests | Location | Command |
|-------|-----------|-------|----------|---------|
| **Backend** | pytest 9.x | 29 files | `backend/tests/` | `uv run pytest` |
| **Frontend** | Vitest 4.x | 24 files | `frontend/src/` | `cd frontend && npm test` |

**Continuous Integration:** Not yet configured. All tests run locally. See §10.

### Core Testing Philosophy

- **Spoiler filtering is the primary architectural invariant.** Every test that exercises a data-reading endpoint must verify that content from beyond the `visible_until_order` boundary is absent — not just that expected content is present.
- **Fail-closed by default.** Missing, malformed, zero, negative, or non-persisted boundaries return 422. Hidden direct reads (e.g., a note attached to a future episode) return indistinguishable 404s.
- **Tests connect to a real Neo4j instance.** The backend test suite uses `fastapi.testclient.TestClient` against a live Neo4j database; it does not mock the database layer (except for error-injection scenarios).
- **OpenAPI contracts are enforced by test.** The documented API surface (in `docs/frontend-api-contract.md`) is compared to the generated OpenAPI schema at test time; drift is caught before deployment.
- **Idempotent seeding is verified.** The seed pipeline must produce identical output when run twice, and must not destroy user-created content on re-run.

---

## 2. Prerequisites

### Backend

- **Neo4j** must be running via Docker Compose:
  ```bash
  docker compose up -d
  ```
- The default connection settings in `conftest.py` assume `bolt://127.0.0.1:7687` with password `hdgraf-local-password`. Override via environment variables:
  ```env
  NEO4J_URI=bolt://127.0.0.1:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=hdgraf-local-password
  NEO4J_DATABASE=neo4j
  ```
- Python dependencies (including test dependencies `pytest`, `pytest-asyncio`, `httpx`):
  ```bash
  uv sync
  ```

### Frontend

- Node.js 18+ and npm:
  ```bash
  cd frontend && npm install
  ```
- No backend or Neo4j required — the frontend test suite uses mocked `fetch` calls and a stubbed Cytoscape component.

---

## 3. Running Tests

### 3.1 Backend Tests (pytest)

**From the project root:**

```bash
uv run pytest
```

**Run a specific test file:**

```bash
uv run pytest backend/tests/test_graph_api.py -v
```

**Run a specific test by name:**

```bash
uv run pytest backend/tests/test_graph_api.py -v -k "test_graph_boundaries"
```

**Run seed-idempotency tests only:**

```bash
uv run pytest backend/tests/test_seed_idempotency.py -v
```

**Run with verbose output and fail-fast:**

```bash
uv run pytest -x -v
```

**With live Neo4j debug logging:**

```bash
uv run pytest -v --log-cli-level=INFO 2>&1 | head -100
```

### 3.2 Frontend Tests (Vitest)

**From the `frontend/` directory:**

```bash
cd frontend && npm test
```

Or, from any directory:

```bash
npx vitest
```

**Run in watch mode (for development):**

```bash
npm test -- --watch
```

**Run a specific test file:**

```bash
npx vitest src/components/detail/DetailPanel.test.tsx
```

**Run with UI mode (Vitest browser dashboard):**

```bash
npx vitest --ui
```

**Coverage report:**

```bash
npx vitest --coverage
```

---

## 4. Backend Test Reference

### 4.1 Test Inventory

All backend tests live under `backend/tests/`. They connect to a live Neo4j database and typically reseed data for each test run — expect runtime of **~30–60 seconds** for the full suite.

| File | Lines | Dependencies | What it covers |
|------|-------|-------------|----------------|
| `conftest.py` | 18 | — | Environment defaults, `sys.path` setup, `os.environ` defaults for Neo4j connection |
| `test_graph_api.py` | 445 | Live Neo4j | Spoiler boundary filtering (parametrized across S01E01/E02/E03), user relationship projection fail-closed, claim temporal validity, error responses (404/422/503), database-unavailable sanitization, Pydantic model validation (dangling edges), degraded startup |
| `test_seed_idempotency.py` | 475 | Live Neo4j | Seed idempotency & completeness, Community-compatible schema (no property-existence constraints), visibility integrity audit, null-visibility rejection (reads + writes), claim provenance, user-layer preservation across re-seed |
| `test_auth.py` | 658 | No DB | Google sign-in (success, failure, missing client ID), session creation/refresh/reuse, cookie lifecycle, logout, `/api/auth/me` (authenticated, unauthenticated, stale session) |
| `test_user_content_api.py` | 377 | Live Neo4j | Notes CRUD, custom nodes CRUD, custom relationships CRUD, spoiler-gated reads (hidden notes return 404), cross-series isolation, 409 conflict on delete-with-dependents |
| `test_user_content_models.py` | 321 | No DB | Pydantic model validation: enum-ontology lock, field stripping/trimming, validation error messages for wrong types/missing fields/extra fields, `VisibleUntilOrder` boundary logic, `Origin` enum contract |
| `test_user_content_repository.py` | 182 | No DB | Repository-layer unit tests with fake Neo4j driver: `execute_write` retry stability, query templating, parameter binding |
| `test_openapi_contract.py` | 300 | No DB | Error response schema + component references, sanitized validation envelopes, strict payload mode, `http_error` helper, `error_responses` utility |
| `test_frontend_contract_doc.py` | 183 | No DB | Locked operation inventory (44 operations, 32 path templates), document vs. OpenAPI schema parity, fail-closed wording, origin/boundary/error documentation checks |

### 4.2 Key Testing Patterns

#### Spoiler Boundary Parametrization

The most critical test pattern. `test_graph_boundaries_have_full_json_sentinels` in `test_graph_api.py` tests every episode boundary with expected node/edge/claim/source/evidence counts **and** forbidden sentinel strings:

```python
@pytest.mark.parametrize(
    ("boundary", "expected", "forbidden"),
    [
        (
            1,
            {"nodes": 11, "edges": 6, "claims": 4, "sources": 1, "evidence": 3},
            ["dexter_s01e02", "S01E02", "Crocodile", "Paul Bennett", "Rudy Cooper", "ice rink"],
        ),
        (
            2,
            {"nodes": 15, "edges": 10, "claims": 5, "sources": 2, "evidence": 5},
            ["dexter_s01e03", "S01E03", "Popping Cherry"],
        ),
        (3, {"nodes": 20, "edges": 16, "claims": 8, "sources": 3, "evidence": 8}, []),
    ],
)
```

Key assertions:
- **Counts are exact integers** — not "at least" or "approximately"
- **Forbidden content is checked via case-insensitive string search** in the raw JSON — ensuring no ID, label, or relationship name leaks through
- **Edge integrity** — every edge's source and target must exist in the returned node set

#### Idempotent Seeding

`test_seed_is_idempotent_and_complete` runs `setup_database()` twice and asserts:
- Exact same node/relationship counts both times
- Exact same node IDs and relationship IDs both times
- No duplicate IDs within any collection

`test_setup_preserves_user_layer_and_deleted_resources_stay_deleted` ensures re-seeding:
- Preserves user-created nodes, relationships, and notes
- Does not re-create user-deleted canonical content
- Keeps constraint/index names stable and non-duplicated

#### Null-Visibility Rejection

A suite of tests in `test_seed_idempotency.py` verifies that nodes with `visible_from_order: null` are:
- Rejected by `audit_visibility_integrity()` (raises `ValueError`)
- Never returned by Cypher reads (the `WHERE node.visible_from_order <= $boundary` filter excludes `null`)
- Blocked from being used as note targets or custom-node episodes (raise `UserContentNotFound`)

#### Error Envelope Standardization

All API errors use a consistent `ErrorResponse` schema:

```json
{"detail": {"code": "error_code", "message": "Human-readable message."}}
```

Tests verify:
- HTTP status codes (404, 422, 503, etc.)
- Error code strings (never raw exception text)
- Sensitive information is **never** leaked (database connection strings, passwords, query text are stripped)

#### Database-Unavailable Mode

`UnavailableDatabase` is a test stub that raises `ServiceUnavailable` on every operation. It's used to verify:
- The app starts in **degraded mode** (HTTP 503 health, but HTTP 200 for `/docs`)
- Error responses do not contain credentials or query text
- The `get_database` dependency override is cleaned up after each test

#### Auth Test Patterns

- **Fakes over mocks** — `FakeUserRepo`, `FakeGoogleVerifier`, and `InMemorySessionRepository` implement the real repository/verifier protocols with in-memory state
- **Cookie inspection** — tests read `Set-Cookie` headers to verify session cookie name, expiry, and `HttpOnly`/`Secure` flags
- **Token hashing verified** — raw session tokens are never stored; tests confirm the repository holds SHA-256 hashes
- **Edge cases** — wrong audience, expired tokens, missing `GOOGLE_CLIENT_ID`, concurrent sessions

### 4.3 Fixtures & Factories

| Fixture | Scope | What it does |
|---------|-------|-------------|
| `live_client` (test_graph_api.py) | Function | Seeds the database, yields a `TestClient`, relies on `setup_database()` being idempotent |
| `live_database` (test_seed_idempotency.py) | Function | Opens a `Neo4jDatabase` connection, yields it, closes it |
| `FakeUserRepo` (test_auth.py) | — | In-memory user store keyed by `google_sub` |
| `FakeGoogleVerifier` (test_auth.py) | — | Returns controlled JWT claims; call `set_failure()` for error scenarios |
| `FakeDriver` / `FakeSession` / `FakeTransaction` (test_user_content_repository.py) | — | Fake Neo4j driver that captures query calls and returns controlled results |

---

## 5. Frontend Test Reference

### 5.1 Test Inventory

All frontend tests live under `frontend/src/` alongside their components, and use Vitest 4.x with `@testing-library/react`. The test environment is `jsdom` (configured in `vite.config.ts`).

| File | Lines | What it covers |
|------|-------|----------------|
| `App.test.tsx` | 595 | End-to-end app flow: empty state → series select → episode confirm → graph render → node tap → DetailPanel → episode cancel → episode forward → episode backward; sessionStorage hydration on remount |
| `components/graph/GraphCanvas.test.tsx` | 409 | Element count parity with backend boundary fixture (S01E01: 11 nodes, 6 edges; S01E03: 20 nodes, 16 edges) |
| `components/detail/DetailPanel.test.tsx` | 247 | Locked state (no selection), node view (3 tabs: Overview/Claims/Evidence), claim-backed edge view, interactive tab switching |
| `components/detail/StructuralEdgeCard.test.tsx` | 37 | Renders PART_OF edge with connected node labels; confirms no tablist |
| `components/episode/ConfirmAdvanceModal.test.tsx` | 80 | Forward copy ("Unlock S01E02?"), backward copy ("Rewatch S01E01?"), cancel button, confirm button |
| `hooks/useWatchProgress.test.ts` | 208 | Hydration from valid/invalid/malformed sessionStorage, empty state fallback, `requestChange()` / `confirmChange()` state transitions, pending change modal gating |

### 5.2 Key Testing Patterns

#### Cytoscape Stubbing

`react-cytoscapejs` renders to `<canvas>`, which is not interactive under jsdom. Both `App.test.tsx` and `GraphCanvas.test.tsx` provide a **stub implementation** that:

1. Renders a `<div data-testid="graph-canvas-stub">` with clickable child elements for each node/edge
2. Provides a `fakeCy` object that captures `cy.on(...)` event registrations
3. Fires those handlers when the stub elements are clicked — testing the real `GraphCanvas` tap-wiring code
4. Maintains handler identity across re-renders via `useRef` to match the real component's guard pattern

The stub in `App.test.tsx` is significantly more elaborate, including chainable fake Cytoscape collections (`.closedNeighborhood()`, `.connectedNodes()`, etc.) for the highlight/fade selection logic.

#### Mocked Fetch with Fixture Data

`App.test.tsx` uses `vi.stubGlobal('fetch', vi.fn(fetchStub))` to mock all API calls:

- `/api/series` → returns `seriesFixture` (one series: Dexter)
- `/api/series/series_dexter/episodes` → returns `episodesFixture` (3 episodes)
- `/api/series/series_dexter/graph?visible_until_order=N` → returns `graphResponseS01E01` fixture
- Everything else → returns 404

Graph responses are loaded from `src/test/fixtures/graphResponse.ts`.

#### SessionStorage State Machine

`useWatchProgress.test.ts` verifies the three-state model:
- **Hydrated** — valid `sessionStorage` entry on mount → `confirmedOrder` set, no modal
- **Corrupted** — invalid JSON, missing fields, `visibleUntilOrder: 0` or negative → empty state fallback
- **Change flow** — `requestChange()` → `pendingChange` set → `confirmChange()` → modal closed → new `confirmedOrder`

#### React Testing Library Idioms

- `@testing-library/user-event` for realistic click/type interactions (`userEvent.setup()` + `await user.click(...)`)
- `waitFor()` for async assertions (graph fetch after confirmation)
- `screen.queryByText()` / `queryByRole()` for absent elements (confirmation modal after cancel)
- `toBeInTheDocument()` matcher from `@testing-library/jest-dom/vitest`
- `act()` wrapping for `renderHook` state transitions

---

## 6. Spoiler Safety Testing

Spoiler-aware filtering is the **core architectural invariant** of the system. Every spoiler-sensitive endpoint must have a test proving that content from beyond the user's `visible_until_order` boundary is never transmitted.

### Backend Verification Points

| What | How it's tested | File |
|------|----------------|------|
| `visible_from_order` Cypher filtering | Parametrized test across boundaries 1, 2, 3 with exact counts + forbidden sentinels | `test_graph_api.py:test_graph_boundaries_have_full_json_sentinels` |
| Claim temporal validity | Claim `temporary_trust` present at boundary 1, absent at boundary 2 | `test_graph_api.py:test_claim_validity_is_independent_of_visibility` |
| User relationship projection | Custom nodes/relationships with different visibility orders; fail-closed on missing `visible_from_order` | `test_graph_api.py:test_user_relationship_projection_is_edge_only_closed_and_fail_closed` |
| Null visibility → excluded from reads | Node with `null` visibility never appears in results | `test_seed_idempotency.py:test_read_never_returns_null_visibility_node` |
| Null visibility → write rejection | Note on null-visibility target raises `UserContentNotFound` | `test_seed_idempotency.py:test_note_write_rejects_null_visibility_target` |
| Hidden direct reads → 404 | Note attached to future episode returns 404, not 403 or 200 | `test_user_content_api.py` |
| Non-persisted boundary → 422 | `visible_until_order=4` (no S01E04) returns 422 | `test_graph_api.py:test_graph_error_shapes` |

### Frontend Verification Points

| What | How it's tested | File |
|------|----------------|------|
| No graph fetch before confirm | Empty state → 0 graph fetch calls | `App.test.tsx` |
| Correct boundary in fetch URL | `visible_until_order=1` in the fetch call after confirming S01E01 | `App.test.tsx` |
| Cancelled change → no new fetch | Modal cancel → no additional graph fetches | `App.test.tsx` |
| Element counts match backend fixture | GraphCanvas renders exact node/edge counts from fixture | `GraphCanvas.test.tsx` |

### Fail-Closed Requirements

When adding a new spoiler-sensitive endpoint, the test must verify:

1. **Boundary enforcement** — data with `visible_from_order > N` is absent from the response
2. **Invalid boundaries** — missing, malformed, zero, negative, or non-persisted boundaries return 4xx (preferably 422)
3. **Hidden direct reads** — attempting to read a specific hidden entity returns 404 (indistinguishable from "does not exist")
4. **No metadata leakage** — response collections contain no totals, counts, or hints about hidden content
5. **Full serialization check** — the forbidden content is searched for in the raw JSON string, not just in parsed fields

---

## 7. OpenAPI Contract Testing

The project enforces an **OpenAPI contract via test** rather than relying on runtime schema generation alone.

### What's Checked

**`test_frontend_contract_doc.py`** compares `docs/frontend-api-contract.md` against the generated OpenAPI schema:

1. **Exact operation inventory** — 44 HTTP operations across 32 path templates, locked in both the document and the OpenAPI schema
2. **Document content checks** — key phrases must appear: `fail-closed`, `required positive integer`, `persisted episode order`, `origin: canonical|candidate|user`, `hidden and missing direct reads are indistinguishable`, `no totals/counts`

**`test_openapi_contract.py`** verifies the error response schema:

1. `ErrorDetail` and `ErrorResponse` component schemas exist in OpenAPI
2. Every `error_responses(...)` usage produces valid `$ref` references
3. Validation errors use a stable, sanitized envelope (`invalid_request` code, no leaked input values)
4. The strict payload mode (`extra="forbid"`) is enforced

### Adding a New Endpoint

1. Add the endpoint to the backend route module
2. Add the path template to `EXPECTED_OPERATIONS` in `test_frontend_contract_doc.py`
3. Add the operation to the `## Exact OpenAPI operation inventory` section in `docs/frontend-api-contract.md`
4. Run both contract tests to confirm lock-step

---

## 8. Writing New Tests

### Backend

**Guidelines:**

- **Prefer parametrized tests** over duplicated test functions. See `test_graph_boundaries_have_full_json_sentinels` for the pattern.
- **Use `live_client` fixture** for integration tests that need the full stack (FastAPI + Neo4j). The fixture reseeds the database, which is safe because seeding is idempotent.
- **Use `live_database` fixture** for tests that need direct database access without the HTTP layer (e.g., seed integrity, repository behavior).
- **Use fakes for auth/service tests** — `FakeUserRepo`, `FakeGoogleVerifier`, `FakeSession`, `FakeTransaction` keep tests fast and deterministic.
- **Always clean up** fixture data created in the database — use `try: ... finally: ...` blocks with cleanup queries.
- **Never hardcode Neo4j credentials or connection strings** in test assertions. Use `conftest.py` environment defaults.
- **Test error cases first** — verify the fail-closed paths (invalid input, missing data, unavailable database) before testing the happy path.

**Template for a new backend test:**

```python
import pytest
from fastapi.testclient import TestClient


def test_new_feature_boundary_works(live_client: TestClient) -> None:
    # Arrange — pick a known boundary
    url = "/api/series/series_dexter/some-endpoint?visible_until_order=1"

    # Act
    response = live_client.get(url)

    # Assert — status code first
    assert response.status_code == 200, response.json()
    payload = response.json()

    # Assert — expected content present
    assert "expected_thing" in str(payload)

    # Assert — forbidden content absent (fail-closed)
    import json
    serialized = json.dumps(payload, sort_keys=True)
    assert "spoilery_thing" not in serialized.lower()
```

### Frontend

**Guidelines:**

- **Stub `react-cytoscapejs`** for any test that renders `GraphCanvas`, `DetailPanel`, or `App`. See `App.test.tsx` for the full stub pattern.
- **Mock `fetch` with `vi.stubGlobal`** — return fixture data from `src/test/fixtures/graphResponse.ts`.
- **Use `userEvent.setup()`** for interactions, not `fireEvent`. User events fire at realistic timing.
- **Clear `sessionStorage` in `beforeEach`** to prevent cross-test pollution.
- **Test the empty/loading/error states** first, then the happy path.
- **Use `data-testid`** sparingly — prefer `getByRole`, `getByText`, `findByRole` for accessibility-respecting queries.

**Template for a new frontend test:**

```typescript
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

beforeEach(() => {
  sessionStorage.clear()
  vi.stubGlobal('fetch', vi.fn(() =>
    Promise.resolve({ ok: true, json: async () => ({ /* ... */ }) })
  ))
})

describe('MyComponent', () => {
  it('renders the locked state with no data', () => {
    render(<MyComponent />)
    expect(screen.getByText('Nothing yet')).toBeInTheDocument()
  })
})
```

---

## 9. Troubleshooting

### Backend Tests

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ServiceUnavailable` on every test | Neo4j container not running | `docker compose up -d` |
| `Neo4jDatabase has no driver` | Connection refused on first call | Wait for Neo4j health check, then re-run |
| Test graph counts are wrong | Seed data or boundaries changed | Update `expected` counts in `test_graph_boundaries_have_full_json_sentinels` |
| `setup_database()` hangs | Neo4j container is unhealthy | `docker compose restart neo4j` |
| Tests pass in isolation but fail in suite | Cross-test database pollution | Use `try/finally` cleanup or add cleanup queries in fixtures |

### Frontend Tests

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `TypeError: expect(...).toBeInTheDocument is not a function` | `@testing-library/jest-dom` not augmented for Vitest | Check `src/test/setup.ts` imports `@testing-library/jest-dom/vitest` |
| `hasPointerCapture is not a function` | Missing jsdom stubs in setup | Add `Element.prototype.hasPointerCapture = () => false` in `src/test/setup.ts` |
| `ResizeObserver is not defined` | Missing ResizeObserver stub | Add stub class in `src/test/setup.ts` |
| Canvas click does nothing | Cytoscape stub not firing handlers | Verify `handlers[key]` matches the event key GraphCanvas registers (e.g., `tap:node`, `tap:edge`) |
| `sessionStorage` leaking between tests | Tests not clearing in `beforeEach` | Add `sessionStorage.clear()` in `beforeEach` |

---

## 10. Roadmap & CI Plans

### Current State

- **No CI pipeline** — all testing is manual/local
- **No coverage thresholds** — backend has no `--cov` configuration; frontend has no coverage target
- **No pre-commit hooks** — tests are not enforced before commits

### Planned Improvements

| Priority | Item | Status |
|----------|------|--------|
| 1 | Configure GitHub Actions CI with Neo4j service container | Planned |
| 2 | Add `pytest-cov` with minimum coverage threshold (target: 80%) | Planned |
| 3 | Add frontend coverage reporting (`@vitest/coverage-v8`) | Planned |
| 4 | Add pre-commit hook running both test suites | Planned |
| 5 | Add integration test marker (`@pytest.mark.integration`) to separate fast unit tests from slow integration tests | Planned |
| 6 | Add test-data factories for larger-scale boundary parametrization | Planned |
| 7 | Add Docker Compose test profile with ephemeral Neo4j | Planned |

### Milestone Context

From `ROADMAP.md`, tests matter most for:

- **M3 — Spoiler-aware graph endpoint**: The parametrized boundary tests (see §4.2) were created here and remain the most critical test surface.
- **M6 — User notes and manual editing**: The `test_user_content_*.py` files cover this milestone with CRUD + spoiler-gated read tests.
- **M7 — Revision history**: No tests yet — this is a coverage gap to address when revision endpoints are built.
- **M9 — Spoiler-grounded LLM chat**: Will need new test patterns for LLM output grounded in the spoiler boundary.

---

## 11. Test Inventory Addendum

> Appended by doc supplement pass. The suite has grown substantially since §1/§4.1/§5.1 were last written (9 backend + 6 frontend files documented there). As of this pass there are **29 backend files** (`backend/tests/`, including `conftest.py`) and **24 frontend test files** (`frontend/src/**/*.test.{ts,tsx}`). The tables in §4.1 and §5.1 are preserved as-is; the files below are the ones not yet covered by those tables.

### 11.1 Backend — files not in §4.1

| File | Lines | What it covers |
|------|-------|----------------|
| `test_extraction_models.py` | 206 | Extraction schema and source-connector interface models (PREP-01, PREP-04) |
| `test_candidate_ingest.py` | 124 | Candidate ingest, storage isolation, and spoiler filtering (PREP-02, PREP-05) |
| `test_candidate_review.py` | 107 | Candidate review workflow: approve, reject, edit (PREP-03) |
| `test_revision_models.py` | 113 | `RevisionAction`/`RevisionResponse` domain models: enum values, construction, optional before/after, extra-field rejection, naive-datetime rejection |
| `test_revisions.py` | 627 | Revision history endpoints: create/update/delete logging, list filters, single-revision get, hidden-revision 404, revert (restores content, restores deleted notes) |
| `test_progress_api.py` | 416 | Watch-progress persistence API (RAG-01), live Neo4j |
| `test_llm_provider.py` | 481 | LLM provider abstraction (RAG-04): deterministic `FakeLLMProvider`, OpenAI-compatible provider behavior |
| `test_retrieval_tools.py` | 912 | Allowlisted retrieval tools (RAG-02, RAG-03), live Neo4j seeded with Dexter S01E01-03 |
| `test_retrieval_pipeline.py` | 479 | Retrieval-pipeline hardening (RAG-05..RAG-08): context normalization, dedup by stable ID |
| `test_prompt_injection.py` | 325 | Prompt-injection defense (RAG-06 / T-06-06) against PRD-quoted malicious strings |
| `test_citations.py` | 410 | Citation-validation hardening (RAG-07, RAG-08 / T-06-09): rejects model-scripted citations without matching evidence |
| `test_conversational_tone.py` | 381 | Conversational-tone policy: friendly, grounded, spoiler-safe phrasing instead of robotic refusals |
| `test_chat_api.py` | 1055 | Chat API vertical slice (RAG-04..RAG-10), live Neo4j, deterministic fake LLM |
| `test_chat_persistence.py` | 359 | Chat session/message persistence at the repository layer (RAG-09), live Neo4j |
| `test_session_repository.py` | 70 | Neo4j-persistent session repository; regression test for `HAS_SESSION` relationship-direction bug (T-AUTH-01) |
| `test_settings_api.py` | 264 | Settings API (LLM provider configuration): auth guard, masked GET, PUT persistence with blank-key-keeps-existing semantics |
| `test_change_set_api.py` | 668 | ChangeSet Stage 1 (Propose) vertical slice (RAG-11, RAG-13) |
| `test_change_set_confirmation.py` | 415 | ChangeSet Stage 2 idempotency, staleness, and reject (RAG-12, RAG-14) |
| `test_change_set_protection.py` | 377 | Canonical/candidate protection for ChangeSet propose (RAG-13): rejects direct mutation of `origin:canonical`/`candidate` |
| `test_change_set_revision.py` | 579 | ChangeSet Stage 3 (Revert) (RAG-15) |

### 11.2 Frontend — files not in §5.1

| File | Lines | What it covers |
|------|-------|----------------|
| `api/changeSet.test.ts` | 85 | ChangeSet API client |
| `api/chat.test.ts` | 267 | Chat API client, including `streamMessage` |
| `api/progress.test.ts` | 60 | Watch-progress API client |
| `components/chat/ChatLauncher.test.tsx` | 23 | Chat launcher trigger button |
| `components/chat/ChatSheet.test.tsx` | 70 | Chat sheet/drawer container |
| `components/chat/ChatPanel.test.tsx` | 267 | Chat panel, including streaming/error states |
| `components/chat/MessageList.test.tsx` | 147 | Chat message list rendering |
| `components/chat/MessageBubble.test.tsx` | 85 | `MessageBubble`, `StreamingMessageBubble`, `FailedMessageBubble` variants |
| `components/chat/CitationChip.test.tsx` | 84 | Citation chip rendering/interaction |
| `components/chat/ChangeSetCard.test.tsx` | 207 | ChangeSet proposal card in chat |
| `components/chat/SessionPicker.test.tsx` | 116 | Chat session picker/switcher |
| `components/detail/RevisionHistoryPanel.test.tsx` | 185 | Revision history panel in the detail inspector |
| `components/settings/SettingsPage.test.tsx` | 142 | Settings page (LLM provider configuration UI) |
| `components/graph/graphElements.test.ts` | 30 | `graphToElements` conversion (backend graph payload → Cytoscape elements) |
| `components/graph/relationshipStyles.test.ts` | 17 | `edgeColorFor` relationship-to-color mapping |
| `hooks/useChatMessages.test.tsx` | 131 | `useChatMessages` hook |
| `hooks/useChatSessions.test.tsx` | 88 | `useChatSessions` hook |
| `hooks/useRevisions.test.tsx` | 154 | `useRevisions` hook |
