# Phase 10-02 — Visualization DTO / Projection / Boundary (shipped 2026-08-13)

Commits: `ba46ec2` (Task 1: DTO + projection), `c0af899` (Task 2: resolver),
`58c781d` (docs metadata). Plan verify: `test_visualization_projection.py` = 31 passed;
`test_spoiler_policy.py` + `test_visualization_projection.py` = 83 passed (always
`unset PYTHONPATH` first on this host).

## Windows + gsd-tools pitfalls (verified this session)

- gsd-tools.cjs lives at `C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs`
  (NO repo-local gsd-core). Invoke node with the NATIVE Windows path. Passing
  `$HOME/...` from git-bash (`/c/Users/...`) makes node resolve
  `C:\c\Users\...` → `MODULE_NOT_FOUND`. Use
  `GSD_TOOLS="C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"`
  (forward slashes are fine for node).
- `state.add-decision --summary "..."` WITHOUT `--phase` writes the decision label as
  `- [Phase ?]: ...`. Pass `--phase "10"` (workflow also prefers `--summary-file` for
  shell-safe text). Already-written bad labels: sed-fix with
  `sed -i 's/- \[Phase ?\]:/- [10-02]:/' .planning/STATE.md`.
- Shared-ID gate (#2388) check: `gsd_run query requirements.ready-ids "<plan>.md" ID1 ID2 --raw`
  returns `0/2 requirement(s) ready` when ALL declared IDs are also declared by sibling
  plans without SUMMARYs → do NOT mark them complete in REQUIREMENTS.md, even though the
  SUMMARY frontmatter `requirements-completed` copies the plan's IDs verbatim. See shared
  IDs up front via `grep -H "^requirements:" .planning/phases/*/*-PLAN.md`.
- `gsd_run query commit "msg" --files ...` (+ `--amend`) returns `{committed, hash}`.
  Verify the commit contains only intended files — pre-existing dirty files
  (`.planning/config.json`, `docs-work-manifest.json`) must not be staged.

## New backend surface (10-02) — the phase-10 visualization contract

- `spoilerless/app/domain/visualization.py`: `PROJECTION_VERSION = "1.0.0"` (MUST match
  fixture `fixture_metadata.projection_version`), `EPISODE_OVERVIEW_MAX_NODES = 40`,
  `EPISODE_OVERVIEW_MAX_EDGES = 60` (D-09). DTO = `VisualizationMetadata` +
  `nodes` / `edges` / `groups` / `timeline` / `focus` with a reference-closure
  `model_validator` (dangling edges, group members outside the node set, focus id
  outside the node set → ValueError; T10-FOCUS-02). `SafeEventContext`: tier is
  `Literal["major","supporting","micro"]`; `visible_from_order=None` means HIDDEN —
  the projection refuses it (fail closed, never defaulted visible).
- `spoilerless/app/services/visualization.py`:
  `VisualizationProjectionService.project_episode_overview(graph: GraphResponse, events: list[SafeEventContext] | None)`
  — Variant A (Series/Episode/Character + major Events; Locations/Objects/Organizations
  omitted). `OMITTED_EDGE_TYPES` = PARTICIPATED_IN/OCCURRED_IN/LOCATED_IN + participation
  family (WITNESSED/CAUSED/AFFECTED/TARGETED/MENTIONED). `HUMAN_EDGE_CLASSES`:
  PART_OF→part_of, PRECEDES→precedes, KNOWS→knows, FAMILY_OF→family, WORKS_WITH→work,
  TRUSTS→trusts, DISTRUSTS→distrusts, HELPS→helps, OPPOSES→opposes, THREATENS→threatens,
  ATTACKS→attacks, KILLS→kills; ANY unmapped type raises ValueError (D-14 fail closed).
  Edges with a non-kept endpoint are dropped (S01E02 `edge_12` WORKS_WITH→loc_miami_metro).
  Hidden rows (`visible_from_order > effective`) raise InvalidVisibilityOrder BEFORE
  projection (T10-LEAK-02). D-09 hard caps raise. Inputs are never mutated.
- `spoilerless/app/spoiler/policy.py::resolve_effective_boundary(requested_view_order, watched_through_order, view_as_of_order=None)`
  — the ONE D-05 resolver for graph/projection/expansion/path/search/focus/restoration
  inputs: `watched is None` → 1 (anonymous/no-progress, PROB-04/#12); `requested is None`
  → persisted view (PROB-09/#59); else `min(min(requested, view), watched)`; invalid
  orders → sanitized `InvalidVisibilityOrder`. Service exposes `resolve_boundary()`
  delegating to it (resolver-before-projection).

## Test conventions (test_visualization_projection.py)

- Fixture loader: JSON → `GraphResponse.model_validate(fixture["graph"])` +
  `[SafeEventContext.model_validate(e) for e in fixture["events"]]`; fixtures at
  `spoilerless/tests/fixtures/visualization/s01e01_safe.json` (9 nodes/4 edges DTO),
  `s01e02_cumulative_safe.json` (13 nodes/7 edges DTO).
- Hidden-data non-influence ("poisoned events"): append a hidden participant AND a
  hidden location ONLY where no valid one exists
  (`location_id=event.location_id or "loc_future_warehouse"`). Replacing a VALID
  location with a hidden one changes the DTO and breaks the poisoned==clean equality —
  hidden refs must be additive, then assert identical `model_dump(mode="json")`.
- Timeline sort key is `(visible_from_order, id)`: same-reveal-order events sort by id
  (`event_micro` before `event_supporting`).
- Raw relation names must not appear ANYWHERE in serialized DTO JSON
  (`json.dumps(dto.model_dump(mode="json"))` grepped against the raw-name tuple).
- 0/1/many payload tests: empty GraphResponse (all lists []) → valid empty DTO; one
  Character node → single-node DTO; fixture payloads → bounded DTO.

## Status notes

- VIZ-01/VIZ-02 NOT marked Complete in REQUIREMENTS.md (shared with 10-03 → #2388
  gate); 10-03 must re-run `requirements.ready-ids` after its SUMMARY lands.
- `display_tier` currently derives from safe editorial event tier (major=1 core,
  supporting=2, micro=3; characters=1 core; containers=2 supporting) — the 10-03/10-08
  audit of the real display_tier source is still pending (see 10-01 decision log).
- 10-03 must rewire `api/graph.py::_resolve_effective_boundary` to the shared resolver
  (deliberately out of 10-02's file scope); existing routes still compute the same min rule.
