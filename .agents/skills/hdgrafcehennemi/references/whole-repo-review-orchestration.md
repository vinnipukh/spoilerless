# Whole-Repo Thermo-Nuclear Review — Orchestration Recipe

Used 2026-08-11 (NINTH PASS, PROBLEMS.md #58-#81). Read-only review of the
whole repo (~150 files, 54k LOC) in one session.

## Fan-out shape (3 parallel leaf subagents)

Split by layer, not by file size — each subagent gets a self-contained brief
with its OWN review standard embedded (subagents know nothing of the session):

1. **App layer**: `spoilerless/app/api/`, `services/`, `core/`, `main.py`, `domain/`
2. **Retrieval/LLM/repo/graph/cache/spoiler**: `retrieval/`, `llm/`, `repository/`, `graph/`, `cache/`, `spoiler/`
3. **Frontend**: `frontend/src` — App.tsx, components/, hooks/, api/, providers/, lib/, types/

Each brief must include:
- Repo root path (both `C:\...` and `/c/...` forms)
- What to EXCLUDE (tests — never review tests in a code-quality pass)
- The review standard (1k-line rule, spaghetti flags, thin-wrapper flags, code-judo ask)
- Output format: `[SEVERITY: BLOCKER|MAJOR|MINOR] file:line — problem — fix`
  + "TOP 5 code-judo moves" section + max ~40 findings
- "Do NOT modify any files — read-only review"
- User-owned constraints (e.g. `llm/system_prompt.py` prose never touched;
  review structure only)

## Verification pass (parent)

Subagent summaries are SELF-REPORTS. Before trusting BLOCKER claims:
- Re-read the cited file lines yourself (read_file)
- Re-grep the claimed imports/usage (`grep -n "X" file` — terminal)
- Re-check claimed cross-file duplication with grep counts
2026-08-11 outcome: 3 BLOCKERs verified real by parent spot-checks (pipeline.py
NameError — missing import; api/graph.py MAX_PATH_HOPS-as-order; dual seriesId
in App.tsx). One subagent claim ("verified by executing the constructor") was
checked by inspecting imports — always re-verify.

## Reading subagent output

Batch-complete messages truncate long summaries ("[SUMMARY TRUNCATED]" + footer
with full path). The FULL summary is saved to:
`C:\Users\arhan\AppData\Local\hermes\cache\delegation\subagent-summary-<n>-<timestamp>.txt`
— read_file that path for the complete findings. Live transcripts:
`.../cache/delegation/live/deleg_<id>/task-<n>.log` (append-only, per-task).
Delegation is NOT a terminal process — `process wait` returns not_found; poll
the log files instead (`tail -1` per task).

## PROBLEMS.md append (canonical ledger)

Memory rule: PROBLEMS.md = canonical ledger, append numbered passes. Pattern:
- Findings numbered sequentially from the last `### N.` (was 57 → started at 58)
- New pass = `## NINTH PASS — <name> (YYYY-MM-DD)` section, appended at file END
- Each finding: `### N. SEVERITY — short title` + evidence w/ file:line + `**Fix:**`
- End with "Survival order for this pass" (numbered priority list)
- Header line states reviewers used, scope, HEAD commit, "No files modified"

**Heredoc pitfall**: `cat >> file << 'EOF'` with content containing backticks
and quotes fails (`unexpected EOF while looking for matching`'). Use write_file
to a temp path (e.g. `.planning/tmp/pass_append.md`) then
`cat tmp >> docs/PROBLEMS.md && rm tmp` — verified working.

## Windows tool quirks (hit this session)

- `search_files`/rg on Windows fails on repo paths: `IO error ... Sistem
  belirtilen yolu bulamıyor (os error 3)` even for absolute paths — MSYS path
  translation issue. Workaround: use terminal `grep`/`find` with workdir set.
- `find ... | xargs wc -l` works from terminal with workdir param; plain `cd`
  does NOT persist across terminal calls on this host — always pass `workdir`.
