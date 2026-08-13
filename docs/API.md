<!-- generated-by: gsd-doc-writer -->
# Spoilerless HTTP API

The backend is a FastAPI application defined by `spoilerless.app.main:app`. Its generated OpenAPI document is the authoritative machine-readable contract.

- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- API version: `0.1.0`
- Registered surface: **52 method/path operations over 39 path templates** (locked by `spoilerless/tests/test_frontend_contract_doc.py`)

All paths below are relative to the backend origin. JSON field names use `snake_case`. The deployed production backend origin is `https://api.spoilerless.net` (Render service `spoilerless` — build `uv sync --frozen`, start `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`; see [DEPLOYMENT.md](./DEPLOYMENT.md)); local development serves the same app at `http://localhost:8000`.

## Authentication

### Google sign-in

`POST /api/auth/google` accepts a Google ID token:

```json
{
  "credential": "<Google ID token>"
}
```

`credential` is required and must be non-empty. The backend verifies the token with `google-auth`, including its signature, audience, issuer, and expiry. If verification succeeds, the backend upserts an `AppUser`, creates a server-side session, sets an opaque session cookie, and returns:

```json
{
  "user": {
    "id": "user:example",
    "email": "user@example.com",
    "display_name": "Example User",
    "avatar_url": "https://example.invalid/avatar.png",
    "role": "user",
    "created_at": "2026-08-02T12:00:00Z",
    "updated_at": "2026-08-02T12:00:00Z"
  }
}
```

`google_sub` is an internal identity key and is deliberately excluded from `UserPublic` responses.

The sign-in and logout routes check the request `Origin`, or the origin reconstructed from `Referer`, against `FRONTEND_ORIGINS` via the `verify_origin` dependency. The check fails closed: a request with neither header, or with a `Referer` that cannot be parsed into a candidate origin, is rejected with `403 AUTH_ORIGIN_NOT_ALLOWED`. A literal `*` in `FRONTEND_ORIGINS` disables the check. `SameSite=Lax` on the session cookie is the complementary cookie-level defense against cross-site POSTs.

### Session cookie

Authenticated routes read the cookie named by `SESSION_COOKIE_NAME` (default `session`). Clients making cross-origin browser requests must include credentials, for example:

```javascript
fetch("/api/auth/me", { credentials: "include" });
```

The cookie has these attributes:

| Attribute | Value |
|---|---|
| `HttpOnly` | `true` |
| `Secure` | `SESSION_COOKIE_SECURE` (default `true`) |
| `SameSite` | `SESSION_COOKIE_SAMESITE` (default `lax`; `strict` or `none` are supported) |
| `Path` | `/` |
| `Domain` | Not set |

The raw cookie value is generated with `secrets.token_urlsafe(48)`. Only its SHA-256 hash is stored in a Neo4j `Session` node linked from the owning `AppUser` by `HAS_SESSION`. The server-side TTL is `SESSION_TTL_SECONDS` (default 604800 seconds, seven days). Validating a session never extends its expiry (no slide-on-read); expiry is enforced by an `expires_at` check at read time, and a background sweep deletes expired and revoked `Session` and `ShareToken` nodes hourly (started only when the database is reachable at startup).

- `GET /api/auth/me` requires a valid session and returns `UserResponse`.
- `POST /api/auth/logout` revokes a supplied session and deletes the cookie. It returns `204` even when no cookie is supplied. It is not session-gated but carries the same `verify_origin` dependency as sign-in.

### Which endpoints require a session?

Routes using `CurrentUserDependency` (directly, or transitively via `RequireAdminDependency`) require authentication:

- `GET /api/auth/me`
- both watch-progress operations
- all chat operations
- all ChangeSet operations
- both LLM-settings operations
- candidate ingest, edit, approve, and reject operations
- all user-content write operations: create/update/delete for notes, custom nodes, and custom relationships
- `POST /api/series/{series_id}/revisions/{revision_id}/revert`
- create, list, and revoke share-link operations

User-content writes and revision revert are additionally owner-scoped: mutating a resource with a known different owner returns `403 FORBIDDEN`, and admins bypass the check. Direct user-content mutations treat legacy resources with no stored owner as admin-only and fail closed. Revision revert currently differs: in both its `Updated` live-resource branch and its `Deleted` snapshot branch, a missing `user_id` skips the non-admin owner check, so legacy ownerless revisions are not admin-only. Share-token revocation is limited to the creator or an admin.

Series and episode reads, the graph read, shortest-path, Markdown export, public share-token graph, notes/custom-node/custom-relationship reads, revision reads, candidate list/read, health, Google sign-in, and logout do not require a session. The graph, episodes, shortest-path, and export routes take an optional session (`OptionalUserDependency`): anonymous readers are fixed at spoiler boundary order 1. When an authenticated reader has persisted progress, the effective boundary is clamped to that split progress; without a progress row, each route keeps its requested or route-default boundary (the shortest-path route's fallback is detailed below). The public share-token graph does not resolve a session; it always uses the boundary captured in the token record.

### Which endpoints require the admin role?

`RequireAdminDependency` (`spoilerless/app/api/deps.py`) first resolves the session via `CurrentUserDependency`, then rejects with `403 FORBIDDEN` unless the resolved `AppUser.role` is `"admin"`. `role` is derived server-side from `ADMIN_EMAILS` membership at Google sign-in and is never accepted from a request body. Admin-gated routes:

- `PATCH /api/series/{series_id}/candidates/{claim_id}` (edit)
- `POST /api/series/{series_id}/candidates/{claim_id}/approve`
- `POST /api/series/{series_id}/candidates/{claim_id}/reject`
- `POST /api/series/{series_id}/change-sets/{change_set_id}/confirm`
- `GET /api/settings/llm`
- `PUT /api/settings/llm`

Candidate read, and ChangeSet propose/reject/revert, are intentionally **not** admin-gated — only the routes that commit candidate claims or an AI-proposed ChangeSet to the shared canonical graph, or mutate the shared LLM settings, require the admin role. Candidate ingest and user-content writes require a valid session but not the admin role.

Share-link creation and listing require a session but not the admin role. Revocation normally requires the token creator; an admin may revoke another user's token, but the route is not admin-only.

## Endpoints Overview

| Method | Path | Description | Auth Required |
|---|---|---|---|
| GET | `/health` | Check service and Neo4j connectivity | No |
| GET | `/api/series` | List series | No |
| GET | `/api/series/{series_id}` | Read one series | No |
| GET | `/api/series/{series_id}/episodes` | List episodes for a series | No |
| GET | `/api/series/{series_id}/graph` | Read the spoiler-filtered graph | No |
| GET | `/api/series/{series_id}/graph/visualization` | Read a task-specific visualization projection (6 view types) | No |
| GET | `/api/series/{series_id}/graph/expand` | Read an allowlisted semantic expansion delta (uncached) | No |
| POST | `/api/series/{series_id}/graph/path` | Find the shortest visible path between two entities | No |
| GET | `/api/series/{series_id}/export` | Export the visible graph as Markdown | No |
| POST | `/api/series/{series_id}/notes` | Create a user note | Yes |
| GET | `/api/series/{series_id}/notes` | List visible notes | No |
| GET | `/api/series/{series_id}/notes/{note_id}` | Read one visible note | No |
| PATCH | `/api/series/{series_id}/notes/{note_id}` | Update note content | Yes |
| DELETE | `/api/series/{series_id}/notes/{note_id}` | Delete a note | Yes |
| POST | `/api/series/{series_id}/custom-nodes` | Create a custom node | Yes |
| GET | `/api/series/{series_id}/custom-nodes/{node_id}` | Read one visible custom node | No |
| PATCH | `/api/series/{series_id}/custom-nodes/{node_id}` | Update a custom node label | Yes |
| DELETE | `/api/series/{series_id}/custom-nodes/{node_id}` | Delete a custom node | Yes |
| POST | `/api/series/{series_id}/custom-relationships` | Create a custom relationship | Yes |
| GET | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Read one visible custom relationship | No |
| PATCH | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Update a custom relationship predicate | Yes |
| DELETE | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Delete a custom relationship | Yes |
| POST | `/api/auth/google` | Sign in with a Google ID token | No |
| GET | `/api/auth/me` | Get the current authenticated user | Yes |
| POST | `/api/auth/logout` | Revoke a session and clear its cookie | No |
| GET | `/api/series/{series_id}/revisions` | List visible revisions | No |
| GET | `/api/series/{series_id}/revisions/{revision_id}` | Read one visible revision | No |
| POST | `/api/series/{series_id}/revisions/{revision_id}/revert` | Revert the resource state captured by a revision | Yes |
| POST | `/api/series/{series_id}/candidates/ingest` | Ingest an extraction batch | Yes |
| GET | `/api/series/{series_id}/candidates` | List candidate claims | No |
| GET | `/api/series/{series_id}/candidates/{claim_id}` | Read one candidate claim | No |
| PATCH | `/api/series/{series_id}/candidates/{claim_id}` | Edit a candidate claim | Yes (admin) |
| POST | `/api/series/{series_id}/candidates/{claim_id}/approve` | Approve a candidate claim | Yes (admin) |
| POST | `/api/series/{series_id}/candidates/{claim_id}/reject` | Reject a candidate claim | Yes (admin) |
| GET | `/api/series/{series_id}/progress` | Read the current user's watch progress | Yes |
| POST | `/api/series/{series_id}/progress` | Upsert the current user's watch progress | Yes |
| POST | `/api/series/{series_id}/chat/sessions` | Create a chat session | Yes |
| GET | `/api/series/{series_id}/chat/sessions` | List the current user's chat sessions | Yes |
| GET | `/api/series/{series_id}/chat/sessions/{session_id}` | Read a session and visible messages | Yes |
| DELETE | `/api/series/{series_id}/chat/sessions/{session_id}` | Delete a session and its messages | Yes |
| POST | `/api/series/{series_id}/chat/sessions/{session_id}/messages` | Generate a grounded answer | Yes |
| POST | `/api/series/{series_id}/chat/sessions/{session_id}/messages/stream` | Stream a grounded answer with SSE | Yes |
| POST | `/api/series/{series_id}/change-sets` | Propose a graph ChangeSet | Yes |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/confirm` | Confirm and apply a ChangeSet | Yes (admin) |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/reject` | Reject a ChangeSet | Yes |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/revert` | Revert an applied ChangeSet | Yes |
| GET | `/api/settings/llm` | Read effective LLM settings with the key masked | Yes (admin) |
| PUT | `/api/settings/llm` | Update LLM settings | Yes (admin) |
| POST | `/api/share` | Create a token-gated graph snapshot | Yes |
| GET | `/api/share` | List the current user's active share tokens | Yes |
| GET | `/api/share/{token}/graph` | Read a token-gated graph snapshot | No (valid token) |
| DELETE | `/api/share/{token}` | Revoke a share token | Yes (owner or admin) |

## Request and Response Formats

### General conventions

- Normal request and response bodies use `application/json`.
- Successful reads and updates normally return `200`.
- Resource creation returns `201`, except candidate batch ingestion and progress upsert, which return `200`.
- User-content deletes, chat-session deletion, and logout return `204` with no body. Share-token revocation is the exception: `DELETE /api/share/{token}` returns `200` with `{"status":"revoked"}`.
- Pydantic request models configured with `extra="forbid"` reject unknown request fields; response typing, including an untyped `dict` response, does not affect request validation.
- The SSE chat route returns `text/event-stream`; the Markdown export route returns `text/markdown`.

### Series, episodes, health, and graph

`GET /health` returns `200` when Neo4j is reachable or `503` when it is not:

```json
{
  "status": "ok",
  "database": "connected",
  "service": "spoilerless-backend"
}
```

The `503` body has the same shape with `"status": "degraded"` and `"database": "unavailable"`. A `HEAD /health` variant (omitted from the OpenAPI schema) returns the same status codes for uptime monitors.

`GET /api/series` returns `SeriesResponse[]`; a single series has `id`, `title`, and `slug`. `GET /api/series/{series_id}/episodes` returns `EpisodeResponse[]` with `id`, `series_id`, season and episode numbers, `episode_order`, `code`, `title`, `visible_from_order`, and nullable `display_title`, `is_unlocked`, and `is_current_view` display fields. The service masks episode metadata above the effective boundary; the frontend is not expected to perform spoiler masking itself.

`GET /api/series/{series_id}/graph` requires the positive integer query parameter `visible_until_order`. The value must identify a persisted episode order for that series. Anonymous readers are fixed at order 1 regardless of the parameter — a client-chosen boundary never widens the spoiler window without a session, and the persisted-episode check resolves against the effective order. Authenticated readers with a progress row are clamped to their persisted split progress; without one, the requested boundary is used. The response is:

```json
{
  "series": {"id": "series_dexter", "title": "Dexter", "slug": "dexter"},
  "visible_until_order": 1,
  "effective_view_order": 1,
  "nodes": [],
  "edges": [],
  "claims": [],
  "sources": [],
  "evidence": []
}
```

Every graph node and narrative item is filtered by `visible_from_order`. Claims also honor `valid_from_order` and `valid_until_order`. Returned edges are closed over the returned nodes: both endpoints must be present. Canonical/candidate claim projections carry their Claim ID; structural edges and user-authored relationship Claims both carry `claim_id: null`. User-origin edges are emitted only when both endpoints survive same-series node visibility filtering, so clients must not use null `claim_id` alone to classify an edge as structural. `GraphNode` additionally supports optional `image_url` and `image_source_url` fields.

#### Shortest path

`POST /api/series/{series_id}/graph/path` finds the shortest visible path between two entities:

```json
{
  "source_entity_id": "dexter:character:dexter_morgan",
  "target_entity_id": "dexter:character:debra_morgan",
  "max_hops": 4
}
```

`source_entity_id` and `target_entity_id` are required. `max_hops` is optional, defaults to the server ceiling `MAX_PATH_HOPS` (4), and is capped at 4 by the request model. The request has no boundary field: since PROB-09/#59, the effective boundary resolves from the caller's persisted progress alone — never from the `MAX_PATH_HOPS` hop constant. Anonymous readers are fixed at order 1, and authenticated readers without a progress row are likewise fail-closed to order 1 (the same read surface an anonymous visitor gets); with a progress row, the boundary is `effective_view_order(view_as_of_order, watched_through_order)` from the persisted split. The resolved order must identify a persisted episode of the series, or the route returns `422 INVALID_VISIBLE_UNTIL_ORDER`. The walk traverses only visible claims, so a path that exists only through a hidden intermediate node is indistinguishable from no path at all. The response shape is `{"found", "path", "edges", "hops"}`; when either endpoint is missing or not visible at the boundary, `found` is `false` with empty arrays, and a self-path returns `found: true` with zero hops. Errors: `404 SERIES_NOT_FOUND`, `422 INVALID_VISIBLE_UNTIL_ORDER`, `503 DATABASE_UNAVAILABLE`.

#### Markdown export

`GET /api/series/{series_id}/export` renders the visible graph as Markdown (feature D-11). It accepts the same optional `visible_until_order` query parameter (defaults to 1, with the same anonymous-fixed-at-1 and progress-clamped boundary resolution as the graph read) and an optional `target_id` query parameter that narrows the export to a single visible resource and its claims. The response is `text/markdown` with a `Content-Disposition: attachment` header naming the file `spoilerless-{slug}-order-{N}.md` for a whole-series export or `spoilerless-{nodeLabel}.md` for a single-target export (labels are slugified; a target that is not visible at the boundary renders a stub note instead of failing). The Markdown is assembled from the same filtered read path as the graph GET — there is no second filter implementation. Errors: `404 SERIES_NOT_FOUND`, `422 INVALID_VISIBLE_UNTIL_ORDER`, `503 DATABASE_UNAVAILABLE`.

#### Visualization projections (Phase 10, D-29/D-30)

`GET /api/series/{series_id}/graph/visualization` returns a library-neutral `VisualizationDTO` (`metadata` with `projection_version`, `view_type`, `series_id`, `series_title`, `episode_order`, `visible_until_order`, `effective_view_order`; plus `nodes`, `edges`, `groups`, `timeline`, and `focus`). Required query `view` is the exact enum `episode_overview|character_network|plot_threads|investigation|full|graphrag_focus`; `episode_order` is a required positive integer with the same persisted-episode resolution and anonymous-clamp semantics as `visible_until_order` (anonymous readers are fixed at order 1; authenticated readers are clamped by persisted progress; an order that does not identify a persisted Episode returns `422 INVALID_VISIBLE_UNTIL_ORDER`). `focus` is `null` for every view except `graphrag_focus`, where it references the primary focus node — always resolvable inside the DTO. Repeated optional `focus_id` values are accepted only for `graphrag_focus` and capped at 20 distinct ids; any other view sending `focus_id` (or `graphrag_focus` without one) returns `422 INVALID_REQUEST`. Missing series: `404 SERIES_NOT_FOUND`; database failures: `503 DATABASE_UNAVAILABLE`.

Projection responses are cached keyed by **series, effective order, view type, projection version, graph revision (Redis-local per-series cache epoch), and user scope**; `graphrag_focus` keys additionally include a deterministic digest of the validated, deduplicated, sorted focus ids. Cache entries can never cross-return a view, boundary, or focus set; an epoch-read failure bypasses the cache.

#### Semantic expansion (Phase 10, D-21/D-29)

`GET /api/series/{series_id}/graph/expand` returns a strict `VisualizationDTO` **delta** — the anchor node, the bounded additions, and the edges between them; `metadata.view_type` carries `expansion:{key}` so a delta is always distinguishable from a view projection. Required `expansion_key` is the exact allowlisted enum `family|work|conflict|episode_events|clues|locations|evidence`; required `node_id` is a non-empty visible graph resource to expand around (hidden and unknown anchors are indistinguishable — both return sanitized `422 INVALID_REQUEST`); required `episode_order` uses the shared boundary resolver. Optional `limit` defaults to 12 and is constrained to **1..25** — no request or server result exceeds the hard max of 25 additions. Additions are ordered deterministically by (reveal order, id) before the limit applies — never randomly. Expansion responses are **never cached** in Phase 10 (`T10-CACHE-06`): every request resolves the boundary and computes the delta from the current safe graph. Errors: `404 SERIES_NOT_FOUND`, `422 INVALID_REQUEST`, `422 INVALID_VISIBLE_UNTIL_ORDER`, `503 DATABASE_UNAVAILABLE`.

### Notes

Create a note:

```json
{
  "target_type": "Character",
  "target_id": "dexter:character:dexter_morgan",
  "content": "Remember this detail."
}
```

| Field | Constraints |
|---|---|
| `target_type` | `Character` or `Claim` |
| `target_id` | 1–255 characters |
| `content` | 1–4000 characters |

The server creates `id`, `series_id`, owner `user_id`, `origin: "user"`, `visible_from_order`, `created_at`, and `updated_at`. PATCH accepts only `{"content":"..."}`. `GET /notes` requires `visible_until_order`; optional `target_type` and `target_id` filters must be supplied together. Creating, updating, and deleting notes require a valid session; a note is owned by its creator, and mutating another user's note returns `403 FORBIDDEN`.

### Custom nodes

Create a node:

```json
{
  "node_type": "Object",
  "label": "Blood slide",
  "episode_id": "dexter_s01e01"
}
```

`node_type` is one of `Character`, `Event`, `Location`, `Organization`, or `Object`; `label` is 1–200 characters; and `episode_id` is 1–255 characters. Visibility is derived from the referenced same-series episode. PATCH accepts only `{"label":"..."}`. Deleting a node with dependent notes or user relationships returns `409 RESOURCE_CONFLICT`. Create, update, and delete require a valid session and are owner-scoped (`403 FORBIDDEN` for another user's node).

### Custom relationships

Create a relationship:

```json
{
  "source_id": "dexter:character:dexter_morgan",
  "target_id": "dexter:character:debra_morgan",
  "predicate": "FAMILY_OF",
  "episode_id": "dexter_s01e01"
}
```

The supported predicates are `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`, `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, and `KILLS`. Source and target must exist in the same series. PATCH accepts only `{"predicate":"TRUSTS"}`. Create, update, and delete require a valid session and are owner-scoped.

The response uses `source`, `target`, and `type` rather than the request names `source_id`, `target_id`, and `predicate`. In `GET /graph`, user-authored relationships are edge-only records with `claim_id: null`; both endpoints must pass the same series and visibility checks as graph nodes before the edge is emitted.

### Revisions

All revision operations require `visible_until_order` as a positive query integer. Like note and direct custom-content reads, but unlike graph, candidate-read, progress-update, and share-create routes, revision routes do **not** verify that a positive value matches a persisted Episode order; they apply it directly to revision visibility queries.

- `GET /revisions` accepts optional `resource_type` and `resource_id` filters and returns newest revisions first.
- `GET /revisions/{revision_id}` returns a visible `RevisionResponse` or an indistinguishable `404 RESOURCE_NOT_FOUND`.
- `POST /revisions/{revision_id}/revert` restores an `Updated` user resource from `before`, or recreates a `Deleted` resource. It emits a new `Reverted` revision. The route requires a valid session and is owner-scoped: a known owner that differs from the actor produces `403 FORBIDDEN`, while admins bypass the check. In the current implementation, however, the `Updated` branch checks ownership only when the live resource has a non-null `user_id`, and the `Deleted` branch only when the `before` snapshot has one; a missing legacy owner skips the check and lets a non-admin proceed.
- Reverting a `Created` revision returns `422 CANNOT_REVERT_CREATE`.
- Reverting an `Updated` resource whose current origin is canonical or candidate returns `409 CANNOT_REVERT_CANONICAL`. The `Deleted` branch does not check the saved snapshot's origin before recreating it.

A revision contains `id`, `series_id`, `resource_type`, `resource_id`, `action`, nullable `before` and `after` snapshots, actor `user_id`, `created_at`, and `visible_from_order`.

### Candidate extraction and review

`POST /candidates/ingest` accepts an `ExtractionBatchEnvelope` with required extractor metadata and 1–500 claims, and requires a valid session:

```json
{
  "extractor_name": "example-extractor",
  "extractor_version": "1.0.0",
  "run_timestamp": "2026-08-02T12:00:00Z",
  "claims": [
    {
      "schema_version": "0.1",
      "subject_id": "character:dexter",
      "predicate": "KNOWS",
      "object_id": "character:debra",
      "claim_type": "explicit_fact",
      "confidence_level": "high",
      "relationship_effect": "neutral",
      "visible_from_order": 1,
      "valid_from_order": 1,
      "valid_until_order": null,
      "evidence_text": "Visible evidence text.",
      "evidence_locator": "S01E01 00:10:00",
      "source_type": "transcript",
      "source_locator": "S01E01",
      "episode_id": "dexter_s01e01"
    }
  ]
}
```

Ingestion returns `200` with `created` and `errors` arrays. Candidate IDs are deterministic hashes of normalized claim content. Per-claim failures do not fail the batch; they are reported in the 200 body's `errors` array with `code: "INGEST_ERROR"` (a body-level code, not an HTTP error). Both candidate reads require a positive `visible_until_order` query parameter. Omitting it returns `422 INVALID_REQUEST`; a value that is not a persisted episode order for the series returns `422 INVALID_VISIBLE_UNTIL_ORDER`. A candidate hidden above the resolved boundary is indistinguishable from a missing candidate (`404 CANDIDATE_NOT_FOUND`).

PATCH accepts at least one of `label`, `predicate`, `claim_type`, `confidence_level`, `relationship_effect`, `valid_from_order`, `valid_until_order`, `evidence_text`, `evidence_locator`, `source_type`, or `source_locator`. Approve changes `status` to `canonical` while retaining `origin: "candidate"`; reject changes `status` to `rejected`. Candidate edit, approve, and reject operations log revisions.

Edit, approve, and reject each require `RequireAdminDependency`: a valid session **and** an admin-role user, or `403 FORBIDDEN`. Ingest requires a valid session (`CurrentUserDependency`); list and single-claim read remain anonymous.

### Watch progress

`POST /api/series/{series_id}/progress` accepts a strict object with three nullable boundary fields. To confirm progress, send the current split-field form:

```json
{
  "watched_through_order": 3,
  "view_as_of_order": 2
}
```

`visible_until_order` remains a deprecated alias for `watched_through_order`, so `{"visible_until_order":3}` is also accepted. Do not send both confirmation fields. A request containing only `view_as_of_order` is a view-only change: it requires an existing progress row and never lowers `watched_through_order`. When a confirmation omits `view_as_of_order`, the view defaults to the confirmed watched order. Every supplied order must be positive, must identify a persisted episode order for the series, and the resulting invariant is `1 <= view_as_of_order <= watched_through_order`.

The authenticated user and path supply `user_id` and `series_id`; clients cannot submit them. The operation upserts and returns `UserSeriesProgressResponse` with `id`, `user_id`, `series_id`, the backward-compatible `visible_until_order` echo, `watched_through_order`, `view_as_of_order`, computed `effective_view_order`, and `updated_at`. GET returns `404 RESOURCE_NOT_FOUND` when no row exists.

### Chat

Create a session with an optional title of at most 200 characters:

```json
{
  "title": "Season 1 questions"
}
```

An omitted, empty, or whitespace-only title is accepted; the repository normalizes an empty result to `"New conversation"`.

Send a question of 1–4000 characters:

```json
{
  "question": "Who is Debra?"
}
```

The non-streaming response is a `MessageResponseEnvelope`:

```json
{
  "message": {
    "id": "chat-message:example",
    "role": "assistant",
    "content": "A grounded answer.",
    "created_at": "2026-08-02T12:00:00Z",
    "visible_until_order_snapshot": 1,
    "status": "completed"
  },
  "citations": [],
  "graph_focus": {"node_ids": [], "edge_ids": []},
  "proposed_change_set": null
}
```

LLM configuration supports per-request bring-your-own-key (BYOK): the client may override the effective provider settings by sending the `X-LLM-Api-Key`, `X-LLM-Provider`, `X-LLM-Base-URL`, and `X-LLM-Model` headers. When `X-LLM-Api-Key` is present and non-blank, the provider is built exclusively from these header values — the persisted LLM settings and the `LLM_*` environment fallback are not consulted for that request. This request-local bypass does not mean the backend holds no secrets: it also supports an API key persisted in Neo4j through `SettingsService`/`SettingsRepository` and the `LLM_API_KEY` environment fallback. BYOK header values reach only the provider constructor: they never appear in a response model, a log line, or a persisted record. `X-LLM-Provider` selects the wire protocol: `gemini` uses Google's REST API (`x-goog-api-key` auth; `base_url` is optional and falls back to the official Gemini endpoint), while a missing/blank value or `openai_compatible`/`vllm`/`ollama` uses a plain OpenAI-compatible `/chat/completions` call. Without BYOK headers, resolution falls back to persisted stored settings, then the `LLM_*` environment values. A malformed BYOK `base_url` fails with `422 INVALID_REQUEST`.

The server reads the spoiler boundary from persisted progress. If progress is absent on a message path, it creates a progress record at order 1. Chat-session ownership is scoped to the authenticated user and series; foreign, cross-series, and missing sessions all produce `404 RESOURCE_NOT_FOUND`.

The streaming route emits SSE frames:

```text
data: {"type":"text_delta","text":"A grounded"}

event: done
data: {"message":{},"citations":[],"graph_focus":{},"proposed_change_set":null}

```

After streaming starts, failures are reported with `event: error` and a JSON object containing `code` and `message`. Possible in-stream codes include `TOO_MANY_REQUESTS`, `LLM_PROVIDER_UNAVAILABLE`, and `LLM_STREAM_FAILED`.

Persisted user messages move from `pending` to `completed` when the final done envelope is delivered, or to `failed` if generation terminates. Session-detail responses expose that `status` on every message.

### ChangeSets

Propose a ChangeSet:

```json
{
  "series_id": "series_dexter",
  "chat_session_id": "chat-session:example",
  "summary": "Add a relationship",
  "operations": [
    {
      "operation_type": "create_relationship",
      "source_id": "character:dexter",
      "target_id": "character:debra",
      "relationship_type": "FAMILY_OF",
      "episode_id": "dexter_s01e01"
    }
  ]
}
```

`series_id`, `chat_session_id`, and a 1–500-character `summary` are required. `operations` must contain at least one item and is a closed discriminated union of:

`create_node`, `update_node`, `delete_node`, `create_relationship`, `update_relationship`, `delete_relationship`, `create_claim`, `update_claim`, `delete_claim`, `attach_evidence`, `create_note`, `update_note`, and `delete_note`.

Propose validates the complete batch and persists only an `awaiting_confirmation` draft. A requested direct mutation of a canonical/candidate Character or Claim is replaced with a `create_note` annotation; other protected labels cannot accept notes and fail validation, while user-origin targets retain the requested operation. Confirm revalidates and applies the batch transactionally. Confirming an already applied ChangeSet is idempotent. Reject performs no graph mutation. Revert supports only applied ChangeSets whose operations are entirely create-shaped; later conflicting modifications return `409`, and unsupported update/delete reversal returns `422`.

Only confirm requires `RequireAdminDependency` — applying an AI-proposed ChangeSet to the shared canonical graph is admin-only, so a non-admin authenticated user gets `403 FORBIDDEN` before any mutation. Propose, reject, and revert require only a valid session (`CurrentUserDependency`), open to any authenticated user.

### Share links

`POST /api/share` requires a session and accepts:

```json
{
  "series_id": "series_dexter",
  "visible_until_order": 2
}
```

The boundary must be positive and identify a persisted episode order. The route currently validates the requested order but does **not** clamp it to the creator's persisted watch progress. It generates a `secrets.token_urlsafe(32)` raw token, stores only its SHA-256 hash in a Neo4j `ShareToken`, and returns `201` with `token`, `expires_at`, frontend-relative `url` (`/share/{token}`), `series_id`, `visible_until_order`, and `created_at`. The fixed repository TTL is 2,592,000 seconds (30 days).

`GET /api/share` requires a session and returns only the caller's active, unexpired tokens, newest first. Each item contains `id`, `token_hash`, `series_id`, `visible_until_order`, `created_at`, and `expires_at`; the raw token is returned only at creation.

`GET /api/share/{token}/graph` is unauthenticated but requires a valid raw token. It returns the ordinary `GraphResponse` assembled by the same filtered graph service at the token's captured boundary. Invalid, expired, and revoked tokens all return `404 TOKEN_NOT_FOUND`.

`DELETE /api/share/{token}` requires a session and accepts a raw token or token hash. The creator or an admin may revoke it; a different non-admin receives `403 FORBIDDEN`. Success returns `200 {"status":"revoked"}`. Missing or already-revoked tokens return `404 TOKEN_NOT_FOUND`.

### LLM settings

`GET /api/settings/llm` returns the resolved provider, model, stored-or-environment base URL (or `null`), enabled state, prompt language, whether a key is configured, and a masked key. The Gemini default base URL is applied later during runtime provider construction and is not reflected by this response. The full API key is never returned.

`PUT /api/settings/llm` accepts:

```json
{
  "provider": "gemini",
  "api_key": null,
  "base_url": null,
  "model": "gemini-2.0-flash",
  "enabled": true,
  "system_prompt_language": "english"
}
```

`provider` is one of `gemini`, `openai_compatible`, `vllm`, or `ollama`. `vllm` and `ollama` currently route through the same `OpenAICompatibleProvider` implementation as `openai_compatible`; they do not yet have dedicated provider classes. The provider used for a chat request is the effective non-empty stored value, falling back to `LLM_PROVIDER`; disabled or incomplete configuration is rejected before use. OpenAI-compatible requests post to `/chat/completions`. Gemini uses the `generateContent`/`streamGenerateContent` action family rather than that path; the current streaming provider posts to `/v1beta/models/{model}:streamGenerateContent?alt=sse`. `system_prompt_language` is `english` or `turkish`. API keys are stripped before persistence: a non-blank value is stored without surrounding whitespace; an empty or whitespace-only value retains an existing stored key but returns `422 INVALID_REQUEST` when no key is already stored; whitespace-only input is never persisted. `api_key: null` leaves the merged stored key state unchanged. `enabled: null` retains the stored enabled state. Responses expose only `api_key_configured` and `api_key_masked`.

Both routes require `RequireAdminDependency`: a non-admin authenticated user gets `403 FORBIDDEN`; an unauthenticated caller gets `401 AUTH_UNAUTHENTICATED`.

## Error Codes

Normal HTTP errors use this envelope:

```json
{
  "detail": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource not found."
  }
}
```

FastAPI request-validation failures are sanitized to `422 INVALID_REQUEST`; Pydantic field details are not returned by the installed handler. Database exceptions and constraint failures are also mapped centrally. Candidate ingestion is an exception: the envelope is pydantic-validated at the route boundary (a malformed batch returns the sanitized `422 INVALID_REQUEST`), and per-claim failures are reported in the 200 body with `INGEST_ERROR` rather than as HTTP errors. Since PROB-09/#81, the Neo4j driver's `ClientError` (invalid Cypher or parameters — a server bug, not infrastructure) is deliberately excluded from the 503 database mask: a bad statement surfaces as the framework's plain 500 with no error envelope, while `ServiceUnavailable`, `AuthError`, and `Neo4jError` still map to 503.

Every code the API emits is `UPPERCASE_SNAKE_CASE`, enforced by the canonical `ERROR_CODES` registry (32 codes in `spoilerless/app/core/errors.py`): `ErrorDetail.code` must match `^[A-Z][A-Z0-9_]*$` and be registered, so a new or legacy-lowercase code fails fast instead of silently drifting. The shared envelope maps each status to a default code — `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 RESOURCE_NOT_FOUND`, `409 RESOURCE_CONFLICT`, `422 INVALID_REQUEST`, `429 TOO_MANY_REQUESTS`, `503 DATABASE_UNAVAILABLE` — and routes override the default with the specific codes below. Registry membership does not imply live emission: `AUTH_SESSION_EXPIRED` and `AUTH_SESSION_INVALID` remain registered constants but are not raised by the current routes; `INGEST_ERROR` appears only inside a successful candidate-ingest body.

| Status | Code | Meaning |
|---|---|---|
| 401 | `AUTH_UNAUTHENTICATED` | Session cookie absent, invalid, expired, revoked, or not linked to a user |
| 401 | `AUTH_INVALID_GOOGLE_CREDENTIAL` | Google ID-token verification failed |
| 401 | `AUTH_DISABLED` | Google client ID or a valid session TTL is not configured |
| 403 | `FORBIDDEN` | Non-admin on an admin-gated route, or mutation of a resource owned by another user |
| 403 | `AUTH_ORIGIN_NOT_ALLOWED` | Sign-in or logout request origin does not match configured frontend origins (fails closed when neither `Origin` nor `Referer` is present) |
| 403 | `AUTH_EMAIL_NOT_ALLOWED` | Sign-in email is not in the `ALLOWED_EMAILS` allowlist |
| 404 | `SERIES_NOT_FOUND` | Series lookup failed |
| 404 | `RESOURCE_NOT_FOUND` | Resource is absent, foreign, cross-series, or hidden at the boundary |
| 404 | `CANDIDATE_NOT_FOUND` | Candidate claim lookup failed |
| 404 | `TOKEN_NOT_FOUND` | Share token is invalid, expired, revoked, or absent |
| 409 | `RESOURCE_CONFLICT` | Resource state, ownership, dependency, or ChangeSet state conflicts |
| 409 | `CONSTRAINT_VIOLATION` | A Neo4j uniqueness or other database constraint failed |
| 409 | `CHANGESET_STALE` | Progress was lowered after a ChangeSet was proposed |
| 409 | `CANNOT_REVERT_CANONICAL` | Revision target is canonical or candidate content |
| 409 | `RESOURCE_ALREADY_EXISTS` | A deleted revision target was already recreated |
| 409 | `CANNOT_APPROVE_NON_CANDIDATE` | Approval target does not have candidate origin |
| 422 | `INVALID_REQUEST` | Request-model or repository validation failed |
| 422 | `INVALID_VISIBLE_UNTIL_ORDER` | Boundary does not identify a persisted episode order |
| 422 | `INVALID_EXTRACTION_PAYLOAD` | Candidate edit failed mutable-field validation (since PROB-09/#71, ingest/approve/reject no longer map failures to this code) |
| 422 | `CANNOT_REVERT_CREATE` | A creation revision has no prior state to restore |
| 422 | `INVALID_ACTION` | Revision action cannot be reverted by the route |
| 429 | `TOO_MANY_REQUESTS` | A rate-limit window was exceeded, or a chat generation is already in flight for the user |
| 503 | `DATABASE_UNAVAILABLE` | Neo4j is unreachable or rejects authentication |
| 503 | `DATABASE_ERROR` | Another handled Neo4j request error occurred |
| 503 | `AUTH_SERVICE_UNAVAILABLE` | Google verification infrastructure failed |
| 503 | `LLM_DISABLED` | Effective LLM configuration is disabled |
| 503 | `LLM_PROVIDER_UNAVAILABLE` | LLM configuration or provider request is unavailable |
| 500 | — (no envelope) | Unhandled internal error, including invalid Cypher or parameters (driver `ClientError`) — deliberately not masked as 503 since PROB-09/#81 |
| SSE (HTTP 200) | `LLM_STREAM_FAILED` | The streaming LLM call failed after the response opened; emitted only in an `event: error` frame |

An SSE response that has already sent HTTP headers cannot change its status; it uses an `event: error` frame instead. `LLM_STREAM_FAILED` is therefore SSE-only after HTTP `200`, not an HTTP `503` response code.

## Rate Limits

There is no general, catch-all HTTP request-rate limiter. Three route groups carry an explicit Redis-backed limiter (`spoilerless/app/services/rate_limit.py`), enforced with pyrate-limiter's atomic `RedisBucket` against the shared Redis instance — correct across multiple backend workers:

| Route group | Routes | Limit | Key |
|---|---|---|---|
| Login | `POST /api/auth/google` | 10 requests / 300 seconds | Client IP |
| Chat send | `POST .../chat/sessions/{session_id}/messages`, `.../messages/stream` | 20 requests / 60 seconds | Authenticated user ID |
| Content write | `POST`/`PATCH`/`DELETE` on notes, custom nodes, and custom relationships | 30 requests / 60 seconds | Authenticated user ID (client IP when no session is resolved) |

A request that exceeds its window's limit returns `429 TOO_MANY_REQUESTS` using the same error envelope as other errors. The limiter is bound at application startup only when `REDIS_URL` is non-empty; if Redis is not configured, every `RateLimiter` dependency is a no-op and the route runs unthrottled instead of the app failing to start. This is separate from CORS and from authentication — it is enforced independently of whether the request is otherwise valid.

Chat generation additionally has an in-process concurrency guard of **one active generation per user**, independent of the Redis-backed chat-send window above. A second concurrent non-streaming generation returns `429 TOO_MANY_REQUESTS`. The streaming route may report the same condition as an SSE `event: error` frame after the stream has opened, since a rejection after headers are sent cannot change the HTTP status. This guard is process-local and is not itself a distributed or time-window rate limit.

## CORS

FastAPI installs `CORSMiddleware` with:

| Setting | Value |
|---|---|
| Allowed origins | Comma-separated `FRONTEND_ORIGINS`; default `http://localhost:5173` |
| Credentials | Allowed |
| Methods | Explicit list: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` — no wildcard |
| Headers | Explicit list: `Content-Type`, `Authorization`, `X-LLM-Api-Key`, `X-LLM-Provider`, `X-LLM-Base-URL`, `X-LLM-Model` — no wildcard |

CORS controls browser access but does not authenticate a request. Except for the `verify_origin` dependency on Google sign-in and logout, state-changing routes do not perform their own general Origin/Referer or CSRF-token validation; the `SameSite=Lax` session cookie is the complementary defense.

## Security Headers

Every response passes through `_security_headers_middleware` (`spoilerless/app/main.py`), which sets:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' https://accounts.google.com; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self' https://accounts.google.com; frame-src https://accounts.google.com; object-src 'none'; base-uri 'self'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

The CSP permits the Google Identity Services script (`https://accounts.google.com/gsi/client`) used by sign-in, plus hotlinked character images. A request-logging middleware logs one INFO line per request — method, path, status, duration, and a small allowlisted header set — and never logs `Cookie`, `Set-Cookie`, `Authorization`, or any `X-LLM-*` header value.


