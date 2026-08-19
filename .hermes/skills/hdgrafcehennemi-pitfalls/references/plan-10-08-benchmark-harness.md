# Plan 10-08 — Visualization benchmark harness (VIZ-10 / D-32)

Plan: `.planning/phases/10-polish-finishing-touches/10-08-PLAN.md`. Worked example of the
`deterministic-benchmark-harness` skill (see it for the general design pattern).

## Files
- `scripts/benchmark_visualization.py` — zero-network harness: seeded (0x1008) synthetic
  `GraphResponse` payloads -> real `VisualizationProjectionService` projections at the four
  required scales 30x50 / 75x150 / 150x400 / 300x1000.
- `scripts/benchmark_visualization_schema.json` — result contract, validated by the stdlib
  subset validator inside the script (repo has NO `jsonschema` package; plan forbids installs).
- `spoilerless/tests/test_visualization_baseline.py::test_benchmark_harness_schema_valid_deterministic_output`
  (`@pytest.mark.benchmark`; marker registered in pyproject `[tool.pytest.ini_options]`).

## Commands (verified green 2026-08-13)
- `unset PYTHONPATH && uv run python scripts/benchmark_visualization.py --sizes 30x50,75x150,150x400,300x1000 --output .planning/tmp/phase-10-benchmark.json` — exit 0 == schema-valid + all hard gates pass.
- `unset PYTHONPATH && uv run pytest spoilerless/tests/test_visualization_baseline.py -q -k benchmark`

## Repo pitfalls (durable)
1. `scripts/` is not a package and `spoilerless` is NOT installed in the venv — scripts must
   `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` before spoilerless imports.
   pytest works without this (it inserts the rootdir); `uv run python scripts/...` does not.
   Mirrors the PYTHONPATH-stripping discipline in `run_backend_tests.py`.
2. New pytest markers MUST be registered in pyproject `[tool.pytest.ini_options]`
   `markers = [...]` — the repo had no markers section before 10-08; unregistered markers warn.
3. D-09 fail-closed is EXPECTED at scale: `project_episode_overview` over a cumulative
   (multi-episode) scope raises `ValueError` once kept nodes > 40 or edges > 60. Happens at
   75x150, 150x400, 300x1000. Harness code projecting cumulative scopes must catch it and
   record cap-enforcement evidence ("cap_raised" gate), never crash. The API already maps the
   ValueError to a typed 422 INVALID_REQUEST (`api/graph.py` `get_visualization`, 10-03).
4. Determinism leak (the bug that broke the fingerprint): wall-clock `ms` values must NEVER
   sit inside the deterministic result tree — every timing belongs in the `observations`
   block; the fingerprint covers structural fields only (counts/bytes/SHA/id-sets). The
   pytest test runs the harness twice and compares per-size fingerprints.
5. Synthetic graph generation must be scope-consistent: every edge's endpoints must be
   visible at the edge's own `visible_from_order`, else derived episode subgraphs fail
   `GraphResponse` closure validation. Generate same-episode character pairs, event->location
   edges only to locations visible <= the event's order, participants only from the event's
   episode. Always provide a deterministic-safe fallback (same-episode sibling pick), never
   `rng.sample` pairs that can cross episodes.

## Measured baselines (seed 0x1008, deterministic)
| Size | payload | overview (ep1) | target 12-28 | cumulative scope |
|---|---|---|---|---|
| 30x50 | 15.5 KB | 15n/13e | True | 27n/28e serialized |
| 75x150 | 40.9 KB | 22n/37e | True | cap_raised |
| 150x400 | 96.3 KB | 25n/46e | True | cap_raised |
| 300x1000 | 205.4 KB | 28n/60e | True (exactly at the 60 hard cap — do NOT loosen bounds) | cap_raised |

16/16 hard gates per size. Browser-side metrics (adapter conversion, fCoSE init/layout,
interaction, React commits, episode-switch latency) are environment-sensitive observations
pointing at `visualizationAdapter.test.ts` / `GraphCanvas.test.tsx`, which pin them.

## Resume state (2026-08-13 — session hit tool-call budget)
Plan 10-08 was NOT committed: the four Task-1 files (harness, schema, baseline test,
pyproject markers) sit uncommitted in the working tree with both Task-1 verify commands
green. Remaining: re-run the other 14 baseline tests, commit Task 1 atomically, Task 2
(vitest + refinement + decision-log update), `npm --prefix frontend run build`,
10-08-SUMMARY.md, STATE/ROADMAP/REQUIREMENTS close-out. Do NOT stage pre-existing dirty
files (`.planning/config.json`, `.planning/tmp/*`, `.hermes/`, `run_*.py`, `verify_*.py`).
