# Visualization projections & versioned cache (phase 10, plan 10-03+)

Design contract established while executing 10-03 (interrupted mid-Task-1, 2026-08-13).
Continuation agents must honor these semantics rather than re-deriving them.

## Six D-29 views — `GET /api/series/{series_id}/graph/visualization`

Route contract: `view` Literal enum (episode_overview|character_network|plot_threads|
investigation|full|graphrag_focus), required `episode_order` gt=0, optional repeated
`focus_id` (accepted ONLY for graphrag_focus, 20 distinct cap), typed 404
`SERIES_NOT_FOUND` / 422 `INVALID_REQUEST` / `INVALID_VISIBLE_UNTIL_ORDER` / 503
envelopes, response = strict `VisualizationDTO`. Boundary resolves through the shared
`api/graph.py::_resolve_effective_boundary(..., boundary_label="episode_order")`:
anonymous fixed at order 1 (PROB-04/#12), authenticated clamped by persisted progress
(D-05); boundary without a persisted episode → 422. Route carries no editorial event
metadata yet (no storage) → episode_overview on the route has empty timeline.

Concrete projection semantics (services/visualization.py):
- **episode_overview**: Variant A — containers + Characters + major Events only;
  omits PARTICIPATED_IN/OCCURRED_IN/LOCATED_IN + participation family (D-13);
  timeline = all declared events by (visible_from_order, id).
- **character_network**: Characters only, narrative edges (HUMAN_EDGE_CLASSES) between
  characters, empty timeline/groups, no auto-communities (D-36).
- **plot_threads**: containers + Characters + ALL declared events (any tier);
  optional `SafePlotThread` editorial groups — thread member outside the kept/visible
  set FAILS CLOSED (InvalidVisibilityOrder), never guessed/dropped.
- **investigation**: Claim/Evidence/Source layer ONLY (claims never on the main story
  graph, D-41); edges `supported_by` (claim→evidence, claim_id rides the edge) and
  `from_source` (evidence→source); claim status → display tier (canonical=1,
  corroborated=2, candidate=3, unknown FAILS CLOSED); missing evidence/source refs
  fail closed; all claim/source/evidence rows must be visible at the boundary.
- **full**: every safe node (all kinds) + every safe edge via `FULL_EDGE_CLASSES`
  (HUMAN_EDGE_CLASSES + participation family human wording: participated_in,
  occurred_in, located_in, witnessed, caused, affected, targeted, mentioned); no D-09
  caps (Advanced mode, D-11); undeclared events tier 3.
- **graphrag_focus**: validate/dedupe/lexical-sort focus ids; every focus id must be a
  visible graph node (hidden and unknown indistinguishable → fail closed); nodes =
  focus + narrative neighbors (participation family excluded), deterministically
  truncated at GRAPHRAG_FOCUS_MAX_NODES=20 (D-27); DTO `focus` = first canonical id
  (must resolve inside the DTO, T10-FOCUS-02); empty focus set → error.
- `project_view()` is the typed dispatch seam; unknown view → ValueError (fail closed).

## Cache contract (D-30, spoilerless/app/cache/graph_cache.py)

- Final key: `viz:{series}:{effective}:{view}:{projection_version}:{epoch}:{user|anon}:{focus_sig}`
  (Task 1 committed the pre-epoch 6-part key; Task 2 adds epoch + signature).
- Stale rejection on read: re-validate payload as `VisualizationDTO` AND require
  metadata.projection_version / view_type / effective_view_order to match the key
  dimensions → otherwise treat as miss (poisoned JSON also miss). Never serve a
  cached DTO whose metadata contradicts the request (T10-CACHE-02/03).
- `graph_revision:{series_id}` is a Redis-LOCAL per-series epoch, default 0 — NOT a
  Neo4j field. `invalidate_series()` atomically `incr` the epoch BEFORE deleting
  `graph:{series}:*` and `viz:{series}:*` keys (all write paths already route through
  this one function: candidates.py ×3, change_set.py ×2, user_content.py ×6).
- Epoch read failure (Redis error OR corrupt value) → bypass cache entirely (None).
- Race separation: the key embeds the epoch read BEFORE projection; a stale-epoch
  write lands only in its own old-epoch key and can never populate the new epoch.
- Focus signature: SHA-256 hexdigest over the length-prefixed canonical sequence
  (`f"{len(id)}:{id}"` joined, deduped + lexically sorted); empty focus → fixed
  `"none"`. Length prefixes prevent ["ab","c"] vs ["a","bc"] collisions.
- Test `_FakeRedis` needs `incr` in addition to get/setex/scan_iter/delete.

## Offline stub-route pattern (no live Neo4j — how plan verifies pass)

`spoilerless/tests/test_graph_api.py` (10-03):
- `_FakeGraphService`: loads a checked-in `fixtures/visualization/*.json`, serves
  get_series_meta / resolve_boundary / fetch_graph. **fetch_graph must FILTER rows by
  the requested boundary** (visible_from_order <= effective, edges need both endpoints
  kept) — the cumulative S01E02 fixture has order-2 rows; serving it at effective 1
  unfiltered trips the projection fail-closed 422.
- `_stub_graph_app()`: FastAPI + install_database_error_handlers +
  install_repository_error_handlers + include_router(graph_router), then
  dependency_overrides on `get_optional_current_user` / `get_graph_service` /
  `get_progress_service` (override keys are the FUNCTIONS).
- `cached_live_client` was reworked to this stub (its only consumer,
  `test_graph_endpoint_cache_hit_matches_miss_byte_for_byte`, is matched by the plan's
  `-k "cache"` filter and must run offline).

## Verification commands (10-03)

- Task 1: `uv run pytest spoilerless/tests/test_graph_api.py spoilerless/tests/test_visualization_cache.py spoilerless/tests/test_openapi_contract.py spoilerless/tests/test_frontend_contract_doc.py -q -k "visualization or projection or cache or exact_operations or locked_inventory"` then `uv run pytest spoilerless/tests/test_visualization_projection.py -q -k "episode_overview or character_network or plot_threads or investigation or full or graphrag_focus"`
- Task 2: `uv run pytest spoilerless/tests/test_visualization_cache.py -q`
- Always `unset PYTHONPATH` first; plain pytest, NO `--timeout` flag (pytest-timeout not installed).
- OpenAPI inventory: 50/37 → 51/38 — update test_openapi_contract.py
  (test_user_route_openapi_has_exact_operations_and_templates paths/methods/count),
  test_frontend_contract_doc.py (EXPECTED_OPERATIONS + counts), and
  docs/reference/frontend-api-contract.md (inventory table + "50 method/path" text +
  new "## Visualization routes and schemas" section).
