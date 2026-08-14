---
phase: 10
slug: polish-finishing-touches
status: draft
shadcn_initialized: true
preset: radix-nova
created: 2026-08-13
---

# Phase 10 — UI Design Contract

> Visual and interaction contract for the spoiler-safe narrative visualization redesign and polish closeout. This contract preserves the existing dark Obsidian-style brand and treats the product as an interactive story map, not a graph-database dump.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | radix-nova (from `frontend/components.json`) |
| Component library | Radix/shadcn primitives; existing Tailwind v4 utility language |
| Icon library | Lucide |
| Font | Space Grotesk Variable for headings; Inter Variable for body/UI |
| Renderer | Cytoscape.js in one stable scene; React/CSS for timeline and panels |

Existing source of truth: `frontend/src/index.css`, `frontend/components.json`, `frontend/src/App.tsx`, and the graph/timeline/detail components named in `10-CONTEXT.md`. Do not add DaisyUI, replace Cytoscape, or introduce an unrelated visual identity.

## Six-Dimension Contract

## Copywriting Contract

### Information architecture

The product hierarchy is fixed and visible in the primary navigation:

| Top-level tab | Default content | Nested modes / responsibilities |
|---------------|-----------------|---------------------------------|
| Story | Episode Overview | Event Timeline; bidirectional graph/timeline selection |
| Characters | Character Network | Local Neighborhood for selected character |
| Evidence | Investigation / Evidence Chain | temporary GraphRAG Answer Graph; Claims, Evidence, Sources, Notes remain Inspector content |
| Advanced | Full Graph Explorer | debug/deep exploration only; raw relation names may appear only here |

Desktop uses top tabs. Mobile uses the same four tabs in a horizontally scrollable top tab strip; never move primary navigation to bottom navigation. View changes preserve Filters unless an incompatibility is explicitly surfaced. Views answer the task; Filters restrict entity types.

Use human labels in all non-debug views: “Family”, “Work”, “Conflict”, “Episode events”, “Clues”, “Locations”, and “Evidence”. Never expose `PARTICIPATED_IN`, `OCCURRED_IN`, or other raw Neo4j relation names in normal UI. Edge labels follow `never`, `on_hover`, `on_select`, `on_path`, `medium_zoom`, and `always` policies; Episode Overview has no persistent procedural labels.

Primary copy:

| Element | Copy |
|---------|------|
| Primary CTA | `Explore story` |
| Episode Overview heading | `Episode Overview` |
| Story timeline heading | `Event Timeline` |
| Expansion CTA | `Expand by {concept}` |
| Expansion recovery | `Undo expansion`, `Collapse`, `Reset view` |
| Focus recovery | `Clear focus` |
| Return recovery | `Back to Episode Overview` |
| Empty state heading | `Nothing to map yet` |
| Empty state body | `This episode has no spoiler-safe story elements at your current progress. Choose another episode or return to Episode Overview.` |
| Loading state | `Updating the story map…` with secondary `Your current scene stays visible while we prepare the next view.` |
| Error state | `We couldn’t update this view.` with action `Try again`; never show Neo4j, stack-trace, or internal error text |
| Partial state | `Some story details are still loading.` with action `Retry missing details` |
| No search results | `No visible matches` with `Try a different name or check your episode boundary.` |
| No evidence | `No evidence is attached yet` with `Select a claim or source to inspect its trail.` |
| Answer Graph notice | `Answer Graph` with `Temporary focus from this answer. Close to restore your scene.` |
| Inspector close | `Close Inspector` |

Destructive or state-resetting actions require confirmation only for `Reset view` when expansions, focus, or selection would be lost: `Reset this story view? Your episode, filters, and camera will stay; temporary expansions and focus will be cleared.` Collapse and Undo are reversible and do not require a modal. “Show in graph” is explicit before any Evidence/Source item changes the main graph.

## Visuals and Component Composition

Desktop composition is a full-height app shell: existing header/actions, a four-tab strip below it, then a task canvas. Story uses a two-region workspace: Cytoscape scene as the dominant region and a right-side timeline rail or coordinated timeline panel. Do not permanently stack graph, timeline, and Inspector into equal columns. Characters keeps the graph dominant and opens Local Neighborhood contextually. Evidence uses a readable layered Claim → Evidence → Source path; it is not placed on the default story graph. Advanced may expose the complete graph, diagnostic controls, and technical labels.

Episode Overview is a bounded narrative scene: target 12–28 nodes, hard maximum 40; preferred fewer than 35 edges, hard maximum 60. Prefer characters and major/supporting Events, using participant avatars/chips, Inspector, and timeline metadata instead of procedural participation edges. `LOCATED_IN` is usually Event metadata. Event cards show spoiler-safe participants and Location. Plot-thread groups are editorial story concepts and never reveal future member counts.

Node treatment is restrained and semantic: Characters use safe image/initial/silhouette fallback; Events use the existing event visual language; Locations, Objects, and Organizations use distinct non-color shape/icon cues. Canonical content is normal weight, candidate content has a small draft/warning marker, and user content has a small pencil badge or subtle dashed border. Do not create a provenance rainbow. Selection uses a clear ring/halo and dims unrelated content without changing layout. Newly revealed content may use a brief glow, then returns to normal.

The Inspector is a single coordinated surface with tabs `Overview`, `Claims`, `Evidence`, `Sources`, and `Notes` where permissions allow. Opening a citation prefers evidence detail. Inspector and timeline selection synchronize with graph selection; clearing selection closes or empties the Inspector without deleting scene state. On mobile the Inspector is a bottom sheet with a visible drag handle and two states: half-height for context-preserving preview and full-height for reading nested detail. It must not squeeze the graph and timeline simultaneously on narrow screens.

Graph controls are compact, discoverable, keyboard reachable, and grouped by task: search, zoom, fit, filters, focus/path, expansion, and recovery. Semantic zoom changes label/icon/secondary-text density only; zoom never fetches data or expands the graph. Keep existing graph backdrop, hover card, legend, filter panel, path finder, and focus indicator patterns where compatible.

## Color

Use the existing `frontend/src/index.css` tokens; no palette replacement.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0F172A` (`--background`) | App background, graph canvas, page gutters |
| Secondary (30%) | `#192134` (`--card`, `--sidebar`, `--popover`) | Cards, Inspector, timeline rail, tab/navigation surfaces |
| Accent (10%) | `#4338CA` (`--primary`), with `#6366F1` (`--secondary`) and `#7C3AED` (`--accent`) | Active top tab, primary CTA, selected/focused node ring, active timeline item, explicit “Show in graph”, Answer Graph boundary |
| Supporting semantic | `#F59E0B` (`--warning`) | Candidate/draft marker, partial/loading attention, newly revealed cue when paired with a non-color indicator |
| Destructive | `#DC2626` (`--destructive`) | Reset confirmation consequence, delete/reject actions, error icon/status only |

Accent is reserved for active navigation, primary actions, intentional selection/focus, explicit graph-opening actions, and temporary Answer Graph state. It is not applied to every link, border, node, or hover. All status distinctions also use text, icon, shape, border, or weight; color is never the only signal. Preserve the existing subtle border `rgba(255,255,255,0.08)` and elevated surface `#1E2740` for hover/raised states.

### Accent semantic roles

The existing accent-family tokens are distinct semantic roles, not interchangeable accents: `--primary` (`#4338CA`) is reserved for the active top tab and primary CTA; `--secondary` (`#6366F1`) is reserved for selected/focused node rings and active timeline items; `--accent` (`#7C3AED`) is reserved for the explicit “Show in graph” action and the temporary Answer Graph boundary. Do not introduce additional accent colors or apply these tokens to generic links, borders, nodes, or hover states.

## Typography

Declare only these four sizes and two weights:

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 regular | 1.5 |
| Label / metadata | 14px | 400 regular | 1.4 |
| Heading | 20px | 600 semibold | 1.2 |
| Display / page title | 28px | 600 semibold | 1.2 |

Use Inter for readable detail, evidence, timeline, and controls; use Space Grotesk for headings and tab labels. Node labels are human names, not IDs. At low zoom show icons/short labels only; at medium zoom show primary labels; on hover/select/path show the full human label and relationship explanation. Long titles wrap inside cards/Inspector and never force horizontal page overflow. Technical IDs, cache/version data, and raw edge types are Advanced/debug content only.

## Spacing Scale

Use the existing 4px-based scale:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon-to-label gap, status marker inset |
| sm | 8px | Compact control and chip spacing |
| md | 16px | Default control padding, card content gap |
| lg | 24px | Panel/card section padding |
| xl | 32px | Workspace and major region gaps |
| 2xl | 48px | Major page/section break |
| 3xl | 64px | Page-level breathing room where space permits |

Exceptions: interactive controls and icon buttons are at least 44×44px; mobile sheet drag handle is 44px wide and 4px high; tab strip can overflow horizontally but its hit areas remain at least 44px high. Desktop Inspector width is 320–384px; mobile half sheet is approximately 45–55vh and full sheet is approximately 90vh, with safe-area padding. Use responsive breakpoints already provided by Tailwind; at narrow widths collapse secondary graph controls behind a menu and show one primary content region at a time.

Responsive truths:

- Desktop: four visible top tabs; graph remains the primary visual anchor; timeline rail and right Inspector coexist only when width supports it.
- Tablet: same hierarchy; timeline can become a collapsible rail; Inspector remains a side panel when there is room.
- Mobile: horizontally scrollable top tabs; graph or timeline is the active primary region; Inspector is half/full bottom sheet; touch pan/zoom/tap works; no simultaneous three-way squeeze.
- Reduced motion: do not animate layout or sheet transitions beyond an accessible short fade/slide; preserve camera and positions.

## Accessibility, Registry, and Implementation Safety

Registry is shadcn official only; `frontend/components.json` declares no third-party registries or blocks. Use existing Radix/shadcn primitives for tabs, sheets, dialogs, tooltips, buttons, and focus behavior. No registry vetting is required beyond the official preset.

Every top tab, nested mode, filter, expansion, recovery action, graph control, timeline card, Inspector tab, sheet state, and “Show in graph” action is keyboard focusable with a visible `--ring` focus indicator. Tabs expose selected state and horizontal mobile scrolling does not trap keyboard focus. The bottom sheet exposes an accessible name, close control, Escape behavior, and half/full state controls. Node access has a readable DOM alternative or equivalent accessible selection description; do not rely on canvas color alone. Respect `prefers-reduced-motion`. Focus remains intentional after tab/view/sheet changes and returns to the invoking control when temporary Answer Graph or dialogs close.

## Interaction and Scene Contract

1. React owns the scene state: active top tab, nested mode, episode boundary, filters, selected element, focus, expansions, camera snapshot, timeline selection, Inspector sheet state, and temporary Answer Graph state.
2. Cytoscape is instantiated once for the active scene and updated through batched element/style diffs. Refresh and Episode changes retain the prior scene while loading where practical; no flashing blank canvas and no unnecessary instance recreation.
3. Initial Episode Overview and Character Network use fCoSE, then deterministic stored preset positions. Expansion adds 8–12 nodes by default, hard max 25, using local constrained/concentric layout. Important existing nodes remain fixed/constrained; never run a random global relayout after selection, focus, expansion, or timeline synchronization.
4. Evidence Chain uses readable left-to-right Dagre through pinned `cytoscape-dagre@4.0.0`; ELK is not added. Timeline is React/CSS, grouped by spoiler-safe plot thread and ordered by safe reveal/publication order. Fictional chronology may be display metadata only and cannot override reveal gating.
5. Selection dims unrelated content, synchronizes graph/timeline/Inspector, preserves camera, and never relayouts. `Clear focus`, `Undo expansion`, `Collapse`, `Reset view`, and `Back to Episode Overview` provide exploration recovery.
6. GraphRAG focus highlights visible entities in place. A safe focus absent from the current view opens a temporary 5–20-element Answer Graph. A micro Event maps to its visible major Event plus Inspector detail. Claim/Evidence opens Evidence Chain. Closing temporary state restores camera, selection, expansions, and timeline state exactly enough to continue exploration.
7. All visible and temporary states are derived only after the effective spoiler boundary is enforced. Future data must not affect visible count, layout force, whitespace, group name/count, search ranking, expansion hint, path existence, focus ID, cache result, or restoration state.

## UI Considerations

Applicable state considerations resolved: 32 covered, 8 backstop, 0 unresolved.

### Zero / one / many content states

Every graph, timeline, evidence, and collection surface must define its singular/plural copy and preserve a stable layout at 0, 1, and many items. Counts are only shown when they are derived from the spoiler-safe visible payload; do not infer hidden totals.

| Surface | Zero | One | Many | Layout contract |
|---------|------|-----|-------|------------------|
| Graph | `Nothing to map yet` | `1 story element` | `{n} story elements` | Keep the graph canvas and controls in place; center one visible node, use the empty-state panel for zero, and use bounded fit-to-view for many without exposing hidden space/counts. |
| Timeline | `No episode events yet` | `1 episode event` | `{n} episode events` | Keep the `Event Timeline` heading and rail; one event uses a full-width card, zero uses an explanatory empty card, and many use the existing grouped scroll/list layout. |
| Evidence | `No evidence is attached yet` | `1 evidence item` | `{n} evidence items` | Preserve the Claim → Evidence → Source structure; one item gets the full readable detail column, zero keeps Inspector tabs and next-step guidance, and many become a vertically scrollable grouped list. |
| Collection (Claims, Sources, or Notes) | `No {type} yet` | `1 {type}` | `{n} {type}` | Keep the collection heading and controls in all states; one item is a detail row/card, zero is an inline empty state, and many use a scrollable list with stable row heights and selection space. Use plural `{type}` only for many and singular `{type}` for one. |

### Long-text behavior

Long content must remain readable without horizontal page overflow. Truncation is reserved for compact navigation or graph labels; full text is available through reflowed detail surfaces or an explicit accessible expansion.

| Element | Long-text contract |
|---------|-------------------|
| Headings | Wrap to a maximum of two lines in cards and Inspector; reflow the surrounding content below rather than clipping. Page titles may wrap to three lines on mobile. |
| Labels | Wrap within cards/panels when meaning would be lost; graph labels truncate with ellipsis at the current zoom and expose the full human label on hover/select and to assistive technology. |
| Tabs | Keep the four top tabs and Inspector tabs single-line with horizontal scrolling on narrow screens; do not truncate a tab into an ambiguous label, and preserve the visible active tab while scrolling. |
| Claims | Wrap fully in the Inspector and Evidence Chain; reflow metadata below the claim and provide an accessible expand/collapse affordance for very long text. |
| Evidence | Wrap fully in readable detail cards; reflow source/type metadata beneath the text and keep the evidence region vertically scrollable. |
| Notes | Wrap and preserve user-entered line breaks in the full Inspector sheet; reflow edit/actions below the note and never clip content to a fixed-height row. |
| Source locators | Wrap long URLs, file paths, and locators at safe break opportunities; show a compact ellipsis only in dense rows with copy/open actions retaining the full value, and reflow to a stacked locator block in detail view. |

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| empty | Episode Overview / sparse Episode | ✅ covered | Render `Nothing to map yet` copy with episode/progress next step; never imply hidden future totals. |
| empty | Search | ✅ covered | Render `No visible matches` and a safe-name/progress hint; do not fall back to Full Graph. |
| empty | Evidence / Claims / Sources | ✅ covered | Render `No evidence is attached yet`; preserve Inspector tabs and explain the next selection. |
| loading | Graph projection / Episode switch | ✅ covered | Keep the last known scene visible with `Updating the story map…`; update shared elements incrementally where possible. |
| loading | Timeline | ✅ covered | Keep existing cards and mark the pending region; do not flash an empty timeline. |
| loading | Inspector | ✅ covered | Preserve selected header/context and show a compact detail skeleton or `Loading details…`. |
| error | Projection / layout / image / Inspector / expansion | ✅ covered | Show `We couldn’t update this view.` plus `Try again` or scoped retry; sanitize internal backend/Neo4j errors. |
| partial | Graph or timeline payload | ✅ covered | Show `Some story details are still loading.` and `Retry missing details`; retain safe elements already rendered. |
| populated | Story / Characters / Evidence / Advanced | ✅ covered | Four-tab hierarchy and nested modes remain stable; default Story opens bounded Episode Overview plus coordinated timeline. |
| selection | Node, edge, timeline event, claim/source | ✅ covered | Use non-color selection ring/weight, dim unrelated elements, sync Inspector/timeline, preserve camera and layout. |
| focus | Search, Chat, path, GraphRAG | ✅ covered | Show a compact `Focused` affordance and `Clear focus`; use in-place highlight or scoped temporary Answer Graph. |
| temporary | Answer Graph | ✅ covered | Label it `Answer Graph`, constrain to 5–20 elements, provide close/restore, and restore camera/selection/expansions/timeline. |
| expansion | Semantic expansion | ✅ covered | Use human concept labels, 8–12 default additions/max 25, and show Undo/Collapse/Reset without hidden totals. |
| zoom | Cytoscape scene | ✅ covered | Semantic zoom changes presentation only; label policies are stable and zoom never fetches or expands data. |
| overflow | Dense Full Graph / long labels | 🧪 backstop | Visual verification at Advanced density confirms labels clip/wrap safely, controls remain reachable, and the viewport never gains accidental page overflow. |
| overflow | Mobile top tabs | ✅ covered | Tabs scroll horizontally with visible active state; no tab is truncated into an ambiguous label. |
| overflow | Mobile Inspector content | 🧪 backstop | Visual verification confirms long claims, evidence text, notes, and source locators wrap within the full-height sheet and remain scrollable. |
| responsive | Desktop / tablet / mobile | 🧪 backstop | Visual verification at representative desktop, tablet, and narrow mobile widths confirms graph/timeline/Inspector composition follows the responsive truths above. |
| responsive | Mobile sheet half/full states | ✅ covered | Half-height preserves graph/timeline context; full-height provides readable detail; drag handle, close, Escape, and state toggle are available. |
| accessibility | Tabs, controls, graph selection, Inspector, sheet | ✅ covered | Keyboard focus, visible ring, labels, non-color status cues, Escape/return focus, and reduced motion are required implementation behavior. |
| accessibility | Cytoscape node access | 🧪 backstop | Manual keyboard/screen-reader-oriented verification confirms every selected node has a readable accessible name and action path. |
| security | Spoiler-safe projection/search/focus/restore | ✅ covered | Effective boundary is enforced before projection/serialization; no hidden counts, IDs, layout influence, ranking, or path hints appear. |
| resilience | Character images / provenance | ✅ covered | Episode-safe image only; invalid/missing image falls back to initials/silhouette/icon; provenance stays restrained and non-color-only. |

Backstop rows are deliberate human visual checks: they cannot be truthfully proven by static source inspection alone. They must produce screenshots or a short manual verification record for desktop, mobile, dense Advanced graph, long evidence text, and accessible node navigation.

## Acceptance Evidence

The implementation is ready for UI verification when the following evidence exists:

- A fixed S01E01 snapshot and cumulative S01E02 snapshot show the selected Episode Overview variant within 12–28 target nodes, max 40 nodes, preferred <35 edges, max 60 edges, with no persistent procedural labels.
- Desktop evidence shows all four top tabs and the Story → Episode Overview + Event Timeline coordination; Characters → Character Network + Local Neighborhood; Evidence → Evidence Chain + temporary Answer Graph; Advanced → Full Graph/debug.
- Mobile evidence shows horizontally scrollable top tabs, touch graph use, and Inspector half/full bottom-sheet states without squeezing graph, timeline, and Inspector together.
- Interaction tests prove selection synchronization, camera preservation, no relayout on selection/focus, deterministic positions across Episode switches, local expansion, Collapse/Undo/Reset, and exact Answer Graph restoration.
- State tests or fixtures cover empty, loading-over-previous-scene, error, partial, populated, selection, focus, temporary Answer Graph, long-text, overflow, and image fallback behavior using the concrete copy above.
- Accessibility evidence covers keyboard traversal, visible focus, tab semantics, Escape/return focus, non-color distinctions, reduced motion, and readable node/Inspector access.
- Regression evidence records backend `pytest`, frontend `vitest`, `npm run lint`, `npm run build`, `git diff --check`, and the real golden path including Episode 2 → Episode 1 spoiler disappearance. Documentation evidence confirms README/root docs describe the shipped v1.3 behavior.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | Existing Radix/shadcn primitives only; no new third-party blocks | not required |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** PASS
