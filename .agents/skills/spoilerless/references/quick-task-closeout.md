# Quick-task orchestrator closeout (validated 260813-ftl / 260813-gao)

## Planner-side: PLAN.md shape (validated 260813-wyp)
- Frontmatter: on-disk quick plans (260813-gao/ftl) use `quick_id:` + `estimate:` + `must_haves:`; orchestrator briefs may instead demand `phase:`/`plan:` fields — include BOTH (`phase: <quick_id>`, `plan: 01`, plus `quick_id:`) — harmless and satisfies both.
- Body: `<objective>` (purpose + output) → `<context>` (verified, line-numbered facts) → `<tasks>` (each `<task type="auto">` with name/files/action/verify/done) → `<verification>` → `<success_criteria>`. Prescriptive style: exact line refs, exact expected values (e.g. drag-test pixel outcomes), byte-identical prop lists, separate code/test atomic commits with explicit `git add <paths>` (never -A, never .planning).
- When a task brief hint contradicts an accessibility rule (e.g. "w-4 … 44px hit target"), the a11y requirement governs — resolve it explicitly in the plan and flag the deviation.

## `quick-tasks-append` row mangling
`gsd_run query quick-tasks-append --task "<TEXT>"` takes a **description only** — it fills id/date/commit columns itself. Passing a full pipe-delimited row (`"260813-x | desc | date | sha | ./quick/..."`) escapes every pipe into the Description cell (`\|` garbage) and stamps a wrong commit sha. Two safe paths:
1. `--task "description text"` only, then verify the appended row.
2. Skip the helper: patch `.planning/STATE.md` directly — Quick Tasks Completed table row format `| {quick_id} | {description} | {date} | {commit} | [{slug}](./quick/{slug}/) |` (match the `#` column convention of existing rows — the helper writes a bare integer, existing rows use the quick_id), plus update the `Last activity:` line (`date — Completed quick task {id}: {description}`).

## Orchestrator-owned docs commit (after executor returns)
- Executor commits source+test atomically and leaves `{id}-SUMMARY.md` untracked **by design** (quick-mode workflow step 8).
- `git add .planning/quick/{dir}/{id}-PLAN.md {id}-SUMMARY.md .planning/STATE.md` → commit `docs(quick-{id}): {description}`.
- Never `git add -A`: pre-existing dirty files (`.planning/config.json`, `.planning/tmp/*`, root `run_*.py` scratch scripts) must stay local.
- Spot-check executor claims on disk before docs commit: commits exist (`git log --oneline -N`), SUMMARY frontmatter `status: complete`, key-files exist.

## Windows git-bash `/tmp` quirk
`curl -o /tmp/<file>` silently writes NOTHING on this host (MSYS path resolution) — subsequent grep reports "file not found" and you waste a round. Write downloads to project-local `.planning/tmp/` (rm after), or pipe curl output straight into grep.

## AFK chain (user: "do it auto im afk")
planner → executor → disk spot-check → docs commit → push (`git fetch origin -q; git rev-list --count origin/main..HEAD` + secret scan `git diff origin/main..HEAD --name-only | grep -iE '\.env|config\.json'` before push) → prod probe per `references/prod-deploy-verification.md`. One consolidated report at the end; only re-verify the changed paths yourself (executor's full-suite claims can be reported as-is).

## Gating a phase-9-style closeout (tail gates, from execute-phase resume path)
All plans summarized + VERIFICATION.md missing → resume at `aggregate_results` → `code_review_gate` → `regression_gate` → `verify_phase_goal` → `update_roadmap` (`gsd_run query phase.complete {N}` — warnings are stale SUMMARY path refs, cosmetic). Critical review findings get fixed inline with minimal-risk patches + regression tests BEFORE `phase.complete`; update REVIEW.md frontmatter `status: clean` + `resolution:` note afterward.
