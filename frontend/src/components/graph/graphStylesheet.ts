// Full Cytoscape stylesheet for the graph canvas: node-type shape mapping,
// origin border treatment, and the tap-driven selection highlight/fade
// classes wired by GraphCanvas.tsx.
//
// 02-RESEARCH.md Pitfall 1: the wire value for `origin` in this project is
// literally 'canonical' — never the design doc's placeholder 'curated'. No
// selector below branches on the literal string 'curated'.
//
// 02-RESEARCH.md Pitfall 2 / Open Question 1: `Episode` and `Series` are
// real, always-present node types with no shape assigned by 02-UI-SPEC.md's
// original table. Both get an explicit shape here (documented as a
// Claude's-discretion addition in 02-UI-SPEC.md itself, not silently
// invented) so neither falls through to Cytoscape's bare default ellipse.

import type { StylesheetJsonBlock } from 'cytoscape'

const NODE_SIZE = 36
const SERIES_NODE_SIZE = 46

export const graphStylesheet: StylesheetJsonBlock[] = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-size': 10,
      color: '#FFFFFF',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 6,
      'text-max-width': '80px',
      'text-wrap': 'ellipsis',
      'background-color': '#131936', // --muted (idle fill for all node types)
      width: NODE_SIZE,
      height: NODE_SIZE,
      'border-width': 1.5,
      // Dashed is the forward-compatible default border for any non-canonical
      // origin (no `automatic`/`user` data exists yet — Phases 3/5 scope);
      // overridden to solid below for origin === 'canonical'.
      'border-color': 'rgba(255, 255, 255, 0.08)', // --border
      'border-style': 'dashed',
    },
  },
  // --- Node-type shape mapping (02-UI-SPEC.md ## Color node-type table) ---
  {
    selector: 'node[nodeType = "Character"]',
    style: { shape: 'ellipse' },
  },
  // Portrait background for Character nodes that carry a Fandom image_url
  // (graphElements.ts only sets the `imageUrl` data key for Character nodes,
  // and only when a value exists, so this selector can never match other
  // node types). No `background-image-crossorigin` here: Fandom's CDN
  // (static.wikia.nocookie.net) doesn't send CORS headers, and requesting
  // 'anonymous' mode makes Cytoscape treat the resulting opaque-response
  // failure as a load error and draw its own broken-image glyph — worse than
  // doing nothing. Loading without crossorigin taints the canvas (blocks
  // cy.png()-style exports, which this app doesn't use) but renders
  // correctly; if the image 404s or is blocked outright, Cytoscape falls
  // back to the node's flat background-color fill — there is no HTML <img>
  // element here to leave a broken-image box.
  {
    selector: 'node[nodeType = "Character"][imageUrl]',
    style: {
      'background-image': 'data(imageUrl)',
      'background-fit': 'cover',
      'background-clip': 'node',
    },
  },
  {
    selector: 'node[nodeType = "Event"]',
    style: { shape: 'round-rectangle' },
  },
  {
    selector: 'node[nodeType = "Location"]',
    style: { shape: 'round-rectangle' },
  },
  {
    selector: 'node[nodeType = "Organization"]',
    style: { shape: 'diamond' },
  },
  {
    selector: 'node[nodeType = "UserNote"]',
    // Reserved for Phase 3 — no seed data uses this type yet.
    style: { shape: 'round-rectangle', 'border-style': 'dashed' },
  },
  // --- Additions beyond the original design contract (Pitfall 2 / Open Question 1) ---
  {
    selector: 'node[nodeType = "Episode"]',
    style: { shape: 'tag' },
  },
  {
    selector: 'node[nodeType = "Series"]',
    style: { shape: 'star', width: SERIES_NODE_SIZE, height: SERIES_NODE_SIZE },
  },
  // --- Origin border treatment ---
  {
    selector: 'node[origin = "canonical"]',
    style: { 'border-style': 'solid' },
  },
  // --- Selection-driven highlight/fade (02-RESEARCH.md Pattern 3) ---
  {
    selector: 'node.selected-dominant',
    style: {
      'background-color': '#192134', // --card
      'border-color': '#7C3AED', // --accent
      'border-width': 3,
    },
  },
  {
    selector: 'node.faded',
    style: { opacity: 0.25 },
  },
  {
    selector: 'edge',
    style: {
      label: 'data(label)',
      'font-size': 9,
      color: '#94A3B8', // --muted-foreground
      width: 1.5,
      'line-color': 'rgba(255, 255, 255, 0.08)', // --border (idle)
      'target-arrow-color': 'rgba(255, 255, 255, 0.08)',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'text-max-width': '80px',
      'text-wrap': 'ellipsis',
    },
  },
  {
    selector: 'edge.hovered, edge.edge-active',
    style: {
      'line-color': '#6366F1', // --secondary (hover-or-selected)
      'target-arrow-color': '#6366F1',
      width: 2.5,
    },
  },
  {
    selector: 'edge.faded',
    style: { opacity: 0.15 },
  },
]
