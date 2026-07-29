# Phase 2: Polished Cytoscape Graph Experience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 02-polished-cytoscape-graph-experience
**Areas discussed:** Startup flow, Graph layout, Edge selection, Progress persistence, Confirm scope, Edge panel

---

## Startup flow

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-select Dexter S01E01 | Immediately fetch and show the S01E01 graph on load, selectors pre-filled | |
| Explicit empty state first | Require deliberate series then episode selection before any graph loads | ✓ |

**User's choice:** Explicit empty state first
**Notes:** Matches the literal required flow more closely than auto-selecting.

---

## Graph layout

| Option | Description | Selected |
|--------|-------------|----------|
| Add cytoscape-cose-bilkent | Install the extension for better small-graph layout quality per UI-SPEC preference | ✓ |
| Use built-in cose only | No new dependency, use Cytoscape's bundled cose layout (UI-SPEC's accepted fallback) | |

**User's choice:** Add cytoscape-cose-bilkent
**Notes:** None.

---

## Edge selection

| Option | Description | Selected |
|--------|-------------|----------|
| Structural edges not selectable | Only claim-backed edges open the detail panel | |
| All edges selectable, different panel content | Structural edges also clickable, with a distinct minimal panel state | ✓ |

**User's choice:** All edges selectable, different panel content
**Notes:** Follow-up (see "Edge panel" below) nailed down exactly what that distinct content looks like.

---

## Progress persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Persist in sessionStorage | Selected series + visible_until_order survive a refresh within the same tab | ✓ |
| In-memory only, resets on reload | Plain React state, refresh returns to startup default | |

**User's choice:** Persist in sessionStorage
**Notes:** None.

---

## Confirm scope

| Option | Description | Selected |
|--------|-------------|----------|
| Forward only | Confirmation modal only on advancing to a later episode; backward moves instant | |
| Every change confirms | Confirmation modal on any episode change, forward or backward | ✓ |

**User's choice:** Every change confirms
**Notes:** Locked UI-SPEC copy ("Unlock S01E0X?") is forward-phrased; CONTEXT.md flags a backward-move copy variant as Claude's discretion since this decision extends confirmation beyond what the existing copy literally describes.

---

## Edge panel

| Option | Description | Selected |
|--------|-------------|----------|
| Overview tab only, other tabs disabled | Reuse the tabbed Sheet, disable Claims/Evidence tabs for structural edges | |
| Single minimal card, no tabs | A distinct tab-less layout just for structural edges | ✓ |

**User's choice:** Single minimal card, no tabs
**Notes:** Reinforces the "all edges selectable" decision from above with a concrete panel design.

---

## Claude's Discretion

- Exact frontend file/component structure (`api/`, `types/`, `hooks/`, `components/{layout,episode,graph,detail}/`).
- Exact confirmation-modal copy variant for backward/rewatch moves (extends the locked UI-SPEC copy, doesn't replace it).
- Precise fallback trigger from `cose-bilkent` to `cose` (only on an actual build/runtime failure).
- Series selector remains a real interactive `Select` despite only one series existing today.

## Deferred Ideas

None raised during this discussion.
