# HD Graf Cehennemi — v1.2 Spoiler-Safety Hardening Requirements

Gathered 2026-08-02 from the supplied "spoiler-free graph database" plan —
selectively adopting its highest-value spoiler-hardening concepts onto the
existing stack. No database migration, no rewrite, no new stack.

## Stack Constraint (locked)

Keep: Neo4j Community, FastAPI, official Neo4j Python driver, React +
TypeScript + Vite, Cytoscape.js, Google authentication, HttpOnly backend
sessions. Do NOT introduce: Memgraph, GQLAlchemy, Next.js, JWT auth, Redis,
a second graph DB, a frontend rewrite, unrestricted Cypher, social
recommendations, ratings/reviews, trivia ingestion, external TMDb/IMDb/OMDb
imports, actor scraping, or a spoiler-unrelated visual redesign.

## Active Requirements

### Progress model (PROG)

- [ ] **PROG-01**: User can view an earlier already-watched episode without lowering their watched progress — selecting it changes only the temporary view boundary and requires no unlock confirmation.
- [ ] **PROG-02**: User can unlock episodes 1..N contiguously with one confirmation; the confirmation states Episodes 1 through N will be considered watched.
- [ ] **PROG-03**: Backend enforces `1 <= view_as_of_order <= watched_through_order`; effective boundary = `min(view_as_of_order, watched_through_order)` and can never be raised by the frontend or the LLM.
- [ ] **PROG-04**: Existing single-value progress records migrate to `watched_through_order = view_as_of_order = old value` without data loss or a manual DB reset; migration is idempotent and preserves chat snapshots, ChangeSets, and revisions.

### Visibility policy (VIS)

- [ ] **VIS-01**: One central visibility-policy service owns `visible_from_order` semantics (`is_visible`, `effective_view_order`, `require_visible_resource`, metadata masking); story-sensitive data fails closed when visibility metadata is missing — no `coalesce(visible_from_order, 1)` defaults.
- [ ] **VIS-02**: Publication order is the authoritative reveal order — numeric episode ordering across seasons (S01E09 < S01E10, season-end < next-season-start), never episode-code string or season-number string ordering; flashbacks/flash-forwards do not alter reveal order.
- [ ] **VIS-03**: Every story-sensitive relationship is visible only when its own `visible_from_order` is set and satisfied, independently of its endpoint nodes; hidden relationships never affect counts, layout, degree, or GraphRAG context.
- [ ] **VIS-04**: The provenance chain Character/Event → Claim → EvidenceFragment → Source is gated at the effective boundary — a visible Claim never exposes future Evidence, visible Evidence never exposes a future Source title/locator, citation labels and external links stay safe.
- [ ] **VIS-05**: User Notes created at a later boundary are hidden when viewing an earlier boundary; Notes never reference hidden resources and never enter chat context below their creation boundary.

### Episode metadata (META)

- [ ] **META-01**: Above the effective boundary, a spoiler-sensitive episode title is replaced server-side by a generic label (e.g. "S01E05 — Episode 5"); episode code and season/episode number stay visible so the user can select and unlock.
- [ ] **META-02**: Above the effective boundary, synopsis, runtime, and spoiler-sensitive image/thumbnail are not returned in any API response; masking happens in the backend, not via CSS.
- [ ] **META-03**: Missing title-safety metadata for a future episode fails conservatively (generic label) per a documented rule; metadata decisions live in seed/domain data, never hard-coded in UI components.

### Search, autocomplete, aggregates (SEARCH)

- [ ] **SEARCH-01**: Hidden entities and aliases behave exactly like nonexistent ones in search, autocomplete, citation lookup, and node selection — a hidden exact ID returns the same public behavior as an unknown ID; timing/errors do not intentionally distinguish hidden from nonexistent.
- [ ] **SEARCH-02**: Counts and aggregates (appearance counts, degree, relationship counts, cast ordering, node sizing) are computed only from visible resources and labeled "seen so far" where displayed; no total-future counts, no last_appearance_order, no early final status (dead/alive) — even unrendered, hidden counts are absent from API responses.

### Media safety (MEDIA)

- [ ] **MEDIA-01**: Images above the effective boundary are never returned; a neutral fallback (initials placeholder) is used instead, with alt text that leaks nothing.
- [ ] **MEDIA-02**: Image URLs/filenames are never shown as user-visible text, and failed image loads must not reveal future character existence (no presence inference through request outcomes).

### Chat & GraphRAG (CHAT)

- [ ] **CHAT-01**: GraphRAG retrieval uses the backend-derived effective boundary — while viewing Episode 1 with watched_through_order 3, the assistant behaves as an Episode 1-safe assistant and the LLM cannot raise the boundary.
- [ ] **CHAT-02**: Chat history, messages, citations, and graph-focus above the current view boundary are hidden and never enter conversation memory; returning the view to a later episode restores eligible messages.
- [ ] **CHAT-03**: The boundary snapshot used for every assistant response is persisted server-side; the assistant never reveals that safer hidden information exists.

### Graph editing (EDIT)

- [ ] **EDIT-01**: New user content (Notes, custom nodes/relationships, ChangeSets) derives `visible_from_order` from the current view context — never freely chosen by the LLM, never above watched_through_order; hidden targets and cross-series targets are rejected; canonical/candidate protection preserved.
- [ ] **EDIT-02**: A stale later-boundary ChangeSet cannot be applied while viewing an earlier boundary; applying at an earlier view fails closed with a clear error.

### Documentation (DOCS)

- [ ] **DOCS-01**: A spoiler-leak threat model documents direct and indirect leak classes (titles, synopses, counts, search, images, citations, error messages, timing) with enforcement layer, query, frontend behavior, and fail-closed rule per class, plus a regression matrix.
- [ ] **DOCS-02**: Deferred features (Person/APPEARS_IN model, reviews, ratings, trivia, recommendations, awards, external wiki integration) are documented with future invariants and no placeholder UI.

## Future Requirements (deferred)

- Per-user/admin-gated LLM Settings scoping + full SSRF protection (carried from v1.1)
- Person / ACTED_AS / APPEARS_IN actor model — only when cast pages/search are actually required; appearances then count visible episodes only (`episodes_seen_so_far`)
- Reviews (spoiler_up_to_order), ratings (watched episodes only), trivia (visible_from_order), recommendations (no future-cast/plot/title leaks)
- CI/CD pipeline; pre-existing test-pollution debt; frontend lint debt (28 errors)

## Out of Scope (this milestone)

- New stack components (Memgraph, GQLAlchemy, Next.js, JWT, Redis, second graph DB) — the current stack is kept per the locked constraint
- Database migration or rewrite — this is selective hardening on the existing model
- Social features: follow lists, collaborative filtering, "also watched" recommendations, genre recs, awards, nominations
- External ingestion: TMDb/IMDb/OMDb imports, actor scraping, trivia ingestion, live wiki integration
- A "reset watched progress" feature (only the existing progress flows are adapted)
- Visual redesign unrelated to spoiler safety

## Traceability

| Requirement | Phase |
|---|---|
| PROG-01..04, VIS-01..05, META-01..03, SEARCH-01..02, MEDIA-01..02, CHAT-01..03, EDIT-01..02, DOCS-01..02 | Phase 7 — Spoiler-Safety Hardening |
