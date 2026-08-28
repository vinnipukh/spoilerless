# SEVENTEENTH PASS — live reseed/sweep + env alias trap (09-18 wave)

## The aura_* env-alias trap — LOCAL TESTS HIT AuraDB, not docker
`scripts/env-local.sh` exports `NEO4J_URI/USERNAME/PASSWORD` — but
`core/config.py` Settings uses `validation_alias=AliasChoices("aura_uri",
"neo4j_uri")` (etc.), and the FIRST alias wins. The repo `.env` carries the
AuraDB values under the `aura_*` names, so `source scripts/env-local.sh` +
pytest still connected to AuraDB (`neo4j+s://03a8623b...`), not local docker.

Symptom observed: `get_settings().neo4j_username == "03a8623b"` even after
sourcing env-local.sh; raw neo4j driver with `neo4j://localhost:7687` +
`neo4j`/`hdgraf-local-password` connected fine (proving container auth OK,
config resolution wrong).

FIX — export the aura_* names too when testing locally:
```bash
source scripts/env-local.sh
export aura_uri="neo4j://localhost:7687" aura_username="neo4j" \
       aura_password="hdgraf-local-password" aura_database="neo4j"
unset PYTHONPATH
.venv/Scripts/python.exe -m pytest spoilerless/tests -q -p no:cacheprovider
```

## Correct local docker container
`hdgrafcehennemi-neo4j` (image `neo4j:2026.06.0-community`, creds
`neo4j`/`hdgraf-local-password`). A second container `hdgraf-neo4j`
(`neo4j:5-community`) may exist — do NOT use it (wrong image; runbook targets
2026.06.0). If both are up, port 7687 conflict: stop the wrong one first.

## neo4j 6.2.0 driver config: `trust=` removed
`zombie_sweep.py` used `config["trust"] = TrustCustomCAs(certifi.where())` →
`neo4j.exceptions.ConfigurationError: Unexpected config keys: trust` on
driver 6.2.0. The app's `graph/database.py` already used the modern key:
`kwargs["trusted_certificates"] = TrustCustomCAs(certifi.where())`. Fix
scripts to use `trusted_certificates=`. Grep for legacy `trust=` when any
standalone script using the driver fails with "Unexpected config keys".

## 01N52 'property key does not exist' — seed null-drop root cause (PROB-20)
Live reseed alone did NOT clear the 01N52 warnings. Root cause: the seed's
`episodes.json` carries `synopsis_visible_from_order: null` /
`image_visible_from_order: null` for most episodes, and the Neo4j driver
DROPS None-valued properties on write — so the keys were never created on
those nodes, and `filter.py`'s SERIES_EPISODES_QUERY reads them →
`01N52 property key is not in the database` warnings per query.

Fix in `seed.py::load_seed_data()`: materialize null reveal-points as the
episode's own `visible_from_order` (semantics: null reveal-point = reveal
with the episode itself):
```python
for reveal_key in ("synopsis_visible_from_order", "image_visible_from_order"):
    if episode.get(reveal_key) is None:
        episode[reveal_key] = episode["visible_from_order"]
```
LESSON: null-in-JSON ≠ null-in-graph. If a query reads a property, the seed
must write the key explicitly; a None property value never reaches the DB.

## Sweep counts drifted from RESEARCH (~3,855 → 65)
RESEARCH predicted ~3,855 zombie AppUsers / 21+5 sessions; live dry-run
showed 65 zombies / 8 stale sessions (an earlier partial sweep had run).
Always trust the live `--dry-run` counts, not the research estimate; the
sweep protocol (dry-run → operator sign-off → --execute → post-check) worked
unchanged.

## Protected user check
Sweep's `NEVER_DELETE_USER_IDS` constant contains the bare id
`ae8a41b7-...` while stored AppUser ids carry the `user:` prefix. The real
admin user (`arhanera@gmail.com`, id `user:f935df68-...`) is protected by
having HAS_PROGRESS/HAS_SESSION ties, so the sweep skips it. When verifying
protection, match BOTH bare and `user:`-prefixed forms.

## Self-healing seed upsert: `SET node += row` never removes stale keys
The #28 hotlink sweep removed `image_url` from `characters.json`, but the
keys lingered on already-seeded nodes — BOTH local docker and AuraDB kept 6
wikia/nocookie URLs (`dexter:character:angel_batista` etc.), failing
`test_graph_nodes_include_image_fields`. Cause: `_upsert_nodes` used
`MERGE ... SET node += row`, which only adds/overwrites, never removes keys
absent from the row. (This also means the 01N52 null-drop fix above needs the
reseed to run against a DB seeded with the fixed code.)

Fix (`spoilerless/app/graph/seed.py::_upsert_nodes`) — delete node keys not
present in the seed row (seed = source of truth for canonical ids; user
content uses separate labels/ids and is untouched):
```cypher
UNWIND $rows AS row
MERGE (node:{label} {id: row.id})
SET node += row
WITH node, keys(node) AS node_keys, keys(row) AS row_keys
FOREACH (k IN node_keys |
  FOREACH (_ IN CASE WHEN NOT k IN row_keys THEN [1] ELSE [] END |
    SET node[k] = null
  )
)
```
`SET node[k] = null` deletes the property in Cypher. LESSON: any seed-JSON
key removal needs this, or the key survives on every already-seeded node.
Verify after reseed with `MATCH (c:Character) WHERE c.image_url IS NOT NULL
RETURN count(c)` → expect 0.

## Shell env contamination: stale aura_* exports poison AuraDB commands
Terminal env persists across calls. After a local-docker run that exported
`aura_uri=neo4j://localhost:7687`, a later AuraDB command fails with
`neo4j.exceptions.AuthError: The client is unauthorized` (settings resolve to
localhost with mismatched creds — and the error is a confusing AuthError, not
a connection error). Before Aura operations: `env | grep -E "^(aura_|NEO4J_)"`
and `unset aura_uri aura_username aura_password aura_database`. Same trap in
reverse: `.env`-sourced Aura creds poison local runs (see aura_* alias trap
above).
