# DetailPanel (left inspector) + shadcn component pitfalls (08-06+)

The node-info inspector (`frontend/src/components/detail/DetailPanel.tsx`) is a
left-side shadcn Sheet with 6 tabs (Overview/Backlinks/Notes/History/Claims/
Evidence). Two shadcn base-class traps cost real debugging time; both are
VERIFIED against the live app.

## PITFALL: shadcn TabsList `w-fit` clips the rightmost tab with NO scrollbar
Base `TabsList` is `inline-flex w-fit` — it grows to content width. With 6
tabs in a narrow sheet the list outgrows its parent and the PARENT clips the
right side (Evidence tab cut off, no scrollbar because the list itself never
overflows — it's the parent that clips). `overflow-x-auto` on the list alone
does nothing while `w-fit` keeps it unconstrained.

Fix (in DetailPanel.tsx):
- TabsList: add `w-fit max-w-[calc(100%-2rem)] overflow-x-auto flex-nowrap`
  (the calc accounts for the existing `mx-4` margins — `w-full` + `mx-4`
  would overflow by the margin width). When content fits → no scrollbar;
  when it doesn't → the list scrolls instead of the parent clipping.
- Each TabsTrigger: add `shrink-0` (base has `flex-1` which would squeeze
  the triggers instead of letting them overflow into the scroll).

## PITFALL: shadcn Sheet width pinned by a DATA-ATTRIBUTE variant
Base SheetContent for side=left includes `data-[side=left]:sm:max-w-sm`
(384px). The attribute selector gives it HIGHER specificity than a plain
`lg:max-w-xl` — so DetailPanel's `lg:max-w-xl` override NEVER applied and the
panel was stuck at 384px at every viewport ≥640px (measured: computed
max-width 384px at innerWidth 1256). Fix: override at the SAME specificity —
`data-[side=left]:sm:max-w-md data-[side=left]:lg:max-w-xl` (448px sm+,
576px lg+). Diagnose via `getComputedStyle(sheet).maxWidth` — don't trust the
class list; the class is present but losing the cascade.

## Evidence tab: claims-style cards (08-06+, product rule)
The Evidence tab previously rendered cards with `max-h-32 overflow-y-auto`
(inner scrollbar per card — with 26 long evidence entries on Dexter's node
the panel became scrollbars-in-scrollbars) and a non-bold title. Claims cards
render clean: `rounded-md border border-border p-2` + `borderLeft: 4px solid
<accent>` + bold title (`font-medium break-words overflow-wrap-anywhere`) +
muted metadata line (`text-muted-foreground`). Evidence now mirrors that
structure exactly: bold `Source: {sourceLabel} - {evidence.locator}` title +
muted `{evidence.origin}` line, NO inner scroll (panel scrolls as a whole).
Keep `EVIDENCE_ACCENT_COLOR` ('#FB923C') for the left bar so evidence stays
visually distinct from claims (CLAIM_ACCENT_COLOR '#D946EF'). Note: claims
title is SpoilerGuard-wrapped; evidence title is not (source labels are
visible at the boundary) — don't "fix" that asymmetry blindly.

## Live verification techniques (browser automation, verified)
- **Canvas node selection**: cytoscape draws to `<canvas>` — nodes are NOT in
  the a11y tree, and synthetic `cy.$('#id').trigger('tap')` does NOT reach
  React's onSelect (nor do dispatched MouseEvents at `renderedPosition()` —
  the coords can also land below the canvas when the graph bbox exceeds the
  viewport). RELIABLE path: open the command palette (Ctrl+K / "Open command
  palette" button), type the node label, click the result — palette selection
  drives onSelect and opens the DetailPanel.
- **Tabs that won't activate via click**: synthetic `el.click()` AND
  browser_click on a Radix tab both failed to switch tabs (no console errors)
  — but keyboard activation worked: focus the tablist, focus the target tab,
  press Enter (Radix `activationMode` default = automatic). Fallback chain:
  clicks → keyboard.
- **Measure overflow, don't screenshot it**: for the tab bar,
  `list.scrollWidth > list.clientWidth` = scrollable; `lastTrigger.getBoundingClientRect().right <= listRect.right + 1` = all tabs visible.
  This is deterministic where vision models misread zoom/overflow.
