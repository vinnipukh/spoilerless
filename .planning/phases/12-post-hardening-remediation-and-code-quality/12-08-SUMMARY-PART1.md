# Plan 12-08 Part 1 — Tasks 1–2 landed (orchestrator-inline after provider deaths)

## State for the Part-2 agent (Tasks 3–4)

### Committed
1. `refactor(12-08): extract shared ResizableRail primitive; ChatSheet consumes it (THERMO-P2-05)`
   - NEW `frontend/src/components/layout/ResizableRail.tsx` — pointer-capture drag rail, jsdom fallback, orientation prop, keyboard ±16px arrows, double-click reset hook.
   - `frontend/src/components/chat/ChatSheet.tsx` consumes it. Preserved: clamp 320..innerWidth-360, `localStorage['chatSheetWidth']`, double-click reset.
2. `refactor(12-08): extract AppIcons module from App.tsx (THERMO-P0-02)`
   - NEW `frontend/src/components/layout/AppIcons.tsx` (SettingsIcon, CalendarClockIcon, LayoutGridIcon). App.tsx imports them; ~70 lines removed.
3. `refactor(12-08): decompose DetailPanel into tab modules and dialogs; drop setTimeout resolve gate (THERMO-P0-04)`
   - NEW: `components/dialogs/CreateRelationshipDialog.tsx` (verbatim incl. numeric episode_order reduce), `detail/CharacterPortrait.tsx`, `detail/tabs/{OverviewTab,NotesTab,ClaimsTab,EvidenceTab}.tsx`.
   - CLAIM_ACCENT_COLOR / EVIDENCE_ACCENT_COLOR canonical homes are now tabs/ClaimsTab + tabs/EvidenceTab; **DetailPanel re-exports both** so CitationChip's `from '../detail/DetailPanel'` import still works — keep this contract.
   - DetailPanel.tsx is now a lean shell (**531 lines**, from 1074): selection/note handlers + Sheet chrome + Tabs wiring. The `setTimeout(()=>setResolved(true),0)` gate and its `resolved` state are DELETED — claims/evidence resolve synchronously; ClaimsTab/EvidenceTab receive `resolved={true}` prop (their Skeleton branch remains for future async use).
   - Test fix in DetailPanel.test.tsx: "shows canonical origin text" now asserts via the Origin `<dt>`'s nextElementSibling (the old `findByText('canonical')` became ambiguous once claim cards render synchronously).

### Verified at commit time
- `NODE_ENV=test CI=1 npx vitest run src/components/detail src/components/chat` → 89/89
- Full suite → **404/404** · `npm run build` → 0 TS errors
- History tab stays inline in DetailPanel (RevisionHistoryPanel wrapper); BacklinksTab untouched.

### Part 2 scope (NOT started)
Plan 12-08 Tasks 3–4:
- Task 3: GraphCanvas.tsx decomposition — extract CreateCustomNodeDialog to components/dialogs/, create graph/useCytoscapeBridge.ts (tap/hover/cxttap listeners + hover-card state) and graph/useCytoscapeLayout.ts (cose-bilkent/concentric/preset runs, position cache, localPlacementFor), instance-scope autoZoomHold, target <350 lines.
- Task 4: App.tsx decomposition — hooks/useWorkspaceScene.ts (view resolution, viz DTO load, expansion records with in-flight race guard THERMO-P2-07, mergedVisualization useMemo), hooks/useWorkspaceNavigation.ts (tabs/modes/command palette/hotkeys), hooks/useVisualization.ts; eliminate ALL render-phase setState (`if (graphData && activeGraph !== graphData)` pattern at former lines ~150/530/560); target <350 lines.
- Gates: full vitest suite green + `npm --prefix frontend run build` clean; then write 12-08-SUMMARY.md (final) covering all 4 tasks.

### Environment warnings
- Provider (Console Go upstream) unstable: 4 executor deaths today on 150s non-streaming timeouts. If you die: COMMIT EARLY per task, never leave uncommitted edits.
- Tests: `NODE_ENV=test CI=1 npm run test`; build compiles test files too (noUnusedLocals).
