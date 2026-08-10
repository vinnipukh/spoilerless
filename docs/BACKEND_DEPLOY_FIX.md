# Backend Deploy Crash — Root Cause & Fix

**Date:** 2026-08-05  
**Error:** `ModuleNotFoundError: No module named 'backend'`

---

## Root Cause

The repository does not expose the current **Render dashboard Start Command**,
so its value requires operator verification. If an existing service still uses
this stale pre-rename command, it produces the reported import error:
```
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

But the Python package is named `spoilerless/`, not `backend/`. There is no `backend/` directory in the repo.

The `render.yaml` in the repo has the **correct** command:
```yaml
startCommand: uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT
```

An existing service can have a dashboard override that differs from the
Blueprint. Whether such an override is currently present, and how it was set,
cannot be determined from this repository. Treat both as operator-verification
items rather than attributing the change to an actor.

## Fix (Manual — Render Dashboard)

1. Go to https://dashboard.render.com → **spoilerless-api** service
2. **Settings** → **Start Command**
3. Inspect the current value; dashboard state is **operator-verification required**.
4. Set it to exactly: `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`
5. Save the setting and follow the dashboard's deployment status to verify the service restarts successfully.

Alternatively, delete and re-create the service from the Blueprint (`render.yaml`) which already has the correct value.

## Verification

- `pyproject.toml` → `name = "spoilerless"`, script entry: `spoilerless.app.graph.setup:main`
- `render.yaml` → `startCommand: uv run uvicorn spoilerless.app.main:app ...`
- Package directory: `spoilerless/app/main.py` exists ✅
- `backend/` directory: **does not exist** ❌

---

## Backend Tests — Break Up Strategy

The full `uv run pytest` suite can be slow in some local and networked-Neo4j
environments. Pull requests still run the full suite and DB-pollution gate in
CI. For targeted local diagnosis, the suite is split into **10 named chunks** —
every file in `spoilerless/tests/` appears in exactly one chunk. A chunk bounds
the test scope, but it has no enforced runtime limit; duration depends on the
selected files, Neo4j environment, network, and current load.

**Preferred entry point** — the chunk runner (strips the Hermes-terminal
`PYTHONPATH` that shadows the venv, so `import spoilerless` works):

```powershell
uv run python scripts/run_backend_tests.py          # all 10 chunks
uv run python scripts/run_backend_tests.py --list   # show chunk/file mapping
uv run python scripts/run_backend_tests.py --chunk 7
uv run python scripts/run_backend_tests.py --chunk auth
```

Equivalent raw pytest invocations (chunk → files):

| # | Chunk | Files | Rough profile |
|---|---|---|---|
| 1 | `core` | `test_config.py` `test_deps.py` `test_database.py` `test_main_lifespan.py` `test_setup_schema_check.py` `test_ontology.py` `test_visibility.py` `test_series_service.py` | unit, ~fast |
| 2 | `domain-models` | `test_revision_models.py` `test_user_content_models.py` `test_extraction_models.py` `test_episode_ordering.py` `test_episode_masking.py` `test_spoiler_policy.py` `test_conversational_tone.py` `test_s01e01_enrichment.py` | unit/domain, ~fast |
| 3 | `series-api` | `test_api_series.py` `test_progress_api.py` | API, ~medium |
| 4 | `graph` | `test_graph_api.py` `test_citations.py` `test_seed_idempotency.py` | Graph/Neo4j, ~slow |
| 5 | `change-set` | `test_change_set_api.py` `test_change_set_confirmation.py` `test_change_set_protection.py` `test_change_set_revision.py` `test_revisions.py` | API + repo, ~medium |
| 6 | `candidates` | `test_candidate_ingest.py` `test_candidate_review.py` | API + live Neo4j, ~medium |
| 7 | `auth` | `test_auth.py` `test_google_verifier.py` `test_session_repository.py` `test_settings_api.py` | auth + middleware, ~medium |
| 8 | `user-content` | `test_user_content_api.py` `test_user_content_repository.py` | API + repo, ~medium |
| 9 | `chat-llm` | `test_chat_api.py` `test_chat_persistence.py` `test_retrieval_pipeline.py` `test_retrieval_tools.py` `test_prompt_injection.py` `test_llm_provider.py` | chat/LLM, ~slow |
| 10 | `contract-ops` | `test_frontend_contract_doc.py` `test_openapi_contract.py` `test_share_api.py` `test_error_handlers.py` `test_rate_limit.py` | contract/doc, ~medium |

Run chunks in parallel only when every worker uses an **isolated Neo4j** that
cannot race with another worker (for example, separately isolated CI service
instances). Never parallelize these chunks against a shared AuraDB. With a
shared database, run chunks sequentially and use `--chunk <name>` for targeted
diagnosis; failure-detection time is workload-dependent and is not guaranteed.

**Measured 2026-08-10 (suite-time pass, commit a56b52f + docs/PROBLEMS.md
SEVENTH PASS):** the full suite is ~40 minutes serial against the shared live
AuraDB (down from 75+). A parallel batch of 8 non-seed chunks (2,3,5,6,7,8,9,10)
was killed after 25+ minutes without completing — still slower than serial, so
the durable guidance stands: against shared AuraDB run single chunks
(`--chunk <name>`) sequentially; parallel is only useful with isolated Neo4j
instances. The graph chunk alone is ~15 min (per-test re-seed is required for
isolation — module-scoped clients broke cookie/get_database state), and the
sub-8-minute target requires local docker Neo4j (`scripts/env-local.sh`).

**Environment pitfall (why agents historically "could not run" the suite):**
the Hermes terminal exports `PYTHONPATH` pointing at the hermes-agent
package dir, which shadows the venv and breaks `import spoilerless` (and
`backend`-root imports). Always run with `PYTHONPATH` unset:

```powershell
$env:PYTHONPATH = ""   # PowerShell — then run the commands above
```

The suite runs against the shared live AuraDB instance (root `.env` →
`NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io`); scratch-series
isolation + teardown in `conftest.py` protects `series_dexter`, and the CI
DB-pollution gate asserts zero residue after the run.
