# 08-14 docs-update run lessons (2026-08-14, full gsd-docs-update pass)

Full docs-update run (9 canonical update-mode + 24 review docs verified, 75
failed claims fixed across 15 docs, 2 fix iterations). Reuse next time.

## Verifier semantics that MUST be passed explicitly per doc class
- **PROBLEMS.md (ledger):** numbered-pass entries, RESOLVED banners, and FIXED
  records are HISTORICAL AUDIT TRAIL — only live claims (banner current-state
  statements "verified fixed as of", still-open items, current-pass rows) must
  match code. First-pass verifier flagged 11 "failures"; 9 were historical and
  correctly left untouched. Without the ledger-semantics instruction, verifiers
  re-flag history every pass.
- **Decision logs / dated records:** references to archived planning artifacts
  PASS when the doc carries an archival note. Fix pattern that worked: ONE
  banner edit, not rewriting N references.
- **Plans/specs with gap lists:** "current gap" bullets that are actually
  closed get REMOVED from the gap list (don't insert implemented-status prose
  into a gaps section).

## Verifier false negatives are real — fix agents must re-verify
One verifier claimed `test_retrieval_tools.py` has 4 tests and that
`test_get_evidence_visible_only` / `test_find_path_*` don't exist (it read only
the file head). Live file has 40 tests. The fix agent re-verified in source,
correctly left the doc's valid citations alone. Rule: fix agents ALWAYS verify
each failing claim against live source before editing; leave claims that turn
out correct.

## Fix-completeness: check ALL occurrences of a claim
runbook "11 chunks" fix updated the prose but MISSED the Backend Tests table +
`# all 10 chunks` comment → iteration 2 needed. After fixing a count/name, grep
the doc for every other occurrence of the old value.

## Repo state facts (as of 08-14)
- `.planning/phases/` was EMPTIED by commit e62e664 "chore: archive v1.3
  milestone"; phase artifacts now live at `.planning/milestones/v1.3-phases/`.
  Docs referencing `.planning/phases/10-*/` paths have dead links — fix with an
  archival-note banner (see above).
- render.yaml service name = `spoilerless-api` (renamed from
  `hdgrafcehennemi-api` in a0aa33a); dashboard state may differ → VERIFY
  markers, never asserted facts.
- VERIFY marker counts (verified): DEPLOYMENT.md = 14, CONFIGURATION.md = 5,
  API.md = 1.
- API surface: 52 ops / 39 path templates; BOTH contract tests green
  (test_openapi_contract.py updated in Phase 10 — not stale).

## hermes verify in this repo
Detected recipe test phase = bare `pytest` (not on PATH in Windows bash;
unguarded run would violate T10-LEAK-09 against the shared container).
`hermes verify --phase bootstrap --json` is safe (uv sync). A corrected
`.hermes/environment.json` recipe (test = guarded runner) requires user
approval — ask the user, don't just write it.

## Prompt recipe that worked (writers AND verifiers)
- required_reading: role file (`C:\Users\arhan\AppData\Local\hermes\agents\
  gsd-doc-writer.md` / `gsd-doc-verifier.md`) + `doc-claim-verification.md` +
  per-doc-class reference (ledger semantics for PROBLEMS, historical-record
  semantics for logs, testing-doc-baseline for TESTING).
- doc_assignment with resolved path; agents read existing content from disk
  (no need to inline it).
- 2 agents per wave (user cap); pairs: readme+architecture,
  configuration+getting_started, development+testing, api+deployment,
  contributing — then verifiers 2-parallel over canonical first, review docs
  second (skip docs unchanged since their last verify artifact — reuse it).
- Fix mode: one agent per doc, failures read from `.planning/tmp/verify-*.json`
  by the agent, Edit-only.
- Re-verify after fixes: full re-verify of fixed docs; docs that passed and
  weren't touched don't regress.
