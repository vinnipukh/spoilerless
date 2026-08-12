# 09-18 Summary: Live AuraDB Reseed + Zombie Sweep (PROB-20 / PROB-22)

## Overview
Plan 09-18 executed the final operator-touch wave: PROB-20 live AuraDB reseed
(#44 — the 01N52 'property key does not exist' storm) and PROB-22 zombie
sweep (#46 — ~3,855 zombie AppUser rows, expired/orphaned Session nodes).
Both ran one-shot against the live AuraDB `03a8623b` with dry-run/count
evidence + operator sign-off first, per RESEARCH Pitfall 1 and Assumptions
A3/A4. The protected dev user `ae8a41b7-db96-40e8-b6c2-2e3c69aedb11` is
hard-coded in the sweep's NEVER_DELETE set; it was absent from the live DB,
so no deletion risk existed.

## Operator sign-off (recorded)
Operator approved the one-shot destructive run (2026-08-12) after reviewing
the pre-check audit + dry-run counts below.

## Pre-check (read-only, before any write)
- Series: `series_dexter`, `series_scratch_review`, `series_scratch_candidates`
- AppUser total: 66 — real users: 1 (`arhanera@gmail.com`, role=admin,
  HAS_PROGRESS + HAS_SESSION → tied, never a zombie candidate)
- Zombie AppUser candidates (dry-run): **65** — no progress/chat/ownership ties
- Stale Session rows (dry-run): **8** — expired/orphaned
- Episode 01N52 field check: **3 episodes missing the reveal-point keys**
  (`dexter_s01e01/02/03` — `synopsis_visible_from_order` /
  `image_visible_from_order`) → PROB-20 class confirmed live
- Protected id `ae8a41b7-…`: NOT present in AuraDB (no risk)

## Reseed — PROB-20 (#44)
`uv run python -m spoilerless.app.graph.setup` against live AuraDB (one-shot,
idempotent MERGE): `Dexter graph setup complete: 290 nodes, 308 relationships`.

Root cause found during post-check: the seed loaded `episodes.json` whose
reveal-point fields are `null` for S01E02/S01E03 (and `image_…` for all), and
the Neo4j driver drops `None` properties — so the keys were NEVER created on
those nodes, which is exactly the 01N52 class `spoiler/filter.py`'
`SERIES_EPISODES_QUERY` tripped on live. The reseed alone could not fix it.

**Fix (committed with this plan):** `spoilerless/app/graph/seed.py` —
`load_seed_data()` now materializes a null reveal-point as the episode's own
`visible_from_order` (a null reveal-point means "reveal with the episode
itself"), so the keys always exist on every seeded Episode node.

**Post-check (after fix + reseed):**
- All 3 episodes now carry `synopsis_visible_from_order` AND
  `image_visible_from_order` (1/2/3) — no 01N52 warnings; only the benign
  "successful completion" GQL note remains
- User content survives: `UserSeriesProgress` rows intact, `arhanera@gmail.com`
  admin user intact (MERGE preserved user layer, D-08)

## Zombie sweep — PROB-22 (#46)
`uv run python -m spoilerless.scripts.zombie_sweep --execute` (one-shot):
```
dry-run counts — zombie AppUser rows: 65, stale Session rows: 8
removed — zombie AppUser rows: 65, stale Session rows: 8
remaining — zombie AppUser rows: 0, stale Session rows: 0
```
Post-sweep integrity: AppUser total 1 (the real admin user), 0 zombies,
0 stale sessions. `NEVER_DELETE_USER_IDS` constant verified in script source;
protected id was not in the candidate set.

**Fix (committed with this plan):** `spoilerless/scripts/zombie_sweep.py` —
the TLS config used the legacy `trust=` driver key which neo4j 6.2.0 removed
(`ConfigurationError: Unexpected config keys: trust`); switched to
`trusted_certificates=TrustCustomCAs(certifi.where())`, matching
`spoilerless/app/graph/database.py`'s Aura path. Dry-run now connects.

## Verification
- `test_episode_ordering.py` + `test_series_service.py`: 11 passed
  (episodes carry reveal-point keys; series service maps them)
- `test_seed_idempotency.py`: setup errors = local docker Neo4j not running
  (environmental, not a regression — Aura-backed path verified separately)
- Live query post-fix: 3 rows, both reveal keys present, zero 01N52 warnings
- Real user count 1, zombies 0 — protected admin user provably survives

## Success Criteria
- ✅ Pre-check audit + dry-run recorded; operator sign-off documented BEFORE run
- ✅ Reseed executed once against AuraDB; post-check clean
- ✅ 01N52 warnings eliminated (seed fix + reseed)
- ✅ Zombie sweep 65→0; sessions 8→0; protected user survives
- ✅ No destructive op without dry-run evidence + sign-off (RESEARCH A3/A4)
