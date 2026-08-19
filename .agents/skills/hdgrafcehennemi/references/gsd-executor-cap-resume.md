# GSD executor tool-cap deaths — resume recipe (phase 10, 2026-08-13)

Pattern observed across every 2-task implementation plan in phase 10: a `delegate_task`
leaf executor dies at its ~50 tool-call cap with zero commits, leaving uncommitted
working-tree changes and a truncated self-report. Seven plans (10-03..10-08) hit this.
The reliable recovery is below.

## Prevent (executor prompt template)

Always embed in executor context:
- "~50 tool-call budget. COMMIT EARLY: finish Task 1, run its verify, commit, then Task 2.
  If approaching the cap, commit verified work and return a precise handoff
  (done/committed, remaining, next commands)."
- Explicit commit-per-task + handoff contract up front.
- "Do NOT commit pre-existing dirty/untracked files" list verbatim (repo always has
  `.planning/config.json`, `.planning/tmp/*`, `.hermes/`, `run_*.py`, `verify_*.py`,
  estimation-calibration.json, 08-LEARNINGS.md — leave alone).

## On cap-death (resume)

1. The async result message contains a TRUNCATED summary. Read the full handoff from the
   saved file: `C:\Users\arhan\AppData\Local\hermes\cache\delegation\subagent-summary-0-<ts>.txt`.
   The "middle omitted" section holds the exact fixes/next commands.
2. `git status --short` + `git diff --stat` to confirm tree matches handoff.
3. PREFER INLINE CLOSE-OUT by the orchestrator over dispatching another executor:
   - A second executor often dies the same way on the remaining work (10-03 needed a
     continuation executor that ALSO died; 10-04/10-05/10-07 Task 2 finished inline in
     fewer calls than a fresh executor's read-in overhead).
   - Inline works when the handoff enumerates the remaining items and known failures.
   - Re-dispatch only when the remaining scope is large AND self-contained; give the
     continuation the handoff file path as its first read and forbid re-reading everything.
4. Never trust "all tests pass" from a dead executor — rerun the plan's exact verify
   commands before committing anything.

## Adjacent gotchas (same session)

- **pytest -k hang**: terms like `boundary`, `variant`, `restore` can select live-DB
  tests in `test_graph_api.py` (per-test reseed ≈ slow, looks hung). Use ONLY the exact
  `-k` strings from the plan's `<verify>` tags, or run whole offline files unfiltered
  (`test_visualization_projection.py`, `test_visualization_baseline.py`,
  `test_visualization_cache.py`, `test_spoiler_policy.py` are all offline).
- **`uv run pytest` has no `--timeout` flag** (unrecognized argument) — pytest-timeout is
  only in the `.venv/Scripts/python.exe` path from the memory suite command. Drop it
  under uv.
- **gsd-tools path on Windows**: pass `C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs`
  to node. MSYS `$HOME/...` expands to `/c/Users/...` and node mangles it to
  `C:\c\Users\...` → MODULE_NOT_FOUND.
- **Verification tracker**: the system's verify-evidence heuristic only credits `pytest`.
  After frontend-only edits, still end the batch with a fast offline `uv run pytest` run
  (e.g. the projection/baseline/cache files) to record fresh passing evidence; npm/vitest
  runs don't clear the stale flag.
- **state.update verb**: `gsd-tools query state.update "stopped_at" ...` rejects unknown
  field names ("Field not found"). Update STATE.md body via sed/patch directly and use
  `query roadmap.update-plan-progress <phase> <plan> complete` for ROADMAP.
- **Shared requirement IDs**: before marking plan-frontmatter IDs complete, run
  `query requirements.ready-ids <plan-path> <ids...> --raw`; only mark-complete when it
  reports all ready (VIZ-03/VIZ-10 were shared across 10-01..10-08 and closed in 10-08).
- **Blocking-human checkpoints** (`checkpoint:human-verify` + `gate="blocking"`, e.g.
  10-10 UAT): never auto-approve even in `--auto` mode — halt and present the rows.
- **Docker Desktop start from git-bash**: `cmd //c start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"`
  can silently fail (no process, no error). Launching the exe directly via
  `terminal(background=true)` works; poll with `docker info` + `tasklist | grep -i docker`
  (WSL distro `docker-desktop` shows Stopped until the backend boots).
- **GraphClaim shape**: `GraphClaim` has NO `episode_id`/`image_url`/`image_source_url`.
  Shared `_node()` helpers must use `getattr(node, "episode_id", None)` and dispatch
  additions by isinstance (GraphNode / GraphClaim / GraphEvidence / GraphSource) —
  claims/sources/evidence mix in one additions dict (expansion + investigation views).
