# HD Graf — gsd-progress / GSD query runbook

SKILL.md is at the 100KB cap (2026-08) — these notes live here instead.

## Repo root / workdir (user expectation)

- Repo: `C:\Users\arhan\PycharmProjects\hdgrafcehennemi`
- cd there FIRST for any GSD work. gsd-tools.cjs resolves the project via cwd /
  `git rev-parse --show-toplevel`; running queries from `$HOME` silently targets
  the wrong/absent project (`.planning/` in home is just `config.json`, not a project).
- User corrected this in-session (2026-08-13): "Cd into pycharmprojects/hdgrafcehennemi".

## gsd-tools query quirks hit during gsd-progress

1. `query summary-extract <SUMMARY.md> --fields one_liner` returns `"one_liner": null`
   for HD Graf summaries — they open with `# {id} Summary: <title>` + `## Overview`,
   no one_liner frontmatter field. Fallback for the progress report's "Recent Work":
   `head -12 <SUMMARY.md>` (Overview paragraph is the one-liner).
2. node -e temp-file parsing: `readFileSync('/tmp/x.json')` resolves to `C:\tmp\x.json`
   → ENOENT. Write JSON under `.planning/tmp/` instead (repo-relative, git-ignored).
3. gsd-tools.cjs invocation from git-bash: never pass `$HOME/...` MSYS path to node
   (`C:\c\Users\...` MODULE_NOT_FOUND). Use `node "C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"`.
   Full treatment: `windows-gsd-setup` skill.

## Typical progress route for v1.3 milestone (reference)

Phase 09 (18 plans, 18 summaries, verification missing) → Route V.missing →
`/gsd-execute-phase 09` to regenerate VERIFICATION.md. Phase 10 blocks on it.
