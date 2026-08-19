# GSD execute-phase on Hermes (HD Graf)

Learnings from Phase 10 (polish-finishing-touches, 11 plans / 10 waves serial chain).

## gsd-tools.cjs path quirk (git-bash on Windows)
`GSD_TOOLS="$HOME/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"` then `node "$GSD_TOOLS"` FAILS: MSYS mangles `$HOME` expansion, node resolves `C:\c\Users\...` → `MODULE_NOT_FOUND`.
FIX: hardcode native forward-slash path — `node "C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs" query ...`. Do this in every terminal batch; env-var shims from gsd-core docs assume bash-without-MSYS.

## Useful init queries (phase 10 flow)
- `query init.execute-phase "10"` → phase_dir, plans, incomplete_plans, branching_strategy (was "none" → stay on main), use_worktrees, section_manifest (read ONLY included step files; excluded ones must not be read: partial-wave, gap-closure-artifacts were excluded).
- `query phase-plan-index "10"` → per-plan wave/depends_on/autonomous/has_summary + waves map. Pipe through python -c json parse to avoid dumping 5K chars.
- `query state.begin-phase --phase 10 --name <slug> --plans 11` before dispatching.
- `query phase.mvp-mode "10" --pick active`, `query check auto-mode --pick active` — both false for phase 10.
- `query config-get workflow.use_worktrees` = false → ISOLATION none → ALL plans sequential on main tree even when wave has 2 plans (10-05/10-06 same wave 5 must serialize).

## Hermes delegate_task executor pattern
delegate_task has NO gsd_role/gsd_role_prompt params (Claude-Code-only). Embed the role contract in goal/context instead:
- Instruct executor to read: plan file, `C:/Users/arhan/AppData/Local/hermes/gsd-core/workflows/execute-plan.md`, `templates/summary.md`, `agents/gsd-executor.md`, .planning/PROJECT.md + STATE.md + config.json, phase 10-CONTEXT/RESEARCH/PATTERNS/VALIDATION/UI-SPEC.md, docs/PROBLEMS.md.
- Always include: `unset PYTHONPATH` before pytest (Hermes terminal shadows venv); commit each task atomically; no --no-verify; leave pre-existing dirty/untracked files alone (list them explicitly); SUMMARY → commit → then narrate (write-before-narrate, #2070).
- Sequential mode: executor OWNS STATE.md/ROADMAP.md updates via execute-plan.md git_commit_metadata step; orchestrator does NOT rewrite them after.
- Shared requirement IDs gate (#2388): executors must NOT mark shared IDs complete in REQUIREMENTS.md (phase 10: VIZ-03/VIZ-10 shared across 10-03/10-08) — plan SUMMARYs document the deferral.

## Wave spot-check protocol (after each executor returns)
1. `ls` SUMMARY + key-files.created (first 2) on disk
2. `grep -c "Self-Check: FAILED" SUMMARY` → must be 0
3. `git log --oneline --grep="<plan_id>"` → ≥1 commit
4. Trust commit SHAs from report only after grep confirms.

## Checkpoint heartbeat lines
Emit literal `[checkpoint] phase N wave X/M ...` lines at wave/plan boundaries (stream-idle prevention #2410) — no tool call, plain text.

## blocking-human checkpoint
Plans with `autonomous: false` + `type="checkpoint:human-verify" gate="blocking"` (10-10) STOP the --auto chain — auto-mode carve-out never auto-approves blocking-human. Grep plans for `autonomous: false` BEFORE dispatching chain so you can warn user early.

## Phase 10 shape
Serial dependency chain 10-01→02→03→04→{05,06}→07→08→09→10→11. Wave 1 was tracer/evidence (fixtures + A/B decision log, Variant A selected, projection_version 1.0.0 in docs/decision-logs/phase-10-visualization.md). Executors succeeded with zero live Neo4j/LLM — all verification commands offline-safe (fixture-driven pytest).
