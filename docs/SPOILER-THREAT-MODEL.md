# Spoilerless — Spoiler Threat Model

**Status:** DOCS-01 deliverable (plan 07-01) · **Date:** 2026-08-03
**Source inventory:** `.planning/phases/07-spoiler-safety-hardening/07-AUDIT.md` (repository audit of
leak channels, grounded in real symbols at HEAD, commit `8e286ed`).
**Locked vocabulary:** `docs/SPOILER-TERMINOLOGY.md` — read it first. `visible_from_order` is the single
canonical reveal-point property; the visibility rule is **fail closed** (D-03).

This document covers every direct and indirect spoiler leak class named in decision **D-19**. Each leak
class carries: **enforcement layer**, **backend query/service** (real symbol), **frontend behavior**,
**test coverage** (real test file), and **fail-closed rule** (what happens when the guard is missing).
A **regression matrix** closes the document.

## 1. Scope and trust boundaries

| Boundary | Description |
|---|---|
| API response → client | Any future-episode/story data rendered or returned is a leak. Masking is **backend-side per D-08**, never CSS. |
| docs → implementation | Every enforcement layer and fail-closed rule below becomes contract; later plans (07-02..07-08 per D-24) execute against it. |
| LLM tool calls | Retrieval tools receive the backend-derived **effective** boundary as a server-owned kwarg (`$visible_until_order`, 77 occurrences in `spoilerless/app/retrieval/tools.py`); the LLM can never raise it (D-12). |

## 2. Canonical verification invocations

Backend (from repo root):

```bash
unset PYTHONPATH && source .venv/Scripts/activate && pytest spoilerless/tests/<file> -k <pattern>
```

Frontend:

```bash
cd frontend && NODE_ENV=test CI=1 npx vitest run <pattern>
```

`git diff --check` must stay clean on every docs change. Full-suite baseline: 321 passed / 5 failed /
7 errors (documented pre-existing names — zero new failures is the gate, D-25).

## 3. Direct leak classes

A *direct* leak returns story content (an entity, relationship, Claim, Evidence, Source text, or chat
message) that belongs to an episode above the viewer's effective boundary.

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **Future node** | Query-level `<= boundary` filter + schema-level non-null `visible_from_order` | `NODES_QUERY` (spoiler/filter.py:48); `GET /api/series/{series_id}/graph` → `GraphService.fetch_graph` (services/graph.py:51); `GraphNode.visible_from_order: int = Field(ge=1)` (domain/graph.py:15) | Cytoscape renders only returned nodes; layout input is the filtered response only | `spoilerless/tests/test_graph_api.py` (hidden-node absence); matrix row G2 | Node with NULL or `> effective_view_order` `visible_from_order` is never returned; schema validation rejects null (fail closed). Missing guard → node leaks. |
| **Relationship** | Chain query filter: relationship + subject + object + (where applicable) Claim all `<= boundary` | `VISIBLE_CLAIMS_QUERY` (filter.py:86), `STRUCTURAL_EDGES_QUERY` (filter.py:65), `VISIBLE_USER_RELATIONSHIPS_QUERY` (filter.py:128); edges projected from visible claims (services/graph.py:87) | Edges rendered from returned set only; node degree computed from visible edges only | `spoilerless/tests/test_graph_api.py`; 07-04 adds per-relationship tests (D-10) | A relationship is visible iff its **own** `visible_from_order` is non-null and satisfied AND both endpoints are visible AND the related Claim is visible. Missing any link → hidden (D-10). |
| **Claim** | Query-level filter incl. `valid_from`/`valid_until_order` temporal window | `VISIBLE_CLAIMS_QUERY` (filter.py:86); retrieval `GET_CLAIMS_QUERY` / `CLAIMS_FOR_FRONTIER_QUERY` (retrieval/tools.py:169,47) | Claims render as edges/cards from returned set only; ChangeSet proposals must not target hidden Claims (07-04) | `spoilerless/tests/test_retrieval_tools.py`, `spoilerless/tests/test_retrieval_pipeline.py`; matrix row G3 | Claim hidden if `visible_from_order` NULL or `> boundary`, or outside validity window. No centralized `is_visible` helper yet — the rule is duplicated per query (D-04 motivation; 07-02 centralizes). |
| **Evidence** | Chain filter: Claim and Evidence both `<= boundary` | `EVIDENCE_QUERY` (filter.py:182); retrieval `EVIDENCE_FOR_CLAIMS_QUERY` / `GET_EVIDENCE_QUERY` (retrieval/tools.py:92,200) | Evidence shown only inside a visible Claim expansion | `spoilerless/tests/test_retrieval_tools.py`, `spoilerless/tests/test_citations.py`; matrix row G4 | A visible Claim must never expose future Evidence (D-11). Evidence hidden if its own or its Claim's order fails. Missing guard → provenance chain leaks. |
| **Source text** | Chain filter: referencing relationship and Source both `<= boundary` | `SOURCES_QUERY` (filter.py:153); retrieval `SOURCES_FOR_CLAIMS_QUERY` / `GET_SOURCES_QUERY` (retrieval/tools.py:111,220); `GraphSource` (domain/graph.py:50) returns `locator` | Citation chips / external links from returned Sources only | `spoilerless/tests/test_citations.py`, `spoilerless/tests/test_retrieval_tools.py`; matrix row G5 | Future Source title or locator never returned. Series-wide Sources safe from order 1 must be **documented explicitly**; do not assume all Sources are safe (D-11). |
| **Chat message** | Service-layer boundary resolution + per-message persisted snapshot | `ChatService.answer_stream` (services/chat.py); boundary from `_resolve_or_create_progress` (services/chat.py:236) / `ensure_progress_for_chat` (services/chat.py:225); messages persist `visible_until_order_snapshot` (repository/chat.py:133,151; domain/chat.py:53) | Message list renders only boundary-visible messages; hidden messages never enter conversation memory | `spoilerless/tests/test_chat_api.py`, `spoilerless/tests/test_chat_persistence.py`; matrix row G6 | Messages above the **effective** boundary (min of view/watched) are hidden; the retrieval pipeline (retrieval/pipeline.py) consumes only the effective boundary (07-07). Missing guard → chat history leaks. |

## 4. Indirect leak classes

An *indirect* leak reveals the **existence, extent, or metadata** of hidden story content without
returning the content itself.

### 4.1 Titles and episode metadata (I1–I4)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I1 — Episode title** | **Implemented (D-08).** Backend masking via `title_is_spoiler` / `title_visible_from_order` and `mask_episode_metadata` | `SERIES_EPISODES_QUERY` (spoiler/filter.py:18) returns `title_is_spoiler` / `title_visible_from_order` (filter.py:28-29); `mask_episode_metadata` (spoiler/policy.py:150) computes `display_title`; `SeriesService` merges it (services/series.py:55); `EpisodeResponse.display_title` (domain/series.py:24) | `EpisodeSelector.tsx` renders `{episode.code} — {episode.display_title ?? episode.title}` with a Lock icon on locked episodes (EpisodeSelector.tsx:56,61-62,85) | 07-03 adds episode-metadata tests (matrix row M1) | Above `effective_view_order`, spoiler-sensitive title is replaced by a generic label (`S01E05 — Episode 5`); code + season/episode number stay visible (D-08). Missing guard → future titles leak in the selector. |
| **I2 — Synopsis** | Absent today; D-08 `synopsis_visible_from_order` | No synopsis field in seed or queries | Not rendered (field absent) | 07-03 metadata tests (matrix row M2) | Synopsis must not be returned above the boundary once added; absence is not a leak. |
| **I3 — Runtime** | Absent today; runtime is a spoiler signal (D-08) | No runtime field | Not rendered | 07-03 metadata tests (matrix row M3) | Runtime must not be returned above the boundary once added. |
| **I4 — Image / poster** | Query-level (images ride on `<= boundary` nodes) | `NODES_QUERY` returns `node.image_url` / `node.image_source_url`; `GraphNode` carries both (domain/graph.py:18-19); seed `data/dexter/seed/characters.json` — 6 characters carry `image_url` (`dexter_morgan`, `debra_morgan`, `angel_batista`, `maria_laguerta`, `james_doakes`, `rita_bennett`), all `visible_from_order:1`; `paul_bennett`, `rudy_cooper`, and `harry_morgan` carry no `image_url` field | Neutral initials fallback for hidden images; alt text safe; no URL as visible text | 07-06 media tests (matrix row M4) | Image above `effective_view_order` is not returned; failed image requests must not imply future character existence (D-14). Missing guard → character image leaks existence. |

### 4.2 Cast and aggregates (I5–I8)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I5 — Cast ordering** | Deferred feature (D-17) — no Person/ACTED_AS/APPEARS_IN model this phase | None (character labels from seed only) | Not rendered | 07-08 regression guard (matrix row C1) | Cast order is never exposed before its reveal point; design documented in `docs/SPOILER-DEFERRED-DESIGN.md`, not built. |
| **I6 — Actor appearance count** | Visible-only counting (D-16) | `GRAPH_SUMMARY_COUNTS_QUERY` (retrieval/tools.py:239) counts only visible entities/claims/evidence/sources; `get_current_visible_graph_summary` (tools.py:746) | Counts labeled "seen so far" where displayed | 07-08 regression guard (matrix row C2) | Any future appearance count is `episodes_seen_so_far` — never total planned, never last appearance (D-16/D-17). |
| **I7 — Character status** | Not returned by any current query (D-16) | None | Not rendered | 07-08 regression guard (matrix row C3) | No final status (dead/alive, main/supporting) before the reveal point; never add `last_appearance_order`. |
| **I8 — First/last appearance** | Not exposed today (D-16) | None | Not rendered | 07-08 regression guard (matrix row C4) | Forbidden before the reveal point — documented in `docs/SPOILER-DEFERRED-DESIGN.md`, not built. |

### 4.3 Search, autocomplete, counts (I9–I11)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I9 — Search suggestion** | Query-level fail-closed + server allowlist (D-15) | `SEARCH_ENTITIES_QUERY` (retrieval/tools.py:128) filters `node.visible_from_order IS NOT NULL AND <= $visible_until_order`; `search_entities` (tools.py:442) allowlists types ∩ narrative labels; empty/whitespace query → `[]` | Search results render only returned entities | `spoilerless/tests/test_retrieval_tools.py`; 07-05 timing/indistinguishability tests (matrix row S1) | Hidden entities behave like nonexistent: hidden name/alias never returned, hidden exact ID behaves like unknown ID, errors and timing do not distinguish hidden from nonexistent (D-15). |
| **I10 — Autocomplete** | No endpoint today (D-15) | None | No entity autocomplete in UI | 07-05 adds autocomplete guard tests (matrix row S2) | Any future autocomplete must reuse the same boundary-filtered search primitive; it cannot suggest future Characters. |
| **I11 — Hidden result count** | Query-level visible-only counting (D-16) | `GRAPH_SUMMARY_COUNTS_QUERY` (tools.py:222); list endpoints return only visible rows | Counts absent from API responses even when unrendered | `spoilerless/tests/test_retrieval_tools.py`; matrix row S3 | Hidden counts never appear in API responses; totals reflect visible resources only. |

### 4.4 Graph layout and degree (I12–I14)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I12 — Node degree** | Backend query filtering (indirect) | No degree field on `GraphEdge`; frontend computes degree from returned edges only | Cytoscape sizing uses visible edges only | `spoilerless/tests/test_graph_api.py`; 07-04 relationship hardening tests (matrix row L1) | Hidden degree / future relationships never influence node sizing or layout (D-16). |
| **I13 — Path existence** | Tool-level fail-closed (D-15) | `find_path` (retrieval/tools.py:474) BFS over visible claims only (`CLAIMS_FOR_FRONTIER_QUERY`); hidden path → `{"found": False}` identical to no path | Path result rendered as returned | `spoilerless/tests/test_retrieval_tools.py`; 07-05 lock (matrix row L2) | Hidden path existence is never revealed; response is byte-identical to "no path". |
| **I14 — Graph layout** | Backend filtering (indirect) | Layout input = filtered `GET /graph` response only | Cytoscape layout consumes returned nodes/edges only | `spoilerless/tests/test_graph_api.py`; 07-04/07-05 (matrix row L3) | Layout metadata (weights, degrees) must not reflect hidden resources (D-16). |

### 4.5 Citations and external links (I15–I16)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I15 — Citation title** | Query-level chain filter | `SOURCES_FOR_CLAIMS_QUERY` / `GET_SOURCES_QUERY` (tools.py:106,205) return only boundary-visible source labels; pipeline citations derive from returned sources | Citation chips from returned sources only | `spoilerless/tests/test_citations.py`, `spoilerless/tests/test_retrieval_pipeline.py`; 07-07 (matrix row T1) | Citations above the boundary stay hidden; the retrieval pipeline passes the **effective** boundary and never hints that safer information exists (D-12). |
| **I16 — External-link label** | Query-level (source visibility) | `SOURCES_QUERY` (spoiler/filter.py:137) returns `source.locator` (URL), exposed on `GraphSource` (domain/graph.py:50) | External links rendered from returned Sources; safe rendering rules in 07-06 | `spoilerless/tests/test_retrieval_tools.py`; 07-04/07-06 (matrix row T2) | External links must not contain visible future titles; `locator` is user-visible text and must be curated per boundary (D-11/D-14). |

### 4.6 Chat sessions and ChangeSets (I17–I18)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I17 — Chat-session title** | Auth scoping (user-owned sessions) | `ChatSessionCreateRequest.title` user-supplied (domain/chat.py:77; imported api/chat.py:22, used api/chat.py:67); session lists scoped to user + series | Session picker lists own sessions | `spoilerless/tests/test_chat_api.py`; 07-07 check (matrix row H1) | Titles are user-authored (safe by origin) but must be re-checked in 07-07 so session lists never reveal content above the view boundary (D-12). |
| **I18 — ChangeSet summary** | Service-level staleness check | `ChangeSetResponse.visible_until_order_snapshot` (domain/change_set.py:274); `ChangeSetStale` → 409 `changeset_stale` on confirm (api/change_set.py:57-63); `ChangeSetStale` (repository/change_set.py:74) | Card shows stale state, replaces Confirm/Reject | `spoilerless/tests/test_change_set_api.py`, `test_change_set_confirmation.py`; 07-07 (matrix row H2) | A stale later-boundary ChangeSet cannot apply at an earlier view; snapshot must be compared against the **effective** boundary (D-13). |

### 4.7 Errors and timing (I19–I20)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I19 — Error message** | Envelope-level generic codes | Generic 404 `resource_not_found` (api/progress.py:53-54, api/user_content.py:34-36); 422 `invalid_visible_until_order` when order is not a persisted episode (api/graph.py:63-67) | Error toast shows generic message | `spoilerless/tests/test_progress_api.py`, `test_user_content_api.py`, `test_graph_api.py`; 07-05 verify 422 path (matrix row E1) | Errors never distinguish hidden from nonexistent (D-15): same code for both. |
| **I20 — Timing-sensitive alternate response** | Tool-level fail-closed | Retrieval tools return empty results for hidden (fail closed); no timing variance measured | N/A (server-side) | 07-05 adds timing-indifference regression tests (matrix row E2) | Search timing and errors do not intentionally distinguish hidden from nonexistent (D-15). |

### 4.8 Cache and ordering (I21–I22)

| Class | Enforcement layer | Backend query / service | Frontend behavior | Test coverage | Fail-closed rule |
|---|---|---|---|---|---|
| **I21 — Cache key / stale cache** | Frontend sessionStorage + backend-authoritative reconciliation | No server cache of visibility; backend is authoritative | `sessionStorage['spoilerless.watchProgress']` (useWatchProgress.ts:21) holds a single `visibleUntilOrder`; reconciled on mount | `frontend/src/hooks/useWatchProgress.test.ts`; 07-03 adds watched/view split (matrix row K1) | Stale cached progress must never widen the effective boundary; D-05 storage shape (watched/view split) lands in 07-03. |
| **I22 — Episode code / season strings** | Numeric-order authority (D-09) | `SERIES_EPISODES_QUERY` orders by `episode_order` (numeric); `code` returned for display; selector selects by `episode_order` | EpisodeSelector keys/selects by numeric order | 07-03 ordering regression (matrix row O1) | Never compare episode-code strings or season-number strings for visibility; episode-code ordering is never used for reveal decisions (D-09). |

## 5. Completion gate (D-25)

Completion of spoiler-safety work is **never claimed** while any public API response still contains a
future entity name, relationship, Claim, Evidence, Source label, citation, episode synopsis,
spoiler-sensitive title, media URL, count, path, chat message, or ChangeSet detail. Verification is
the full backend pytest suite (zero new failures vs the documented 321/5/7 baseline), the frontend
vitest suite, frontend lint (0 new errors vs the 28-error baseline), TypeScript typecheck, production
build, and `git diff --check` — plus the regression matrix below, executed green.

## 6. Regression matrix

One row per leak class: **leak class → enforcement → test file/command → pass gate**. Backend
invocation is `unset PYTHONPATH && source .venv/Scripts/activate && pytest spoilerless/tests/<file> -k <pattern>`
from the repo root; frontend invocation is `cd frontend && NODE_ENV=test CI=1 npx vitest run <pattern>`.
Rows marked "07-0N adds" are new tests owned by the named plan per D-24; the file they live in exists
at HEAD.

| Leak class | Enforcement | Test file / command | Pass gate |
|---|---|---|---|
| G1 Future node | `NODES_QUERY` + `GraphNode` schema | `pytest spoilerless/tests/test_graph_api.py -k "hidden or visible"` | Future nodes absent from response; null `visible_from_order` rejected |
| G2 Relationship | Chain queries (filter.py) | `pytest spoilerless/tests/test_graph_api.py -k "relationship or edge"` (+ 07-04 adds `-k "hidden"`) | Hidden edge never returned; no degree/layout influence |
| G3 Claim | `VISIBLE_CLAIMS_QUERY` + temporal window | `pytest spoilerless/tests/test_retrieval_tools.py -k "claim"` (+ 07-04 adds target-rejection tests) | Hidden/invalid-window Claim absent; edit proposals reject hidden targets |
| G4 Evidence | `EVIDENCE_QUERY` chain | `pytest spoilerless/tests/test_retrieval_tools.py -k "evidence"` (+ 07-04) | Visible Claim never exposes future Evidence |
| G5 Source text | `SOURCES_QUERY` chain | `pytest spoilerless/tests/test_citations.py -k "source"` (+ 07-04) | Future Source title/locator absent |
| G6 Chat message | service boundary + snapshot | `pytest spoilerless/tests/test_chat_api.py -k "boundary or hidden"`, `test_chat_persistence.py` (+ 07-07) | Messages above effective boundary hidden; no memory pollution |
| M1 Episode title | D-08 masking (07-03) | 07-03 adds `pytest spoilerless/tests/test_episode_metadata.py -k "title"` (or extends `test_progress_api.py`) | Spoiler title masked to generic label; non-spoiler visible |
| M2 Synopsis | `synopsis_visible_from_order` (07-03) | 07-03 metadata tests `-k "synopsis"` | Synopsis absent above boundary |
| M3 Runtime | D-08 (07-03) | 07-03 metadata tests `-k "runtime"` | Runtime absent above boundary |
| M4 Image / poster | D-14 (07-06) | 07-06 adds `pytest spoilerless/tests/test_media_safety.py -k "image"` | Future image absent; fallback + safe alt; no URL text |
| C1 Cast ordering | Deferred (D-17) | 07-08 regression guard | No Person/APPEARS_IN exposure; no cast order in any response |
| C2 Appearance count | `episodes_seen_so_far` only (D-16) | 07-08 guard (extends `test_retrieval_tools.py -k "count"`) | Counts visible-only; never total planned, never last appearance |
| C3 Character status | D-16 | 07-08 guard | No final status before reveal point |
| C4 First/last appearance | D-16 | 07-08 guard | Never exposed before reveal point |
| S1 Search suggestion | `SEARCH_ENTITIES_QUERY` + allowlist | `pytest spoilerless/tests/test_retrieval_tools.py -k "search"` (+ 07-05 timing tests) | Hidden entity/alias absent; exact-ID behaves unknown; timing/error indifferent |
| S2 Autocomplete | Boundary-filtered primitive (07-05) | 07-05 adds `-k "autocomplete"` tests | Autocomplete never suggests future Characters |
| S3 Hidden result count | visible-only counts | `pytest spoilerless/tests/test_retrieval_tools.py -k "count or summary"` (+ 07-05) | Hidden counts absent from responses |
| L1 Node degree | visible edges only | `pytest spoilerless/tests/test_graph_api.py -k "degree"` (+ 07-04) | Degree/layout unaffected by hidden relationships |
| L2 Path existence | `find_path` fail-closed | `pytest spoilerless/tests/test_retrieval_tools.py -k "path"` (+ 07-05) | Hidden path response identical to no-path |
| L3 Graph layout | filtered response only | `pytest spoilerless/tests/test_graph_api.py -k "layout or summary"` (+ 07-04/07-05) | Layout metadata reflects visible resources only |
| T1 Citation title | effective-boundary pipeline | `pytest spoilerless/tests/test_citations.py`, `test_retrieval_pipeline.py` (+ 07-07) | Citations above boundary hidden; no "safer info exists" hints |
| T2 External-link label | source visibility + curation | `pytest spoilerless/tests/test_retrieval_tools.py -k "source or locator"` (+ 07-04/07-06) | Links never contain visible future titles |
| H1 Chat-session title | auth scoping (07-07 check) | `pytest spoilerless/tests/test_chat_api.py -k "session"` (+ 07-07) | Session lists never reveal above-boundary content |
| H2 ChangeSet summary | snapshot vs effective boundary | `pytest spoilerless/tests/test_change_set_api.py -k "stale"`, `test_change_set_confirmation.py` (+ 07-07) | Stale later-boundary ChangeSet cannot apply at earlier view |
| E1 Error message | generic envelopes | `pytest spoilerless/tests/test_progress_api.py -k "not_found"`, `test_user_content_api.py`, `test_graph_api.py` (+ 07-05) | Hidden and nonexistent produce identical errors |
| E2 Timing indifference | fail-closed tools | 07-05 adds `-k "timing"` tests | Search timing/errors do not distinguish hidden from nonexistent |
| K1 Cache / stale cache | backend-authoritative + D-05 split | `cd frontend && NODE_ENV=test CI=1 npx vitest run useWatchProgress` (+ 07-03) | Stale cache never widens effective boundary |
| O1 Episode code / season strings | numeric `episode_order` authority | `pytest spoilerless/tests/test_progress_api.py -k "order"` (+ 07-03 ordering tests) | Reveal decisions never compare code/season strings (S01E09 < S01E10, cross-season, flashback) |
| X1 Contract lock | OpenAPI + FE contract | `pytest spoilerless/tests/test_openapi_contract.py`, `test_frontend_contract_doc.py` | All 33 path templates / 45 operations intact after every change |
| X2 Seed idempotency | MERGE-only seeding | `pytest spoilerless/tests/test_seed_idempotency.py` | No constraint/label drift from metadata changes |
