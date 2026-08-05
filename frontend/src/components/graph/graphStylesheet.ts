// Full Cytoscape stylesheet for the graph canvas: node-type shape/color
// mapping, relationship-type edge coloring, origin border treatment, and the
// selection/hover highlight/fade classes wired by GraphCanvas.tsx.
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
//
// Phase 03.1: edge color derived from EDGE_TYPE_TO_FAMILY (relationshipStyles.ts),
// preferred-reduced-motion transition control via buildGraphStylesheet().

import type { StylesheetJsonBlock } from 'cytoscape'
import { edgeColorFor } from './relationshipStyles'

const DEFAULT_NODE_SIZE = 36
const SERIES_NODE_SIZE = 64

export function buildGraphStylesheet(prefersReducedMotion: boolean): StylesheetJsonBlock[] {
  const transitionMs = prefersReducedMotion ? 0 : 150

  return [
    {
      selector: '.filtered-out',
      style: {
        display: 'none',
      },
    },
    {
      selector: 'node[isCluster]',
      style: {
        shape: 'round-rectangle',
        'background-color': '#1E2740',
        'background-opacity': 0.7,
        'border-width': 1,
        'border-color': '#334155',
        'border-style': 'solid',
        color: '#94A3B8',
        'font-size': 10,
        'font-weight': 'bold',
        'text-valign': 'top',
        'text-halign': 'left',
        'text-margin-y': 4,
        padding: '24px',
      },
    },
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
        width: DEFAULT_NODE_SIZE,
        height: DEFAULT_NODE_SIZE,
        'border-width': 1.5,
        // Dashed is the forward-compatible default border for non-canonical
        // origins (user-content, future candidate/automatic data). Overridden
        // to solid below for origin === 'canonical'.
        'border-color': 'rgba(255, 255, 255, 0.08)', // --border
        'border-style': 'dashed',
        'transition-property': 'background-color, border-color, border-width, width, height, opacity, overlay-color, overlay-opacity, overlay-padding',
        'transition-duration': transitionMs,
      },
    },
    // --- Node-type shape/color mapping (03.1-UI-SPEC.md) ---
    {
      selector: 'node[nodeType = "Character"]',
      style: { shape: 'ellipse', width: 44, height: 44, 'background-color': '#38BDF8' },
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
      style: { shape: 'round-rectangle', width: 44, height: 44, 'background-color': '#2DD4BF' },
    },
    {
      selector: 'node[nodeType = "Location"]',
      style: { shape: 'round-rectangle', width: 44, height: 44, 'background-color': '#60A5FA' },
    },
    {
      selector: 'node[nodeType = "Organization"]',
      style: { shape: 'diamond', width: 48, height: 48, 'background-color': '#FB7185' },
    },
    {
      selector: 'node[nodeType = "Episode"]',
      style: { shape: 'tag', width: 40, height: 40, 'background-color': '#FBBF24' },
    },
    {
      selector: 'node[nodeType = "UserNote"]',
      // Reserved for Phase 3 — no seed data uses this type yet.
      style: { shape: 'round-rectangle', width: 40, height: 40, 'border-style': 'dashed' },
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
    // --- Obsidian-style simple nodes (08-05 user-directed declutter) ---
    // Nodes stamped `simple` by graphElements.ts (no portrait AND < 3 edges)
    // collapse to a small neutral dot + quiet gray label — the reference
    // "Journal" look (photo 08-05). Placed after every node-type
    // shape/color selector so it wins at equal specificity; the portrait
    // selector `node[imageUrl]` can never match a `simple` node (simple
    // requires no imageUrl).
    {
      selector: 'node[simple]',
      style: {
        shape: 'ellipse',
        width: 13,
        height: 13,
        'background-color': '#64748B', // slate-500: quiet neutral dot
        'border-width': 1,
        'border-color': 'rgba(255, 255, 255, 0.12)',
        'border-style': 'solid',
        color: '#94A3B8', // --muted-foreground
        'font-size': 9,
        'text-margin-y': 4,
      },
    },
    // User-origin edges: dashed line
    {
      selector: 'edge[origin = "user"]',
      style: { 'line-style': 'dashed' },
    },
    // --- Selection-driven highlight/fade (02-RESEARCH.md Pattern 3) ---
    {
      selector: 'node.selected-dominant',
      style: {
        'background-color': '#192134', // --card
        'border-color': '#7C3AED', // --accent
        'border-width': 3,
        'overlay-color': '#7C3AED',
        'overlay-opacity': 0.35,
        'overlay-padding': 8,
      },
    },
    // Hover glow (Phase 03.1)
    {
      selector: 'node.hovered',
      style: {
        'overlay-color': '#7C3AED',
        'overlay-opacity': 0.15,
        'overlay-padding': 6,
      },
    },
    // Selected size bump per node type (Phase 03.1)
    {
      selector: 'node[nodeType="Character"].selected-dominant',
      style: { width: 51, height: 51 },
    },
    {
      selector: 'node[nodeType="Event"].selected-dominant',
      style: { width: 51, height: 51 },
    },
    {
      selector: 'node[nodeType="Location"].selected-dominant',
      style: { width: 51, height: 51 },
    },
    {
      selector: 'node[nodeType="Organization"].selected-dominant',
      style: { width: 55, height: 55 },
    },
    {
      selector: 'node[nodeType="Episode"].selected-dominant',
      style: { width: 46, height: 46 },
    },
    {
      selector: 'node[nodeType="UserNote"].selected-dominant',
      style: { width: 46, height: 46 },
    },
    {
      selector: 'node[nodeType="Series"].selected-dominant',
      style: { width: 74, height: 74 },
    },
    // Simple-node selection bump — must sit AFTER the per-type selected
    // bumps (all specificity 3, later wins) or a selected `simple` Character
    // would jump to the 51px portrait size.
    {
      selector: 'node[simple].selected-dominant',
      style: { width: 20, height: 20 },
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
        'line-color': (ele) => edgeColorFor(ele.data('edgeType')),
        'target-arrow-color': (ele) => edgeColorFor(ele.data('edgeType')),
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'text-max-width': '80px',
        'text-wrap': 'ellipsis',
        'transition-property': 'line-color, target-arrow-color, width, opacity',
        'transition-duration': transitionMs,
      },
    },
    // Dashed candidate edges
    {
      selector: 'edge[claimStatus="candidate"]',
      style: { 'line-style': 'dashed' },
    },
    {
      // Phase 03.1 supersession (03.1-UI-SPEC.md): hover/active edge uses
      // type-aware colors from the base selector rather than hardcoded
      // #6366F1 — the base line-color/target-arrow-color functions already
      // handle per-type coloring, so we only bump width/opacity/arrow-scale.
      selector: 'edge.hovered, edge.edge-active',
      style: {
        width: 3.5,
        opacity: 1,
        'arrow-scale': 1.3,
      },
    },
    {
      selector: 'edge.faded',
      style: { opacity: 0.15 },
    },
    // FEAT-03 (09-07): transient glow on elements newly revealed by a forward
    // episode advance (UI-SPEC §10.5) — #7C3AED overlay at 0.45, padding 10,
    // applied for 4000ms by GraphCanvas then auto-cleared. The 2-cycle pulse
    // (overlay-opacity 0.45→0.15→0.45) is driven imperatively by GraphCanvas
    // via element.animate — Cytoscape JSON stylesheets cannot express
    // keyframes; under prefers-reduced-motion the base transitions are 0ms so
    // the glow is static with no pulse.
    {
      selector: 'node.newly-revealed, edge.newly-revealed',
      style: {
        'overlay-color': '#7C3AED',
        'overlay-opacity': 0.45,
        'overlay-padding': 10,
      },
    },
    // FEAT-06 (09-11) path finder: source/target endpoints get a violet
    // #7C3AED border (width 3); path elements get a violet overlay + thicker
    // edges; everything else fades via the existing `.faded` class.
    {
      selector: 'node.path-source, node.path-target',
      style: {
        'border-color': '#7C3AED',
        'border-width': 3,
      },
    },
    {
      selector: 'node.on-path',
      style: {
        'overlay-color': '#7C3AED',
        'overlay-opacity': 0.3,
      },
    },
    {
      selector: 'edge.on-path',
      style: {
        'width': 3.5,
        'line-color': '#7C3AED',
        'target-arrow-color': '#7C3AED',
      },
    },
  ]
}

// Legacy re-export for callers not yet migrated to buildGraphStylesheet().
// New code should call buildGraphStylesheet() directly.
export const graphStylesheet = buildGraphStylesheet(false)
