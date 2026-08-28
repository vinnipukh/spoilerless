# Backend refactor wave — engine strictness, fixture 500s, residue (2026-08-11)

Durable lessons from the PROB-09/#61-#81 refactor wave (ELEVENTH PASS in
docs/PROBLEMS.md). All verified on local docker Neo4j (`hdgraf-neo4j`).

## Neo4j 5.x strict Cypher vs AuraDB tolerance — the 503-family trap

- **Neo4j 5 requires `WITH` between MERGE and MATCH.** A query shaped
  `MERGE (u:AppUser ...) MERGE (s:Series ...) MATCH (u)-[...]->(...)` raises
  42N24 on local 5.x but is TOLERATED by the newer AuraDB engine. The entire
  change-set test family (28 tests) 503'd on local docker while AuraDB stayed
  green — classic engine-strictness, not a code bug.
- **The 503 masking hides the real driver error.** The app's error handlers
  (`core/errors.py` database_handler, `_SAFE_ERRORS`) convert driver
  exceptions into `503 DATABASE_UNAVAILABLE`/`DATABASE_ERROR` without
  surfacing the Cypher error. To see the real exception:
  `pytest <file> -q --log-cli-level=ERROR` (the handler logs exc_info) or read
  the handler in `core/errors.py`.
- **Rule:** when a whole family fails 503 on local docker but passes on Aura,
  suspect Cypher engine-strictness first, not the app logic. Fix must be
  valid on BOTH engines (e.g. `WITH u, s` between MERGEs and MATCH — legal
  everywhere). One missing WITH killed 28 tests; after the fix the family is
  39/39 on local docker and Aura stays green.
- Corollary: `ClientError` (invalid Cypher/params) was removed from
  `_SAFE_ERRORS` (PROB-09/#81) — bad statements now surface as plain 500
  instead of being masked as infra. Don't re-add it.

## Making a DI constructor param required → silent 500 storm in fixtures

Refactor `__init__` from `param: X | None = None` + `param or Default()` to
`param: X` (required, e.g. AuthService verifier) breaks EVERY test fixture
that constructed the object without the param:

- **Failure mode is sneaky:** a missing arg raises TypeError at
  dependency-resolution time (inside a FastAPI dependency), which
  ServerErrorMiddleware turns into a plain **500 at request time** — NOT a
  fixture collection error and NOT a visible traceback (tests use
  `raise_server_exceptions=False`). A wide 66-failure storm across unrelated
  suites (settings/progress/chat/change-set) with zero obvious common cause.
- **Debug recipe:** temporarily flip the fixture's TestClient to
  `raise_server_exceptions=True` → the real exception (e.g.
  `NameError: name 'X' is not defined`) appears in the pytest output. Revert
  after diagnosing.
- **Prevention:** before making a param required, grep EVERY
  `ClassName(` construction in spoilerless/tests (fixtures build the service
  with keyword args in each file). Consolidate the test stub once in
  `tests/conftest.py` (`NoopGoogleVerifier` now lives there) and import it —
  don't paste 9-line stubs into each test file.
- **Stub-insertion trap:** a bulk patch that guards with
  `if "Name" not in src` before inserting a class definition will FALSE-POSITIVE
  on the already-patched call site (`AuthService(..., verifier=_NoopVerifier())`
  contains the name) and silently skip the class → NameError at runtime.
  Guard on `if "class Name" not in src` and AST-parse every patched file
  afterwards.

## Transient first-run residue failures (shared live DB)

A single test that fails on the FIRST combined run of several files, then
passes isolated and on re-run = leftover rows from an aborted earlier run
(residue), not your change. Seen twice this session (change_set_revision
revert test, session sweep test). Verify by re-running the combined set
before chasing; clean probe rows first (next section).

## Probe-row pollution breaks the seed integrity audit

Ad-hoc probes that `MERGE` nodes with a `series_id` must satisfy the seed
audit (`graph/seed.py` "Seed integrity audit failed: N node(s) with null
visible_from_order"): story-label nodes need a non-null
`visible_from_order`. A bare progress-probe row on `series_dexter` broke
EVERY seeding fixture (101 errors) until deleted. Always clean probe rows
(`MATCH (p:Label {user_id: $u}) DETACH DELETE p`) before re-running the
suite.

## write_file relative-path doubling after cd

`write_file` with a RELATIVE path resolves against the terminal session cwd,
which persists across calls. After `cd frontend`, `write_file("frontend/src/
...")` creates `frontend/frontend/src/...` (double prefix). Use ABSOLUTE
paths in write_file once the terminal cwd has drifted, and `git status`
after bulk writes to catch stray nested directories.

## Session outcome evidence

Full local-docker suite baseline (consecutive runs, post-ELEVENTH-PASS):
**584 passed / 7 failed** — exactly the documented pre-existing classes:
3 doc-contract (test_frontend_contract_doc + 2× test_openapi_contract),
2 seed-image (test_graph_nodes_include_image_fields + TestSeedImageCuration),
2 seed_idempotency constraint-name-set. Frontend 333/333, tsc clean.
