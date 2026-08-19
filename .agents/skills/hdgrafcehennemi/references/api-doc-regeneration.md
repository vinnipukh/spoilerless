# API documentation regeneration checklist

Use this when rebuilding `docs/API.md` from the FastAPI application.

## Ground truth

- Read `C:\Users\arhan\AppData\Local\hermes\agents\gsd-doc-writer.md` first and obey the assigned mode.
- In `update` mode with `preservation_mode: regenerate`, replace the stale document as one coherent reference rather than preserving appended supplement structure.
- Generate the live schema from `backend.app.main:app`; the verified 2026-08-02 inventory is **44 operations over 32 path templates**.
- Treat OpenAPI as the route/schema inventory, then inspect route dependencies and handlers for behavior OpenAPI does not encode: cookie authentication, Origin checks, SSE errors, persistence, and concurrency guards.

## Important current corrections

- Only routes using `CurrentUserDependency` require a session: `/api/auth/me`, progress, chat, ChangeSets, and LLM settings. User-content, revisions, and candidate mutations currently have no auth dependency.
- Authentication and LLM runtime codes are uppercase (`AUTH_UNAUTHENTICATED`, `AUTH_INVALID_GOOGLE_CREDENTIAL`, `AUTH_DISABLED`, `AUTH_ORIGIN_NOT_ALLOWED`, `AUTH_SERVICE_UNAVAILABLE`, `LLM_DISABLED`, `LLM_PROVIDER_UNAVAILABLE`), while most domain codes are lowercase.
- `UserPublic` does not expose `google_sub`.
- Production uses `Neo4jSessionRepository`, not the in-memory repository. Session expiry is sliding because authenticated reads refresh the server-side TTL.
- No general request-rate limiter exists. Chat instead permits one active generation per user in the current process.
- `POST /api/auth/google` validates Origin/Referer when present; requests with neither header pass. Other state-changing routes do not share a general CSRF dependency.

## Verification

1. Confirm the GSD marker is the first line and appears once.
2. Confirm required API sections exist: Authentication, Endpoints Overview, Request and Response Formats, Error Codes, Rate Limits.
3. Parse the overview table into `(method, path)` pairs and compare it exactly with `app.openapi()`.
4. Run a Markdown whitespace check and count final lines.
5. Return only the requested short confirmation; do not echo document content.
