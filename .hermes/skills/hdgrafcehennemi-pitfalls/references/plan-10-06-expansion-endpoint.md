# Plan 10-06 — expansion endpoint patterns & pitfalls

`GET /api/series/{series_id}/graph/expand` (D-21): allowlisted keys `family|work|conflict|episode_events|clues|locations|evidence`, `limit` 1..25 (default 12), strict `VisualizationDTO` DELTA (anchor + additions + edges only, NO hidden totals), **no cache-aside** (T10-CACHE-06). `metadata.view_type = "expansion:{key}"` so a delta never collides with the D-29 view vocabulary. Route lives in `spoilerless/app/api/graph.py`; projection is `project_expansion(graph, node_id, expansion_key, limit)` in `spoilerless/app/services/visualization.py`; constants in `spoilerless/app/domain/visualization.py` (EXPANSION_KEYS / EXPANSION_DEFAULT_LIMIT / EXPANSION_MAX_LIMIT / EXPANSION_VIEW_TYPE_PREFIX).

## Pitfalls (each one cost a verify cycle — check these first)

1. **Investigation rows are NOT graph nodes.** `clues`/`evidence` additions include Claim/Evidence/Source rows; `node_by_id` is built from `graph.nodes` only, so `node_by_id[nid]` KeyErrors. Keep additions in `additions_by_id`, classify display tiers from `additions_by_id[nid]`, and keep a separate `investigation_order: dict[str, int]` (row.visible_from_order) for the deterministic `(order, id)` addition sort. **Dispatch by concrete type, not attributes**: `GraphClaim` has NO `type`/`episode_id`/`image_url`/`image_source_url` (GraphEvidence/Source have no `type` either) — the shared `_node()` helper crashed on `claim.episode_id` and later `claim.image_url` (10-03 investigation view hit the same class). Use `isinstance(node, GraphClaim|GraphEvidence|GraphSource|GraphNode)` to pick `kind` + tier, and `getattr(node, "episode_id", None)` etc. inside `_node()`. The evidence-layer edge loop must filter with `isinstance(evidence, GraphEvidence)` — `evidence.type` raises AttributeError.

2. **Delta edges must be filtered to the key's relation family.** Mapping ALL `FULL_EDGE_CLASSES` edges between kept nodes leaks unrelated families — the s01e01 fixture's `user-rel:test-1` KNOWS edge (dexter↔debra) surfaced inside a `family` delta (`['family','knows']`). Neighbor/location keys filter `edge.type in _EXPANSION_EDGE_TYPES[key]` (family=FAMILY_OF, work=WORKS_WITH, conflict={OPPOSES,THREATENS,ATTACKS,KILLS,DISTRUSTS}, locations={LOCATED_IN,OCCURRED_IN}); `episode_events` keeps all kept-node edges; `clues`/`evidence` carry only `supported_by`/`from_source` layer edges.

2b. **`clues` adds claims AND their supporting evidence.** The seven-key delta parametrize expects clues = claims + evidence (evidence_1..4 interleaved by order), evidence = evidence + sources, and NO claims for evidence. Evidence is added to `additions_by_id` for BOTH `clues` and `evidence` keys (visibility fail-closed per row); sources are added only under `evidence`.

3. **Anonymous clients are clamped to order 1 (PROB-04/#12).** `episode_order=99` on an anonymous stub client returns 200, not 422. To test `INVALID_VISIBLE_UNTIL_ORDER`, use an authenticated user + progress record on a fixture whose max episode order is below the effective boundary (s01e01 fixture + `user={"id": "user:test"}` + `_ProgressRecord(2, 2)` → effective 2 → `resolve_boundary` fails → 422).

4. **Stub-app route tests need `install_error_handlers(app)`.** The 10-03 stub (test_graph_api.py) installs only database+repository handlers; the sanitized 422 envelope `{"detail":{"code":"INVALID_REQUEST","message":"Request validation failed."}}` comes from `install_error_handlers` (core/errors). test_visualization_projection.py now carries a self-contained stub (`_StubGraphService` / `_StubProgressService` / `_ProgressRecord` / `_expansion_app`) — install `install_error_handlers` + `install_database_error_handlers` + `install_repository_error_handlers`, include the graph router, and override `get_optional_current_user` / `get_graph_service` / `get_progress_service`. Serving fixtures: `GraphResponse.model_validate(fixture["graph"])` filtered per boundary like the real queries.

5. **Cache-bypass negative test: poison BOTH bindings.** graph.py binds cache fns at import (`from ...graph_cache import get_cached_graph`), so monkeypatching only `graph_cache.get_cached_graph` misses the route's binding. Patch the cache module attr AND the bound name on `import spoilerless.app.api.graph as graph_api_module` for every get/set fn (`get_cached_graph`, `set_cached_graph`, `get_cached_visualization`, `set_cached_visualization`); then every expansion key must still serve 200.

6. **Distinct-request-tuple independence** (T10-CACHE-06): prove limit=1 vs limit=2 vs a different key return independently computed deltas — there is no cache anywhere on the path to cross.

7. **OpenAPI inventory locks are exact.** Adding a route breaks `test_user_route_openapi_has_exact_operations_and_templates` (paths set + `len(schema["paths"])`) and `test_document_and_openapi_have_exact_locked_inventory` (operations 51→52, templates 38→39) plus `docs/reference/frontend-api-contract.md` (inventory table + counts + a contract section). Update all three in the same change (D-29).

## Tooling note

`search_files` patterns are regex — unescaped `(` in patterns like `it(` fails with "unclosed group" (JSON layer eats one backslash). Use paren-free alternates (`describe|^\s+it`) or double-escape (`it\\(` in the JSON string).

## Budget note for 2-task tracer/auto plans (~50-call cap)

The `<read_first>` gate can burn 30+ calls before any code is written. Order: read the plan + the 3-4 files that carry the pattern being extended → write production code → run the task's `<verify>` immediately → fix → commit Task 1 → then write remaining tests / start Task 2. Never save all verifies for the end.

## Frontend recovery state (useSceneState.ts, committed c4473b7)

`SceneState` carries `expansionHistory: ExpansionRecord[]` (`{anchorId, key, additionIds}`). Actions:
- `ADD_EXPANSION {nodeIds, record?}` — pushes the record; unsafe ids (incl. record additions) refused.
- `UNDO_EXPANSION` — pops the NEWEST record and removes exactly its `additionIds` (history-based, never heuristic).
- `COLLAPSE_EXPANSION {anchorId}` — removes all records rooted at the anchor + their additions.
- `BACK_TO_OVERVIEW` — activeView → episode_overview, clears expansions/history/focus/temporary/selection, PRESERVES filters + camera (D-47).
- `RESET_VIEW` — clears exploration layers, keeps view/filters/camera.
`fetchExpansion(seriesId, nodeId, expansionKey, episodeOrder, limit?)` lives in frontend/src/api/graph.ts with the 7-key `ExpansionKey` union.

## Plan status (2026-08-13 — COMPLETE)

Executor hit the tool cap mid-Task-1 with zero commits; orchestrator took over inline. Final commits: `999bc30` (endpoint + delta projection), `8ae9785` (typed expansion API client), `c4473b7` (history/recovery actions), `392018d` (SUMMARY/STATE/ROADMAP). All four fixes above applied. Task-1 backend verify green (21 passed), Task-2 verify green (23 passed + vitest 48). VIZ-06 marked complete; VIZ-03/VIZ-10 left open for 10-08.
