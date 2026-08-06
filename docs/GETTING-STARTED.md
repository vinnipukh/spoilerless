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

The Node.js constraint accounts for the full installed frontend toolchain: the committed lockfile's `jsdom` 30.0.1 requires `^22.22.2 || ^24.15.0 || >=26.0.0`, which is stricter than Vite 8.1.5 and ESLint 10.8.0.

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
   git clone https://github.com/vinnipukh/hdgrafcehennemi.git
   cd hdgrafcehennemi
   ```

2. Create the local configuration file from the committed template. The frontend reads its `VITE_*`
   variables from the **root `.env`** (via `envDir: '..'` in `frontend/vite.config.ts` — there is
   no `frontend/.env.local` file):

   ```bash
   cp .env.example .env
   ```

3. Edit the root `.env`:

   - Make `NEO4J_PASSWORD` match the password in `docker-compose.yml`'s `NEO4J_AUTH` setting.
   - Keep the local Neo4j URI on Bolt port `7687` and the database name `neo4j` unless you intentionally changed Compose.
   - Set `GOOGLE_CLIENT_ID` to a Google OAuth 2.0 Web Client ID if you want to sign in.
   - Set `ADMIN_EMAILS` to your own Google account email (comma-separated for more than one) to grant yourself
     the `admin` role at login. Admin is required to approve/reject/edit candidate claims, commit AI-proposed
     change sets, and view or edit the LLM settings; role is re-derived from `ADMIN_EMAILS` on every login.
   - Optionally set `REDIS_URL` to an Upstash-style `rediss://` connection string to enable Redis-backed
     login/chat/content rate limiting and the `GET /api/series/{series_id}/graph` response cache — see the
     [configuration reference](./CONFIGURATION.md#rate-limiting--redis-cache). `docker-compose.yml` does not
     provision a local Redis container; leaving `REDIS_URL` empty is the default and both features degrade
     to a no-op rather than blocking startup or requests.

4. Set the frontend variable in the same root `.env`:

   - Set `VITE_GOOGLE_CLIENT_ID` to the same client ID used by the backend.
   - Keep `VITE_API_BASE_URL` commented out (the dev proxy handles `/api`).

   The application can start without a Google client ID, but the login page reports that Google Sign-In is not configured. Do not commit the root `.env`, and do not place secrets in `VITE_*` variables.

   <!-- VERIFY: Creating a Google OAuth 2.0 Web Client ID and registering http://localhost:5173 as an authorized JavaScript origin are external Google Cloud Console steps. -->

5. Install the Python and frontend dependencies:

   ```bash
   uv sync
   cd frontend
   npm install
   cd ..
   ```

`uv` uses `pyproject.toml` and `uv.lock`; npm uses `frontend/package.json` and `frontend/package-lock.json`.

## First Run

To start the database, seed the graph, and launch both the backend and frontend servers at once, run the following compound command in a bash-compatible terminal from the repository root:

```bash
docker compose up -d && \
  sleep 5 && \
  uv run python -m spoilerless.app.graph.setup && \
  uv run uvicorn spoilerless.app.main:app --reload & \
  (cd frontend && npm run dev)
```

Wait until Neo4j is healthy before the seed script runs (the 5-second sleep helps ensure it). The backend listens on `http://localhost:8000` (Swagger UI at `/docs`) and the Vite frontend listens on `http://localhost:5173`.

> **Note:** If you prefer not to use background jobs (`&`), you can run `docker compose up -d` and the seed script, then start the backend (`uv run uvicorn spoilerless.app.main:app --reload`) and frontend (`cd frontend && npm run dev`) in separate terminal windows.

### 5. Confirm the application works

1. Open `http://localhost:5173`.
2. Sign in with Google; authentication is required to reach the series, episode, and graph controls.
3. Select the seeded Dexter series and an episode boundary.
4. Confirm that the graph loads only content visible through the selected episode.

## Demo Walkthrough

The seeded identifiers are `series_dexter` and `dexter_s01e01` through `dexter_s01e03`.

1. Select **Dexter** and set progress to **S01E01**. The initial graph contains only episode-1-visible data.
2. Select a character or claim-backed relationship. The left inspector shows graph details, claims, evidence/source metadata, notes, and revision history where applicable.
3. Advance to **S01E02**. Confirm the spoiler warning, then observe the newly unlocked nodes and relationships. Moving backward also asks for confirmation and contracts the visible graph.
4. Add a note or user-created graph item from the available inspector/canvas controls. User content remains visually distinguishable and participates in revision/refresh flows.
5. Open **Settings** with the top-bar gear to configure the optional LLM provider, model, API key, enabled switch, and English/Turkish assistant language. Settings saved here are stored in Neo4j and take precedence over matching `LLM_*` environment values. This page requires the signed-in account to carry the `admin` role (see `ADMIN_EMAILS` in [Installation](#installation)); a non-admin account gets `403 FORBIDDEN`.
6. Open chat and ask about a relationship visible at the current progress. Chat is optional and reports a disabled/provider error when no effective provider is enabled; it must not retrieve beyond persisted watch progress.

Candidate extraction review is currently an API workflow rather than a dedicated frontend screen. Use Swagger UI at `http://localhost:8000/docs` to inspect the ingest, list/get, edit, approve, and reject routes under `/api/series/{series_id}/candidates`. Ingest and list/get carry no authentication requirement; edit, approve, and reject require the `admin` role, same as Settings above. Candidate ingestion accepts structured, evidence-bearing records; it is not an automatic subtitle/script ingestion pipeline.

## Common Setup Issues

### `spoilerless-setup` is not found

`uv sync` currently warns that project entry points are skipped because the repository has no build system or `tool.uv.package = true`. Use the verified module form instead:

```bash
uv run --project spoilerless python -m spoilerless.app.graph.setup
```

### Python or Node.js is rejected

- The backend requires Python `>=3.13`. Run `uv run python --version`; uv can provision a compatible interpreter when one is available for the platform.
- Vite 8 requires Node.js `20.19.x` or `>=22.12.0`. Upgrade Node.js if `npm install` reports an `EBADENGINE` warning or Vite refuses to start.

### Neo4j is unavailable or the seed command cannot connect

Check the service and logs:

```bash
docker compose ps neo4j
docker compose logs neo4j
```

Confirm Docker is running, ports `7474` and `7687` are free, and the root `.env` credentials match `docker-compose.yml`. Wait for the Compose health check before retrying the seed command.

If the seed integrity audit fails against an older local graph, do not ignore the error: inspect or replace the stale local Neo4j data before reseeding. Removing the bind-mounted `neo4j_data` directory deletes the local graph, so back it up first if it contains work you need.

### The login page says Google Sign-In is not configured

Set the same OAuth Web Client ID in both `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` in the **root `.env`** (the frontend reads `VITE_*` from the root `.env` via `envDir: '..'`), then restart both dev servers. The local frontend origin must also be registered with the OAuth provider. Do not add a Google client secret; this application verifies browser-issued ID tokens using the client ID.

### A local port is already in use

The default ports are `5173` (Vite), `8000` (Uvicorn), `7474` (Neo4j HTTP), and `7687` (Neo4j Bolt). Stop the conflicting process or deliberately update every corresponding application, proxy, Compose, and environment setting; changing only one side breaks connectivity.

### The frontend is blank or `/api` requests fail

Open browser developer tools and inspect the Console and Network tabs. Check `curl http://localhost:8000/health`, then confirm `frontend/vite.config.ts` still proxies `/api` to `http://127.0.0.1:8000`. A 503 points to Neo4j/backend health; a proxy error usually means the backend is not listening on port `8000`.

### Changing `.env` does not change chat behavior

Open the in-app Settings page. A value persisted in `:AppSetting {key: 'llm'}` wins over the matching environment fallback, including the `enabled` switch. Updating only `.env` does not replace an already stored value.

## Next Steps

- Read the [architecture guide](./ARCHITECTURE.md) for the system layers and spoiler-safety model.
- Read the [configuration reference](./CONFIGURATION.md) before changing authentication, database, session, or LLM settings.
- Use the [development guide](./DEVELOPMENT.md) for contributor workflows and project conventions.
- Use the [testing guide](./TESTING.md) to run the pytest and Vitest suites.
- Explore the HTTP surface in the [API reference](./API.md) or the local Swagger UI at `http://localhost:8000/docs`.
