# Public-Deployment Audit Evidence (2026-08-04)

Full evidence for the audit written to `docs/PROBLEMS.md` (30 problems, severity-tiered,
each with file:line evidence + fix direction). All facts below were verified this session
against the live repo (HEAD `9caa85b`, branch 47 ahead of origin/main), the RUNNING backend
(`curl http://localhost:8000/health` → ok; `/openapi.json` ground truth), live pytest and
vitest runs, and git history. Audit was read-only; the only write was `docs/PROBLEMS.md`.

## How the audit was run (reusable recipe)

1. **Surface map:** `grep -rn "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/*.py`
   + `grep -rn "CurrentUserDependency\|OptionalUserDependency\|require_current_user" backend/app/api/`
   → classify every route as authed / optional / bare. Bare = anonymous.
2. **Ground truth counts:** `curl -s localhost:8000/openapi.json` → 33 paths / 45 ops.
   `python -c` counting script: `paths=len(d['paths']); ops=sum(len([m for m in v if m in ('get','post','put','patch','delete')]) for v in d['paths'].values())`.
3. **Anonymous-write inventory** (from openapi, minus /health): 19 no-session paths; 14 write
   operations across 11 paths — see the table in SKILL.md / PROBLEMS.md #1.
4. **Docs-vs-reality drift:** grep docs for countable claims (N ops/N paths) and for
   capability claims (`proposed_change_set: null`), then diff against source/openapi.
5. **Shipped-red proof:** `unset PYTHONPATH && source .venv/Scripts/activate && python -m
   pytest backend/tests/test_seed_idempotency.py backend/tests/test_openapi_contract.py -q`
   → 3 failed / 14 passed (seed drift `{'relationships': 33} != {'relationships': 27}`);
   openapi contract green. Safe on the live DB (seed setup is MERGE-only/idempotent).
6. **FE flake detection:** full run `NODE_ENV=test CI=1 npx vitest run` → 185/186 with
   `App.test.tsx` e2e failing; same file in isolation → 15/15. Suite order/timing-dependent.
7. **Config/secrets by NAME ONLY:** `grep -E '^[A-Za-z_]+=' .env | cut -d= -f1` → keys
   `GOOGLE_CLIENT_ID`, `AUTH_DEV_CODE` (read tool blocks .env; never read values).
8. **Hygiene:** `git ls-files | grep -E "main\.py|index\.html"` (PyCharm junk), `ls .github`
   (absent → zero CI), `git rev-list --count origin/main..HEAD` (47 unpushed), `ls LICENSE*`
   (absent), `git status -sb`.

## Key verified facts (as of 08-04)

### Auth / security
- `api/user_content.py`: zero `CurrentUserDependency` on any of 12 routes (notes CRUD,
  custom-nodes CRUD, custom-relationships CRUD). `NoteResponse` (domain/user_content.py:131)
  has NO `user_id`. update/delete match by id only → global shared whiteboard, anonymous
  vandalism + data deletion.
- `api/candidates.py`: zero auth; `POST /{id}/approve` (line 163) sets `status='canonical'`
  on any `origin:'candidate'` claim; `ingest` (line 79) injects arbitrary claims; `reject`
  (line 219); `PATCH /{id}` (line 269) edits any field incl. valid_from/until_order.
- `api/revisions.py:119` `POST /{id}/revert` — zero auth; restores `before` snapshots onto
  live nodes.
- `domain/settings.py:26-29` — code comment admits: "Any authenticated user can still
  redirect the shared provider to an external attacker-controlled https:// host — closing
  that requires per-user-scoped or admin-gated settings, which is a separate, larger change
  tracked outside this fix". `PUT /api/settings/llm` auth = any Google account; stored key
  sent to configured `base_url` via `provider.py:132` (Bearer) / `:369` (x-goog-api-key).
  Scheme allowlist `("http","https")` → SSRF-to-internal allowed deliberately (local vLLM).
- No rate limiting anywhere (`grep -rni "rate.limit|slowapi|throttle"` → 0 hits). Only
  per-user in-memory generation slot (`services/chat.py:48-71`) — single-process only.
- `verify_origin` (api/auth.py:55-105) returns when no Origin/Referer header (fails open);
  logout route (line 284) has no verify_origin dependency.
- `SESSION_COOKIE_SECURE=false` default (core/config.py:26-29) AND in `.env.example:10`.
- Sessions: no sweep (repository/session.py:5-16 docstring: "not implemented"); sliding TTL
  refresh on EVERY authenticated request (services/auth.py:168 → refresh write per request).
- `ErrorDetail.code` regex `^[a-z][a-z0-9_]*$` (core/errors.py:26) vs real uppercase codes
  `AUTH_UNAUTHENTICATED`, `LLM_DISABLED`, `LLM_PROVIDER_UNAVAILABLE` etc.

### Spoiler-safety integrity
- Anonymous `GET /graph?visible_until_order=N` keeps the client-chosen order verbatim
  (api/graph.py:83-87, OptionalUserDependency); `/episodes` likewise → whole future graph
  fetchable without login. Only the LLM chat boundary is server-persisted.
- `GET /candidates` `visible_until_order` optional → all visibility levels by default
  (candidates.py:130-136, API.md:264).
- Anonymous notes at target-derived `visible_from_order` = arbitrary spoiler text served to
  all visitors; no moderation.

### Docs drift (verified)
- `docs/API.md:10` "44 method/path operations over 32 path templates" — live is 45/33
  (missing: `POST /api/auth/dev`). Only `docs/frontend-api-contract.md` is test-locked.
- `docs/ARCHITECTURE.md:562` "the current chat/retrieval pipeline … always emits
  `proposed_change_set: null`" — FALSE since 07-07 (`67f4a58`, 12-tool TOOL_SCHEMAS).
- `docs/ARCHITECTURE.md:596` "progress update path accepts any positive integer and does
  not verify that it matches an Episode" — FALSE since 07-02 (services/progress.py:92-123,
  D-09). "GRAPH_SUMMARY_COUNTS_QUERY counts claims without gating their subject/object
  endpoints" — FALSE since 07-05 (EXISTS subqueries, tools.py:253-262). The same paragraph's
  GET_EVIDENCE_QUERY/GET_SOURCES_QUERY claim is STILL TRUE: those queries gate the
  relationship + evidence/source but never re-check `claim.visible_from_order` (the claim
  id set came from earlier retrieval) — residual defense-in-depth gap.
- `docs/ROADMAP.md:207-209` unchecked: auth/ownership for user-content+revision+candidate
  mutations, comprehensive CSRF, production authorization roles — the roadmap defers the
  top blockers.

### Test suites (live runs 08-04)
- Backend: `test_seed_idempotency.py` ×3 FAILED (drift), `test_openapi_contract.py` PASSED.
  Documented baseline 410 passed / 3 failed means the repo ships permanently red.
- Frontend: 185 passed / 1 failed (full run) — failing: `App.test.tsx` > "runs select ->
  confirm -> fetch -> render -> inspect end-to-end"; passes 15/15 in isolation (flake).
- Lint: 28 errors (react-hooks/refs writing refs during render in useChatSessions.ts:34,
  useNotes.ts:35, useRevisions.ts:32; preserve-manual-memoization in DetailPanel/GraphCanvas;
  no-explicit-any in tests). tsc -b clean. Build OK but one chunk >500kB.

### Repo hygiene
- Root `main.py` = PyCharm `print_hi('PyCharm')` template (committed). Root `index.html`
  (60KB landing) is the only GitHub-Pages-servable artifact; no `.github/` → no CI at all.
- `frontend/README.md` = unmodified create-vite boilerplate.
- `docker-compose.yml:12` hardcodes `neo4j/hdgraf-local-password`; `.env.example:3` ships
  `NEO4J_PASSWORD=change-me` — mismatched documented startup path.
- Seed `data/dexter/seed/characters.json` hotlinks `static.wikia.nocookie.net` images.
- No LICENSE / CONTRIBUTING. `.gitignore` has a stale "Streamlit" section; `backend/
  requirements.txt` is a generated `uv export` duplicating uv.lock.
- `VITE_API_BASE_URL` declared in frontend/.env.example but read by NO source (all
  `frontend/src/api/*.ts` hardcode `/api`).
- PUT settings persists whitespace-only API keys (no strip); `ARCHITECTURE.md:610` documents.
