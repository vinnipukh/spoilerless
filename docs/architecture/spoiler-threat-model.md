# Spoilerless — Spoiler Threat Model

**Status:** DOCS-01 deliverable (plan 07-01) · **Date:** 2026-08-03
**Source inventory:** `docs/architecture/spoiler-threat-model.md` itself is the living leak-channel inventory
(originally grounded in `.planning/phases/07-spoiler-safety-hardening/07-AUDIT.md` at commit `8e286ed`; that
phase directory was archived during the Phase 8/9 restructure — audit findings were folded into this
document and `docs/PROBLEMS.md`).
**Locked vocabulary:** `docs/architecture/spoiler-terminology.md` — read it first. `visible_from_order` is the single
canonical reveal-point property; the visibility rule is **fail closed** (D-03).

This document inventories every current public spoiler-bearing read surface: the series graph
(`GET /api/series/{series_id}/graph`), shortest visible path (`POST /api/series/{series_id}/graph/path`),
Markdown export (`GET /api/series/{series_id}/export`), chat sessions and messages, ChangeSets, and the
four `/api/share` operations (create, list, revoke, and the unauthenticated token graph). It covers the
direct and indirect spoiler leak classes named in decision **D-19** plus those later surfaces. Each leak
class carries: **enforcement layer**, **backend query/service** (real symbol), **frontend behavior**,
**test coverage** (real test file), and **fail-closed rule** (what happens when the guard is missing).
Controls are labeled **implemented** (live at HEAD) or **desired** (designed but not yet enforced in
code), so historical plan intent never blurs current status; a **regression matrix** closes the document.

## 1. Scope and trust boundaries

| Boundary | Description |
|---|---|
| API response → client | Any future-episode/story data rendered or returned is a leak. Masking is **backend-side per D-08**, never CSS. |
| docs → implementation | Every enforcement layer and fail-closed rule below becomes contract; later plans (07-02..07-08 per D-24) execute against it. |
| Anonymous vs authenticated read boundary | **Implemented.** `GET /graph`, `POST /graph/path`, and `GET /export` all take `OptionalUserDependency` and resolve the effective boundary in `_resolve_effective_boundary` (api/graph.py:129): anonymous readers are **fixed at order 1** — a client-chosen `visible_until_order` can never widen the window without a session, and the persisted-episode check resolves against the effective (not requested) order so anonymous clients cannot even probe episode ids above boundary 1 — while authenticated readers are clamped to `min(requested, persisted view_as_of_order)` then `effective_view_order(view, watched)` against the persisted `UserSeriesProgress` row. Progress writes require `CurrentUserDependency` (api/progress.py:49,82). |
| Ownership / admin mutation gates | **Implemented.** User-content writes, candidate ingest/review, and revision revert are gated by `CurrentUserDependency` with an admin bypass (09-03); ChangeSet confirm/reject are admin-gated (`RequireAdminDependency`, api/change_set.py:116); cross-owner mutations return 403. One user can never widen or mutate another user's view. |
| LLM tool calls | **Implemented.** Retrieval tools receive the backend-derived **effective** boundary as a server-owned kwarg (`$visible_until_order`, 39 literal occurrences in `spoilerless/app/retrieval/tools.py`); the LLM can never raise it (D-12). The model-visible surface is 11 keyword-only read tools (get_entity, get_neighborhood, search_entities, find_path, get_claims, get_evidence, get_sources, get_current_visible_graph_summary, get_character_context, get_timeline, fetch_episode_codes) plus `propose_changeset`, registered by pipeline.py as the 12th tool. Server ceilings: `MAX_PATH_HOPS=4`, `MAX_TRAVERSAL_DEPTH=3`, `MAX_SEARCH_RESULTS=25`, `MAX_RESULT_LIMIT=50` (retrieval/tools.py:26-31); no tool accepts raw Cypher; replayed tool output is truncated to 4000 chars (`_MAX_TOOL_RESULT_CHARS`, pipeline.py:108); `propose_changeset` validates typed operations and persists only an `awaiting_confirmation` draft via `ChangeSetService.propose`. |
| LLM-delivered story content | **Implemented.** `retrieval/pipeline.py` re-filters retrieved rows against the effective boundary, renders only allowlisted fields (auth/session fields excluded by allowlist, never denylist), assembles a fixed 9-section delimited context (`CONTEXT_SECTIONS`), applies item/character budgets (`llm_max_context_items` / `llm_max_context_characters`), truncates replayed tool output to 4000 chars, and validates citations against the **current turn's** retrieved ID set only. `llm/system_prompt.py` appends anti-prompt-injection framing: content inside the labeled delimiters is data, never instructions. Covered by `test_prompt_injection.py`, `test_retrieval_pipeline.py`, `test_citations.py`. |
| Browser delivery (security headers + CORS) | **Implemented.** A middleware installs `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy` on every response (main.py:45-55); CORS is explicit credentialed (`allow_credentials=True` with explicit method/header lists — never wildcards — covering the BYOK `X-LLM-*` headers, main.py:188-201). Verified by `test_security_headers_on_every_response` and `test_cors_preflight_is_explicit_no_wildcard_with_credentials`. |
| Cache vs rate-limiter failure behavior | **Distinct.** The Redis graph cache (`cache/graph_cache.py`) is **fail-open/best-effort**: read/write Redis errors are caught and fall through to Neo4j. The Redis rate limiter (`services/rate_limit.py`) is **not fully fail-open**: `RedisBucket.init()` during lifespan and `limiter.try_acquire_async()` are not wrapped, so configured-Redis failures there can propagate (`test_rate_limit.py`). |

## 2. Canonical verification invocations

Backend (from repo root):

```bash
unset PYTHONPATH && source .venv/Scripts/activate && pytest spoilerless/tests/<file> -k <pattern>
```

Frontend:

```bash
cd frontend && NODE_ENV=test CI=1 npx vitest run <pattern>
```

`git diff --check` must stay clean on every docs change. The full-suite gate is the **live suite at HEAD
with zero new failures** (D-25); the archived pre-hardening baseline (321 passed / 5 failed / 7 errors)
is historical context only and must not be presented as current evidence — the backend suite and test
inventory have changed substantially since that run.

## 3. Direct leak classes

A *direct* leak returns story content (an entity, relationship, Claim, Evidence, Source text, or chat
message) that belongs to an episode above the viewer's effective boundary.

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **Future node** | Query-level `<= boundary` filter + schema-level non-null `visible_from_order` | `NODES_QUERY` (spoiler/filter.py:48); `GET /api/series/{series_id}/graph` → `GraphService.fetch_graph` (services/graph.py:51); `GraphNode.visible_from_order: int = Field(ge=1)` (domain/graph.py:11) | Cytoscape renders only returned nodes; layout input is the filtered response only | `spoilerless/tests/test_graph_api.py` (hidden-node absence); matrix row G1 | Node with NULL or `> effective_view_order` `visible_from_order` is never returned; schema validation rejects null (fail closed). Missing guard → node leaks. |
| **Relationship** | Chain query filter: relationship + subject + object + (where applicable) Claim all `<= boundary` | `VISIBLE_CLAIMS_QUERY` (filter.py:86), `STRUCTURAL_EDGES_QUERY` (filter.py:65), `VISIBLE_USER_RELATIONSHIPS_QUERY` (filter.py:128); edges projected from visible claims (services/graph.py:92) | Edges rendered from returned set only; node degree computed from visible edges only | `spoilerless/tests/test_graph_api.py` (per-relationship tests, incl. edge-only projection); matrix row G2 | A relationship is visible iff its **own** `visible_from_order` is non-null and satisfied AND both endpoints are visible AND the related Claim is visible. Missing any link → hidden (D-10). |
| **Claim** | Query-level filter incl. `valid_from`/`valid_until_order` temporal window, composed with the centralized policy helpers | `VISIBLE_CLAIMS_QUERY` (filter.py:86); retrieval `GET_CLAIMS_QUERY` / `CLAIMS_FOR_FRONTIER_QUERY` (retrieval/tools.py:169,47) | Claims render as edges/cards from returned set only; ChangeSet proposals are validated server-side | `spoilerless/tests/test_retrieval_tools.py`, `spoilerless/tests/test_retrieval_pipeline.py`; matrix row G3 | Claim hidden if `visible_from_order` NULL or `> boundary`, or outside validity window. Centralized `is_visible`, `effective_view_order`, `require_visible_resource`, and `assert_visibility_invariants` now live in `spoiler/policy.py` (policy.py:80,94,109,190) and compose with the per-query filters (D-04). |
| **Evidence** | Chain filter: Claim and Evidence both `<= boundary` — **implemented at graph-query level; only partial at retrieval-query level** | `EVIDENCE_QUERY` (filter.py:182) gates the full chain; retrieval `EVIDENCE_FOR_CLAIMS_QUERY` / `GET_EVIDENCE_QUERY` (retrieval/tools.py:92,200) match a Claim by caller-supplied `claim_ids` but only visibility-gate `SUPPORTED_BY` and `EvidenceFragment` — the matched Claim, its validity window, and endpoints are not gated in the query | Evidence shown only inside a visible Claim expansion | `spoilerless/tests/test_retrieval_tools.py` (test_get_evidence_visible_only), `spoilerless/tests/test_citations.py`; matrix row G4 | A visible Claim must never expose future Evidence (D-11). Evidence hidden if its own or its Claim's order fails; retrieval rows above the boundary are additionally dropped by pipeline context re-filtering (defense-in-depth). Missing guard → provenance chain leaks. |
| **Source text** | Chain filter: referencing relationship and Source both `<= boundary` — **implemented at graph-query level; only partial at retrieval-query level** | `SOURCES_QUERY` (filter.py:153); retrieval `SOURCES_FOR_CLAIMS_QUERY` / `GET_SOURCES_QUERY` (retrieval/tools.py:111,220) match a Claim by `claim_ids` and gate `REFERS_TO` + `Source` only; `GraphSource` (domain/graph.py:50) returns `locator` | Citation chips / external links from returned Sources only | `spoilerless/tests/test_citations.py` (test_hidden_claim_evidence_source_citations_are_rejected), `spoilerless/tests/test_retrieval_tools.py` (test_get_sources_visible_only); matrix row G5 | Future Source title or locator never returned. Series-wide Sources safe from order 1 must be **documented explicitly**; do not assume all Sources are safe (D-11). |
| **Chat message** | Service-layer boundary resolution + per-message persisted snapshot | `ChatService.answer_stream` (services/chat.py:278); boundary from `_resolve_or_create_progress` (services/chat.py:237) / `ensure_progress_for_chat` (services/chat.py:226); messages persist `visible_until_order_snapshot` (repository/chat.py:135,154; domain/chat.py:71) | Message list renders only boundary-visible messages; hidden messages never enter conversation memory | `spoilerless/tests/test_chat_api.py`, `spoilerless/tests/test_chat_persistence.py`; matrix row G6 | Messages above the **effective** boundary (min of view/watched) are hidden; the retrieval pipeline consumes only the effective boundary. Missing guard → chat history leaks. |

## 4. Indirect leak classes

An *indirect* leak reveals the **existence, extent, or metadata** of hidden story content without
returning the content itself.

### 4.1 Titles and episode metadata (I1–I4)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I1 — Episode title** | **Implemented (D-08).** Backend masking via `mask_episode_metadata` (spoiler/policy.py:154), which consumes `episode.visible_from_order` (episode-unlock masking): above the effective view the real title is replaced by a generic label. The title-specific fields `title_is_spoiler` / `title_visible_from_order` are returned by the episode query but are **not** consumed by the policy function | `SERIES_EPISODES_QUERY` (spoiler/filter.py:18) returns `title_is_spoiler` / `title_visible_from_order` (filter.py:28-29); `mask_episode_metadata` (policy.py:154) computes `display_title`; `SeriesService` merges it (services/series.py:52-55); `EpisodeResponse.display_title` (domain/series.py:24) | `EpisodeSelector.tsx` renders `{episode.code} — {episode.display_title ?? episode.title}` with a Lock icon on locked episodes (EpisodeSelector.tsx:25,61-62,85) | `test_episode_masking.py -k "title"`, `test_spoiler_policy.py -k "mask"` (matrix row M1) | Above `effective_view_order`, spoiler-sensitive title is replaced by a generic label (`S01E05 — Episode 5`); code + season/episode number stay visible; a missing title also falls back to the generic label (fail closed) (D-08). Missing guard → future titles leak in the selector. |
| **I2 — Synopsis** | **Text absent today; visibility metadata present.** D-08 `synopsis_visible_from_order` | `SERIES_EPISODES_QUERY` returns `episode.synopsis_visible_from_order` (filter.py:30); no synopsis text exists in seed or responses | Not rendered (field absent) | `test_episode_masking.py -k "synopsis"` (matrix row M2) | Synopsis must not be returned above the boundary once added; absence is not a leak. |
| **I3 — Runtime** | Absent today; runtime is a spoiler signal (D-08) | No runtime field | Not rendered | `test_episode_masking.py -k "runtime"` (matrix row M3) | Runtime must not be returned above the boundary once added. |
| **I4 — Image / poster** | Query-level (images ride on `<= boundary` nodes) | `NODES_QUERY` returns `node.image_url` / `node.image_source_url`; `GraphNode` carries both (domain/graph.py:11); seed `data/dexter/seed/characters.json` — **0 characters carry `image_url`; 6 carry `image_source_url` only** (attribution/source URLs, not image assets), all `visible_from_order:1` | Neutral initials fallback for hidden images; alt text safe; no URL as visible text | **Desired:** no `test_media_safety.py` exists at HEAD. Implemented proxies: `test_graph_api.py -k "hidden or visible"` (test_graph_hidden_character_image_urls_never_serialized, test_no_seed_image_for_resources_visible_above_order_one) (matrix row M4) | Image above `effective_view_order` is not returned; failed image requests must not imply future character existence (D-14). Missing guard → character image leaks existence. |

### 4.2 Cast and aggregates (I5–I8)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I5 — Cast ordering** | Deferred feature (D-17) — no Person/ACTED_AS/APPEARS_IN model this phase | None (character labels from seed only) | Not rendered | **Desired:** 07-08 regression guard (matrix row C1) | Cast order is never exposed before its reveal point; design documented in `docs/architecture/spoiler-deferred-design.md`, not built. |
| **I6 — Actor appearance count** | Visible-only counting (D-16) | `GRAPH_SUMMARY_COUNTS_QUERY` (retrieval/tools.py:239) counts only visible entities/claims/evidence/sources and gates claim endpoints via EXISTS subqueries; `get_current_visible_graph_summary` (tools.py:746) | Counts labeled "seen so far" where displayed | `test_retrieval_tools.py -k "count or summary"` (matrix row C2) | Any future appearance count is `episodes_seen_so_far` — never total planned, never last appearance (D-16/D-17). |
| **I7 — Character status** | Not returned by any current query (D-16) | None | Not rendered | **Desired:** 07-08 regression guard (matrix row C3) | No final status (dead/alive, main/supporting) before the reveal point; never add `last_appearance_order`. |
| **I8 — First/last appearance** | Not exposed today (D-16) | None | Not rendered | **Desired:** 07-08 regression guard (matrix row C4) | Forbidden before the reveal point — documented in `docs/architecture/spoiler-deferred-design.md`, not built. |

### 4.3 Search, autocomplete, counts (I9–I11)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I9 — Search suggestion** | Query-level fail-closed + server allowlist (D-15) | `SEARCH_ENTITIES_QUERY` (retrieval/tools.py:135) filters `node.visible_from_order IS NOT NULL AND <= $visible_until_order`; `search_entities` (tools.py:476) allowlists types ∩ narrative labels; empty/whitespace query → `[]` | Search results render only returned entities | `test_retrieval_tools.py -k "search"` (matrix row S1); the timing-indifference part is **Desired** (see E2) | Hidden entities behave like nonexistent: hidden name/alias never returned, hidden exact ID behaves like unknown ID, errors and timing do not distinguish hidden from nonexistent (D-15). |
| **I10 — Autocomplete** | No endpoint today (D-15) | None | No entity autocomplete in UI | **Desired:** no autocomplete test exists at HEAD (matrix row S2) | Any future autocomplete must reuse the same boundary-filtered search primitive; it cannot suggest future Characters. |
| **I11 — Hidden result count** | Query-level visible-only counting (D-16) | `GRAPH_SUMMARY_COUNTS_QUERY` (tools.py:239); list endpoints return only visible rows | Counts absent from API responses even when unrendered | `test_retrieval_tools.py -k "count or summary"` (matrix row S3) | Hidden counts never appear in API responses; totals reflect visible resources only. |

### 4.4 Graph layout and degree (I12–I14)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I12 — Node degree** | Backend query filtering (indirect) | No degree field on `GraphEdge`; frontend computes degree from returned edges only | Cytoscape sizing uses visible edges only | **Implemented proxy:** `test_graph_api.py -k "edge or hidden"` (edge-only projection); **Desired:** a dedicated degree test — no test named `degree` exists at HEAD (matrix row L1) | Hidden degree / future relationships never influence node sizing or layout (D-16). |
| **I13 — Path existence** | Tool-level fail-closed (D-15) | `find_path` (retrieval/tools.py:519) BFS over visible claims only (`CLAIMS_FOR_FRONTIER_QUERY`); hidden path → `{"found": False}` identical to no path | Path result rendered as returned | `test_retrieval_tools.py -k "path"`, `test_graph_api.py -k "path"` (test_path_route_*) (matrix row L2) | Hidden path existence is never revealed; response is byte-identical to "no path". |
| **I14 — Graph layout** | Backend filtering (indirect) | Layout input = filtered `GET /graph` response only | Cytoscape layout consumes returned nodes/edges only | **Implemented proxy:** `test_graph_api.py -k "edge or hidden"`; **Desired:** a dedicated layout test — no test named `layout` exists at HEAD (matrix row L3) | Layout metadata (weights, degrees) must not reflect hidden resources (D-16). |

### 4.5 Citations and external links (I15–I16)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I15 — Citation title** | **Implemented as defense-in-depth, not query-level Claim gating.** Retrieval source queries gate `REFERS_TO` + `Source` but not the matched Claim's visibility/validity window; the stronger protections are pipeline context boundary re-filtering and current-turn retrieved-ID citation validation | `SOURCES_FOR_CLAIMS_QUERY` / `GET_SOURCES_QUERY` (tools.py:111,220); `get_sources` (tools.py:725); pipeline citations derive from returned sources and are validated against this turn's retrieved ID set | Citation chips from returned sources only | `spoilerless/tests/test_citations.py` (test_hidden_claim_evidence_source_citations_are_rejected), `spoilerless/tests/test_retrieval_pipeline.py` (matrix row T1) | Citations above the boundary stay hidden; the retrieval pipeline passes the **effective** boundary and never hints that safer information exists (D-12). |
| **I16 — External-link label** | Query-level (source visibility) + curation | `SOURCES_QUERY` (spoiler/filter.py:153) returns `source.locator` (URL), exposed on `GraphSource` (domain/graph.py:50) | External links rendered from returned Sources; safe rendering rules are **Desired** (07-06 media-safety suite, row M4) | `test_retrieval_tools.py -k "source or locator"` (matrix row T2) | External links must not contain visible future titles; `locator` is user-visible text and must be curated per boundary (D-11/D-14). |

### 4.6 Chat sessions and ChangeSets (I17–I18)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I17 — Chat-session title** | Auth scoping (user-owned sessions) | `ChatSessionCreateRequest.title` user-supplied (domain/chat.py:102; imported api/chat.py:23, used api/chat.py:68); session lists scoped to user + series | Session picker lists own sessions | `test_chat_api.py -k "session"` (matrix row H1) | Titles are user-authored (safe by origin) but session lists must never reveal content above the view boundary (D-12). |
| **I18 — ChangeSet summary** | Service-level staleness check + admin-gated confirm | `ChangeSetResponse.visible_until_order_snapshot` (domain/change_set.py:274); `ChangeSetStale` → 409 `CHANGESET_STALE` on confirm (api/change_set.py:61); confirm/reject are **admin-gated** (`RequireAdminDependency`, api/change_set.py:116); `ChangeSetStale` (repository/change_set.py:75) | Card shows stale state, replaces Confirm/Reject | `test_change_set_confirmation.py -k "stale"` (matrix row H2) | A stale later-boundary ChangeSet cannot apply at an earlier view; snapshot must be compared against the **effective** boundary (D-13). |

### 4.7 Errors and timing (I19–I20)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I19 — Error message** | Envelope-level generic codes (uppercase) | Generic 404 `RESOURCE_NOT_FOUND` (api/progress.py:65,101,103; api/user_content.py:39); 422 `INVALID_VISIBLE_UNTIL_ORDER` when order is not a persisted episode (api/progress.py:63,105; api/graph.py:87,147); share token graph 404 `TOKEN_NOT_FOUND` | Error toast shows generic message | `test_progress_api.py -k "not_found"`, `test_user_content_api.py`, `test_graph_api.py` (matrix row E1) | Errors never distinguish hidden from nonexistent (D-15): same code for both. |
| **I20 — Timing-sensitive alternate response** | Tool-level fail-closed | Retrieval tools return empty results for hidden (fail closed); no timing variance measured | N/A (server-side) | **Desired:** no timing-indifference test exists at HEAD (matrix row E2) | Search timing and errors do not intentionally distinguish hidden from nonexistent (D-15). |

### 4.8 Cache and ordering (I21–I22)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I21 — Cache key / stale cache** | **Server cache-aside + frontend backend-reconciliation.** `GET /graph` and the share-token graph use `cache/graph_cache.py`: keys `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}` (the boundary is part of the key, so a boundary change auto-misses), TTL 300s, Redis read/write failures fall through to Neo4j (fail-open), and graph-changing writes call coarse per-series `invalidate_series` after commit | `get_cached_graph` / `set_cached_graph` / `invalidate_series` (cache/graph_cache.py:24-28,71); backend remains authoritative | `sessionStorage['spoilerless.watchProgress']` (useWatchProgress.ts:41) is now **only a loading-state compatibility cache** — `useWatchProgress` tracks `watchedThroughOrder` and `viewAsOfOrder` separately and reconciles them against the backend; the legacy single `visibleUntilOrder` shape is written solely for hydration | `test_graph_api.py -k "cache"` (cache hit/miss, key separation, byte-for-byte equality), `cd frontend && NODE_ENV=test CI=1 npx vitest run useWatchProgress` (matrix row K1) | Stale cached progress must never widen the effective boundary; boundary-in-key caching makes stale server data self-invalidating (D-05 watched/view split is live). |
| **I22 — Episode code / season strings** | Numeric-order authority (D-09) | `SERIES_EPISODES_QUERY` orders by `episode_order` (numeric); `code` returned for display; selector selects by `episode_order` | EpisodeSelector keys/selects by numeric order | `test_episode_ordering.py -k "order"`, `test_progress_api.py -k "order"` (matrix row O1) | Never compare episode-code strings or season-number strings for visibility; episode-code ordering is never used for reveal decisions (D-09). |

### 4.9 Public graph, path, export, and share surfaces (P1–P6)

The read surfaces below were added after the original D-19 inventory. Each reuses the same boundary
machinery as the graph GET (`_resolve_effective_boundary` / `fetch_graph`); the share-creation clamping
gap is the one place a stored boundary can exceed the creator's own view.

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **P1 — Shortest visible path** (`POST /api/series/{series_id}/graph/path`) | **Implemented.** `OptionalUserDependency` + `_resolve_effective_boundary` with `MAX_PATH_HOPS` (4) as the server-injected requested order — the client supplies only `source_entity_id` / `target_entity_id` / `max_hops` (1..4) and can never widen the boundary (api/graph.py:167-196) | `find_path` (retrieval/tools.py:519) BFS over visible claims only (`CLAIMS_FOR_FRONTIER_QUERY`, tools.py:47); hidden path → `{"found": false}` byte-identical to no path | Path result rendered as returned | `test_graph_api.py -k "path"` (test_path_route_*), `test_retrieval_tools.py -k "path"` (test_find_path_*) (matrix row P1) | Hidden path existence is never revealed; an anonymous caller is fixed at order 1 (D-15). |
| **P2 — Markdown export** (`GET /api/series/{series_id}/export`) | **Implemented.** `OptionalUserDependency` with `visible_until_order` defaulting to 1; `_resolve_effective_boundary` then renders Markdown from the **same** filtered `fetch_graph` read path — never a second filter implementation (api/graph.py:199-236) | `_render_export_markdown` over `GraphService.fetch_graph` output; `Content-Disposition: attachment` | Download rendered from returned set only | `test_graph_api.py -k "export"` (test_export_*) (matrix row P2) | Export contains only boundary-visible nodes/edges/Claims/Evidence/Sources; anonymous export is fixed at order 1. |
| **P3 — Share creation** (`POST /api/share`) | **Implemented: persisted-episode validation only; boundary clamping is Desired.** `CurrentUserDependency`; `resolve_boundary` validates `visible_until_order` identifies a persisted episode (422 `INVALID_VISIBLE_UNTIL_ORDER` otherwise) but the stored boundary is **not clamped to the creator's persisted view/watched progress** — the token graph later serves the stored boundary even if the creator's own view is lower (api/share.py create_share_link) | `ShareRepository.create` persists `{created_by, series_id, visible_until_order}` + token hash | Share link created from current view | `test_share_api.py` (matrix row P3) | A non-persisted order is rejected (fail closed). **Desired:** clamp `visible_until_order` to the creator's effective view at creation so a share can never expose more than the creator can see. |
| **P4 — Share token graph** (`GET /api/share/{token}/graph`) | **Implemented; unauthenticated by design.** No user dependency; token resolved by hash; invalid/expired/revoked → 404 `TOKEN_NOT_FOUND`; serves the **stored** `record.visible_until_order` as the effective boundary and reuses `fetch_graph` + cache-aside (api/share.py) | `get_share_graph` → `fetch_graph` with `effective_view_order = record.visible_until_order` | Snapshot graph rendered read-only | `test_share_api.py` (matrix row P4) | The snapshot boundary is fixed at creation; revocation and expiry both hide the graph. The only widening path is the P3 creation-time gap. |
| **P5 — Share list** (`GET /api/share`) | **Implemented.** `CurrentUserDependency`; creator-scoped | `ShareRepository.list_active(created_by)` | Own shares only | `test_share_api.py` (matrix row P5) | Only the caller's active shares are returned. |
| **P6 — Share revoke** (`DELETE /api/share/{token}`) | **Implemented.** `CurrentUserDependency`; creator-scoped | `ShareRepository.revoke`; revoked tokens immediately 404 on the token graph (revoke returns HTTP 200 `{"status":"revoked"}`) | Revoked link disappears from list | `test_share_api.py` (matrix row P6) | A revoked share never serves the token graph again. |

## 5. Completion gate (D-25)

Completion of spoiler-safety work is **never claimed** while any public API response still contains a
future entity name, relationship, Claim, Evidence, Source label, citation, episode synopsis,
spoiler-sensitive title, media URL, count, path, chat message, or ChangeSet detail — including the
graph, path, export, and share-token responses. Verification gates are executable against HEAD: the
full backend pytest suite (zero new failures vs the current HEAD baseline — the archived 321/5/7
pre-hardening numbers are historical, not a current gate), the frontend vitest suite, frontend lint
(**zero errors** — the lint-zero hardening is complete; the historical 28-error allowance is obsolete),
TypeScript typecheck via `npm run build`, the production build, `git diff --check`, and the regression
matrix below. Matrix rows labeled **Desired** are not evidence of current coverage; only rows labeled
**Implemented** count toward the gate.

## 6. Regression matrix

One row per leak class: **leak class → enforcement → test file/command → status → pass gate**. Backend
invocation is `unset PYTHONPATH && source .venv/Scripts/activate && pytest spoilerless/tests/<file> -k <pattern>`
from the repo root; frontend invocation is `cd frontend && NODE_ENV=test CI=1 npx vitest run <pattern>`.
**Status** is **IMPLEMENTED** (the test file exists at HEAD and the selector matches at least one test)
or **DESIRED** (no current test exists; the row states the intended regression). Rows referencing absent
future-plan files (`test_episode_metadata.py`, `test_media_safety.py`) are labeled DESIRED — never
presented as landed coverage.

| Leak class | Enforcement | Test file / command | Status | Pass gate |
|---|---|---|---|---|
| G1 Future node | `NODES_QUERY` + `GraphNode` schema | `pytest spoilerless/tests/test_graph_api.py -k "hidden or visible"` | IMPLEMENTED | Future nodes absent from response; null `visible_from_order` rejected |
| G2 Relationship | Chain queries (filter.py) | `pytest spoilerless/tests/test_graph_api.py -k "relationship or edge"` | IMPLEMENTED | Hidden edge never returned; no degree/layout influence |
| G3 Claim | `VISIBLE_CLAIMS_QUERY` + temporal window + policy helpers | `pytest spoilerless/tests/test_retrieval_tools.py -k "claim"` | IMPLEMENTED | Hidden/invalid-window Claim absent; proposals validated server-side |
| G4 Evidence | `EVIDENCE_QUERY` chain + pipeline re-filter | `pytest spoilerless/tests/test_retrieval_tools.py -k "evidence"` | IMPLEMENTED | Visible Claim never exposes future Evidence |
| G5 Source text | `SOURCES_QUERY` chain + pipeline re-filter | `pytest spoilerless/tests/test_citations.py -k "source"` | IMPLEMENTED | Future Source title/locator absent |
| G6 Chat message | service boundary + snapshot | `pytest spoilerless/tests/test_chat_api.py -k "boundary or hidden"`, `test_chat_persistence.py` | IMPLEMENTED | Messages above effective boundary hidden; no memory pollution |
| M1 Episode title | `mask_episode_metadata` (episode-unlock) | `pytest spoilerless/tests/test_episode_masking.py -k "title"` (+ `test_spoiler_policy.py -k "mask"`) | IMPLEMENTED | Spoiler title masked to generic label; non-spoiler visible |
| M2 Synopsis | `synopsis_visible_from_order` metadata; no text | `pytest spoilerless/tests/test_episode_masking.py -k "synopsis"` | IMPLEMENTED | Synopsis absent above boundary; metadata never leaks text |
| M3 Runtime | D-08 (absent today) | `pytest spoilerless/tests/test_episode_masking.py -k "runtime"` | IMPLEMENTED | Runtime absent above boundary |
| M4 Image / poster | D-14 query-level + safe fallback | `pytest spoilerless/tests/test_graph_api.py -k "hidden or visible"` (dedicated `test_media_safety.py` suite) | DESIRED (proxies IMPLEMENTED) | Future image absent; fallback + safe alt; no URL text |
| C1 Cast ordering | Deferred (D-17) | 07-08 regression guard | DESIRED | No Person/APPEARS_IN exposure; no cast order in any response |
| C2 Appearance count | `episodes_seen_so_far` only (D-16) | `pytest spoilerless/tests/test_retrieval_tools.py -k "count or summary"` (+ 07-08 guard) | IMPLEMENTED (guard DESIRED) | Counts visible-only; never total planned, never last appearance |
| C3 Character status | D-16 | 07-08 regression guard | DESIRED | No final status before reveal point |
| C4 First/last appearance | D-16 | 07-08 regression guard | DESIRED | Never exposed before reveal point |
| S1 Search suggestion | `SEARCH_ENTITIES_QUERY` + allowlist | `pytest spoilerless/tests/test_retrieval_tools.py -k "search"` | IMPLEMENTED (timing-indifference part DESIRED) | Hidden entity/alias absent; exact-ID behaves unknown; timing/error indifferent |
| S2 Autocomplete | Boundary-filtered primitive | no endpoint, no tests at HEAD | DESIRED | Autocomplete never suggests future Characters |
| S3 Hidden result count | visible-only counts | `pytest spoilerless/tests/test_retrieval_tools.py -k "count or summary"` | IMPLEMENTED | Hidden counts absent from responses |
| L1 Node degree | visible edges only | `pytest spoilerless/tests/test_graph_api.py -k "edge or hidden"` (dedicated `degree` test) | IMPLEMENTED proxy; dedicated test DESIRED | Degree/layout unaffected by hidden relationships |
| L2 Path existence | `find_path` fail-closed | `pytest spoilerless/tests/test_retrieval_tools.py -k "path"`, `test_graph_api.py -k "path"` | IMPLEMENTED | Hidden path response identical to no-path |
| L3 Graph layout | filtered response only | `pytest spoilerless/tests/test_graph_api.py -k "edge or hidden"` (dedicated `layout` test) | IMPLEMENTED proxy; dedicated test DESIRED | Layout metadata reflects visible resources only |
| T1 Citation title | effective-boundary pipeline + current-turn citation validation | `pytest spoilerless/tests/test_citations.py`, `test_retrieval_pipeline.py` | IMPLEMENTED | Citations above boundary hidden; no "safer info exists" hints |
| T2 External-link label | source visibility + curation | `pytest spoilerless/tests/test_retrieval_tools.py -k "source or locator"` | IMPLEMENTED | Links never contain visible future titles |
| H1 Chat-session title | auth scoping | `pytest spoilerless/tests/test_chat_api.py -k "session"` | IMPLEMENTED | Session lists never reveal above-boundary content |
| H2 ChangeSet summary | snapshot vs effective boundary | `pytest spoilerless/tests/test_change_set_confirmation.py -k "stale"` | IMPLEMENTED | Stale later-boundary ChangeSet cannot apply at earlier view |
| E1 Error message | generic uppercase envelopes | `pytest spoilerless/tests/test_progress_api.py -k "not_found"`, `test_user_content_api.py`, `test_graph_api.py` | IMPLEMENTED | Hidden and nonexistent produce identical errors |
| E2 Timing indifference | fail-closed tools | no timing-named test at HEAD | DESIRED | Search timing/errors do not distinguish hidden from nonexistent |
| K1 Cache / stale cache | boundary-keyed cache-aside + watched/view split | `cd frontend && NODE_ENV=test CI=1 npx vitest run useWatchProgress` (+ `pytest spoilerless/tests/test_graph_api.py -k "cache"`) | IMPLEMENTED | Stale cache never widens effective boundary |
| O1 Episode code / season strings | numeric `episode_order` authority | `pytest spoilerless/tests/test_progress_api.py -k "order"`, `test_episode_ordering.py -k "order"` | IMPLEMENTED | Reveal decisions never compare code/season strings (S01E09 < S01E10, cross-season, flashback) |
| P1 Shortest path | `OptionalUserDependency` + `find_path` BFS | `pytest spoilerless/tests/test_graph_api.py -k "path"`, `test_retrieval_tools.py -k "path"` | IMPLEMENTED | Hidden path identical to no-path; boundary never client-widened |
| P2 Markdown export | shared `fetch_graph` read path | `pytest spoilerless/tests/test_graph_api.py -k "export"` | IMPLEMENTED | Export contains only boundary-visible content |
| P3 Share creation | persisted-episode validation (clamping desired) | `pytest spoilerless/tests/test_share_api.py` | IMPLEMENTED (clamp DESIRED) | Non-persisted order rejected; order clamped to creator's effective view (desired) |
| P4 Share token graph | token-gated stored boundary | `pytest spoilerless/tests/test_share_api.py` | IMPLEMENTED | Snapshot boundary fixed at creation; revoke/expiry 404 |
| P5 Share list | creator-scoped | `pytest spoilerless/tests/test_share_api.py` | IMPLEMENTED | Only the caller's active shares returned |
| P6 Share revoke | creator-scoped | `pytest spoilerless/tests/test_share_api.py` | IMPLEMENTED | Revoked token 404s the token graph immediately |
| X1 Contract lock | OpenAPI + FE contract | `pytest spoilerless/tests/test_frontend_contract_doc.py` (37 templates / 50 operations). Note: `test_openapi_contract.py` still pins `len(schema["paths"]) == 32` — stale vs HEAD's 37; refresh that assertion before trusting the file | IMPLEMENTED (doc contract); contract test needs refresh | All 37 path templates / 50 operations intact after every change |
| X2 Seed idempotency | MERGE-only seeding | `pytest spoilerless/tests/test_seed_idempotency.py` | IMPLEMENTED | No constraint/label drift from metadata changes |
