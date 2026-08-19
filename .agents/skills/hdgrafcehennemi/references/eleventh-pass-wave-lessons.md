# ELEVENTH/TWELFTH PASS wave lessons (2026-08-11/12)

Durable pitfalls from the PROB-09 dedup wave (#61-#68, #72-#74, #77, #81,
#71) + the docs refresh. PROBLEMS.md ELEVENTH/TWELFTH PASS sections carry
the full commit-level record; this file is the reusable knowledge.

## Neo4j 5.x strict Cypher: WITH required between MERGE and MATCH
Local docker (neo4j:5-community) rejects `MERGE ... MERGE ... MATCH ...`
with 42N24 (`WITH is required between MERGE and MATCH`); the newer AuraDB
engine tolerates the omission. This was the EIGHTH-PASS 503 class: 28
change-set test failures on local docker that stayed green on Aura.
Fix pattern: insert `WITH <vars>` between the MERGEs and the following
MATCH — valid on both engines. When a query passes Aura but 503s on local
5.x, run the failing test with `--log-cli-level=ERROR` and read the real
driver error in the app's exception log (the 503 envelope masks it).

## Making a constructor parameter required breaks test fixtures silently
Changing `AuthService.__init__` params to required (no
`or InMemorySessionRepository()` / `or ProductionGoogleVerifier()`
fallbacks) turned every test fixture that built it with 2 args into a
dependency-resolution TypeError → ServerErrorMiddleware → 500. On the
full suite that surfaced as a 66-failure storm across unrelated files
(settings/progress/chat/change-set). Rules:
1. Before making a param required, grep the WHOLE tests tree for
   constructions without it (`grep -rn "AuthService(" spoilerless/tests`).
2. Shared no-op verifier lives in `tests/conftest.py` as
   `NoopGoogleVerifier`; import it, don't re-declare per file.

## Stub-insertion bug: presence check must match the DEFINITION
A script that inserts a stub class guarded by
`if "_NoopVerifier" not in src` silently skipped defining the class — the
call site had already been rewritten to `_NoopVerifier()` before the
check ran, so the substring matched and the class was never inserted →
`NameError` at dependency resolution. Rules:
- Check for `class _NoopVerifier` (the definition), not the bare name.
- After any generated edit, `ast.parse` every touched file and grep the
  definition line count; don't trust the writer's success message.

## Probe rows on the shared live DB poison the seed audit
Writing probe rows with a REAL series id (`series_dexter`) and no
`visible_from_order` (e.g. `MERGE (p:Progress {series_id:'series_dexter'})`)
breaks `seed.py`'s integrity audit (`ValueError: ... null visible_from_order`)
for EVERY later test run — 101 fixture errors until the rows are deleted.
Rules: probes on the shared local docker Neo4j must (a) use throwaway
ids (`probe-user-123`) and (b) be deleted immediately after. Same rule
as the scratch-series teardown discipline for tests.

## Transient combined-run residue vs real regressions
A test that fails in a combined run but passes isolated is usually
residue from a previous aborted run (leftover rows on the shared DB),
not a code regression. Re-run the combined set before chasing; two
consecutive green combined runs = clean.

## Baseline is 584 passed / 7 failed (local docker)
3 doc-contract (`test_frontend_contract_doc`, `test_openapi_contract` ×2 —
the openapi tests still assert the old 45-op contract while the live
surface is 50 ops / 37 templates; red by policy), 2 seed-image, 2
seed_idempotency constraint-name. Anything else = regression.

## Docs refresh (gsd-docs-update) specifics
- `docs-init` has_api_routes is a false negative for Python/FastAPI
  projects — codebase-discover `docs/API.md` anyway.
- Dispatch writers with the role file path FIRST
  (`C:/Users/arhan/AppData/Local/hermes/agents/gsd-doc-writer.md`) —
  it is self-contained (mode + template sections).
- Every `.planning/tmp/docs-work-manifest.json` edit re-triggers the
  verification gate → batch manifest updates with the wave completion,
  or expect a full-suite re-run per wave.
- Writers reliably catch stale claims: SYSTEM_PROMPT_VERSION (deleted),
  `--project spoilerless` seed forms, AuthService fallback wording,
  NODE_LABELS location. Feed them the session's refactor list in
  project_context; they verify against source.
