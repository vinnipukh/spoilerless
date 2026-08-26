---
phase: 12-post-hardening-remediation-and-code-quality
plan: 06
subagent: executor
status: complete
requirements: [THERMO-P3-02, THERMO-P3-05, THERMO-P3-06]
---

# Plan 12-06 Summary — Domain/service layer boundary cleanups

## What was built

1. **THERMO-P3-02** (commit `1f89d25`): `ProposeChangesetInput` moved verbatim (docstring included) from `spoilerless/app/retrieval/pipeline.py` to `spoilerless/app/domain/change_set.py`, placed after the operation union. `pipeline.py` now imports it from domain; `services/change_set.py` imports it top-level and the inline "avoid circular import" import in `propose_via_tool` is gone. One deviation (Rule 1): the plan snippet omitted `BaseModel` from the pydantic import in `domain/change_set.py` — added it (caught by test collection NameError).
2. **THERMO-P3-05/P3-06** (commit `43c5f96`): `warn_if_open_signup(settings)` moved from `services/chat.py` to `services/auth.py` with its own module logger; chat.py's now-unused `logging` import + `logger` removed. `main.py` lifespan calls it via direct top-level `from spoilerless.app.services.auth import warn_if_open_signup`; defensive try/except import deleted. Behavior identical (warns only when environment==production and ALLOWED_EMAILS empty).
3. **Revisions hygiene** (commit `79fba5b`): single clean `from spoilerless.app.domain.user_content import CustomNodeType, NoteTargetType` (dropped the duplicate change_set re-export + alias — verified both enums have identical members at runtime); `before_snapshot` deserialized exactly once in `revert_revision_work` (`RevisionRepository._from_json(revision.get("before")) or {}`), target_type validation reads the same dict. No module split (deferred to 12-11). Envelopes/messages untouched.

## Verification

- `pytest spoilerless/tests/test_change_set_revision.py spoilerless/tests/test_revisions.py -q` → **22 passed**
- `pytest spoilerless/tests/test_auth.py spoilerless/tests/test_chat_api.py -q` → 74 passed (Task 2)
- `pytest spoilerless/tests/test_change_set_api.py` included in Task 1 gate run → 40 passed across the trio
- `unset PYTHONPATH && uv run python -c "from spoilerless.app.main import app"` → OK after every task
- Grep audits: no `class ProposeChangesetInput` left in pipeline.py; no inline pipeline import in services/change_set.py; main.py has the direct top-level auth import

## Deviations

- **[Rule 1 - Bug]** Added missing `BaseModel` to `domain/change_set.py` pydantic imports (plan snippet assumed it was already imported). Commit `1f89d25`.
- **[Rule 1 - Cleanup]** Removed chat.py's dead `import logging` + module `logger` left behind by the function move. Commit `43c5f96`.
- **Pre-existing flake found (out of scope, not fixed):** `test_change_set_revision.py::test_revert_of_canonical_override_note_leaves_canonical_resource_untouched` fails when run AFTER `test_revisions.py` — its `_user_note_count_for_target(DEXTER)` counts UserNotes globally within `series_dexter`, and `test_revisions.py` creates dexter-targeted notes with no DETACH DELETE cleanup, so leftovers double the count. Order-dependent only: passes in isolation and passes when change-set suite runs first (the plan's prescribed gate order). Suggest a cleanup fixture or per-test unique series for 12-11.

## Self-Check: PASSED

Commits: `1f89d25`, `43c5f96`, `79fba5b` on main. Files modified: spoilerless/app/domain/change_set.py · spoilerless/app/retrieval/pipeline.py · spoilerless/app/services/change_set.py · spoilerless/app/services/auth.py · spoilerless/app/services/chat.py · spoilerless/app/main.py · spoilerless/app/revisions/__init__.py
