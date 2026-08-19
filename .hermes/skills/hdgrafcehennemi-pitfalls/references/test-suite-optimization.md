# HD Graf Test Suite Optimization (08-10, session 75min → ~15min serial)

Measured numbers that drive every decision:
- `setup_database()` full seed = **~10.3s**, `verify_connection` = **~1.2s**, `Neo4jDatabase.open()` = **~0s (lazy)**.
- Every `asyncio.run()` probe = fresh loop → fresh TLS handshake (~1s) per call.
- `test_chat_api` is the slowest file (~5.6 min alone): each message test runs the retrieval pipeline (5-10 AuraDB round trips). That cost is app design, not test overhead.

## Pattern: module-scoped seeded `live_client` (conftest.py)
A function-scoped fixture that re-seeds per test cost ~12s × N tests (graph_api was ~10 min alone). Seeding is idempotent (MERGE-based), graph tests are read-only → one module-scoped seed + client is equivalent and N× faster. Lives in `conftest.py` as `seed_live_database()` + module-scoped `live_client` fixture. `test_graph_api`/`test_episode_masking`/`test_api_series` use it; `candidate_*` keep local variants (scratch-series bootstrap around the client); `user_content_api` has its own `_seed_and_clean` variant — do NOT flatten those.

## Pattern: shared asyncio.Runner + one driver for probes (conftest `run_query`/`helper_db`/`run_async`)
Test-body DB probes used to spawn `Neo4jDatabase()` + `asyncio.run()` per call = a handshake per probe. Fix: module-level `asyncio.Runner` + shared `_HELPER_DB`; `run_query(query, **params)` runs on that one loop, so pooled connections stay bound → one handshake per suite. Convert helpers to SYNC defs (`async def _fresh_query` → `def _fresh_query` returning `run_query(...)`), and call sites `asyncio.run(_helper(...))` → `_helper(...)`.

Pitfalls:
- `asyncio.Runner.run()` **cannot be called from inside a running loop** (RuntimeError) — so async helpers that wrap `run_query` still break. Helpers must be sync.
- App-driver (TestClient portal loop) writes vs helper-driver reads: cross-driver read-after-write on AuraDB is not guaranteed. If probes miss right after an app write, the cause is usually **residue** (see next), but keep probe reads on the helper driver only after the app's transaction is fully visible — don't over-retry; fix residue instead.
- Blanket `asyncio.run(X(` → `X(` replace leaves double parens (`asyncio.run(_loc(x))` → `_loc(x))`). Use a quote-aware paren matcher, or fix by hand. Multi-line `asyncio.run(\n _fresh_query(` is NOT caught by single-line replace_all.
- Blanket `async def _` → `def _` is safe only when every async helper is a DB probe. In `test_chat_api`/`test_progress_api`, service-wrapping helpers (`_simulate_disconnect` → `ChatService(...)`, `ProgressRepository` flows) convert via `run_async(coro_factory)` + `helper_db()` instead.

## PITFALL (caused the worst debugging spiral): fixture-factory result discarded = cleanup silently never ran
`module_cleanup_fixture(queries)` returns a fixture FUNCTION, but pytest discovers fixtures by module-level NAME. A bare call `module_cleanup_fixture(...)` discards the return → fixture never registered → teardown never runs → residue accumulates → **false "flaky" failures** (fixed-label nodes like `"Mutated by later change"` collide across runs → id-mismatch asserts). MUST bind: `_cleanup_after_module = module_cleanup_fixture(...)`.
Symptoms of silent-no-cleanup: residue with fixed labels (uuid labels hide it), tests pass standalone but fail in full-module/full-suite runs.

## Module-scoped TestClient + shared fakes = state leaks (DON'T)
Module-scoping `database`+repos+`client` together broke `test_chat_api` provider-mutation tests (shared `fake_provider` state leaks 503/401 behavior into later tests) and `_clear_cookies` hack didn't save it. Reverted. Keep client chains function-scoped; the wins are in seeding + probes + cleanup, not client reuse. Also: module-scoped driver + function-scoped TestClients = cross-loop connection reuse (the repo's documented crash class) — never combine those.

## pytest-asyncio loop_scope=module (pyproject)
```
asyncio_default_fixture_loop_scope = "module"
asyncio_default_test_loop_scope = "module"
```
Makes module-scoped async `database` fixtures safe (all tests in a module share one loop). Applied to `test_retrieval_tools`/`test_seed_idempotency`/`test_session_repository`/`test_chat_persistence`.

## Other gotchas
- Killed pytest runs (`process.kill`) skip teardown → residue; after killing, clean with a one-off script (`MATCH (n:Location) WHERE n.id STARTS WITH 'user-node:' DETACH DELETE n` etc.) before re-running.
- To check if a test failure predates your changes: `git stash push -- <file>` → run → `git stash pop`. Decisive, cheap.
- `_HELPER_DB`/settings capture at conftest import — if tests mutate NEO4J_* env, helper/app drivers can point at different DBs; keep NEO4J_* env stable.
- `--durations=40` on the full run is the ground truth; kill long runs early rather than waiting (a 75-min suite can't be measured by waiting).
