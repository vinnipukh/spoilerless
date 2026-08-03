# HD Graf Cehennemi — Spoiler Visibility Terminology (Locked Vocabulary)

**Status:** DOCS-01 deliverable (plan 07-01) · **Date:** 2026-08-03
**Purpose:** Lock the visibility vocabulary so every later plan in phase 07 (07-02..07-08) and every
future contributor uses identical semantics. Later plans reference this document verbatim; do not
re-derive these rules. Source decisions: **D-02, D-03, D-05, D-09** in
`.planning/phases/07-spoiler-safety-hardening/07-CONTEXT.md`.

## 1. Canonical reveal-point property (D-02)

`visible_from_order` is the **single canonical reveal-point property** for story-sensitive graph
resources (nodes, relationships, Claims, Evidence, Sources, Notes, and — once added — trivia entries
and episode metadata gates).

- The value is a positive integer: the global publication order (see §4) at which the resource
  becomes visible.
- **Rejected competing names** — never introduce any of these anywhere in `backend/app` or
  `frontend/src`:
  - `safe_at_order`
  - `revealed_at_order`
  - `spoiler_up_to_order`
  - `last_contiguous_order`
- Field-level **metadata** gates are companions, not renames: `title_visible_from_order`,
  `synopsis_visible_from_order`, `image_visible_from_order` (D-08) gate *display metadata* on an
  episode. They never replace `visible_from_order` on the story resource itself. The resource-level
  reveal point stays `visible_from_order` everywhere.
- Schema convention: `visible_from_order` is a **non-null** integer field
  (`int = Field(ge=1)`, as in `domain/graph.py:11` and `domain/series.py`) so a null value fails
  validation — the schema layer itself fails closed.

## 2. Visibility rule — fail closed (D-03)

A resource is **visible** iff:

```
visible_from_order IS NOT NULL AND visible_from_order <= effective_view_order
```

- **Missing visibility fails closed.** A resource with a NULL `visible_from_order`, or whose
  `visible_from_order` exceeds the effective boundary, is treated as hidden.
- **`coalesce(visible_from_order, 1)` is FORBIDDEN for story-sensitive data.** A coalesce-default
  would make a missing reveal point visible from order 1 — the opposite of fail-closed. It may
  appear only in queries over provably non-story data, and never in the visibility rule itself.
- The rule is enforced at the query level today (`<= $visible_until_order` in
  `backend/app/spoiler/filter.py`, `backend/app/retrieval/tools.py`,
  `backend/app/repository/user_content.py`, etc.) and will be centralized in the
  `backend/app/spoiler/policy.py` service (see the "Central visibility-policy service contract"
  section) in 07-02.
- Effective boundary: `effective_view_order` (see §3). When no boundary is available, fail closed
  (return nothing hidden-ineligible), never default to "visible".

## 3. Progress model (D-05)

Three fields describe a user's progress against one series. All are global publication orders
(§4), never episode-code strings.

| Field | Definition |
|---|---|
| `watched_through_order` | Highest contiguous order the user **confirmed watched**. Confirming Episode N marks Episodes 1..N watched; `watched_through_order` and `view_as_of_order` both become N. Selecting an earlier already-watched episode never lowers this value. |
| `view_as_of_order` | **Temporary spoiler boundary** the user currently wants to view. Selecting an earlier already-watched episode changes only this value (no unlock confirmation); it hides later graph content, chat messages/citations, and disables ChangeSets created above the selected view. |
| `effective_view_order` | The boundary every read, retrieval, chat, citation, and ChangeSet check must use: `effective_view_order = min(view_as_of_order, watched_through_order)`. |

**Invariant:** `1 <= view_as_of_order <= watched_through_order`.

- The `min()` rule means the effective boundary can never exceed the *watched* boundary even if the
  user asks for a higher view, and never exceeds the *view* boundary even if the user has watched
  further. The frontend and the LLM can never override this rule (D-05/D-12).
- The current codebase has a single-boundary model (`visible_until_order` persisted on
  `UserSeriesProgress`, one query param on graph/user-content routes, one server-resolved boundary
  for chat). The D-05 split and the D-21 API shape
  (`{watched_through_order, view_as_of_order, effective_view_order, episodes:[...]}`) land in 07-02;
  the terminology above is the target semantics for that work.
- Any boundary resolution must be `effective = min(requested, persisted_view_as_of_order,
  persisted_watched_through_order)` — the persisted view is always inside the min. A formula that
  omits the persisted view is **fail-open** and is rejected.

## 4. Publication-order authority (D-09)

Spoiler visibility follows **release/publication order**, never fictional chronology.

- Flashbacks/flash-forwards do not alter `episode_order`: an event shown in Episode 1 is visible
  from 1 even if it occurs later in fictional chronology; an event revealed in Episode 5 stays
  hidden until 5 even if it describes an earlier fictional event.
- One stable global episode order per series (`episode_order`, numeric, as ordered by
  `SERIES_EPISODES_QUERY` in `spoiler/filter.py`).
- **Never compare episode-code strings** (`"S01E09"` vs `"S01E10"`) and **never derive visibility
  from season-number string ordering** (`"2"` vs `"10"`). All reveal decisions use the numeric
  `episode_order` / global publication order.
- Required ordering regression tests: `S01E09` vs `S01E10` (same season), end-of-season vs
  next-season start, flashback revealed later, out-of-order fictional chronology.
- Movie-series installments may later map to publication order; a movie-series product model is
  **not** implemented this phase (see `docs/SPOILER-DEFERRED-DESIGN.md`).

## 5. Naming prohibitions (summary)

| Prohibition | Rule |
|---|---|
| No competing reveal-point property names | `safe_at_order`, `revealed_at_order`, `spoiler_up_to_order`, `last_contiguous_order` are never introduced (D-02). |
| No coalesce-default on story-sensitive reveal points | `coalesce(visible_from_order, 1)` is forbidden in visibility rules (D-03). |
| No string-based order comparison | Episode-code strings and season-number strings are never compared for visibility (D-09). |
| No `last_appearance_order`, no final status before reveal | Forbidden for characters (D-16); see deferred design. |
