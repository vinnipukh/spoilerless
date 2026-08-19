# Internship report evidence inventory audit (2026-08-10)

Use this when accuracy-reviewing a hand-written evidence inventory such as `docs/internship-report/REPORT_EVIDENCE_EN.md` against the live repository.

## Verified workflow

1. Treat the document as a historical snapshot, not as trusted current evidence. Check Git divergence/HEAD/status, renamed roots, route inventory, file/test counts, seed counts, and commands against the live tree.
2. Check **every exact cited path occurrence**. A symbol may still exist after a rename, but an exact citation such as `backend/app/...` still fails when the live root is `spoilerless/app/...`. Record the current replacement in `actual`.
3. Check semantic claims separately from path claims: symbols/models, architecture behavior, endpoint sets, data-model fields, constants, and line anchors. Approximate line references fail when they no longer identify the claimed code, even if the feature survives elsewhere.
4. Historical test-result claims require fresh evidence when the assignment says “against the live codebase.” Do not preserve old pass/fail totals as current facts. Run bounded, DB-free/currently safe commands where possible; distinguish a command being valid from its claimed result being current.
5. For this repo, clean Python test invocation under Hermes is:
   `unset PYTHONPATH; export PATH="$PWD/.venv/Scripts:$PATH"; pytest <focused-file> -q`
   A focused current run of `spoilerless/tests/test_user_content_models.py` produced 23/23 passing. Do not inflate that into a full-backend-suite result.
6. Frontend checks are independently auditable: run `npm run lint`, `npx tsc -b --noEmit`, `npm run build`, and `npx vitest run`. Preserve exact fresh counts and note flaky/time-out failures honestly.
7. Write only the required JSON artifact; do not edit the reviewed document. Validate:
   - `claims_checked > 0`
   - `claims_passed + claims_failed == claims_checked`
   - `len(failures) == claims_failed`
   - each failure has exactly `line`, `claim`, `expected`, `actual`

## Snapshot findings

- The report evidence file was deeply stale after the `backend/` → `spoilerless/` rename.
- Fresh audit artifact: `.planning/tmp/verify-REPORT_EVIDENCE_EN.json`.
- Result: 211 checked, 123 passed, 88 failed.
- Major drift classes: old Git/phase snapshot, obsolete backend paths, 10→11 route modules, expanded seed corpus, expanded test/doc inventories, obsolete frontend lint/type/build failures, and stale approximate line anchors.

## Pitfalls

- Do not count an absent human screenshot or explicit placeholder as a repository failure by itself.
- Do not run the shared live-Neo4j full suite merely to validate a documentation artifact.
- Keep path existence, symbol survival, and semantic correctness as separate claims; otherwise a rename can be accidentally marked as passing because the symbol was found elsewhere.
- A fresh full frontend Vitest run can expose an isolated timeout while lint/typecheck/build pass; report each gate independently.