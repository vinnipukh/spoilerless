---
status: complete
task: "Align .planning plans with root ROADMAP.md"
date: 2026-07-28
requirement_count: 30
phase_count: 8
commit: "docs(planning): align Prototype v0 with canonical roadmap"
---

# Quick Task Summary: Align `.planning` with Root `ROADMAP.md`

## Changes

- Reframed `.planning/PROJECT.md` around the complete canonical Prototype v0 and retained qualified brownfield facts: existing scaffolds and the unexecuted seed script are not described as runtime-verified or complete.
- Rebuilt `.planning/REQUIREMENTS.md` as 30 pending Prototype v0 requirements covering root milestones 1–8, with each requirement assigned exactly once.
- Replaced the two-phase backend-only `.planning/ROADMAP.md` with eight dependency-ordered phases covering infrastructure, metadata, spoiler API, evidence-backed seed data, React/Cytoscape spoiler UX, notes/manual editing, revision/revert, and future-extraction preparation.
- Updated `.planning/STATE.md` to preserve Phase 1 pending project state, list all eight pending phases, state the complete release target, and record this quick task.
- Kept automated source ingestion/extraction, operational LLM extraction, and LLM chat explicitly post-v0.
- Did not modify canonical root `ROADMAP.md`, product source, configuration, data, tests, or research files.

## Verification Evidence

- Coverage/consistency Python assertion: `PASS: 30 unique requirements; 30 traceability rows; every requirement mapped exactly once; roadmap/state phases 1-8 consistent`.
- Canonical capability/post-v0 Python assertion: `PASS: all 8 canonical capability groups present; automated ingestion/extraction and LLM chat explicitly post-v0`.
- Root immutability check: `git diff --exit-code -- ROADMAP.md` passed.
- Scope check confirmed tracked edits were limited to the four required planning documents before adding required quick-task artifacts.
- `git diff --check -- .planning/PROJECT.md .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/STATE.md` passed after whitespace cleanup.
- Final staged-file and traceability checks were run before the atomic commit.

## Commit Info

Atomic commit message: `docs(planning): align Prototype v0 with canonical roadmap`. The exact SHA is reported from Git after commit creation because a commit cannot embed its own SHA.
