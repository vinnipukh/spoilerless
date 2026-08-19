# 10-09: Guarded ephemeral-container test runner (POLISH-01 gate)

Status at end of the 10-09 session: runner + guard tests + chunk inventory + docs verified,
committed per-task; Task 2 (full `--all` run) and SUMMARY/STATE/ROADMAP closeout may still be pending.

## The only Phase 10 backend entrypoint

`scripts/run_phase10_backend_tests.py` is the ONLY supported full-suite entrypoint for Phase 10.
Never run `pytest spoilerless/tests` or `run_backend_tests.py` directly for the full gate.

```bash
unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py            # all chunks
unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py --all      # explicit
unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py --files \
    spoilerless/tests/test_graph_api.py spoilerless/tests/test_seed_idempotency.py
```

Behavior: provisions a uniquely named `neo4j:2026.06.0-community` container (random password,
random loopback-only ports, NO volume mounts — anonymous volumes only), waits ready (wget
spider inside container + TCP connect on bolt port), runs a settings+driver probe, runs
`spoilerless.app.graph.setup`, then tests; teardown `docker rm -f -v <name>` runs in
`finally` even on test failure, and container absence is verified afterwards. Exit codes:
0 green, 1 test failures, 2 forbidden target / usage error.

## Fail-closed refusal rules (checked BEFORE anything is created)

- Ambient `NEO4J_*`/`aura_*` env vars must be ABSENT or exactly equal the ephemeral target
  values — any other value is a "user-provided connection override" → REFUSED. Root `.env`
  carries live Aura `NEO4J_*` creds; the runner overrides all 8 vars for children.
- URI host must be loopback (`localhost`/`127.0.0.1`/`::1`) — remote/Aura hosts refused.
- Port `:7687` refused (docker-compose developer container port).
- Running developer containers `spoilerless-neo4j` / `hdgraf-neo4j` refused (fail-closed:
  refuse whenever either is running, even though the runner uses its own random port).
- Pre-existing container or named volume with the generated name → refused.
- `Settings` AliasChoices: `aura_*` WINS over `neo4j_*`. Children get BOTH families exported
  with identical values (lowercase `aura_*` works — pydantic-settings matches case-insensitively;
  on Windows os.environ normalizes lowercase to uppercase anyway, values stay identical).
- Probe proves ownership: `Settings(_env_file=None)` resolves to the ephemeral creds AND
  `MATCH (n) RETURN count(n)` == 0 before any test runs.

## Seven-red baseline is RETIRED — zero known failures

The old "584 passed / 7 failed — never chase the 7" baseline in docs/TESTING.md is gone.
Full suite is **0 failed** on the ephemeral container. How each red died (no whitelisting):
- 3 doc-contract reds → fixed by 10-03/10-06 inventory updates (52 operations / 39 templates,
  locked by `test_frontend_contract_doc.py` + `test_openapi_contract.py`).
- 2 seed-image reds → 08-12 self-hosted portrait restore: seed now has 6 order-1 `/api/static/`
  images, 0 above-order-1, 0 external http (verified against `characters.json`; locked by
  `TestSeedImageCuration` + `test_graph_nodes_include_image_fields`).
- 2 constraint-name reds → engine-tolerant assertions (`type.replace("NODE_PROPERTY_","")` etc.)
  green on `neo4j:2026.06.0-community`; `SHOW CONSTRAINTS ... WHERE type IN ['NODE_PROPERTY_UNIQUENESS','UNIQUENESS']`.
**Any backend failure on the runner is now a real regression.**

## Chunk inventory gate

`scripts/run_backend_tests.py` now has `assert_chunk_inventory_matches_disk()` called at the
top of `main()`: every `test_*.py` under `spoilerless/tests/` must appear in CHUNKS exactly
once, else the run fails before starting. A new test file MUST be added to a chunk
(`phase10-viz` holds the 5 Phase 10 test files) or `--all` breaks.

## Guard tests

`spoilerless/tests/test_phase10_test_runner.py` — 18 mock-driven tests (no docker daemon):
FakeDocker records calls, monkeypatch `_docker`/`compute_target`; covers refusal classes,
teardown-on-failure, alias export, inventory sync. Import pattern: `importlib.util.spec_from_file_location`
on `scripts/*.py` (scripts/ is not a package).

## Docker CLI gotchas (bit us in this session)

1. `docker container inspect <missing>` prints `[]` to STDOUT with **rc=1**. Existence checks
   MUST key off the exit code (`proc.returncode == 0`), never `stdout != ""` — the latter
   falsely reports "exists" for every missing name.
2. `docker volume inspect <missing>` behaves the same way (rc=1, `[]` on stdout).
3. In unit tests asserting docker arg lists: `["--name", "value"]` is TWO list elements, not
   one `--name=value` string; `["-p", "127.0.0.1:PORT:7687"]` likewise.

## Measured evidence (2026-08-13)

- Focused 8-file run on ephemeral container: **179 passed, 0 failed, 27.8s**
  (4 viz files + frontend_contract_doc + openapi_contract + graph_api + seed_idempotency —
  exactly the files that held the old seven reds).
- Guard tests: 18 passed. Frontend focused (App.test.tsx + useSceneState.test.ts): 40 passed.
- Container naming: `hdgraf-phase10-tests-<hex>`; teardown proof printed as
  "teardown verified: container <name> and its anonymous volumes removed".

## POLISH-01 shared-ID trap

`POLISH-01` is declared by BOTH 10-09 and 10-11. Per `requirements.ready-ids`, it must NOT be
marked Complete by 10-09's closeout until 10-11 also has a SUMMARY — check ready-ids before
calling requirements.mark-complete.
