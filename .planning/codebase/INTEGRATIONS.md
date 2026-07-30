---
last_mapped: 2026-07-30
focus: tech
---

# Integrations

## Summary

The codebase has two real backend integrations: Neo4j (graph database) and Google Sign-In (identity/authentication, new since the prior snapshot). The frontend now has a full typed API client layer and calls the backend for series/graph/notes/revisions data and session auth. There is still no LLM/extraction-service integration — Phase 5's candidate/extraction pipeline is a schema + ingest API designed to receive claims from a *future* external extractor, not a live integration itself.

## Neo4j

### Configuration

Neo4j connection settings are modeled in `backend/app/core/config.py` (`Settings`, pydantic-settings, `.env` loading enabled):

- `neo4j_uri`
- `neo4j_username`
- `neo4j_password`
- `neo4j_database`, defaulting to `neo4j`

`.env` is gitignored; `.env.example` exists at repo root documenting the expected keys (contents not read here — see forbidden-files policy).

### Driver Ownership

`backend/app/graph/database.py` defines `Neo4jDatabase`:

- Takes a `Settings` instance (now passed explicitly from `get_settings()` in `main.py`'s lifespan, rather than only a module-level singleton).
- Creates a `neo4j.GraphDatabase` async driver with basic auth via `.open()`.
- Exposes dependency-injectable access via `get_database` (used as a FastAPI `Depends` across `auth.py`, `candidates.py`, `revisions.py`, `series.py`, `graph.py`, `user_content.py`).
- `verify_connection()` / `close()` for lifecycle management.

### FastAPI Lifespan

`backend/app/main.py` opens the database and session repo in the lifespan hook and attaches both to `app.state`. Startup connectivity verification failures are caught and treated as "degraded" rather than fatal — `/health` reports live status (`{status, database, service}`), returning 503 when Neo4j is unavailable. This is a change from the prior snapshot's fail-fast description.

### Query Usage

Cypher queries are used directly (no ORM) across:

- `backend/app/api/series.py` — series/episode listing.
- `backend/app/api/graph.py` — spoiler-boundary-filtered graph reads.
- `backend/app/api/revisions.py` — revision history reads (`REVISION_LIST_QUERY`, `REVISION_GET_QUERY`), filtered by `visible_from_order` boundary.
- `backend/app/api/candidates.py` — extraction candidate claim ingest/list/get/edit/review, keyed on `Claim {id, series_id}` nodes.
- `backend/app/graph/candidates.py` — `CandidateRepository`, backing store for candidate claims.
- `backend/app/repository/session.py`, `backend/app/repository/user.py`, `backend/app/repository/user_content.py` — session, user, and notes/watch-progress persistence.
- `backend/app/revisions/` — revision repository, writes an audit trail (`Revision` nodes) for structural/content edits.
- `backend/app/graph/seed.py` / `backend/app/graph/setup.py` — constraint/index creation and metadata seeding from `data/dexter/metadata/`.

## Google Sign-In / Authentication (new since prior snapshot)

### Backend

- `backend/app/api/auth.py` — `/api/auth` router: Google credential verification endpoint, session issuance, logout.
- `backend/app/services/auth.py` — `AuthService`, wraps `google-auth` ID-token verification (`GoogleTransportError`, `GoogleVerificationError` as distinct failure modes).
- `backend/app/domain/auth.py` — `GoogleAuthRequest`, `UserPublic`, `UserResponse` models.
- `backend/app/repository/session.py` — `SessionRepository` / `InMemorySessionRepository`, backing session storage; also Neo4j-backed (`Neo4jSessionRepository`, wired in `main.py`).
- `backend/app/repository/user.py` — user persistence.
- Session cookie: HttpOnly, name/TTL/secure-flag configurable via `Settings` (`session_cookie_name`, `session_ttl_seconds`, `session_cookie_secure`).
- CSRF mitigation: `verify_origin` dependency checks `Origin`/`Referer` against `settings.frontend_origins` on state-changing auth routes, complementing `SameSite=Lax` on the cookie.
- Config: `settings.google_client_id` (Google OAuth 2.0 client ID for ID-token verification), `settings.frontend_origins` (drives both CORS and CSRF checks).

### Frontend

- `frontend/src/components/auth/LoginPage.tsx` — integrates Google Identity Services via the global `window.google.accounts.id` script (`initialize`, `renderButton`, `cancel`), not an npm SDK.
- `frontend/src/providers/AuthProvider.tsx`, `AuthContext.ts`, `useAuth.ts` — React context wrapping session state.
- `frontend/src/api/auth.ts` — typed client calling `/api/auth` endpoints.
- `frontend/src/types/auth.ts` — auth type definitions.

## Frontend API Client Layer (new since prior snapshot)

The prior snapshot noted "no frontend API client abstraction yet." This is now fully built out:

- `frontend/src/api/client.ts` — shared `apiFetch<T>` wrapper: `credentials: 'include'` on every request (sends the HttpOnly session cookie), parses the backend's `{detail: {code, message}}` error envelope into a typed `ApiError`.
- `frontend/src/api/series.ts`, `graph.ts`, `revisions.ts`, `userContent.ts`, `auth.ts` — per-resource typed clients, each paired with a `hooks/use*.ts` hook (`useSeries`, `useEpisodes`, `useGraph`, `useRevisions`, `useNotes`, `useWatchProgress`).
- `frontend/vite.config.ts` proxies `/api` to `http://127.0.0.1:8000` in dev; production origin resolution not otherwise configured (no env-driven base URL detected).

## Browser/CORS Integration

CORS is now driven by `settings.frontend_origins` (comma-separated, default `http://localhost:5173`) rather than hardcoded in `main.py`, with `allow_credentials=True` required for the session cookie to be accepted cross-origin.

## Candidate / Extraction Pipeline (Phase 5 — backend-only, no live external integration)

This is a schema and review-workflow foundation for a *future* external extraction step (e.g., an LLM-based extractor), not a running integration:

- `backend/app/domain/extraction.py` — `EvidencePayload`, `ExtractionBatchEnvelope`, and related models define the contract any future connector must produce (evidence text, locator, episode ID, content hash). Explicitly documented as "not a running service."
- `backend/app/api/candidates.py` — `/api/series/{series_id}/candidates` ingest endpoint accepts batches conforming to this contract; list/get/edit endpoints and a review-decision flow (approve/reject, tied into `RevisionRepository`) let a human curator process candidate claims.
- `backend/app/graph/ontology.py` + `ontology/*.yaml` — validates claim types, predicates, confidence levels, and relationship effects against a versioned allowlist (`ONTOLOGY_VERSION = "0.1"`).
- Candidate claims are stored as `Claim` nodes with a `status` field (candidate/approved/rejected) and `origin` field distinguishing extracted vs. manually-authored content.
- **Gap driving Phase 05.1:** there is no frontend UI to review, edit, or approve/reject these candidates — `frontend/src/` has no `candidates` API client, hook, or component yet. This is the next planned phase.

## External Web Links

None detected in current frontend components — the prior snapshot's scaffolded Vite template links (Vite/React/GitHub/Discord docs) are no longer present; `App.tsx` now renders the actual product shell (`AppShell`, `LoginPage`, graph canvas, detail panel).

## Missing or Not Yet Present

- No LLM provider integration in backend code — the extraction/candidate pipeline is a receiving contract, not a live extractor call.
- No candidate-review frontend UI yet (target of upcoming Phase 05.1).
- No Docker Compose or managed Neo4j setup file checked in.
- No CI configuration under `.github/`.
- No production API base-URL configuration detected on the frontend beyond the Vite dev proxy.

---

*Integration audit: 2026-07-30*
