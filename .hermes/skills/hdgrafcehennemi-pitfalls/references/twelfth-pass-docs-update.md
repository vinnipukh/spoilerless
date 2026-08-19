# TWELFTH PASS — gsd-docs-update lessons (2026-08-12, commit b30ccc5)

Full docs-update run over the hdgrafcehennemi repo. Facts verified live; reuse next time.

## docs-init false-negative on this repo
- `gsd_tools query docs-init` reports `has_api_routes: false` for the Python FastAPI
  backend (heuristics are JS/package.json-biased). Queue `docs/API.md` MANUALLY as
  codebase-discovered; record `source: "codebase-discovered FastAPI package"` in the
  work manifest.
- Live API surface (post-ELEVENTH): **50 operations / 37 path templates** — re-derive
  from routers + `app.openapi()` (import the app), never trust the old doc.
- `test_openapi_contract` baseline tests still assert the OLDER 45-op contract; they
  stay red by policy (pre-existing class) even after API.md is correct.

## Queue / preservation facts
- All 9 canonical docs (README, ARCHITECTURE, CONFIGURATION, GETTING-STARTED,
  DEVELOPMENT, TESTING, API, DEPLOYMENT, CONTRIBUTING) exist and carry the GSD
  marker → mode = update for all, preservation_check never prompts.
- Docs structure is FLAT (`docs/*.md`); `docs/internship-report/` is not a doc group.
- Review queue = hand-written docs (PROBLEMS.md, ROADMAP.md, RUNBOOK.md,
  PROJECT-SPEC.md, SPOILER-*, FEATURE-*, internship-report/*, frontend-api-contract.md,
  BACKEND_DEPLOY_FIX.md). Previous run verified them; leave unless changed —
  next run: `references/thirteenth-pass-docs-update.md` has the git-diff
  change-detection method (re-verify only changed docs, reuse verify-*.json for
  unchanged) + PROBLEMS.md pass-number discovery before the ledger append.
- `.planning/tmp/docs-work-manifest.json` is TRACKED in git; commit_docs=true commits
  only the 9 canonical files (workflow artifact left uncommitted).

## Operator constraint
- User caps concurrent doc-writer subagents at **2** → 5 sequential waves × 2 agents
  (readme+architecture, configuration+getting_started, development+testing,
  api+deployment, contributing). Never dispatch 3.

## Agent prompt recipe that worked
- First line: read the role file `C:\Users\arhan\AppData\Local\hermes\agents\gsd-doc-writer.md`
  and follow `<update_mode>` + `<template_<type>>`.
- Include `<doc_assignment>` block + project orientation + per-doc "recent refactors
  that MUST be reflected" bullet list (writers verified every one against source).
- Omit `model` param when `doc_writer_model` is empty (inherit).
- Writers catch real stale claims (e.g. `SYSTEM_PROMPT_VERSION`, `--project spoilerless`
  commands, `backend.app.main:app`, compose image `neo4j:2026.06.0-community`).
- Two writers independently re-confirmed the 584 passed / 7 failed baseline empirically.

## Post-run ledger
- Append a TWELFTH PASS section to docs/PROBLEMS.md recording the refresh + commit hash.
