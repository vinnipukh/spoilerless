# .env File Management — Concurrent AI Agent Pitfall

## The problem

When TWO AI agents (e.g., Hermes orchestrator + Claude Code) work concurrently on the same
repo, they both reach for `.env` files to switch between local docker Neo4j and AuraDB.
One agent flips to localhost for its test run, the other agent's subsequent test runs hit
the wrong database. The user experiences "all tests suddenly fail with connection refused."

## Root cause

- `config.py` line 128: `env_file=".env"` (read from CWD, not from `backend/`)
- `backend/.env` is a **zombie** — it's never read by pydantic-settings; pydantic reads
  `.env` relative to the process working directory, which is the repo root during `pytest`.
- Both agents used to have two copies of the same env (root `.env` + `backend/.env`),
  doubling the chore when switching between AuraDB and local docker.

## The fix

### 1. Single `.env` at repo root — always production (AuraDB)
```
NEO4J_URI=neo4j+s://03a8623b.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<Aura instance password>
NEO4J_DATABASE=03a8623b
GOOGLE_CLIENT_ID=...
AUTH_DEV_CODE=...
```

**Critical: `NEO4J_DATABASE` must be `03a8623b` (the AuraDB instance ID), NOT `neo4j`.**
The Aura instance database name matches the instance ID — queries with `neo4j` as the
database name will return `DatabaseNotFound` (22000) because the database literally doesn't
exist under that name.

### 2. `scripts/env-local.sh` — source for local docker testing
```bash
#!/usr/bin/env bash
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="hdgraf-local-password"
export NEO4J_DATABASE="neo4j"
```

Workflow: `docker compose up -d neo4j && source scripts/env-local.sh && uv run pytest ...`

Shell exports take priority over `.env` file values in pydantic-settings, so sourcing the
script before a test run is sufficient — the `.env` file is never modified.

### 3. Delete `backend/.env`
It's a zombie — pydantic-settings reads `.env` relative to CWD, never from `backend/`.
Keeping it around invites accidental divergence.

## Verification

After restoring Aura values to `.env`:
```
unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/test_auth.py -q
→ 42 passed  (proves Neo4jDatabase().open() succeeds against AuraDB)
```

The `scripts/env-local.sh` is verified by sourcing it and checking the exports land:
```
source scripts/env-local.sh
echo $NEO4J_URI  → neo4j://localhost:7687
```

## Windows AuraDB TLS note (certifi)

When testing AuraDB directly (not through the project's `database.py`), use:
```python
AsyncGraphDatabase.driver(
    "neo4j://03a8623b.databases.neo4j.io",
    auth=(user, pw),
    database="03a8623b",
    encrypted=True,
    trusted_certificates=TrustCustomCAs(certifi.where()),
)
```

The Windows OS trust store lacks the SSL.com root cert that AuraDB uses; `certifi` has it.
The project's `database.py` already normalizes `neo4j+s://` → `neo4j://` + `encrypted=True`
+ `TrustCustomCAs(certifi.where())` at the driver level, so tests using the project's own
`Neo4jDatabase` class work correctly. Only raw `AsyncGraphDatabase.driver()` calls from
ad-hoc scripts need the pattern above.
