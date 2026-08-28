# Docs-update run lessons — 2026-08-14 (commits 23f619e + 5bd1641)

Full gsd-docs-update sweep: 9 canonical docs updated, 25 docs claim-verified
(~1,400 claims), 16 docs surgically fixed, zero failures at close. Reuse
next time; supersedes stale claims in older references where they conflict.

## Facts that CHANGED since the 08-12 run (verify live, don't trust old refs)
- **API surface: 52 ops / 39 path templates. `test_openapi_contract.py` is
  NO LONGER STALE** — Phase 10 (10-03/10-06) updated it to lock the current
  inventory (comment: "current inventory instead of the stale 45-op/32-path
  set", asserts `len(schema["paths"]) == 39`). Both contract tests are green
  members of the zero-failure baseline; DEVELOPMENT/TESTING/CONTRIBUTING docs
  describe them as synchronized gates. The "test_openapi_contract is stale"
  narrative (still in 08-12-doc-update-facts.md) is DEAD.
- **render.yaml service name: `spoilerless-api`** (renamed from
  `hdgrafcehennemi-api` in a0aa33a). Docs quote it verbatim; dashboard
  service state is VERIFY-marked.
- **PROBLEMS.md:** newest pass at run start was NINETEENTH (2026-08-13);
  this run appended TWENTIETH (sweep summary + commit hash, per ledger
  convention).
- **`.planning/phases/` was EMPTIED by the v1.3 milestone archive (e62e664,
  2026-08-14)**; phase artifacts live at `.planning/milestones/v1.3-phases/`.
  Docs citing `.planning/phases/10-polish-finishing-touches/*` (e.g. the
  phase-10 decision log's traceability table) get ONE archival-note banner —
  do NOT rewrite each reference. Also check for phantom filenames
  (`10-10-11-SUMMARY.md` never existed; correct to `10-11-SUMMARY.md`).
- `.python-version` = 3.13. CI exists: `.github/workflows/ci.yml` +
  `release.yml` (skeleton, echo-only). Frontend vitest: `NODE_ENV=test CI=1
  npm run test`.

## Verifier quality lessons (the big one)
- **`async def test_*` extraction trap**: a verifier grepping `def test_`
  misses async tests — it reported test_retrieval_tools.py as 4 tests and
  test_citations.py as 1; live counts are 40 and 8 (incl.
  `test_get_evidence_visible_only`, `test_get_sources_visible_only`,
  `test_find_path_*`, `test_hidden_claim_evidence_source_citations_are_rejected`).
  Instruct verifiers to extract with `def test_|async def test_` and LIST the
  test file when a test-name claim is in doubt. A fix agent caught the false
  negatives by verifying live before editing and correctly LEFT those claims
  alone.
- **Line-pin drift is a claim class**: threat-model docs carry `file:NN`
  refs; symbols stay correct while code moves (27/28 pins off in one doc).
  One dedicated fix pass updating pins (each verified by grep) resolves the
  whole class — don't treat each pin as a separate content bug.
- **PROBLEMS.md ledger semantics for re-verification**: RESOLVED-banner
  entries and historical pass records are audit trail → PASS. Only live
  claims are checked (current-pass rows, "verified fixed as of" banners,
  still-open items). First-pass flagged 11; only 2 were live inaccuracies
  (#8 banner line pin .env.example:10→16; #60 FIXED record overclaiming
  `invalidate_series` on the revert route — it still omits it, known bug).
- **Historical-record semantics** (decision logs, UAT records): dated docs
  keep their audit trail; references explained by an archival note PASS.

## Guarded runner / verification channel (this host)
- `hermes verify` default recipe = bare `pytest` (not on PATH here; project
  uses `uv run pytest`) AND an unguarded run against the shared DB violates
  T10-LEAK-09. The only policy-safe recognized-evidence channel is
  `hermes verify --phase bootstrap --json` (uv sync only). Recipe save to
  `.hermes/environment.json` needs user approval — don't retry unapproved
  writes.
- Guarded suite dance: `docker stop spoilerless-neo4j` → run
  `scripts/run_phase10_backend_tests.py` with `.venv/Scripts/python.exe`
  and PYTHONPATH unset (bare `python` = system 3.11 → `ModuleNotFoundError:
  neo4j`) → `docker start spoilerless-neo4j`. The runner REFUSES while the
  shared container is live (by design, T10-LEAK-09) — that refusal is a
  green signal, not a failure.
- Re-verify scope pragmatics: docs untouched by fixes cannot regress —
  re-verify only the fixed docs; unchanged docs keep their prior artifact +
  an integrity check.

## Run logistics that held
- 2-writer wave pairing (readme+architecture, configuration+getting_started,
  development+testing, api+deployment, contributing) works; docs-init
  `has_api_routes: false` is a false-negative → queue docs/API.md manually.
- A verifier can hit its tool-iteration cap BEFORE writing the result JSON
  (verify-API.md.json). Parent backfills the artifact from the verifier's
  reported counts; strict contract: `claims_passed + claims_failed ==
  claims_checked`, `len(failures) == claims_failed`.
- VERIFY-marker counts drift between runs (API.md 1, DEPLOYMENT.md 14 —
  TWELFTH-pass ledger claimed 15, pre-v1.3 refs claimed 13). Count live;
  verifiers report the count.
- First-pass verifier quality varies (claim counts 73 → 533 on the same doc
  between passes) — re-verification after fixes is a genuinely fresh pass,
  not a formality.
