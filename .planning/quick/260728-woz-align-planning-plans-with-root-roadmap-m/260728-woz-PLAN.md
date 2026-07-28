---
mode: quick
task: "Align .planning plans with root ROADMAP.md"
status: pending
created: 2026-07-28
files_to_modify:
  - .planning/PROJECT.md
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/STATE.md
canonical_source: ROADMAP.md
---

# Quick Task Plan: Align `.planning` with Root `ROADMAP.md`

## Objective

Reconcile the GSD planning artifacts with the root `ROADMAP.md`, which is the canonical product vision and Prototype v0 scope. Keep verified brownfield implementation facts, but correct the current planning model that defines v1 as only backend infrastructure/seed work plus the spoiler-aware API and incorrectly defers the usable frontend, user notes/manual editing, revision history, and preparation for future LLM extraction.

This is documentation reconciliation only. Do not edit source code, data, tests, configuration, the root `ROADMAP.md`, or research files.

## Reconciliation Findings to Address

- `.planning/REQUIREMENTS.md` says the initial prototype release is backend-heavy and defers the frontend to v2; this contradicts root Prototype v0 scope and its demo story.
- `.planning/ROADMAP.md` contains only two backend phases while claiming `21 v1 requirements — 100% mapped`; that percentage is true only for the narrowed requirement set, not for canonical Prototype v0 coverage.
- `.planning/STATE.md` presents only those two phases as the project trajectory, so it omits canonical milestones 4–8 and cannot represent completion of the Prototype v0 demo.
- `.planning/PROJECT.md` already lists UI, notes, revisions, and LLM preparation as active, but its requirement groupings and status language must be made consistent with the reconciled requirements and roadmap.
- Root Prototype v0 must cover infrastructure, metadata graph, spoiler-aware graph endpoint, manual Dexter S01E01–03 seed graph with evidence, React/Cytoscape graph UI, progress selector and spoiler confirmation, details/evidence display, user notes/manual graph editing, revision history/revert, and preparation interfaces/workflow for future LLM extraction. Actual automated extraction and LLM chat remain post-v0.
- Existing scaffold/endpoints/files may remain recorded as brownfield facts, but “existing,” “implemented,” “executed,” “verified,” and “complete” must not be conflated. In particular, preserve the seed script’s documented “existing (unexecuted)” qualification and do not infer runtime completion from file presence.

## Task 1: Reconcile project scope and requirements

**Files:** `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`

**Actions:**

1. Treat root `ROADMAP.md` sections 0–2, milestones 1–8, Demo Story, and Evaluation Plan as authoritative for Prototype v0; use `.planning/research/SUMMARY.md` and brownfield facts in `.planning/PROJECT.md` only as supporting detail where they do not narrow or contradict that intent.
2. Update `.planning/PROJECT.md` so its Active/Out-of-Scope language unambiguously includes the complete Prototype v0 experience, not just backend work. Preserve accurate existing-code facts and the distinction between scaffolded, implemented, unexecuted, and verified behavior.
3. Restructure `.planning/REQUIREMENTS.md` so all canonical Prototype v0 capabilities are in the initial release requirement set:
   - local infrastructure and real Neo4j health verification;
   - series/episode metadata graph and endpoints;
   - manual character/claim/source/evidence seed graph;
   - spoiler-gated graph API and boundary tests;
   - React/TypeScript/Cytoscape UI, episode progress selector, spoiler modal, graph/detail/evidence views;
   - UserNote support and manual custom node/relationship editing with visual separation from canonical content;
   - revision logging, history display, correction/rejection handling, and simple revert;
   - extraction JSON contract, candidate-claim layer, review/approve/reject/edit workflow, and source connector interface as **preparation for** future LLM extraction.
4. Keep OpenSubtitles/script/podcast/external-site automation, the operational LLM extraction pipeline, LLM chat, multi-user/auth, and deployment explicitly post-v0. Do not describe candidate-claim preparation as requiring or delivering an LLM.
5. Retain useful architecture/test requirements discovered during brownfield research, but classify them as enabling requirements under the relevant canonical capability rather than allowing them to replace user-facing Prototype v0 scope.
6. Rebuild the traceability table and totals from the revised initial-release requirements; remove the inaccurate implication that mapping the current 21 backend requirements constitutes 100% canonical Prototype v0 coverage.

**Verification:**

- Search the initial-release section and confirm each root milestone 1–8 capability has at least one uniquely identified requirement.
- Confirm `UI-*`, `NOTE-*`, `REV-*`, and LLM-extraction-preparation requirements are not under v2/post-v0.
- Confirm actual LLM extraction and LLM chat remain out of scope/later.
- Cross-check validated claims against the existing qualifications in `.planning/PROJECT.md`; no unexecuted or merely scaffolded item is called runtime-verified or complete.

**Done when:** `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` describe one consistent Prototype v0 matching the root roadmap, with complete and truthful requirement traceability.

## Task 2: Remap the roadmap and project state to the full Prototype v0

**Files:** `.planning/ROADMAP.md`, `.planning/STATE.md`

**Actions:**

1. Replace the two-phase backend-only roadmap with a dependency-aware phase sequence that represents all root milestones 1–8. Phases may combine closely related canonical milestones, but must retain explicit coverage and success criteria for:
   - infrastructure/metadata foundation;
   - spoiler-aware endpoint;
   - evidence-backed manual seed graph;
   - frontend graph exploration and spoiler-progress UX;
   - notes/manual editing;
   - revision history/revert;
   - future-extraction preparation.
2. Keep backend/API work early where dependency ordering warrants it, but ensure the Prototype v0 release endpoint is the complete root demo story rather than “API proven.” The roadmap must remain consistent with its stated vertical-MVP mode or revise the mode wording if its phases are intentionally technical foundations.
3. Map every revised Prototype v0 requirement exactly once to a primary phase, add cross-phase dependencies where needed, and regenerate coverage counts. Include source/evidence, UX, spoiler-safety, and revision acceptance checks from the root Evaluation Plan rather than relying only on backend endpoint checks.
4. Update `.planning/STATE.md` to point to the reconciled current and next phases, list the full pending phase history, and describe the Prototype v0 target accurately. Preserve truthful current status: do not mark planned work complete, and do not erase accurate brownfield capabilities merely because their broader milestone is pending.
5. Update planning-document descriptions and timestamps/status summaries as needed so `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, and `STATE.md` use the same release terminology and phase numbering.

**Verification:**

- Build a checklist from root milestones 1–8 and confirm every item is represented by a requirement and roadmap phase; explicitly verify frontend UI, notes/manual editing, revisions, and extraction preparation are inside Prototype v0.
- Confirm root milestone 9 / LLM chat and automated ingestion/extraction remain later work.
- Confirm every initial-release requirement appears in roadmap traceability and every traceability phase exists in `.planning/STATE.md` phase history.
- Recalculate requirement/phase totals rather than copying the old `21 / 100%` claim.
- Review all four edited planning artifacts for contradictory “v1,” “v2,” “Prototype v0,” “deferred,” and completion-status language.
- Run `git diff --check -- .planning/PROJECT.md .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/STATE.md` and inspect `git diff --` for documentation-only changes.

**Done when:** the four `.planning` artifacts consistently represent the root `ROADMAP.md` Prototype v0 scope, preserve accurate brownfield facts, contain no unsupported completion claims, and provide complete requirement-to-phase-to-state traceability.

## Overall Done Criteria

- Root `ROADMAP.md` remains unchanged and is explicitly treated as canonical.
- Only `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` are changed during execution of this plan.
- Prototype v0 in `.planning` is not reduced to backend API work: it includes the complete graph UI/demo, notes/manual editing, revisions, and future-LLM-extraction preparation.
- LLM chat and actual automated extraction/ingestion remain later scope.
- All scope, phase, traceability, status, and completion statements agree across the planning artifacts and are supported by either canonical intent or accurately qualified brownfield evidence.
