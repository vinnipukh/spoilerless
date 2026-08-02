# HD Graf Cehennemi

**A spoiler-aware, source-grounded television-series knowledge graph application.**

Explore characters, events, locations, claims, and relationships through an interactive graph interface — with spoiler protection enforced at the backend data-access layer.

> **Prototype scope:** Dexter, Season 1, Episodes 1–3.

---

## Features

- **Interactive knowledge graph** — Browse a Cytoscape.js-powered graph of narrative entities (characters, events, locations, organizations, objects) and their relationships.
- **Spoiler-aware filtering** — Set your watch progress by episode. The backend enforces visibility at the data-access layer: nodes, claims, relationships, and evidence fragments beyond your selected episode are never returned — not merely hidden in the UI.
- **Source-grounded claims** — Every claim is backed by at least one evidence fragment with source metadata (type, URL, episode, timestamp). Confidence and status are tracked separately from relationship semantics.
- **User notes & custom content** — Add plain-text notes attached to characters or claims. Create custom nodes and relationships that are visually distinct from canonical seed data.
- **Revision history** — All user edits, corrections, and rejections are recorded in a revision log, enabling inspect-and-revert workflows.
|- **Google OAuth authentication** — Sign-in with Google ID tokens. Sessions are managed via HttpOnly cookies with configurable TTL. A Google Cloud OAuth client is required to log in. |
- **Future-ready architecture** — Clean extension points for LLM-powered extraction pipelines, candidate claim review workflows, and spoiler-grounded LLM chat.

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

The **spoiler boundary** is the system's core architectural invariant. Every story-sensitive entity carries a `visible_from_order` field. When a user sets their watch progress to episode N, the backend queries only data with `visible_from_order <= N`. Neither the frontend nor any future LLM integration ever receives data beyond this boundary.

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
| **Orchestration** | Docker Compose (Neo4j container) |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Neo4j)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js](https://nodejs.org/) — v18 or later

### 1. Clone and configure

```bash
git clone <repository-url>
cd hdgrafcehennemi
cp .env.example .env
```

Edit `.env` to set your Neo4j password.

### 2. Set up Google OAuth

This application **requires** a Google OAuth 2.0 client to log in.

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

### 3. Install Python dependencies and seed the database

```bash
uv sync
uv run hdgraf-setup
```

The `hdgraf-setup` command creates Neo4j constraints and seeds the Dexter series, episodes, characters, locations, events, claims, sources, and evidence fragments.

### 4. Start the backend

```bash
uv run uvicorn backend.app.main:app --reload
```

API documentation (Swagger UI) opens at `http://localhost:8000/docs`.

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Make sure `frontend/.env.local` exists with your `VITE_GOOGLE_CLIENT_ID` (set in step 2).

The frontend opens at `http://localhost:5173` and immediately shows the login screen. Sign in with your Google account to access the graph.

---

## Project Structure

```
hdgrafcehennemi/
├── backend/
│   └── app/
│       ├── api/            # Route handlers (series, graph, user_content, auth)
│       ├── core/           # Config, error handling
│       ├── domain/         # Pydantic models / schemas
│       ├── graph/          # Neo4j database, ontology, seed, setup
│       ├── repository/     # Data access layer (sessions, users, user content)
│       ├── revisions/      # Revision history model
│       ├── services/       # Business logic
│       ├── spoiler/        # Spoiler-aware filtering logic
│       └── main.py         # FastAPI application entry point
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
├── pyproject.toml           # Python project config & dependencies
└── .env.example            # Environment variable template
```

---

## API Overview

The backend exposes **21 operations over 14 path templates**, documented via OpenAPI at `/docs`.

| Endpoint | Description |
|---|---|
| `GET /health` | Service and database health check |
| `GET /api/series` | List all series |
| `GET /api/series/{series_id}` | Get series details |
| `GET /api/series/{series_id}/episodes` | List episodes for a series |
| `GET /api/series/{series_id}/graph?visible_until_order=N` | Get spoiler-filtered graph |
| `POST/GET /api/series/{series_id}/notes` | Create / list user notes |
| `PATCH/DELETE /api/series/{series_id}/notes/{note_id}` | Update / delete a note |
| `POST/GET /api/series/{series_id}/custom-nodes` | Create / get custom nodes |
| `PATCH/DELETE /api/series/{series_id}/custom-nodes/{node_id}` | Update / delete a custom node |
| `POST/GET /api/series/{series_id}/custom-relationships` | Create / get custom relationships |
| `PATCH/DELETE /api/series/{series_id}/custom-relationships/{...}` | Update / delete a custom relationship |
| `POST /api/auth/google` | Sign in with Google ID token |
| `GET /api/auth/me` | Get current user |
| `POST /api/auth/logout` | Sign out |

Spoiler-aware endpoints require a `visible_until_order` query parameter — a positive integer identifying the user's last watched episode order. Backend filtering is **fail-closed**: data beyond the boundary is never returned.

---

## Ontology (v0.1)

**Node types:** `Series`, `Season`, `Episode`, `Scene`, `Character`, `Location`, `Organization`, `Object`, `Event`, `Claim`, `Source`, `EvidenceFragment`, `UserNote`, `Revision`

**Relationship types:** Structural (`PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN`), participation (`PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`), character dynamics (`KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS`), provenance (`SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO`), and revision (`CORRECTS`, `SUPERSEDES`, `REVERTS_TO`).

**Claim dimensions:** Claims are atomic facts with type (`explicit_fact`, `observed_event`, `inferred_state`, `external_interpretation`, `user_authored`), status (`candidate`, `corroborated`, `canonical`, `disputed`, `rejected`), and confidence (`low`, `medium`, `high`, `verified`).

---

## Roadmap

This prototype builds toward:

1. **M1 — Local infrastructure** (Neo4j + FastAPI + Vite running)
2. **M2 — Metadata graph** (series/episode nodes and relationships)
3. **M3 — Spoiler-aware graph endpoint** (backend filtering with `visible_from_order`)
4. **M4 — Manual seed graph** (Dexter S01E01–03 character network)
5. **M5 — Frontend graph UI** (Cytoscape.js visualization, episode selector, spoiler modal)
6. **M6 — User notes and manual editing**
7. **M7 — Revision history**
8. **M8 — LLM extraction pipeline preparation**
9. **M9 — Spoiler-grounded LLM chat**

### Enabling the GraphRAG chat locally (optional)

The chat feature is **disabled by default**. To try it, point the backend at any
OpenAI-compatible chat-completions endpoint by setting `LLM_ENABLED=true`,
`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in your root `.env` (never commit
real key values). See [`docs/GETTING-STARTED.md`](./docs/GETTING-STARTED.md)
section 7.8 and [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) for the full
`LLM_*` reference. The LLM only ever sees the spoiler-filtered, tool-allowlisted
context — see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) §4.10
"Spoiler-Safety Invariants" for the guarantees.

See [`ROADMAP.md`](./ROADMAP.md) for details.

---

## License

This project is for demonstration and development purposes. All show-related data is used for illustrative, non-commercial prototyping.
