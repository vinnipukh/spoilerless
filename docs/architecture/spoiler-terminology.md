# Spoilerless — Spoiler Visibility Terminology (Locked Vocabulary)

**Status:** DOCS-01 deliverable (plan 07-01) · **Date:** 2026-08-03 · **Accuracy refresh:** 2026-08-10
(policy.py implemented; §3 split-progress model live; §6 contract updated to live signatures)
**Purpose:** Lock the visibility vocabulary so every later plan in phase 07 (07-02..07-08) and every
future contributor uses identical semantics. Later plans reference this document verbatim; do not
re-derive these rules. Source decisions: **D-02, D-03, D-05, D-09** in
`.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/07-CONTEXT.md`.

## 1. Canonical reveal-point property (D-02)

`visible_from_order` is the **single canonical reveal-point property** for story-sensitive graph
resources (nodes, relationships, Claims, Evidence, Sources, Notes, episode metadata gates, and —
once added — trivia entries).

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
  reveal point stays `visible_from_order` everywhere. **Current masking status (verified
  2026-08-10):** `SERIES_EPISODES_QUERY` selects these gate values, but the masking service does not
  apply them — `policy.mask_episode_metadata` keys title masking on `episode.visible_from_order` and
  `effective_view_order` and never reads `title_visible_from_order`, `synopsis_visible_from_order`,
  `image_visible_from_order`, or `title_is_spoiler`.
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
- The rule is implemented in `spoilerless/app/spoiler/policy.py` (see the "Central
  visibility-policy service contract" section), but fail-closed `IS NOT NULL` /
  `<= $visible_until_order` predicates remain duplicated throughout the Cypher in
  `spoilerless/app/spoiler/filter.py`, `spoilerless/app/retrieval/tools.py`, and the repositories —
  policy.py is not yet the single enforcement point for every read.
- Effective boundary: `effective_view_order` (see §3). When no boundary is available, fail closed
  (return nothing hidden-ineligible), never default to "visible".

## 3. Progress model (D-05)

Three fields describe a user's progress against one series. All are global publication orders
(§4), never episode-code strings.

| Field | Definition |
|---|---|
| `watched_through_order` | Highest contiguous order the user **confirmed watched**. Confirming Episode N sets `watched_through_order` to N; an omitted `view_as_of_order` also defaults to N, but the confirmation payload may carry an independent `view_as_of_order=M` (M must be a persisted episode order and M <= N — `assert_visibility_invariants` rejects M > N). Selecting an earlier already-watched episode never lowers `watched_through_order`. |
| `view_as_of_order` | **Temporary spoiler boundary** the user currently wants to view. Selecting an earlier already-watched episode changes only this value (no unlock confirmation); it hides later graph content, chat messages/citations, and disables ChangeSets created above the selected view. |
| `effective_view_order` | The boundary graph/episode/progress/chat reads and ChangeSet checks resolve through: `effective_view_order = min(view_as_of_order, watched_through_order)`. Direct user-content and revision reads accept a bare `Boundary` query value (`gt=0` only, no persisted-progress resolution) and candidate reads accept `visible_until_order` after persisted-episode validation — those paths do not resolve persisted split progress. |

**Invariant:** `1 <= view_as_of_order <= watched_through_order`.

- The `min()` rule means the effective boundary can never exceed the *watched* boundary even if the
  user asks for a higher view, and never exceeds the *view* boundary even if the user has watched
  further. The frontend and the LLM can never override this rule (D-05/D-12).
- The D-05 split is implemented (07-02): `watched_through_order`, `view_as_of_order`, and the
  policy-computed `effective_view_order` are persisted on `UserSeriesProgress`
  (`domain/progress.py`, `repository/progress.py`, `graph/progress.py`, `services/progress.py`,
  `frontend/src/api/progress.ts`, plus tests), with `visible_until_order` kept as a
  backward-compatible legacy echo. The D-21 episode envelope
  (`{series_id, watched_through_order, view_as_of_order, effective_view_order, episodes:[...]}`) is
  **not** a live API shape: `GET /api/series/{series_id}/episodes` returns a bare
  `list[EpisodeResponse]`, and the progress response carries the split boundary fields without an
  `episodes` array.
- The three-way clamp `effective = min(requested, persisted_view_as_of_order,
  persisted_watched_through_order)` is applied on the graph and episode routes for authenticated
  users — the persisted view is always inside the min; a formula that omits the persisted view is
  **fail-open** and is rejected. It does **not** apply to user-content, revision, or candidate read
  routes, which accept a direct boundary query value and never resolve persisted split progress.

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
  **not** implemented this phase (see `docs/architecture/spoiler-deferred-design.md`).

## 5. Naming prohibitions (summary)

| Prohibition | Rule |
|---|---|
| No competing reveal-point property names | `safe_at_order`, `revealed_at_order`, `spoiler_up_to_order`, `last_contiguous_order` are never introduced (D-02). |
| No coalesce-default on story-sensitive reveal points | `coalesce(visible_from_order, 1)` is forbidden in visibility rules (D-03). |
| No string-based order comparison | Episode-code strings and season-number strings are never compared for visibility (D-09). |
| No `last_appearance_order`, no final status before reveal | Forbidden for characters (D-16); see deferred design. |

## 6. Central visibility-policy service contract (D-04)

Module: `spoilerless/app/spoiler/policy.py` — the **canonical home of `visible_from_order`
semantics** and of the D-05 effective-boundary formula. Implemented in 07-02; the signatures below
document the **live module** (verified 2026-08-10) — where live behavior differs from the original
07-01 contract, the live behavior is authoritative. Consolidation note: query-level `IS NOT NULL` /
`<= $visible_until_order` predicates remain duplicated in `spoiler/filter.py`, `retrieval/tools.py`,
and repository queries, and application references to `is_visible` /
`require_visible_resource` / `filter_public_metadata` are sparse — not every visibility decision
delegates to this module yet. Follows the existing package layout (`spoilerless/app/spoiler/`,
alongside `filter.py`) with **no new framework** (D-01). No competing reveal-point names are
introduced anywhere in `spoilerless/app` or `frontend/src` (D-02).

```python
# spoilerless/app/spoiler/policy.py — live module (implemented 07-02, verified 2026-08-10)

def validate_visibility_order(order: int) -> int:
    """Return `order` unchanged, or raise `InvalidVisibilityOrder` on `order < 1`
    (None is rejected too — never a bare TypeError). The non-persisted-order
    check (an order that is not a real episode's global publication order in
    this series) lives in the calling service (ProgressService), which has
    database access; this function owns the numeric invariant only."""

def is_visible(record, effective_view_order: int) -> bool:
    """D-03 rule: True iff record.visible_from_order IS NOT NULL
    AND record.visible_from_order <= effective_view_order.
    FAILS CLOSED: a record with null visible_from_order returns False."""

def effective_view_order(view_as_of_order: int, watched_through_order: int) -> int:
    """D-05: return min(view_as_of_order, watched_through_order). Both inputs
    must be >= 1 (raise InvalidVisibilityOrder otherwise). The min rule is
    fail-closed: the effective boundary can never exceed the watched boundary
    even if a caller passes a higher view. The cross-field invariant
    view <= watched is NOT enforced here (effective_view_order(6, 5) == 5);
    it is enforced by assert_visibility_invariants on writes."""

def require_visible_resource(record, effective_view_order: int) -> Any:
    """Raise a resource-hidden error (ResourceHiddenError, mapped to the API
    layer's generic hidden/404 envelope per D-15) when is_visible(record,
    effective_view_order) is False; otherwise return the record unchanged
    (safe to project)."""

def filter_public_metadata(record, effective_view_order: int) -> dict:
    """Return the record's public projection, dropping spoiler-sensitive fields
    (title, synopsis, runtime, image_url, image_source_url, counts, locator)
    above the boundary. Missing guard = fail closed: never emit a field you
    could not prove safe."""

def mask_episode_metadata(episode, effective_view_order: int) -> dict:
    """Produce the D-21 display shape:
    {id, code, display_title, is_unlocked, is_current_view}
    - display_title: generic label ('S01E05 — Episode 5') when the real title is
      spoiler-sensitive above the boundary (D-08) or missing (fail closed);
      the real title otherwise.
    - is_unlocked: visible_from_order <= effective_view_order (the function
      receives only the episode record and the effective boundary — it never
      evaluates episode_order against watched_through_order, and it does not
      read title_visible_from_order / synopsis_visible_from_order /
      image_visible_from_order / title_is_spoiler).
    - is_current_view: episode_order == effective_view_order (view boundary)."""

def assert_visibility_invariants(record) -> None:
    """Validate a record's own invariants (visible_from_order is a positive int
    or None; watched/view fields satisfy D-05: 1 <= view_as_of_order <=
    watched_through_order) and raise on violation."""
```

Semantics notes (live behavior):

- **`effective_view_order`** owns the D-05 min rule. Callers pass `view_as_of_order` and
  `watched_through_order`; the function validates both are >= 1 and returns the min. The
  `view <= watched` invariant is enforced by `assert_visibility_invariants` on writes, not by this
  function. Boundary resolution at the graph/episode API layer is
  `min(requested, persisted_view_as_of_order, persisted_watched_through_order)` — the persisted
  view is always inside the min; omitting it is fail-open and rejected.
- **`is_visible`** fails closed: null `visible_from_order` → `False`. It never applies
  `coalesce(visible_from_order, 1)` (D-03).
- **`mask_episode_metadata`** returns a five-key episode projection
  (`{id, code, display_title, is_unlocked, is_current_view}`) and keeps masked episodes
  selectable for the unlock flow (D-22). The D-21 envelope
  (`{series_id, watched_through_order, view_as_of_order, effective_view_order, episodes:[...]}`)
  is not a live API shape: the episodes endpoint returns a bare `list[EpisodeResponse]`, and the
  progress response carries the split fields without an `episodes` array.
- `filter_public_metadata` drops spoiler-sensitive fields rather than returning them masked —
  hidden fields are absent from responses (D-16), not replaced with placeholders.
