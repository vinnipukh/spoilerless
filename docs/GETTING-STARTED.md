<!-- generated-by: gsd-doc-writer -->
# Getting Started

Run the HD Graf Cehennemi Dexter prototype locally with Neo4j, the FastAPI backend, and the React frontend.

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

2. Create local configuration files from the committed templates:

   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env.local
   ```

3. Edit the root `.env`:

   - Make `NEO4J_PASSWORD` match the password in `docker-compose.yml`'s `NEO4J_AUTH` setting.
   - Keep the local Neo4j URI on Bolt port `7687` and the database name `neo4j` unless you intentionally changed Compose.
   - Set `GOOGLE_CLIENT_ID` to a Google OAuth 2.0 Web Client ID if you want to sign in.

4. Edit `frontend/.env.local`:

   - Set `VITE_GOOGLE_CLIENT_ID` to the same client ID used by the backend.
   - Keep `VITE_API_BASE_URL=/api` as shown by the template.

   The application can start without a Google client ID, but the login page reports that Google Sign-In is not configured. Do not commit either local environment file, and do not place secrets in `VITE_*` variables.

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

Run each long-lived server in its own terminal from the repository root.

### 1. Start Neo4j

```bash
docker compose up -d
docker compose ps neo4j
```

Docker Compose defines one service named `neo4j`, using the container name `hdgrafcehennemi-neo4j`. Wait until it is healthy.

| Service | Local address | Purpose |
|---|---|---|
| Neo4j Browser | `http://localhost:7474` | Browser UI and HTTP health check |
| Neo4j Bolt | `neo4j://localhost:7687` | Backend database connection |

### 2. Seed the graph

The `pyproject.toml` declares an `hdgraf-setup` entry point, but the project currently has no build-system/package setting, so `uv sync` may skip installing that executable. The directly runnable module is:

```bash
uv run python -m backend.app.graph.setup
```

A successful run prints a `Dexter graph setup complete` summary. The seed operation is intended to create constraints and load the Dexter Season 1, Episodes 1–3 data from `data/dexter/`.

### 3. Start the backend

```bash
uv run uvicorn backend.app.main:app --reload
```

The backend listens on `http://localhost:8000` by default. Check it in another terminal:

```bash
curl http://localhost:8000/health
```

Swagger UI is available at `http://localhost:8000/docs`. The backend deliberately starts in degraded mode if Neo4j is unavailable; in that case `/health` returns HTTP 503 with the database marked unavailable.

### 4. Start the frontend

```bash
cd frontend
npm run dev
```

Vite serves the frontend at `http://localhost:5173` and proxies `/api` requests to `http://127.0.0.1:8000`.

### 5. Confirm the application works

1. Open `http://localhost:5173`.
2. Sign in with Google; authentication is required to reach the series, episode, and graph controls.
3. Select the seeded Dexter series and an episode boundary.
4. Confirm that the graph loads only content visible through the selected episode.

## Common Setup Issues

### `hdgraf-setup` is not found

`uv sync` currently warns that project entry points are skipped because the repository has no build system or `tool.uv.package = true`. Use the verified module form instead:

```bash
uv run python -m backend.app.graph.setup
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

Set the same OAuth Web Client ID in the backend's `GOOGLE_CLIENT_ID` and the frontend's `VITE_GOOGLE_CLIENT_ID`, then restart both dev servers. The local frontend origin must also be registered with the OAuth provider. Do not add a Google client secret; this application verifies browser-issued ID tokens using the client ID.

### A local port is already in use

The default ports are `5173` (Vite), `8000` (Uvicorn), `7474` (Neo4j HTTP), and `7687` (Neo4j Bolt). Stop the conflicting process or deliberately update every corresponding application, proxy, Compose, and environment setting; changing only one side breaks connectivity.

## Next Steps

- Read the [architecture guide](./ARCHITECTURE.md) for the system layers and spoiler-safety model.
- Read the [configuration reference](./CONFIGURATION.md) before changing authentication, database, session, or LLM settings.
- Use the [development guide](./DEVELOPMENT.md) for contributor workflows and project conventions.
- Use the [testing guide](./TESTING.md) to run the pytest and Vitest suites.
- Explore the HTTP surface in the [API reference](./API.md) or the local Swagger UI at `http://localhost:8000/docs`.
