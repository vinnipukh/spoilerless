<!-- generated-by: gsd-doc-writer -->
# HD Graf Cehennemi HTTP API

The backend is a FastAPI application defined by `backend.app.main:app`. Its generated OpenAPI document is the authoritative machine-readable contract.

- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- API version: `0.1.0`
- Registered surface: **44 method/path operations over 32 path templates**

All paths below are relative to the backend origin. JSON field names use `snake_case`. No production base URL is defined in the repository. <!-- VERIFY: deployed backend base URL -->

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
    "created_at": "2026-08-02T12:00:00Z",
    "updated_at": "2026-08-02T12:00:00Z"
  }
}
```

`google_sub` is an internal identity key and is deliberately excluded from `UserPublic` responses.

The sign-in route checks the request `Origin`, or the origin reconstructed from `Referer`, against `FRONTEND_ORIGINS` when reconstruction succeeds. A malformed `Referer` that raises during parsing, such as one with an invalid port, is treated as having no candidate origin and is allowed. It returns `403 AUTH_ORIGIN_NOT_ALLOWED` for a mismatch. A request with neither header is allowed.

### Session cookie

Authenticated routes read the cookie named by `SESSION_COOKIE_NAME` (default `session`). Clients making cross-origin browser requests must include credentials, for example:

```javascript
fetch("/api/auth/me", { credentials: "include" });
```

The cookie has these attributes:

| Attribute | Value |
|---|---|
| `HttpOnly` | `true` |
| `Secure` | `SESSION_COOKIE_SECURE` (default `false`) |
| `SameSite` | `Lax` |
| `Path` | `/` |
| `Domain` | Not set |

The raw cookie value is generated with `secrets.token_urlsafe(48)`. Only its SHA-256 hash is stored in a Neo4j `Session` node linked from the owning `AppUser` by `HAS_SESSION`. The server-side TTL is `SESSION_TTL_SECONDS` (default 604800 seconds, seven days) and is extended whenever an authenticated request successfully resolves the current user. Expired or revoked sessions are rejected lazily; no background cleanup task is implemented.

- `GET /api/auth/me` requires a valid session and returns `UserResponse`.
- `POST /api/auth/logout` revokes a supplied session and deletes the cookie. It returns `204` even when no cookie is supplied.

### Which endpoints require a session?

Only routes using `CurrentUserDependency` require authentication:

- `GET /api/auth/me`
- both watch-progress operations
- all chat operations
- all ChangeSet operations
- both LLM-settings operations

Series, episodes, graph, notes, custom nodes, custom relationships, revisions, candidate review, health, Google sign-in, and logout do **not** currently require a session. In particular, the current code does not apply a user identity or ownership dependency to user-content, revision, or candidate mutation routes.

## Endpoints Overview

| Method | Path | Description | Auth Required |
|---|---|---|---|
| GET | `/health` | Check service and Neo4j connectivity | No |
| GET | `/api/series` | List series | No |
| GET | `/api/series/{series_id}` | Read one series | No |
| GET | `/api/series/{series_id}/episodes` | List episodes for a series | No |
| GET | `/api/series/{series_id}/graph` | Read the spoiler-filtered graph | No |
| POST | `/api/series/{series_id}/notes` | Create a user note | No |
| GET | `/api/series/{series_id}/notes` | List visible notes | No |
| GET | `/api/series/{series_id}/notes/{note_id}` | Read one visible note | No |
| PATCH | `/api/series/{series_id}/notes/{note_id}` | Update note content | No |
| DELETE | `/api/series/{series_id}/notes/{note_id}` | Delete a note | No |
| POST | `/api/series/{series_id}/custom-nodes` | Create a custom node | No |
| GET | `/api/series/{series_id}/custom-nodes/{node_id}` | Read one visible custom node | No |
| PATCH | `/api/series/{series_id}/custom-nodes/{node_id}` | Update a custom node label | No |
| DELETE | `/api/series/{series_id}/custom-nodes/{node_id}` | Delete a custom node | No |
| POST | `/api/series/{series_id}/custom-relationships` | Create a custom relationship | No |
| GET | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Read one visible custom relationship | No |
| PATCH | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Update a custom relationship predicate | No |
| DELETE | `/api/series/{series_id}/custom-relationships/{relationship_id}` | Delete a custom relationship | No |
| POST | `/api/auth/google` | Sign in with a Google ID token | No |
| GET | `/api/auth/me` | Get the current authenticated user | Yes |
| POST | `/api/auth/logout` | Revoke a session and clear its cookie | No |
| GET | `/api/series/{series_id}/revisions` | List visible revisions | No |
| GET | `/api/series/{series_id}/revisions/{revision_id}` | Read one visible revision | No |
| POST | `/api/series/{series_id}/revisions/{revision_id}/revert` | Revert the resource state captured by a revision | No |
| POST | `/api/series/{series_id}/candidates/ingest` | Ingest an extraction batch | No |
| GET | `/api/series/{series_id}/candidates` | List candidate claims | No |
| GET | `/api/series/{series_id}/candidates/{claim_id}` | Read one candidate claim | No |
| PATCH | `/api/series/{series_id}/candidates/{claim_id}` | Edit a candidate claim | No |
| POST | `/api/series/{series_id}/candidates/{claim_id}/approve` | Approve a candidate claim | No |
| POST | `/api/series/{series_id}/candidates/{claim_id}/reject` | Reject a candidate claim | No |
| GET | `/api/series/{series_id}/progress` | Read the current user's watch progress | Yes |
| POST | `/api/series/{series_id}/progress` | Upsert the current user's watch progress | Yes |
| POST | `/api/series/{series_id}/chat/sessions` | Create a chat session | Yes |
| GET | `/api/series/{series_id}/chat/sessions` | List the current user's chat sessions | Yes |
| GET | `/api/series/{series_id}/chat/sessions/{session_id}` | Read a session and visible messages | Yes |
| DELETE | `/api/series/{series_id}/chat/sessions/{session_id}` | Delete a session and its messages | Yes |
| POST | `/api/series/{series_id}/chat/sessions/{session_id}/messages` | Generate a grounded answer | Yes |
| POST | `/api/series/{series_id}/chat/sessions/{session_id}/messages/stream` | Stream a grounded answer with SSE | Yes |
| POST | `/api/series/{series_id}/change-sets` | Propose a graph ChangeSet | Yes |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/confirm` | Confirm and apply a ChangeSet | Yes |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/reject` | Reject a ChangeSet | Yes |
| POST | `/api/series/{series_id}/change-sets/{change_set_id}/revert` | Revert an applied ChangeSet | Yes |
| GET | `/api/settings/llm` | Read effective LLM settings with the key masked | Yes |
| PUT | `/api/settings/llm` | Update LLM settings | Yes |

## Request and Response Formats

### General conventions

- Normal request and response bodies use `application/json`.
- Successful reads and updates normally return `200`.
- Resource creation returns `201`, except candidate batch ingestion and progress upsert, which return `200`.
- Deletes and logout return `204` with no body.
- Pydantic request models configured with `extra="forbid"` reject unknown request fields; response typing, including an untyped `dict` response, does not affect request validation.
- The SSE chat route returns `text/event-stream`, not JSON.

### Series, episodes, health, and graph

`GET /health` returns `200` when Neo4j is reachable or `503` when it is not:

```json
{
  "status": "ok",
  "database": "connected",
  "service": "hdgrafcehennemi-backend"
}
```

`GET /api/series` returns `SeriesResponse[]`; a single series has `id`, `title`, and `slug`. `GET /api/series/{series_id}/episodes` returns `EpisodeResponse[]` with `id`, `series_id`, season and episode numbers, `episode_order`, `code`, `title`, and `visible_from_order`.

`GET /api/series/{series_id}/graph` requires the positive integer query parameter `visible_until_order`. The value must identify a persisted episode order for that series. The response is:

```json
{
  "series": {"id": "series_dexter", "title": "Dexter", "slug": "dexter"},
  "visible_until_order": 1,
  "nodes": [],
  "edges": [],
  "claims": [],
  "sources": [],
  "evidence": []
}
```

Every graph node and narrative item is filtered by `visible_from_order`. Claims also honor `valid_from_order` and `valid_until_order`. Returned edges are closed over the returned nodes: both endpoints must be present. Canonical/candidate claim projections carry their Claim ID; structural edges and user-authored relationship Claims both carry `claim_id: null`. User-origin edges are emitted only when both endpoints survive same-series node visibility filtering, so clients must not use null `claim_id` alone to classify an edge as structural. `GraphNode` additionally supports optional `image_url` and `image_source_url` fields.

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

The server creates `id`, `series_id`, `origin: "user"`, `visible_from_order`, `created_at`, and `updated_at`. PATCH accepts only `{"content":"..."}`. `GET /notes` requires `visible_until_order`; optional `target_type` and `target_id` filters must be supplied together.

### Custom nodes

Create a node:

```json
{
  "node_type": "Object",
  "label": "Blood slide",
  "episode_id": "dexter_s01e01"
}
```

`node_type` is one of `Character`, `Event`, `Location`, `Organization`, or `Object`; `label` is 1–200 characters; and `episode_id` is 1–255 characters. Visibility is derived from the referenced same-series episode. PATCH accepts only `{"label":"..."}`. Deleting a node with dependent notes or user relationships returns `409 resource_conflict`.

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

The supported predicates are `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`, `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, and `KILLS`. Source and target must exist in the same series. PATCH accepts only `{"predicate":"TRUSTS"}`.

The response uses `source`, `target`, and `type` rather than the request names `source_id`, `target_id`, and `predicate`. In `GET /graph`, user-authored relationships are edge-only records with `claim_id: null`; both endpoints must pass the same series and visibility checks as graph nodes before the edge is emitted.

### Revisions

All revision operations require `visible_until_order` as a positive query integer. Unlike graph, note, and direct custom-content reads, revision routes do **not** verify that a positive value matches a persisted Episode order; they apply it directly to revision visibility queries.

- `GET /revisions` accepts optional `resource_type` and `resource_id` filters and returns newest revisions first.
- `GET /revisions/{revision_id}` returns a visible `RevisionResponse` or an indistinguishable `404 resource_not_found`.
- `POST /revisions/{revision_id}/revert` restores an `Updated` user resource from `before`, or recreates a `Deleted` resource. It emits a new `Reverted` revision.
- Reverting a `Created` revision returns `422 cannot_revert_create`.
- Reverting an `Updated` resource whose current origin is canonical or candidate returns `409 cannot_revert_canonical`. The `Deleted` branch does not check the saved snapshot's origin before recreating it.

A revision contains `id`, `series_id`, `resource_type`, `resource_id`, `action`, nullable `before` and `after` snapshots, `created_at`, and `visible_from_order`.

### Candidate extraction and review

`POST /candidates/ingest` accepts an `ExtractionBatchEnvelope` with required extractor metadata and 1–500 claims:

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

Ingestion returns `200` with `created` and `errors` arrays. Candidate IDs are deterministic hashes of normalized claim content. Listing accepts an optional positive `visible_until_order`; omitting it returns candidates at all visibility levels.

PATCH accepts at least one of `label`, `predicate`, `claim_type`, `confidence_level`, `relationship_effect`, `valid_from_order`, `valid_until_order`, `evidence_text`, `evidence_locator`, `source_type`, or `source_locator`. Approve changes `status` to `canonical` while retaining `origin: "candidate"`; reject changes `status` to `rejected`. Candidate edit, approve, and reject operations log revisions.

### Watch progress

`POST /api/series/{series_id}/progress` accepts only:

```json
{
  "visible_until_order": 3
}
```

The integer must be greater than zero. The authenticated user and path supply `user_id` and `series_id`; clients cannot submit them. The operation upserts and returns `UserSeriesProgressResponse`. GET returns `404 resource_not_found` when no row exists.

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
    "visible_until_order_snapshot": 1
  },
  "citations": [],
  "graph_focus": {"node_ids": [], "edge_ids": []},
  "proposed_change_set": null
}
```

The server reads the spoiler boundary from persisted progress. If progress is absent on a message path, it creates a progress record at order 1. Chat-session ownership is scoped to the authenticated user and series; foreign, cross-series, and missing sessions all produce `404 resource_not_found`.

The streaming route emits SSE frames:

```text
data: {"type":"text_delta","text":"A grounded"}

event: done
data: {"message":{},"citations":[],"graph_focus":{},"proposed_change_set":null}

```

After streaming starts, failures are reported with `event: error` and a JSON object containing `code` and `message`. Possible in-stream codes include `too_many_requests`, `LLM_PROVIDER_UNAVAILABLE`, and `LLM_STREAM_FAILED`.

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

`provider` is `gemini` or `openai_compatible`; these are available implementations, not a statement that both are active. The provider used for a chat request is the effective non-empty stored value, falling back to `LLM_PROVIDER`; disabled or incomplete configuration is rejected before use. OpenAI-compatible requests post to `/chat/completions`. Gemini uses the `generateContent`/`streamGenerateContent` action family rather than that path; the current streaming provider posts to `/v1beta/models/{model}:streamGenerateContent?alt=sse`. `system_prompt_language` is `english` or `turkish`. A null or empty-string `api_key` retains the stored key; a whitespace-only string is truthy and is persisted as the new key. `enabled: null` retains the stored enabled state. Responses expose only `api_key_configured` and `api_key_masked`.

## Error Codes

Normal HTTP errors use this envelope:

```json
{
  "detail": {
    "code": "resource_not_found",
    "message": "Resource not found."
  }
}
```

FastAPI request-validation failures are sanitized to `422 invalid_request`; Pydantic field details are not returned by the installed handler. Database exceptions and constraint failures are also mapped centrally. Candidate ingestion is an exception: its `invalid_extraction_payload` message may include batch or claim validation context.

The codebase currently emits both lowercase domain codes and uppercase authentication/LLM codes. Clients should compare codes exactly as returned.

| Status | Code | Meaning |
|---|---|---|
| 401 | `AUTH_UNAUTHENTICATED` | Session cookie absent, invalid, expired, revoked, or not linked to a user |
| 401 | `AUTH_INVALID_GOOGLE_CREDENTIAL` | Google ID-token verification failed |
| 401 | `AUTH_DISABLED` | Google client ID or a valid session TTL is not configured |
| 403 | `AUTH_ORIGIN_NOT_ALLOWED` | Sign-in request origin does not match configured frontend origins |
| 404 | `series_not_found` | Series lookup failed |
| 404 | `resource_not_found` | Resource is absent, foreign, cross-series, or hidden at the boundary |
| 404 | `candidate_not_found` | Candidate claim lookup failed |
| 409 | `resource_conflict` | Resource state, ownership, dependency, or ChangeSet state conflicts |
| 409 | `constraint_violation` | A Neo4j uniqueness or other database constraint failed |
| 409 | `changeset_stale` | Progress was lowered after a ChangeSet was proposed |
| 409 | `cannot_revert_canonical` | Revision target is canonical or candidate content |
| 409 | `resource_already_exists` | A deleted revision target was already recreated |
| 409 | `cannot_approve_non_candidate` | Approval target does not have candidate origin |
| 422 | `invalid_request` | Request-model or repository validation failed |
| 422 | `invalid_visible_until_order` | Boundary does not identify a persisted episode order |
| 422 | `invalid_extraction_payload` | Candidate batch, candidate edit, approval, or rejection failed validation |
| 422 | `cannot_revert_create` | A creation revision has no prior state to restore |
| 422 | `invalid_action` | Revision action cannot be reverted by the route |
| 429 | `too_many_requests` | The user already has a chat generation in flight |
| 503 | `database_unavailable` | Neo4j is unreachable or rejects authentication |
| 503 | `database_error` | Another handled Neo4j request error occurred |
| 503 | `AUTH_SERVICE_UNAVAILABLE` | Google verification infrastructure failed |
| 503 | `LLM_DISABLED` | Effective LLM configuration is disabled |
| 503 | `LLM_PROVIDER_UNAVAILABLE` | LLM configuration or provider request is unavailable |

An SSE response that has already sent HTTP headers cannot change its status; it uses an `event: error` frame instead.

## Rate Limits

There is **no general HTTP request-rate limiter** in the application: no time window or maximum request count is configured.

Chat generation has a separate in-process concurrency guard of **one active generation per user**. A second non-streaming generation returns `429 too_many_requests`. The streaming route may report the same condition as an SSE error after the stream has opened. This guard is process-local and is not a distributed or time-window rate limit.

## CORS

FastAPI installs `CORSMiddleware` with:

| Setting | Value |
|---|---|
| Allowed origins | Comma-separated `FRONTEND_ORIGINS`; default `http://localhost:5173` |
| Credentials | Allowed |
| Methods | All |
| Headers | All |

CORS controls browser access but does not authenticate a request. Except for the explicit origin dependency on Google sign-in, state-changing routes do not perform their own general Origin/Referer or CSRF-token validation.
