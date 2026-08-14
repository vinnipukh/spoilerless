# Feature Ideas — Brainstorm, Not Commitments

> This is a research/brainstorm list, distinct from [ROADMAP.md](../ROADMAP.md) (authoritative status/backlog) and [PROBLEMS.md](../PROBLEMS.md) (known bugs/security gaps). Unshipped ideas here are not scoped, approved, or scheduled; entries marked **Already shipped** are retained as ideation history and possible extension points, not backlog. Any idea that touches spoiler visibility, ontology, or GraphRAG retrieval must still satisfy the invariants in [PROJECT-SPEC.md §3](../architecture/project-spec.md#3-non-negotiable-architecture-invariants) and [§7](../architecture/project-spec.md#7-graphrag-constraints) before it becomes a real task. [FEATURE-RESEARCH.md](feature-research.md) is the dated companion research, but some paths, dependencies, and proposed change sites there predate the `spoilerless/` rebrand and later deliveries; verify them against the live tree before implementation.

## 1. Graph exploration UX

- **Already shipped — Direct "find path" UI action.** The allowlisted executor is implemented in `spoilerless/app/retrieval/tools.py` and registered for chat in `spoilerless/app/retrieval/pipeline.py`. A direct bounded path flow also exists: `POST /api/series/{series_id}/graph/path`, `frontend/src/api/graph.ts`, `PathFinder.tsx`, and the **Show path** action in `GraphControls.tsx`. Future ideation here should extend that flow rather than add a second entry point.
- **Saved views / bookmarks.** Let a user pin a node + zoom/pan state per series so returning to the app resumes where they left off, instead of re-searching every session.
- **Already shipped — Node/edge type filter panel.** `GraphCanvas.tsx` renders `GraphFilterPanel` and applies client-side node-type and edge-family filters over the already-fetched, boundary-filtered response. Possible follow-up work could add saved filter presets.
- **Already shipped — Search-as-you-type over visible nodes.** `NodeSearch` and `CommandPalette` search the current graph payload (plus the user's notes) through the zero-dependency substring index in `frontend/src/lib/searchIndex.ts`; there is no search endpoint or added spoiler surface. Fuzzy ranking remains a possible enhancement, not the baseline feature.
- **Relationship strength as edge weight.** Map `relationship_effect`/confidence onto edge thickness or opacity so "strong ally" reads differently from "weak acquaintance" at a glance.
- **Export current view as image/PDF.** Useful for the demo and for users building a personal reference; strictly a client-side render of already-visible data.
- **Color-blind-safe palette toggle.** The spec already asks for a distinguishable visual language per node type (PROJECT-SPEC §6) — a second palette option makes that requirement accessible.

## 2. Spoiler-safe progress and timeline

- **Already shipped — "What's new" highlight on advance.** On a forward advance, `App.tsx` diffs the pre/post graph element IDs and passes `newlyRevealedIds` to `GraphCanvas`, which highlights newly visible elements for four seconds. A richer recap list or persistent history would be separate future work.
- **Per-episode progress history.** Show which episodes a user has confirmed as a timeline strip. This is **not** derivable from current persistence: `ProgressRepository` upserts one `UserSeriesProgress` row per user and series, so true confirmation history needs a new history/event model. The existing `TimelineView` is a story-event timeline, not watch-progress history.
- **Already shipped — Explicit "this episode not yet watched" empty state.** When the visible graph has no nodes, `App.tsx` renders `GraphEmptyState` with “Nothing revealed yet” and guidance to advance watch progress instead of showing a bare canvas. Future work could tailor this state per series or episode.

## 3. Chat / GraphRAG

- **Already shipped — Clickable citations.** `CitationChip.tsx` supports detail navigation and **Show in graph**; `App.tsx` wires those actions to detail/focus state, and `GraphCanvas` focuses the resulting graph elements. A future extension could add multi-citation tours or breadcrumbs.
- **Suggested follow-up questions.** After a `done` event, surface 2–3 template follow-ups derived from the answer's `graph_focus` (e.g. "Who else is connected to X?") — still routed through the same allowlisted tools, no free-text-to-Cypher.
- **"Ask about this" from the detail panel.** A button on a selected node/claim that pre-fills the chat input with a scoped question about that entity.
- **Session search.** Full-text search over a user's own persisted chat sessions/messages (already stored server-side), useful once a user has more than a couple of sessions.
- **Per-provider status indicator.** Now that BYOK supports `gemini`/`openai_compatible` (and scaffolded `vllm`/`ollama`), show which provider/model is active in the chat header so the user isn't guessing which key is live.
- **Rename a conversation.** `SessionPicker.tsx` supports select/create/delete but no rename — sessions carry a `title` field already, so this is a small edit-in-place addition to an existing model, not a new one.
- **Surface `get_character_context` as a dedicated "character read" view.** The backend already has a tool description built for "future-looking, opinion, motivation, or 'what do you think' questions" (`pipeline.py` `get_character_context`) — today a user only reaches it indirectly by phrasing a chat question the right way. A direct "Character insight" panel/button would call it explicitly.

## 4. Provenance and trust

- **Navigable source links.** Already tracked as a known gap (ROADMAP §8 item 3) — worth restating as a feature: turn plain-text locators into real links wherever the source is a rights-safe URL, without ever republishing copyrighted script/subtitle text.
- **Claim confidence legend.** A small always-visible key explaining `low/medium/high/verified` and `candidate/corroborated/canonical/disputed/rejected` so the distinction in PROJECT-SPEC §4 is legible to a first-time user, not just implied by color.
- **"Why do you believe this?" evidence drill-down.** One click from a claim to its full evidence chain (source → fragment → claim), collapsing what today requires reading several detail-panel sections separately.

## 4a. Revisions and ChangeSets

- **Real before/after values, not "Before: Not shown."** `ChangeSetCard.tsx`'s `changedFieldsFor()` documents, in a code comment, that the backend `ChangeSetOperation` payload never carries a prior-value snapshot — so today every proposed update honestly renders "Before: Not shown." Since `Revision` records already store `before`/`after` state (PROJECT-SPEC §3.5), the backend could resolve the operation's target resource at propose-time and attach the current value, turning every update proposal into a real diff instead of a one-sided preview.
- **Edit a proposed ChangeSet before confirming.** Today the only actions on an awaiting-confirmation ChangeSet are Confirm or Reject (`ChangeSetCard.tsx`) — there's no "tweak this field, then confirm" path. Even a narrow version (edit a single free-text field like a note's content or a claim's description before applying) would save a full reject-and-reask round trip through chat.
- **Already shipped — Before/after values in revision history.** `RevisionHistoryPanel.tsx`'s `diffFields()` returns each changed snapshot key with its `before` and `after` values, and `RevisionItem` renders “Before: … → After: …”. Possible follow-up work includes collapsible formatting for large or structured values.
- **Cross-resource activity feed.** Revision history today is always scoped to one selected node/claim (`RevisionHistoryPanel` takes a single `resourceId`). A separate "recent activity" view aggregating a user's own recent revisions across the whole series — reusing the existing `GET` revisions endpoint without the resource filter — would answer "what have I changed recently" without clicking through nodes one at a time.

## 5. Personal content and collaboration

- **Note tagging.** Let users tag their own notes and filter/search by tag — pure user-content metadata, with the same inherited visibility as the anchor node. Free-text note search has already shipped through `NodeSearch`/`searchIndex.ts`; tags and tag-aware filtering have not.
- **Already shipped — Shareable read-only progress snapshot.** `ShareDialog.tsx` creates, lists, copies, and revokes snapshot links; `ShareView` renders them, and the backend share API uses a token-gated graph read path at the captured boundary. Future work should harden or extend the existing share lifecycle rather than introduce a parallel boundary mechanism.
- **Per-user theory/speculation notes, visually distinct from canonical claims.** Already partially covered by `origin: user`, but a dedicated "theory" note subtype (never conflated with `canonical`/`candidate`) would let users track guesses ("I think X is the killer") without ever being mistaken for confirmed graph fact.

## 6. Candidate review workflow

- **Reviewer queue with source/candidate diff view.** Side-by-side rendering of the source fragment and the proposed claim, replacing the current API-only review workflow (ROADMAP Milestone 8) — UI only, no change to the underlying candidate/evidence model.
- **Bulk approve/reject for low-risk batches.** Once a reviewer trusts an extraction batch, approving many low-ambiguity candidates one at a time doesn't scale; batch actions over the existing approve/reject endpoints would help without any new backend semantics.

## 7. Multi-series and account features

- **Second demo series.** The architecture is series-scoped already (`series_id` throughout); adding one more small, rights-manageable series would validate the "one series" assumption doesn't hide accidental Dexter-only coupling.
- **Theme (light/dark) toggle.** A concrete, bounded accessibility/personalization idea; PROJECT-SPEC §13 does not currently classify theme switching as out of scope.
- **Mobile-responsive layout.** Mobile is listed as future breadth in PROJECT-SPEC §13; a responsive web pass would need explicit scope and should remain distinct from building a mobile app.
- **Turkish UI strings.** The chat system prompt already supports an `english`/`turkish` language setting for LLM answers (`system_prompt_language`); the surrounding UI chrome is still English-only — localizing it would make the two consistent.

## 8. Operational / provider features

- **Model/latency/cost hint in Settings.** Once a provider + model is chosen (see BYOK work in `frontend/src/components/settings/SettingsPage.tsx`), show a short static hint (e.g. approximate context window, whether it supports tool calling) to help users pick a workable model instead of discovering incompatibility mid-chat.
- **Local-model privacy messaging.** When dedicated `vllm`/`ollama` support lands (both currently route through `OpenAICompatibleProvider` in `spoilerless/app/services/chat.py`), surface an indicator only when configuration proves requests stay on the user's machine. Do not infer local-only privacy merely from the provider label or the current passthrough.

## Explicitly not features to add casually

Per PROJECT-SPEC §13 and ROADMAP §9, do not treat any of the following as a small feature: automated subtitle/script ingestion, vector/hybrid retrieval, actor/character appearance counts (leaks future participation), general multi-user production authorization, or Kubernetes/deployment complexity. Each needs explicit scoping against the invariants first.
