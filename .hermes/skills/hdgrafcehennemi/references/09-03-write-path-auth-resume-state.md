# 09-03 Write-Path Auth & Ownership — Resume State (2026-08-05)

Plan: `.planning/phases/09-feature-expansion-full-audit-remediation/09-03-PLAN.md`
(requirements PROB-01/02/12/25/26/27). Executor died at the tool budget
mid-Task-1 verification. **HEAD is `63665ce` (docs(09): summary for 09-02).
NO 09-03 commits exist. The Task-1 edits below are ALL UNCOMMITTED in the
working tree.**

## Uncommitted Task-1 edits (code complete, verification NOT green yet)

- `spoilerless/app/domain/user_content.py` — `user_id` REQUIRED on
  `NoteResponse`/`CustomNodeResponse`/`CustomRelationshipResponse` (+ examples).
- `spoilerless/app/repository/user_content.py` — new `UserContentForbidden`;
  `user_id` added to `NoteCreateCommand`/`NoteUpdateCommand`(+`is_admin`)/
  `CustomNodeCreateCommand`/`CustomRelationshipCreateCommand`/`CustomUpdateCommand`;
  `user_id: $user_id` stored on every created node/Claim; owner-scope WHERE
  `AND ($is_admin = true OR <resource>.user_id = $user_id)` added to note/node/rel
  UPDATE + DELETE queries; `OWNERSHIP_QUERY` now returns `resource.user_id`;
  new `_raise_on_ownership_conflict(ownership, actor_user_id, is_admin, msg)`
  helper (origin != user → 409; user_id mismatch → 403; else 404); methods take
  `(series_id, user_id, request, *, is_admin=False)`; `_delete_note` REORDERED —
  owner-scoped delete query runs first, DELETED revision logged only after it
  matches (no ghost revisions on failed cross-owner deletes).
- `spoilerless/app/api/user_content.py` — `user: CurrentUserDependency` on all
  9 mutation routes; `UserContentForbidden → http_error(403, "forbidden", ...)`;
  `_actor(user)` helper returning `(user["id"], user.get("role") == "admin")`;
  403 added to each mutation route's `error_responses(...)`.
- `spoilerless/app/api/candidates.py` — `ingest_candidates` gated with
  `user: CurrentUserDependency` (intentionally unused beyond the gate — candidate
  lifecycle stays admin-gated; actor lands on revisions in Task 3). Approve/
  reject/edit `_admin: RequireAdminDependency` gates untouched.
- `spoilerless/app/api/revisions.py` — `revert_revision` gated; command carries
  `user_id` + `is_admin`; UPDATED branch checks live resource `user_id` mismatch →
  403 AFTER the origin-409 check; DELETED branch checks `before_snapshot.get("user_id")`
  (legacy snapshot without user_id = admin-only, fail-closed).
- `spoilerless/app/revisions/__init__.py` — `take_snapshot` keys += `"user_id"`
  (so revert-recreated resources keep ownership).
- Tests: `test_user_content_api.py` — `_create_user_with_session(role) ->
  (google_sub, user_id, raw_token)` + `_delete_test_user` helpers; fixtures
  `user_session`/`admin_session` (yield `{google_sub, user_id, token}`);
  `user_content_client` fixture now creates a user + sets the cookie; new
  `test_anonymous_mutations_are_rejected_with_401` (9 routes on scratch series,
  `live_client.cookies.clear()` first) + `test_user_content_is_owner_bound_and_cross_owner_mutations_rejected`
  (scratch `second_series`: owner creates node+rel+note; user B gets 403
  forbidden on all 6 mutations; admin bypasses; owner still mutates).
  `test_candidate_review.py` — `ingest_session` fixture + `ingested_claim_id`
  depends on it + `test_ingest_anonymous_returns_401`.
  `test_revisions.py` — `TestRevertAuthentication.test_revert_anonymous_returns_401`.
  `test_user_content_repository.py` — call sites updated (2 of 3 — see failure 1).

## 2 diagnosed failures (fast unit run: 37 passed, 2 failed) — fix BEFORE live suites

1. `test_user_content_repository.py::test_unsafe_series_or_ownership_input_rejects_before_query_selection`
   — MISSED call site at ~line 137: `await repository.create_note("series bad label", request)`
   still uses the old 2-arg signature → TypeError, not UserContentValidationError.
   FIX: `await repository.create_note("series bad label", "user:test-owner", request)`.
2. `test_user_content_models.py::test_model_responses_are_graph_compatible_and_use_typed_origin`
   — ValidationError (~line 221): fixture rows lack the now-REQUIRED `user_id`.
   FIX: add `"user_id": "user:test"` to the response-model rows the test validates.

## Next steps

1. Fix the 2 above, then run (env overrides, `unset PYTHONPATH` first):
   `NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=hdgraf-local-password NEO4J_DATABASE=neo4j uv run pytest spoilerless/tests/test_user_content_api.py -x -q`
   + `... test_candidate_review.py -k "ingest" -x -q` + full `test_revisions.py` +
   `test_user_content_repository.py` + `rg -c "CurrentUserDependency" spoilerless/app/api/user_content.py spoilerless/app/api/candidates.py spoilerless/app/api/revisions.py`.
2. Commit Task 1: `feat(09-03): auth-gate all mutation routes + owner-bound user content`.
   Stage EXPLICIT paths only — pre-existing dirty files to never stage:
   `.planning/config.json`, `.planning/ROADMAP.md`, `.planning/tmp/docs-work-manifest.json`,
   `docs/PROBLEMS.md`; untracked `.hermes/`, `docs/FEATURE-IDEAS.md`, `docs/FEATURE-RESEARCH.md`.

## Task 2 (created_by + ONE visibility rule) — design already decided

- New `spoilerless/app/spoiler/visibility.py`: pure `derive_visible_from_order(
  episode_order, current_progress) -> int` = `max(...)` fail-closed, never < 1,
  both absent → 1. Add pure unit tests (new file OK).
- Direct API custom-node/relationship creates: pre-read the episode's order in-tx
  and call the helper; ALSO read the acting user's current progress
  (`min(view_as_of_order, watched_through_order)` — reuse `CURRENT_PROGRESS_QUERY`
  from `graph/change_set.py`) so "create for episode N with progress P reveals at
  max(N, P)" holds. Custom RELATIONSHIP must keep `max(source.vfo, target.vfo,
  derived)` — existing test `test_custom_relationship_visibility_max_cross_series_dangling_and_in_use`
  asserts vfo == 3 (node at s01e03). Notes keep `target.visible_from_order` (no
  episode in payload; outside the #49 fork scope — document in SUMMARY).
- ChangeSet apply path: `_apply_one_operation` create branches bind
  `derive_visible_from_order(episode_order, current_progress)` instead of
  `current_progress` (create_note passes None episode → derive = current_progress).
  `_read_current_progress` in `repository/change_set.py` is the shared progress source.
- Scratch dual-path test: `test_change_set_api.py`'s `_authed(client, ..., progress=N)`
  pattern (POST `/api/series/{SERIES_ID}/progress` `{"visible_until_order": N}`) is
  the mechanism. WARNING: `test_user_content_api.py`'s `second_series` scratch
  series has only ONE episode — progress P=3 fails validation; build a 3-episode
  scratch fixture for the max(N,P) test.
- Grep gate: no inline `visible_from_order.*episode_order` derivation left outside
  `spoiler/visibility.py`.
- Commit: `feat(09-03): created_by attribution + single visibility-derivation rule (PROB-25/26)`.

## Task 3 (real revision ids + actor + dual revert links) — design already decided

- `api/candidates.py` approve/reject/edit: delete the fabricated
  `rev_id = f"revision:{hashlib.sha256(...)}"` (lines ~206/260/319) and return the
  id `RevisionRepository.log_revision` actually persisted; rename `_admin` → `user`
  and pass `user["id"]` into `log_revision` (RequireAdminDependency resolves the
  user dict, so this is safe).
- `revisions/__init__.py` `log_revision`: add `user_id` parameter, persist on the
  Revision node + RETURN it; thread from every call site (candidates, revert,
  `repository/user_content.py` callbacks, ChangeSet apply). `RevisionResponse` may
  gain `user_id` — check `test_revisions.py`/`test_change_set_*.py` assertions.
- PROB-27: rename ChangeSet `revision_id` → `apply_revision_id` + add
  `revert_revision_id` across `graph/change_set.py` (CREATE init, `_CHANGE_SET_FIELDS`,
  MARK_APPLIED writes apply id, MARK_REVERTED writes revert id),
  `domain/change_set.py` `ChangeSetResponse`, and `repository/change_set.py` readers
  (~:317-318 revert read, :479 apply write, :389 revert write). Read-compat:
  `_CHANGE_SET_FIELDS` selects `COALESCE(cs.apply_revision_id, cs.revision_id)` so
  legacy applied ChangeSets stay revertible. Same commit must update tests asserting
  `revision_id`: `test_change_set_api.py:569`, `test_change_set_confirmation.py:290`.
- Commit: `feat(09-03): real persisted revision ids + actor attribution + dual revert links`.

## Task 4

- 09-03-SUMMARY.md at `.planning/phases/09-feature-expansion-full-audit-remediation/`
  (template `$HOME/AppData/Local/hermes/gsd-core/templates/summary.md`; `status: complete`).
- Commit `docs(09): summary for 09-03` staging ONLY SUMMARY.md + STATE.md + ROADMAP.md
  (never `.planning/config.json`); gsd-tools state handlers take FLAGS
  (`state.record-metric --phase 9 --plan 3 --duration ... --tasks 3 --files ...`,
  `state.add-decision --summary "..."`) — see the Phase 9 planning anchors note.
- Return `## EXECUTION COMPLETE` with SHAs + test counts.
