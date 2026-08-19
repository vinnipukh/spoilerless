# CONTRIBUTING.md verification snapshot (2026-08-10)

Use this when auditing contributor/setup/quality-gate documentation against the live Spoilerless repository.

## Verified bounded commands

- `pytest spoilerless/tests/test_graph_api.py -k 'graph_error_shapes' -q` passed: 1 passed, 34 deselected.
- `NODE_ENV=test npm run test -- --run` passed: 40 files, 330 tests.
- `npm run build` passed (`tsc -b && vite build`).
- `npm run lint` exited 0.

## Stale backend contract gate

The exact documented command `pytest spoilerless/tests/test_openapi_contract.py -q` is currently red: 2 failed, 7 passed.

1. `test_user_route_openapi_has_exact_operations_and_templates` still locks 32 templates and omits the five current path/export/share templates:
   - `/api/series/{series_id}/graph/path`
   - `/api/series/{series_id}/export`
   - `/api/share`
   - `/api/share/{token}`
   - `/api/share/{token}/graph`
2. `test_all_story_reads_graph_errors_health_and_deletes_are_fully_typed` assumes every DELETE operation returns 204; the live share-token DELETE operation does not have a 204 response.

`spoilerless/tests/test_frontend_contract_doc.py` is the newer inventory authority in this area and locks 50 operations / 37 templates, including those five templates. A contributor guide that presents `test_openapi_contract.py` as a focused green gate is stale until the older test is synchronized.

## Candidate-read wording

Do not describe candidate-review reads as an exception to spoiler filtering. `spoilerless/app/api/candidates.py` requires `visible_until_order` for list and detail, resolves it against a persisted episode, and passes it into repository visibility filtering. Its docstrings explicitly describe fail-closed behavior.

## Verification-artifact discipline

For a JSON-only verification assignment:

1. Write only the requested artifact; do not edit the audited document.
2. Keep distinct failures distinct (for example, a stale synchronization/process claim versus the exact documented command being red), but state their shared root cause clearly.
3. Validate exact top-level and failure key sets, positive checked count, `passed + failed = checked`, and `len(failures) = failed`.
4. If fresh canonical evidence is required, run a single temporary pytest test that validates only the final JSON artifact, then delete it. Do not substitute a database-mutating application suite.
