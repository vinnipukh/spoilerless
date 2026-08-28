<!-- generated-by: gsd-doc-writer -->
# Getting Started

Run the Spoilerless Dexter prototype locally with Neo4j, the FastAPI backend, and the React frontend.

## Prerequisites

Install the following before cloning the repository:

| Tool | Version | Purpose |
|---|---:|---|
| Git | Current supported release | Clone the repository |
| Docker with Docker Compose | Compose v2 (`docker compose`) | Run the Neo4j service |
| Python | `>=3.13` | Run the backend; declared by `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Current supported release | Install and run Python dependencies |
| Node.js | `^22.22.2` or `^24.15.0` or `>=26.0.0` | Run Vite 8 and the frontend toolchain |
| npm | Bundled with a compatible Node.js release | Install and run frontend dependencies |

The Node.js constraint accounts for the full installed frontend toolchain: the committed lockfile's `jsdom` 30.0.1 requires `^22.22.2 || ^24.15.0 || >=26.0.0`, which is stricter than Vite 8.1 and ESLint 10.6.

Verify the tools:

```bash
git --version
docker --version
docker compose version
uv --version
node --version
npm --version
```

## Installation

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/vinnipukh/spoilerless.git
   cd spoilerless
   ```

2. Create the local configuration file from the committed template. The frontend reads its `VITE_*`
   variables from the **root `.env`** (via `envDir: '..'` in `frontend/vite.config.ts` — there is
   no `frontend/.env.local` file):

   ```bash
   cp .env.example .env
   ```

3. Edit the root `.env`:

   - Set `NEO4J_PASSWORD=hdgraf-local-password` so the Compose container, the backend, and the test
     suite all use one database. `scripts/env-local.sh` (used by the [First Run](#first-run) flow and by
     the pytest suite) exports `hdgraf-local-password`, and `docker-compose.yml` interpolates
     `${NEO4J_PASSWORD:-change-me}` — a container created with the `change-me` fallback rejects every
     test connection. If you deliberately choose a different password, keep it identical in `.env`, in
     Compose, and in any shell that sources `scripts/env-local.sh`; `NEO4J_AUTH` is fixed when the
     container is first created, so change it before the first `docker compose up`.
   - Keep the local Neo4j URI on Bolt port `7687` and the database name `neo4j` unless you intentionally changed Compose.
   - Set `GOOGLE_CLIENT_ID` to a Google OAuth 2.0 Web Client ID if you want to sign in.
   - Set `ADMIN_EMAILS` to your own Google account email (comma-separated for more than one) to grant yourself
     the `admin` role at login. Admin is required to approve/reject/edit candidate claims, commit AI-proposed
     change sets, and view or edit the server-managed LLM settings API; role is re-derived from `ADMIN_EMAILS` on every login.
   - Optionally set `REDIS_URL` to an Upstash-style `rediss://` connection string to enable Redis-backed
     login/chat/content rate limiting and the `GET /api/series/{series_id}/graph` response cache — see the
     [configuration reference](./CONFIGURATION.md#rate-limiting--redis-cache). `docker-compose.yml` does not
     provision a local Redis container; leaving `REDIS_URL` empty is the default and both features degrade
     to a no-op rather than blocking startup or requests.

4. Set the frontend variables in the same root `.env`:

   - Set `VITE_GOOGLE_CLIENT_ID` to the same client ID used by the backend. The backend refuses to start
     when both `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` are set to different values, so keep them identical.
   - Remove or blank `VITE_API_BASE_URL` for local development. Frontend request paths already begin with `/api`, and Vite proxies those relative paths to the backend. The committed template's `VITE_API_BASE_URL=/api` would produce incorrect `/api/api/...` URLs. For a separately hosted backend, use only its origin, such as `https://api.example.com`.

   The application can start without a Google client ID. The login page reports that Google Sign-In is not configured, but **Continue as visitor** still opens the read-only graph. Do not commit the root `.env`, and do not place secrets in `VITE_*` variables.

   <!-- VERIFY: Creating a Google OAuth 2.0 Web Client ID and registering http://localhost:5173 as an authorized JavaScript origin are external Google Cloud Console steps. -->

5. Install the Python and frontend dependencies:

   ```bash
   uv sync
   cd frontend
   npm install
   cd ..
   ```

   `uv` uses `pyproject.toml` and `uv.lock`; npm uses `frontend/package.json` and `frontend/package-lock.json`.
   If your npm is configured with a global `omit=dev` (`npm config get omit` prints `dev`), a plain
   `npm install` skips devDependencies such as Vitest — use `npm install --include=dev` instead (see
   [Common Setup Issues](#common-setup-issues)).

## First Run

Run these commands from the repository root. First, clear any stray `PYTHONPATH` and load the
local-development environment so the backend and the seed command target the local Docker Neo4j:

```bash
unset PYTHONPATH
source scripts/env-local.sh
```

`scripts/env-local.sh` exports `NEO4J_URI=neo4j://localhost:7687`, username `neo4j`, password
`hdgraf-local-password`, and database `neo4j`. Shell variables outrank the root `.env`, so this overrides
`.env` for the current shell. Because `docker-compose.yml` interpolates `${NEO4J_PASSWORD:-change-me}`, source
the script **before** starting Compose so the container is created with the same password the backend will
use. If you skip the script and rely on `.env` alone, keep `NEO4J_PASSWORD` identical in `.env` and Compose.

Start Neo4j and wait for its committed health check before seeding:

```bash
docker compose up -d --wait neo4j
uv run python -m spoilerless.app.graph.setup
```

The setup module creates constraints and indexes, loads the Dexter seed data, and runs a visibility-schema integrity check. Then keep the backend running in one terminal:

```bash
uv run uvicorn spoilerless.app.main:app --reload
```

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev
```

The backend listens on `http://localhost:8000` (Swagger UI at `/docs`) and the Vite frontend listens on `http://localhost:5173`.

### Confirm the Application Works

1. Open `http://localhost:5173`.
2. Sign in with Google for persisted progress, later episode boundaries, chat, sharing, and write features, or choose **Continue as visitor** for read-only browsing at the backend-enforced anonymous order-1 boundary.
3. Select the seeded Dexter series and, when signed in, an episode boundary.
4. Confirm that the graph loads only content visible through the selected episode.

## Demo Walkthrough

The seeded identifiers are `series_dexter` and `dexter_s01e01` through `dexter_s01e03`. Sign in before following the full walkthrough: visitor mode hides chat and canvas write controls, keeps progress local to the browser tab, and backend graph reads remain fixed at anonymous order 1. The detail inspector hides the Notes and History tabs and note/relationship write affordances from visitors via `readOnly`, and the backend also rejects unauthenticated writes.

1. Select **Dexter** and set progress to **S01E01**. The initial graph contains only episode-1-visible data.
2. Select a character or claim-backed relationship. The left inspector shows graph details, claims, evidence/source metadata, notes, and revision history where applicable. The Cytoscape-based canvas (v1.3 visualization) offers layout switching, a legend, a filter panel, node search, and a path finder from the graph toolbar.
3. Advance to **S01E02**. Confirm the spoiler warning, then observe the newly unlocked nodes and relationships. Moving backward to an already-watched episode applies immediately without confirmation and contracts the visible graph while preserving the highest watched episode.
4. Add a note or user-created graph item from the available inspector/canvas controls. User content remains visually distinguishable and participates in revision/refresh flows.
5. Open **Settings** with the top-bar gear to configure the optional browser-held LLM provider, model, base URL, and API key — Google Gemini is the default provider (key plus optional model; the official Gemini REST endpoint is used when the base URL is blank), with OpenAI-compatible endpoints selectable; vLLM and Ollama are scaffolding options. Saving writes only to this browser's `localStorage`; chat sends non-blank BYOK values in `X-LLM-Api-Key`, `X-LLM-Provider`, `X-LLM-Base-URL`, and `X-LLM-Model` request headers. This frontend page does not call the admin-only `/api/settings/llm` endpoints — that separate server-managed configuration (stored in Neo4j as `:AppSetting {key: 'llm'}`, API key write-only and returned masked to its last four characters) also holds the assistant language and is edited via the API or Swagger UI.
6. If signed in, open chat and ask about a relationship visible at the current progress. Chat is hidden in visitor mode. With no browser BYOK key, the backend falls back to its Neo4j-stored/admin-managed configuration and then `LLM_*` environment values; if none is effectively enabled, chat reports a disabled/provider error. Retrieval remains bounded by persisted watch progress.

Candidate extraction review is currently an API workflow rather than a dedicated frontend screen. Use Swagger UI at `http://localhost:8000/docs` to inspect the ingest, list/get, edit, approve, and reject routes under `/api/series/{series_id}/candidates`. Ingest requires any authenticated user; list/get are anonymous reads that require a valid `visible_until_order` boundary; edit, approve, and reject require the `admin` role. Candidate ingestion accepts structured, evidence-bearing records; it is not an automatic subtitle/script ingestion pipeline.

## Common Setup Issues

### `spoilerless-setup` is not found

`uv sync` currently warns that project entry points are skipped because the repository has no build system or `tool.uv.package = true`. Use the verified module form instead:

```bash
uv run python -m spoilerless.app.graph.setup
```

### Python or Node.js is rejected

- The backend requires Python `>=3.13`. Run `uv run python --version`; uv can provision a compatible interpreter when one is available for the platform.
- The committed frontend dependency graph requires Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0` because `jsdom` 30.0.1 is stricter than Vite itself. Upgrade Node.js if `npm install` reports an `EBADENGINE` warning or Vite refuses to start.

### `npm install` skipped devDependencies (Vitest missing)

If `npm config get omit` prints `dev`, your global npm configuration excludes devDependencies from installs, so `vitest` and other test tooling are missing. Re-run with:

```bash
cd frontend
npm install --include=dev
```

### Neo4j is unavailable or the seed command cannot connect

Check the service and logs:

```bash
docker compose ps neo4j
docker compose logs neo4j
```

Confirm Docker is running, ports `7474` and `7687` are free, and the credentials used by the seed/backend
match `docker-compose.yml` — either the `.env` value or `scripts/env-local.sh`'s `hdgraf-local-password`,
whichever the container was created with. `NEO4J_AUTH` is fixed when the container is first created:
recreating with `docker compose up -d` after changing the password does not update an existing database, and
a container created with a different password than the one your commands export will reject connections.
Wait for the Compose health check before retrying the seed command.

If the seed integrity audit fails against an older local graph, do not ignore the error: inspect or replace the stale local Neo4j data before reseeding. Removing the bind-mounted `neo4j_data` directory deletes the local graph, so back it up first if it contains work you need.

### The login page says Google Sign-In is not configured

To enable sign-in, set the same OAuth Web Client ID in both `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` in the **root `.env`** (the frontend reads `VITE_*` from the root `.env` via `envDir: '..'`), then restart both dev servers. The backend also refuses to start if the two IDs are set to different values. The local frontend origin must also be registered with the OAuth provider. Do not add a Google client secret; this application verifies browser-issued ID tokens using the client ID. Alternatively, choose **Continue as visitor** for read-only browsing.

### A local port is already in use

The default ports are `5173` (Vite), `8000` (Uvicorn), `7474` (Neo4j HTTP), and `7687` (Neo4j Bolt). Stop the conflicting process or deliberately update every corresponding application, proxy, Compose, and environment setting; changing only one side breaks connectivity.

### The frontend is blank or `/api` requests fail

Open browser developer tools and inspect the Console and Network tabs. Check `curl http://localhost:8000/health`, then confirm `frontend/vite.config.ts` still proxies `/api` to `http://127.0.0.1:8000`. A 503 points to Neo4j/backend health; a proxy error usually means the backend is not listening on port `8000`.

### Changing `.env` does not change chat behavior

First check the in-app Settings page. A non-blank browser BYOK key takes complete precedence for that chat request and is stored in `localStorage`, not Neo4j. Clear or update those browser values to exercise backend configuration. Without BYOK headers, a value persisted in `:AppSetting {key: 'llm'}` wins over the matching `LLM_*` environment fallback, including the `enabled` switch; updating only `.env` does not replace an already stored server value.

## Next Steps

- Read the [architecture guide](./ARCHITECTURE.md) for the system layers and spoiler-safety model.
- Read the [configuration reference](./CONFIGURATION.md) before changing authentication, database, session, or LLM settings.
- Use the [development guide](./DEVELOPMENT.md) for contributor workflows and project conventions.
- Use the [testing guide](./TESTING.md) to run the pytest and Vitest suites.
- Explore the HTTP surface in the [API reference](./API.md) or the local Swagger UI at `http://localhost:8000/docs`.

Run the suites yourself:

```bash
unset PYTHONPATH && source scripts/env-local.sh && uv run pytest spoilerless/tests
```

```bash
cd frontend && NODE_ENV=test CI=1 npx vitest run
```

The pytest suite targets the live local Docker Neo4j; the Vitest suite runs in jsdom.
