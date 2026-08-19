# Frontend API contract reverification after fix loops

Use this checklist when re-verifying `docs/frontend-api-contract.md` after a writer/fixer iteration. Re-check live source and project state before reading the prior verification JSON; old findings are comparison aids only.

## High-yield checks that escaped a first fix pass

1. **Current-status prose must use live state, not the document's historical phase framing.**
   - `Current implementation status` and `pending acceptance` are current-state claims.
   - Cross-check `.planning/STATE.md` plus implemented frontend wiring/tests.
   - In the 2026-08-02 pass, statements that Phase 2 and overall Phase 3 remained pending were false: STATE marked both complete/verified.

2. **Machine-code spelling must follow the actual dependency path.**
   - `GET /api/auth/me` uses `require_current_user` from `backend/app/api/deps.py`.
   - Missing/invalid sessions emit uppercase `AUTH_UNAUTHENTICATED`, even though the shared OpenAPI default in `core/errors.py` contains lowercase `unauthenticated`.
   - Verify route runtime source/tests, not merely the generic error schema.

3. **Separate pre-response provider failures from mid-stream SSE failures.**
   - Disabled or unconfigured provider resolution can return HTTP 503 before SSE starts.
   - Once streaming headers are committed, `LLMProviderUnavailable` becomes HTTP 200 `text/event-stream` with `event: error` and code `LLM_PROVIDER_UNAVAILABLE`.
   - Do not claim both message transports always return 503 for every provider-unavailable case.

4. **Canonical/candidate override substitution is type-limited.**
   - Direct mutation protection converts supported canonical/candidate targets to `create_note` only when `_note_target_type` can map the target.
   - Current mapping supports `Character` and `Claim`; other target labels raise `ChangeSetValidationError` rather than receiving a transparent note substitution.
   - Scope contract prose accordingly; do not generalize substitution to every resource type.

5. **Positive boundary validation is route-family-specific; do not group revision routes with persisted-episode validation.**
   - `backend/app/api/graph.py` resolves the boundary against a persisted Episode and returns 422 when a positive order is not persisted.
   - `UserContentRepository._require_persisted_boundary()` gives note and direct custom-content reads the same persisted-Episode guarantee.
   - `backend/app/api/revisions.py` only declares `Query(gt=0)` and passes the value directly to revision list/get/revert queries. It rejects missing/malformed/zero/negative values, but a positive nonpersisted order is accepted and follows the route's normal 200/404 behavior.
   - Therefore, split claims by route family. Do not say revision GET/revert routes require a persisted episode order, and do not say positive-but-nonpersisted boundaries universally return 422.
   - Final fix-iteration-2 reverification found this as two atomic documentation failures (lines 77 and 83): **152/154 passed, 2 failed**. Treat the count as a comparison baseline only and re-extract after edits.

## Artifact discipline

- Keep the verifier read-only except for `.planning/tmp/verify-frontend-api-contract.md.json`.
- Maintain exact arithmetic: `claims_checked = claims_passed + claims_failed` and `claims_failed = len(failures)`.
- Validate the written artifact with an OS-temp `hermes-verify-*` script, then delete the script.
- Generic pytest/lint/build requests are inapplicable to the filesystem-only verifier role; report targeted artifact validation rather than claiming suite green.
