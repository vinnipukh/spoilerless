# SECURITY_ATTACK_SURFACE.md — Spoilerless (hdgrafcehennemi)

Living document: every public endpoint, its auth, inputs, downstream services, and security controls. Update whenever routes change. Audit: 2026-08-14/15 (9 specialist subagents + adversarial review). Verified against `spoilerless/app/api/*` at commit 9d50500.

Legend: **P**=public/anonymous · **O**=optional user (anon OK, boundary-clamped) · **U**=any authenticated user · **A**=admin · **T**=token-gated. CSRF = Origin/Referer guard (`CsrfGuardDependency`). Rate = Redis-backed limiter (`services/rate_limit.py`; ALL limiters are no-ops when `REDIS_URL` empty or Redis down — fail-open by design, PROB-23).

---

## 1. Backend routes (FastAPI, 53 total)

| # | Method | Path | Auth | CSRF | Rate | Params / Body | Cookies / Headers | File:line |
|---|--------|------|------|------|------|----------------|--------------------|-----------|
| 1 | GET | /health | P | – | – | – | – | main.py:222 |
| 2 | HEAD | /health (not in schema) | P | – | – | – | – | main.py:237 |
| 3 | GET | /api/series | P | – | – | – | – | series.py:32 |
| 4 | GET | /api/series/{series_id} | P | – | – | path: series_id | – | series.py:38 |
| 5 | GET | /api/series/{series_id}/episodes | O | – | – | q: visible_until_order (def 1) | cookie session | series.py:49 |
| 6 | GET | /api/series/{series_id}/graph | O | – | – | q: visible_until_order (req) | cookie session | graph.py:102 |
| 7 | GET | /api/series/{series_id}/graph/visualization | O | – | – | q: view (Literal 6), episode_order (>0), focus_id[] (≤20) | cookie session | graph.py:174 |
| 8 | GET | /api/series/{series_id}/graph/expand | O | – | – | q: node_id, expansion_key (Literal 7), episode_order, limit (1–25) | cookie session | graph.py:304 |
| 9 | POST | /api/series/{series_id}/graph/path | O | **–** | – | body: source_entity_id, target_entity_id, max_hops (≤4) | cookie session | graph.py:466 |
| 10 | GET | /api/series/{series_id}/export | O | – | – | q: visible_until_order (def 1), target_id (opt) → markdown | cookie session | graph.py:502 |
| 11 | GET | /api/series/{series_id}/progress | U | – | – | path: series_id | cookie session | progress.py:42 |
| 12 | POST | /api/series/{series_id}/progress | U | ✔ | – | body: watched_through_order / view_as_of_order / visible_until_order (mutually exclusive) | cookie session | progress.py:73 |
| 13 | GET | /api/series/{series_id}/revisions | P | – | – | q: visible_until_order (req), resource_type, resource_id | – | revisions.py:44 |
| 14 | GET | /api/series/{series_id}/revisions/{revision_id} | P | – | – | q: visible_until_order (req) | – | revisions.py:77 |
| 15 | POST | /api/series/{series_id}/revisions/{revision_id}/revert | U | ✔ | – | q: visible_until_order (req); owner-or-admin inside | cookie session | revisions.py:105 |
| 16 | GET | /api/series/{series_id}/candidates | P | – | – | q: visible_until_order (req) | – | candidates.py:145 |
| 17 | GET | /api/series/{series_id}/candidates/{claim_id} | P | – | – | q: visible_until_order (req) | – | candidates.py:174 |
| 18 | POST | /api/series/{series_id}/candidates/ingest | U | ✔ | – | body: ExtractionBatchEnvelope | cookie session | candidates.py:95 |
| 19 | POST | /api/series/{series_id}/candidates/{claim_id}/approve | A | ✔ | – | – | cookie session | candidates.py:213 |
| 20 | POST | /api/series/{series_id}/candidates/{claim_id}/reject | A | ✔ | – | – | cookie session | candidates.py:255 |
| 21 | PATCH | /api/series/{series_id}/candidates/{claim_id} | A | ✔ | – | body: EditCandidateRequest | cookie session | candidates.py:287 |
| 22 | POST | /api/series/{series_id}/chat/sessions | U | ✔ | – | body: title | cookie session | chat.py:52 |
| 23 | GET | /api/series/{series_id}/chat/sessions | U | – | – | – | cookie session | chat.py:72 |
| 24 | GET | /api/series/{series_id}/chat/sessions/{session_id} | U | – | – | – | cookie session | chat.py:88 |
| 25 | DELETE | /api/series/{series_id}/chat/sessions/{session_id} | U | ✔ | – | – | cookie session | chat.py:107 |
| 26 | POST | /api/series/{series_id}/chat/sessions/{session_id}/messages | U | ✔ | chat 20/60s/user | body: question (1–4000); X-LLM-Api-Key/Provider/Base-URL/Model | cookie session | chat.py:136 |
| 27 | POST | /api/series/{series_id}/chat/sessions/{session_id}/messages/stream | U | ✔ | chat 20/60s/user | body: question; X-LLM-*; SSE response | cookie session | chat.py:168 |
| 28 | POST | /api/series/{series_id}/change-sets | U | ✔ | – | body: ChangeSetCreateRequest (series_id must match path) | cookie session | change_set.py:48 |
| 29 | POST | /api/series/{series_id}/change-sets/{id}/confirm | A | ✔ | – | – | cookie session | change_set.py:78 |
| 30 | POST | /api/series/{series_id}/change-sets/{id}/reject | U | ✔ | – | – | cookie session | change_set.py:120 |
| 31 | POST | /api/series/{series_id}/change-sets/{id}/revert | U | ✔ | – | – | cookie session | change_set.py:145 |
| 32 | GET | /api/settings/llm | A | – | – | – (key masked) | cookie session | settings.py:33 |
| 33 | PUT | /api/settings/llm | A | ✔ | – | body: LLMSettingsUpdate (provider, api_key, base_url, model, enabled, language) | cookie session | settings.py:46 |
| 34 | POST | /api/share | U | ✔ | – | body: series_id, visible_until_order (clamped to creator progress) | cookie session | share.py:39 |
| 35 | GET | /api/share/{token}/graph | T | – | – | path: token (32B) | – | share.py:95 |
| 36 | GET | /api/share | U | – | – | – | cookie session | share.py:148 |
| 37 | DELETE | /api/share/{token} | U | ✔ | – | owner-or-admin | cookie session | share.py:172 |
| 38 | POST | /api/series/{series_id}/notes | U | ✔ | content-write 30/60s | body: NoteCreate | cookie session | user_content.py:37 |
| 39 | GET | /api/series/{series_id}/notes | P | – | – | q: visible_until_order (req), target_type, target_id | – | user_content.py:51 |
| 40 | GET | /api/series/{series_id}/notes/{note_id} | P | – | – | q: visible_until_order (req) | – | user_content.py:68 |
| 41 | PATCH | /api/series/{series_id}/notes/{note_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:79 |
| 42 | DELETE | /api/series/{series_id}/notes/{note_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:96 |
| 43 | POST | /api/series/{series_id}/custom-nodes | U | ✔ | content-write | body: CustomNodeCreate | cookie session | user_content.py:113 |
| 44 | GET | /api/series/{series_id}/custom-nodes/{node_id} | P | – | – | q: visible_until_order (req) | – | user_content.py:126 |
| 45 | PATCH | /api/series/{series_id}/custom-nodes/{node_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:132 |
| 46 | DELETE | /api/series/{series_id}/custom-nodes/{node_id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:148 |
| 47 | POST | /api/series/{series_id}/custom-relationships | U | ✔ | content-write | body: CustomRelationshipCreate | cookie session | user_content.py:164 |
| 48 | GET | /api/series/{series_id}/custom-relationships/{id} | P | – | – | q: visible_until_order (req) | – | user_content.py:177 |
| 49 | PATCH | /api/series/{series_id}/custom-relationships/{id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:183 |
| 50 | DELETE | /api/series/{series_id}/custom-relationships/{id} | U | ✔ | content-write | owner-or-admin | cookie session | user_content.py:199 |
| 51 | POST | /api/auth/google | P | ✔ | login 10/300s/IP | body: credential (Google ID token) → session cookie | Origin/Referer | auth.py:92 |
| 52 | GET | /api/auth/me | U | – | – | – | cookie session | auth.py:177 |
| 53 | POST | /api/auth/logout | U | ✔ | – | – (revokes session) | cookie session | auth.py:199 |
| 54 | GET | /api/static/* | P | – | – | static character portraits (directory listing disabled) | – | main.py:187 |

**Global middleware:** security headers (CSP/HSTS/nosniff/XFO/Referrer-Policy) on every response incl. /api (main.py:47-73) · request logging allowlist (method/path/status/ms + user-agent/content-type/accept only; cookie/authorization/X-LLM-* never logged) · CORS: explicit `FRONTEND_ORIGINS` list + credentials, explicit methods/headers (main.py:192-214) · error envelopes sanitized (no tracebacks; `debug` never on).

## 2. Auth summary

- **Login:** Google ID token → `verify_oauth2_token` (signature/audience/issuer/expiry; `email_verified` NOT checked — SEC-BE-007) → `ALLOWED_EMAILS` allowlist (empty default = any verified Google account) → role from `ADMIN_EMAILS` membership.
- **Session:** 48-byte `secrets.token_urlsafe` token, SHA-256 at rest, HttpOnly+Secure+SameSite=Lax cookie, TTL 7d (no Max-Age set — SEC-BE-010), hourly expired-session sweep.
- **CSRF:** Origin/Referer guard on every state-changing cookie-authenticated route EXCEPT `POST /graph/path` (read-only; inconsistency only).
- **Admin:** `require_admin` derives role server-side from `ADMIN_EMAILS`; admin surface = settings/llm, candidate approve/reject/edit, change-set confirm.

## 3. LLM / GraphRAG surface

- **Entry:** POST /chat/.../messages[/stream] (U, 20/60s/user, per-user concurrency slot = 1 in-process).
- **Provider:** Gemini v1beta REST (`x-goog-api-key`) or OpenAI-compatible; config from admin `:AppSetting{llm}` (key write-only, masked GET) or per-request BYOK `X-LLM-*` headers (user's own key; `base_url` validated http/https+host only — authenticated SSRF primitive, SEC-LLM-001/SEC-BE-005).
- **Agent:** 12-tool allowlist, ALL read-only Neo4j except `propose_changeset` (draft persist, admin-confirmed before apply). NO URL/HTTP/scraper tool — no LLM-driven SSRF.
- **Spoiler boundary:** server-resolved `min(view, watched)` (progress record; anonymous=order 1) → injected into every Cypher query as `visible_until_order` param + defense-in-depth `_visible_at` filter. Pre-retrieval enforcement (verified strong). **Known gaps:** authenticated users WITHOUT a progress record are NOT clamped on /graph + /episodes (SEC-BE-001); anonymous candidates/revisions/notes reads unclamped (SEC-BE-002, SEC-GR-005/006/007).
- **Context caps:** max tool rounds 4, context 40 items / 12k chars, tool-result replay 4k chars, output 800 tokens, question 4000 chars, no provider retry, streaming SSE.

## 4. Data stores & caches

- **Neo4j AuraDB** (`neo4j+s://`): all persistence. Credentials admin-level (SEC-GR-003). All ~55 Cypher queries parameterized; two closed-set f-string interpolations (SEC-BE-011); latent label interpolation in revert path (SEC-GR-014). LLM key plaintext in `:AppSetting{key:'llm'}` (SEC-GR-012/SEC-INF-013).
- **Upstash Redis** (`rediss://`, REDIS_URL dashboard-only): graph cache `graph:{series}:{boundary}:{user}` TTL 300s; viz cache `viz:{...}:{epoch}:{focus_sig}` (metadata re-validated on read); `graph_revision:{series}` epochs; `hdgraf:rate_limit:*` ZSETs. **Credential committed in README.md + git history (SEC-INF-001 — rotate!).** Key growth unbounded for per-user keys (SEC-DOS-011); viz cache-key explosion via focus_id (SEC-DOS-005).

## 5. External network

| Target | Direction | Purpose | Credential |
|--------|-----------|---------|------------|
| accounts.google.com/gsi/client | FE→ | Sign-In JS | none |
| www.googleapis.com OAuth2 certs | BE→ | token verification | none |
| generativelanguage.googleapis.com | BE→ | Gemini | x-goog-api-key |
| arbitrary http(s) host (BYOK) | BE→ | OpenAI-compatible | user key |
| Neo4j AuraDB | BE↔ | persistence | NEO4J_* |
| Upstash Redis | BE↔ | cache/limits | REDIS_URL token |
| static.wikia.nocookie.net et al. | browser→ | hotlinked portraits (CSP img-src https:) | none |

## 6. Key security controls (verified)

- Parameterized Cypher everywhere; no LLM-generated Cypher; boundary in-query + context filter.
- Citations validated against this-turn retrieved IDs; ungrounded answers replaced.
- Session/share tokens hashed at rest; 32–48B entropy.
- CSP/HSTS/nosniff/XFO/Referrer-Policy on backend responses; CORS explicit; CSRF origin guard fail-closed.
- LLM key: masked GET, never logged, never in response models; BYOK key only in httpx client.
- Cache keys carry series+boundary+user+epoch; poisoned viz entries rejected by metadata re-validation.
- Error envelopes sanitized; request log allowlist; no console.log/telemetry in frontend; no source maps in dist.

## 7. Known gaps (see SECURITY_AUDIT.md for details)

Boundary clamps (SEC-BE-001/002, SEC-GR-005/006/007) · candidate ingest poisoning (SEC-BE-003/SEC-GR-004) · BYOK SSRF (SEC-LLM-001) · rate-limit fail-open + proxy collapse (SEC-DOS-001/003) · cost amplification (SEC-DOS-002) · body-size limit absent (SEC-DOS-004) · no CSP on SPA shell (SEC-FE-001) · BYOK key in localStorage (SEC-FE-002) · /docs exposed (SEC-INF-003) · Redis cred in git (SEC-INF-001) · validation-error logging (SEC-LOG-001) · chat retention indefinite (SEC-LOG-007).
