# hdgrafcehennemi — Frontend Design System & UI-SPEC Contract Cheat Sheet

Verified 2026-08-05 while producing Phase 9's UI-SPEC (09-UI-SPEC.md, 309 lines).
Read this before ANY frontend feature plan or UI-SPEC/UI-audit task — it saves
re-reading the whole component tree. Token claims below were checked against the
live files this session.

## Where the design system lives

- `frontend/src/index.css` — Tailwind v4 entry: `@theme inline` token block,
  `:root`/`.dark` (identical today — dark is the only theme; a future light
  toggle can diverge without restructuring), `@layer base`, and the
  `.graph-canvas-backdrop` radial violet glow + 24px dot grid.
- Fonts: self-hosted via `@fontsource-variable/space-grotesk` +
  `@fontsource-variable/inter` (imported in index.css). **Never add a font.**
- `frontend/components.json` — shadcn initialized: style `radix-nova`,
  baseColor zinc, iconLibrary lucide, **empty registries** (no third-party
  blocks; ui/* components only).
- `frontend/src/App.css` — empty; all styling is tokens/utilities.

## Token values (exact — do not re-derive)

| Token | Value | Notes |
|---|---|---|
| background | `#0F172A` | dominant surface, canvas |
| card / popover / sidebar | `#192134` | all panels, sheets, dialogs, controls |
| elevated | `#1E2740` | hover surfaces, cluster parents, empty-canvas fill |
| muted | `#131936` | pill tracks, badges, avatar fallback |
| muted-foreground | `#94A3B8` | secondary text, placeholders, inactive |
| primary | `#4338CA` | primary buttons, active progress fill, ring |
| secondary | `#6366F1` | — |
| accent | `#7C3AED` | canvas selection/hover overlays, focus ring color |
| destructive | `#DC2626` | destructive actions only |
| warning | `#F59E0B` | unlock-progress confirmations only |
| border / input | `rgba(255,255,255,0.08)` | all 1px rings (`ring-1 ring-border`) |
| radius | `0.625rem` | scaled sm..4xl via `--radius-*` |

Fonts: `--font-heading` = Space Grotesk (headings/display, 600 weight),
`--font-sans` = Inter (body/label, 400/500). Typography contract: 4 sizes
(12 label / 14 body / 20 heading / 24 display), 2 weights (400/600).

## Graph-semantic colors (committed — never re-derive)

- Node types (`graphStylesheet.ts` + `GraphLegend.tsx` NODE_TYPES):
  Character `#38BDF8` ellipse · Event `#2DD4BF` round-rect ·
  Location `#60A5FA` round-rect · Organization `#FB7185` diamond ·
  Episode `#FBBF24` tag · Series star · Object ellipse ·
  UserNote dashed round-rect. Idle fill `#131936`; canonical = solid border,
  non-canonical = dashed border.
- Edge families: `relationshipStyles.ts` `EDGE_TYPE_TO_FAMILY` + `FAMILY_HEX`.
- Claim accent `#D946EF`, Evidence accent `#FB923C` (exported from
  `DetailPanel.tsx` — citation chips reuse them).
- Cytoscape interaction classes: `.selected-dominant` (violet overlay,
  3px accent border, per-type size bump), `.hovered`, `.edge-active`
  (width 3.5, arrow-scale 1.3), `.faded` (node opacity 0.25 / edge 0.15).
- Current layout: cose-bilkent, `padding: 48, nodeRepulsion: 8000,
  idealEdgeLength: 100, edgeElasticity: 0.45`, `animate: reduced? false : 'end'`.
  **Phase 9 replaces the layout pass with cytoscape-fcose (D-03)** — cose-bilkent
  stays installed as fallback only.

## Component inventory (all exist — reuse, never rebuild)

- `ui/`: alert, badge, button, card, collapsible, dialog, scroll-area, select,
  separator, sheet, skeleton, tabs, textarea, tooltip.
- `graph/`: **GraphCanvas.tsx (530-line god-file)** — layout registration +
  `layoutOptionsFor` at top, imperative `runLayout(cy)` effect keyed on `graph`
  (react-cytoscapejs declarative layout prop NEVER re-lays-out on element
  change), tap-select (closedNeighborhood → fade others → selected-dominant →
  `onSelect`), external `focusedElementIds` + `revealElementIds` effects
  (2.2s reveal), CreateCustomNodeDialog + bottom-left FAB. · GraphControls
  (fixed bottom-left 44px icon buttons, Tooltip-wrapped, zoom/fit/reset) ·
  GraphLegend (Collapsible bottom-left, NodeSwatch/EdgeSwatch) ·
  GraphFocusIndicator · GraphStatus (Loading/Error/Empty trio, copy locked) ·
  `graphElements.ts` · `graphStylesheet.ts` · `relationshipStyles.ts`.
- `detail/`: DetailPanel (Sheet + Tabs Overview/Notes/Claims/Evidence/History —
  tab set gated on selected element kind), StructuralEdgeCard (structural edges
  never reach DetailPanel — App.tsx routes them), RevisionHistoryPanel
  (`diffFields` shows field NAMES only — Phase 9 FEAT-11 upgrades to values).
- `episode/`: SeriesSelect (radix Select), EpisodeSelector (ToggleGroup pills
  md+ / Select <md; active pill `data-[state=on]:bg-accent`; locked pills
  `text-muted-foreground` + Lock icon + sr-only), ConfirmAdvanceModal
  (Dialog `border-warning/40`, copy locked verbatim).
- `chat/`: ChatLauncher, ChatSheet, ChatPanel (error banners + "Ask about
  {episode} and earlier…" placeholder), MessageBubble/List, SessionPicker,
  CitationChip, ChangeSetCard.
- `layout/`: AppShell (header Card, h1 `font-heading text-2xl`
  "HD Graf Cehennemi" → **"Spoilerless"** in Phase 9 REBRAND-01), HeaderNavAction.
- `settings/SettingsPage.tsx` (Card max-w-lg), `auth/LoginPage.tsx`.
- Hooks: `useGraph` (status machine + `refetch` (loading flash) vs `refresh`
  (in-place, no flash) — key distinction used everywhere), `useSeries`,
  `useEpisodes`, `useWatchProgress` (Phase 9 PROB-31 fixes requestChange
  silent no-ops lines 133/139 + hydration race), `useNotes`, `useChatSessions`,
  `useRevisions`. API: `client.ts` central apiFetch + per-resource modules.
- `lib/byok.ts` — localStorage pattern; `BYOK_STORAGE_KEY =
  'hdgraf:byok-llm-settings'` (Phase 9 renames to `spoilerless:...` with
  read-compat migration).

## Conventions (contract-level)

- **NO router.** App.tsx is state-driven (`view: 'graph' | 'settings'`).
  Phase 9 FEAT-09 share route must match `window.location.pathname` against
  `/^\/share\/[A-Za-z0-9_-]+$/` at the App root, before the auth gate —
  zero new deps.
- 44px min touch targets (`min-h-[44px] min-w-[44px]`); spacing scale 4px
  (xs 4 … 3xl 64) with exceptions: 44px targets, 48px graph fit/layout padding.
- `prefers-reduced-motion` captured at module scope (GraphCanvas pattern);
  `transitionMs = 0` and `animate: false` when reduce.
- Locked copy (verbatim, from GraphStatus/ConfirmAdvanceModal):
  "Nothing revealed yet" / "Advance your watch progress to unlock the story.";
  "Couldn't load the graph. Check the backend connection and retry." + Retry;
  unlock dialog "Unlock {code}?" / "Episodes 1 through {N} will be considered
  watched. This can't be undone."
- Selection model: tap node → `.selected-dominant` + neighborhood kept,
  difference faded; tap empty canvas clears. External graph_focus (citation
  chips, ChangeSet apply) reuses the SAME classes; focus auto-clears when
  referenced ids leave the payload. Focus fit uses `cy.fit(focused, 48)`.
- Every graph element derives from the backend response; frontend never
  manufactures a second representation (PROJECT-SPEC §6). New search/palette
  features search the already-fetched, already-boundary-filtered payload.

## Phase 9 locked UI decisions (D-03/D-04/D-09/D-11/D-12 + gates)

- **D-03:** `cytoscape-fcose@2.2.0` is the ONLY new dependency of the phase
  (npm legitimacy gate OK 2026-08-05: 11.3M/wk, iVis-at-Bilkent, no postinstall).
  Register once module-level with try/catch fallback to built-in 'cose'
  (existing cose-bilkent pattern); extend `layoutOptionsFor` union to `'fcose'`;
  compound parent nodes per cluster key (subplot/cluster tag or episode band
  from `visible_from_order` via the episodes prop); `randomize: false` +
  position cache per `(seriesId, visibleUntilOrder)` for determinism.
- **D-04:** node/edge-type filter toggles (new `GraphFilterPanel.tsx`, Cytoscape
  class toggling — never relayout), zoom-based label culling (stylesheet on
  `cy.zoom()`, labels hidden < 0.8), focus/neighborhood mode via existing
  `faded`/`selected-dominant`, edge opacity falloff. **Extract**
  `layoutConfig.ts` / `filterState.ts` / `focusReducer.ts` (D-06) — do NOT grow
  the 530-line god-file.
- **D-09/D-10:** share links = snapshot-at-creation; read-only `/share/:token`
  route distinct from AppShell, reuses the SAME spoiler-filtering path;
  token `secrets.token_urlsafe(32)`, store hash, 30-day expiry, revoke = delete.
- **D-11:** FEAT-05 export is **Markdown only** — Blob + `a[download]`, zero deps.
- **D-12:** rename EVERY user-visible `hdgrafcehennemi` → `spoilerless`
  (AppShell h1 line 46, `frontend/index.html` title line 12, root `index.html`
  window-title + GITHUB_REPOSITORY_URL), byok.ts key + migration. Do it EARLY
  in the phase so later plans touch renamed paths.
- **fuse.js = SUS, EXCLUDED** — zero-dep substring search (new
  `lib/searchIndex.ts`) for FEAT-01/07/08 + the ⌘K palette (FEAT-08);
  the palette doubles as FEAT-11's quick-switcher.
- `GraphCanvas.test.tsx:200` `toHaveLength(11)` → count-independent (D-05).

## UI-SPEC production workflow (gsd-ui-researcher — verified working)

1. Read agent def + template FIRST: `~/AppData/Local/hermes/agents/
   gsd-ui-researcher.md` and `~/AppData/Local/hermes/gsd-core/templates/
   UI-SPEC.md`.
2. Pre-populate from CONTEXT.md / RESEARCH.md / REQUIREMENTS.md / ROADMAP.md —
   never re-ask locked decisions; RESEARCH.md is usually exhaustive.
3. Scout the LIVE tree (components.json, index.css tokens, component inventory
   via `find frontend/src -type f | sort`, App.tsx view state). Token claims
   must match the files — the frontend is a moving target (sibling agents edit
   it between sessions).
4. Write the contract as: template's 6 dimensions (design system table,
   spacing, typography, color, copywriting, registry safety) + an Interaction
   Contract section (keyboard/focus/motion/touch/hover/selection) +
   Screen-by-Screen sections (one per FEAT/PROB/REBRAND item; each entry:
   Trigger · Visual contract with exact token values · Interaction · Files
   M=modify/C=create) + a Consolidated File Manifest (create/modify lists).
5. The accent **reserved-for** list is mandatory and explicit — never
   "all interactive elements".
6. Return exactly `## UI-SPEC COMPLETE` + a 3-5 line summary (the parent task
   format overrides the template's longer structured return).
7. Write with write_file in ONE call to
   `$PHASE_DIR/$PADDED_PHASE-UI-SPEC.md` (e.g. `09-UI-SPEC.md`); verify with
   `wc -l` + section grep after.
