# Suite timing reality — the "sub-8m" claim is a false benchmark (SEVENTEENTH PASS, 2026-08-12)

## Why the green suite is ~42 min even on local docker
The EIGHTH PASS "<8m met (2:01)" figure is WRONG as a green-suite benchmark:
it was measured on the stale `hdgraf-neo4j` (5-community) container with 35
failing tests (change-set family 503'd instantly — fast-fail = no work done).
`bacd536` (08-11) fixed that local-5.x 503 class; those tests now pass and do
full work per test.

Measured 2026-08-12 (correct container `hdgrafcehennemi-neo4j`, 2026.06.0):
- `setup_database` on local docker: ~4.6s
- `live_client` fixture is FUNCTION-scoped: full re-seed per test + TestClient
  lifespan boot ≈ 10s/test (`test_progress_api.py`: 26 tests / 260s)
- ~250+ API tests use `live_client` → full green suite ≈ 42:45 (599 passed)
- The runbook's "sub-8-minute target requires local docker" line was stale
  optimism; corrected in docs/ops/runbook.md + docs/ROADMAP.md §8.7

## Do NOT trust
- "2:01 local docker" as a green-suite expectation — it was a failing run.
- Wall-time of a suite with failures as a baseline: fast-failing tests
  (503s, constraint errors) complete in seconds and inflate apparent speed.

## Speedup task (tracked, not yet done)
ROADMAP §8.7: module/session-scoped seed + read-only client targeting
sub-10-min green local runs. The DRY conftest comment (conftest.py:163)
documents the earlier attempt broke `get_database` state — the per-module
shared client must be resurrected without that breakage.

## Practical guidance
- Per-file targeted runs are fast: pick the file, get results in seconds to
  minutes (graph/change-set files are the slow ones, ~5-15 min).
- For a full-suite gate, budget ~45 min on local docker; AuraDB serial is
  ~40 min (SEVENTH PASS measurement) — roughly the same wall time now.
- pytest-timeout is installed (uv pip install pytest-timeout): add
  `--timeout=120 --timeout-method=thread` so a hang fails with a named test
  instead of a silent stuck run (a "hung" suite with near-zero CPU is usually
  just slow seeding — check progress via `-v > log` + `tail`, not by killing).
