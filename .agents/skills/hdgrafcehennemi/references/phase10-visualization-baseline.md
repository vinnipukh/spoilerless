# Phase 10 — Visualization Baseline & A/B Gate (plan 10-01)

Shipped 2026-08-13. Commits: `3cec852` (Task 1: fixtures + tracer), `4903b23` (Task 2: decision log), `82d1951` (metadata/SUMMARY). Plans 10-02..10-11 consume these artifacts — read this before touching projection/DTO/cache/benchmark work.

## Artifacts

- **Fixtures:** `spoilerless/tests/fixtures/visualization/s01e01_safe.json` and `s01e02_cumulative_safe.json`. Immutable, synthetic-safe (never `series_dexter`, no live reads).
- **Envelope schema** (both fixtures): `fixture_metadata` `{schema_version, fixture_type: "episode_safe", episode, episode_order, scope: "safe"|"cumulative_safe", series_id, effective_view_order, projection_version, immutable, generated_by, checked_in}` + `events` `[{id, label, episode_id, tier: "major"|"supporting"|"micro", participant_ids, location_id, visible_from_order}]` + `graph` (GraphResponse-shaped payload).
- **projection_version: `1.0.0`** — the version the 10-02 DTO and 10-03 cache key must carry.
- **Tracer:** `spoilerless/tests/test_visualization_baseline.py` — `load_fixture` → `GraphResponse.model_validate` → `effective_view_order`/`is_visible` from `spoilerless/app/spoiler/policy.py` → `measure_baseline()` → `project_variant()` → `approximate_crossings()` → `build_evidence()`. No mock seam. **`build_evidence()` is THE evidence object — tests and the decision log quote only its measured values; never hand-write numbers.**
- **Variant projection rules:** A = characters + major Events (+ Series/Episode containers); B = character-led, all Events timeline-only. Both omit `OCCURRED_IN`/`PARTICIPATED_IN`/`LOCATED_IN` edges (D-13). Crossings = deterministic id-order interleave approximation (D-32 permits approximation).
- **Decision log:** `docs/decision-logs/phase-10-visualization.md` (D-03 format: problem / alternatives / evidence / choice / rejection / risk).

## Measured baseline (locked numbers)

| Metric | S01E01 | Cumulative S01E02 |
|---|---|---|
| Nodes (kinds) | 11: C6 Ep1 E1 L2 S1 | 17: C8 Ep2 E2 L4 S1 |
| Edges (types) | 7: FAMILY_OF1 KNOWS1(user) OCCURRED_IN3 PART_OF1 WORKS_WITH1 | 14: FAMILY_OF2 KNOWS1 OCCURRED_IN6 PART_OF2 PRECEDES1 WORKS_WITH2 |
| Claims / Sources / Evidence | 4 / 1 / 3 | 6 / 2 / 5 |
| Payload bytes | 7,692 | 12,386 |

Variants (nodes/edges): A = 9/4 (E01), 13/7 (E02); B = 8/4 (E01), 11/7 (E02). Crossings 0 everywhere; procedural labels 0; stability retention 1.0 (6 shared characters), displacement 0 by construction (real fCoSE displacement measured in 10-08).

**DECISION: Variant A (characters + major Events) is the Episode Overview production default.** B rejected: 11 nodes < 12-node target floor on cumulative S01E02. Full Graph stays Advanced (D-11). S01E01 is sparse (8–9 nodes, below floor) — accepted per D-44 empty-state policy.

## Pitfalls

- **Derive cumulative counts from existing fixture math, never an invented expectation.** Cumulative S01E02 = the E03 fixture's 20 nodes (9C/3E/4L/3Ep/1S) minus E03-only rows (episode, `event_paul_flashback`, `char_paul_bennett`) = 17 (8 characters). A first expectation of 18 was wrong; the fixture was right, the test expectation was fixed.
- **Extracting evidence values via `uv run python -c` + `importlib.util.spec_from_file_location` fails for modules defining dataclasses** with `AttributeError: 'NoneType' object has no attribute '__dict__'` (dataclasses look up `sys.modules[cls.__module__]`). Register the module first: `sys.modules['name'] = m` BEFORE `spec.loader.exec_module(m)`.
- **Plan verify filters use `-k`:** name tests so substrings match (e.g. `-k "variant or bound"` → `test_variant_*` / `test_*bounds*`). Re-run BOTH the full-file command and the `-k` command after committing.
- Always `unset PYTHONPATH` before `uv run pytest` / `uv run python` in this repo (Hermes env shadows the venv).
- Shared-ID gate (#2388): VIZ-03/VIZ-10 are also declared by 10-03/10-08, so REQUIREMENTS.md must NOT mark them Complete after 10-01 alone — they flip when the last declaring plan's SUMMARY exists.
