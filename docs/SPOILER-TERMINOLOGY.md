# HD Graf Cehennemi — Spoiler Visibility Terminology (Locked Vocabulary)

**Status:** DOCS-01 deliverable (plan 07-01) · **Date:** 2026-08-03
**Purpose:** Lock the visibility vocabulary so every later plan in phase 07 (07-02..07-08) and every
future contributor uses identical semantics. Later plans reference this document verbatim; do not
re-derive these rules. Source decisions: **D-02, D-03, D-05, D-09** in
`.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/07-CONTEXT.md`.

## 1. Canonical reveal-point property (D-02)

`visible_from_order` is the **single canonical reveal-point property** for story-sensitive graph
resources (nodes, relationships, Claims, Evidence, Sources, Notes, and — once added — trivia entries
and episode metadata gates).

- The value is a positive integer: the global publication order (see §4) at which the resource
  becomes visible.
- **Rejected competing names** — never introduce any of these anywhere in `spoilerless/app` or
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
  (`int = Field(ge=1)`, as in `domain/graph.py:15` and `domain/series.py`) so a null value fails
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
  `spoilerless/app/spoiler/filter.py`, `spoilerless/app/retrieval/tools.py`,
  `spoilerless/app/repository/user_content.py`, etc.) and will be centralized in the
  `spoilerless/app/spoiler/policy.py` service (see the "Central visibility-policy service contract"
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

## 6. Central visibility-policy service contract (D-04)

Module: `spoilerless/app/spoiler/policy.py` — the **single owner of `visible_from_order` semantics**
and of the D-05 effective-boundary formula. Every repository, service, retrieval tool, and API
route that decides visibility delegates to this module; the rule is never reimplemented per query.
Follows the existing package layout (`spoilerless/app/spoiler/`, alongside `filter.py`) with **no new
framework** (D-01). Implemented in **07-02**; the signatures below are the contract the 07-02
executor implements without reinterpretation. No competing reveal-point names are introduced
anywhere in `spoilerless/app` or `frontend/src` (D-02).

```python
# spoilerless/app/spoiler/policy.py — contract (07-02 implements)

def validate_visibility_order(order: int) -> int:
    """Return `order` unchanged, or raise on `order < 1` or a non-persisted order
    (an order that is not a real episode's global publication order in this series)."""

def is_visible(record, effective_view_order: int) -> bool:
    """D-03 rule: True iff record.visible_from_order IS NOT NULL
    AND record.visible_from_order <= effective_view_order.
    FAILS CLOSED: a record with null visible_from_order returns False."""

def effective_view_order(view_as_of_order: int, watched_through_order: int) -> int:
    """D-05: enforce the invariant 1 <= view_as_of_order <= watched_through_order
    (raise ValueError on violation), then return min(view_as_of_order, watched_through_order).
    The min rule and the invariant are enforced HERE, inside this function."""

def require_visible_resource(record, effective_view_order: int) -> None:
    """Raise a resource-hidden error (mapped to the API layer's generic hidden/404
    envelope, per D-15) when is_visible(record, effective_view_order) is False."""

def filter_public_metadata(record, effective_view_order: int) -> dict:
    """Return the record's public projection, dropping spoiler-sensitive fields
    (title, synopsis, image, runtime, counts, locator, ...) above the boundary.
    Missing guard = fail closed: never emit a field you could not prove safe."""

def mask_episode_metadata(episode, effective_view_order: int) -> dict:
    """Produce the D-21 display shape:
    {id, code, display_title, is_unlocked, is_current_view}
    - display_title: generic label ('S01E05 — Episode 5') when the real title is
      spoiler-sensitive above the boundary (D-08); code/season numbers stay visible.
    - is_unlocked: episode_order <= watched_through_order.
    - is_current_view: episode_order == effective_view_order (view boundary)."""

def assert_visibility_invariants(record) -> None:
    """Validate a record's own invariants (visible_from_order is a positive int or
    None; watched/view fields satisfy D-05) and raise on violation."""
```

Semantics notes for the implementer:

- **`effective_view_order`** is the only place the D-05 min rule lives. Callers pass
  `view_as_of_order` and `watched_through_order` (persisted values); the function enforces
  `1 <= view_as_of_order <= watched_through_order` (raise) and returns the min. Boundary
  resolution at the API layer must be `min(requested, persisted_view_as_of_order,
  persisted_watched_through_order)` — the persisted view is always inside the min; omitting it is
  fail-open and rejected.
- **`is_visible`** fails closed: null `visible_from_order` → `False`. It never applies
  `coalesce(visible_from_order, 1)` (D-03).
- **`mask_episode_metadata`** output matches the D-21 API contract
  (`{series_id, watched_through_order, view_as_of_order, effective_view_order, episodes:[...]}`)
  and keeps masked episodes selectable for the unlock flow (D-22).
- `filter_public_metadata` drops spoiler-sensitive fields rather than returning them masked —
  hidden fields are absent from responses (D-16), not replaced with placeholders.