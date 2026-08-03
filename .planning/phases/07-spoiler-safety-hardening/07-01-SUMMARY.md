---
phase: 07-spoiler-safety-hardening
plan: 1
subsystem: docs
tags: [spoiler-safety, threat-model, visibility, terminology, policy-service, regression-matrix]

# Dependency graph
requires:
  - phase: 06-spoiler-safety
    provides: spoiler-filtered graph APIs, progress persistence, chat/ChangeSet boundary plumbing
provides:
  - docs/SPOILER-THREAT-MODEL.md — D-19 leak-class inventory (6 direct + 22 indirect) with enforcement layer, backend query/service, frontend behavior, test coverage, fail-closed rule per class, plus 26-row regression matrix and D-25 completion gate
  - docs/SPOILER-TERMINOLOGY.md — locked vocabulary: visible_from_order canonical (D-02), fail-closed visibility rule + no-coalesce (D-03), watched/view/effective progress model (D-05), publication-order authority (D-09), and the D-04 central policy-service contract for backend/app/spoiler/policy.py
  - docs/SPOILER-DEFERRED-DESIGN.md — future invariants for Person/APPEARS_IN (episodes_seen_so_far), reviews, ratings, trivia, recommendations, awards, external wiki, movie-series (D-17/D-18)
  - .planning/phases/07-spoiler-safety-hardening/07-AUDIT.md — repository leak-channel audit with real symbols and gap ownership
affects: [07-02 progress-migration/policy-service, 07-03 episode-metadata, 07-04 relationship-hardening, 07-05 search/count-leak, 07-06 media-safety, 07-07 chat/citation/ChangeSet, 07-08 regression]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "single reveal-point property visible_from_order; fail-closed visibility rule; no coalesce-default on story-sensitive data"
    - "effective boundary = min(view_as_of_order, watched_through_order); persisted view always inside the min"
    - "central visibility-policy service (backend/app/spoiler/policy.py) owns visible_from_order semantics; no per-query reimplementation"
    - "every docs deliverable gates on git diff --check clean + acceptance grep commands"

key-files:
  created:
    - docs/SPOILER-THREAT-MODEL.md
    - docs/SPOILER-TERMINOLOGY.md
    - docs/SPOILER-DEFERRED-DESIGN.md
    - .planning/phases/07-spoiler-safety-hardening/07-AUDIT.md
  modified: []

key-decisions:
  - "visible_from_order is the single canonical reveal-point property; safe_at_order/revealed_at_order/spoiler_up_to_order/last_contiguous_order rejected (D-02)"
  - "visibility rule fails closed: visible iff visible_from_order IS NOT NULL AND <= effective_view_order; coalesce(visible_from_order,1) forbidden for story-sensitive data (D-03)"
  - "effective_view_order = min(view_as_of_order, watched_through_order) with invariant 1 <= view_as_of_order <= watched_through_order enforced inside the policy service (D-05)"
  - "D-04 policy-service contract specified (not implemented): validate_visibility_order, is_visible, effective_view_order, require_visible_resource, filter_public_metadata, mask_episode_metadata, assert_visibility_invariants — 07-02 implements"
  - "deferred features (Person model, reviews, ratings, trivia, recommendations, awards, external wiki, movie-series) documented with invariants only; no placeholder tables/UI (D-17/D-18)"

patterns-established:
  - "Leak-class docs: one row per class with enforcement layer / backend query-service / frontend behavior / test coverage / fail-closed rule, fed by a symbol-grounded repository audit"
  - "Regression matrix references real backend/tests files and the canonical pytest/vitest invocations"

requirements-completed: [DOCS-01, DOCS-02]

coverage:
  - id: D1
    description: "docs/SPOILER-THREAT-MODEL.md documents all D-19 direct and indirect leak classes with enforcement layer, backend query/service, frontend behavior, test coverage, fail-closed rule, and a regression matrix"
    requirement: DOCS-01
    verification:
      - kind: other
        ref: "grep -c \"regression matrix\" docs/SPOILER-THREAT-MODEL.md → 2 (>= 1)"
        status: pass
      - kind: other
        ref: "grep -c \"title\\|synopsis\\|autocomplete\\|degree\\|citation\" docs/SPOILER-THREAT-MODEL.md → 24 (representative indirect-class sample present)"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/SPOILER-TERMINOLOGY.md locks visible_from_order (D-02), the fail-closed rule and no-coalesce (D-03), watched_through_order/view_as_of_order/effective_view_order with min rule and invariant (D-05), and publication-order authority with never-compare-code-strings (D-09)"
    requirement: DOCS-01
    verification:
      - kind: other
        ref: "grep -c \"effective_view_order\" docs/SPOILER-TERMINOLOGY.md → 4; grep -c \"fails closed\" → 2 (>= 1); grep -c \"visible_from_order\" → 11 (>= 3)"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs/SPOILER-TERMINOLOGY.md section 6 specifies the D-04 central visibility-policy service contract (all seven function signatures for backend/app/spoiler/policy.py) for 07-02 to implement"
    requirement: DOCS-01
    verification:
      - kind: other
        ref: "grep -c \"def effective_view_order\" docs/SPOILER-TERMINOLOGY.md → 1; mask_episode_metadata → 2; validate_visibility_order → 1; is_visible → 4; require_visible_resource → 1; filter_public_metadata → 2; assert_visibility_invariants → 1"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/SPOILER-DEFERRED-DESIGN.md documents future invariants for Person/ACTED_AS/APPEARS_IN (episodes_seen_so_far, never last appearance), reviews, ratings, trivia, recommendations, awards, external wiki, and movie-series publication-order — no placeholder tables or UI"
    requirement: DOCS-02
    verification:
      - kind: other
        ref: "grep -c \"episodes_seen_so_far\" docs/SPOILER-DEFERRED-DESIGN.md → 2 (>= 1); grep -c \"last appearance\" → 1 (>= 1)"
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-08-03
status: complete
---

# Phase 7 Plan 1: Spoiler Leak Audit, Threat Model, Terminology Lock, and Policy-Service Contract Summary

**Repository leak-channel audit grounded in real symbols, a D-19-shaped spoiler threat model with a 26-row regression matrix, a locked visibility terminology (visible_from_order / fail-closed rule / watched-view-effective progress model), deferred-feature invariants, and the exact D-04 contract for the backend/app/spoiler/policy.py service that 07-02 implements.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-08-03T08:49:00Z (approx.)
- **Completed:** 2026-08-03T09:29:05Z
- **Tasks:** 3 (Task 1 completed by prior executor, commit `8e286ed`)
- **Files modified:** 4 (3 new docs + 07-AUDIT.md from Task 1)

## Accomplishments

- **Task 1 (prior executor, `8e286ed`):** `.planning/phases/07-spoiler-safety-hardening/07-AUDIT.md` — 172-line audit inventorying every direct (D1–D6) and indirect (I1–I22) leak channel with real routes, query constants (`SERIES_EPISODES_QUERY`, `NODES_QUERY`, `VISIBLE_CLAIMS_QUERY`, `EVIDENCE_QUERY`, `SOURCES_QUERY`, `SEARCH_ENTITIES_QUERY`, `GRAPH_SUMMARY_COUNTS_QUERY`, …), response fields, `visible_until_order` boundary-plumbing status per surface, the episodes-list route flagged as the boundary-unaware gap, and the D-01 keep/reject stack verdict with grep evidence.
- **Task 2 (this executor):** `docs/SPOILER-THREAT-MODEL.md` — every D-19 leak class (6 direct: future node, relationship, Claim, Evidence, Source text, chat message; 22 indirect: title, synopsis, runtime, image, cast ordering, appearance count, character status, first/last appearance, search suggestion, autocomplete, hidden result count, node degree, path existence, graph layout, citation title, external-link label, chat-session title, ChangeSet summary, error message, timing, cache) as a table row carrying enforcement layer, backend query/service, frontend behavior, test coverage, and fail-closed rule; D-25 completion gate; 26-row regression matrix mapping every leak class to a real `backend/tests/` file and the canonical `pytest`/`vitest` invocations.
- **Task 2 (this executor):** `docs/SPOILER-TERMINOLOGY.md` — locked vocabulary per D-02/D-03/D-05/D-09: single canonical reveal-point property with rejected names, fail-closed visibility rule with explicit `coalesce(visible_from_order, 1)` prohibition, `watched_through_order` / `view_as_of_order` / `effective_view_order = min(...)` with invariant `1 <= view_as_of_order <= watched_through_order`, publication-order authority (never compare episode-code/season strings).
- **Task 3 (this executor):** `docs/SPOILER-DEFERRED-DESIGN.md` — future invariants for Person/ACTED_AS/APPEARS_IN (`episodes_seen_so_far` counts visible episodes only, never total planned, never last appearance), reviews (`spoiler_up_to_order`), ratings (watched-only), trivia (`visible_from_order`), recommendations (no future-cast/plot/title/relationship leaks), awards, external wiki integration, movie-series publication-order note — no placeholder tables or UI.
- **Task 3 (this executor):** Terminology doc §6 "Central visibility-policy service contract" — exact D-04 signatures for `backend/app/spoiler/policy.py` (validate_visibility_order, is_visible, effective_view_order, require_visible_resource, filter_public_metadata, mask_episode_metadata, assert_visibility_invariants) with the D-05 min rule and fail-closed semantics specified inside the functions, the D-21 mask shape `{id, code, display_title, is_unlocked, is_current_view}`, and the no-competing-names / no-new-framework constraints.

## Verification

Plan-level gate (all passed, real output):

```text
$ ls docs/SPOILER-THREAT-MODEL.md docs/SPOILER-TERMINOLOGY.md docs/SPOILER-DEFERRED-DESIGN.md .planning/phases/07-spoiler-safety-hardening/07-AUDIT.md
.planning/phases/07-spoiler-safety-hardening/07-AUDIT.md
docs/SPOILER-DEFERRED-DESIGN.md
docs/SPOILER-TERMINOLOGY.md
docs/SPOILER-THREAT-MODEL.md

$ grep -c "regression matrix" docs/SPOILER-THREAT-MODEL.md
2
$ grep -c "Central visibility-policy service contract" docs/SPOILER-TERMINOLOGY.md
2
$ git diff --check
(clean — exit 0)
```

Task 2 acceptance greps:

```text
$ grep -c "regression matrix" docs/SPOILER-THREAT-MODEL.md        -> 2  (>= 1)
$ grep -c "effective_view_order" docs/SPOILER-TERMINOLOGY.md       -> 4
$ grep -c "fails closed" docs/SPOILER-TERMINOLOGY.md               -> 2  (>= 1)
$ grep -c "visible_from_order" docs/SPOILER-TERMINOLOGY.md         -> 11 (>= 3)
$ grep -c "title\|synopsis\|autocomplete\|degree\|citation" docs/SPOILER-THREAT-MODEL.md -> 24
$ git diff --check -- docs/                                         -> clean
```

Task 3 acceptance greps:

```text
$ grep -c "episodes_seen_so_far" docs/SPOILER-DEFERRED-DESIGN.md   -> 2  (>= 1)
$ grep -c "last appearance" docs/SPOILER-DEFERRED-DESIGN.md        -> 1  (>= 1)
$ grep -c "def effective_view_order" docs/SPOILER-TERMINOLOGY.md   -> 1  (>= 1)
$ grep -c "mask_episode_metadata" docs/SPOILER-TERMINOLOGY.md      -> 2
$ validate_visibility_order: 1 | is_visible: 4 | require_visible_resource: 1 |
  filter_public_metadata: 2 | assert_visibility_invariants: 1     (all >= 1)
$ git diff --check -- docs/                                         -> clean
```

No test suites were run this plan (docs-only per plan scope; the plan's automated verification is
grep + `git diff --check`, both green). Full-suite baseline 321/5/7 is untouched — no code changed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Repository leak-channel audit** - `8e286ed` (docs(07-01): audit spoiler leak channels across repo surfaces — 07-AUDIT.md) [prior executor]
2. **Task 2a: Threat-model document + regression matrix (DOCS-01, D-19)** - `c81f95b` (docs(07-01): add spoiler threat model with regression matrix)
3. **Task 2b: Terminology lock (D-02/D-03/D-05/D-09)** - `dc0aa00` (docs(07-01): lock spoiler visibility terminology and progress model)
4. **Task 3a: Deferred-feature invariants doc (DOCS-02, D-17/D-18)** - `8fc6a40` (docs(07-01): document deferred feature invariants)
5. **Task 3b: Central policy-service contract (D-04)** - `1bac593` (docs(07-01): specify central visibility-policy service contract for 07-02)

**Plan metadata:** this summary (docs(07-01): complete 07-01 plan summary)

## Files Created/Modified

- `docs/SPOILER-THREAT-MODEL.md` - D-19 threat model: 6 direct + 22 indirect leak classes with enforcement layer / backend query-service / frontend behavior / test coverage / fail-closed rule; D-25 completion gate; 26-row regression matrix
- `docs/SPOILER-TERMINOLOGY.md` - locked vocabulary (visible_from_order, fail-closed rule, watched/view/effective progress model, publication-order authority, naming prohibitions) + §6 D-04 policy-service contract
- `docs/SPOILER-DEFERRED-DESIGN.md` - future invariants for Person model, reviews, ratings, trivia, recommendations, awards, external wiki, movie-series
- `.planning/phases/07-spoiler-safety-hardening/07-AUDIT.md` - repository leak-channel audit (Task 1, prior executor)

## Decisions Made

- Locked `visible_from_order` as the single canonical reveal-point property; rejected `safe_at_order` / `revealed_at_order` / `spoiler_up_to_order` / `last_contiguous_order` (D-02).
- Locked the fail-closed rule (`visible_from_order IS NOT NULL AND <= effective_view_order`) and the `coalesce(visible_from_order, 1)` prohibition for story-sensitive data (D-03).
- Locked `effective_view_order = min(view_as_of_order, watched_through_order)` with `1 <= view_as_of_order <= watched_through_order`, enforced inside the policy service; boundary resolution must keep the persisted view inside the min (D-05).
- Specified (not implemented) the D-04 policy-service contract — seven exact signatures — as the single owner of visibility semantics for 07-02.
- Documented deferred features with invariants only, no placeholder tables/UI (D-17/D-18); movie-series publication-order note (D-09).

## Deviations from Plan

None - plan executed exactly as written. Task 1 was delivered by a prior executor (commit `8e286ed`); this executor continued with Tasks 2 and 3 without redoing Task 1.

## Issues Encountered

- `git diff --check` flagged one trailing blank line at EOF in `docs/SPOILER-TERMINOLOGY.md` after the contract-section patch; removed via a targeted patch (no functional impact). Re-check clean.
- Pre-existing working-tree modifications (`.planning/STATE.md`, `.planning/config.json`, deleted `ROADMAP.md` / `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md`, untracked `.hermes/`) were left untouched per task instructions; all commits staged explicit paths only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **07-02** can implement `backend/app/spoiler/policy.py` directly from `docs/SPOILER-TERMINOLOGY.md` §6 (exact signatures, D-05 min rule and fail-closed semantics specified inside `effective_view_order` / `is_visible`), plus the D-05 progress split (watched_through_order / view_as_of_order) and the D-21 API shape.
- **07-03..07-08** each have an owning-plan column in 07-AUDIT.md and regression-matrix rows in the threat model to execute against.
- The episodes-list route (`SERIES_EPISODES_QUERY`, `GET /api/series/{series_id}/episodes`) is documented as the boundary-unaware fail-open gap for 07-03.

---
*Phase: 07-spoiler-safety-hardening*
*Completed: 2026-08-03*
