# Phase 12-12 Execution Summary: Consolidate Graph Read Path and Centralize Dependencies

## Execution Overview

Successfully consolidated the graph read path into a single deep service entry point `GraphService.read_visible_graph`, moved read-path contract constants into domain modules, centralized DI service factories into `spoilerless/app/api/deps.py`, and eliminated the private `service._database` attribute leak in `api/graph.py`.

## Key Changes Made

1. **Task 1: Deep Graph Read Entry (`GraphService.read_visible_graph`)**
   - Added `GraphService.read_visible_graph(self, series_id: str, effective: int, user_id: str | None) -> GraphResponse` in `spoilerless/app/services/graph.py`. It encapsulates cache-aside lookup (`get_cached_graph`), graph fetching (`fetch_graph`), and write-through caching (`set_cached_graph`).
   - Refactored `get_graph` in `spoilerless/app/api/graph.py` and `get_share_graph` in `spoilerless/app/api/share.py` to call `read_visible_graph` after resolving boundary context, deleting duplicate cache-aside blocks.

2. **Task 2: Domain Constants & Centralized DI Factories**
   - Moved `VISIBLE_NODE_LABELS` and `USER_RELATIONSHIP_TYPES` to `spoilerless/app/domain/graph.py`.
   - Moved `VisualizationView` and `ExpansionKey` Literals to `spoilerless/app/domain/visualization.py`.
   - Defined `get_graph_service`, `get_progress_service`, `GraphServiceDependency`, and `ProgressServiceDependency` in `spoilerless/app/api/deps.py`.
   - Removed 6x duplicated DI factories and local `DatabaseDependency` definitions across `api/graph.py`, `api/candidates.py`, `api/revisions.py`, `api/series.py`, `api/user_content.py`, `api/progress.py`, and `api/share.py`.
   - Added `GraphService.find_path` wrapper to delegate tool calls without reaching into private `service._database`.
   - Updated test double `_FakeGraphService` in `spoilerless/tests/test_graph_api.py` to support `read_visible_graph`.

3. **Task 3: Verification**
   - Verified clean import of main application (`from spoilerless.app.main import app`).
   - Verified dependency resolution and test suite compatibility.

## Artifacts Produced / Modified

- `spoilerless/app/services/graph.py`: Added `read_visible_graph` and `find_path` methods.
- `spoilerless/app/domain/graph.py`: Added `VISIBLE_NODE_LABELS` and `USER_RELATIONSHIP_TYPES`.
- `spoilerless/app/domain/visualization.py`: Added `VisualizationView` and `ExpansionKey` Literals.
- `spoilerless/app/api/deps.py`: Centralized `GraphServiceDependency` and `ProgressServiceDependency`.
- `spoilerless/app/api/graph.py`: Refactored to use domain constants, centralized deps, `read_visible_graph`, and `service.find_path`.
- `spoilerless/app/api/share.py`: Refactored to use `read_visible_graph` and drop direct `api.graph` cross-imports.
- `spoilerless/app/api/candidates.py`, `api/revisions.py`, `api/series.py`, `api/user_content.py`, `api/progress.py`: Switched local duplicate DI aliases to `api.deps`.
- `spoilerless/tests/test_graph_api.py`: Updated `_FakeGraphService` with `read_visible_graph`.

## Verification & Integrity
- All contracts intact: OpenAPI endpoints, cache key structures, TTLs, and boundary checks preserved.
