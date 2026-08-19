# Frontend API contract verification — 2026-08-10

Use when accuracy-reviewing `docs/frontend-api-contract.md` against the live FastAPI/OpenAPI and frontend API/type modules.

## Verified inventory and artifact

- Live `spoilerless.app.main:app.openapi()` has **50 operations over 37 path templates**.
- Verification artifact shape: `doc_path`, positive `claims_checked`, `claims_passed`, `claims_failed`, and `failures`; require `passed + failed == checked`, `len(failures) == failed`, and each failure to contain exactly `line`, `claim`, `expected`, `actual`.
- Session result: 151 claims checked, 129 passed, 22 failed. Artifact: `.planning/tmp/verify-frontend-api-contract.json`.

## High-value drift classes found

1. **Candidate reads are now fail-closed.** Candidate list and direct GET both require `visible_until_order`, resolve it to a persisted Episode, and return 422 when omitted/non-persisted. Hidden direct candidate reads return 404 `CANDIDATE_NOT_FOUND`. Any text saying list filtering is optional or direct GET has no boundary is stale.
2. **Anonymous graph requests clamp to order 1.** `get_graph` ignores the caller's requested order for anonymous users before persisted-boundary resolution. Do not claim every positive non-persisted requested graph order necessarily returns 422.
3. **Cookie/auth drift.** `session_cookie_secure` defaults to `True`; local HTTP must opt out. SameSite defaults to `lax` but is configurable. Both Google login and logout use `verify_origin`; logout can therefore 403 before its nominal 204. Admin/user roles are implemented, with `ADMIN_EMAILS` assignment and admin gates on candidate review, ChangeSet confirm, and LLM settings.
4. **Backend/frontend response-type drift.** Backend-required fields missing from the handoff examples and/or frontend types:
   - `GraphResponse.effective_view_order`
   - `UserPublic.role`
   - user-content response `user_id` fields
   - progress `watched_through_order`, `view_as_of_order`, `effective_view_order`
   - chat-message `status`
   - ChangeSet `revert_revision_id`
   - revision `user_id` (frontend type omission; the contract doc currently has no full revision schema section)
   Frontend `CustomNodeResponse` also still declares `node_type` while backend returns `type`; `GraphEvidence.content_hash` is nullable backend-side but non-nullable in the frontend type.
5. **ChangeSet revert has two revision links.** `revision_id` remains the apply-time Revision; `revert_revision_id` stores the later revert Revision. Examples that overwrite `revision_id` on revert are stale. ChangeSet confirm is admin-only.
6. **Client-supplied series-id exception.** A blanket statement that clients never submit `series_id` is too broad: `ChangeSetCreateRequest` requires it and the route verifies it equals the path series id. Scope that ownership statement to direct user-content DTOs or document the exception.

## Verification method

1. Read the doc with line numbers; treat each operation row, count, concrete field, status, auth/boundary rule, and example as a separate claim.
2. Import the app with the project venv (`unset PYTHONPATH`; put `.venv/Scripts` first) and compare exact `(method, path)` sets plus 50/37 counts.
3. Inspect backend route dependencies and Pydantic domain models, not OpenAPI counts alone. FastAPI's OpenAPI does not encode every auth dependency as a security scheme.
4. Compare frontend `src/api/*.ts`, `src/types/*.ts`, hooks, and tests field-for-field against backend models and route semantics.
5. Validate the JSON artifact programmatically after writing it.
6. In fix mode, edit only `docs/frontend-api-contract.md`: preserve the `generated-by: gsd-doc-writer` marker and surrounding structure, leave the verification JSON untouched, then compare the documented operation table to the live OpenAPI `(method, path)` set for exact equality. Also assert that each reported stale phrase is absent and each corrected contract phrase is present; counts alone can miss a swapped or omitted route.
7. Put the focused post-fix verifier under the Windows OS temp directory and delete it after execution. Because executing an absolute temp-script path makes that temp directory `sys.path[0]`, explicitly insert the repository root before `from spoilerless.app.main import app`; merely running the command with the repository as shell `workdir` is not sufficient for this import shape. Run with the project venv and `PYTHONPATH` unset. Finish with `git diff --check`, a pre/post line count, and a scoped status check proving the verification artifact was not modified.
8. `spoilerless/tests/test_openapi_contract.py` currently has two known stale assertions: its exact path set omits share/path/export, and it assumes every DELETE returns 204 although share revoke returns 200. A focused run excluding those two stale tests yielded 7 passing tests. Do not present the full file as green; keep the exclusion explicit and treat the stale tests as findings, not as evidence against the live OpenAPI inventory.
