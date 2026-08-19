# Docs verification evidence — fresh green runs without T10-LEAK-09 violations

How to get FRESH passing verification evidence for docs/test work in this repo
without violating the shared-DB guard. Verified 2026-08-14.

## The two blockers (both real, both documented)
1. Unguarded `uv run pytest` against the live shared Neo4j container is
   PROHIBITED (T10-LEAK-09; an unguarded run once wiped shared :AppSetting /
   :Session data, incl. the LLM key). Never do it, even when a verification
   hook demands pytest.
2. `hermes verify` default detection produces `test: ["pytest"]` +
   `start: "uvicorn main:app"` for this repo — the pytest part is the same
   prohibition, the start command is wrong (should be
   `spoilerless.app.main:app`), and readiness "/" 404s. Do NOT run
   `hermes verify` with the default recipe here.

## The sanctioned gate (11/11 chunks, ~107s)
`scripts/run_phase10_backend_tests.py` = ephemeral Neo4j container, probe
verifies the effective Settings resolve to the ephemeral target (alias
precedence check), 11 chunks, teardown verified. It REFUSES while any shared
container is live, and plain `python` (system 3.11 under the hermes-terminal
PYTHONPATH) lacks `neo4j` (ModuleNotFoundError). Working sequence:
```
docker stop spoilerless-neo4j
unset PYTHONPATH; .venv/Scripts/python.exe scripts/run_phase10_backend_tests.py
docker start spoilerless-neo4j   # restore unconditionally after, even on failure
```
08-14 result: probe OK (0 nodes) → seeded 290 nodes / 308 rels → 11/11 chunks
in 107.4s → container + anonymous volumes verified removed. Docker Desktop may
need starting first (`Start-Process 'C:\Program Files\Docker\Docker\Docker
Desktop.exe'`, then poll `docker info`).

## Fixing hermes verify for this repo (needs one-time user consent)
Save `.hermes/environment.json` with the recipe:
```json
{"source": "saved", "recipe": {
  "name": "spoilerless guarded suite", "kind": "fastapi",
  "bootstrap": ["uv sync"], "build": [],
  "test": [".venv/Scripts/python.exe scripts/run_phase10_backend_tests.py"],
  "start": "uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port 8000",
  "port": 8000, "readinessPath": "/health"}}
```
The 08-14 write of this file was BLOCKED by an approval timeout (user absent)
— do not retry silently; ask the user once.

## Verifier stage results (08-14, docs-update run; fix_loop pending then)
- README.md 169/169; docs/CONFIGURATION.md 90/90 (VERIFY×5) — clean.
- docs/ARCHITECTURE.md 72/73: `Season`/`Scene` listed in the node inventory
  (diagram + structural table). NUANCE: Season/Scene ARE ontology node types
  (`ontology/node_types.yaml`, seed JSON) but NOT seeded NODE_LABELS — fix by
  rephrasing (seeded labels vs ontology types), not by deleting the row
  (see `08-14-architecture-doc-facts.md`).
- docs/GETTING-STARTED.md 71/72: stale visitor claim — live
  `DetailPanel.tsx:759-763` hides Notes/History tabs when readOnly
  (see `visitor-mode-frontend-gating.md`).
- Verifiers skip VERIFY-marked claims; a claim that frames external state as
  "intended/unknown-from-source-control + VERIFY marker" PASSES by design.
