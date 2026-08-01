# Getting Started

> **A step-by-step guide to running HD Graf Cehennemi locally and exploring the demo flow.**
>
> **Project:** Spoiler-aware TV series knowledge graph (Dexter prototype)
> **Tech stack:** FastAPI + React/TypeScript/Cytoscape.js + Neo4j + Docker Compose

---

**Wave 1 docs (prerequisite reading):**

| Document | What it covers |
|---|---|
| [`README.md`](../README.md) | Project overview, features, tech stack, project structure, API overview |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System architecture, layer-by-layer breakdown, spoiler model, ontology |
| [`CONFIGURATION.md`](./CONFIGURATION.md) | Environment variables, Docker Compose setup, backend settings, ontology |

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone & Configure](#2-clone--configure)
3. [Start Neo4j](#3-start-neo4j)
4. [Install Dependencies & Seed the Database](#4-install-dependencies--seed-the-database)
5. [Start the Backend](#5-start-the-backend)
6. [Start the Frontend](#6-start-the-frontend)
7. [Demo Walkthrough](#7-demo-walkthrough)
8. [Troubleshooting](#8-troubleshooting)
9. [Next Steps](#9-next-steps)

---

## 1. Prerequisites

Install these tools before proceeding:

| Tool | Minimum version | Purpose |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | latest stable | Runs the Neo4j database container |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager and task runner |
| [Node.js](https://nodejs.org/) | v18+ | Runs the frontend dev server |
| [Git](https://git-scm.com/) | latest | Cloning the repository |

**OS support:** The commands below use POSIX shell syntax and work on:

- **Windows** (via Git Bash, WSL, or any MSYS2-based terminal)
- **macOS** (Terminal, iTerm2)
- **Linux** (any standard shell)

> If you're on Windows and using PowerShell or cmd.exe, open **Git Bash** instead — the commands assume POSIX conventions (`cp`, `cd`, `&&`, etc.).

### Verify installations

```bash
docker --version
uv --version
node --version
npm --version
git --version
```

---

## 2. Clone & Configure

### 2.1 Clone the repository

```bash
git clone <repository-url>
cd hdgrafcehennemi
```

### 2.2 Create the environment files

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

### 2.3 Configure backend `.env`

Open `.env` in your editor and update the **Neo4j password** to match the Docker Compose default:

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=hdgraf-local-password    # ← Must match docker-compose.yml
NEO4J_DATABASE=neo4j
```

> **Why `hdgraf-local-password`?** The `docker-compose.yml` sets `NEO4J_AUTH: neo4j/hdgraf-local-password`. The `.env` file must match these credentials so the Python backend can connect.

### 2.4 Set up Google OAuth

This application **requires** a Google OAuth 2.0 client to log in.

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** of type **Web application**
3. Add `http://localhost:5173` to **Authorized JavaScript origins**
4. Copy the **Client ID**

Add the client ID to both `.env` and `frontend/.env.local`:

```bash
echo "GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com" >> .env
# Then edit frontend/.env.local and set VITE_GOOGLE_CLIENT_ID to the same value
```

> Never commit `.env` or `.env.local`. The `.gitignore` already excludes them.
> `GOOGLE_CLIENT_SECRET` is **not** used and must not be added.

**Environment variable reference**

|| Variable | File | Description |
|---|---|---|---|
|| `GOOGLE_CLIENT_ID` | `.env` | Google OAuth client ID for token verification |
|| `VITE_GOOGLE_CLIENT_ID` | `frontend/.env.local` | Same client ID, exposed to the React app |
|| `SESSION_COOKIE_NAME` | `.env` | HttpOnly cookie name (default: `session`) |
|| `SESSION_TTL_SECONDS` | `.env` | Session lifetime in seconds (default: 604800 — 7 days) |
|| `SESSION_COOKIE_SECURE` | `.env` | Set `true` if testing over HTTPS |
|| `FRONTEND_ORIGINS` | `.env` | Comma-separated CORS origins (default: `http://localhost:5173`) |

See [`CONFIGURATION.md`](./CONFIGURATION.md) for full details on every variable.

---

## 3. Start Neo4j

Bring up the Neo4j container using Docker Compose:

```bash
docker compose up -d
```

This starts a single container (`hdgrafcehennemi-neo4j`) running Neo4j Community.

### Verify Neo4j is running

```bash
docker compose ps neo4j
```

Expected output:

```
NAME                       IMAGE                    STATUS                    PORTS
hdgrafcehennemi-neo4j      neo4j:2026-community     Up (healthy) ...          0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

You can also open the Neo4j Browser at [http://localhost:7474](http://localhost:7474) and log in with `neo4j` / `hdgraf-local-password`.

> **Wait for the health check:** Docker Compose waits up to ~100 seconds (10 retries × 10s interval) for Neo4j to become healthy. The backend will also handle degraded startup if Neo4j isn't ready yet, but running the seed script requires a healthy connection.

### Key ports

| Port | Service |
|---|---|
| `7474` | Neo4j HTTP Browser |
| `7687` | Neo4j Bolt protocol (used by the Python driver) |

---

## 4. Install Dependencies & Seed the Database

### 4.1 Install Python dependencies

```bash
uv sync
```

This creates a virtual environment (`.venv`) and installs all dependencies from `pyproject.toml`, including:

- FastAPI + Uvicorn (backend web framework)
- Neo4j Python driver (database connectivity)
- Pydantic + pydantic-settings (configuration and validation)
- google-auth (optional, for Google OAuth)
- PyYAML (ontology file parsing)

### 4.2 Seed the database

```bash
uv run hdgraf-setup
```

This command:

1. Connects to Neo4j using credentials from `.env`
2. Creates Neo4j constraints and indexes (uniqueness constraints on node IDs, range indexes on `visible_from_order`, etc.)
3. Loads seed JSON from `data/dexter/` (series metadata, episodes, characters, claims, sources, evidence fragments)
4. Validates all data against the ontology (node types, relationship types, claim types, statuses, confidence levels)
5. Creates all nodes and relationships via `MERGE` (idempotent — safe to re-run)
6. Runs a visibility integrity audit

Expected output:

```
Dexter graph setup complete: <N> nodes, <M> relationships
```

> **Already seeded?** The command is idempotent. Re-running it won't duplicate data — `MERGE` operations skip existing nodes with matching IDs.

### What got seeded?

The seed script populates the graph with data from **Dexter Season 1, Episodes 1–3**:

- **Structural nodes:** Series (`series:dexter`), Season, 3 Episode nodes (S01E01–S01E03)
- **Narrative nodes:** Characters, locations, events, organizations, objects
- **Knowledge nodes:** Claims with evidence fragments linked to sources
- **Relationships:** `PART_OF`, `PRECEDES`, `OCCURRED_IN`, and claim-driven edges like `KNOWS`, `KILLS`, `FAMILY_OF`, etc.

Each entity carries a `visible_from_order` integer field that the spoiler filter uses to gate visibility.

---

## 5. Start the Backend

```bash
uv run uvicorn backend.app.main:app --reload
```

This starts the FastAPI server with hot reload enabled.

| Property | Value |
|---|---|
| **URL** | `http://localhost:8000` |
| **API docs (Swagger UI)** | `http://localhost:8000/docs` |
| **Health check** | `http://localhost:8000/health` |
| **OpenAPI spec** | `http://localhost:8000/openapi.json` |

### Verify the backend

```bash
# Health check
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "database": "connected", "service": "hdgrafcehennemi-backend"}
```

> **Database shows `"unavailable"`?** Neo4j may still be starting. Wait a few seconds and retry. The backend starts even without a live database (degraded startup).

### API overview

The backend exposes **21 operations over 14 path templates**. Key endpoints for the demo:

| Endpoint | Purpose |
|---|---|
| `GET /api/series` | List all seeded series |
| `GET /api/series/{series_id}/episodes` | List episodes for a series |
| `GET /api/series/{series_id}/graph?visible_until_order=N` | **Spoiler-filtered graph data** — the core endpoint |
| `POST /api/series/{series_id}/notes` | Create a user note |
| `GET /api/auth/me` | Get current authenticated user (only if auth is configured) |

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to explore every endpoint interactively.

---

## 6. Start the Frontend

Open a **new terminal** (keep the backend running) and:

```bash
cd frontend
npm install
npm run dev
```

| Property | Value |
|---|---|
| **URL** | `http://localhost:5173` |
| **Dev server** | Vite 8 |

> **Prerequisite:** `frontend/.env.local` must exist with `VITE_GOOGLE_CLIENT_ID` set to your Google OAuth client ID (configured in step [2.4](#24-set-up-google-oauth)). Without it, the login page shows a configuration error.

### How the frontend communicates with the backend

The Vite dev server proxies all `/api` requests to the backend at `http://127.0.0.1:8000`. This means:

- The frontend calls `fetch('/api/series')` — no hardcoded backend URL needed
- No CORS issues during development
- Session cookies are set on the same origin

You can verify the proxy is working by opening your browser's developer tools (Network tab) and watching API requests flow to `localhost:8000`.

---

## 7. Demo Walkthrough

Once everything is running ([http://localhost:5173](http://localhost:5173)), the login screen appears. Sign in with your Google account, then follow this flow to experience the application's core features.

### 7.1 Select the series

1. The app loads and presents a series selector.
2. Click **Dexter** (the only seeded series).
3. The episode list populates with S01E01, S01E02, and S01E03.

**What's happening behind the scenes:**
- `useSeries()` calls `GET /api/series` → returns Dexter
- `useEpisodes()` calls `GET /api/series/series:dexter/episodes` → returns 3 episodes
- These endpoints have **no spoiler filtering** — series and episode metadata are always public

### 7.2 Set watch progress to S01E01

1. In the **Episode Selector**, choose **S01E01**.
2. No confirmation modal appears for the initial selection (the user hasn't made a forward jump yet).
3. The graph renders with nodes and edges visible up to episode 1.

**What you should see:**
- Series and episode nodes
- Characters introduced in S01E01 (Dexter Morgan, Debra Morgan, Harry Morgan, etc.)
- Locations from the first episode (Miami Metro, Dexter's apartment)
- Claims and relationships backed by evidence from S01E01
- The graph layout uses the **cose-bilkent** algorithm for organic placement

**What you should NOT see:**
- Characters or events from S01E02 or S01E03
- Claims with `visible_from_order > 1`

**What's happening behind the scenes:**
- `useGraph()` calls `GET /api/series/series:dexter/graph?visible_until_order=1`
- `GraphService.fetch_graph()` runs **7 concurrent Cypher queries**:
  1. Series metadata
  2. All visible nodes (`visible_from_order <= 1`)
  3. Structural edges (`PART_OF`, `PRECEDES`, `OCCURRED_IN`)
  4. Visible claims (canonical + candidate, filtered)
  5. User-authored relationships
  6. Sources for claims
  7. Evidence fragments for claims
- The frontend's `graphToElements()` maps the response to Cytoscape elements **without any additional filtering** — the backend is the sole authority on visibility.

### 7.3 Interact with the graph

1. **Tap a character node** (e.g., Dexter Morgan).
   - The node's closed neighborhood highlights (connected nodes and edges stay at full opacity).
   - Everything else dims to 0.15–0.25 opacity.
   - A detail panel opens on the right side.

2. **Inspect the detail panel:**
   - **Node info:** Label, type, series, visibility metadata.
   - **Claim-backed edges:** Toggle through claims connected to this character.
   - **Evidence:** Each claim shows its supporting evidence fragments with source metadata (source type, URL, episode, timestamp).
   - **Confidence level:** `low`, `medium`, `high`, or `verified` — displayed alongside claim status (`canonical`, `corroborated`, etc.).

3. **Hover over a truncated label** to see the full name in a tooltip.

4. **Tap a structural edge** (e.g., `PART_OF` between an episode and the series) — the `StructuralEdgeCard` renders topology info.

5. **Drag nodes** to rearrange the layout. The cose-bilkent algorithm automatically spaces related nodes close together.

### 7.4 Advance to S01E02 (spoiler confirmation)

1. Open the **Episode Selector** and select **S01E02**.
2. A **confirmation modal** appears with a spoiler warning: **"You're about to advance your watch progress to S01E02. New nodes, claims, and relationships will become visible."**
3. Click **Confirm**.
4. The graph re-renders with additional nodes, edges, and claims from S01E02.

**What becomes visible:**
- Characters, events, and locations introduced in S01E02
- Claims with `visible_from_order: 2`
- Evidence fragments referencing S01E02

**What's happening behind the scenes:**
- `useWatchProgress.setState()` updates a `pendingChange` in sessionStorage
- `ConfirmAdvanceModal` dispatches `confirmChange()` on user confirmation
- `visibleUntilOrder` changes from `1` to `2`
- The `useGraph` hook fires a new `GET /api/series/series:dexter/graph?visible_until_order=2`
- The entire graph re-renders with the new spoiler boundary

**Try the reverse:** Select S01E01 again. A similar confirmation modal asks you to confirm stepping back. The graph contracts to only show S01E01-visible data.

### 7.5 Inspect claims and evidence

1. Tap a claim-backed edge (displayed as a solid line between two character nodes).
2. The detail panel shows:
   - **Claim summary:** "Dexter knows Debra" (subject → predicate → object)
   - **Claim type:** `explicit_fact`, `observed_event`, etc.
   - **Status:** `canonical`, `corroborated`, `candidate`, `disputed`, `rejected`
   - **Confidence:** `verified`, `high`, etc.
   - **Evidence tab:** One or more evidence fragments linked to this claim
   - **Source tab:** The original source (e.g., a transcript, episode script, summary)

**Evidence fragment detail:**
```json
{
  "id": "evt:dexter_and_debra_are_siblings",
  "source_type": "episode_script",
  "text": "Dexter: 'Debra's my sister. She's a cop. She doesn't know about me.'",
  "url": "",
  "episode_order": 1,
  "timestamp": null,
  "confidence": "high"
}
```

### 7.6 Create a user note (optional)

1. Select a character node (e.g., Dexter Morgan).
2. In the detail panel, click **Add Note**.
3. Type a note (e.g., "Interesting how he compartmentalizes his work and personal life.").
4. Click **Save**.
5. The note appears as a dashed-border node attached to the character.

**What's happening behind the scenes:**
- `POST /api/series/series:dexter/notes` with `{target_type: "Character", target_id: "character:dexter_morgan", content: "..."}`
- The note inherits the target's `visible_from_order`
- The note node has a **dashed border** (user-created content is visually distinct from canonical data)
- The note's `origin` is `user`

### 7.7 Advance to S01E03 (repeat)

The same spoiler confirmation flow applies. With all three episodes visible, you see the complete Dexter S01 graph prototype.

### 7.8 Enable the GraphRAG chat (optional)

Chat is **disabled by default** (`LLM_ENABLED=false`). To turn it on you need an
OpenAI-compatible chat-completions endpoint — OpenAI, a local vLLM server, or any
compatible provider. Add these to the **backend** `.env` (project root):

```bash
LLM_ENABLED=true
LLM_BASE_URL=https://api.openai.com/v1     # or your local endpoint
LLM_API_KEY=your-key-here                  # never commit real values
LLM_MODEL=gpt-4.1-mini                     # any model your endpoint exposes
```

Restart the backend. The remaining `LLM_*` knobs (`LLM_TIMEOUT_SECONDS`,
`LLM_MAX_OUTPUT_TOKENS`, `LLM_TEMPERATURE`, `LLM_MAX_TOOL_ROUNDS`,
`LLM_MAX_CONTEXT_ITEMS`, `LLM_MAX_CONTEXT_CHARACTERS`) are optional; see
[`CONFIGURATION.md`](./CONFIGURATION.md) for defaults and bounds. With
`LLM_ENABLED=false` (or no provider reachable), the chat panel still opens but
turns return a clear "chat is disabled / provider unavailable" banner instead
of crashing.

---

## 8. Troubleshooting

### Neo4j won't start

```bash
# Check container logs
docker compose logs neo4j

# Common issues:
# - Port 7474 or 7687 already in use → stop other Neo4j instances
# - Docker not running → start Docker Desktop
# - Image not found → try neo4j:5-community as a fallback
```

### Backend can't connect to Neo4j

```
# Error: database_unavailable
# Check your .env matches docker-compose.yml:
NEO4J_PASSWORD=hdgraf-local-password   # Match docker-compose.yml
NEO4J_URI=neo4j://localhost:7687       # Bolt port, not HTTP port
```

### Frontend shows blank page

```bash
# Check the browser's developer console for errors
# Common issues:
# - Backend not running → start it with uv run uvicorn ...
# - Vite proxy misconfigured → check frontend/vite.config.ts
# - Port conflict → ensure nothing else runs on :5173
```

### `uv run hdgraf-setup` fails

```bash
# Error: "Neo4j connection refused"
# → Neo4j may still be starting. Wait and retry.
# → Verify docker compose ps shows "healthy" status.

# Error: "Ontology validation error"
# → Check ontology/ files have ontology_version: "0.1"

# Error: "Constraint already exists"
# → The idempotent MERGE should handle this. Try re-running.
```

### Python version issues

This project requires **Python 3.13+**. Verify:

```bash
python --version
```

If you have multiple Python versions, uv auto-discovers the right one from `.python-version` or `requires-python` in `pyproject.toml`.

### Windows-specific notes

| Issue | Fix |
|---|---|
| `docker compose` not found | Use `docker-compose` (with hyphen) on older Docker Desktop |
| `uv` not found after install | Restart your terminal, or add `~/.local/bin` to PATH |
| `npm install` fails with long paths | Enable long path support: `git config --system core.longpaths true` |
| Line endings (CRLF) | Git for Windows defaults to `core.autocrlf=true` — files work fine |

---

## 9. Next Steps

Once you're up and running:

| Goal | Resource |
|---|---|
| Understand the architecture | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) |
| Configure auth, ports, or Neo4j | [`docs/CONFIGURATION.md`](./CONFIGURATION.md) |
| Learn the graph data model | [`ontology/node_types.yaml`](../ontology/node_types.yaml), [`relation_types.yaml`](../ontology/relation_types.yaml), [`claim_types.yaml`](../ontology/claim_types.yaml) |
| See the planned features | [`ROADMAP.md`](../ROADMAP.md) |
| Add seed data | Add JSON files under `data/dexter/seed/` or `data/dexter/metadata/` |
| Run the tests | `uv run pytest` (backend) / `cd frontend && npm test` (frontend) |
| Build for production | `cd frontend && npm run build` |

---

## Quick Reference: All Commands

```bash
# 1. Clone and configure
git clone <repo-url>
cd hdgrafcehennemi
cp .env.example .env
cp frontend/.env.example frontend/.env.local
# Edit .env: set NEO4J_PASSWORD=hdgraf-local-password
# Edit .env and frontend/.env.local: set GOOGLE_CLIENT_ID matching values

# 2. Start Neo4j
docker compose up -d

# 3. Install Python deps and seed data
uv sync
uv run hdgraf-setup

# 4. Start the backend (terminal 1)
uv run uvicorn backend.app.main:app --reload

# 5. Start the frontend (terminal 2)
cd frontend && npm install && npm run dev

# 6. Open in browser
open http://localhost:5173
```

### Demo flow checklist

- [ ] Select Dexter series
- [ ] Set watch progress to S01E01
- [ ] Explore the graph — tap nodes, inspect claims and evidence
- [ ] Advance to S01E02 — confirm spoiler warning
- [ ] Inspect newly visible nodes and claims
- [ ] Add a user note
- [ ] Advance to S01E03
- [ ] View the complete S01 graph with all three episodes unlocked
