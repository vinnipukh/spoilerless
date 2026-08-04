<!-- generated-by: gsd-doc-writer -->
# HD Graf Cehennemi

**A spoiler-aware, source-grounded television-series knowledge graph application.**

Explore characters, events, locations, claims, and relationships through an interactive graph interface — with spoiler protection enforced at the backend data-access layer, plus an optional spoiler-safe LLM chat over the same filtered graph.

> **Prototype scope:** Dexter, Season 1, Episodes 1–3.

## Product direction

The repository is a polished vertical prototype for a **spoiler-aware, provenance-backed narrative knowledge graph**: an Obsidian-like graph, human-authored knowledge, revision history, and GraphRAG over only the viewer-visible subgraph. Candidate review and chat, which began as roadmap goals, are now implemented; automated subtitle/script ingestion, production deployment, and broader product scope remain future work.

Coding agents should use [`docs/PROJECT-SPEC.md`](./docs/PROJECT-SPEC.md) for product intent and non-negotiable invariants, and [`docs/ROADMAP.md`](./docs/ROADMAP.md) for milestone history and future research direction. Both documents distinguish implemented capability, historical prototype scope, and future requirements; implementation status must still be verified against live source and tests before acting on it.

---

## Features

- **Interactive knowledge graph** — Browse a Cytoscape.js-powered graph of narrative entities (characters, events, locations, organizations, objects) and their relationships.
- **Spoiler-aware filtering** — Set your watch progress by episode. Graph and boundary-aware user-content reads enforce visibility at the backend data-access layer; candidate review reads are an exception because their boundary is optional or absent.
- **Source-grounded claims** — Curated canonical claims are backed by evidence fragments whose sources include type, episode, locator, and retrieval date metadata; user-authored relationship claims may have no evidence. Confidence and status are tracked separately from relationship semantics.
- **User notes & custom content** — Add plain-text notes attached to characters or claims. Create custom nodes and relationships that are visually distinct from canonical seed data.
- **Revision history** — All user edits, corrections, and rejections are recorded in a revision log, enabling inspect-and-revert workflows.
- **Candidate claim review** — Extraction candidates go through a review workflow before entering the canonical graph.
- **Change sets** — Batched, confirmable edits with revision tracking and protection against conflicting changes.
- **Google OAuth authentication** — Sign in with Google ID tokens. Sessions are managed via HttpOnly cookies with configurable TTL. A Google Cloud OAuth client is required to log in. A user's role (`admin` or `user`) is derived server-side at login from the `ADMIN_EMAILS` allowlist; the admin role gates candidate review commits, change-set commits, and the application settings endpoints.
- **Spoiler-grounded LLM chat (optional)** — Disabled by default. When enabled, an OpenAI-compatible chat model answers questions using only the spoiler-filtered, tool-allowlisted graph context for the user's watch progress.
- **Redis-backed rate limiting and caching (optional)** — When `REDIS_URL` is set, login, chat-send, and content-write routes are rate-limited, and spoiler-filtered graph responses are cached. An empty `REDIS_URL` disables both features rather than failing startup.

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
    FastAPI REST API
         │
         ▼
React + TypeScript frontend
(Cytoscape.js interactive graph)
```

The **spoiler boundary** is the system's core architectural invariant. Every story-sensitive entity carries a `visible_from_order` field. When a user sets their watch progress to episode N, graph and GraphRAG queries return only data with `visible_from_order <= N`; candidate review reads remain the documented exception because their boundary is optional or absent.

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full system breakdown.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13+, FastAPI, Pydantic v2 |
| **Database** | Neo4j Community (via Docker Compose) |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4 |
| **Graph visualization** | Cytoscape.js + react-cytoscapejs |
| **UI components** | shadcn/ui (Radix UI primitives, Lucide icons) |
| **Python deps** | uv |
| **Frontend deps** | npm |
| **Rate limiting / caching** | Redis (Upstash) via `fastapi-limiter` — optional, disabled when `REDIS_URL` is empty |
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

This application **requires** a Google OAuth 2.0 client to log in.
<!-- VERIFY: Google Cloud Console OAuth 2.0 client setup steps (console.cloud.google.com) are external service details. -->

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** of type **Web application**
3. Add `http://localhost:5173` to **Authorized JavaScript origins**
4. Copy the **Client ID**

Configure both backend and frontend:

```bash
# Backend
echo "GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com" >> .env

# Frontend
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local and set VITE_GOOGLE_CLIENT_ID to the same client ID
```

> Never commit `.env` or `.env.local`. The `.gitignore` already excludes them.
> `GOOGLE_CLIENT_SECRET` is **not** used and must not be added.

### 3. Start Neo4j

```bash
docker compose up -d
```

Neo4j Browser will be available at `http://localhost:7474`.

### 4. Install Python dependencies and seed the database

```bash
uv sync
uv run --project backend python -m backend.app.graph.setup
```

The setup module creates Neo4j constraints and seeds the Dexter series, episodes, characters, locations, events, claims, sources, and evidence fragments. Although `pyproject.toml` declares an `hdgraf-setup` script, the current project packaging configuration does not install that executable through `uv sync`.

### 5. Start the backend

```bash
uv run uvicorn backend.app.main:app --reload
```

API documentation (Swagger UI) opens at `http://localhost:8000/docs`.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Make sure `frontend/.env.local` exists with your `VITE_GOOGLE_CLIENT_ID` (set in step 2).

The frontend opens at `http://localhost:5173` and immediately shows the login screen. Sign in with your Google account to access the graph.

For a full walkthrough with troubleshooting, see [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md).

---

## Project Structure

```
hdgrafcehennemi/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (series, graph, user_content, auth,
│   │   │                   #   revisions, candidates, progress, chat, change_set, settings)
│   │   ├── cache/          # Redis client, graph response cache (optional)
│   │   ├── core/           # Config, error handling
│   │   ├── domain/         # Pydantic models / schemas
│   │   ├── graph/          # Neo4j database, ontology, seed, setup
│   │   ├── llm/            # LLM provider, fallbacks, system prompt (GraphRAG chat)
│   │   ├── repository/     # Data access layer (sessions, users, user content, etc.)
│   │   ├── retrieval/      # Retrieval pipeline and tools for chat context
│   │   ├── revisions/      # Revision history model
│   │   ├── services/       # Business logic
│   │   ├── spoiler/        # Spoiler-aware filtering logic
│   │   └── main.py         # FastAPI application entry point
│   └── tests/              # pytest test suite
├── frontend/
│   └── src/
│       ├── api/            # API client calls
│       ├── components/     # React components
│       ├── hooks/          # Custom React hooks
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

---

## API Overview

The backend exposes REST endpoints grouped by area, documented via OpenAPI at `/docs`. See [`docs/API.md`](./docs/API.md) for the full reference.

| Area | Path prefix | Description |
|---|---|---|
| Health | `GET /health` | Service and database health check |
| Series | `/api/series` | List/get series and episodes |
| Graph | `/api/series/{series_id}/graph` | Spoiler-filtered graph, keyed by `visible_until_order` |
| Auth | `/api/auth` | Google sign-in, current user, logout |
| User content | `/api/series/{series_id}/notes`, `/custom-nodes`, `/custom-relationships` | User notes and custom graph content |
| Revisions | `/api/series/{series_id}/...` | Revision history for user edits |
| Candidates | `/api/series/{series_id}/candidates` | Candidate claim review workflow |
| Progress | `/api/series/{series_id}/progress` | User watch-progress tracking |
| Chat | `/api/series/{series_id}/chat` | Spoiler-grounded LLM chat (enabled through stored application settings or the `LLM_ENABLED` environment fallback) |
| Change sets | `/api/series/{series_id}/change-sets` | Batched, confirmable graph edits |
| Settings | `/api/settings` | Application settings |

Spoiler boundaries vary by endpoint: graph and boundary-aware user-content reads require a positive `visible_until_order` query parameter, chat resolves persisted watch progress server-side, the candidate list accepts an optional boundary, and candidate detail has no boundary parameter.

---

## Usage

Once the stack is running and you are signed in, the frontend at `http://localhost:5173` renders the interactive graph filtered to your watch progress. The API is also usable directly:

```bash
# List series (the Dexter prototype ships with series_dexter)
curl http://localhost:8000/api/series

# Fetch the spoiler-filtered graph visible up to the end of episode 2
curl "http://localhost:8000/api/series/series_dexter/graph?visible_until_order=2"
```

Watch progress is persisted per user via `GET/POST /api/series/{series_id}/progress`. Progress and chat endpoints require the Google OAuth session cookie; note and custom-content routes currently have no session dependency. See [`docs/API.md`](./docs/API.md) for the full reference.

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
| [`docs/PROJECT-SPEC.md`](./docs/PROJECT-SPEC.md) | Canonical product aim, invariants, coding-agent rules, and future architecture |
| [`docs/ROADMAP.md`](./docs/ROADMAP.md) | Canonical milestones, current gaps, backlog, and research direction |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System architecture, layer breakdown, spoiler model, ontology |
| [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) | Environment variables, Docker Compose, backend settings |
| [`docs/API.md`](./docs/API.md) | Full HTTP API reference |
| [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md) | Local development workflow, build/lint/format commands |
| [`docs/TESTING.md`](./docs/TESTING.md) | Test framework, running tests, coverage |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment targets and pipeline |
| [`docs/frontend-api-contract.md`](./docs/frontend-api-contract.md) | Frontend-facing API contract |

### Enabling the GraphRAG chat locally (optional)

The chat feature is **disabled by default**. To try it, point the backend at any
OpenAI-compatible chat-completions endpoint by setting `LLM_ENABLED=true`,
`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in your root `.env` (never commit
real key values). See [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md)
and [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) for the full `LLM_*`
reference. The LLM only ever sees the spoiler-filtered, tool-allowlisted
context — see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the
spoiler-safety guarantees.

---

## License

This project is for demonstration and development purposes. All show-related data is used for illustrative, non-commercial prototyping.
