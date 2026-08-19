# 08-14 docs-update facts — corrections to dated claims + run lessons

Verified 2026-08-14 during the full gsd-docs-update run (all 9 canonical docs
updated + 25-doc verification + fix loop). Supersedes these claims from
`08-12-doc-update-facts.md` where they conflict.

## API surface: 52 ops / 39 path templates — and test_openapi_contract.py is GREEN
- `spoilerless/tests/test_frontend_contract_doc.py` asserts **52 operations /
  39 path templates** (was 50/37 on 08-12).
- **`test_openapi_contract.py` is NO LONGER STALE**: Phase 10 10-03/10-06
  inventory updates replaced its 32-path snapshot — it now pins
  `len(schema["paths"]) == 39`, types every DELETE (204 no-content or
  200-with-body), and is a green member of the zero-failure baseline.
  Anything claiming it's a known-stale test is itself stale.
- Docs describing the inventory: docs/API.md + docs/reference/frontend-api-contract.md.

## PROBLEMS.md passes
- NINETEENTH PASS (2026-08-13) is the newest as of 08-14; next docs-update
  ledger append = TWENTIETH PASS. Do not claim a newer pass.

## Guarded runner: refuses while ANY shared container runs
- T10-LEAK-09 refusal also fires when the dev shared container
  `spoilerless-neo4j` is live. Sequence: `docker stop spoilerless-neo4j` →
  `.venv/Scripts/python.exe scripts/run_phase10_backend_tests.py` (system
  `python` lacks neo4j; `unset PYTHONPATH` helps) → `docker start
  spoilerless-neo4j` (volume-persisted, safe). Runner: ~11 chunks ≈ 2 min.

## .planning/phases/ emptied by the v1.3 archive
- Commit e62e664 "chore: archive v1.3 milestone" (2026-08-14) removed
  `.planning/phases/`; artifacts survive at `.planning/milestones/v1.3-phases/`.
  Old docs citing `.planning/phases/10-polish-finishing-touches/10-0X-*.md`
  have dead links — fix with one archival note, never rewrite the traceability
  table (dated historical record).

## Ledger/verifier conventions re-confirmed
- PROBLEMS.md + decision logs are chronological ledgers: historical entries
  stay as audit trail under RESOLVED/FIXED banners; only live inaccuracies
  get fixed (e.g. #8 banner line-pin, #60 FIXED overclaim on revision-revert
  `invalidate_series` — revert path still omits it; candidates.py 3×,
  change_set.py 2×, user_content.py 3× call it).
- Fix agents MUST verify live before editing: the threat-model fixer
  disproved a verifier false-negative — `test_retrieval_tools.py` has 40
  tests (incl. `test_get_evidence_visible_only`, `test_get_sources_visible_only`,
  `test_find_path_*`), `test_citations.py` has 8; the 08-13 verifier's "4
  tests / 1 test" claims were wrong.

## hermes verify on this repo
- Detected recipe = `test: ["pytest"]` + wrong start (`uvicorn main:app`) —
  running it is the prohibited unguarded path (T10-LEAK-09). Safe phase:
  `hermes verify --phase bootstrap --json` (uv sync only). Saving a corrected
  recipe to `.hermes/environment.json` needs explicit user approval.

## render.yaml vs dashboard
- render.yaml service name = `spoilerless-api` (renamed from
  `hdgrafcehennemi-api`, commit a0aa33a). Live probe stays
  spoilerless.onrender.com/health; dashboard service name may differ — VERIFY
  marker territory.
