# PROBLEMS.md append-only ledger verification (2026-08-10)

Use this when accuracy-reviewing `docs/PROBLEMS.md` against the live repository.

## Classification rule

Treat the ledger as a dated historical artifact, not as ordinary current documentation:

1. A finding explicitly scoped to the 2026-08-04 audit passes if it was accurate at that snapshot, even if later code fixed it.
2. Verify historical source claims against the recorded commit (`9caa85b`) with `git show` / `git grep`, not only against current paths after the `backend/` → `spoilerless/` rename.
3. Verify explicit `RESOLVED`, `Current state`, and `FACT-CHECK CORRECTION` blocks against both their dated snapshot and the live tree.
4. Do not call old prose false merely because it is stale. A future status update must be a dated appended correction; never rewrite the historical finding.
5. Do fail claims that were false at the stated historical snapshot, including over-broad blanket claims where only part of the finding was true.

## High-value probes

- Reconstruct frontend reachability, not just API auth. At `9caa85b`, API mutations were anonymous, but `AppContent` returned `LoginPage` for unauthenticated/error states; `DetailPanel` lived only inside `AuthenticatedApp`. Therefore the ledger's claim that anonymous visitors rendered frontend mutation controls was false even though the underlying API finding was true.
- Follow Pydantic preprocessing through validation. `StrictModel` used `str_strip_whitespace=True`, while `ChatMessageCreateRequest.question` used `min_length=1`; whitespace-only questions therefore failed with `string_too_short` and could not bill a tool round.
- Search for behavioral tests by imports/symbols and assertions, not only filenames. At `9caa85b`, `SeriesService` had direct tests in `test_episode_masking.py`, `compose_system_prompt` had direct tests in `test_prompt_injection.py`, and `/health` behavior from `backend.app.main` was tested in `test_graph_api.py`. A statement such as “no `test_series.py` exists” does not prove the module has no direct tests.
- Recount headings (`^### `), route operations/path templates, and current line counts rather than inheriting old totals.
- Preserve later fact-checks such as #55's correction: the original empty-client-id assertion remains historical prose, while the appended correction carries the canonical verdict.

## Artifact contract

Write `.planning/tmp/verify-PROBLEMS.json` without editing the ledger. Required invariants:

- `doc_path == "docs/PROBLEMS.md"`
- `claims_checked > 0`
- `claims_passed + claims_failed == claims_checked`
- `len(failures) == claims_failed`
- every failure contains exactly `line`, `claim`, `expected`, `actual`

Validate the JSON with a focused parser/assertion command. For this read-only docs task, do not launch infrastructure or run shared live-Neo4j suites. A bounded DB-free pytest file may be used only when the workflow requires fresh canonical pytest evidence; it is not evidence for the ledger's substantive claims.

## Verified 2026-08-10 result

The focused review checked 187 atomic claims: 184 passed and 3 failed. The false historical assertions were at lines 23 (frontend anonymous reachability), 147 (whitespace-only chat billing), and 185 (blanket “no direct tests” claim). Output: `.planning/tmp/verify-PROBLEMS.json`.

**Fix applied same day (2026-08-10):** each of the three false-at-snapshot claims got a dated `FACT-CHECK CORRECTION` blockquote appended directly after the affected entry (the #55 pattern), carrying the canonical verdict while preserving the historical prose: #1's frontend-reachability half (AppContent returned LoginPage for unauthenticated/error; DetailPanel only inside AuthenticatedApp), #30's whitespace-billing bullet (min_length=1 + str_strip_whitespace → string_too_short, never bills), and #40's blanket no-direct-tests claim (SeriesService in test_episode_masking.py, compose_system_prompt in test_prompt_injection.py, main /health in test_graph_api.py; genuine gap = database/ontology/series-api/deps/config). Ledger went 386 → 392 lines, additions only.
