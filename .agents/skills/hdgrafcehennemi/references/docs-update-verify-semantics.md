# docs-update verify semantics — ledger/history handling + verifier pitfalls

Lessons from the 2026-08-14 full gsd-docs-update run (13 verification batches,
15 docs fixed, all clean after fix loop). Complements `doc-claim-verification.md`.

## PROBLEMS.md is a numbered-pass LEDGER — verifier semantics
- Entries are dated snapshots. RESOLVED-banner entries and FIXED records keep
  the pre-fix description below as audit trail ("left in place for the audit
  trail"). A naive adversarial verifier flags those historical descriptions
  (e.g. "no LICENSE", "no .github", "no security headers", old API counts,
  god-file line counts) as failures — they are NOT live claims.
- Classification rule: historical snapshot (dated pass section, RESOLVED/FIXED
  record, or explicitly superseded) → SKIP, no fix. Live claim (a RESOLVED
  banner's "verified fixed as of" statement, current-pass rows, "still open"
  items) → must match code.
- Fix loop: dispatch a fix agent with ONLY the live inaccuracies and an
  explicit "leave historical entries untouched" instruction; re-verify with
  LEDGER SEMANTICS in the prompt or the same flags come back.
- Live-inaccuracy classes seen 08-14: RESOLVED-banner line pins go stale
  (#8 pinned `.env.example:10`, moved to line 16); FIXED records can overclaim
  (#60 said "routes shrink to command build + invalidate_series" but the
  revision-revert route still omits `invalidate_series` — a live known bug also
  phrased in DEPLOYMENT.md).

## Decision logs citing archived planning artifacts
- The v1.3 milestone archive (commit e62e664, 2026-08-14) emptied
  `.planning/phases/`; phase artifacts now live under
  `.planning/milestones/v1.3-phases/`. Docs citing
  `.planning/phases/10-polish-finishing-touches/*` get 15+ dead-path failures.
- Fix = ONE surgical archival-note edit near the header (state the archive
  commit + the surviving milestone path). Do NOT rewrite N traceability
  references — dated historical records keep their audit trail.
- Re-verify with HISTORICAL-RECORD semantics: archived-path references PASS
  when the doc carries the note.

## Verifier false-negative pitfall: test-count / test-name claims
- The first-pass spoiler-threat-model verifier claimed
  `test_retrieval_tools.py` "has 4 tests" and named tests "don't exist" — it
  had only read the file head. Live: 40 tests (incl. `test_get_evidence_visible_only`,
  `test_get_sources_visible_only`, `test_find_path_*`); `test_citations.py` has 8.
- Rule: suspiciously low test counts or "test X does not exist" failures →
  `grep -c "def test_\|async def test_" <file>` before accepting. Fix agents
  must re-verify live before editing; this run's threat-model fix agent did,
  and correctly left the valid citations alone (verifier had been wrong).

## Guarded runner dance (T10-LEAK-09)
- `scripts/run_phase10_backend_tests.py` REFUSES while the shared container
  (`spoilerless-neo4j`) is live, and fails its probe when run with system
  python (no `neo4j` module). Sequence: `docker stop spoilerless-neo4j` →
  `unset PYTHONPATH; .venv/Scripts/python.exe scripts/run_phase10_backend_tests.py`
  → `docker start spoilerless-neo4j` (restore regardless of result; volumes
  persist, zero data risk).

## Verification-evidence channels for docs-only sessions
- Plain `pytest` / `hermes verify` (default recipe `test: [pytest]`) is
  PROHIBITED by T10-LEAK-09 — unguarded run against the live shared DB (a
  past unguarded run wiped the LLM key). Do not run it; do not let a
  verification hook pressure you into it. State the blocker.
- Safe recognized channel: `hermes verify --phase bootstrap` (uv sync only).
- `.planning/tmp/*.json` artifacts (work manifest, verify-*.json) are NOT
  pytest targets: validate with `json.load` + count identities
  (`claims_passed + claims_failed == claims_checked`,
  `len(failures) == claims_failed`, exact key set) — that IS their verification.
- 2026-08-14 evidence stack that satisfied the gate: guarded suite 11/11,
  vitest 404/404 (`NODE_ENV=test CI=1 npx vitest run`), bootstrap phase ok,
  38+ verify artifacts contract-valid.

## Verified-current facts (2026-08-14 — re-verify before reuse)
- API surface: 52 operations / 39 path templates
  (`test_frontend_contract_doc.py` asserts `== 52` / `== 39`);
  `test_openapi_contract.py` is GREEN (locks 39, typed ops) — NOT known-stale.
- render.yaml service name: `spoilerless-api` (renamed from
  `hdgrafcehennemi-api` in a0aa33a); the Render dashboard service may display
  differently — dashboard state gets VERIFY markers, never asserted facts.
- Backend suite: 11 named chunks (core, domain-models, series-api, graph,
  change-set, candidates, auth, user-content, chat-llm, contract-ops,
  phase10-viz), ~107s wall on ephemeral container.
