# Seed-drift test updates — making the suite deterministic (Phase 09, plan 09-08)

The enriched S01E01 seed (commits `ade1066`/`7bc8791`, "32 characters" era)
moved character visibility and renamed claims. Tests asserting OLD seed state
fail deterministically until updated. These are TEST drift, not product bugs.

## Diagnose with live-DB probes BEFORE writing assertions (never guess)

The failing assertion tells you the old expectation; the live graph tells you
the new truth. Probe with raw Cypher, not the tool under test:

```bash
unset PYTHONPATH && NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j \
  NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j \
  uv run python - <<'EOF'
# visible_from_order of every candidate probe char
MATCH (n) WHERE n.series_id=$sid AND n.id CONTAINS 'morgan' RETURN n.id, n.visible_from_order
# which fragments match NOTHING visible at boundary 1 (hidden-only probe)
MATCH (n) WHERE n.series_id=$sid AND toLower(n.label) CONTAINS 'paul' AND n.visible_from_order <= 1
EOF
```

Observed facts after enrichment (2026-08-05):
- `harry_morgan`, `doris_morgan` → vfo=1 (VISIBLE at boundary 1). Genuinely
  hidden probes are `paul_bennett` (vfo=2) and `rudy_cooper` (vfo=3).
- Dexter→Debra `find_path` edge renamed: `dexter:claim:s01e01:dexter_debra_family`
  → `dexter:claim:s01e01:debra_trusts_dexter` (both may exist). Use an any-of
  assertion, not exact-edge.
- "bennett" matches THREE visible chars (astor/cody/rita, all vfo=1) + a
  claim; "aul" matches a visible claim (`jaw_faulty_warrant`). Hidden-only
  fragments: "coop" (rudy_cooper, vfo=3), "paul" (nothing visible ≤1).
  Choose fragments that match ONLY your intended set — probe first.

## Test-constant updates in test_retrieval_tools.py

- Constants file now has DORIS, PAUL, RUDY alongside HARRY.
- Hidden-probe swaps: `test_search_entities_hides_future_matches` query
  "harry"→"paul" (reveal at order 2, not 3); `get_claims`/`get_entity`/
  `get_neighborhood_hidden_entity_fails_closed` entity `HARRY`→`PAUL`;
  `get_neighborhood_excludes_hidden_claims` uses rita-bennett neighborhood +
  `rita_paul_family` claim (DEXTER's harry claim is vfo=1 now);
  summary-hides-future `HARRY`→`RUDY`.
- Stable-order assert at boundary 3: all four Morgans are vfo=1 now →
  `[DEBRA, DEXTER, DORIS, HARRY]` (id-stable within same vfo).

## Seed-file canonical-vs-candidate origin counting (easy to get wrong)

Seed files MIX origins: `characters.json` has 26 canonical + 6 candidate,
`organizations.json` 4+1, `claims.json` 114+18. `_layer_snapshot(db,
"canonical")` counts ONLY `origin='canonical'` rows. So a completeness
assertion like `nodes >= 1 + sum(len(data[k]))` OVERCOUNTS by the candidate
rows (observed: 267 canonical nodes in DB vs 290 raw seed rows → false red).
Fix: filter the expectation to canonical origin:

```python
def _canonical(rows): return sum(1 for r in rows if r.get("origin", "canonical") == "canonical")
```

Same for relationship expectations (PART_OF/PRECEDES/SUPPORTED_BY/REFERS_TO
counts must use canonical episodes/claims). "Drift-agnostic" means: compare
snapshots to each other (first == second), assert supersets, never exact
totals that the seed files can grow.

## Scratch-series conversion (D-07 isolation, PROB-22)

`spoilerless/tests/conftest.py` now ships (since 09-08):

- `CANDIDATE_SCRATCH_SERIES` / `REVIEW_SCRATCH_SERIES` constants.
- `bootstrap_scratch_series(series_id, episode_orders=(1,2,3))` — creates
  scratch :Series + :Episode nodes on a FRESH driver/loop (safe inside sync
  TestClient tests, never the app's portal-loop driver). Required because
  candidate boundary-validation (`api/candidates.py::_require_resolved_boundary`,
  D-09) resolves against a persisted episode order.
- `teardown_scratch_series(series_id)` — deletes all `{series_id}` rows +
  `origin='candidate'` residue + `UserSeriesProgress` rows (progress rows
  carry series_id but no visible_from_order and trip the seed-integrity
  audit — the documented full-suite contamination path).

Conversion pattern: module-scope `live_client` fixture bootstraps the
scratch series before TestClient and tears down in `finally`. Gate after
conversion: `rg 'series_dexter' <converted-file>` = 0.

## CI DB-pollution gate (PROB-22)

After `uv run pytest` in ci.yml, a step fails if residue remains:

```python
MATCH (n) WHERE n.series_id STARTS WITH 'series_scratch' OR n.origin='candidate' RETURN count(n)
```

plus `actions/upload-artifact@v4` on failure and `npm audit --audit-level=high`
in the frontend job.
