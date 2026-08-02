# Phase 6: Spoiler-Safe GraphRAG Chat and Graph-Editing Agent - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning
**Source:** PRD Express Path (`06-PRD-SOURCE.md` — pasted in full as the `/gsd-plan-phase 6` command arguments)

<domain>
## Phase Boundary

Add a conversational GraphRAG interface to the existing premium Cytoscape graph workspace: the authenticated user asks questions about the selected series and gets answers grounded only in graph data visible up to their **persisted, backend-authoritative** watch progress, with validated Claim/Evidence/Source citations and graph-node/edge highlighting. The same agent also supports safe graph modification through a typed propose/confirm `ChangeSet` flow — the LLM proposes structured operations, never executes Cypher, and the backend independently validates, transacts, and audits every mutation.

This phase opens root `ROADMAP.md` milestone 9 ("LLM chat, later phase"), which was explicitly out of scope for Prototype v0 (shipped as milestone v1.0, archived). It is **not** a v0 requirement; it is tracked as `RAG-01..RAG-17` in `REQUIREMENTS.md` under "Phase 6 Requirements" (separate from the closed 30/30 v0 table). Functional prerequisites are Phase 3 (origin distinction: canonical/candidate/user) and Phase 4 (Revision model) — both complete. Phase 5 / 05.1 (extraction preparation / candidate-review UI) are sequential neighbors in the roadmap but are **not** functional dependencies of this phase; this phase does not touch the `candidate` origin content pipeline.

**In this phase:** watch-progress persistence backend model, spoiler-safe allowlisted retrieval tool layer, LLM provider abstraction, GraphRAG-lite context pipeline, grounded/cited answers, versioned system prompt with injection defenses, chat session/message persistence with boundary-snapshot visibility, streaming chat REST API, typed ChangeSet propose/confirm/apply flow reusing the Phase 4 Revision model, frontend chat UI integrated into the existing right-workspace, graph-focus synchronization, comprehensive backend+frontend test coverage, and documentation.

**Not in this phase:** any real automated ingestion/extraction, unrestricted text-to-Cypher, autonomous unconfirmed writes, canonical-data deletion, admin/moderator roles, billing, multi-model routing, web search, subtitle/screenplay ingestion, ontology auto-expansion, voice chat, native mobile, real-time collaborative editing, production K8s deployment, or any further graph-visual redesign.

</domain>

<decisions>
## Implementation Decisions

Every item below is a locked decision from `06-PRD-SOURCE.md`. REQ-IDs in brackets map to `REQUIREMENTS.md`.

### Watch Progress is Backend-Authoritative [RAG-01]
- Introduce a persisted per-user, per-series watch-progress record — conceptually `(:User)-[:HAS_PROGRESS]->(:UserSeriesProgress)-[:FOR_SERIES]->(:Series)` with `id, user_id, series_id, visible_until_order, updated_at` — or an equivalent representation only if the repository already has one (research confirmed it does not: `GET /api/series/{id}/graph` currently takes `visible_until_order` as a plain validated query parameter — see `canonical_refs`).
- Every GraphRAG request resolves progress server-side from this record; the LLM and every retrieval/mutation tool receive the resolved boundary internally and cannot choose or raise it.
- Frontend may *request* a progress change through the existing confirmation-modal UX; the backend validates and persists it.
- Session owners cannot read another user's progress. Missing/invalid progress fails closed (no data, not an error that leaks existence).
- The existing `/api/series/{id}/graph` endpoint and the new chat retrieval tools must use compatible visibility semantics — do not fork the spoiler model. Existing episode selection must keep working unmodified from the user's perspective.

### Chat and Message Persistence [RAG-09]
- `ChatSession` (id, user_id, series_id, title, created_at, updated_at, optional deleted_at if it matches repo soft-delete conventions) and `ChatMessage` (id, session_id, role, content, created_at, `visible_until_order_snapshot`, status, citations, graph_focus, change_set_id) are persisted per user.
- Every assistant message records the exact `visible_until_order` used to generate it.
- **Critical regression scenario (must have a test):** user reaches Episode 3, asks a question, gets an Episode-3-boundary answer, moves progress back to Episode 1, reopens the chat — the Episode-3 answer must not leak through history, previews, titles, citations, or ChangeSets, and must not enter LLM conversation memory. It is **hidden, not deleted** — raising progress again can re-reveal it. Every read verifies ownership + series match + current progress + message visibility.

### Backend Chat API [RAG-10]
- Series-scoped REST family (adapt names to existing conventions, keep consistent): `POST/GET /api/series/{series_id}/chat/sessions`, `GET/DELETE .../sessions/{session_id}`, `POST .../sessions/{session_id}/messages` (+ `/stream` variant).
- Explicit Pydantic request/response schemas, existing auth dependency, ownership validation, generic 404 for inaccessible sessions, existing error envelope, bounded message/history length, bounded concurrent generations, cancellation/disconnect handling.
- Streaming (SSE or fetch-compatible) sends incremental answer text, ends with a structured final event: message ID, citations, graph_focus, proposed ChangeSet. Never streams chain-of-thought, raw tool reasoning, or provider diagnostics. Keep a non-streaming endpoint for tests/fallback.

### LLM Provider Abstraction [RAG-04]
- Backend-only; no API key ever reaches frontend code, logs, or Revision records. Research confirmed no existing LLM/provider code in the repo — this is new.
- OpenAI-compatible config via env vars, adding only what's needed from: `LLM_ENABLED, LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_MAX_OUTPUT_TOKENS, LLM_TEMPERATURE, LLM_MAX_TOOL_ROUNDS, LLM_MAX_CONTEXT_ITEMS, LLM_MAX_CONTEXT_CHARACTERS`.
- A provider interface with a real implementation and a **deterministic fake provider for tests** (tests must never make real LLM network calls). Structured-output/tool-call support, timeout handling, bounded safe-only retries (no unlimited loops), clear disabled-provider error. Provider failures are infra failures (503), never authentication errors.

### Spoiler-Safe Retrieval Tools [RAG-02, RAG-03]
- Explicit allowlisted typed tools, exact names may adapt but responsibilities stay explicit: `search_entities, get_entity, get_neighborhood, find_path, get_timeline, get_claims, get_evidence, get_sources, get_current_visible_graph_summary, get_user_notes` (inputs per PRD §5).
- Every tool independently (not just at the pipeline entry) enforces: parameterized queries only, mandatory series scope, `visible_until_order` from backend progress (never model/tool input), `visible_from_order IS NOT NULL AND visible_from_order <= resolved_visible_until_order` on story-sensitive nodes/relationships/Claims/Evidence/Sources, cross-series rejection, bounded traversal depth, bounded result counts, allowlisted labels/relationship types only (no interpolation), and **no raw Cypher from user or model, ever**.
- Hidden resources must behave as nonexistent everywhere — no leakage through counts, path existence, error message differences, timing, search suggestions, autocomplete, citation metadata, or session titles.

### Retrieval and Context-Building Pipeline [RAG-05]
- Deterministic pipeline: validate input → resolve current user → resolve persisted progress → intent/entity planning → allowlisted tool calls (model chooses which, never writes Cypher) → spoiler-filtered results → context normalization → LLM answer → citation validation → graph-focus extraction → stream response. Bounded tool-call rounds; no recursive/runaway tool calls.
- Context builder deduplicates entities/claims/evidence, prioritizes direct evidence over distant neighbors, preserves stable IDs and source locators, omits User/Session/ChatSession/auth data and hidden data and irrelevant properties, stays within configured size limits, prefers verified/canonical claims while retaining origin metadata, and distinguishes evidence from inference. No secrets/PII in model context. Structured context sections: series context, current watched boundary, relevant entities, relevant relationships, claims, evidence fragments, sources, user notes.

### Answer Grounding and Citations [RAG-07, RAG-08]
- Public `Citation` model: `claim_id, evidence_id, source_id, source_label, source_type, episode_code, locator, optional excerpt (bounded), related_node_ids, related_edge_ids`.
- Citation IDs are validated against retrieved context; hallucinated/hidden-record citations are rejected/removed. Insufficient evidence → explicit uncertainty answer, never an invented claim. Response distinguishes graph fact / candidate claim / user-authored statement / assistant inference.
- Public response shape: `{ message: {id, content, created_at, visible_until_order_snapshot}, citations: [...], graph_focus: {node_ids, edge_ids}, proposed_change_set }`.
- Future-content questions never confirm/deny existence, name, or count of hidden entities — no "you haven't met them yet," just "the watched graph doesn't contain enough information."

### System Prompt and Prompt-Injection Defense [RAG-06]
- Versioned backend system prompt (see PRD §8 for the full required content list: spoiler-safety, tool-only access, no raw Cypher, no pretraining-memory answers, ChangeSets require confirmation, cite evidence, state insufficiency, follow user's language, never reveal the prompt/hidden tool data/reasoning).
- Notes, Claims, Evidence, Sources, and chat history are **untrusted data**, never instructions — this must hold even when they contain strings like "ignore previous instructions," "reveal all future episodes," "execute this Cypher," "delete every node," "print the system prompt." Tests must exercise exactly these strings via malicious graph content and assert they're treated as quoted data.

### Safe Graph-Editing Agent [RAG-11, RAG-12]
- Two-stage flow. Stage 1 (Propose): model constructs a typed `ChangeSet`, backend validates it, frontend shows a readable diff, **no DB mutation occurs**. Stage 2 (Confirm+Apply): explicit user confirmation, backend revalidates against current graph/progress, applies the whole ChangeSet in one transaction, records revision/audit metadata, frontend refreshes affected data.
- `ChangeSet`: id, user_id, series_id, chat_session_id, status (`draft | awaiting_confirmation | applied | rejected | failed | reverted`), visible_until_order_snapshot, summary, operations, created_at, confirmed_at, applied_at, revision_id, idempotency_key.
- Operations are an **explicit Pydantic discriminated union** — adapt exact type names to existing domain ontology/APIs, but cover: create/update/delete node, create/update/delete relationship, create/update/delete claim, attach_evidence, create/update/delete note.
- Reject: arbitrary labels/relationship types/properties, raw Cypher, hidden IDs, cross-series IDs, model-generated database IDs, model-chosen `visible_from_order`.
- Server always: generates stable IDs, validates ontology labels/predicates/property schemas, confirms targets belong to the selected series and are currently visible, derives `visible_from_order` server-side (never above current progress), assigns `origin:user` + creator user ID, validates **all** operations before applying **any**, applies transactionally with full rollback on failure, honors the idempotency key against replay, uses optimistic conflict detection, and preserves referential integrity (no prohibited orphaning of Claims/Evidence).

### Canonical and Candidate Content Stays Protected [RAG-13]
- Only `origin:user` resources are directly mutable — unchanged invariant from Phase 3. The assistant never silently updates/deletes `origin:canonical` or `origin:candidate`.
- Requested edits to canonical/candidate content become a user-origin override/annotation/note/replacement proposal instead, clearly shown as not changing the canonical record, linked to it where the ontology already supports linking. No new ontology relation invented without justification; no admin/moderator roles introduced in this phase; never claim the assistant overwrote canonical history when it didn't.

### Destructive Actions and Confirmation [RAG-14]
- Explicit confirmation required for: delete node/relationship/claim/evidence, multi-operation ChangeSets, changes touching >1 graph element, operations that may detach dependent user content. **The chat message itself is never confirmation.**
- Frontend confirmation UI shows: human-readable summary, per-operation before/after values, affected graph elements, visibility/episode placement, warnings, Confirm/Reject controls.
- On confirm, backend re-reads current user, progress, resource origin, resource version, series ownership. A ChangeSet snapshotted at a higher boundary than the user's (since-lowered) current progress becomes non-applicable and must be regenerated — never silently applied against stale/unsafe state.

### Revision, Audit, and Revert [RAG-15]
- Every applied ChangeSet becomes a Revision (reuse/extend the Phase 4 model) carrying: revision ID, ChangeSet ID, user ID, series ID, timestamp, operation types, affected IDs, before/after snapshot, visible_until_order snapshot, and model/prompt-version/app-version identifiers where useful. Never store API keys, raw auth/session tokens, or private model reasoning.
- Revert (for user-origin changes, where safe) creates a **new** Revision, validates current state, avoids overwriting unrelated later changes, fails with a conflict when unsafe, and requires explicit confirmation. A minimal revert implementation is acceptable, but every applied change must remain auditable regardless.

### Chat Frontend [RAG-16]
- Audit the existing chat-adjacent UI with the UI/UX Pro Max skill before building, and review visual hierarchy/accessibility/responsiveness after.
- Graph stays the primary surface — the right workspace gets an Inspector/Chat mode toggle or a well-designed resizable split; **do not** replace the graph with a full-screen chat page. Chat is collapsible.
- Required: session list/selector, new-conversation action, streaming text, stop/cancel, retry-on-recoverable-failure, timestamps, current series+episode badge, citation chips/cards with "Show in graph," proposed-change cards with confirm/reject and applied/rejected status, visible error states, disabled-provider state, empty-state suggestions, accessible keyboard behavior, responsive narrow-screen behavior.
- Never display: chain-of-thought, raw tool calls, raw Cypher, provider secrets/diagnostics, or hidden visibility metadata beyond what's useful as episode context.

### Graph Synchronization [RAG-17]
- `graph_focus` on an answer highlights/dims the relevant existing nodes/edges, fits/centers without destroying the user's current view, is clearable, and preserves existing entity-inspector behavior.
- Applying a ChangeSet refetches/incrementally updates only affected graph data, shows new user nodes/edges, preserves episode filtering + character images + layout stability, animates subtly, avoids unnecessary full relayout, and selects the new/changed resource where helpful.
- Progress decreasing immediately hides graph resources/chat messages/citations beyond the new boundary, invalidates unsafe draft ChangeSets, and clears any graph focus referencing now-hidden resources.

### Rate Limits and Resource Safety
- Bound: input length, messages loaded into context, retrieval results, traversal depth, tool rounds, ChangeSet operation count, concurrent generations per user. Handle timeouts, provider failures, request cancellation. No unbounded DB queries. Reuse existing middleware patterns; no billing system.

### Localization
- The assistant follows the user's language (PRD's own worked examples are in Turkish — e.g. "Dexter'ın şu ana kadar kimlerle çalıştığını göster" — answer in Turkish, cite evidence, highlight the visible subgraph). This is a runtime behavior (match the question's language), not a build-time i18n requirement on the UI chrome itself.

### Claude's Discretion
- Exact tool/endpoint/type names (PRD explicitly allows adapting to existing conventions as long as responsibilities and safety properties stay explicit).
- Whether `UserSeriesProgress` is a first-class Neo4j node/relationship pair or a simpler embedded property on the existing `(:User)`-adjacent structure — PRD allows "a relational or different representation... only if already used by the repository"; research found no existing progress persistence, so the planner/researcher should pick the representation that best fits `backend/app/graph/database.py` and `backend/app/domain/*` conventions already in place.
- Exact SSE vs. chunked-fetch streaming transport choice.
- Exact entity/intent-planning strategy inside "the model may decide which allowlisted retrieval tools to call" (tool-calling loop shape) — bounded by `LLM_MAX_TOOL_ROUNDS`, but the internal orchestration pattern is an implementation choice.
- Whether this phase's scope requires a `## PHASE SPLIT RECOMMENDED` split into sub-phases (e.g., 6a backend retrieval+chat, 6b graph-editing agent, 6c frontend) — explicitly the planner's call per its own context-budget assessment; this CONTEXT.md does not pre-decide phase boundaries.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Master project spec (has its own GraphRAG-lite design — reconcile, don't contradict)
- `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md` §2.2 "Spoiler-Aware GraphRAG Chat" and §10 "GraphRAG-Lite Design" (lines ~93-120, ~735-798) — the project's own pre-existing GraphRAG sketch (entity extraction → parameterized Cypher → spoiler-filtered context → cited LLM answer). This PRD is a superset (adds persisted watch progress, chat persistence, and the ChangeSet graph-editing agent on top of it) — treat V2 as historical intent, this CONTEXT.md as the authoritative current scope.
- `ROADMAP.md` (root) §"Milestone 9 — LLM chat, later phase" — canonical milestone this phase opens.

### Watch progress / spoiler boundary (confirmed via research — currently frontend/query-param driven, NOT backend-persisted)
- `backend/app/api/graph.py` — `GET /api/series/{series_id}/graph` currently takes `visible_until_order` as a validated request parameter (`VisibleUntilOrder` from `backend/app/domain/user_content.py`), not a persisted per-user value. This is the exact anti-pattern PRD §1 warns against; Phase 6 must introduce the missing persisted-progress layer without breaking this endpoint's existing contract/behavior.
- `backend/app/domain/user_content.py` — defines `VisibleUntilOrder` (Annotated validated type) and the existing user-content domain models to extend/follow for ChangeSet operation shapes.
- `backend/app/spoiler/filter.py` — existing backend spoiler-filtering enforcement point; new retrieval tools must compose with (not duplicate/diverge from) this filtering logic.
- `backend/app/services/graph.py`, `backend/app/domain/graph.py` — current graph response shape/service the researcher should fully catalog.

### Auth / current-user model (existing, reuse — do not rebuild)
- `backend/app/api/auth.py` (`get_current_user`, line ~224) — existing session-cookie-backed auth dependency; chat/ChangeSet endpoints must use this same dependency for ownership enforcement.
- `backend/app/services/auth.py`, `backend/app/repository/session.py`, `backend/app/repository/user.py` — session/user persistence backing auth; `UserSeriesProgress` should key off the same `user_id` this layer produces.

### Notes / custom-content / origin invariant (existing, Phase 3 — extend, don't reinvent)
- `backend/app/domain/user_content.py`, `backend/app/api/user_content.py`, `backend/app/repository/user_content.py` — existing Note + custom node/relationship CRUD and the `origin: canonical | candidate | user` distinction this phase's ChangeSet mutation rules must preserve exactly.

### Revision model (existing, Phase 4 — extend, don't reinvent)
- `backend/app/domain/revision.py`, `backend/app/api/revisions.py`, `backend/app/revisions/__init__.py` — existing append-only Revision model/API (`04-01-PLAN.md`..`04-05-PLAN.md`, `04-SUMMARY.md` for design rationale) that ChangeSet-apply must record into, per PRD §12.

### Direct-Cypher call sites (researcher must produce the exhaustive list; this is the partial signal from a `session.run|tx.run|execute_query` grep)
- `backend/app/graph/database.py` (driver/session management), `backend/app/repository/{session,user,user_content}.py`, `backend/app/graph/{seed,candidates}.py`, `backend/app/api/{candidates,revisions}.py`, `backend/app/services/{graph,series}.py`.

### Frontend conventions to extend (existing detail panel / graph canvas — chat integrates alongside, does not replace)
- `frontend/src/components/detail/DetailPanel.tsx` — existing right-workspace Overview/Claims/Evidence/History tabbed panel; PRD §13 wants Chat integrated as an Inspector/Chat mode or resizable split here, not a full-screen replacement.
- `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/graphElements.ts` — existing Cytoscape selection/highlight mechanism the new `graph_focus` sync (PRD §14) must reuse.
- `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/components/episode/ConfirmAdvanceModal.tsx` — existing sessionStorage-backed watch-progress hook + confirmation-modal UX that PRD §1 requires preserving while moving authority server-side.
- `frontend/src/api/*.ts` — existing typed API client conventions new chat/ChangeSet client calls must match.

### No existing LLM/provider code
- Grep across `backend/` for `openai|anthropic|llm|langchain` found no real provider integration — the LLM provider abstraction (PRD §4) is wholly new; nothing to migrate or reconcile.

</canonical_refs>

<specifics>
## Specific Ideas

- Worked example conversations (Turkish) from PRD §15 are acceptance-relevant, not decorative — they should map onto integration tests / manual acceptance items: "Dexter'ın şu ana kadar kimlerle çalıştığını göster" (relationship query, cited, highlighted), "Dexter ve Doakes arasındaki ilişki neden gergin?" (multi-hop claims/events, evidence vs. inference), "Bu grafikte Rita'nın evini ekle" (create_node ChangeSet preview→confirm), "Dexter ile Batista arasına arkadaş ilişkisi ekle" (reject unapproved `FRIEND_OF` predicate, offer valid alternatives), "Dexter node'unu sil" (refuse canonical deletion, offer note/override instead).
- The 22-section PRD's own "Final Report" checklist (§22) and "Manual Acceptance Matrix" (§18) are strong candidates for the phase's UAT/verification checklist content almost verbatim — the planner should lift them rather than re-derive equivalents.
- PRD explicitly names "Testing" (§17) as an exhaustive checklist across auth/ownership, progress, retrieval, leakage, GraphRAG, prompt injection, chat persistence, ChangeSets, and regression — this is dense enough that it likely belongs split across multiple plans' `<acceptance_criteria>` rather than one test-writing task.

</specifics>

<deferred>
## Deferred Ideas

Explicitly out of scope per PRD §20 — do not implement in this phase:
Memgraph/FalkorDB/Apache AGE backends; unrestricted text-to-Cypher; autonomous unconfirmed writes; autonomous canonical-data deletion; admin/moderator roles; payments/token billing; multi-model routing marketplace; internet search/web scraping; automatic subtitle/screenplay ingestion; automatic ontology expansion; voice chat; native mobile app; real-time collaborative editing; production Kubernetes deployment; further unrelated graph-visual redesign beyond the completed 03.1 overhaul.

Also deferred (roadmap-level, not PRD-level): Phase 5 / 05.1's candidate-extraction-review pipeline is a sibling initiative, not a prerequisite — this phase does not touch `origin:candidate` ingestion mechanics beyond respecting the existing origin invariant.

</deferred>

---

*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Context gathered: 2026-07-30 via PRD Express Path*
