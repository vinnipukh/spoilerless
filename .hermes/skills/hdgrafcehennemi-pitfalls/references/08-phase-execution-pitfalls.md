# Phase 08 execution pitfalls (08-02 BYOK session, 2026-08-04)

## FastAPI sanitized error envelope — RequestValidationError details never reach the client

`install_error_handlers` (backend/app/core/errors.py) collapses EVERY
RequestValidationError into the generic envelope
`{"detail":{"code":"invalid_request","message":"Request validation failed."}}`
— field names, locs, and validator messages are stripped by design. Two consequences:

1. **Tests asserting a field name in a 422 body can never pass via
   RequestValidationError.** Observed 08-02: the BYOK malformed-base_url test
   asserted `"base_url" in response.text.lower()` — the sanitized handler
   returned the generic message, so the test failed with
   `assert 'base_url' in '{"detail":{"code":"invalid_request","message":"request validation failed."}}'`.
   Fix that shipped: raise `http_error(422, "invalid_request", <validator msg>)`
   from `backend.app.core.errors` — HTTPException detail `{"code","message"}`
   passes through the envelope verbatim, so the actionable message ("base_url
   scheme must be one of ...") reaches the client while the shape stays stable.
   Swap the import accordingly (drop `fastapi.exceptions.RequestValidationError`
   unless used elsewhere in the file).
2. **The stored-settings 422 path behaves the same**: PUT /api/settings/llm
   body-validation errors also yield the generic envelope. "Fails the same way
   as stored settings" means generic envelope, not field-named detail.

When writing 422 assertions, check whether the test app installs
`install_error_handlers`; with the sanitized handler, assert on the envelope's
`message` content or the status code — never FastAPI's default
`{"detail":[{loc,msg}]}` shape.

## Patch-tool fuzzy-match misfire on adjacent import lines

`patch` mode='replace' fuzzy matching can replace a NEARBY similar line when
the old_string prefix collides. Observed 08-02: targeting
`from fastapi.exceptions import RequestValidationError`, the tool replaced
`from fastapi import Depends, Header` on the line above (both start
`from fastapi `), silently dropping `Depends` and leaving a duplicate
`from fastapi import Header`; lint passed and no error surfaced. Always read
the returned diff before continuing — an import-line replacement that removes
a name or adds a duplicate import is the tell-tale; re-read the import block
and fix in one follow-up patch.

## AuraDB Free app credential — Console "Member" path is DEAD (superseded 08-04, verified live)

**CORRECTION:** the earlier "Member-role user via Console" guidance below was
verified WRONG during 08-01 provisioning (2026-08-04) and superseded:

- Console "Member"/"Viewer"/"Administrator" roles are **human console access**
  (Project Settings → Users → invite) — NOT database credentials. Aura docs:
  "User management within the Aura console does not replace built-in roles or
  fine-grained RBAC at the database level."
- **`CREATE USER` via the Query browser is denied on AuraDB Free** — even with
  the credentials-file instance admin. Console tool-auth connects as a UUID
  user with the immutable DBMS role `console_admin_free_<dbid>` (lacks user
  management on Free) → `Neo.ClientError.Security.Forbidden: Permission has not
  been granted for CREATE USER`; retrying as the instance admin →
  `42NFF: Syntax error or access rule violation`. Docs "Option 1" (CREATE USER)
  applies to paid tiers only.
- **Working setup (verified): single credential — the instance admin from the
  downloaded credentials file** (`NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io`,
  `NEO4J_USERNAME=<dbid>`, `NEO4J_DATABASE=<dbid>`, password shown once at
  download). D-16 least-privilege becomes a documented Free-tier ceiling.
  Diagnostic when a command is forbidden: `SHOW CURRENT USER;` — a UUID +
  `console_admin_free_*` role means console tool-auth, not the instance credential.
- Custom `CREATE ROLE`/`GRANT` unsupported on Free (BC/VDC/Enterprise only);
  `seed.py`'s `CREATE CONSTRAINT`/`CREATE INDEX` therefore run as the admin
  credential during migration/reseed.

Values a plan executor needs back:
- NEO4J_URI: Aura Console -> Instance -> Connect -> `neo4j+s://<dbid>.databases.neo4j.io`
- NEO4J_USERNAME / NEO4J_PASSWORD: the Member-role user
- REDIS_URL: Upstash console -> Redis database -> Details -> `rediss://` TLS URL
- Render/Vercel: repo-linked project confirmation (Vercel Root Directory = frontend/)

## 08-05/06 session — Conftest setdefault clobbers .env, dual-.env trap, Redis probe pattern

### `os.environ.setdefault` in conftest kills `.env` file (pydantic-settings priority: env vars > .env)

The 08-05 executor's `backend/tests/conftest.py` added:

```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "hdgraf-local-password")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```

Pydantic-settings (`SettingsConfigDict(env_file=".env")`) reads **shell environment
variables before `.env` file values**.  `setdefault` fires when the env var isn't
already exported in the shell — which is the default state.  Result: every test
connects to localhost even when `.env` points at AuraDB.  The 42/42 test_auth
pass afterward is misleading — it passes because the test fixture mocks the
Neo4jDatabase, not because the config resolves correctly.

**Fix**: remove the four `setdefault` lines from conftest entirely.  For local
docker testing, use `source scripts/env-local.sh` (exports the same four vars)
before running pytest — never edit the file.

### Dual `.env` files (root `.env` and `backend/.env`) — only the root is read

`config.py::SettingsConfigDict` sets `env_file=".env"` relative to the process
CWD.  When pytest is invoked from the repo root, pydantic-settings reads the root
`.env`; `backend/.env` is **never read** and becomes a stale zombie.  Delete
`backend/.env` — the root `.env` is the single source of truth.  Sibling agents
that need a local docker DB should `source scripts/env-local.sh`, never edit
either file.

### Redis connectivity — probe via `POST /notes`, NOT `POST /auth/google`

To verify Redis is wired on the live API:
- **BAD**: `POST /api/auth/google` — hits the CSRF `verify_origin` gate (403 with
  no Origin header), then a Google network call (GoogleTransportError → 503 with
  a fake credential).  The 403/503 noise hides whether the rate-limiter
  dependency even ran.
- **GOOD**: `POST /api/series/{id}/notes` — rate-limited per-IP via
  `content_write_rate_limiter`, **no auth dependency**, no external network call.
  An empty `{}` body → 422 `invalid_request` proves the limiter dependency ran
  and reached request validation.  A connection-refused/hang proves Redis is down.

### Upstash URL scheme: `redis://` vs `rediss://`

Upstash console shows `redis-cli --tls -u redis://default:...@...:6379` — the
`redis://` scheme with `--tls` flag is redis-cli's convention.  Python redis-py
(`Redis.from_url()`) uses `rediss://` to auto-negotiate TLS.  On Render, set
`REDIS_URL = rediss://default:<password>@<host>:6379` — never `redis://`.

### Executor 429/503 death pattern — skip-baseline continuation strategy

Five executors died this session before completing their first task — all during
baseline reads (reading the PLAN.md frontmatter, CONTEXT, RESEARCH, source
files).  Continuation executors given explicit "skip the baseline reads, here are
the files + exact changes" instructions succeeded.  Strategy when re-dispatching
after a death: pass the plan's `<files>` list and `<action>` summary directly
in the context so the continuation agent can go straight to implementation
without re-reading the whole plan.
