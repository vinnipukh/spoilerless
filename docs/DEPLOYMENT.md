<!-- generated-by: gsd-doc-writer -->
# Deployment

HD Graf Cehennemi currently supports a local, developer-operated deployment. The repository does not define a production hosting target, application Docker images, or an automated CI/CD pipeline.

## Detected Deployment Targets

| Target | Scope | Repository configuration |
|---|---|---|
| Docker Compose | Local Neo4j Community database only | `docker-compose.yml` |
| Native Python process | Local FastAPI backend | `pyproject.toml`, `backend/requirements.txt`, `backend/app/main.py` |
| Vite development server or static build | Local frontend development or a build artifact for an operator-selected static host | `frontend/package.json`, `frontend/vite.config.ts` |

`docker-compose.yml` contains only the `neo4j` service using `neo4j:2026-community`. It exposes Neo4j HTTP on `7474` and Bolt on `7687`, persists data and logs through local bind mounts, and checks container health through `http://localhost:7474`.

There are no backend or frontend `Dockerfile` files. No Vercel, Netlify, Fly.io, Railway, Serverless Framework, Kubernetes, Helm, or other production deployment configuration is present. There is therefore **no production deployment target defined in the repository**.

<!-- VERIFY: Confirm that the `neo4j:2026-community` image tag is available in the container registry used by the deployment environment before relying on it. -->

## Local Deployment

### Prerequisites

- Docker Engine or Docker Desktop with Docker Compose.
- Python `>=3.13`, as required by `pyproject.toml`.
- [`uv`](https://docs.astral.sh/uv/) for the Python environment.
- Node.js and npm for the frontend; the repository does not pin a Node.js version.

### Start the application

1. Create the backend environment file and configure it as described in [CONFIGURATION.md](./CONFIGURATION.md):

   ```bash
   cp .env.example .env
   ```

2. Start Neo4j:

   ```bash
   docker compose up -d
   docker compose ps neo4j
   ```

3. Install the Python dependencies and initialize the graph:

   ```bash
   uv sync
   # The declared hdgraf-setup script is not installed by uv sync.
   uv run --project backend python -m backend.app.graph.setup
   ```

   The `hdgraf-setup` script resolves to `backend.app.graph.setup:main` through `pyproject.toml`.

4. Start the FastAPI backend:

   ```bash
   uv run uvicorn backend.app.main:app
   ```

5. In another terminal, install the frontend dependencies and start Vite:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   Vite proxies `/api` requests to `http://127.0.0.1:8000` during development.

6. Verify Neo4j and the backend:

   ```bash
   docker compose ps neo4j
   curl http://localhost:8000/health
   ```

   A healthy backend returns HTTP 200 with `status: "ok"` and `database: "connected"`. If Neo4j is unavailable, the backend remains running and `/health` returns HTTP 503 with `status: "degraded"`.

## Build Pipeline

No `.github/workflows` directory or other CI/CD configuration is present. **No CI/CD pipeline detected.** Builds, tests, artifact publication, and deployment are not automated by this repository.

The repository-defined manual build sequence is:

1. Resolve the locked Python environment:

   ```bash
   uv sync --frozen
   ```

   The backend has no compilation or packaging step; it runs from the repository source through Uvicorn. `backend/requirements.txt` is a uv-generated export, while `pyproject.toml` and `uv.lock` define the project environment.

2. Install the locked frontend dependencies:

   ```bash
   cd frontend
   npm ci
   ```

3. Type-check and build the frontend:

   ```bash
   npm run build
   ```

   `frontend/package.json` defines this as `tsc -b && vite build`. Vite writes the static artifact to its default `frontend/dist/` directory because no custom output directory is configured.

4. Run validation manually before deployment:

   ```bash
   # From the repository root
   uv run pytest

   # From frontend/
   npm run lint
   npm test -- --run
   ```

No container image build, image registry push, release trigger, artifact upload, or deploy command exists in the repository.

## Environment Setup

Use [CONFIGURATION.md](./CONFIGURATION.md) as the authoritative reference for all backend, frontend, Docker Compose, and runtime LLM settings. Never commit `.env` files or real credentials.

For any backend deployment, these settings have no code defaults and must be supplied:

- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

`NEO4J_DATABASE` defaults to `neo4j`. Authentication additionally needs matching `GOOGLE_CLIENT_ID` and build-time `VITE_GOOGLE_CLIENT_ID` values. An HTTPS deployment should set `SESSION_COOKIE_SECURE=true` and restrict `FRONTEND_ORIGINS` to the deployed frontend origin. LLM-backed chat remains disabled unless an effective LLM configuration enables it; see CONFIGURATION.md for environment and Neo4j-stored runtime override precedence.

The frontend's `VITE_*` values are embedded at build time. `VITE_GOOGLE_CLIENT_ID` is consumed by the login UI. `VITE_API_BASE_URL` is declared in `frontend/.env.example` but is not currently consumed by frontend source, so production `/api` routing must be provided by the selected host or reverse proxy.

No deployment-platform secret manager is configured in this repository. <!-- VERIFY: Store `NEO4J_PASSWORD`, `LLM_API_KEY`, and any other deployment secrets in the secret-management facility selected for the actual hosting platform. -->

## Rollback

There is no repository-defined production rollback command, release workflow, immutable image tag policy, or database migration rollback procedure.

For the current manual deployment model:

1. Stop the affected backend and frontend processes.
2. Check out the previously verified source revision in a clean working tree.
3. Re-run `uv sync --frozen` and `npm ci`, then rebuild the frontend with `npm run build`.
4. Restart the application processes and verify `GET /health` plus the main frontend flow.
5. If graph data changed, restore a separately created Neo4j backup that matches the prior application revision. The repository does not configure or automate Neo4j backups.

<!-- VERIFY: Adapt the rollback commands, process manager restart, artifact selection, and backup restoration steps to the actual production platform before first deployment. -->

Do not use `docker compose down -v` as a rollback command: the Compose file uses bind mounts for Neo4j data, and the repository provides no automated backup or restoration workflow.

## Monitoring

Repository-provided monitoring is limited to:

- `GET /health` in `backend/app/main.py`, which verifies Neo4j connectivity and returns HTTP 200 or 503.
- The Neo4j Compose health check, which probes `http://localhost:7474` every 10 seconds with a 5-second timeout and 10 retries.
- Neo4j logs persisted at `./neo4j_logs` by `docker-compose.yml`; container output can be viewed with `docker compose logs neo4j`.

No direct Sentry, Datadog, New Relic, or OpenTelemetry application dependency or configuration is present. The repository also defines no metrics endpoint, log aggregation, alert rules, uptime checks, monitoring dashboard, or alert webhook.

<!-- VERIFY: Select an external uptime, logging, metrics, and alerting service for production, and configure it to monitor `/health` and the hosting platform's process/container health. -->
