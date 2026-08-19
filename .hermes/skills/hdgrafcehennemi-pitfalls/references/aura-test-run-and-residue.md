# Backend test runs on live AuraDB — runner, residue, seed audit

Measured 2026-08-05. Suite: 45 test files in `spoilerless/tests`, split into
**10 named chunks** (complete partition, verified 0 missing / 0 dupes) in
`scripts/run_backend_tests.py`. Chunks run against the SHARED live AuraDB
(root `.env`: `NEO4J_URI=neo4j+s://03a8623b.databases.neo4j.io`).

## Running the suite
- `uv run python scripts/run_backend_tests.py --list` — chunk→file mapping
- `... --chunk core` / `--chunk 7` / `--chunk auth,graph` — bounded per-area runs
- `... --parallel` — launches all selected chunks as concurrent pytest processes
- The runner strips `PYTHONPATH` itself (hermes-terminal shadow), so it works
  regardless of the ambient shell.

## Parallel on live AuraDB is counterproductive (measured)
10 concurrent chunk processes exceeded **27 minutes without completing** — slower
than the serial run (15–20 min). 10 driver pools contend on the free instance's
connection budget (plus production traffic) and the suite thrashes. Parallel only
pays off against an **isolated** Neo4j: the CI job's ephemeral docker container,
or local docker via `source scripts/env-local.sh` (Docker Desktop must be running).
Against live Aura, use single chunks for agent verification.

## Never run two pytest processes against Aura concurrently
A full-suite baseline overlapping a chunk run produced non-deterministic
ChangeSet residue on `series_dexter` → the seed audit failed on whichever run
re-seeded first. Tests are written serial-safe against the shared DB; they are
NOT cross-process safe.

## Seed integrity audit — ChangeSet exclusion (2026-08-05)
`seed.py::audit_visibility_integrity` matches ALL nodes under the seeded series
with null `visible_from_order`, excluding `UserSeriesProgress`, `ChatSession`,
and (since 2026-08-05) `ChangeSet`. ChangeSet nodes NEVER carry
`visible_from_order` by domain contract (`domain/change_set.py`) — the audit
previously failed on any real user ChangeSet on `series_dexter`, breaking
`setup_database` and `test_setup_schema_check.py`. Fixed by adding
`AND NOT node:ChangeSet`.

If you see `Seed integrity audit failed: ... ChangeSet (<uuid>)` it is test
residue or a legit user ChangeSet — NOT story drift. Do not "fix" story nodes.

## Residue classes + cleanup (run before re-verifying)
- Scratch-series nodes are keyed by `id` (`series_scratch_candidates`, ...),
  NOT a `series_id` property — conftest teardown
  (`MATCH (n {series_id: $series_id}) DETACH DELETE n`) never catches them.
- `origin='candidate'` nodes are global residue.
- Killed/interrupted runs (and parallel contention) leave both classes behind;
  the seed audit then trips on residue.

Cleanup (matches the documented teardown classes; read-only-safe):
```cypher
MATCH (n) WHERE n.origin = 'candidate'
  OR n.series_id STARTS WITH 'series_scratch'
  OR n.id STARTS WITH 'series_scratch'
DETACH DELETE n
```
Then confirm zero residue before re-running. NEVER delete `:AppSetting`/`:Session`
(backup→restore only) or real dev user rows (`user:ae8a41b7-...`).

## Settings-construction drift pattern
`Settings` requires `neo4j_uri`/`neo4j_username`/`neo4j_password`
(`AliasChoices("aura_*", "NEO4J_*")`, no defaults). `Settings(_env_file=None)`
without creds → pydantic `ValidationError`. Unit tests must use a helper with
dummy creds — pattern: `test_database.py::_settings` and `test_config.py::_settings`
(`_env_file=None, neo4j_uri="bolt://localhost:7687", neo4j_username="u",
neo4j_password="p"`).

## Frontend: episode-cluster area expansion (2026-08-05)
Ep-1 band gets ~3× the layout area: `graphElements.ts` stamps `areaScale: 3` on
the `'Ep #1'` parent element; `graphStylesheet.ts` adds
`node[areaScale = 3] { padding: '300px' }` — compound-node padding grows the box
~1.73× linear ≈ 3× area for a ~700px cluster. The rule is declared AFTER
`node[isCluster]` (equal specificity) so it wins for the Ep-1 parent.
