# Phase-10 visualization frontend wiring (260814-viz) — audit-gap closure

Class lesson: **backend + components + reducer + API clients built and unit-tested
≠ wired feature.** The v1.3 milestone audit (GAP-1, blocker-class) found
`fetchVisualization`/`fetchExpansion` had ZERO callers, the `visualization` prop was
test-only, tabs were navigation-only, and the expansion UI didn't exist — while every
unit suite was green and the operator UAT had APPROVED rows describing those features.
The UAT couldn't distinguish the DTO scene from the legacy one (both render safe graphs).

## Prevent: call-site audit before claiming end-to-end

```bash
grep -rn "fetchVisualization\|fetchExpansion" frontend/src --include="*.ts" --include="*.tsx" | grep -v "\.test\." | grep -v "export async"
# empty result = dead client code, no matter how green the suites are
```

## Scene-selection rule (the design that unblocked everything)

Projection DTOs never contain user content (custom nodes/edges/notes live only in the
legacy `GraphResponse`). Never replace the legacy scene wholesale:

- Story + Advanced → keep legacy scene (`visualization={undefined}`)
- Characters → `character_network`; Evidence → `investigation`; Answer Graph → `graphrag_focus` (focus ids from chat citation)

This preserved legacy user-content tests (user-created edge testids come from the
canvas, which renders legacy on Story) while exercising the real projection routes.

## GraphCanvas `visualization` prop semantics (extended 260814)

- `undefined` = explicit **leave-projection** — clears the DTO hold, legacy scene restored
- `null` = loading, **retain** last non-null DTO (D-44, no blank canvas)
- DTO = render `toCytoscapeElements(dto)`

Before this, `null`/`undefined` were conflated (`visualization ?? lastRef.current`),
so returning to Story kept the last DTO pinned forever.

## Expansion flow

Expand menu (7 allowlisted keys) → `fetchExpansion` → delta DTO → merge into base
(seen-sets dedup by id across nodes/edges/timeline) → pass merged DTO. Undo pops the
newest record, Collapse removes an anchor's records; App owns the records list AND
mirrors them into the scene reducer (ADD_EXPANSION/UNDO/COLLAPSE) for state coherence.
All spoiler filtering stays backend-side; the merge is mechanical.

## App.test.tsx patterns that bit (all fixed)

- fetchStub route order: `/graph/visualization` and `/graph/expand` branches MUST be
  checked BEFORE the generic `url.startsWith('/graph')` branch (their URLs also match it).
- `graphFetchCalls()` (legacy-route assertions) must exclude the projection routes:
  `includes('/graph') && !includes('/graph/visualization') && !includes('/graph/expand')`.
- Accessible-name collisions: canvas mock node/edge buttons vs search-dropdown rows
  ('Dexter Morgan' node, 'Family' edge vs the Expand menu's 'Family' key) — the
  canvas renders FIRST in DOM order, so pick `matches[matches.length - 1]` for the
  dropdown/menu control.
- View switches legitimately run one layout (DTO arrival): reset
  `graphStubHooks.layoutRuns = 0` after the switch settles before asserting
  selection/timeline never lays out.
- `useGraph(seriesId, order)` with `order ?? 1` fires a fetch pre-unlock; pass the
  raw `viewAsOfOrder` (null until confirmed) — the empty-state test asserts 0 graph
  calls while the unlock modal is open.

## sed bulk-replace hazard

A global `sed -i 's/watchProgress\.confirmedOrder)/confirmedOrder)/g'` silently
changed nullability semantics at an unrelated call site (`useGraph` gained `?? 1`).
After any bulk sed on call sites, grep the touched lines; prefer targeted `patch`
calls for semantics-sensitive edits.

## Closure evidence (commit b133ee7)

400 frontend tests + build clean + 130 backend offline tests; UAT rows 2/3/8/9
re-verified with wiring tests named per row; audit GAP-1 marked CLOSED.
