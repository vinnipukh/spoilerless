# Phase 7: Spoiler-Safety Hardening — Context

**Gathered:** 2026-08-02
**Status:** Ready for planning
**Source:** User-supplied "spoiler-free graph database" plan — selective adoption onto the existing HD Graf Cehennemi stack. No database migration, no rewrite.

<domain>
## Phase Boundary

Integrate the highest-value spoiler-hardening concepts from the supplied plan into the existing application (Neo4j Community + FastAPI + official driver, React 19 + TypeScript + Vite + Cytoscape.js, Google Sign-In, HttpOnly sessions, persisted progress, spoiler-filtered graph APIs, GraphRAG chat, ChangeSets, revisions). Keep the current stack; do not adopt the source plan's stack (Memgraph, GQLAlchemy, Next.js, JWT, Redis) or rebuild working features.

Deliverable concepts: one consistent reveal-point rule; contiguous watched progress; watched-vs-view-boundary separation; relationship-level visibility; field-level episode metadata masking; spoiler-safe media; indirect-leak protection (counts, search, paths, autocomplete, metadata, UI hints); publication-order authority; "seen so far" aggregation; documented threat model + regression matrix.
</domain>

<decisions>
## Implementation Decisions

### Stack and terminology
- **D-01:** Keep the current stack: Neo4j Community, FastAPI, official Neo4j Python driver, React + TypeScript + Vite, Cytoscape.js, Google authentication, HttpOnly backend sessions. Do not introduce Memgraph, GQLAlchemy, Next.js, JWT auth, Redis, a second graph database, a frontend rewrite, unrestricted Cypher, social recommendations, ratings/reviews, trivia ingestion, external TMDb/IMDb/OMDb imports, actor scraping, or spoiler-unrelated visual redesign.
- **D-02:** Keep `visible_from_order` as the single canonical reveal-point property for story-sensitive graph resources. Do not introduce competing names (safe_at_order, revealed_at_order, spoiler_up_to_order, last_contiguous_order).
- **D-03:** Visibility rule: resource is visible iff `visible_from_order IS NOT NULL AND visible_from_order <= effective_view_order`. Missing visibility fails closed. Never use `coalesce(visible_from_order, 1)` for story-sensitive data.
- **D-04:** Introduce one central visibility-policy service/helper so the same semantics are not reimplemented per repository: `validate_visibility_order`, `is_visible`, `effective_view_order`, `require_visible_resource`, `filter_public_metadata`, `mask_episode_metadata`, `assert_visibility_invariants`. Follow existing architecture and naming; no new framework.

### Progress model
- **D-05:** Separate `watched_through_order` (highest contiguous order the user confirmed watched) from `view_as_of_order` (temporary spoiler boundary the user wants to view). Invariant `1 <= view_as_of_order <= watched_through_order`; `effective_view_order = min(view_as_of_order, watched_through_order)`; the frontend and the LLM can never override this rule.
- **D-06:** Contiguous unlock semantics: confirming Episode N marks Episodes 1..N watched; watched_through_order and view_as_of_order both become N; the confirmation dialog states Episodes 1 through N will be unlocked; backend validates N belongs to the series and derives the global publication order; the frontend cannot submit arbitrary hidden orders. Selecting an earlier already-watched episode changes only view_as_of_order, never lowers watched_through_order, needs no unlock confirmation, hides later graph content and later chat messages/citations, invalidates or hides unsafe graph focus, and disables ChangeSets created above the selected view boundary. Do not destroy chat messages or revisions when viewing an earlier boundary.
- **D-07:** Backward-compatible migration: initialize watched_through_order from the current persisted progress and view_as_of_order from the same value; preserve user behavior, chat-message visibility snapshots, ChangeSets, and revisions; idempotent; no manual DB reset; parameterized Cypher for new properties; stable user-series scope; update seed/migration tests; document rollback behavior.

### Metadata and ordering
- **D-08:** Episode metadata gating: add `title_is_spoiler`, `title_visible_from_order`, `synopsis_visible_from_order`, `image_visible_from_order` only where the current UI needs them. Above effective_view_order: episode code and season/episode number stay visible (user must be able to select and unlock), spoiler-sensitive title becomes a generic label ("S01E05 — Episode 5"), synopsis not returned, spoiler-sensitive image/thumbnail not returned, runtime not returned if it is a spoiler signal. Masking is backend-side, never CSS. Non-spoiler titles may be returned before watched. Missing title-safety metadata for a future episode fails conservatively per a documented rule. Metadata decisions live in seed/domain data, never hard-coded in UI components.
- **D-09:** Publication order is authoritative: spoiler visibility follows release/publication order, never fictional chronology; flashbacks/flash-forwards do not alter episode_order; an event shown in Episode 1 is visible from 1 even if it occurs later in fictional chronology; an event revealed in Episode 5 stays hidden until 5 even if it describes an earlier fictional event. One stable global episode order per series. Never compare episode-code strings or derive visibility from season-number string ordering. Tests: S01E09 vs S01E10, end-of-season vs next-season start, flashback revealed later, out-of-order fictional chronology. Movie-series installments may later map to publication order; do not implement a movie-series product model now.

### Relationship and provenance visibility
- **D-10:** Relationship-level visibility: every story-sensitive relationship must be safe independently of its endpoint nodes — own `visible_from_order` non-null and satisfied, source node visible, target node visible, related Claim visible where applicable. Hidden relationships must not affect public counts, layout metadata, GraphRAG context, or existence-through-errors. Do not collapse evolving relationships into one timeless mutable property — preserve the atomic Claims/revisions model; relationship change over time is expressed through visible Claims, revisions, or time-bounded semantics, never by overwriting history.
- **D-11:** Provenance chain gating: Character/Event → Claim → EvidenceFragment → Source — every returned element valid at the effective boundary. A visible Claim must not expose future Evidence; visible Evidence must not expose a future Source title or locator; citation labels must be safe; external links must not contain visible future titles; user Notes must not reference hidden resources; Notes created at later boundaries are hidden when viewing an earlier boundary; chat context omits hidden Notes; graph-edit proposals must not target hidden Claims or entities. Series-wide Sources safe from order 1 must be documented explicitly; do not assume all Sources are safe.

### Chat, GraphRAG, editing
- **D-12:** GraphRAG uses effective_view_order, not watched_through_order alone. Retrieval tools receive the backend-derived effective boundary; the LLM cannot increase it; chat history above the current view boundary stays hidden; hidden messages never enter conversation memory; citations above the boundary stay hidden; graph_focus above the boundary is cleared or filtered; speculation uses only context visible at the selected boundary (friendly speculation must not use later watched information while viewing an earlier episode); persist the boundary snapshot used for every assistant response; never reveal that safer hidden information exists.
- **D-13:** ChangeSets and new user content: derive visible_from_order from the currently selected view context when appropriate; never let the LLM freely choose visibility; never set visibility above watched_through_order; reject hidden targets; reject cross-series targets; keep origin:user; preserve canonical and candidate protection and transaction/revision behavior. Example: watched through 3, viewing 1, user creates a Note about an Episode 1 Character → the Note is safe from Episode 1, not auto-stamped 3. Do not infer earlier visibility if proposed content includes information not supported at the current selected boundary. A stale later-boundary ChangeSet cannot apply at an earlier view.

### Leak protection and media
- **D-14:** Spoiler-safe media: an image above effective_view_order is not returned; neutral fallback (initials placeholder) or safe default; alt text must not leak hidden information; filenames and URLs never shown as user-visible text; failed image requests must not imply future character existence; external image selection curated per boundary. Smallest safe extension of the existing image system — no asset-management platform.
- **D-15:** Search/autocomplete leak protection: hidden entity names and aliases are never returned; hidden result counts never returned; hidden entities behave like nonexistent; autocomplete cannot suggest future Characters; fuzzy matching cannot reveal a future entity; search timing and errors do not intentionally distinguish hidden from nonexistent; a hidden exact ID produces the same public behavior as an unknown ID. Regression tests required.
- **D-16:** Aggregate/count protection: counts computed only from currently visible resources, labeled "seen so far" where displayed; no total future counts; no last_appearance_order; no final status (dead/alive) before the reveal point; hidden degree/future relationships never influence node sizing or layout; hidden counts absent from API responses even when unrendered. Existing at-risk aggregates: total/remaining appearance count, relationship count, node degree, episodes involving a Character, cast ordering, first/last appearance, character status, main/supporting labels, hidden-path existence, graph layout weight.
- **D-17:** Do NOT add the Person/ACTED_AS/APPEARS_IN model this phase (no actor pages, cast metadata, actor search, or immediate roadmap need). Document the safe future design in an ADR/backlog item instead. If partially implemented already, appearances count only visible episodes (`episodes_seen_so_far`), never total planned count, never last appearance.
- **D-18:** Deferred features get future invariants documented, no placeholder tables or UI: Reviews require spoiler_up_to_order and hide above the reader's effective boundary; Ratings only for watched Episodes, aggregates must not expose future quality signals; Trivia requires visible_from_order; Recommendations must not reveal future cast, plot, title, or relationship metadata.

### Threat model and query hardening
- **D-19:** Create/update a spoiler-safety document covering direct leaks (future node, relationship, Claim, Evidence, Source text, chat message) and indirect leaks (episode title, synopsis, runtime, image, poster, cast ordering, actor appearance count, character status, first/last appearance, search suggestion, autocomplete, hidden result count, node degree, path existence, graph layout, citation title, external-link label, chat-session title, ChangeSet summary, error message, timing-sensitive alternate response, cache key/stale cache) — each with enforcement layer, backend query/service, frontend behavior, test coverage, and fail-closed behavior. Include a regression matrix.
- **D-20:** Cypher hardening: prefer filtering visible resources before expanding large traversals; every public story query enforces series ID, authenticated user scope where applicable, effective view boundary, non-null visible_from_order, bounded traversal, bounded result count, parameterized inputs. Never interpolate labels, relationship types, property names, or Cypher fragments from user input or the LLM; use server-side allowlists for dynamic ontology choices. No premature Redis optimization.

### API and UX
- **D-21:** API contract: public APIs clearly separate watched_through_order, view_as_of_order, and effective_view_order; never expose internal Neo4j records; episode responses expose safe, already-masked display values (e.g. `{series_id, watched_through_order, view_as_of_order, effective_view_order, episodes:[{id, code, display_title, is_unlocked, is_current_view}]}`); keep backward compatibility where practical; update frontend API types.
- **D-22:** Frontend UX: preserve the graph-first interface and the existing design system; episode selector represents view_as_of_order; already-watched episodes selectable without re-confirming; selecting above watched_through_order opens a clear confirmation stating Episodes 1 through N will be considered watched; moving back to an earlier episode changes only the view; UI subtly distinguishes watched/unlocked, currently viewed, locked/future; spoiler-sensitive future titles use generic labels; masked episodes stay selectable for the unlock flow; no layout shift when labels change; do not clutter the header. Accessibility: episode controls keyboard accessible, locked state never communicated by color alone, confirmation dialog focus handling, generic titles have accessible labels, progress state has clear screen-reader text.

### Testing and process
- **D-23:** Backend tests per the supplied matrix: progress model (migration, contiguity, view<=watched, lower selection doesn't lower progress, unlock 1..N, cross-series rejected, unauthenticated rejected); effective boundary (graph, GraphRAG, chat history, ChangeSets, citations); episode metadata (spoiler title masked, non-spoiler visible, synopsis/image absent, conservative failure); relationships (hidden edge with visible endpoints, hidden endpoint, null visibility, no degree/count influence, no GraphRAG context); provenance (future Claim/Evidence/Source hidden, future citation rejected, future Note hidden); search (hidden entity/alias absent, exact ID behaves unknown, autocomplete, counts); media (hidden image absent, fallback, safe alt, no URL); counts (visible-only, no total, no layout influence, no early last appearance/status); chat (watched 3 viewing 1 → Episode-1-safe answer, Episode 3 messages hidden, restore on return, no memory pollution, no later context in speculation); graph edits (safe visibility derivation, hidden target rejected, protections intact, stale ChangeSet cannot apply); ordering (S01E09 < S01E10, cross-season, fictional chronology irrelevant); regression (auth, Google Sign-In, sessions, graph loading, selector, Notes, revisions, citations, GraphRAG, ChangeSets, images, seed idempotency). Frontend tests: watched/unlocked/current/locked states, masked title rendering, unlock confirmation, earlier-view selection, graph refresh, chat filtering, responsive and keyboard behavior.
- **D-24:** Implementation order: small reviewable plans — (1) repository audit + visibility terminology + threat-model documentation + progress/view domain design; (2) backward-compatible progress migration + effective-boundary service + API contract updates; (3) episode title/synopsis metadata gating + frontend selector UX; (4) relationship, Claim, Evidence, Source, Note visibility audit + Cypher hardening; (5) search/autocomplete/count leak protection + graph layout metadata protection; (6) media safety + safe character-image fallback; (7) GraphRAG, chat-history, citation, graph-focus, ChangeSet integration; (8) full regression suite + manual browser acceptance + documentation. Do not mix unrelated visual changes in.
- **D-25:** Verification: full backend pytest suite, spoiler-specific tests, GraphRAG tests, prompt-injection tests, ChangeSet tests, seed-idempotency tests, frontend tests, frontend lint, TypeScript typecheck, production build, `git diff --check`; never commit secrets; never modify real environment files. Do not claim completion while any public API response still contains a future entity name, relationship, Claim, Evidence, Source label, citation, episode synopsis, spoiler-sensitive title, media URL, count, path, chat message, or ChangeSet detail. All final reports in English.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Progress & graph visibility (current model — one field today)
- `backend/app/api/progress.py` — `visible_until_order` progress GET/POST; the single current boundary field
- `backend/app/api/graph.py` — graph API filtering by `visible_until_order` (existing spoiler filter)
- `backend/app/repository/progress.py` — `UserSeriesProgress` persistence; `visible_from_order` on nodes/relationships
- `backend/app/graph/database.py` — `Neo4jDatabase.execute_query` (single-statement, parameterized)
- `backend/app/graph/seed.py` + `data/dexter/metadata/episodes.json` — seeded episodes carry `episode_order` + `visible_from_order`; idempotent MERGE-only seeding; constraint label-set locked by `test_seed_idempotency.py`
- `docs/ROADMAP.md` lines 20, 229 — canonical spoiler-safety principles

### Chat / GraphRAG / editing
- `backend/app/services/chat.py` — `ChatService.answer_stream`, progress resolution, effective boundary today
- `backend/app/llm/pipeline.py` + `retrieval/tools.py` + `system_prompt.py` — retrieval tools, `CONTEXT_DATA_FRAMING`, prompt-injection defenses (user-owner system prompt — never edit prose)
- `backend/app/api/change_set.py` + `repository/change_set.py` — propose/confirm/revert, origin protection, revisions
- `backend/app/repository/user.py`, `backend/app/services/auth.py`, `backend/app/api/auth.py` — auth/session; dev-login `POST /api/auth/dev` gated by `AUTH_DEV_CODE`

### Frontend
- `frontend/src/App.tsx` — view state (`graph | settings`), chatOpen, watchProgress wiring
- `frontend/src/hooks/useWatchProgress.ts` — `hdgraf.watchProgress` sessionStorage shape
- `frontend/src/components/episode/EpisodeSelector.tsx` + `ConfirmAdvanceModal.tsx` — selector + unlock confirmation UI
- `frontend/src/components/settings/SettingsPage.tsx`, `components/layout/HeaderNavAction.tsx` — settings + unified header nav (08-02)
- `frontend/src/components/chat/*`, `frontend/src/hooks/useChatMessages.ts` — chat UI/hooks

### Contract / docs
- `backend/tests/test_openapi_contract.py`, `test_frontend_contract_doc.py`, `docs/frontend-api-contract.md` — locked OpenAPI inventory (33 path templates / 45 ops; adding routes requires updating all three + `_ERROR_SPECS` if a new status is used)
- `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/ROADMAP.md` — architecture/API/roadmap docs
- Runbook: `hdgrafcehennemi-pitfalls` skill (test invocation, live-DB hygiene, contract sync, baseline failures 321 passed / 5 failed / 7 errors)
</canonical_refs>

<specifics>
## Specific Ideas

- Conceptual API for the shared nav action already exists (`HeaderNavAction`); episode selector work must use existing design tokens (`h-11`, `bg-accent`, `text-muted-foreground`, `hover:bg-elevated`, ring-2 ring-ring) — no DaisyUI (not in package.json), no inline styles where shared tokens exist.
- The existing confirmation flow is `ConfirmAdvanceModal` (watchProgress.requestChange/confirmChange); the unlock dialog must gain the "Episodes 1 through N will be considered watched" copy.
- Backend test invocation: `unset PYTHONPATH && source .venv/Scripts/activate && pytest backend/tests/<file>` from repo root; frontend: `NODE_ENV=test CI=1 npm run test`.
- Frontend lint baseline: 28 pre-existing errors (do not fix in this phase); gate on 0 new errors only.
- Full-suite baseline: 321 passed / 5 failed / 7 errors (documented names); contract files must stay green.
- Integration tests run against the SHARED live Neo4j — `:AppSetting`-style global-node tests MUST backup→restore; tests creating users/sessions/progress must tear down or use unique keys.
</specifics>

<deferred>
## Deferred Ideas

- Person / ACTED_AS / APPEARS_IN actor model (document only; build when cast pages are actually required)
- Reviews (spoiler_up_to_order), Ratings (watched-only), Trivia (visible_from_order), Recommendations (no future-cast/plot leaks), awards, nominations, external wiki integration
- Movie-series product model (publication-order mapping documented as future-compatible only)
- "Reset watched progress" feature (out of scope unless one already exists)
- Per-user/admin-gated LLM Settings scoping + full SSRF protection (carried from v1.1, not part of this phase)
- CI/CD pipeline; pre-existing test-pollution and frontend-lint debt
</deferred>

---

*Phase: 07-spoiler-safety-hardening*
*Context gathered: 2026-08-02 from user-supplied spoiler-free graph plan (selective adoption)*
