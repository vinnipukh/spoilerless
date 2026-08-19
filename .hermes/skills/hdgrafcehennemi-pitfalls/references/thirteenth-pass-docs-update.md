# THIRTEENTH PASS — gsd-docs-update run (2026-08-14)

Full docs-update run over hdgrafcehennemi, following the twelfth-pass recipe
(`references/twelfth-pass-docs-update.md`). Recipe held up; refinements below.

## Review-queue change detection (NEW — verification cost control)
Twelfth-pass said "previous run verified them; leave unless changed" — too vague.
Concrete method used 08-14:
1. Find last docs-update commit: `git log --oneline -3 -- docs/` (12th pass = b30ccc5).
2. `git diff --name-only <commit> HEAD -- 'docs/*' README.md CONTRIBUTING.md`
3. Changed review docs → fresh gsd-doc-verifier runs. Unchanged → reuse existing
   `.planning/tmp/verify-*.json` artifacts; mark manifest status `verified_reuse`.
Outcome 08-14: 16/24 review docs changed (fresh verify), 8 internship-report/* docs
reused (~8 verifier runs saved). Total verification dispatch: 9 canonical + 16 review.

## PROBLEMS.md pass numbering (NEW — never hardcode)
Before appending the post-run ledger section, discover the newest pass:
`grep -n "PASS" docs/PROBLEMS.md | tail -5`. As of 08-14 the ledger tops out at
NINETEENTH PASS (2026-08-13); this run appends TWENTIETH.
Note: ledger pass numbers (runtime/security passes) and docs-update run numbers are
SEPARATE series — reference file names here use the docs-update series (thirteenth).

## Subagent prompt recipe (validated + one addition)
Twelfth-pass recipe (role file first line, doc_assignment + project orientation +
per-doc "recent refactors that MUST be reflected" bullets, omit `model` param when
doc_writer_model empty) confirmed working. Addition: wrap the three mandatory reads
in a `<required_reading>` XML block (the role file mandates reading it first) —
role file + `08-12-doc-update-facts.md` + `doc-claim-verification.md` — instead of
pasting role content inline (~38KB saved per agent × 9 writers + verifiers).
Writers independently verified the stale-claim traps against source (no
`--project spoilerless`, no `backend.app.*`, `SYSTEM_PROMPT_VERSION` absent).

## Workflow mechanics re-confirmed
- `node C:/Users/arhan/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs query init.docs-update`
  → section_manifest; monorepo dispatch excluded on this repo → skip that step.
- docs-init still reports `has_api_routes: false` (JS-biased detector) → queue
  docs/API.md manually, source "codebase-discovered FastAPI package".
- All 9 canonical docs GSD-marked → mode=update, preservation_check never prompts.
- Docs changed substantially since twelfth pass (v1.3 archive, Phase 10 viz,
  Render service rename to 'spoilerless') — writers must re-derive from source.

## Host quirk (re-confirmed)
Complex bash one-liner (for-loop with printf + nested quotes) hardline-blocked by
the command parser ("oversized/unparseable inline command payloads"); recovery
offers a saved script path to run via `bash <path>`. Plain sequential commands
(`wc -l f1 f2 …`, `head -1`) pass fine — keep terminal one-liners simple.

## Verified-current facts (08-14, live greps — corrects older references)
- **`test_openapi_contract.py` is GREEN, NOT stale.** Locks 39 templates
  (`assert len(schema["paths"]) == 39`, line 225; comment line 152: "current
  inventory instead of the stale 45-op/32-path set"). Both contract tests
  (52 ops/39 templates) are green members of the zero-failure baseline. The
  "test_openapi_contract.py is STALE (32 paths)" claim in
  `08-12-doc-update-facts.md` AND `08-15-api-doc-facts.md` is WRONG as of
  08-14 — Phase 10 10-03/10-06 inventory updates fixed it. Never call it stale
  without re-grepping the file.
- Rate limiter is **fully fail-open in BOTH paths** (PROB-23: `RedisBucket
  .init()` and `try_acquire_async()` wrapped, degrade to no-op) — docs saying
  "not fully fail-open" are stale.
- Disabled-provider 503 error code = **`LLM_DISABLED`** (NOT
  `LLM_PROVIDER_DISABLED`).
- `reject_change_set` carries only `CurrentUserDependency`; `confirm_change_set`
  is admin-gated (asymmetric — say so, don't claim both).
- ToolSpecs = 12 (11 read tools incl. `get_user_notes` + `propose_changeset`);
  `$visible_until_order` literal occurrences = 27 (not 39).
- `NODE_LABELS` = 12 (no Season/Scene); `STORY_LABELS` = 8.
- `test_retrieval_tools.py` has 4 tests only — no `claim`/`evidence`/`source`/
  `search`/`count`/`path` in names; threat-model `-k "..."` matrix selectors
  are dead.
- Visitor mode: `DetailPanel.tsx:759-763` hides Notes/History tabs + write
  affordances when `readOnly` (wired to `isVisitor`).
- CONTRIBUTING.md heading is `## Branches, Commits, and the Issue Ledger`
  (slug `branches-commits-and-the-issue-ledger`) — anchor `#branches-and-commits`
  is DEAD.
- `.python-version` = 3.13. CI exists: `.github/workflows/ci.yml` (backend +
  frontend jobs, DB-pollution gate) + `release.yml` (skeleton). DEPLOYMENT.md
  VERIFY markers = 14; API.md = 1.
- `.planning/phases/` EMPTIED by the v1.3 archive commit (e62e664) — any
  traceability reference to `.planning/phases/10-*/...` is a dead path.

## Orchestration mechanics that worked (08-14)
- **Guarded runner invocation**: `.venv/Scripts/python.exe
  scripts/run_phase10_backend_tests.py` with `unset PYTHONPATH` — system
  `python` fails with `ModuleNotFoundError: No module named 'neo4j'` (venv
  shadowed). Runner REFUSES while shared container `spoilerless-neo4j` is live
  (T10-LEAK-09): `docker stop spoilerless-neo4j` → run → `docker start
  spoilerless-neo4j` (volume-persisted). 11 chunks ≈107s.
- `hermes verify` default recipe for this repo = `["pytest"]` + start
  `uvicorn main:app` — unguarded pytest against the shared DB is prohibited
  (T10-LEAK-09, LLM-key wipe history). `hermes verify --phase bootstrap` is
  the safe recognized-evidence path (uv sync only). Saving a corrected recipe
  to `.hermes/environment.json` requires explicit user approval.
- **Verifier tool-cap backfill**: gsd-doc-verifier subagents can exhaust their
  tool-iteration budget AFTER gathering evidence but BEFORE writing
  `.planning/tmp/verify-*.json`. Orchestrator backfills the artifact from the
  reported counts (strict contract: `claims_passed + claims_failed ==
  claims_checked`, `len(failures) == claims_failed`).
- **Ledger classification rule** (PROBLEMS.md, decision logs): verifier flags
  on historical entries are mostly false positives. Entries with a RESOLVED
  banner ("left in place for the audit trail") or dated pass context stay —
  do NOT rewrite history. Only fix LIVE claims: stale line-pins in RESOLVED
  banners (e.g. `.env.example:10` → now line 16) and FIXED records that
  overclaim (e.g. #60 "routes shrink to command build + invalidate_series"
  while the revert route still omits invalidation).
- **Archival banner pattern**: decision-log traceability tables referencing
  archived `.planning/phases/` paths (15+ dead links) → ONE banner note
  ("planning artifacts archived with v1.3, commit e62e664"), never per-row
  rewrites.
- **Verifier prompt recipe**: per-doc "Verification focus" bullets with
  expected values (e.g. "VERIFY marker count: expected 14") produce grounded
  confirmations; verifiers enumerate focus items one by one.
