# S6 — Secrets, Infrastructure & Deployment Audit

**Audit:** 20260814-security-audit · **Subagent:** S6 (secrets / infra / network boundaries) · **Scope:** static only — no network probing, no prod requests, no secret values printed (all values below REDACTED)
**Repo:** `C:/Users/arhan/PycharmProjects/hdgrafcehennemi` · **App:** "Spoilerless" — Render backend + Vercel frontend + Cloudflare DNS + Neo4j AuraDB + Upstash Redis

---

## Executive summary

- **CRITICAL:** A live Upstash Redis connection string with an embedded password is committed in `README.md` (current tree, HEAD commit `099df01`) and in ≥9 commits of history.
- Secrets handling is otherwise solid: `.env` never tracked, `.gitignore` covers `.env*` (except template), no hardcoded creds in code, CI uses no secrets, LLM key is write-only/admin-gated, request logging denies auth/X-LLM headers.
- Deployment posture gaps: FastAPI `/docs` `/redoc` `/openapi.json` exposed in prod; uvicorn trusts no forward headers behind Render's proxy (per-IP rate limiting collapses); `render.yaml` carries zero env config and its service name drifts from the dashboard; release workflow's CI gate is a skeleton.
- TLS: no disabled verification found (Neo4j `neo4j+s`→certifi CA path, `rediss://` Redis, HSTS header). Config does not *enforce* `+s` schemes (a plain `neo4j://` prod URI would silently go plaintext).

---

## Findings

### SEC-INF-001 | Live Upstash Redis credential committed to git (README + history) | CRITICAL | High
- **Component:** `README.md` (repo root), git history
- **Entry point:** `README.md:40` — Deployment & Environment Quick Reference block: `REDIS_URL=rediss://default:REDACTED@darling-rat-221809.upstash.io:6379` (password REDACTED here; 7-char, non-placeholder — every sibling line in the same block uses `<...>` placeholders, this one is a real value). Introduced in `099df01` (HEAD); present in `3b1a3b6`, `2207919`, `0e28695`, `51d69c5`, `b30ccc5`, `e62e664`, `ec13d3d`, `9a472d3` (confirmed via `git log -S darling-rat`).
- **Data flow:** repo (public GitHub `vinnipukh/hdgrafcehennemi`, HTTPS remote) → anyone who clones/forks/mirrors → Upstash Redis endpoint with credentials.
- **Vulnerability:** Production secret committed to version control; survives in history even after deletion.
- **Attack scenario:** Attacker reads README (or `git log -S`) → connects to Upstash Redis → reads/writes rate-limit counters and graph/viz cache → poisons cached graph responses (spoiler injection), resets/floods rate-limit buckets, or harvests the credential for reuse.
- **Impact:** Redis takeover; cache poisoning of spoiler-filtered data; rate-limit bypass; credential reuse.
- **Reproduction:** `git log --all -S darling-rat -- README.md`; `grep -n REDIS_URL README.md` (line 40).
- **Existing defenses:** Redis is Upstash-hosted with TLS (`rediss://`); no WAF on the Redis endpoint (Upstash REST/Redis is credential-gated only).
- **Recommended fix:** (1) Rotate the Upstash password immediately (Upstash console → reset credentials); (2) replace the value with `<Upstash rediss:// connection string>` in README; (3) purge history (`git filter-repo --replace-text` or BFG) and force-push; (4) add gitleaks/trufflehog pre-commit hook + CI secret scan (see SEC-INF-002).
- **Verification:** After rotation+purge: `git log --all -p | grep -c darling-rat` = 0; `git remote show origin` + `gitleaks detect` on a fresh clone = clean.

### SEC-INF-002 | No automated secret scanning (CI or pre-commit) | MEDIUM | High
- **Component:** `.github/workflows/ci.yml`, repo hygiene
- **Entry point:** CI pipeline on pull_request.
- **Data flow:** developer commit → push → CI.
- **Vulnerability:** Nothing detects secret-pattern content before merge; SEC-INF-001 shipped through CI and the whole history.
- **Attack scenario:** Developer accidentally commits a key; it merges and remains in history indefinitely.
- **Impact:** Recurrence of SEC-INF-001; silent credential exposure.
- **Reproduction:** Inspect `.github/workflows/ci.yml` — backend/frontend jobs only (no gitleaks/trufflehog step).
- **Existing defenses:** `.gitignore` covers `.env*`; `npm audit --audit-level=high` runs in CI (dependency-focused only).
- **Recommended fix:** Add `gitleaks` (actions/gitleaks-action or `gitleaks detect` step) on PR + push, plus a pre-commit hook.
- **Verification:** Introduce a dummy `sk-` string in a branch → CI fails with gitleaks finding.

### SEC-INF-003 | FastAPI interactive docs & OpenAPI schema exposed in production | MEDIUM | High
- **Component:** `spoilerless/app/main.py:164-168` (`FastAPI(title=..., version=...)` with default `docs_url`); `render.yaml` startCommand.
- **Entry point:** `GET /docs`, `/redoc`, `/openapi.json` on `api.spoilerless.net` / `spoilerless.onrender.com`.
- **Data flow:** unauthenticated internet → FastAPI default routes.
- **Vulnerability:** Full API schema (all 52 routes, params, models, admin endpoints) public; version string `0.1.0` + title leak.
- **Attack scenario:** Recon: attacker enumerates admin/undocumented endpoints, learns exact parameter shapes, targets the settings/share/auth surface precisely.
- **Impact:** Aids targeted attacks; minor version/enum disclosure. No direct data breach.
- **Reproduction:** No `docs_url=None` / `redoc_url=None` / `openapi_url=None` anywhere in `main.py` or env; `render.yaml` startCommand runs plain uvicorn.
- **Existing defenses:** Routes themselves are auth-gated; no sensitive data in the schema.
- **Recommended fix:** Gate docs behind `ENV=production` (or an env flag): `docs_url=None, redoc_url=None, openapi_url=None` when `APP_ENV == "production"`, or serve only on a non-public path. Keep `/openapi.json` off in prod.
- **Verification:** `curl -s -o /dev/null -w '%{http_code}' https://api.spoilerless.net/docs` → 404 after fix (was 200).

### SEC-INF-004 | Trusted-proxy misconfig: per-IP rate limiting collapses behind Render proxy | MEDIUM | Medium
- **Component:** `render.yaml:10` startCommand (`uvicorn ... --host 0.0.0.0 --port $PORT`, no `--proxy-headers` / `--forwarded-allow-ips`); `spoilerless/app/services/rate_limit.py:50` (`request.client.host` as anonymous key).
- **Entry point:** any anonymous request to login (10/5min), content-write (30/min), user_content routes.
- **Data flow:** internet → Render proxy → uvicorn. Uvicorn default `forwarded_allow_ips=127.0.0.1` → Render proxy IP (non-loopback) is not trusted → `request.client.host` = proxy IP for **all** clients.
- **Vulnerability:** All anonymous traffic shares one rate-limit bucket (single proxy IP); X-Forwarded-For is ignored (safe from spoofing, but breaks attribution).
- **Attack scenario:** (a) One attacker exhausts the shared bucket → global lockout of login/content-write (DoS); (b) conversely an attacker can't be individually throttled; (c) logs record proxy IP, not client IP.
- **Impact:** Rate limiting ineffective/anonymized; anonymous-route DoS; degraded abuse attribution.
- **Reproduction:** Static: no `FORWARDED_ALLOW_IPS`/`--forwarded-allow-ips` anywhere in repo (`grep -rn "forwarded" render.yaml spoilerless/ scripts/` → only unrelated match in `retrieval/pipeline.py`).
- **Existing defenses:** Authenticated requests key on user id (not IP) — chat/write limits still work per user.
- **Recommended fix:** Set `FORWARDED_ALLOW_IPS=*` (uvicorn env var) or add `--forwarded-allow-ips=*` behind Render's trusted proxy, and confirm via `request.client.host` logging; alternatively key anonymous limits on `X-Forwarded-For` first hop after verifying Render's proxy sets it.
- **Verification:** Deploy, hit `/api/...` twice from different egress IPs, observe distinct `ip:` buckets in Redis keys `hdgraf:rate_limit:*`.

### SEC-INF-005 | render.yaml carries no environment config; infra-as-code drift | MEDIUM | High
- **Component:** `render.yaml` (10 lines: build/start only).
- **Entry point:** Render deploy pipeline / dashboard.
- **Data flow:** operator dashboard → service env.
- **Vulnerability:** All secrets/config (`REDIS_URL`, `FRONTEND_ORIGINS`, `ALLOWED_EMAILS`, `ADMIN_EMAILS`, `SESSION_COOKIE_*`, `LLM_*`, Aura creds) live unversioned in the dashboard: no audit trail, no review, no rollback, no staging parity. Service name in `render.yaml` (`spoilerless-api`) differs from the dashboard service (`spoilerless`, per deployment context) — blueprint re-apply would create a duplicate service. No `healthCheckPath` configured.
- **Attack scenario:** Operator error or silent dashboard change (e.g. `FRONTEND_ORIGINS` unset → default `http://localhost:5173`; `ALLOWED_EMAILS` unset → open sign-in, per `config.py:60-67` "never leave empty in production") ships without review.
- **Impact:** Config drift; potential open sign-in / broken CORS in prod; deployment tooling mismatch.
- **Reproduction:** `cat render.yaml` — no `envVarGroups`/`env` section; compare `name:` with the dashboard service name.
- **Existing defenses:** `docs/DEPLOYMENT.md` documents dashboard-only env setup (manual SOP).
- **Recommended fix:** Move env into `render.yaml` `envVarGroups` (secret values via Render secret files/dashboard with a documented SOP), align service name to the dashboard, add `healthCheckPath: /health`.
- **Verification:** `render blueprint validate`; dashboard shows blueprint-managed env; `healthCheckPath` probe green.

### SEC-INF-006 | CORS origin list unverifiable from repo; default is localhost-only | MEDIUM | Medium
- **Component:** `main.py:192-214` (CORSMiddleware, `allow_credentials=True`, explicit origins from `FRONTEND_ORIGINS`); `config.py:56-59` (default `http://localhost:5173`); `render.yaml` (no env).
- **Entry point:** browser → API `OPTIONS`/credentialed requests.
- **Data flow:** SPA origin → CORS check → backend.
- **Vulnerability:** If `FRONTEND_ORIGINS` is unset on Render, prod CORS allows only `http://localhost:5173` → real frontend blocked (availability) — or, if the operator ever widens it, the config is invisible to review. Config itself is correct (explicit list + credentials, no wildcard). SameSite=lax session cookie only flows same-site (`*.spoilerless.net`); direct calls to the raw Render origin would silently drop cookies.
- **Attack scenario:** (n/a — misconfig is availability/verifiability, not exploitability, unless origins are widened unknowingly).
- **Impact:** Broken prod login if unset; unverifiable security posture.
- **Reproduction:** Static only — `FRONTEND_ORIGINS` appears in no tracked file for prod (README example shows `https://app.spoilerless.net`).
- **Existing defenses:** Explicit allowlist; `allow_credentials=True` without wildcard (PROB-17/#38).
- **Recommended fix:** Set `FRONTEND_ORIGINS=https://app.spoilerless.net` in render.yaml env (SEC-INF-005); add a startup assertion that fails when `frontend_origins` contains localhost while `APP_ENV=production`.
- **Verification:** `curl -H "Origin: https://app.spoilerless.net" -i https://api.spoilerless.net/health | grep -i access-control-allow-origin` → echo of origin.

### SEC-INF-007 | Backend origin reachable outside Cloudflare (no edge protection on API) | MEDIUM | Medium
- **Component:** deployment topology — Cloudflare DNS fronts `api.spoilerless.net`; Render origin `spoilerless.onrender.com` per deployment context (health probe target).
- **Entry point:** internet → Render origin directly (if DNS/WAF not origin-locked).
- **Data flow:** attacker → `*.onrender.com` → backend (bypasses Cloudflare WAF/rate-limit/CDN).
- **Vulnerability:** Raw Render origin is a separate public hostname; nothing in repo configures origin protection (no Cloudflare Authenticated Origin Pulls, no IP allowlist documented for Render).
- **Attack scenario:** Attacker bypasses Cloudflare (WAF, bot management, edge rate limiting) and hits the origin directly — relevant once SEC-INF-004 is fixed, since edge-level throttles would not apply.
- **Impact:** Weakened network boundary; all app defenses reduced to app-level controls.
- **Reproduction:** Static-only (no network requests per audit rules): no origin-lock config in repo/docs; `onrender.com` not mentioned in README/docs (good — origin not advertised, but health probes confirm the hostname).
- **Existing defenses:** App-level auth/rate limiting; CSP/HSTS; docs avoid leaking the origin URL.
- **Recommended fix:** Verify origin reachability; if reachable, restrict Render service to Cloudflare egress (IP allowlist or Cloudflare Tunnel / Authenticated Origin Pulls), or set Cloudflare as the only DNS record for the API hostname.
- **Verification:** From a non-CF network: `curl -I https://spoilerless.onrender.com/health` → should time out/403 after fix.

### SEC-INF-008 | /health discloses DB connectivity + service marker to anonymous callers | LOW | High
- **Component:** `main.py:104-110, 222-249` (`HealthResponse`: status/database/service only; HEAD variant for uptime monitors).
- **Entry point:** `GET|HEAD /health` (unauthenticated).
- **Data flow:** internet → `/health` → live Neo4j `verify_connectivity()`.
- **Vulnerability:** Probes reveal backend DB reachability state and the internal service marker `spoilerless-backend`; no version/build/redis/env fields (good). `extra="forbid"` on the response model.
- **Attack scenario:** Attacker times health checks to time DB migrations/outages; service marker aids fingerprinting.
- **Impact:** Minimal info leak; standard for uptime monitors.
- **Reproduction:** `main.py:222-249` — fields limited to status/database/service.
- **Existing defenses:** Minimal field set already; 503 on DB down (intentional degraded-startup design).
- **Recommended fix:** Acceptable as-is; optionally drop the `service` marker or gate detail behind an admin header. Do not add redis/version/build fields.
- **Verification:** n/a.

### SEC-INF-009 | Secret-pattern strings and a real local dev password scattered through git history | LOW | High
- **Component:** git history (docs, `.planning/*`, legacy `backend/` tree, test fixtures).
- **Entry point:** `git log --all -p` / any clone.
- **Data flow:** history → scanner/attacker.
- **Vulnerability:** ~296 secret-pattern hits across history (`sk-*`, `AIza*`, `rediss://*`, `api_key=*`, `bolt://*`); most are placeholders/test fixtures (`sk-test-secret`, `sk-byok-secret`, `rediss://fake...`, `ci-test-password-not-used-elsewhere`), but `PASSWORD=hdg` (real local Neo4j password) appears in docs (DEVELOPMENT/GETTING-STARTED/TESTING/PROBLEMS/README history, e.g. `23f619e`, `0e28695`, `6a19e70`). Legacy `backend/` package path adds scanner noise. `.env` itself was never tracked (verified: `git log --all -- .env` empty). Stash empty; reflog clean of secrets.
- **Attack scenario:** Automated secret scanners flag the repo; an attacker tests `hdg` against any exposed Neo4j instance.
- **Impact:** Low (local-only credential, but real); scanner fatigue; false positives.
- **Reproduction:** `git log --all -p | grep -cE 'sk-|AIza|rediss://'` → 296 hits.
- **Existing defenses:** `.gitignore` covers `.env*`; history purge never performed.
- **Recommended fix:** Optional history scrub via `git filter-repo` (rename `backend/`→`spoilerless/` origin is already in history); replace `PASSWORD=hdg` doc examples with `<password>`; then run gitleaks history scan (`gitleaks detect --log-opts=--all`).
- **Verification:** `gitleaks detect` on fresh clone returns 0 findings (or only documented placeholders).

### SEC-INF-010 | GitHub Actions third-party actions pinned to mutable tags | LOW | High
- **Component:** `.github/workflows/ci.yml`, `.github/workflows/release.yml`.
- **Entry point:** CI/CD execution.
- **Data flow:** workflow → actions marketplace tags → runner.
- **Vulnerability:** `actions/checkout@v5`, `actions/setup-node@v4`, `actions/upload-artifact@v4` resolve mutable tags (supply-chain: tag retarget = arbitrary code in CI). `astral-sh/setup-uv` is SHA-pinned (`08807647...` # v8.1.0) — good. `npm audit --audit-level=high` runs (good). `ci.yml` has no explicit `permissions:` block (defaults apply on PR trigger; `release.yml` correctly sets `contents: read`).
- **Attack scenario:** Compromised/malicious tag retarget on a pinned-by-tag action executes attacker code with repo/runner access.
- **Impact:** CI compromise → artifact tampering, secret exfiltration (none currently used, but CI has no secrets today).
- **Reproduction:** `grep "uses:" .github/workflows/*.yml`.
- **Existing defenses:** setup-uv SHA-pinned; no secrets in CI env; npm audit.
- **Recommended fix:** Pin all `uses:` to full commit SHAs (Dependabot `enable-beta-ecosystems` / `update: github-actions` keeps them current); add explicit `permissions: contents: read` to `ci.yml`.
- **Verification:** `grep "uses:" .github/workflows/*.yml` → all SHA references.

### SEC-INF-011 | Loose dependency ranges in pyproject/package.json (lockfile mitigates) | LOW | High
- **Component:** `pyproject.toml` (all `>=` floors, no upper bounds), `frontend/package.json` (caret ranges), `uv.lock` + `frontend/package-lock.json` committed.
- **Entry point:** dependency resolution at build (`uv sync --frozen`, `npm ci`).
- **Data flow:** lockfile → deploy artifact.
- **Vulnerability:** Floor-only ranges allow transitive drift on fresh installs; mitigations are strong: `uv sync --frozen` in CI and Render buildCommand, `npm ci` + committed lockfiles, `npm audit` gate.
- **Attack scenario:** Malicious/compromised upstream release pulled in by a fresh `uv sync` outside the frozen path.
- **Impact:** Supply-chain risk limited to non-frozen installs (e.g. operator laptops).
- **Reproduction:** `pyproject.toml:5-16` — `fastapi>=0.140.7`, `neo4j>=6.2.0`, etc.
- **Existing defenses:** Committed `uv.lock`/`package-lock.json`; frozen installs; npm audit in CI.
- **Recommended fix:** Enable Dependabot for pip/uv + npm; consider upper-bound pins for runtime deps; keep `--frozen` mandatory.
- **Verification:** Dependabot PRs land; `uv lock --check` passes.

### SEC-INF-012 | Neo4j TLS not enforced at config level (silent plaintext fallback) | LOW | High
- **Component:** `spoilerless/app/graph/database.py:68-97`; `config.py` `neo4j_uri` alias.
- **Entry point:** backend startup env `NEO4J_URI`/`aura_uri`.
- **Data flow:** driver → DB connection.
- **Vulnerability:** `neo4j+s://`/`bolt+s://` are normalized to `neo4j://` + `encrypted=True` + certifi `TrustCustomCAs` (CA-verified, deterministic — good). But a plain `neo4j://`/`bolt://` prod URI (typo/misconfig) connects **plaintext with no guard**; no startup validation enforces `+s` outside loopback.
- **Attack scenario:** Misconfigured prod URI → credentials + graph data in cleartext on the wire.
- **Impact:** Credential/data disclosure on the network path; low likelihood (Aura requires +s and local `.env` uses loopback).
- **Reproduction:** `database.py:74-87` — only `+s` prefixes trigger TLS kwargs.
- **Existing defenses:** Aura's own TLS requirements; local dev loopback-only URI.
- **Recommended fix:** Validate in `Settings`: require `neo4j+s://`/`bolt+s://` when host is not localhost/127.0.0.1; fail startup otherwise.
- **Verification:** Unit test: `Settings(neo4j_uri="neo4j://prodhost")` raises.

### SEC-INF-013 | LLM API key stored plaintext in Neo4j :AppSetting | LOW | High
- **Component:** `spoilerless/app/repository/settings.py:17-18` (`SETTINGS_UPSERT_QUERY ... SET s.value = $value`); `spoilerless/app/api/settings.py` (admin-only, CSRF-guarded, GET returns masked key).
- **Entry point:** admin `PUT /api/settings/llm`.
- **Data flow:** admin → Neo4j `:AppSetting {key:'llm'}` node (plaintext property).
- **Vulnerability:** Secret at rest in the graph DB, unprotected by app-layer encryption; anyone with AuraDB access (or a future DB leak) reads it. Mitigations: admin-only API, masked responses, never logged, "read only inside provider" discipline.
- **Attack scenario:** DB backup/exfiltration or Aura credential compromise → LLM key harvested; provider billing abuse.
- **Impact:** Provider account abuse; limited blast radius (single key).
- **Reproduction:** `settings.py:18` — plain `SET s.value = $value`.
- **Existing defenses:** Admin-gated write/read; masked GET; no logging (T-06-07).
- **Recommended fix:** Acceptable given DB access control; consider encrypting the value at rest (app-layer envelope encryption) or preferring `LLM_API_KEY` env var and keeping DB value as fallback.
- **Verification:** `MATCH (s:AppSetting{key:'llm'}) RETURN s.value` shows ciphertext after fix.

### SEC-INF-014 | BYOK X-LLM-* headers: safe handling confirmed | INFO | High
- **Component:** `main.py:43-44, 206-213` (header deny-list for logs; CORS allowlist for `X-LLM-Api-Key/Provider/Base-URL/Model`); `services/chat.py:79-82, 114-130`.
- **Entry point:** authenticated chat requests with BYOK headers.
- **Data flow:** browser-held key → backend → provider (key never persisted, never logged).
- **Vulnerability:** None found: header path is used only when `X-LLM-Api-Key` present; stored key path uses only admin-set base_url (no header override → no stored-key exfiltration via `X-LLM-Base-URL`); `_validate_base_url` restricts to http/https with host (per S0 notes; allowlisted); provider keys never written to repo/records.
- **Attack scenario:** n/a.
- **Impact:** n/a.
- **Reproduction:** `chat.py:114-130` — BYOK branch requires the header key; stored-key branch at `:155-176` ignores client headers.
- **Existing defenses:** Log deny-list; CORS allowlist; validation; admin-only stored settings.
- **Recommended fix:** None required. Optional: reject `http://` base URLs in prod to keep BYOK keys off plaintext transit.
- **Verification:** n/a.

### SEC-INF-015 | Release workflow CI gate is a non-functional skeleton | MEDIUM | High
- **Component:** `.github/workflows/release.yml` (`verify-ci-gate` job body is an `echo`; `tag` job pushes without real verification).
- **Entry point:** `workflow_dispatch` release promotion.
- **Data flow:** operator → GitHub → tag push.
- **Vulnerability:** The "gate" asserts nothing (comment admits: "Skeleton: in a full setup this step queries the checks API..."); workflow-level `permissions: contents: read` would actually prevent the `git push origin $TAG` step (needs `contents: write`) — as written the release path either fails or, if permissions are widened, pushes tags with no CI verification.
- **Attack scenario:** Untested code promoted to a release tag; or a misleading green "gate" giving false confidence.
- **Impact:** Release integrity; false assurance; broken pipeline.
- **Reproduction:** `release.yml:27-33` — echo-only gate; `permissions: contents: read` at `:20-21` vs tag push at `:43-44`.
- **Existing defenses:** `ci.yml` runs on PRs (branch protection out of band, per comment).
- **Recommended fix:** Implement the gate (GitHub Checks API query for the head SHA's `ci` run status, fail otherwise); set `permissions: contents: write` only on the `tag` job; or delete the workflow until real.
- **Verification:** Run `workflow_dispatch` with failing CI state → job fails before tagging.

---

## Non-findings (verified clean)

- `.env` never tracked; `.gitignore` covers `.env`, `.env.*` (whitelists `.env.example`); only key NAMES present in local `.env` (`NEO4J_*`, `aura_*`, `GOOGLE_CLIENT_ID`, `AUTH_DEV_CODE` — the latter has **no code references** anywhere, dead local config). `frontend/.env.example` has no secrets; `VITE_GOOGLE_CLIENT_ID` is public-by-design (OAuth client ID, not secret).
- docker-compose binds Neo4j to `127.0.0.1` only; CI Neo4j password is an explicit throwaway (`ci-test-password-not-used-elsewhere`).
- Session cookie: HttpOnly + Secure (default true) + SameSite=lax, host-only (no `domain=` widening) — correct.
- HSTS (`max-age=31536000; includeSubDomains`), CSP, nosniff, X-Frame-Options DENY set in middleware.
- No `verify=False` / TLS-disabled code paths anywhere; Redis is `rediss://` (TLS).
- No hardcoded creds in `spoilerless/` source; request logging denies Cookie/Authorization/X-LLM-*.
- `.hermes/`, `.claude/` contain no secrets (attachments are planning docs).
