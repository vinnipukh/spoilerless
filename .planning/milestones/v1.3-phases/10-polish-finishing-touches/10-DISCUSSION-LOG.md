# Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves alternatives considered.

**Date:** 2026-08-13
**Phase:** 10-polish-finishing-touches
**Areas discussed:** Scope amendment, View navigation and mobile structure

---

## Scope Amendment

| Option | Description | Selected |
|--------|-------------|----------|
| Replace Phase 10 | Replace polish scope with visualization redesign | |
| Add Phase 11 | Keep Phase 10 polish; place redesign in Phase 11 | |
| Expand Phase 10 | Combine polish and visualization redesign | ✓ |

**User's choice:** Expand Phase 10 to include both polish and redesign.
**Notes:** This overrides existing roadmap boundary forbidding new features/architecture in Phase 10.

---

## Desktop View Switching

| Option | Description | Selected |
|--------|-------------|----------|
| Top view tabs | Clear; reuses existing Graph/Timeline pattern | ✓ |
| Left navigation rail | Persistent; costs canvas width | |
| Dropdown | Compact; less discoverable | |

**User's choice:** Top view tabs.

---

## View Hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| Primary tabs + overflow | Overview, Characters, Timeline visible; specialized views contextual | |
| Seven tabs | Maximum discoverability; crowded | |
| Four tabs | Story, Characters, Evidence, Advanced; contextual modes nested | ✓ |

**User's choice:** Four tabs with contextual nested modes.

---

## Mobile Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom tabs | Story, Characters, Evidence; Advanced under More | |
| Top scrollable tabs | Mirrors desktop hierarchy | ✓ |
| Story canvas + sheets | Minimal switching | |

**User's choice:** Top scrollable tabs.

---

## Mobile Inspector

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom sheet | Preserves context; half/full heights | ✓ |
| Full-screen detail | More room; loses visual context | |
| Side drawer | Desktop parity; narrow on phones | |

**User's choice:** Bottom sheet.

## Claude's Discretion

- Exact contextual subnavigation inside four main tabs.
- Technical choices already bounded by supplied brief and repository audit requirement.

## Deferred Ideas

- NVL production migration, 3D visualization, research-grade StoryFlow, unrelated UI redesign.
