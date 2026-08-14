<!-- generated-by: gsd-doc-writer -->
# Spoilerless

**A spoiler-aware, source-grounded television-series knowledge graph application.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

Explore characters, events, locations, claims, and relationships through an interactive graph interface — with spoiler protection enforced at the backend data-access layer, plus an optional spoiler-safe LLM chat over the same filtered graph.

> **Shipped content scope:** Dexter, Season 1, Episodes 1–3 (the v1.3 seed series).

---

## Deployment & Environment Quick Reference

**Live production (operator-verified, v1.3 shipped 2026-08-13):** Vercel `app.spoilerless.net` (frontend) · Render `api.spoilerless.net` (backend) · Neo4j AuraDB Free `03a8623b` · Upstash Redis `darling-rat-221809` · Cloudflare DNS + apex redirect.

### Where configuration lives

| Location | Holds | Notes |
|---|---|---|
| `.env` (repo root) | Backend settings (`NEO4J_*`, `GOOGLE_CLIENT_ID`, `ALLOWED_EMAILS`, `ADMIN_EMAILS`, `REDIS_URL`, `LLM_*`) and frontend `VITE_*` values | Read by `spoilerless/app/core/config.py` via pydantic-settings; Vite reads the same root file via `envDir: '..'` in `frontend/vite.config.ts`. **Never committed.** `.env.example` provides the local-Neo4j, auth, and LLM baseline; `ALLOWED_EMAILS`, `ADMIN_EMAILS`, and `REDIS_URL` are optional settings declared in code but are not currently listed in that template. |
| `scripts/env-local.sh` | Compatibility credentials for an existing local Neo4j container (`localhost:7687`, password `hdgraf-local-password`) | Use only when the running container was created with that password. A fresh Compose deployment instead uses `NEO4J_PASSWORD` from the shell or `.env`, defaulting to `change-me`. |
| `docker-compose.yml` | Local Neo4j Community container (`spoilerless-neo4j`, auth `neo4j` / `${NEO4J_PASSWORD:-change-me}`) | Only for local testing; production uses AuraDB. |

### Platform environment variables

<!-- VERIFY: Render platform deployment environment variables and target database URL. -->
**Render — `api.spoilerless.net`** — service `spoilerless-api` (Blueprint `render.yaml`): build **`uv sync --frozen`**, start **`uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`**. Required environment unless noted:

```
NEO4J_URI=neo4j+s://03a8623b.databases.neo4j.io
NEO4J_USERNAME=<AuraDB username>
NEO4J_PASSWORD=<AuraDB password>
NEO4J_DATABASE=03a8623b
GOOGLE_CLIENT_ID=<Google OAuth web client ID>
ALLOWED_EMAILS=<comma-separated sign-in allowlist>
ADMIN_EMAILS=<comma-separated admin allowlist>
FRONTEND_ORIGINS=https://app.spoilerless.net
REDIS_URL=rediss://default:<token>@darling-rat-221809.upstash.io:6379   # optional; empty disables rate limiting + graph cache
SESSION_COOKIE_SECURE=true                                            # optional
SESSION_TTL_SECONDS=604800                                            # optional
```

<!-- VERIFY: Vercel deployment parameters and target API URL. -->
**Vercel — `app.spoilerless.net`**:

```
VITE_API_BASE_URL=https://api.spoilerless.net
VITE_GOOGLE_CLIENT_ID=<same Google OAuth web client ID>
```

Build settings: Framework Preset **Vite**, Root Directory **`frontend/`**, Build Command **`npm run build`**, Output Directory **`dist`**.

<!-- VERIFY: Cloudflare DNS routing and HTTP dynamic redirect configuration. -->
**Cloudflare — DNS + redirect:** CNAME `app` → Vercel target (proxied), CNAME `api` → Render target (DNS-only), apex `@` A-record `192.0.2.1` (proxied), plus a Dynamic Redirect rule: hostname `spoilerless.net` → 301 → `concat("https://app.spoilerless.net", http.request.uri.path)`.

### Fresh machine checklist

1. `git clone https://github.com/vinnipukh/hdgrafcehennemi.git`
2. `uv sync` (backend deps) and `cd frontend && npm install`
3. `cp .env.example .env` → for local development, keep the matching Neo4j defaults, set `VITE_API_BASE_URL=` (empty, so `/api` paths use the Vite proxy), and add Google/allowlist/Redis values only if those features are needed; `VITE_GOOGLE_CLIENT_ID` lives in this same root `.env`. In production, set `VITE_API_BASE_URL` to the full backend origin instead.
4. Start the local database with `docker compose up -d neo4j`
5. Backend: `uv run uvicorn spoilerless.app.main:app --reload` · Frontend: `cd frontend && npm run dev`

Full platform-specific procedures, rollback, and monitoring: [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

---

## Product direction

Spoilerless v1.3 is **shipped, deployed, and archived** (git tag `v1.3`) as a spoiler-aware, provenance-backed narrative knowledge graph: an Obsidian-like graph, human-authored knowledge, revision history, and GraphRAG over only the viewer-visible subgraph, presented through the Story / Characters / Evidence / Advanced projection views. Candidate review and chat are implemented; automated subtitle/script ingestion, broader product scope, and further deployment hardening remain future work (see [`docs/ROADMAP.md`](./docs/ROADMAP.md)).

Coding agents should use [`docs/architecture/project-spec.md`](./docs/architecture/project-spec.md) for product intent and non-negotiable invariants. The document distinguishes implemented capability, historical prototype scope, and future requirements; implementation status must still be verified against live source and tests before acting on it.

---

## Features

- **Interactive knowledge graph** — Browse a Cytoscape.js-powered graph of narrative entities (characters, events, locations, organizations, objects) and their relationships.
- **Spoiler-aware filtering** — Set your watch progress by episode. Graph, boundary-aware user-content, and candidate review reads enforce visibility at the backend data-access layer; candidate list and detail reads require a positive boundary validated against a persisted episode.
- **Source-grounded claims** — Curated canonical claims are backed by evidence fragments whose sources include type, episode, locator, and retrieval date metadata; user-authored relationship claims may have no evidence. Confidence and status are tracked separately from relationship semantics.
- **User notes & custom content** — Add plain-text notes attached to characters or claims. Create custom nodes and relationships that are visually distinct from canonical seed data.
- **Revision history** — All user edits, corrections, and rejections are recorded in a revision log, enabling inspect-and-revert workflows.
- **Candidate claim review** — Extraction candidates go through a review workflow before entering the canonical graph.
- **Change sets** — Batched, confirmable edits with revision tracking and protection against conflicting changes.
- **Google OAuth + visitor mode** — Sign in with Google ID tokens for persisted progress and write features, or continue as a read-only visitor without an account. Authenticated sessions use HttpOnly cookies with configurable TTL. A user's role (`admin` or `user`) is derived server-side at login from the `ADMIN_EMAILS` allowlist; the admin role gates candidate review commits, change-set commits, and the application settings endpoints. All state-changing cookie-authenticated endpoints are additionally protected by a shared CSRF origin guard.
- **Spoiler-grounded LLM chat (optional, BYOK)** — Disabled by default. When enabled, an LLM (Google Gemini or any OpenAI-compatible chat model, selectable per deployment) answers questions using only spoiler-filtered, tool-allowlisted graph context for the user's watch progress. Browser-stored BYOK settings travel per request in `X-LLM-*` headers; when those headers are absent, the backend falls back to its own configuration — either the `LLM_*` environment variables or admin-managed application settings stored in Neo4j (`:AppSetting {key: 'llm'}`, managed through the admin-gated `GET/PUT /api/settings/llm` endpoints, where the API key is write-only and displayed only in masked form, e.g. `••••1234`).
- **Redis-backed rate limiting and caching (optional)** — When `REDIS_URL` is set, login, chat-send, and content-write routes are rate-limited, and spoiler-filtered graph responses are cached. An empty `REDIS_URL` disables both features rather than failing startup.
- **Stale-while-refetch graph** — Refetching keeps the last-known-good graph on screen; loading/error/empty states render as overlays above the canvas instead of unmounting it.
- **Command palette (⌘K)** — Jump to any node, episode, or action from a keyboard-first palette; `/` focuses the floating search bar.
- **Node search + Notes & Claims search** — Zero-dependency substring search over the loaded graph payload (nodes, notes, and claims) with spoiler-safe results.
- **Timeline view** — A chronological, episode-grouped timeline of visible events; selecting an event frames it in the graph.
- **Series dashboard** — A dialog listing all available series with watch-progress bars; opens any series through the existing progress flow.
- **Markdown export** — Export the visible graph (or a single resource) as Markdown from the same filtered read path.
- **Path finder** — Pick two nodes to highlight the shortest visible path between them (server-resolved boundary, capped hops).
- **Read-only share links** — Authenticated users can create, list, and revoke expiring snapshot links; recipients can open the token-gated spoiler boundary without signing in.
- **Four projection views (v1.3)** — Story (bounded Episode Overview + coordinated Event Timeline), Characters (Character Network + Local Neighborhood), Evidence (layered Investigation / Evidence Chain + temporary GraphRAG Answer Graph), and Advanced (Full Graph / debug explorer). The backend serves library-neutral, task-specific projections from `GET /api/series/{series_id}/graph/visualization` (view types: `episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`) after the effective spoiler boundary is enforced; raw Neo4j relation names stay hidden outside debug mode.
- **Semantic expansion** — Server-allowlisted expansion (`family`, `work`, `conflict`, `episode_events`, `clues`, `locations`, `evidence`) adds 8–12 elements by default (hard max 25) with no hidden totals or future hints, and supports Collapse / Undo / Reset without global relayout.
- **Stable scene state** — React owns the scene; Cytoscape updates arrive as batched diffs, so camera, selection, expansions, and timeline state survive episode switches and restore exactly when temporary Answer Graph / Evidence Chain views close. Projection responses are cached per series / order / view / projection version / graph revision / user (focus views add a deterministic focus digest; expansion is deliberately uncached).
- **Responsive four-tab navigation** — Desktop uses top tabs; mobile mirrors the hierarchy with horizontally scrollable top tabs and a half/full-height Inspector bottom sheet, with keyboard focus, Escape/return-focus, and reduced-motion support (see the [Phase 10 UAT record](./docs/uat/phase-10-golden-path.md)).

---

## Architecture Overview

```
Curated seed data (JSON/YAML)
         │
         ▼
    Neo4j Graph Database
         │
         ▼
  Backend spoiler filtering
  (visible_from_order)
         │
         ▼
  Visualization projections
  (neutral DTOs, view/cache separation)
         │
         ▼
    FastAPI REST API
         │
         ▼
React + TypeScript frontend
(Cytoscape.js interactive graph)
```

The **spoiler boundary** is the system's core architectural invariant. Every story-sensitive entity carries a `visible_from_order` field. When a user sets their watch progress to episode N, graph and GraphRAG queries return only data with `visible_from_order <= N`; candidate list and detail reads likewise require a positive boundary that the server validates against a persisted episode. Projection and expansion reads enforce `effective_view_order = min(requested_view_order, watched_progress)` **before** projection or serialization (D-05), so future elements never leak through counts, layout, group names, expansion hints, or cache entries.

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full system breakdown.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13+, FastAPI, Pydantic v2 |
| **Database** | Neo4j Community via Docker Compose locally; Neo4j Aura-compatible deployment configuration |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4 |
| **Graph visualization** | Cytoscape.js + react-cytoscapejs |
| **UI components** | shadcn/ui (Radix UI primitives, Lucide icons) |
| **Python deps** | uv |
| **Frontend deps** | npm |
| **Rate limiting / caching** | Redis (Upstash); rate limiting uses a custom FastAPI dependency built on `pyrate-limiter` — optional, disabled when `REDIS_URL` is empty |
| **Tests** | pytest (backend, live Neo4j) · Vitest + React Testing Library (frontend) |
| **Orchestration** | Docker Compose (Neo4j container) |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Neo4j)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js](https://nodejs.org/) — `^22.22.2`, `^24.15.0`, or `>=26.0.0` (the committed `jsdom` lockfile requirement is stricter than Vite's)

### 1. Clone and configure

```bash
git clone https://github.com/vinnipukh/hdgrafcehennemi.git
cd hdgrafcehennemi
cp .env.example .env
```

Edit `.env` to set `NEO4J_PASSWORD` so it matches `docker-compose.yml` (the Compose default is `change-me`).

### 2. Set up Google OAuth

Google OAuth is required for authenticated sessions, persisted progress, chat, and write features. It is not required for read-only visitor browsing.
<!-- VERIFY: Google Cloud Console OAuth 2.0 client setup steps (console.cloud.google.com) are external service details. -->

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** of type **Web application**
3. Add `http://localhost:5173` to **Authorized JavaScript origins**
4. Copy the **Client ID**

Configure both backend and frontend in the **root `.env`** (the frontend reads it via `envDir: '..'` — there is no `frontend/.env.local` anymore):

```bash
echo "GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com" >> .env
echo "VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com" >> .env
```

> Never commit `.env`. The `.gitignore` already excludes it.
> `GOOGLE_CLIENT_SECRET` is **not** used and must not be added.

### 3. Start Neo4j

```bash
docker compose up -d
```

Neo4j Browser will be available at `http://localhost:7474`.

### 4. Install Python dependencies and seed the database

```bash
uv sync
uv run python -m spoilerless.app.graph.setup
```

The setup module creates Neo4j constraints and seeds the Dexter series, episodes, characters, locations, events, claims, sources, and evidence fragments. Although `pyproject.toml` declares a `spoilerless-setup` script, the current project packaging configuration (no `[build-system]` section) does not install that executable through `uv sync`.

### 5. Start the backend

```bash
uv run uvicorn spoilerless.app.main:app --reload
```

API documentation (Swagger UI) opens at `http://localhost:8000/docs`.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

For Google sign-in, make sure `VITE_GOOGLE_CLIENT_ID` is set in the root `.env` (step 2). Visitor browsing works without it.

The frontend opens at `http://localhost:5173` and shows the entry screen. Sign in with Google for the full application, or choose **Continue as visitor** for read-only graph browsing.

For a full walkthrough with troubleshooting, see [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md).

---

## Project Structure

```
.
├── spoilerless/
│   ├── app/
│   │   ├── api/            # Route handlers (auth, graph, share, chat, candidates, change sets, writes, settings)
│   │   ├── cache/          # Redis client and graph response cache (optional)
│   │   ├── core/           # Configuration, error handling, token helpers (core/tokens.py)
│   │   ├── domain/         # Pydantic models / schemas
│   │   ├── graph/          # Neo4j driver (single row normalizer / executor in database.py),
│   │   │                   #   label constants (labels.py), ontology, seed, setup
│   │   ├── llm/            # LLM providers (OpenAI-compatible + Gemini), fallbacks, GraphRAG prompt
│   │   ├── repository/     # Data access (sessions, users, user content, shares, settings, etc.)
│   │   ├── retrieval/      # Chat retrieval pipeline: context section registry (context.py),
│   │   │                   #   ToolSpec tool registry (pipeline.py), shared BFS (tools.py)
│   │   ├── revisions/      # Revision history repository
│   │   ├── services/       # Business logic (auth, change sets, graph, chat, progress, rate limit, …)
│   │   ├── spoiler/        # Spoiler-aware filtering logic
│   │   ├── static/         # Self-hosted character portraits (served under /api/static/)
│   │   └── main.py         # FastAPI application entry point
│   ├── scripts/            # Backend maintenance utilities (smoke.sh, zombie_sweep.py, test runners)
│   └── tests/              # pytest suite
├── frontend/
│   └── src/
│       ├── api/            # API client calls
│       ├── components/     # React components (graph/ includes canvas + status overlays; settings/ hosts the admin LLM settings page)
│       ├── hooks/          # Custom React hooks (shared useFetchState fetch machine)
│       ├── lib/            # Graph highlight helper, search index, BYOK, export (lib/graph/highlight.ts)
│       ├── providers/      # React context providers
│       └── types/          # TypeScript type definitions
├── data/dexter/            # Seed data for Dexter S01E01–03
│   ├── metadata/           # Series and episode metadata
│   └── seed/               # Characters, claims, events, evidence, locations, sources
├── ontology/               # Graph ontology definitions
│   ├── node_types.yaml
│   ├── relation_types.yaml
│   └── claim_types.yaml
├── docs/                   # Project documentation
├── docker-compose.yml      # Neo4j container orchestration
├── pyproject.toml          # Python project config & dependencies
└── .env.example            # Environment variable template
```

### Recent structural consolidations

- **Repository layer** — One row normalizer (`neo4j_row_to_python`) and one query executor (`run_single`) in `graph/database.py` replace per-repository duplicates; token helpers live in `core/tokens.py` and label constants in `graph/labels.py`.
- **Chat retrieval** — `retrieval/context.py` defines a single `CONTEXT_SECTIONS` registry whose delimiters are derived from it (they cannot drift); `retrieval/pipeline.py` registers all allowlisted tools as a single `ToolSpec` list (replacing three parallel schema/executor/input-model tables); neighborhood and path reads share one `_walk_visible_claims` BFS in `retrieval/tools.py`, with server-side ceilings (e.g. `MAX_PATH_HOPS = 4`) clamping any requested depth or hop count.
- **Change sets** — `services/change_set.py` applies operations through a table-driven dispatch and validates targets in parallel; `AuthService` now requires an explicit `session_repo` and verifier at construction (a missing dependency is a wiring bug, never a silent fallback).
- **Frontend** — All fetch hooks run on one shared `useFetchState` machine (`hooks/useFetchState.ts`); a single `applyHighlight` helper in `lib/graph/highlight.ts` replaces four cytoscape class-juggling copies; the graph canvas never unmounts on refetch — loading/error/empty overlays render above the last-known-good graph.

---

## API Overview

The backend exposes REST endpoints grouped by area, documented via OpenAPI at `/docs`. See [`docs/API.md`](./docs/API.md) for the full reference.

| Area | Path prefix | Description |
|---|---|---|
| Health | `GET /health` | Service and database health check |
| Series | `/api/series` | List/get series and episodes |
| Graph | `/api/series/{series_id}/graph` | Spoiler-filtered graph, keyed by `visible_until_order` |
| Graph projections | `GET /api/series/{series_id}/graph/visualization` | Library-neutral task projections (6 view types) after the effective boundary |
| Graph expansion | `GET /api/series/{series_id}/graph/expand` | Allowlisted, bounded semantic expansion (uncached) |
| Graph path | `POST /api/series/{series_id}/graph/path` | Shortest visible path between two entities (server-resolved boundary, `max_hops` capped at 4) |
| Export | `GET /api/series/{series_id}/export` | Visible graph (or `target_id` resource) as Markdown |
| Auth | `/api/auth` | Google sign-in, current user, logout |
| User content | `/api/series/{series_id}/notes`, `/custom-nodes`, `/custom-relationships` | User notes and custom graph content |
| Revisions | `/api/series/{series_id}/...` | Revision history for user edits |
| Candidates | `/api/series/{series_id}/candidates` | Candidate claim review workflow |
| Progress | `/api/series/{series_id}/progress` | User watch-progress tracking |
| Chat | `/api/series/{series_id}/chat` | Spoiler-grounded LLM chat (Gemini or OpenAI-compatible provider; enabled through stored application settings or the `LLM_ENABLED` environment fallback) |
| Change sets | `/api/series/{series_id}/change-sets` | Batched, confirmable graph edits |
| Settings | `/api/settings` | Admin-gated LLM provider configuration stored in Neo4j (`:AppSetting {key: 'llm'}`); the API key is write-only and masked in responses |
| Share links | `/api/share` | Create/list/revoke snapshots and read a token-gated graph |

Spoiler boundaries vary by endpoint: graph and boundary-aware user-content reads require a positive `visible_until_order` query parameter, chat resolves persisted watch progress server-side, and both candidate list and detail require `visible_until_order`, rejecting omission or a non-persisted episode order with 422.

---

## Usage

Once the stack is running and you are signed in, the frontend at `http://localhost:5173` renders the interactive graph filtered to your watch progress. The API is also usable directly:

```bash
# List series (the Dexter prototype ships with series_dexter)
curl http://localhost:8000/api/series

# Fetch the spoiler-filtered graph visible up to the end of episode 2
curl "http://localhost:8000/api/series/series_dexter/graph?visible_until_order=2"
```

Watch progress is persisted per user via `GET/POST /api/series/{series_id}/progress`. Progress, chat, user-content writes, candidate ingestion/review writes, revision reverts, change-set writes, settings, and share-link management require an authenticated session; selected operations additionally require the server-derived admin role. Visitor mode remains read-only. See [`docs/API.md`](./docs/API.md) for the full authorization matrix.

---

## Ontology (v0.1)

**Node types:** `Series`, `Season`, `Episode`, `Scene`, `Character`, `Location`, `Organization`, `Object`, `Event`, `Claim`, `Source`, `EvidenceFragment`, `UserNote`, `Revision`

**Relationship types:** Structural (`PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN`), participation (`PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`), character dynamics (`KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS`), provenance (`SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO`), and revision (`CORRECTS`, `SUPERSEDES`, `REVERTS_TO`).

**Claim dimensions:** Claims are atomic facts with type (`explicit_fact`, `observed_event`, `inferred_state`, `external_interpretation`, `user_authored`), status (`candidate`, `corroborated`, `canonical`, `disputed`, `rejected`), and confidence (`low`, `medium`, `high`, `verified`).

---

## Documentation

| Document | What it covers |
|---|---|
| [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md) | Step-by-step local setup and demo walkthrough |
| [`docs/architecture/project-spec.md`](./docs/architecture/project-spec.md) | Canonical product aim, invariants, coding-agent rules, and future architecture |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System architecture, layer breakdown, spoiler model, ontology |
| [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) | Environment variables, Docker Compose, backend settings |
| [`docs/API.md`](./docs/API.md) | Full HTTP API reference |
| [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md) | Local development workflow, build/lint/format commands |
| [`docs/TESTING.md`](./docs/TESTING.md) | Test framework, running tests, coverage |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment targets and pipeline |
| [`docs/uat/phase-10-golden-path.md`](./docs/uat/phase-10-golden-path.md) | Phase 10 (v1.3) operator-approved golden-path UAT record — 12 scenarios + 7 responsive/accessibility backstop rows |
| [`docs/decision-logs/phase-10-visualization.md`](./docs/decision-logs/phase-10-visualization.md) | Phase 10 evidence-based decision log (Episode Overview variant selection, bounds, cache, benchmark evidence) + final multi-source coverage audit |
| [`docs/ops/runbook.md`](./docs/ops/runbook.md) | Operations runbook — zombie sweep, DB-pollution gate, CI checks |
| [`docs/PROBLEMS.md`](./docs/PROBLEMS.md) | Audit ledger — findings and fixes across passes (NINETEENTH PASS: Phase 10 regression gate — guarded ephemeral-container test runner retires the seven-red baseline, 2026-08-13) |
| [`docs/ROADMAP.md`](./docs/ROADMAP.md) | Authoritative roadmap — milestones and acceptance status, known gaps, future direction |
| [`docs/reference/frontend-api-contract.md`](./docs/reference/frontend-api-contract.md) | Frontend-facing API contract |

### Enabling the GraphRAG chat locally (optional)

The chat feature is **disabled by default**. To try it, point the backend at any
OpenAI-compatible chat-completions endpoint by setting `LLM_ENABLED=true`,
`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in your root `.env` (never commit
real key values) — or use Google Gemini with `LLM_PROVIDER=gemini` (the Gemini
base URL defaults to `https://generativelanguage.googleapis.com`). Alternatively,
an admin can configure the provider from the Settings page in the app: the
`GET/PUT /api/settings/llm` endpoints persist the configuration in Neo4j as
`:AppSetting {key: 'llm'}`, which takes precedence over the environment
fallback, and never return the full API key — only a masked form such as
`••••1234`. See [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md)
and [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) for the full `LLM_*`
reference. The LLM only ever sees the spoiler-filtered, tool-allowlisted
context — see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the
spoiler-safety guarantees.

---

## Contributing

Please refer to [`CONTRIBUTING.md`](./CONTRIBUTING.md) for details on our code of conduct, development workflow, and the process for submitting pull requests.

---

## License

This project is licensed under the MIT License - see the [`LICENSE`](./LICENSE) file for details. All show-related data is used for illustrative, non-commercial prototyping.
