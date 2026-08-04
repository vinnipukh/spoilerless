# HD Graf Cehennemi — Deferred Feature Design (Future Invariants)

**Status:** DOCS-02 deliverable (plan 07-01) · **Date:** 2026-08-03
**Purpose:** Document the *safe future design* of features that are deliberately **not built this
phase** (D-17, D-18, and the movie-series note in D-09). No placeholder tables, no placeholder UI,
no stubbed endpoints — only invariants that a future plan must honor. This document is the
decision record; it is not a work order.

## 1. Person / ACTED_AS / APPEARS_IN actor model (D-17)

**Not built this phase.** No actor pages, no cast metadata, no actor search, no
`Person`/`ACTED_AS`/`APPEARS_IN` nodes or relationships in the seed or the schema.

Future invariants (when cast support is actually required):

- An actor's appearance count is `episodes_seen_so_far`-style: it counts **only episodes visible
  at the viewer's effective boundary** — never the total planned episode count, never a projected
  total.
- **Never a "last appearance"** value. `last_appearance_order` is forbidden (D-16): a last
  appearance before its reveal point is a spoiler (it proves the character survives or departs).
- Cast ordering (billing order) must not be exposed before its reveal point; any ordering shown to
  a viewer is derived from resources visible at the effective boundary.
- The `episodes_seen_so_far` field must be computed by the central visibility policy
  (`spoilerless/app/spoiler/policy.py`, 07-02), not by ad-hoc queries, so the boundary rule is
  applied once.
- No actor data may be scraped or imported externally (D-01 rejects actor scraping).

## 2. Reviews (D-18)

**Not built this phase.** Future invariants:

- Every review carries `spoiler_up_to_order`: the publication order up to which the review's
  content is safe. (Note: this is a *review-content* gate, not a story-resource reveal point —
  story resources keep `visible_from_order` per D-02.)
- A review is hidden **above the reader's effective boundary**: a review whose
  `spoiler_up_to_order` is below the reader's `effective_view_order` is not returned.
- A reader viewing an earlier episode never sees reviews that reference content beyond that
  boundary — same rule as chat messages and ChangeSets (D-12/D-13).
- No review UI, no review endpoints, no review tables this phase.

## 3. Ratings (D-18)

**Not built this phase.** Future invariants:

- Ratings are **watched-only**: a user may rate only episodes at or below `watched_through_order`
  (contiguous confirmed watch, D-05).
- Aggregates (average, distribution) must never expose future quality signals — e.g. an average
  computed only from early episodes must not hint at later-episode quality or episode count.
- Any displayed count is labeled "seen so far" and reflects only ratings from visible/watched
  episodes (D-16).
- No rating UI, no rating endpoints this phase.

## 4. Trivia (D-18)

**Not built this phase.** Future invariants:

- Every trivia item carries a `visible_from_order` reveal point (the single canonical property,
  D-02) and is served only when `visible_from_order IS NOT NULL AND <= effective_view_order`
  (fail-closed, D-03).
- Trivia is story-sensitive by default: a missing `visible_from_order` fails closed (hidden),
  never coalesced to visible.
- No trivia ingestion pipeline (D-01 rejects external trivia ingestion), no trivia tables, no
  trivia UI this phase.

## 5. Recommendations (D-18)

**Not built this phase.** Future invariants:

- Recommendations must **not reveal future cast, plot, title, or relationship metadata** — no
  "because you watched Episode 1, you'll like this character who appears in Episode 6".
- Recommendation signals are computed only from resources visible at the user's effective
  boundary; hidden degree/future relationships never influence scores (D-16).
- No recommendation endpoint or UI this phase.

## 6. Awards and external wiki integration

**Not built this phase** (deferred in CONTEXT.md). Future invariants:

- Awards: any award referencing a future episode/character carries a `visible_from_order` reveal
  point and is hidden above the viewer's effective boundary; award counts are visible-only.
- External wiki integration (e.g. Wikipedia/TMDb/IMDb/OMDb): **rejected as imports this phase**
  (D-01). If ever revisited, external link labels must not contain visible future titles and
  external text must be treated as untrusted, spoiler-bearing content gated by the same boundary
  rules (D-11/D-14). External image selection is curated per boundary.

## 7. Movie-series product model (D-09 note)

**Not implemented this phase.** Future-compatible note only:

- Movie-series installments may later map to **publication order** (the same numeric
  `episode_order`-style global order used for episodes). When that happens, movie installments get
  a position in the series' one stable global order and are subject to the same
  `visible_from_order` / `effective_view_order` rules.
- No movie-series nodes, relationships, or UI this phase; do not design a second ordering axis now.
- Episode-code strings and season-number strings remain never-compared for visibility (D-09),
  including for any future movie installment codes.

## 8. Standing rules that apply to every deferred feature

1. No placeholder tables, no placeholder UI, no stubbed endpoints (D-18).
2. Every story-sensitive resource uses `visible_from_order` (D-02) and the fail-closed rule (D-03).
3. All boundary math goes through the central visibility policy service
   (`spoilerless/app/spoiler/policy.py`, specified in `docs/SPOILER-TERMINOLOGY.md`, implemented in
   07-02).
4. Any future implementation must be a new plan in the GSD flow; nothing in this document grants
   permission to build these features inline.
