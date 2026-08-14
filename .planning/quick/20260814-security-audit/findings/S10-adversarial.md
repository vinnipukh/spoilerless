# S10 — Independent Adversarial Review (Challenge of the 9-Agent Audit)

**Auditor:** S10 (adversarial challenger) · **Date:** 2026-08-15 · **Scope:** independent re-verification of S0–S9 claims against code, hunt for missed attack paths, attack-chain synthesis, final public-exposure verdict.
**Method:** static re-verification of every headline finding at its cited `file:line` (no live DB/network; all secrets redacted). Accepted S3/S4/S9 findings only where I re-read the underlying files (byok.ts, index.html, vercel.json, chat.py SSE, errors.py, main.py); pipeline-internal claims (S4) spot-checked at the cited loops.

---

## 1. Verdict per major finding (verified at code)

| ID | Severity (as reported) | S10 verdict | Grounds (file:line) |
|---|---|---|---|
| **SEC-INF-001** (live Upstash password in README + history) | CRITICAL | **REJECTED — downgrade to INFO** | `README.md:40` and all 9 commits (`git log -S darling-rat`) contain the literal string `<token>` — verified byte-for-byte via `git show <commit>:README.md \| od -c` on HEAD. The password was never committed; S6's "7-char non-placeholder real value" is factually wrong. Residual: the Upstash endpoint name `darling-rat-221809` and AuraDB instance id `03a8623b` are public in README/docs (fingerprinting only; Upstash auth is the high-entropy token). The audit's headline CRITICAL does not exist. |
| **SEC-BE-001** (fresh-account graph/episodes boundary bypass) | HIGH | **CONFIRMED** | `api/graph.py:133` `effective = requested`; clamp only when `progress_service.get(...)` returns a record (`:135-140`). `api/series.py:87-94` identical. The fail-closed sibling `_resolve_effective_boundary` (`graph.py:426-437`) returns 1 for record-less users — the two paths disagree. |
| **SEC-BE-002 / SEC-GR-005/006/007** (anonymous unclamped reads) | HIGH | **CONFIRMED, one upgrade** | Candidates list/get: no user dependency (`api/candidates.py:154-207`); notes/custom-node/custom-relationship get: no user dependency (`api/user_content.py:51-76,126-129,177-179`); revisions list/get: no auth, returns `before`/`after` snapshots + `user_id` (`api/revisions.py:44-97`, query `:20-33`). **Upgrade:** notes/custom-node/relationship/revisions routes use `Boundary = Annotated[int, Query(gt=0)]` with **no persisted-episode validation at all** (`user_content.py:25`, `revisions.py:16-18`) — weaker than S2/S5 reported ("persisted-episode check ✓" applies only to candidates). |
| **SEC-BE-003 / SEC-GR-004** (ingest = any auth'd user, client-chosen `visible_from_order`) | HIGH | **CONFIRMED** | `api/candidates.py:121-142` (`CurrentUserDependency` only, docstring admits gate-only use); `domain/extraction.py:111` client field; `graph/candidates.py:132` `"visible_from_order": claim.visible_from_order` → `INGEST_CANDIDATE_QUERY` (`:35-98`) writes `:Claim{origin:'candidate'}` visible to all via `spoiler/filter.py:16` `origin IN ['canonical','candidate']`. No existence checks on subject/object/episode. |
| **SEC-BE-005 / SEC-LLM-001** (BYOK SSRF) | MED-HIGH | **CONFIRMED** | `domain/settings.py:62-81` — http/https + host only, no private/loopback/metadata block; the risk is *documented as accepted* (`:27-33`). `services/chat.py:77-146` — BYOK branch; stored-key branch (`:147-178`) ignores client headers → no shared-key exfil via headers (S6's "safe" conclusion holds **only** for key exfiltration, not for the network primitive). |
| **SEC-LLM-002** (stored base_url redirect w/ shared key) | LOW | **CONFIRMED** | Requires admin (`api/settings.py:46-58` RequireAdmin + CSRF); then every non-BYOK chat turn POSTs the stored key to attacker host (`services/chat.py:147-178`). Frontend SettingsPage has **no admin gating** (grep: zero role refs) — it is BYOK-only; no non-admin path reaches the stored key. |
| **SEC-LLM-003 / SEC-DOS-002** (cost farm / denial-of-wallet) | CRITICAL | **CONFIRMED (config-dependent)** | Tool loop executes all `new_calls` with no per-round cap (`retrieval/pipeline.py:822`), rounds=4 (`:780`), replay cap 4000 chars/result (`:105`), per-user limits only, `allowed_emails` default "" = open signup (`config.py:60-67`). $600-860/day arithmetic (10 accounts × 20 msg/min × ≤5 calls × ~40-60k input) is sound at Gemini 2.5 Flash pricing. Exploitability hinges on prod `ALLOWED_EMAILS`/`LLM_ENABLED`+stored key (unverifiable statically). |
| **SEC-BE-004 / SEC-DOS-003 / SEC-INF-004** (per-IP limits collapse → global login bucket) | MEDIUM | **CONFIRMED — upgrade availability impact to HIGH** | `render.yaml:10` no `--proxy-headers`/`--forwarded-allow-ips`; `rate_limit.py:41-50` keys anonymous on `request.client.host` = Render proxy IP for every client → the 10-logins/5min bucket is site-global. Scripted 10 failed logins = site-wide login outage; repeatable forever. Also `api/graph.py:466-499` is the only POST without CSRF (read-only, low impact — confirmed). |
| **SEC-DOS-001** (limiter fail-open) | HIGH | **CONFIRMED** | `rate_limit.py:86-105` (exception → pass), `:116-145` (init failure → unbound no-op). |
| **SEC-DOS-004** (no body-size limit) | HIGH | **CONFIRMED** | No size middleware anywhere in `main.py`; `change_set.py` operations list `min_length=1` no max (`domain/change_set.py:263`). |
| **SEC-DOS-005** (viz cache-key explosion) | HIGH | **CONFIRMED** | `cache/graph_cache.py:164-167` — `focus_sig` (SHA-256 of attacker-set) in key; `focus_id` ≤20 ids, anonymous allowed (`api/graph.py:188-192`). |
| **SEC-DOS-006/007/008/009/010/011/012** | MED/LOW | **CONFIRMED (spot-checked)** | No LIMIT on `CHAT_MESSAGE_LIST_QUERY` (S8 :58-68 cited); `invalidate_series` epoch+scan (`graph_cache.py:115-137`); slot dict decrement-only (`services/chat.py:71-74`); expand uncached/anonymous (`api/graph.py:304-386`). |
| **SEC-FE-001** (no CSP on SPA shell) | HIGH | **CONFIRMED** | `vercel.json` = rewrites only; `index.html` no CSP meta; backend header middleware (`main.py:47-73`) never serves the shell. |
| **SEC-FE-002 / SEC-LOG-003** (BYOK key plaintext localStorage) | MEDIUM | **CONFIRMED** | `byok.ts:9,53-62,71-85` — key in localStorage, sent as `X-LLM-*` headers to the **backend** on every chat call (the copy "never leaves this browser" is misleading: it transits `api.spoilerless.net`). |
| **SEC-FE-006** (forgeable visitor flag) | MEDIUM | **DOWNGRADE to LOW** | I verified every endpoint the visitor gates assume is auth'd server-side: chat sessions/messages POST (`api/chat.py:52-263` CurrentUser), share POST/DELETE (`api/share.py:46-52,172+`), notes/custom writes (`user_content.py` CurrentUser), progress GET/POST (`api/progress.py` CurrentUser). Forging the flag yields nothing beyond anonymous boundary-1 access; the blur is cosmetic UX, the enforcement is server-side and holds. |
| **SEC-LOG-001** (validation errors log raw inputs) | MEDIUM | **CONFIRMED** | `core/errors.py:234` `logger.error("validation_error", exc_info=exc)`; FastAPI `RequestValidationError.__str__` = `json.dumps(errors())` incl. `input` → oversized `question` (4001 chars) and malformed Google `credential` JWTs land verbatim in prod logs. |
| **SEC-LOG-002** (PII emails logged) | LOW | **CONFIRMED** | `api/auth.py:137`. |
| **SEC-INF-003 / SEC-LOG-004** (/docs exposed) | MEDIUM | **CONFIRMED** | `main.py:164-168` defaults kept. |
| **SEC-BE-007** (email_verified never checked; allowlist default empty) | MEDIUM | **CONFIRMED statically** | `services/auth.py:162-164` reads sub/email/name/picture only; `config.py:60-67` default "". Prod value needs operator check. |
| **SEC-BE-010** (no cookie Max-Age) | LOW | **CONFIRMED** | `api/auth.py:69-78` no `max_age`. |
| **No XSS anywhere** (S3 SEC-FE-010) | positive | **ACCEPTED** | No dangerous sinks in src (S3 grep); rendering is React-text/canvas. No sanitizer layer exists — future-regression risk, not current vuln. |
| **SSE injection** (hunt item) | — | **NOT PRESENT (positive)** | `api/chat.py:206-263` — all `data:` frames are `json.dumps(...)` (LLM content newlines escaped); `event:` names are fixed literals. No framing injection. |
| **Redis key collisions** (hunt item) | — | **NOT PRESENT (positive)** | `graph:{series}:{boundary}:{user\|anon}` (`graph_cache.py:71-72`): boundary is an int, user is UUID/`anon` — no colliding decomposition for any valid series_id. |
| **Admin endpoints reachable by non-admin** (hunt item) | — | **NOT PRESENT (positive)** | All `RequireAdminDependency` uses: candidates approve/reject/edit (`api/candidates.py:227,265,298`), change-set confirm (`api/change_set.py:95`), settings GET/PUT (`api/settings.py:40,54`). Revisions revert is user-scoped owner-checked (`api/revisions.py:111-136`). |
| **IDOR on revisions/candidates writes** (hunt item) | — | **NOT PRESENT (positive)** | Owner/admin checks in work functions; foreign ≡ 404. |
| **BYOK admin-settings poisoning of shared key path** (hunt item) | — | **CONFIRMED as designed** | Only admins can set stored `base_url` (SEC-LLM-002); non-admin frontend settings are BYOK-only. No widening found. |
| **AUTH_DEV_CODE vestige** | INFO | **CONFIRMED dead** | Zero references in `spoilerless/` + `frontend/src/` (grep). |
| **httpx undeclared prod dep** | INFO | **ACCEPTED** | `llm/provider.py:18` imports httpx; dev-group only (S7). Works only because Render installs dev deps. |
| **No TrustedHostMiddleware** | LOW | **CONFIRMED** | Middleware stack = CORS + security headers + logging (`main.py:215-216`). No absolute-URL generation found → low immediate impact. |

## 2. NEW findings (S10)

### SEC-ADV-001 | Candidate ingest is completely unthrottled (write amplification + unbounded corpus) | MEDIUM | CONFIRMED
- **Component:** `api/candidates.py:121-127` — ingest deps are `repo, user: CurrentUserDependency, _csrf` only; **no rate limiter** (S8's SEC-DOS-009 inventory missed it: session/progress/change-set/share are listed, ingest is not).
- **Vulnerability:** unlimited batches of up to 500 claims each (`domain/extraction.py:195` `max_length=500`), each an idempotent MERGE — one scripted account can insert hundreds of thousands of claim/evidence/source nodes with zero throttling, amplifying SEC-BE-003's poisoning volume and the read cost of the **unpaginated** `list_candidate_claims` (`graph/candidates.py:292-337` — no LIMIT; response grows monotonically for every anonymous reader).
- **Recommended fix:** rate-limit ingest (content-write bucket); paginate/LIMIT the list query; admin-gate or server-derive visibility per SEC-BE-003.

### SEC-ADV-002 | Candidate ingest never invalidates the graph cache — stale/poisoned window | LOW | CONFIRMED
- **Component:** `api/candidates.py` ingest path vs `invalidate_series` callers (`api/user_content.py:122,144,160...`, `api/change_set.py:116`). Ingest calls no invalidation.
- **Vulnerability:** after an ingest, cached `graph:*`/`viz:*` entries keep serving the pre-poison graph for up to 300s while the (uncached) candidates list shows the poison immediately — inconsistent state window that also means the *graph UI* briefly hides attacker content the *candidates panel* shows (confusion + stale-data integrity, and the reverse for deletions).
- **Recommended fix:** call `invalidate_series` on ingest (and approve/reject/edit already do per `graph/candidates.py:340-343` comment — verify).

### SEC-ADV-003 | Notes/custom-node/relationship/revisions GET accept any positive int (no persisted-episode check) | LOW (refinement) | CONFIRMED
- S2/S5 matrices claimed "persisted-episode check ✓" on these routes; actual: `Boundary = Query(gt=0)` (`user_content.py:25`, `revisions.py:16-18`) — **no `resolve_boundary` call** in `list_notes/get_note/get_custom_node/get_custom_relationship/list_revisions/get_revision`. Effect: no 422 oracle on invalid orders (marginal), and the boundary is even less constrained than reported. Fix comes free with the SEC-BE-002 clamp (route through `_resolve_effective_boundary`).

### SEC-ADV-004 | README documents exact production infra fingerprints | INFO | CONFIRMED
- `README.md:16` and `docs/ROADMAP.md:266` publish live infra identity (Render svc name, AuraDB instance `03a8623b`, Upstash db `darling-rat-221809`, hostnames). Not exploitable alone (no credentials), but it zeroes recon cost once any adjacent leak (e.g., dashboard misconfig) appears. Consider scrubbing to generic names.

## 3. Attack-chain analysis

| Chain | Steps (prereqs) | Impact | Likelihood | Fix |
|---|---|---|---|---|
| **A. Anonymous full-spoiler dump** (product-fatal) | 1) no account needed: `GET /candidates?visible_until_order=<last>` + `GET /notes?visible_until_order=999` + `GET /revisions?visible_until_order=999` + `GET /custom-nodes/…`; 2) or fresh Google account: `GET /graph?visible_until_order=96` (no progress record). | Complete defeat of the app's core spoiler-boundary guarantee; every claim's narrative evidence text, all users' notes, revision snapshots, author `user_id`s. | **Certain** (anonymous, no rate limit) | SEC-BE-002 clamp + auth on candidates/revisions; SEC-BE-001 fail-closed; drop `before/after`/`user_id` for non-owners. **P0.** |
| **B. Graph poisoning → cross-user indirect prompt injection** | 1) any Google account (or none needed to *read*); 2) `POST /candidates/ingest` with `visible_from_order:1` + payload text (spoiler or "ignore previous instructions…"); 3) claim visible at boundary 1 to all users in graph UI (`filter.py:16`) and enters every chat turn's `<claims>`/`<evidence>` context; 4) defense = framing only; uncited injected answers pass verbatim (`_finalize`, pipeline.py:1072-1076). | Spoilered/fabricated answers served as grounded; system-prompt disclosure; app integrity. | High (one account, one request) | SEC-BE-003 server-derived visibility + admin gate; SEC-LLM-004 delimiter neutralization + output guard. **P0.** |
| **C. Redis takeover via git history** | Read README/history for `REDIS_URL`. | — | **N/A — REJECTED.** Value is placeholder `<token>` in all 9 commits. Endpoint name alone ≠ access (Upstash token is the credential). | None (rotate only if ever pasted in dashboards). |
| **D. XSS → BYOK key theft** | Any XSS in SPA (none exists today) → `localStorage['spoilerless:byok-llm-settings']` → attacker spends user's LLM quota. | Key theft. | Low today (no XSS found), rises with every future rich-render feature since shell has **no CSP**. | SEC-FE-001 CSP on shell; keep keys in memory/sessionStorage. **P1.** |
| **E. Site-wide login lockout** | 10 failed `POST /api/auth/google` (any origin header) within 5 min → global bucket exhausted (proxy-IP key); repeat every 5 min. | Total login outage; also blocks legit signups. | Certain (any client) | `--proxy-headers --forwarded-allow-ips=<Render CIDR>` + per-IP keys; fail-closed limiter; login circuit breaker. **P0.** |
| **F. Cost farm / denial-of-wallet** | N burner Google accounts (open signup default); each 20 msgs/min, ≤5 calls/turn, 4 tool rounds, replay growth; no global semaphore; limiter fail-open on Redis blip. | $600-860/day (10 accounts) on the operator's stored key; worker saturation (60s×5 per turn). | High if prod allowlist empty + LLM enabled | `ALLOWED_EMAILS` required in prod (verify operator), global semaphore, per-round tool-call cap (≤8) + replay budget, token budget per user, BYOK-first. **P0 (verify config first).** |
| **G. BYOK SSRF against internal network** | Any account; `X-LLM-Base-URL: http://<internal-host>`; server POSTs `{base}/chat/completions` with attacker's key; status/timing oracle; 200-SSE content echo; no redirects. | Blind port scan/fingerprint of Render-internal services, POST side-effects on internal HTTP endpoints, self-SSRF probes. Stored key safe; CSRF fail-closed blocks self-SSRF state changes (no Origin → 403). | Medium (authenticated only) | Block loopback/private/link-local/metadata in `_validate_base_url` (both BYOK + stored); resolve-and-pin DNS. **P1.** |
| **H. Info-leak + SSRF + LLM exfiltration combo** | Combine A (spoilered data), B (poison), G (oracle). | No *secret* exfiltration path exists: keys never enter context; SSRF response handling only echoes SSE-shaped bodies; no URL tool in the LLM allowlist. Chain H degrades to A+B+G independently. | n/a | Fix A, B, G independently. |

## 4. Missed-area review (what the 9 agents didn't cover)

1. **S6's headline CRITICAL (SEC-INF-001) is factually wrong** — the "live password" is a literal `<token>` placeholder in every one of the 9 commits (verified byte-wise). The audit's severity pyramid loses its only CRITICAL in the secrets domain. Remaining secrets posture (allowlist logging, hashed sessions, no `.env` in git) is genuinely good.
2. **S8 missed the unthrottled candidates ingest** (SEC-ADV-001) — the one write path with unbounded volume and no limiter.
3. **S2/S5 overstated boundary validation on notes/custom/revisions GET** — no persisted-episode check at all (SEC-ADV-003).
4. **S6's SEC-INF-014 ("BYOK safe") contradicts S2/S4's SSRF finding** — the "safe" verdict covers key exfiltration only; the network primitive is real. Unresolved disagreement the lead must adjudicate.
5. **Nobody flagged the misleading BYOK copy vs. actual data flow** (key transits the app backend every request — S3 noted; S9 repeated; it is a privacy-notice gap, not a vuln).
6. **Positive verifications worth recording:** SSE framing injection-safe; Redis key collision-free by construction; all admin endpoints admin-gated; no IDOR on write paths; visitor-flag forging yields nothing beyond anonymous access (downgrade SEC-FE-006); `__pycache__` not tracked.

## 5. FINAL VERDICT

**NO — do not expose this to the public internet today (conditional: not before the P0 list lands).**

The app's *core security property is spoiler safety*, and that property is broken by **unauthenticated, unthrottled read routes** (Chain A) and **one-request graph poisoning** (Chain B) — both trivially exploitable with zero privileges, both confirmed at code level. Independently, availability is compromised by the global login bucket (Chain E) and wallet by the open-signup cost farm (Chain F, config-dependent). The one headline CRITICAL of the audit (Redis credential in git) does not exist — but that correction does not rescue the go/no-go: the spoiler-boundary findings alone are product-fatal.

**P0 (must land before public exposure):**
1. SEC-BE-002 family — anonymous clamp to order 1 (and auth-gate/persist-validate) on candidates/notes/custom-nodes/custom-relationships/revisions reads; strip `before/after`/`user_id` for non-owners.
2. SEC-BE-001 — fail closed to order 1 for authenticated users with no progress record on `/graph` and `/episodes`.
3. SEC-BE-003 — server-derive `visible_from_order`, verify subject/object/episode exist, gate or clamp ingest; add ingest rate limit (SEC-ADV-001).
4. SEC-DOS-003/SEC-BE-004 — trusted-proxy config so per-IP limits are per-IP again (or replace with a site-wide login circuit breaker).
5. SEC-DOS-001 — fail-closed rate limiting (never silent no-op in prod).
6. SEC-LLM-001/002 — block loopback/private/link-local/metadata `base_url` for BYOK and stored paths.
7. SEC-DOS-002/SEC-LLM-003 — require `ALLOWED_EMAILS` in prod (operator-verify now), global generation semaphore, per-round tool-call cap, body-size middleware (SEC-DOS-004).
8. SEC-INF-003 — disable `/docs`/`/redoc`/`/openapi.json` in prod.
9. SEC-FE-001 — CSP + security headers on the Vercel shell (backstops D and future XSS).
10. SEC-LOG-001 — drop `input`/`ctx` from validation-error logging.

**P1 (next):** SEC-LLM-004 output guard + delimiter neutralization; SEC-DOS-005 cache-key redesign; session Max-Age (SEC-BE-010); `email_verified` check (SEC-BE-007); TrustedHostMiddleware; candidate list pagination; SEC-ADV-002 invalidation on ingest.
