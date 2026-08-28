# Backend tests, live-DB hygiene & graph conventions (2026-08-05/06)

## Running the backend suite (agent-safe)
- Canonical: `uv run python scripts/run_backend_tests.py` — 10 named chunks
  (complete 45-file partition, verified no miss/dupe). It strips the hermes
  terminal `PYTHONPATH` shadow itself. `--list` shows chunk→file mapping;
  `--chunk core|auth|graph|...` runs one; `--parallel` launches all at once.
- Per-file fallback: `unset PYTHONPATH && .venv/Scripts/python.exe -m pytest
  spoilerless/tests/test_X.py -x` from the repo root. conftest inserts both
  `spoilerless/` and the repo root into `sys.path`.
- Full sequential suite vs live AuraDB: 15–20 min. `--parallel` against the
  SHARED live instance is WORSE (measured: >27 min without finishing, killed)
  — 10 driver pools contend on the Aura Free connection budget plus prod
  traffic. Parallelism only pays off against isolated Neo4j: the CI job's
  ephemeral docker container, or local docker via
  `source scripts/env-local.sh` (Docker Desktop must be running; local docker
  is NOT up by default).

## Shared live AuraDB — concurrency rule
- NEVER run two pytest processes concurrently against the live instance.
  One process's teardown deletes `origin='candidate'` nodes GLOBALLY while
  another is mid-test → the second's in-flight data vanishes → flaky
  failures. ChangeSet residue (null `visible_from_order`, by contract)
  additionally trips the seed audit in `setup_database`.
- After any interrupted/killed run, sweep residue:
  `MATCH (n) WHERE n.origin='candidate' OR n.series_id STARTS WITH
  'series_scratch' OR n.id STARTS WITH 'series_scratch' DETACH DELETE n`
  plus `UserSeriesProgress` rows carrying scratch series_id.
- GOTCHA: scratch Series nodes are MERGEd with `id='series_scratch_*'` but
  NO `series_id` property — conftest's teardown
  (`MATCH (n {series_id: $series_id})`) MISSES them. Any cleanup must also
  match `n.id STARTS WITH 'series_scratch'`.

## Seed integrity audit (`seed.py::audit_visibility_integrity`)
- Flags ANY node under the seeded series with `visible_from_order IS NULL`,
  excluding `UserSeriesProgress`, `ChatSession`, and — since 2026-08-05 —
  `ChangeSet`. ChangeSet nodes NEVER carry `visible_from_order` (domain
  contract, `app/domain/change_set.py`); a real user ChangeSet on
  series_dexter used to break `spoilerless-setup` and
  `test_visibility_schema_check_passes_on_fresh_seed`.
- Debug pattern: that test failing inside a chunk but passing alone = a
  concurrent process left residue, NOT a regression.

## Settings drift (`app/core/config.py`)
- `neo4j_uri/username/password` are REQUIRED (no defaults; aliases
  `aura_*/NEO4J_*`). Any `Settings(_env_file=None)` construction must supply
  dummy creds — copy the `_settings()` helper from `tests/test_database.py`
  (bolt://localhost:7687 / u / p). `test_config.py` was fixed this way
  2026-08-05 after the env-consolidation commit made the fields required.

## Frontend graph conventions (graphElements / layoutConfig / graphStylesheet)
- Cluster parents derived per node: `subplot`/`cluster` tag, else
  `Ep #N` from `visible_from_order`, else `Main`.
- Cluster-area control: stamp a data flag on the parent element (e.g.
  `areaScale: 3` for the `Ep #1` band), then style
  `node[areaScale = 3] { padding: 300px }` — compound-node padding grows the
  box on all sides; ~300px ≈ 3× the area of a typical episode cluster
  (√3 ≈ 1.73 linear). Declare AFTER `node[isCluster]` (equal specificity,
  later wins).
- Isolated-node pruning (08-06): `graphToElements` drops nodes with zero
  edges in the backend-filtered edge list, and drops clusters left empty.
  Pure topology over the already-filtered lists (D-16 safe — never filter by
  `visible_from_order` client-side; the backend is the visibility authority).
- "2.5cm clearance" ≈ 95px at 96dpi. fcose has no hard min-gap param, so the
  gap is enforced via constants (all three layouts bumped 2026-08-06):
  fcose `nodeRepulsion` parent 450000 / leaf 220000, `idealEdgeLength` 320,
  `gravity` 0.04. Tune the constants if the live graph reads tight/loose.
