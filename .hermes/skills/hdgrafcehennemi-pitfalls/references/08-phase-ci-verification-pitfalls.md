# Phase 08 CI-Verification Pitfalls (08-04..08-07 sessions)

Durable lessons from running the phase-08 production-deployment plans and
watching the new GitHub Actions CI gate (08-07) surface pre-existing debt.

## 1. conftest.py `os.environ.setdefault` silently shadows .env

The 08-05 executor added this to `backend/tests/conftest.py`:

```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "hdgraf-local-password")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```

pydantic-settings (BaseSettings) reads **real env vars BEFORE the .env file**,
so a `setdefault` in conftest (imported before any test) permanently overrode
`.env`'s AuraDB connection string. Symptom: tests that passed minutes earlier
start connecting to `127.0.0.1:7687` with "connection refused" — and the `.env`
file looks correct the whole time.

Fix (committed `94ce675`): delete the setdefault block; provide
`scripts/env-local.sh` (exports localhost docker creds) for the sibling/local
docker workflow instead. `source scripts/env-local.sh` before local-docker test
runs; `.env` stays pointed at AuraDB permanently. Check conftest.py's top for
env-var setdefaults whenever the DB target "unexplainedly" flips.

## 2. Tests that pass against warm AuraDB fail on CI's fresh container

AuraDB holds data seeded weeks ago. When a later commit changes the seed
(D-14 curation, `871f72f`, removed future-character portraits) or adds tests
that leave residue, the shared DB can keep old behavior alive while the
committed seed files tell a different story:

- `test_graph_nodes_include_image_fields` asserted all 9 characters carry
  portraits — passed against AuraDB (old rows), failed on CI's fresh container
  because `characters.json` now deliberately has `image_url: None` for
  paul_bennett/rudy_cooper/harry_morgan (D-14: no future-character portraits).
- `test_graph_hidden_character_image_urls_never_serialized` asserted
  `Paul_Bennett_7.PNG` appears at boundary 2 — the D-14 rule means it never
  appears at any boundary.

**Lesson:** when a CI container fails seed/image tests that pass locally
against AuraDB, diff the committed seed data (`data/dexter/seed/*.json`) against
what the test asserts — the test is stale relative to the seed, not the seed
broken. Fix the test to match the locked curation rule. AuraDB as the only
verification target hides seed drift indefinitely.

## 3. Suite residue: candidate-origin nodes break seed-count tests in CI

`test_candidate_ingest.py` ingests claims/evidence/sources into `series_dexter`
and doesn't tear them down. `test_seed_idempotency.py` cleaned only
`origin = 'user'` / `user-`-prefixed nodes, so candidate-origin residue
(3 Claims + 3 EvidenceFragments + 2 Sources = 8 nodes) survived into the
`41/26` and `48/27` count assertions → failures. On shared AuraDB this looked
like "pre-existing pollution debt"; on CI's single shared container it's
**deterministic** (same suite, same order).

**Fix:** seed-count tests must also clear candidate residue before asserting:

```python
await live_database.execute_query(
    "MATCH (n) WHERE n.origin = 'candidate' DETACH DELETE n"
)
```

Add it to every seed test that asserts pristine counts (idempotency,
constraints/provenance, user-layer preservation).

## 4. `docker compose down -v` does NOT remove bind-mount data

`docker-compose.yml` mounts `./neo4j_data:/data` as a bind mount. `down -v`
removes named volumes only — bind mounts persist on the host. After the
sibling's graph-population runs, "fresh" containers still carry the old data
(49 nodes instead of 41) and tests keep failing. For a genuinely clean local
reproduction of CI:

```bash
docker compose stop neo4j
rm -rf neo4j_data neo4j_logs
docker compose up -d neo4j
```

(Delete the whole `neo4j_data` dir; `down -v` alone is insufficient.)

## 5. Render free tier + UptimeRobot = false "Down"

Render free Web Services sleep after ~15 min without inbound traffic; cold
start ~50s. UptimeRobot's default timeout is 30s, so a check hitting a sleeping
instance times out → monitor shows Down while the site works fine for humans
(who wake it). Also: a health endpoint returning 200 in 0.4s from curl does not
contradict the monitor — the check may land mid-cold-start.

Diagnosis: look for long silent gaps in Render logs followed by
"Starting process… Application startup complete" (sleep/wake cycles). Fixes:
paid instance ($7/mo), a keep-alive ping, or accept false alarms. Also verify
the monitor URL is exactly `/health` and no keyword check is set.

## 6. Upstash URL scheme: `redis://` vs `rediss://`

Upstash console shows `redis-cli --tls -u redis://default:...@host:6379`.
The app's Python client (`redis.asyncio.Redis.from_url`) needs **`rediss://`**
for TLS — a `redis://` URL connects without TLS and Upstash rejects it.
Set `REDIS_URL=rediss://default:<pw>@<host>:6379` on Render. The console's
REST vars (`UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN`) are for the
HTTP API and are NOT what the app reads.

## 7. CI lint gate: react-hooks v6 flat-recommended React-Compiler rules

`eslint.config.js` extends `reactHooks.configs.flat.recommended`, which in
v6+ includes React-Compiler-era rules (`react-hooks/set-state-in-effect`,
`react-hooks/refs`, `react-hooks/preserve-manual-memoization`,
`typescript-eslint/no-explicit-any`). A codebase written before those rules
accumulated ~30 errors — CI's `npm run lint` (08-07) surfaces them all at once
as pre-existing debt. Phase 9 SC#2 already owns "npm run lint = 0 errors".
When triaging: check whether the errors are pre-existing (git log the files)
before rewriting 7 files; the lint gate working as designed is a feature.

## 8. Redis cache-aside wiring: graph.py changes must be staged with the cache module

The 08-06 executor committed `graph_cache.py` (new module) with a commit
message mentioning api/graph.py changes — but only the new file was staged.
`get_cached_graph`/`set_cached_graph` calls in `get_graph` were left uncommitted
in the working tree (verification passed on the RED state only by luck).
**Lesson:** after any multi-file feature, verify `git show <sha> --stat` lists
EVERY intended file — a commit message describing a file does not mean it was
staged. The cache-aside read path was later re-committed as `623e4e6`.
