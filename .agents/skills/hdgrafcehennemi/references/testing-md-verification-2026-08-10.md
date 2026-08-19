# TESTING.md re-verification (2026-08-10) — 72/72/0 after surgical fix

Baseline artifact (`.planning/tmp/verify-TESTING.json`): 50 checked / 2 failed.
Fix batch surgically changed `docs/TESTING.md`; re-verify of the CURRENT revision
= 72 checked / 72 passed / 0 failed. All evidence DB-free (no live-Neo4j suite run).

## The two baseline failures and their fixed form

1. **Line 67-68 (bounded DB-free example):** now `uv run pytest spoilerless/tests/test_user_content_models.py`.
   VERIFIED: `unset PYTHONPATH; export PATH="$PWD/.venv/Scripts:$PATH"; pytest spoilerless/tests/test_user_content_models.py -q`
   → 23 passed in ~0.2s (twice: pre- and post-artifact-write). This is the doc's canonical green gate.
2. **Line 133 (contract-gate claim):** now reads: `test_frontend_contract_doc.py` locks the live
   50-operation, 37-template inventory; `test_openapi_contract.py` "is an intended companion gate but is
   currently stale and red: it still expects 32 templates, omits the graph-path, export, and share templates,
   and assumes every DELETE response is 204 even though share-token revocation returns 200. Do not treat that
   file as a passing bounded gate until those assertions are updated."
   All sub-claims VERIFIED against live code:
   - `test_frontend_contract_doc.py:105-106`: `len(documented) == len(generated) == 50`,
     `len(EXPECTED_TEMPLATES) == 37` — the locking gate, green.
   - `test_openapi_contract.py:202`: `assert len(schema["paths"]) == 32` (stale); `expected_paths` set omits
     `/api/series/{series_id}/graph/path`, `/api/series/{series_id}/export`, `/api/share`,
     `/api/share/{token}`, `/api/share/{token}/graph`; DELETE-204 assumptions at lines 221/250/302-304.
   - Live app via in-process `app.openapi()`: 37 templates, 50 operations; share paths present;
     `DELETE /api/share/{token}` responses = 200/401/403/404/422/503 (200, NOT 204).
   - Full-file run: **2 failed / 7 passed** — failures are exactly
     `test_user_route_openapi_has_exact_operations_and_templates` and
     `test_all_story_reads_graph_errors_health_and_deletes_are_fully_typed` (the two tests the doc names).
   - Line-80 `-k` example `test_validation_error_uses_stable_sanitized_envelope`: 1 passed, 8 deselected (works).

## Method notes (durable)

- **Two-sided gate for docs that document a red file:** the doc's MUST-PASS examples are the canonical green
  evidence; the documented-red file run is a CONFIRMATION whose expected failures = the failures the doc
  names. Explain this in the summary so the parent doesn't misread 2 failed as a verification failure.
- Re-run the green gate AFTER writing the JSON artifact — the last pytest log often shows the documented red
  state and trips the stale-evidence check; the post-edit green run is what the parent records.
- Static checks: substring checks for pyproject bare specs (`"pytest>=9.1.1"` in `[dependency-groups]`);
  resolve scratch-series IDs via conftest constants (`CANDIDATE_SCRATCH_SERIES`, `REVIEW_SCRATCH_SERIES`)
  plus test-file imports, never literal grep in the test files.
- Do NOT "repair" `test_openapi_contract.py` (32→37, DELETE-204→share-200) without also rewriting
  TESTING.md line 133 — the doc's stale/red statement is intentional until that pair ships together.
- Artifact invariants held: `claims_checked=72`, `passed+failed=checked`, `len(failures)==failed` (0),
  empty `failures` array is valid JSON.
