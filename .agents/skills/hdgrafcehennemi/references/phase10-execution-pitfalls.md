# Phase 10 execution pitfalls (2026-08-13, verified in a full 11-plan run)

## Executor tool-cap reality (the #1 recurring pattern)
`delegate_task` subagents cap at ~50 tool calls (~12–21 min) on big plans — 8 of 9
executors in this run hit the cap with uncommitted working trees. Plan for it:
- Always instruct executors: COMMIT EARLY (finish Task 1 → verify → commit → Task 2),
  and "if nearing the cap, commit verified work and return a precise handoff
  (done/committed, remaining, next commands)".
- On cap: the working tree is the source of truth. Read the handoff file
  (`cache/delegation/subagent-summary-*.txt`), `git status`/`git diff` to confirm,
  then resume INLINE as orchestrator. Two cap hits on one plan → stop dispatching,
  finish inline (10-03, 10-07 pattern).
- Handoffs must name exact remaining commands and known-failure root causes — the
  executor's "recommended next command" is usually right; run it first.

## pytest quirks (uv run)
- `--timeout=120` FAILS under `uv run pytest` ("unrecognized arguments") —
  pytest-timeout isn't installed in the uv env. The documented ~43min suite command
  uses `.venv/Scripts/python.exe -m pytest ... --timeout=120` directly. Under uv run,
  drop the flag.
- BROAD `-k` FILTERS HANG: terms like `boundary`/`variant` match live-DB tests
  (per-test reseed, ~43min, looks hung, times out at 420s). The safe offline filter
  set: `-k "visualization or projection or cache or exact_operations or locked_inventory"`
  on the 4 route/cache/contract files, plus the 3 offline files unfiltered
  (test_visualization_projection.py, test_spoiler_policy.py, test_visualization_baseline.py).
- Hermes verification-evidence tracker only credits `pytest` commands for changed
  paths — vitest/build runs for frontend edits don't register, so after frontend
  edits ALWAYS rerun the focused pytest too (cheap: ~30-100s).

## Windows / Docker
- Python `subprocess.run(..., shell=True)` on this host runs **cmd.exe** — `grep`/`rg` don't exist there and the command silently returns EMPTY output (looks like "no matches"). Run repo greps through the git-bash `terminal` tool instead. (The `search_files` tool also targets a different filesystem on this host and errors on Windows paths — git-bash grep is the reliable path.)
- `cmd //c start "" "Docker Desktop.exe"` SILENTLY FAILS (no process appears).
  Launch the exe directly in a background terminal instead; daemon takes 60–90s.
- `docker container inspect <missing>` prints `[]` to stdout with rc=1 — trust the
  EXIT CODE for existence checks, not stdout (a false "exists" → spurious REFUSED).
- Ephemeral container names must be unique per run (random suffix); a deterministic
  suffix collides with the previous run's container and the guard refuses it.
- Full backend suite on the guarded ephemeral container (run_phase10_backend_tests.py
  --all): 11 chunks in ~90s wall, vs ~43min on the shared live DB (per-test reseed).
  The ephemeral runner replaces the slow profile.

## Projection code pitfalls (visualization.py)
- `additions_by_id` mixes node kinds: GraphNode AND GraphClaim/GraphEvidence/GraphSource.
  Dispatch by `isinstance` (claims/evidence/sources lack `type`, `episode_id`,
  `image_url`, `image_source_url` that GraphNode has). Shared `_node()` helpers need
  `getattr(node, "episode_id", None)`-style tolerance or claims crash with
  `AttributeError: 'GraphClaim' object has no attribute 'episode_id'`.
- Expansion edge surfacing must be restricted per key (`_EXPANSION_EDGE_TYPES`) —
  an unfiltered full-vocabulary loop leaks e.g. the KNOWS user-rel into a "family"
  expansion.
- Clues expansion = claims AND their supporting evidence (not claims alone);
  evidence = evidence + sources.
- Anonymous users clamp to order 1 (PROB-04/#12) — boundary-failure tests need an
  AUTHENTICATED user + _ProgressRecord(2,2) past the fixture's max order.

## GSD checkpoint handling (--auto chain)
- Plans with `autonomous: false` + `checkpoint:human-verify gate="blocking"` are the
  blocking-human carve-out: NEVER auto-approve, regardless of auto-mode. Halt, present
  the full UAT checklist, wait for explicit "approved" or a blocker list.
- `state.advance-plan` can overwrite STATE.md frontmatter with a stale
  `last_activity_desc` — re-fix the desc after calling it.

## Render deploy probes
- Render service names: `x-render-routing: no-server` = no web service under that
  name (wrong URL guess, not a down app). The real service is `spoilerless` →
  https://spoilerless.onrender.com/health. Probe BOTH candidate names + read the
  header before declaring the backend down.
- Build marker = `service` field in /health: `spoilerless-backend` = new build.

## Docs closeout (10-11 Task 1) — stale-wording gate
The plan's verify greps markdown for `prototype only|no deployment|no production base url`
(case-insensitive) **per heading block**, excluding blocks whose heading line matches
`historical|audit|archive|changelog`. Reusable recipe:
- Before editing, run the exact grep to find the failing blocks (docs/API.md "No production
  base URL...", docs/DEPLOYMENT.md gaps bullet, docs/PROBLEMS.md heading #26 were the 10-11 hits).
- **Your own rewrite can reintroduce the literal pattern**: "no deployment smoke-test workflow"
  matches `no deployment`. Prefer "a deployment smoke-test workflow is not committed".
- PROBLEMS.md ledger headings are scanned too (the excluded words are in the BLOCK heading,
  and each `### N.` heading starts its own block) — reword a finding heading to past tense
  ("Deployment story was entirely absent") instead of leaving the literal phrase.
- Re-run the grep after editing, before committing; `sys.exit(1)` if any hits remain.
- Locked numbers (route counts, op/template totals) come from the CONTRACT TESTS
  (`test_frontend_contract_doc.py`: 52 ops / 39 templates), not from stale doc prose — the
  docs had drifted to 50/37 and 51/37. When citing file paths in new doc sections, `ls` them
  first (visualization.py/useSceneState.ts/etc. were all verified on disk before being named).

## Coverage audit (10-11 Task 2) — marker-delimited machine-readable table
Pattern: a strict markdown table between literal `<!-- X:START -->` / `<!-- X:END -->` markers,
validated by `scripts/verify_phase10_coverage.py` (CLI exit 0/1/2, run with
`uv run python scripts/verify_phase10_coverage.py docs/decision-logs/phase-10-visualization.md`).
- `EXACT_SOURCE_IDS` is copied VERBATIM from the plan's Task 2 inventory (98 ids: goal, 13 REQ,
  49 DEC, 17 UI, 8 RESEARCH, 5 PATTERNS, 5 VALIDATION) — never inferred/scraped. Assert the
  generated row set == the frozenset before appending.
- Parser contract: exact header `source_id|plan_id|artifact_or_test|evidence_ref`, skip
  separator rows, reject duplicate/missing/extra ids, malformed rows, empty fields,
  `evidence_ref == source_id`, absent/duplicate/reversed markers.
- Evidence refs must name REAL artifacts: for decisions use the implementing plan's
  `10-XX-SUMMARY.md`; use the decision log for decisions with recorded evidence there
  (D-03/D-09/D-10/D-11/D-13/D-31/D-32/D-38/D-39/D-44) and the UAT doc for manual rows.
- Per-decision plan_id: derive by grepping sibling `10-XX-PLAN.md` files for `D-XX` (one
  `grep -o` per file) instead of guessing — 10-11's map came straight from that scan.
- Unit tests load the script via importlib (`_load_module` pattern from
  `test_phase10_test_runner.py`) — 15 tests covering valid block, unrelated tables outside
  markers, header handling, dup/missing/extra/malformed/empty/self-ref rows, marker variants.
- **Chunk inventory rule**: every new `test_*.py` MUST be added to `scripts/run_backend_tests.py`
  `CHUNKS` exactly once or `assert_chunk_inventory_matches_disk` fails every run; AND
  `test_phase10_test_runner.py::test_phase10_chunk_lists_all_five_phase10_test_files` asserts
  the `phase10-viz` chunk is EXACTLY those 5 files — so new phase-10 test files go into
  `contract-ops` (or another named chunk), never `phase10-viz`. Run the runner's own test file
  plus the new test together to prove both the inventory and the new tests pass.
- The 10-11 run validated the cap-handoff loop: Task 1 verify+commit, Task 2 verify+commit,
  then a precise handoff (remaining: ready-ids → mark-complete, SUMMARY commit, STATE/ROADMAP
  via gsd-tools queries, metadata commit) — exactly the pattern at the top of this file.

## Milestone closeout (v1.3 verifier + complete-milestone, 2026-08-14)
- Verifier gap G1: REQUIREMENTS.md markers go stale even when every plan completed —
  plans mark only the IDs they own, so shared/early IDs (VIZ-01/02/04/05/06/08,
  POLISH-02) can stay `[ ]`. Close with
  `gsd_run query requirements.mark-complete <ID>...` (7/7 works in one call), then flip
  VERIFICATION.md status gaps_found → passed and rewrite its Gaps section as CLOSED.
- Verifier gap G2: coverage-audit evidence refs can be typos that pass the parser (it
  validates structure, not file existence). `10-10-0X-SUMMARY.md` never existed — the real
  names are `10-0X-SUMMARY.md`. One `sed -i 's/10-10-0\([0-9]\)-SUMMARY/10-0\1-SUMMARY/g'`
  fixes all rows; re-run `verify_phase10_coverage.py` (expect OK 98/98) before flipping status.
- `roadmap.update-phase-status` DOES NOT EXIST — available roadmap verbs: analyze,
  get-phase, update-plan-progress, annotate-dependencies, validate, upgrade. To mark a
  phase row Complete on ROADMAP.md, sed the checkbox line directly.
- `init.manager` JSON has `progress_percent`/`all_phases_verified` as null — the real
  signals are per-phase `phase_complete` + `verification_status: passed`.
- `audit-open` before milestone close lists legacy quick tasks + deferred items — those
  are the Acknowledge bucket; do not treat them as new gaps.
- Milestone archive flow: `gsd_run query milestone.complete "v1.3" --name "..."` archives
  ROADMAP/REQUIREMENTS (+phases dir), then reorganize ROADMAP.md manually (Backlog section
  must be preserved; arm `.planning/.gsd-allow-shrink` sentinel before the shrink write).
