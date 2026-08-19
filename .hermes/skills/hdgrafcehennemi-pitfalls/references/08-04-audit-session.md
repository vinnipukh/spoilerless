# 08-04 audit session — verified facts (docs/PROBLEMS.md is the ledger)

All facts verified against live source, the running backend, and a read-only
live-DB audit on 2026-08-04. Items marked UNFIXED were still open at session
end — re-verify before claiming they're resolved.

## Ledger convention

- **`docs/PROBLEMS.md` is the canonical problem ledger (54 numbered items as of 08-04).**
  New audit findings get a numbered pass section (`## FOURTH PASS — ...`), a row
  in the APPENDIX file:method→effect table, and a survival-order bump. Verify
  with `grep -c '^### '` == appendix row count. This is a docs-only deliverable —
  never change code during an audit unless asked.

## POST /progress 422 on every confirm (UNFIXED, root-caused 08-04)

- `frontend/src/api/progress.ts::updateProgress` ALWAYS adds `visible_until_order`
  (line 36); `useWatchProgress.ts::confirmChange` (165-168) then adds
  `watched_through_order` — the BE validator
  `domain/progress.py::ProgressUpdateRequest._exactly_one_boundary_field` (68-83)
  rejects that exact pair ("Provide either ... not both").
- The FE catch commits optimistically (`useWatchProgress.ts:180-192`) → UI shows
  confirmed, backend never persisted, snaps back on reload.
- The VIEW-ONLY path also ships the legacy `visible_until_order` (a watched-confirm
  alias) → view-only clicks actually confirm watched server-side.
- Same class as the 08-01 chat-422: FE tests mock `updateProgress`. Fix direction:
  stop sending `visible_until_order` from the FE.

## `ProductionGoogleVerifier` NameError (UNFIXED, reproduced 08-04)

- `services/auth.py::verify` line 73 `except google.auth.exceptions.TransportError` —
  `from google.oauth2 import id_token` binds ONLY `id_token`, never the parent
  `google` name → the except-clause expression raises
  `NameError: name 'google' is not defined` AT EXCEPTION TIME.
- Except-clause expressions evaluate lazily, only when an exception occurs —
  valid tokens never trigger it, hence intermittent logins (one 200 amid 503s).
- Every verification failure (audience mismatch = backend GOOGLE_CLIENT_ID ≠
  frontend VITE_GOOGLE_CLIENT_ID, expired token, cert fetch) → misleading
  `503 internal_error (NameError)`.
- **GENERAL PYTHON GOTCHA: `from a.b import c` does not bind `a`; an
  `except a.b.E:` clause needs a module-level import of the exception module.**
- Shipped because `ProductionGoogleVerifier` has ZERO behavioral tests
  (`test_auth.py::test_auth_module_imports` only imports it; every other auth
  test injects a fake verifier — the verifier is the untested seam).
- Fix: module-top `from google.auth.exceptions import TransportError` +
  a garbage-token/MockTransport test.

## `get_user_notes` tool is wired but results never enter the assembled context (UNFIXED)

- `pipeline.py::_finalize` hardcodes `notes=[]` (line 880); `_accumulate` has no
  notes bucket; `retrieved` has no `notes` key (614-621).
- Model sees notes only via a raw tool round-trip, never via the `<notes>`
  context section. Same "shipped plumbing, missing bridge" family as the
  pre-07-07 ChangeSet gap.

## Live-DB pollution (08-04 read-only audit)

- 3,855 `:AppUser` (test zombies), 21 `:Session` ALL expired (5 orphaned) — no
  sweep ever ran.
- `series_dexter` holds 12 Claims/12 Evidence vs 9/9 seeded → +6 edges = the
  exact `{'relationships': 33} != {'relationships': 27}` seed-test failure.
- **ROOT CAUSE of the seed drift: `test_candidate_ingest`/`test_candidate_review`
  write real `series_dexter` rows without cleanup. Reseeding will NOT fix the
  red suite** — the candidate tests must be scratch-series-scoped (as the
  retrieval tests already are).
- Read-only audit probe pattern: fresh `Neo4jDatabase` + `asyncio.run` + count
  queries; for the `:AppSetting` llm node check key PRESENCE only
  (`size(s.value)`, `s.value CONTAINS 'api_key'`) — never print the value.

## ChangeSet create-path facts (verified 08-04)

- ChangeSet create ops stamp `visible_from_order = current_progress`
  (`repository/change_set.py` apply, lines 625/669/726/777/797) while direct
  user-content creates stamp `episode.episode_order`
  (`repository/user_content.py:179`) — two visibility-derivation rules for the
  same create intent; the ChangeSet path validates `episode_id` but never uses
  its order.
- `created_by` is stamped ONLY on ChangeSet creates
  (`graph/change_set.py:211,249,284,320,339`), never on the direct API creates
  (which are the anonymous routes).
- The ChangeSet path (propose→confirm→revert) + `spoiler/filter.py` are the
  strongest code in the repo — don't rework them.

## Full-history secret/PII audit (pre-publication)

- Coverage must be `git rev-list --all` + `git reflog --all --format=%H`
  (amended/reset-away commits) + `git fsck --full --unreachable` (commits AND
  blobs) + stash.
- Dedupe blobs via `git cat-file --batch`; pushed-status per commit via
  `git merge-base --is-ancestor <sha> origin/main` exit code.
- Author emails come from commit METADATA (the personal Gmail
  `oyunlarinefendiler@gmail.com` was the only real PII in this repo's pushed
  history — blobs were clean).
- Working script + pitfalls: see the `git-history-secret-audit` skill.
