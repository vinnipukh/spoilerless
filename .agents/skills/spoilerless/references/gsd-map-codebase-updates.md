# gsd-map-codebase UPDATE-mode runs on this repo

Validated 2026-08-14 (full 7-doc update run, 4 mapper agents, all completed).

## When maps already exist: user prefers UPDATE, not full refresh

`.planning/codebase/` already existed (mapped 2026-08-12). Offered
Refresh/Update/Skip per map-codebase workflow; user chose:
**"remap changed areas, supplement old documentation to ensure all is covered."**
→ UPDATE mode = read existing docs first, preserve accurate content, supplement
drift. Offer the three options, but recommend Update when drift is moderate.

## Drift anchor

- `last_mapped_commit` in any doc's YAML frontmatter (e.g. `STACK.md`) is the
  diff anchor: `git diff --stat <sha>..HEAD` + `git status --short`.
- Even 2 days after a map the drift was 253 files / 23,783 insertions (phase-10
  test suite, visualization subsystem, docs) — always check, don't assume "recent
  map = no drift".
- Uncommitted working-tree work counts as drift: new untracked modules
  (`cytoscapeReconciler.ts` + test), modified components, root verify scripts.

## Windows git-bash runtime quirks (hit this session)

- `node "$HOME/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"` FAILS:
  MSYS mangles to `C:\c\Users\...` → `MODULE_NOT_FOUND`.
  Fix: export `GT="C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"`
  (Windows-style forward-slash path) and `node "$GT" ...`.
- Same for role prompts: `C:/Users/arhan/AppData/Local/hermes/agents/gsd-codebase-mapper.md`
  (agents dir from init JSON `agents_dir`).
- `node "$GT" query init.map-codebase` returns JSON with: `date`, `codebase_dir`,
  `existing_maps`, `mapper_model` (empty → OMIT model param, inherit),
  `subagent_timeout` (300000), `agents_dir`, `commit_docs`.

## Spawn split: max 3 concurrent children

`delegate_task` rejects a 4-task batch (`max_concurrent_children=3`). Split:
- Batch A: tech (STACK.md+INTEGRATIONS.md), arch (ARCHITECTURE.md+STRUCTURE.md),
  quality (CONVENTIONS.md+TESTING.md) — 3 parallel.
- Batch B (after A returns): concerns (CONCERNS.md).

## UPDATE-mode mapper prompt recipe (worked well)

Every agent prompt must include:
1. Explicit **"UPDATE run, NOT a rewrite — read the EXISTING docs first, preserve
   accurate content and structure, SUPPLEMENT with drift"** — without this,
   mappers can rewrite from scratch.
2. Mandatory initial read of the mapper role file path (templates live there).
3. `Today's date: <date>` from init + "set ALL date stamps (Analysis Date,
   footer, `<!-- refreshed -->`) to <date>" (Update runs seed from concrete
   prior dates — replacing `[YYYY-MM-DD]` placeholders is not enough).
4. Per-focus drift checklist:
   - tech: `git diff <anchor>..HEAD -- spoilerless/pyproject.toml frontend/package.json`; check untracked modules' imports; root scripts (stdlib?); note `.hermes/` (Hermes desktop-attachment notes — not a repo artifact).
   - arch: new untracked modules + `git diff <anchor>..HEAD -- frontend/`; new routers/services (`ls spoilerless/app/api/`).
   - quality: new test families + canonical runner `scripts/run_phase10_backend_tests.py`; PROBLEMS.md conventions (PASS ledger, PHASE10-COVERAGE marker).
   - concerns: PROBLEMS.md latest passes; uncommitted-state flag; largest files (`wc -l`); TODO/FIXME; operational (Render health, spoilerless-neo4j docker vs AuraDB, :AppSetting LLM key).
5. "Do NOT commit. Do NOT modify the other docs. Return confirmation only (no contents)."

Mappers finished in ~3.5–4.5 min each (13–17 api_calls, ~285s for batch A).
Worth reusing: mappers stamped frontmatter + added per-doc "Map Delta" sections —
keeps future diffing easy.

## Post-run sequence

1. `wc -l .planning/codebase/*.md` — all 7 exist, none empty (>20 lines).
2. Secret scan (sk-/ghp_/AKIA/PRIVATE KEY/eyJ patterns) before commit.
3. Commit: `node "$GT" query commit "docs: map existing codebase" --files .planning/codebase/*.md`
   (only codebase docs — repo has unrelated dirty files; commit_docs=true).
