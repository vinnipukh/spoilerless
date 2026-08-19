# PROBLEMS.md ledger processing (PROB-N passes)

Used when the user says "work through problems.md one by one" (gsd-quick --auto
style): each ledger finding gets verified → fixed → committed → logged before
moving on. Canonical ledger = `docs/PROBLEMS.md`; append a numbered pass at the
end (never edit older passes' verdicts; add FACT-CHECK CORRECTIONS inline where
a prior claim is wrong).

## Workflow (proven 08-11, TENTH PASS: #58/#59/#75/#76/#80 fixed, 4 commits)

1. **Identify the current pass.** PROBLEMS.md grows append-only; the newest
   section (NINTH PASS at HEAD c2ff7f5 = #58-#81) is the work queue. Findings
   marked `RESOLVED` in earlier passes are audit trail — skip.
2. **Translate stale paths.** Finding headers cite `backend/app/...` — that
   tree was renamed to `spoilerless/app/` (09-01). Live layout:
   `spoilerless/app/**` (code), `spoilerless/tests/**` (pytest), `frontend/src/**`.
3. **Verify against live source, reproduce FIRST.** Instantiating
   `RetrievalPipeline(database=None)` reproduced #58's NameError before the
   one-line import fix. Never fix from the finding text alone — several claims
   are wrong at HEAD (see pitfalls).
4. **Fix + test, atomic commit per finding.** Backend: local docker Neo4j
   (`source scripts/env-local.sh && uv run --project spoilerless pytest <file> -q`;
   container `hdgraf-neo4j`; start Docker Desktop headless via
   terminal(background=true) then `docker start hdgraf-neo4j`). Frontend:
   `NODE_ENV=test CI=1 npx tsc -b` then targeted `npx vitest run <file>`. Never
   run pytest chunks concurrently on shared AuraDB.
5. **Log the pass.** Append numbered pass to PROBLEMS.md (fix + commit SHA +
   verification numbers + finding corrections with evidence), add a row to
   `.planning/STATE.md` "Quick Tasks Completed", commit docs separately.
6. **Given-up items get documented reasons** (size/time), not silence.

## Pitfalls learned the hard way

- **Usage greps MUST include the tests directory.** NINTH PASS #80 called
  `CONTEXT_SECTIONS`, `INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE`, and
  `install_database_error_handlers` dead — all three are LIVE: asserted by
  `spoilerless/tests/test_prompt_injection.py`, `test_retrieval_pipeline.py`,
  `test_citations.py`, and called by `main.py:206` (26 test refs). Grep
  `spoilerless/ frontend/src` together, tests included, before deleting
  anything. Only symbols with exactly 1 hit (the definition) are safe.
- **Substring grep traps.** `getRevision` matched `getRevisions` (11 false
  hits). Use word boundaries: `grep -rn "\bgetRevision\b"`.
- **Pre-existing local-5.x reds are not your regression.** On local docker
  Neo4j: `TestSeedImageCuration` + graph image-field tests (seed data has zero
  character `image_url` values) and 3 doc-contract tests fail on HEAD too —
  documented EIGHTH PASS. Confirm the failure class before chasing it.
- **Adding a hook function breaks App.test.tsx until its mock is updated.**
  `useWatchProgress.switchSeries` (#61) → App tests failed with "Unable to
  find ... Unlock S01E01? / Yes, unlock episode" because App.test.tsx's
  hand-rolled hook mock lacked the new function (TypeError mid-render → modal
  never opens). Symptom looks like a modal bug; it's a stale mock. Fix the
  mock object first, re-run.
- **App.tsx dual series-id state**: graph keys off `watchProgress.seriesId`,
  the series dropdown/dashboard off `selectedSeriesId` (useState). A series
  switch that only sets `selectedSeriesId` leaves the OLD series' graph
  rendered (#61). Fix: navigation-only `switchSeries` in useWatchProgress
  (no confirm modal, boundary→1) called from handleSeriesSelect /
  handleOpenSeries.
- **Dead-code sweep discipline**: skip tested-but-unused API exports
  (`proposeChangeSet`/`revertChangeSet`/non-streaming `sendMessage`) — their
  api tests are the wire-contract coverage; deleting removes tested behavior
  from a "zero-risk" sweep. Document the skip in the ledger.
