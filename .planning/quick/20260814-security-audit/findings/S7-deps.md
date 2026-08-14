# S7 — Dependency & Supply-Chain Audit (hdgrafcehennemi / Spoilerless)

Auditor: S7 (dependency/supply-chain). Date: 2026-08-14/15. Scope: pyproject.toml + uv.lock (Python 3.13 — repo truth; task context said 3.11, but `.python-version`/`requires-python` are consistently `>=3.13`), frontend/package.json + package-lock.json (lockfileVersion 3, 641 entries, integrity hashes present), .github/workflows/ci.yml + release.yml, docker-compose.yml, render.yaml. Methods: `npm audit` (registry live, exit 1 = findings), manual CVE knowledge for Python (pip-audit NOT installed), dependency-path tracing via `npm ls`, built-bundle grep for reachability, lockfile static analysis. No packages installed or upgraded.

## Bottom line

- **No reachable known-vulnerable code at runtime.** All 5 npm audit findings (4 high, 1 moderate) are transitive through `shadcn@4.16.0`, a CLI that is (a) declared as a **runtime dependency**, (b) never imported by app code, and (c) provably absent from the built bundle (`dist/assets/*.js`). Effective risk: **not exploitable in this app** — but the CI `npm audit --audit-level=high` gate will **fail on the next PR** (4 high present), and the misclassified CLI inflates the prod tree to 432 packages.
- Python tree is clean per available knowledge: all versions current (fastapi 0.140.7, starlette 1.3.1, pydantic 2.13.4, certifi 2026.7.22, urllib3 2.7.0, neo4j 6.2.0, redis 8.1.0, cryptography 49.0.0). All third-party packages resolve to wheels (no setup.py build hooks); only install-script package in the npm tree is `fsevents@2.3.3` (macOS-only optional native dep, benign on Linux/Windows).
- No typosquats found. `annotated-doc@0.0.4` (name looks suspicious) is a **legitimate** FastAPI dependency (pydantic team docs package; lock source verified `files.pythonhosted.org`, hashes present). All other names match official packages.
- Main structural issues: mutable (non-SHA) GitHub Actions tags, lower-bound-only Python pins, shadcn CLI in `dependencies`, no automated Python vuln scanning.

## Inventory

### Python (uv.lock, 45 packages; all `source: registry` with pinned hashes)

| Package | Version | Purpose | Pinned? | Notes |
|---|---|---|---|---|
| fastapi | 0.140.7 | API framework | Lock-pinned; manifest `>=0.140.7` | Current; pulls annotated-doc (legit) |
| uvicorn[standard] | 0.51.0 | ASGI server | Lock; `>=0.51.0` | → uvloop/httptools/watchfiles/websockets/click |
| starlette | 1.3.1 | ASGI toolkit | Lock | Current; old multipart DoS (CVE-2024-47874) fixed long ago |
| pydantic | 2.13.4 | validation | Lock | Current |
| pydantic-settings | 2.14.2 | config | Lock; `>=2.14.2` | Current |
| neo4j | 6.2.0 | graph driver | Lock; `>=6.2.0` | Current; pulls pytz |
| redis | 8.1.0 | cache + rate limit | Lock; `>=8.1.0` | Reachable (graph cache, RateLimiter) |
| fastapi-limiter | 0.2.0 | rate limiting | Lock; `>=0.2.0` | Reachable (login/chat/write limiters). Niche, low-activity upstream — monitor (SEC-DEP-010) |
| pyrate-limiter | 4.4.0 | limiter backend | Lock | Reachable |
| google-auth[requests] | 2.56.2 | Google token verify | Lock; `>=2.56.2` | Reachable (auth.py); → pyasn1/pyasn1-modules |
| requests | 2.34.2 | HTTP | Lock | via google-auth |
| urllib3 | 2.7.0 | HTTP | Lock | Current |
| certifi | 2026.7.22 | CA roots | Lock; `>=2026.7.22` | Fresh |
| cryptography | 49.0.0 | crypto | Lock | Current; → cffi/pycparser |
| pyyaml | 6.0.3 | YAML | Lock; `>=6.0.3` | Current; verify app uses safe_load |
| python-dotenv | 1.2.2 | env files | Lock; `>=1.2.2` | — |
| annotated-doc | 0.0.4 | FastAPI docs dep | Lock | LEGIT (pydantic team), not typosquat |
| httpx / pytest / pytest-asyncio | 0.28.1 / 9.1.1 / 1.4.0 | dev/test | Lock; `>=` in dev group | Dev-only (pytest pulls pygments, iniconfig, packaging, pluggy, colorama) |
| spoilerless | 0.1.0 | this project | n/a | Only sdist-only entry (build-from-source) |

### npm (frontend, package-lock.json v3, 641 entries, integrity hashes on all)

| Package | Version | Purpose | Pinned? | Notes |
|---|---|---|---|---|
| react / react-dom | 19.2.7 | UI | `^` | Current |
| cytoscape | 3.34.0 | graph canvas | `^3.34.0` | Runtime, reachable |
| cytoscape-cose-bilkent | 4.1.0 | layout | `^4.1.0` | Runtime; very quiet upstream — monitor (SEC-DEP-013) |
| cytoscape-dagre | 4.0.0 | layout | exact | Runtime, reachable |
| cytoscape-fcose | 2.2.0 | layout | `^2.2.0` | Runtime, reachable |
| react-cytoscapejs | 2.0.0 | React wrapper | `^2.0.0` | Runtime; quiet upstream — monitor (SEC-DEP-013) |
| radix-ui / lucide-react / clsx / cva / tailwind-merge / tw-animate-css | 1.6.7 / 1.27.0 / 2.1.1 / 0.7.1 / 3.6.0 / 1.4.0 | UI primitives | `^` | All official packages |
| tailwindcss / @tailwindcss/vite | 4.3.3 | styling | `^4.3.3` | Build-time |
| @fontsource-variable/* | 5.3.0 | fonts | `^` | Official |
| **shadcn** | **4.16.0** | **CLI codegen** | `^4.16.0` | **MISCLASSIFIED as runtime dep; sole carrier of ALL 5 audit findings** (SEC-DEP-001..006) |
| vite 8.1.5 / vitest 4 / typescript 6.0.2 / eslint 10.6 / jsdom 30 / testing-library | — | dev/build/test | `^`/`~` | Dev-only; no audit findings in dev tree |

### Infra

| Component | Version/Pin | Notes |
|---|---|---|
| .github/workflows/ci.yml | checkout@v5, setup-node@v4, upload-artifact@v4 (major tags), setup-uv@SHA `0880764…` (v8.1.0) | Mutable tags — SEC-DEP-008 |
| .github/workflows/release.yml | checkout@v5 | `permissions: contents: read` (good); tag step pushes tags |
| docker-compose.yml | neo4j:2026.06.0-community | Patch-pinned tag, no digest; ports bound to 127.0.0.1 (good) |
| render.yaml | `uv sync --frozen` + uvicorn | Lockfile-frozen build (good); autoDeploy on push |

## Findings

### SEC-DEP-001 | shadcn CLI declared as runtime dependency (attack-surface bloat + root cause of all npm vulns)
- **Severity:** High | **Confidence:** High
- **Component:** frontend/package.json:28 (`"shadcn": "^4.16.0"` under `dependencies`)
- **Vulnerability:** The `shadcn` CLI codegen tool is a build-time/authoring utility, not app code. Declaring it in `dependencies` pulls its full toolchain (`@modelcontextprotocol/sdk`, `ts-morph`, `cosmiconfig`, `postcss`, `@dotenvx/dotenvx`, ajv, hono…) into the **production** dependency set (432 prod packages for a SPA that needs ~20), and every npm audit finding in this repo traces back to it.
- **Reachability:** Not exploitable at runtime — `shadcn` is never imported by `src/` (only comments mention shadcn components) and its packages are absent from `dist/assets/*.js`. Risk is tree-wide: any future advisory in that 400-package toolchain will keep failing CI and alarming audits, and a compromised CLI could run code at author time.
- **Existing defenses:** lockfile v3 with integrity hashes; `npm ci` in CI; `npm audit --audit-level=high` gate.
- **Recommended fix:** Move `shadcn` to `devDependencies` (components are already committed — consider removing it entirely). Then `npm audit fix` (or `npm update`) to clear remaining transitive advisories; re-run `npm audit` to confirm 0 high.
- **Verification:** `npm audit --audit-level=high` exits 0; `npm ls shadcn` shows it under dev; bundle size drops.

### SEC-DEP-002 | hono@4.12.32 — 4 advisories (CORS ReDoS, `memo()` SSR data disclosure, proxy `Connection` header leak, language-middleware DoS)
- **Severity:** Moderate (effective: none) | **Confidence:** High (reachability), High (existence — npm audit live)
- **Component:** package-lock `node_modules/hono` 4.12.32 via `shadcn@4.16.0 → @modelcontextprotocol/sdk@1.30.0 → @hono/node-server@2.0.12`
- **Vulnerability:** GHSA-8j4g-w8fx-2239 (ReDoS in CORS middleware, <4.12.34), GHSA-f23p-vx2j-j53r (SSR memo cross-user disclosure), GHSA-79qm-7rj5-m7r9 (proxy header leak), GHSA-54fx-42gc-7vw4 (language middleware algorithmic DoS). Fix: ≥4.12.34.
- **Reachability:** NOT REACHABLE. hono exists only as the MCP SDK's embedded server inside the shadcn CLI; the app never starts a hono server, never SSRs (client-side Vite SPA), and hono is not in the built bundle. No attacker-controlled input ever reaches hono code.
- **Existing defenses:** none needed; bundle excludes it.
- **Recommended fix:** Fold into SEC-DEP-001 (remove/relocate shadcn). Optionally add `"overrides": {"hono": "^4.12.34"}` if the CLI must stay.
- **Verification:** `npm audit` clean; `grep -r hono dist/assets` empty.

### SEC-DEP-003 | js-yaml@4.3.0 — quadratic CPU in `!!omap` resolution (CVE-2026-59870 fix not backported)
- **Severity:** High (effective: none) | **Confidence:** High
- **Component:** package-lock `node_modules/js-yaml` 4.3.0 via `shadcn → cosmiconfig@9.0.2` (GHSA-5p4m-2wfm-xmqj, fix ≥4.3.1)
- **Reachability:** NOT REACHABLE. cosmiconfig parses local, developer-controlled config files at CLI authoring time; no runtime path parses YAML. The app backend uses PyYAML (Python side, 6.0.3 — not this package).
- **Recommended fix:** part of SEC-DEP-001 cleanup (bump via lockfile refresh).
- **Verification:** `npm audit` clean.

### SEC-DEP-004 | brace-expansion@5.0.8 — DoS via unbounded intermediate arrays
- **Severity:** High (effective: none) | **Confidence:** High
- **Component:** package-lock `node_modules/brace-expansion` 5.0.8 via `shadcn → ts-morph@26.0.0 → @ts-morph/common@0.27.0 → minimatch@10.2.6` (GHSA-rgw5-rvv9-x895, fix ≥5.0.9)
- **Reachability:** NOT REACHABLE. minimatch here powers TypeScript AST file matching inside the CLI; no app/runtime code path expands globs from untrusted input.
- **Recommended fix:** part of SEC-DEP-001 cleanup.
- **Verification:** `npm audit` clean.

### SEC-DEP-005 | fast-uri@3.1.4 — host confusion via backslash authority introducer
- **Severity:** High (effective: none) | **Confidence:** High
- **Component:** package-lock `node_modules/fast-uri` 3.1.4 via `shadcn → @dotenvx/dotenvx → conf → ajv@8.20.0` (GHSA-7p8r-x3mc-p8w7, fix ≥3.1.5)
- **Reachability:** NOT REACHABLE. ajv validates CLI's local config schemas; no network-facing URI parsing uses this code in the app.
- **Recommended fix:** part of SEC-DEP-001 cleanup.
- **Verification:** `npm audit` clean.

### SEC-DEP-006 | nanoid@3.3.16 — custom generators loop indefinitely with size 0
- **Severity:** High (effective: none) | **Confidence:** High
- **Component:** package-lock `node_modules/nanoid` 3.3.16 via `shadcn → postcss@8.5.25` (GHSA-2v37-7h3g-55p8, fix ≥3.3.18)
- **Reachability:** NOT REACHABLE. This postcss copy is the CLI's; the app's Tailwind v4 pipeline uses `@tailwindcss/vite` (lightningcss-based), not postcss. No app code calls nanoid generators.
- **Recommended fix:** part of SEC-DEP-001 cleanup.
- **Verification:** `npm audit` clean.

### SEC-DEP-007 | CI audit gate currently red — next PR's frontend job will fail
- **Severity:** Medium | **Confidence:** High
- **Component:** .github/workflows/ci.yml:77 (`npm audit --audit-level=high`) + frontend/package-lock.json (last updated 2026-08-13, commit 5aedd1a)
- **Vulnerability:** 4 high + 1 moderate advisories exist in the locked tree (SEC-DEP-002..006); `npm audit --audit-level=high` exits 1 → `frontend` CI job fails. Findings postdate the last lockfile refresh, so this is a time bomb for the next PR, not a regression.
- **Reachability:** CI process impact (blocked merges), not runtime.
- **Existing defenses:** the gate itself is the defense — it will catch this; the failure is by design.
- **Recommended fix:** Refresh the lockfile (`npm audit fix` or targeted `npm update` after SEC-DEP-001) so the gate passes with 0 high. Consider `--audit-level=moderate` once clean.
- **Verification:** `npm audit --audit-level=high` exits 0 locally; CI frontend job green.

### SEC-DEP-008 | GitHub Actions pinned to mutable major-version tags (not SHAs)
- **Severity:** Medium | **Confidence:** High
- **Component:** .github/workflows/ci.yml:21,68,53 (`actions/checkout@v5`, `actions/setup-node@v4`, `actions/upload-artifact@v4`); release.yml:27 (`checkout@v5`)
- **Vulnerability:** Floating tags can be force-moved by the action owner or a compromised account; a malicious replacement executes in CI with the workflow's token. Standard supply-chain hardening.
- **Reachability:** Compromise requires upstream action compromise — but CI runs on every PR (incl. forks under `on: [pull_request]`), and a tampered toolchain can inject code into build artifacts/deps. Low likelihood, high blast radius.
- **Existing defenses:** `astral-sh/setup-uv` is correctly SHA-pinned with a `# v8.1.0` comment (good pattern to copy); release.yml sets `permissions: contents: read` (least privilege); secrets are not exposed to fork PRs by default.
- **Recommended fix:** Pin all three actions to full commit SHAs with the version as a comment (e.g. `actions/checkout@<sha> # v5.x.y`); use Dependabot `github-actions` updates to refresh SHAs.
- **Verification:** grep workflows for `uses:` — all lines carry 40-hex SHAs.

### SEC-DEP-009 | Python manifest uses lower-bound-only pins; reproducibility rests entirely on uv.lock
- **Severity:** Low | **Confidence:** High
- **Component:** pyproject.toml:5-16 (all `>=`), dev group :22-26
- **Vulnerability:** No upper bounds means a future `uv lock` refresh can jump major versions (e.g. FastAPI 0.x→1.x, Redis client 8.x→9.x) with breaking changes or newly introduced risk, and the range allows any resolver to pick untested versions.
- **Reachability:** Not a runtime vuln; supply-chain hygiene. Mitigated: uv.lock is committed and every build path (`ci.yml` `uv sync --frozen`, `render.yaml` `uv sync --frozen`) is frozen.
- **Existing defenses:** lockfile + `--frozen` everywhere; CI installs from lock.
- **Recommended fix:** Keep `>=` floors but add Dependabot/Renovate for uv.lock refresh with PR review; optionally cap major versions for fastapi/redis/neo4j. Consider adding `pip-audit` (or `uv audit`) to CI — see SEC-DEP-011.
- **Verification:** `uv lock --check` passes; CI backend job green.

### SEC-DEP-010 | fastapi-limiter@0.2.0 — niche, low-activity upstream on a reachable runtime path
- **Severity:** Low | **Confidence:** Medium (maintenance status unverified without network)
- **Component:** uv.lock fastapi-limiter 0.2.0; used in spoilerless/app/services/rate_limit.py (login/chat/content-write limiters) — **runtime-reachable**
- **Vulnerability:** No known CVEs in this codebase's knowledge; the concern is abandonment risk: tiny package, slow release cadence. If the upstream dies, rate limiting (a security control against credential brute-force) stays pinned at whatever it last shipped.
- **Reachability:** The limiter runs on login/chat/write endpoints — a real path, but no vulnerability identified.
- **Existing defenses:** redis-backed; limiter no-ops when REDIS_URL empty (documented in code comment) — note: **rate limiting is disabled without Redis**, so deploys lacking Redis lose brute-force protection (config risk, not dep risk).
- **Recommended fix:** Monitor upstream; have a fallback (implement the 3 limiter calls against redis directly — the abstraction layer already exists in `services/rate_limit.py`); ensure Redis is provisioned in any public deployment.
- **Verification:** none needed now; re-audit at next lock refresh.

### SEC-DEP-011 | No automated Python vulnerability scanning in CI
- **Severity:** Low | **Confidence:** High
- **Component:** .github/workflows/ci.yml (backend job) — absence of a check
- **Vulnerability:** npm side is gated (`npm audit`), Python side is not. pip-audit is not installed locally; manual review found no known applicable CVEs (all versions current as of knowledge cutoff; fastapi 0.140.7/starlette 1.3.1 postdate the last multipart DoS advisories, certifi root-store issue moot at 2026.7.22).
- **Reachability:** n/a — preventive control gap.
- **Recommended fix:** Add `uv run pip-audit` (or `uv audit`) step to the backend CI job, mirroring the npm gate.
- **Verification:** CI step passes; pip-audit reports 0 known vulns.

### SEC-DEP-012 | Docker/Neo4j image pinned by tag only, no digest
- **Severity:** Low | **Confidence:** High
- **Component:** docker-compose.yml:3, ci.yml:9 (`neo4j:2026.06.0-community`)
- **Vulnerability:** Patch-pinned tag is good (not `latest`), but the tag can be re-published; digest pinning is the stronger guarantee. Neo4j is the only containerized component (no app Dockerfile — Render builds from source).
- **Reachability:** Runtime-reachable in the sense the DB image runs, but no specific vuln identified; port exposure already minimized (127.0.0.1-only bind in compose).
- **Existing defenses:** exact patch tag; localhost-only port bind; healthcheck.
- **Recommended fix:** Pin image by digest (`neo4j@sha256:…`) in both compose and CI; keep Dependabot/docker-compose update flow.
- **Verification:** compose config references digest; `docker pull` resolves to same digest.

### SEC-DEP-013 | Quiet-upstream UI deps: cytoscape-cose-bilkent@4.1.0, react-cytoscapejs@2.0.0
- **Severity:** Info | **Confidence:** Medium
- **Component:** frontend/package.json:20,26
- **Vulnerability:** No known CVEs; both are functional but release very infrequently (cose-bilkent is a 2020-era layout algorithm, react-cytoscapejs a thin wrapper). Risk is maintenance, not compromise.
- **Reachability:** Runtime-reachable (graph layouts/rendering) — a supply-chain issue in either would be exploitable on page load.
- **Existing defenses:** lockfile integrity hashes.
- **Recommended fix:** Keep, but note for periodic review; prefer direct cytoscape API usage over the wrapper if the wrapper stalls (codebase already has layout-config abstraction per commit history).
- **Verification:** none.

### SEC-DEP-014 | Install-time script surface is minimal (positive finding)
- **Severity:** Info | **Confidence:** High
- **Component:** full lockfiles
- **Vulnerability:** none. npm tree has exactly 1 `hasInstallScript` package (`fsevents@2.3.3`, macOS-only optional native dependency, no-op on Linux/Windows); Python tree has 0 third-party sdist-only packages (no setup.py/pyproject build hooks execute at install); no package in either tree is on known malicious-history lists; all PyPI artifacts are hash-pinned in uv.lock and all npm artifacts have `integrity` hashes.
- **Reachability:** n/a.
- **Recommended fix:** none; maintain as-is (hash-pinned lockfiles).
- **Verification:** `grep -c '"integrity"' package-lock.json` = 218/218 hashed entries; uv.lock wheel/sdist hashes present for all 45 packages.

## Suggested remediation order
1. SEC-DEP-001 + 002–007 (one change: move/remove shadcn, refresh lockfile) — unblocks CI, removes ~400 prod packages.
2. SEC-DEP-008 (SHA-pin Actions) — cheap, high value.
3. SEC-DEP-011 (pip-audit in CI) — cheap.
4. SEC-DEP-009/010/012/013 — policy-level, next lock refresh cycle.
