# GSD Phase Scope Amendments

Use when a detailed new brief conflicts with an existing HD Graf/Spoilerless ROADMAP phase boundary.

## Required sequence

1. Run `gsd-tools query init.phase-op <phase>` and read the phase's ROADMAP goal, requirements, and explicit exclusions before treating the supplied brief as phase scope.
2. State the exact conflict. Ask one product-level routing question:
   - replace current phase scope,
   - add a later phase,
   - expand current phase to contain both.
3. Do not silently reinterpret ROADMAP. User choice is a scope amendment and must be recorded in CONTEXT.md as an explicit decision.
4. If user expands/replaces scope, tell downstream planner to reconcile both `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` before implementation. Preserve old obligations unless user explicitly removes them.
5. Keep canonical refs to original ROADMAP/REQUIREMENTS plus prior phase CONTEXT. Mark exactly which old boundary sentence is superseded; do not imply whole document is void.
6. Discuss only unresolved product decisions. Treat detailed user brief decisions as locked; avoid re-asking them.
7. Check `workflow.auto_advance` after context commit. A persistent true value triggers plan-phase even without `--auto`/`--chain`; load chain workflow and honor it rather than ending at a manual next-step summary.

## Spoilerless visualization example

Phase 10 originally allowed regression/UAT/docs only and explicitly prohibited new features or architecture. Narrative visualization redesign therefore required an explicit routing decision. User chose expansion: original `POLISH-01..03` remained mandatory; redesign requirements were added; planner was tasked to reconcile tracking files.

## Pitfalls

- Long acceptance brief does not automatically override roadmap phase boundary.
- Do not place conflicting work into current phase by assumption.
- Do not drop original closeout requirements when expansion means “both.”
- Do not ask implementation questions already settled in supplied brief.
- Do not report discussion complete while configured auto-advance remains unhandled.
