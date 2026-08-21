# Runbook — incident detection, diagnosis, rollback (carry-over 09-08)

Executable by a future operator. No dashboards platform wiring — this is the
procedure, with concrete Cypher checks, exact live-DB counts, and thresholds
that distinguish failure classes. Run every Cypher block against the live
AuraDB (see §2 env preamble); re-run counts at incident time — all numbers
below are snapshots or threshold rules, never guarantees.

## 1. Incident detection

- **External uptime monitor: PLANNED, NOT yet configured.** DEPLOYMENT.md
  records an UptimeRobot (or equivalent) monitor on
  `https://api.spoilerless.net/health` (5-min interval, alert on non-200 or
  timeout) as human-provisioned; no monitor configuration is tracked in the
  repo. Until an operator provisions it, detect outages manually:
  `curl -s -o /dev/null -w "%{http_code}" https://api.spoilerless.net/health`
  — anything other than `200` = outage (503 below means app-up/DB-down).
- `/health` has exactly two live tuples (locked by `spoilerless/app/main.py`
  and `test_main_lifespan.py`):
  - HTTP 200 `{"status":"ok", "database":"connected", "service":"spoilerless-backend"}`
    — healthy. `status:"ok"` is NEVER paired with an unavailable database.
  - HTTP 503 `{"status":"degraded", "database":"unavailable", ...}` — the app
    process is UP and serving `/health`; only the Neo4j connection failed.
    `status:"degraded"` therefore does NOT mean the app itself is failing.
- Chat stream failures: the backend SSE route (`spoilerless/app/api/chat.py`)
  emits `LLM_PROVIDER_UNAVAILABLE` and `LLM_STREAM_FAILED` as structured
  `event: error` payload codes (09-06) — they are NOT logged to the browser
  console (ChatPanel classifies them into UI error states). Server logs do
  NOT contain those code strings; grep the actual log messages instead (see
  the §2 grep recipe), which do carry the exception class in the generic
  branch.

## 2. Diagnosis ladder

Run from the repo root with the live AuraDB env (root `.env`, never commit
it). Override per-run; do not edit `.env`. Aura one-shot commands MUST set
`NEO4J_DATABASE` too — `zombie_sweep.py` and scripts default it to `neo4j`,
which is the docker-local name and can select a wrong/nonexistent Aura
database:

```bash
unset PYTHONPATH
NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io NEO4J_USERNAME=<dbid> \
NEO4J_PASSWORD=<credential> NEO4J_DATABASE=<dbid> \
  uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --dry-run
```

| Symptom | Check (executable) | Counts that mean "this class" |
|---|---|---|
| Chat dead / streaming hangs | `MATCH (c:ChatSession) RETURN count(c)`; `MATCH (m:ChatMessage) RETURN count(m)`; orphaned: `MATCH (m:ChatMessage) WHERE NOT EXISTS { (:ChatSession)-[:HAS_MESSAGE]->(m) } RETURN count(m)` | Any orphaned `ChatMessage` (no `HAS_MESSAGE` owner) = this class; zero sessions while messages exist = ownership path broken (`AppUser-[:HAS_CHAT_SESSION]->ChatSession-[:HAS_MESSAGE]->ChatMessage`) |
| Graph wrong at boundary N | `MATCH (n) WHERE n.series_id = 'series_dexter' AND (n:Character OR n:Event OR n:Location OR n:Organization OR n:Object OR n:Claim OR n:EvidenceFragment OR n:Source) AND n.visible_from_order IS NULL RETURN labels(n)[0] AS label, count(*) AS n` | 0 rows = clean; any row = seed drift — `setup_database`'s seed-integrity audit fails on such nodes. NOTE: the 09-08 startup schema check covers `visible_from_order` on story labels ONLY — `Episode` is excluded, and `synopsis_visible_from_order` / `image_visible_from_order` are NOT validated at setup; check them manually: `MATCH (e:Episode) WHERE e.series_id = 'series_dexter' AND (e.synopsis_visible_from_order IS NULL OR e.image_visible_from_order IS NULL) RETURN e.code` (0 rows expected) |
| Slow login / 401 storms | `MATCH (u:AppUser) RETURN count(u)`; then the sweep's zombie count (dry-run above, no mutation) | Thousands of `:AppUser` with no ownership ties = this class (PROB-22/#46: ~3,855 on Aura, 2026-08-04 snapshot — re-count live); zero AppUser rows + 401s = auth allowlist/verifier misconfig, not zombies |
| LLM 429s | `grep -c '^REDIS_URL=' .env` → 0, or Render dashboard env | `REDIS_URL` unset = rate limiting inactive (fail-open = unthrottled, not a crash — and no 429s should be emitted); `REDIS_URL` set = check `hdgraf:rate_limit:*` bucket state in the Redis console |

Structured-log grep points (Render logs) — the server messages do NOT embed
the SSE codes, so grep the message text; the generic branch interpolates the
exception class name:

```bash
grep -E "Chat stream provider failure|Chat stream failed mid-turn" <log>
grep -E "Chat stream failed mid-turn.*[A-Z][A-Za-z]+Error" <log>   # class name, generic branch only
```

## 3. Rollback procedure

1. **Backend (Render):** redeploy the previous deploy (Render dashboard →
   service → Deploys → "Redeploy" on last known-good).
2. **Frontend (Vercel):** Production → Instant Rollback to the previous
   deployment.
3. **Graph:** the graph is the source of truth. `uv run --project
   spoilerless python -m spoilerless.app.graph.setup` (MERGE-based, preserves
   user content) restores canonical seed rows — but it is NOT the complete or
   exclusive recovery for every bad-reseed class: it does not remove extra
   seeded-series nodes or candidate-test pollution (PROBLEMS.md), and it has
   NO dry-run CLI (it immediately creates constraints/indexes, upserts seeds,
   deletes stale relationships, and audits). Treat it as mutating: require
   operator sign-off before running, pair it with targeted cleanup for
   pollution classes, e.g.
   `MATCH (n {series_id: $sid}) DETACH DELETE n` for scratch/candidate
   series. The dry-run-gated command is `zombie_sweep --dry-run`, NOT setup.
4. **Cache (Upstash Redis):** the graph-response cache lives under
   `graph:{series_id}:{effective_boundary}:{user-id-or-anon}` keys (written
   by `spoilerless/app/cache/graph_cache.py`); invalidation scans
   `graph:{series_id}:*`. There is NO `spoilerless:*` namespace — flushing
   that pattern clears nothing. Flush `graph:*` (or the affected
   `graph:{series_id}:*`) in the Upstash console if a bad write path cached
   stale graph responses (09-06 write-path invalidation should prevent this;
   flush is the escape hatch). Rate-limit buckets live under
   `hdgraf:rate_limit:*` and are separate — leave them unless resetting
   limits.

## 4. On-call contact flow

1. Operator (repo owner) — GitHub notifications + Render/Vercel dashboards.
2. If operator unreachable: leave the previous deploy live, do NOT trigger
   the destructive reseed path without sign-off.
3. Record the incident in `docs/PROBLEMS.md` (canonical ledger) with the
   counts from §2 before fixing — every entry needs evidence.

## 5. Zombie sweep (PROB-22/#46)

```bash
# Dry-run FIRST (mandatory) — include the Aura env + NEO4J_DATABASE as in §2:
uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --dry-run
# Review counts, then:
uv run --project spoilerless python -m spoilerless.scripts.zombie_sweep --execute
```

HARD rules baked into the script: never deletes the protected dev user
(`ae8a41b7-db96-40e8-b6c2-2e3c69aedb11`); deletes only `:AppUser` rows with
no ownership ties and expired/revoked/orphaned `:Session` nodes.

Requires the modern driver TLS key: the script connects to Aura via
`trusted_certificates=TrustCustomCAs(certifi.where())` — the legacy `trust=`
driver key was removed in neo4j 6.2 and raises `ConfigurationError`
(fixed 2026-08-12, SEVENTEENTH PASS). If the dry-run fails with
`Unexpected config keys: trust`, update the venv driver first.

KNOWN LIMITATION (verify counts before `--execute`): the script's tie check
guards only `HAS_PROGRESS`, `HAS_SESSION`, `CREATED` (both directions), and
`REFERS_TO`. Live ownership edges also include `HAS_CHAT_SESSION`,
`PROPOSED_CHANGE_SET`, and `CREATED_SHARE` — a user holding ONLY those ties
still matches the delete query, and `DETACH DELETE` would orphan the owned
chat/change-set/share records. Until the script covers all ownership
relations (PROB-22 follow-up), inspect the dry-run count and spot-check for
those edges before executing:
`MATCH (u:AppUser) WHERE NOT (u)-[:HAS_PROGRESS|HAS_SESSION]->() AND NOT ()-[:CREATED]->(u) AND NOT (u)-[:CREATED|REFERS_TO]->() AND ((u)-[:HAS_CHAT_SESSION]->() OR (u)-[:PROPOSED_CHANGE_SET]->() OR ()-[:CREATED_SHARE]->(u)) RETURN u.id LIMIT 20`.


---

# Appendix: Backend Deploy Crash — Root Cause and Fix (2026-08-05)

> Folded in from docs/BACKEND_DEPLOY_FIX.md during the 2026-08-12 docs
> restructure (grouped layout) — one incident record, one runbook.

**Date:** 2026-08-05  
**Error:** `ModuleNotFoundError: No module named 'backend'`


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
CI. For targeted local diagnosis, the suite is split into **11 named chunks** —
every file in `spoilerless/tests/` appears in exactly one chunk. A chunk bounds
the test scope, but it has no enforced runtime limit; duration depends on the
selected files, Neo4j environment, network, and current load.

**Preferred entry point** — the chunk runner (strips the Hermes-terminal
`PYTHONPATH` that shadows the venv, so `import spoilerless` works):

```powershell
uv run python scripts/run_backend_tests.py          # all 11 chunks
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
| 7 | `auth` | `test_auth.py` `test_google_verifier.py` `test_session_repository.py` `test_settings_api.py` `test_security_boundary.py` | auth + middleware + boundary security, ~medium |
| 8 | `user-content` | `test_user_content_api.py` `test_user_content_repository.py` | API + repo, ~medium |
| 9 | `chat-llm` | `test_chat_api.py` `test_chat_persistence.py` `test_retrieval_pipeline.py` `test_retrieval_tools.py` `test_prompt_injection.py` `test_llm_provider.py` | chat/LLM, ~slow |
| 10 | `contract-ops` | `test_frontend_contract_doc.py` `test_openapi_contract.py` `test_share_api.py` `test_error_handlers.py` `test_rate_limit.py` `test_phase10_coverage_audit.py` | contract/doc, ~medium |
| 11 | `phase10-viz` | `test_visualization_baseline.py` `test_visualization_projection.py` `test_visualization_cache.py` `test_visualization_graphrag.py` `test_phase10_test_runner.py` | fixture/offline, ~fast |

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
isolation — module-scoped clients broke cookie/get_database state). Local
docker Neo4j (`scripts/env-local.sh` + the `aura_*` exports; correct container
is `spoilerless-neo4j` on 2026.06.0, NOT the stale `hdgraf-neo4j`
5-community) makes seeding ~4.6s — but the green full suite is still ~42 min
because the function-scoped `live_client` re-seeds per test (~10s/test). The
EIGHTH PASS "<8m (2:01)" figure was measured on the stale 5-community
container with 35 fast-failing tests — never a green-suite benchmark. Suite
speedup task is tracked in docs/ROADMAP.md §8 item 7 (Testing isolation).

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
