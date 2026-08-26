# Plan 12-11 Summary: Name Revisions Package & Unseam Data Layer from HTTP

## Overview
- **Phase**: 12-post-hardening-remediation-and-code-quality
- **Plan**: 12-11
- **Objective**: Split `spoilerless/app/revisions/__init__.py` into named submodules (`repository.py` and `service.py`), unseam the data layer from HTTP exception dependencies by introducing domain exceptions, and register the uniform revision exceptions in `api/exceptions.py::_SENTINEL_SPECS`.

## Completed Tasks

### Task 1: Split `revisions/__init__.py` into `repository.py` and `service.py`
- Created `spoilerless/app/revisions/repository.py` owning `RevisionRepository`, `REVISION_CREATE_QUERY`, and `REVISION_GET_QUERY`.
- Created `spoilerless/app/revisions/service.py` owning `revert_revision_work`, `_REVERT_LABEL_ALLOWLIST`, and `_IMMUTABLE_FIELDS`.
- Reduced `spoilerless/app/revisions/__init__.py` to a package docstring only (no re-export shim).
- Updated all importer paths across the codebase (`api/revisions.py`, `graph/candidates.py`, `repository/change_set.py`, `repository/user_content.py`).

### Task 2: Introduce Domain Exceptions & Sentinel Registration
- Defined domain exception hierarchy in `spoilerless/app/revisions/service.py`: `RevisionError`, `RevisionNotFound`, `RevisionForbidden`, `RevisionCannotRevertCreate`, `RevisionCannotRevertCanonical`, `RevisionAlreadyExists`, and `RevisionInvalidAction`.
- Converted all 10 `http_error` raise sites inside `revert_revision_work` to domain exceptions, completely removing `http_error` from `service.py`.
- Registered the 5 uniform revision exceptions in `_SENTINEL_SPECS` within `spoilerless/app/api/exceptions.py`.
- Updated `revert_revision` route in `spoilerless/app/api/revisions.py` with an explicit catch for context-varying `RevisionInvalidAction`.

### Task 3: Envelope Parity Tests & Registry Pinning
- Added `TestRevertEnvelopeParityAndSuccess` in `spoilerless/tests/test_revisions.py` covering byte-identical error envelopes for all 6 exception types and asserting that successful revert logs a `Reverted` revision with actor `user_id`.
- Added `TestSentinelRegistryPin` in `spoilerless/tests/test_error_handlers.py` pinning the 5 revision sentinels in `_SENTINEL_SPECS`.

## Verification & Artifacts
- **Provided Artifacts**:
  - `spoilerless/app/revisions/repository.py`
  - `spoilerless/app/revisions/service.py`
  - `spoilerless/app/revisions/__init__.py` (docstring only)
  - `spoilerless/app/api/exceptions.py`
  - `spoilerless/app/api/revisions.py`
  - `spoilerless/app/graph/candidates.py`
  - `spoilerless/app/repository/change_set.py`
  - `spoilerless/app/repository/user_content.py`
  - `spoilerless/tests/test_revisions.py`
  - `spoilerless/tests/test_error_handlers.py`

## Git Commit Instructions
Commit message:
`refactor(12-11): name revisions package and unseam data layer from HTTP exceptions`
