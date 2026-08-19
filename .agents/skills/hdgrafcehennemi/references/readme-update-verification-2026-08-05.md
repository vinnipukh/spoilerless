# README doc-update verification — 2026-08-05 (gsd-doc-writer, update mode)

Verified a partially-updated README against live code. Durable facts + the method to reuse.

## Verified facts (do NOT re-derive)

- **GitHub remote is `vinnipukh/hdgrafcehennemi`** — `vinnipukh/spoilerless` does NOT exist
  (`git ls-remote https://github.com/vinnipukh/spoilerless.git` → "Repository not found";
  `vinnipukh/hdgrafcehennemi` resolves, main @ `288743e`). The REBRAND-01 "GitHub remote
  vinnipukh/spoilerless" claim was never executed. README clone URLs + `cd <dir>` after clone
  must use `hdgrafcehennemi`.
- **docker-compose.yml declares `container_name: spoilerless-neo4j`**, auth
  `neo4j/${NEO4J_PASSWORD:-change-me}` — the compose FILE is the doc source for the container.
  The RUNNING container is `hdgrafcehennemi-neo4j` (pre-rename leftover, never recreated) with
  NEO4J_AUTH `hdgraf-local-password` (per `scripts/env-local.sh`). env-local.sh's password must
  match the RUNNING container, NOT the Compose default.
- **Frontend Node engine claim** in README (`^22.22.2 || ^24.15.0 || >=26.0.0`) derives from
  jsdom 30.0.1's `engines` in the committed lockfile (strictest of the stack; vite 8.1.5 is
  `^20.19.0 || >=22.12.0`, vitest 4.1.10 is `^20.0.0 || ^22.0.0 || >=24.0.0`). frontend/package.json
  has NO engines field — verify engine claims from `frontend/package-lock.json`
  `packages[].engines`, never from package.json.
- README envDir flow verified: `frontend/vite.config.ts:9` `envDir: '..'`; only
  `frontend/.env.example` is tracked (no `.env.local`); root `.env` points at AuraDB
  (`neo4j+s://03a8623b.databases.neo4j.io`, `NEO4J_DATABASE=03a8623b`).
- API rows verified live: `POST /{series_id}/graph/path` (graph.py:167, `MAX_PATH_HOPS=4`,
  PathRequest max_hops ge=1 le=4) and `GET /{series_id}/export` (graph.py:199, D-11,
  `target_id` optional, default `visible_until_order=1`).
- `spoilerless-setup` console script declared (pyproject.toml:18-19) but NOT installed (no
  build-system) — README note is correct; seeding runs via `uv run --project spoilerless python
  -m spoilerless.app.graph.setup`.

## Verification method (reuse for any doc-update pass)

1. **Remote URL proof:** `git remote -v` only shows local config, not reachability. Run
   `git ls-remote --heads <url>` — a renamed repo redirects, so "Repository not found" means the
   URL truly does not exist.
2. **Container claims:** read `docker-compose.yml` directly for container_name/NEO4J_AUTH;
   `docker ps` shows only the running (possibly stale, pre-rename) container.
3. **Version/engine claims:** `python -c` json dump of lockfile `packages[].engines`;
   cross-check package.json devDependencies versions.
4. **Route claims:** rg the router file for `@router.(get|post)` + handler; confirm caps
   (`MAX_PATH_HOPS`, etc.) at their definition site.
5. **Prior partial edits:** `git diff README.md` first to see exactly what an earlier pass
   changed before re-verifying; uncommitted README edits may themselves be wrong.

## 2026-08-10 refresh deltas

The README was refreshed again from the live tree. Re-check these points on future passes:

- **Project tree shape:** the import root is `spoilerless/app/`, not
  `spoilerless/spoilerless/app/`. Render the README tree from repository root (`.`), with
  `spoilerless/` and `frontend/` as siblings; otherwise an apparently tidy tree can encode
  a nonexistent nested package.
- **Auth/read-only behavior:** `frontend/src/components/auth/LoginPage.tsx` exposes
  **Continue as visitor** for read-only browsing. Google OAuth is required for authenticated
  sessions and write/persisted features, not for opening the graph as a visitor.
- **Share API:** `spoilerless/app/api/share.py` is registered in `main.py` and owns
  `/api/share` create/list/revoke operations plus unauthenticated token-gated graph reads.
  Keep it in both Features and API Overview.
- **User-content auth:** the old README statement that note/custom-content routes had no
  session dependency was stale. Writes are authenticated; the README should defer the exact
  per-operation/admin matrix to `docs/API.md` rather than overstate every route inline.
- **BYOK fallback:** browser BYOK keys travel in `X-LLM-*` headers, but absent headers can
  fall back to backend `LLM_*` settings. Do not claim the backend can never hold an LLM key.
- **Declared vs templated settings:** `Settings` declares `ALLOWED_EMAILS`, `ADMIN_EMAILS`,
  and `REDIS_URL`, while root `.env.example` currently omits them. Document that distinction
  rather than implying the template contains every setting.
- **Local Neo4j password split:** fresh Compose uses `${NEO4J_PASSWORD:-change-me}`;
  `scripts/env-local.sh` hardcodes `hdgraf-local-password` for an already-created legacy
  local container. Do not tell fresh-machine users to start Compose with the default and then
  source that script—the credentials would disagree.
- **External deployment claims:** preserve `<!-- VERIFY: -->` markers and call the stack a
  "documented production target" unless current liveness is checked independently. Repo
  deployment files verify configuration, not that public endpoints are live.

## 2026-08-10 adversarial verification findings

A claim-by-claim verifier found six README failures (147 checked, 141 passed). Reuse these
checks on future README/API/setup refreshes:

- **Candidate reads are no longer boundary exceptions.** Both
  `GET /api/series/{series_id}/candidates` and
  `GET /api/series/{series_id}/candidates/{claim_id}` declare
  `visible_until_order` and call `api/candidates.py::_require_resolved_boundary`.
  Omission and a non-persisted episode order both return 422. Remove wording that the list
  accepts an optional boundary or that detail has no boundary; this stale statement appeared
  three times in one README pass.
- **The copied local env template currently double-prefixes API paths.** Both
  `frontend/src/api/client.ts` and streaming `frontend/src/api/chat.ts` prepend
  `VITE_API_BASE_URL` to call paths already beginning with `/api`. Therefore
  `.env.example`'s `VITE_API_BASE_URL=/api` produces `/api/api/...` after the documented
  `cp .env.example .env`. Local proxy value must be empty/absent; production value may be a
  full backend origin. Verify template value shape, not only the `envDir: '..'` loader.
- **Rate-limiter attribution:** application code imports and directly uses
  `pyrate_limiter` (`Limiter`, `RedisBucket`, etc.) through a custom FastAPI dependency
  wrapper. `fastapi-limiter` is still declared in `pyproject.toml`, but no application Python
  file imports `fastapi_limiter`; docs should not say the implementation is "via
  fastapi-limiter" without qualifying this distinction.
- **Artifact verification and application verification are distinct.** Validate the standard
  JSON artifact with `scripts/validate-verification-artifact.py`; if an orchestration gate
  separately requires canonical pytest evidence, use the DB-free focused file
  `spoilerless/tests/test_user_content_models.py`. In Hermes shells, inherited `PYTHONPATH`
  can outrank the project venv; diagnose `sys.path`, then run
  `unset PYTHONPATH; uv run pytest spoilerless/tests/test_user_content_models.py -q`.

Validation used on this pass: first-line GSD marker, balanced Markdown fences, all local links
and selected documented paths, stale-phrase absence, `docker compose config --quiet`,
`uvicorn --help`, frontend script inventory, remote reachability, backend import smoke, and
`git diff --check -- README.md`.
