---
phase: 09-feature-expansion-full-audit-remediation
plan: 10
type: execute
status: complete
executed_by: orchestrator inline (user directive — no subagents after repeated 429/budget deaths)
---

# Phase 09 — Plan 09-10 Summary: Timeline view + Series dashboard

## Objective

FEAT-02 (tabbed chronological timeline) + FEAT-04 (series dashboard dialog
augmenting the dropdown). Both payload-local (render only the already
boundary-filtered graph data — T-09-10-01), state-driven (no router —
T-09-10-03), and reusing existing selection/boundary flows
(T-09-10-02).

## Commits

| SHA | Message |
|-----|---------|
| `5edae60` | feat(09-10): timeline view tab (FEAT-02) + series dashboard dialog (FEAT-04) |

## What shipped

### Task 1 — Timeline view (FEAT-02)
- `frontend/src/components/timeline/TimelineEventRow.tsx` — button row
  (min-h-[44px]) per UI-SPEC §10.4: size-2.5 rounded-full bg-accent dot
  (filled + ring-accent when selected), font-medium label, rounded bg-muted
  episode badge, "N claims" count.
- `frontend/src/components/timeline/TimelineView.tsx` — full-canvas
  ScrollArea; events = `nodes` filtered to `type === 'Event'` from the
  already-filtered graph payload (never a new data call); sorted by
  `visible_from_order` then episode order (stable secondary: label);
  grouped under sticky episode headers (bg-background/90 backdrop-blur);
  vertical rail border-l-2 border-border pl-4 ml-3; empty state with the
  locked copy; ↑/↓/Enter keyboard navigation with scroll-into-view.
- App.tsx wiring: view union `'graph' | 'timeline' | 'settings'`;
  CalendarClockIcon inline SVG trigger in topBar; row click →
  `handleJumpToNode` (existing onSelect path) + switch to graph so the
  node is framed.

### Task 2 — Series dashboard (FEAT-04)
- `frontend/src/components/series/SeriesDashboard.tsx` — Dialog (max-w-lg),
  header "Series" font-heading text-xl; series cards bg-card ring-1
  ring-border rounded-lg p-4: title font-heading text-base, episode-count
  line text-xs text-muted-foreground, progress bar h-1.5 w-full bg-muted
  with bg-primary fill (watched/episodeCount %), "Open series" primary
  button (min-h-[44px]); currently-open series gets ring-accent; empty
  state locked copy; ↑/↓/Enter over cards.
- Episode counts are fetched lazily once per dialog open via the existing
  `getEpisodes` endpoint (counts only — titles stay server-side masked,
  D-08); no new backend endpoint.
- App.tsx wiring: LayoutGridIcon topBar trigger beside SeriesSelect (the
  dropdown is KEPT — augment, not replace); "Open series" →
  setSelectedSeriesId + close + switch to graph through the existing
  watchProgress flow.

## Verification (real runs)

- TimelineView.test.tsx: 4/4 (sort+grouping, row click select, keyboard
  nav, empty state)
- SeriesDashboard.test.tsx: 5/5 (cards+counts, ring-accent+progress, open
  callback, empty state, keyboard nav)
- Full frontend suite: **267/267** (35 files), `npm run build` green,
  `npm run lint` 0/0 (one react-hooks/set-state-in-effect warning fixed by
  removing the sync reset in the counts effect)

## Self-Check

✅ PASS — both views render only boundary-filtered payloads (no new data
calls); selection reuses handleJumpToNode; dashboard reuses the existing
progress flow; dropdown regression covered; no new dependencies
(T-09-10-SC); no .planning/config.json touched.

*Completed: 2026-08-05 (orchestrator inline)*
