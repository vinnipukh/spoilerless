# Local docker Neo4j — fast backend-test loop

Fast alternative to AuraDB for non-change-set files. Full suite ~2m wall vs ~40m
serial AuraDB (EIGHTH PASS, docs/PROBLEMS.md). AuraDB stays the canonical green
target; local 5.x has documented failure classes below.

## Boot sequence (after reboot / Docker Desktop not running)

1. Launch Docker Desktop headless. Do NOT use nohup/disown/trailing `&` — Hermes
   blocks shell background wrappers; use `terminal(background=true)`:
   `"/c/Program Files/Docker/Docker/Docker Desktop.exe"`
2. Wait ~40s for the engine, then start the DB container — it EXITS (255) when
   Docker Desktop shuts down and does NOT auto-restart:
   `docker start hdgraf-neo4j` (image neo4j:5-community, port 7687, creds per
   scripts/env-local.sh)
3. Run tests:
   `source scripts/env-local.sh && unset PYTHONPATH && uv run --project spoilerless pytest spoilerless/tests/test_graph_api.py -q`
   - `unset PYTHONPATH` required (hermes terminal shadows the venv)
   - `--project spoilerless` required — pyproject.toml lives in spoilerless/,
     repo root has none

## Expected pre-existing failures on local 5.x — DO NOT chase

- `TestSeedImageCuration` + `test_graph_nodes_include_image_fields` — seed data
  has zero `image_url` values; image-field assertions cannot pass locally.
- change-set family 503s (test_change_set_*) — local 5.x Cypher/constraint gap,
  untriaged (EIGHTH PASS); same code passes on AuraDB. Iterate non-change-set
  files locally only.
- 3 doc-contract failures (frontend_contract_doc + 2x openapi_contract) — fail
  on HEAD too; docs mid-update.

## PROBLEMS.md-ledger workflow (PROB-09 passes)

- Verify EVERY finding against live source before fixing; reproduce with own
  tools first (e.g. `.venv/Scripts/python.exe -c "import spoilerless.app.retrieval.pipeline as p; ..."`).
- PROBLEMS.md early passes cite stale `backend/app/...` paths — code lives at
  `spoilerless/app/...` since the 09-01 rename; read the newest pass's paths.
- Commit atomically per finding; append the pass to docs/PROBLEMS.md.
- Unit-test pattern for private API helpers without a DB: stub service/progress
  deps with async fakes + `types.SimpleNamespace` records and drive the helper
  via `asyncio.run(...)` — see test_graph_api.py `_run_resolve` (PROB-09/#59).

## Windows host pitfall

- `search_files` may fail on this repo with a Turkish-locale IO error
  ("Sistem belirtilen yolu bulamıyor", os error 3) while terminal ls/grep works
  on the same path — fall back to terminal grep for content searches.
  Host-specific; re-test if the locale or rg changes.
