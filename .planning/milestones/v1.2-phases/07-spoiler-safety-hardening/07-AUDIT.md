# Phase 7 Repository Audit — Spoiler Leak Channels (07-01, Task 1)

**Audit date:** 2026-08-03
**Scope:** Every direct and indirect leak surface in the existing repo at HEAD,
grounded in real symbols (routes, query constants, response fields, service
methods). Feeds `docs/SPOILER-THREAT-MODEL.md` (DOCS-01) and organizes work per
the D-24 implementation order (audit/terminology/design first → migration →
metadata → relationships → search → media → chat → regression).

## 1. Stack verdict (D-01)

The current stack is **kept**: Neo4j Community + FastAPI + official Neo4j Python
driver + React 19/TypeScript/Vite + Cytoscape.js + Google authentication +
HttpOnly backend sessions.

The source plan's stack items are **rejected** (not adopted, not introduced
this phase): Memgraph, GQLAlchemy, Next.js, JWT auth, Redis, a second graph
database, a frontend rewrite, unrestricted Cypher. (Also rejected per D-01:
social recommendations, ratings/reviews, trivia ingestion, external
TMDb/IMDb/OMDb imports, actor scraping, spoiler-unrelated visual redesign.)

## 2. Current boundary plumbing (`visible_until_order`)

Single-boundary model today: one persisted field per user-series
(`UserSeriesProgress.visible_until_order`), one request query param on graph /
user-content routes, one server-resolved boundary for chat. The D-05
`watched_through_order` / `view_as_of_order` split and the D-04 central
policy service do **not** exist yet (07-02).

| Surface | Route / symbol | Boundary-aware today? |
|---|---|---|
| Progress GET/POST | `GET/POST /api/series/{series_id}/progress` — `ProgressUpdateRequest.visible_until_order`, `ProgressService.upsert` (api/progress.py, services/progress.py, graph/progress.py, repository/progress.py) | Yes — the single boundary write path |
| Graph read | `GET /api/series/{series_id}/graph?visible_until_order=` (api/graph.py) — `GraphService.resolve_boundary` (services/graph.py:39) validates against `BOUNDARY_QUERY`; `fetch_graph` (services/graph.py:50) filters every query | **Partial** — the request order is validated against a *persisted episode* but **not clamped to the user's persisted progress**; client may request any persisted order |
| User content | `GET /notes`, `GET /notes/{id}`, `GET /custom-nodes/{id}`, `GET /custom-relationships/{id}` — `Boundary = Annotated[int, Query(gt=0)]` (api/user_content.py:27) | Yes — query params on read routes (repository/user_content.py filters by boundary) |
| Episodes list | `GET /api/series/{series_id}/episodes` (api/series.py:46) → `SeriesService.list_episodes` → `SERIES_EPISODES_QUERY` (spoiler/filter.py:18) | **NO — the expected gap.** Query has no boundary parameter and returns `episode.title` for **all** episodes, including future ones. 07-03 adds masking + a boundary param. |
| Chat / GraphRAG | `POST /sessions/{id}/messages/stream` (api/chat.py) → `ChatService.answer_stream`; boundary from `_resolve_or_create_progress` (services/chat.py:172), `ensure_progress_for_chat` (services/chat.py:161) | Yes — boundary resolved server-side, never from the client; message rows persist `visible_until_order_snapshot` (repository/chat.py, domain/chat.py:53) |
| Revisions | api/revisions.py (9 `visible_until_order` uses) | Yes — read filtering by boundary |
| ChangeSets | api/change_set.py / repository/change_set.py / graph/change_set.py — `ChangeSetStale` (repository/change_set.py:74), `visible_until_order_snapshot` (domain/change_set.py:274) | Yes — snapshot carried; apply-staleness compares against since-lowered progress (extended in 07-07) |
| Candidates | api/candidates.py, graph/candidates.py | Yes — boundary filtering present |
| Retrieval tools | retrieval/tools.py (all 15 query constants take `$visible_until_order`; 75 occurrences) | Yes — server-owned kwarg, never from model tool-call args |

## 3. Leak-channel inventory (D-19 classes)

Columns: **channel** → **current behavior (real symbols)** → **enforcement
layer today** → **gap vs D-03 fail-closed rule** → **owning plan (07-02..07-08)**.
Every row names a symbol verified at HEAD by grep/read (see §4 evidence).

### 3.1 Direct leak classes

| # | Channel | Current behavior (real symbols) | Enforcement layer today | Gap vs D-03 | Owning plan |
|---|---|---|---|---|---|
| D1 | Future node | `NODES_QUERY` (spoiler/filter.py:43) filters `node.visible_from_order <= $visible_until_order`; `GET /graph` projects via `GraphNode` (domain/graph.py:11, `visible_from_order: int = Field(ge=1)`) | Query-level filter + schema-level non-null `visible_from_order` | No central policy service; per-query duplication of the rule; episodes route (`SERIES_EPISODES_QUERY`) exposes future Episode nodes with titles | 07-02 (policy), 07-03 (episodes) |
| D2 | Relationship | `VISIBLE_CLAIMS_QUERY` (filter.py:77) requires claim + subject + object + `SUPPORTED_BY` + `REFERS_TO` + evidence + source all `<= boundary`; `STRUCTURAL_EDGES_QUERY` (filter.py:59); `VISIBLE_USER_RELATIONSHIPS_QUERY` (filter.py:112) | Query-level chain filtering; edges projected from claims (services/graph.py:87) | Rule is duplicated across four queries and two tools files — D-04 service would centralize; candidate/change-set writes are the second path needing the same check (07-04) | 07-02, 07-04 |
| D3 | Claim | `VISIBLE_CLAIMS_QUERY`, `GET_CLAIMS_QUERY`/`CLAIMS_FOR_FRONTIER_QUERY` (retrieval/tools.py:47,159) filter claim + endpoints + `valid_from/until_order` window | Query-level filtering incl. temporal validity window | No `is_visible` helper; null-`visible_from_order` rows are excluded by `<=` (fail closed at query level, but not centralized); ChangeSet ops may target hidden Claims (07-04/07-07) | 07-02, 07-04, 07-07 |
| D4 | Evidence | `EVIDENCE_QUERY` (filter.py:161), `EVIDENCE_FOR_CLAIMS_QUERY`/`GET_EVIDENCE_QUERY` (tools.py:89,187) — `supported.visible_from_order` and `evidence.visible_from_order` both `<= boundary` | Query-level chain filter | Provenance chain (Claim → Evidence → Source) not enforced by one helper — each query re-states it; a visible Claim's future Evidence must never surface (07-04) | 07-02, 07-04 |
| D5 | Source text | `SOURCES_QUERY` (filter.py:137), `SOURCES_FOR_CLAIMS_QUERY`/`GET_SOURCES_QUERY` (tools.py:106,205) — `ref.visible_from_order` + `source.visible_from_order` filtered; returns `locator` (URL) | Query-level chain filter; `GraphSource` schema (domain/graph.py:50) | Series-wide safe Sources are not documented anywhere (D-11 requirement); locator URLs are external-link labels needing safe rendering (07-04/07-06) | 07-02, 07-04, 07-06 |
| D6 | Chat message | `get_session_detail` returns boundary-visible messages only; messages carry `visible_until_order_snapshot` (repository/chat.py:133/151, domain/chat.py:53); history above the view boundary hidden by service layer | Service-layer boundary filtering (`ChatService`) | Retrieval pipeline (retrieval/pipeline.py, 5 `visible_until_order` uses) must consume the **effective** boundary (min of view/watched) not the raw persisted one; hidden messages must never enter conversation memory (07-07) | 07-02, 07-07 |

### 3.2 Indirect leak classes

| # | Channel | Current behavior (real symbols) | Enforcement layer today | Gap vs D-03 | Owning plan |
|---|---|---|---|---|---|
| I1 | Episode title | `SERIES_EPISODES_QUERY` returns `episode.title` for every episode; `EpisodeResponse.title` (domain/series.py:17); `EpisodeSelector.tsx` renders `{episode.code} — {episode.title}` (EpisodeSelector.tsx:46,65) | **None** — title returned raw for future episodes | **FAIL-OPEN**: future episode titles leak on the episodes route and in the selector; D-08 masking (`title_is_spoiler`/`title_visible_from_order`) missing | 07-03 |
| I2 | Synopsis | No synopsis field exists in seed or query today | N/A (absent) | D-08: `synopsis_visible_from_order` — synopsis must not be returned above the boundary once added | 07-03 |
| I3 | Runtime | No runtime field exists today | N/A (absent) | D-08: runtime is a spoiler signal; must not be returned above the boundary once added | 07-03 |
| I4 | Image / poster | `NODES_QUERY` returns `node.image_url`, `node.image_source_url`; `GraphNode` carries both (domain/graph.py:18-19); seed: `data/dexter/seed/characters.json` — 9 characters have `image_url`, incl. `paul_bennett` (visible_from_order 2), `rudy_cooper` (3), `harry_morgan` (3) | Query-level: images only on nodes `<= boundary` | D-14: three seeded characters carry `image_url` at order > 1 — must be nulled/curated per boundary; neutral fallback + safe alt; no failed-request existence hints | 07-06 |
| I5 | Cast ordering | No Person/ACTED_AS/APPEARS_IN model (D-17 deferred); character labels from seed only | N/A (absent) | Deferred feature — documented in SPOILER-DEFERRED-DESIGN.md, not built this phase | 07-08 (regression guard) |
| I6 | Actor appearance count | No actor model; `GRAPH_SUMMARY_COUNTS_QUERY` (tools.py:222) counts only visible entities/claims/evidence/sources | Query-level visible-only counts | D-16: any future appearance count must be `episodes_seen_so_far` — never total planned, never last appearance (documented, not built) | 07-08 (regression guard) |
| I7 | Character status | Character status (main/supporting/dead-alive) is not returned by any current query | N/A (absent) | D-16: no final status before reveal point; never add `last_appearance_order` | 07-08 (regression guard) |
| I8 | First/last appearance | Not exposed today | N/A (absent) | D-16: forbidden before reveal point — documented, not built | 07-08 (regression guard) |
| I9 | Search suggestion | `SEARCH_ENTITIES_QUERY` (tools.py:128) filters `node.visible_from_order IS NOT NULL AND <= $visible_until_order`; `search_entities` (tools.py:442) allowlists types ∩ narrative labels; empty/whitespace query → `[]` | Query-level fail-closed + server allowlist | D-15: hidden entities behave like nonexistent — already the behavior; needs regression tests locking timing/error indistinguishability | 07-05 |
| I10 | Autocomplete | No autocomplete endpoint exists; frontend has no entity autocomplete | N/A (absent) | D-15: any future autocomplete must use the same boundary-filtered search primitive; cannot suggest future Characters | 07-05 |
| I11 | Hidden result count | `GRAPH_SUMMARY_COUNTS_QUERY` counts visible-only; `get_current_visible_graph_summary` (tools.py:701) returns visible counts; list endpoints return only visible rows | Query-level visible-only counting | D-16: hidden counts absent from API responses even when unrendered — already true; regression-lock | 07-05 |
| I12 | Node degree | Frontend computes degree from returned (visible) edges only; `GraphEdge` has no degree field; graph layout (Cytoscape) consumes only returned nodes/edges | Backend query filtering (indirect) | D-16: hidden degree/future relationships must never influence node sizing or layout — true today because backend filters; must survive 07-04 hardening | 07-04, 07-05 |
| I13 | Path existence | `find_path` (tools.py:474) BFS over visible claims only (`CLAIMS_FOR_FRONTIER_QUERY`); hidden-path → `{"found": False, ...}` identical to no path | Tool-level fail-closed | D-15: hidden path existence never revealed — already true; regression-lock | 07-05 |
| I14 | Graph layout | Layout input = filtered `GET /graph` response only | Backend filtering (indirect) | D-16: layout metadata (weights/degrees) must not reflect hidden resources — verify after relationship hardening | 07-04, 07-05 |
| I15 | Citation title | `SOURCES_FOR_CLAIMS_QUERY`/`GET_SOURCES_QUERY` return only boundary-visible source labels; pipeline citations derive from returned sources | Query-level chain filter | D-12: citations above the boundary stay hidden; retrieval pipeline must pass the **effective** boundary and never hint that safer info exists (07-07) | 07-07 |
| I16 | External-link label | `SOURCES_QUERY` returns `source.locator` (URL) — exposed on `GraphSource`; no per-boundary curation of external links | Query-level (source visibility) | D-11/D-14: external links must not contain visible future titles; locator is user-visible text — needs safe rendering rules | 07-04, 07-06 |
| I17 | Chat-session title | `ChatSessionCreateRequest.title` user-supplied (api/chat.py:64); sessions are user-owned; list scoped to user+series | Auth scoping | D-12: session lists/messages must not reveal content above the current view boundary; titles are user-authored (safe by origin) but must be checked in 07-07 | 07-07 |
| I18 | ChangeSet summary | `ChangeSetResponse.visible_until_order_snapshot` (domain/change_set.py:274); `ChangeSetStale` 409 `changeset_stale` on confirm (api/change_set.py:57-63) | Service-level staleness check vs lowered progress | D-13: a stale later-boundary ChangeSet cannot apply at an earlier view — partially enforced; must compare snapshot vs **effective** boundary (07-07) | 07-07 |
| I19 | Error message | Generic 404 `resource_not_found` for hidden/missing (api/progress.py:53-54, api/user_content.py:34-36); 422 `invalid_visible_until_order` when order is not a persisted episode (api/graph.py:63-67) | Envelope-level (generic codes) | D-15: error messages must not distinguish hidden from nonexistent — 404 pattern is generic; verify the 422 path and search-error paths in 07-05 | 07-05 |
| I20 | Timing-sensitive alternate response | Retrieval tools return empty results for hidden (fail closed); no timing variance measured | Tool-level fail-closed | D-15: search timing and errors must not intentionally distinguish hidden from nonexistent — add timing-indifference regression tests | 07-05 |
| I21 | Cache key / stale cache | `sessionStorage['hdgraf.watchProgress']` (useWatchProgress.ts:21) — single `visibleUntilOrder` field, backend-authoritative on mount; no server cache; no stale-cache of visibility | Frontend sessionStorage + backend-authoritative reconciliation | D-05: storage shape has no watched/view split (07-03 frontend); stale cached progress must never widen the effective boundary | 07-03, 07-05 |
| I22 | Episode code / season strings | `SERIES_EPISODES_QUERY` orders by `episode_order` (numeric); `code` returned for display; `EpisodeSelector` selects by `episode_order` | Numeric-order authority | D-09: never compare episode-code strings or season-number strings for visibility — audit any frontend ordering to confirm numeric-only | 07-03 (regression) |

## 4. Evidence (grep, run at HEAD from repo root)

`grep -rn "visible_until_order" backend/app` — per-file occurrence counts (source
files; `__pycache__` binary hits omitted):

```
75 backend/app/retrieval/tools.py
34 backend/app/spoiler/filter.py
21 backend/app/repository/user_content.py
 9 backend/app/repository/change_set.py
 9 backend/app/api/revisions.py
 8 backend/app/repository/chat.py
 8 backend/app/api/user_content.py
 7 backend/app/graph/chat.py
 6 backend/app/graph/change_set.py
 5 backend/app/services/graph.py
 5 backend/app/retrieval/pipeline.py
 4 backend/app/graph/candidates.py
 4 backend/app/api/graph.py
 3 backend/app/services/progress.py
 3 backend/app/services/chat.py
 3 backend/app/graph/progress.py
 3 backend/app/domain/progress.py
 2 backend/app/repository/progress.py
 2 backend/app/domain/change_set.py
 2 backend/app/api/progress.py
 2 backend/app/api/candidates.py
 1 backend/app/services/change_set.py
 1 backend/app/domain/graph.py
 1 backend/app/domain/chat.py
```

`grep -rn "visible_from_order" backend/app` — per-file occurrence counts
(source files; binary hits omitted):

```
64 backend/app/retrieval/tools.py
52 backend/app/repository/user_content.py
46 backend/app/spoiler/filter.py
28 backend/app/graph/change_set.py
12 backend/app/graph/seed.py
12 backend/app/api/revisions.py
11 backend/app/graph/candidates.py
10 backend/app/repository/change_set.py
 6 backend/app/domain/user_content.py
 5 backend/app/revisions/__init__.py
 5 backend/app/domain/graph.py
 4 backend/app/api/candidates.py
 3 backend/app/domain/revision.py
 3 backend/app/domain/extraction.py
 2 backend/app/domain/change_set.py
 1 backend/app/services/graph.py
 1 backend/app/domain/series.py
```

Notable: `visible_from_order` is enforced at **query level** everywhere (the
`<= $visible_until_order` pattern), and `domain/graph.py` + `domain/series.py`
make it a **non-null schema field** (`Field(ge=1)`) — a null value fails
validation (fail closed at the schema layer). There is **no** central
`is_visible` helper yet: the rule is restated in every query. That duplication
is the D-04 motivation; the policy-service contract is specified in
`docs/SPOILER-TERMINOLOGY.md` (Task 3 of this plan) and implemented in 07-02.

## 5. Key gap summary (feeds owning plans)

1. **07-02** — boundary formula is not D-05-shaped (single `visible_until_order`
   field; `resolve_boundary` validates but does not clamp to persisted view);
   no central policy service; API contract exposes one boundary field instead of
   the D-21 three-field shape.
2. **07-03** — `SERIES_EPISODES_QUERY`/`GET /episodes` is the only
   boundary-unaware read surface: future episode titles are returned raw and
   rendered by `EpisodeSelector.tsx`; no `title_is_spoiler`/synopsis/image
   metadata exists in `data/dexter/metadata/episodes.json`.
3. **07-04** — visibility chain (Claim→Evidence→Source, endpoints, Note targets)
   is per-query duplication; ChangeSet ops and user-content writes need the
   centralized check; seed carries `image_url` on three future-order characters
   (07-06).
4. **07-05** — D-15/D-16 protections largely exist at query level
   (search/path/counts) but are un-locked by regression tests; error/timing
   indistinguishability needs tests.
5. **07-06** — media: `image_url`/`image_source_url` on future-order characters
   must be curated; fallback + safe alt rules.
6. **07-07** — chat/citations/graph_focus/ChangeSet must consume the
   **effective** boundary; stale ChangeSet vs effective boundary; hidden
   messages never enter memory.
7. **07-08** — full regression matrix (backend + frontend) per
   `docs/SPOILER-THREAT-MODEL.md`.
