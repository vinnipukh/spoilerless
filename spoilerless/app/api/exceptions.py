"""One registry mapping repository sentinel exceptions to the shared error envelope.

PROB-10/#70: routes no longer repeat the 4-clause try/except
(ValidationError -> 422, NotFound -> 404, Conflict -> 409, Forbidden -> 403);
the sentinels propagate to FastAPI and are translated here exactly once.
Lives in the **api** layer (not ``core/errors.py``) so the core module stays
free of repository imports — the layer-correct direction of the finding's
"one registry" fix.

Envelope texts are byte-identical to the per-router helpers they replace
(verified against the old ``_not_found``/``_invalid``/``_conflict``/
``_forbidden``/``_too_many_requests`` definitions). Exceptions whose message
varies by context (``ChangeSetConflict``: confirm/reject/revert wording)
stay as explicit one-line catches at their routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from spoilerless.app.core.errors import http_error
from spoilerless.app.repository.change_set import (
    ChangeSetNotFound,
    ChangeSetOperationInvalid,
    ChangeSetRevertUnsupported,
    ChangeSetSessionNotFound,
    ChangeSetStale,
)
from spoilerless.app.repository.chat import ChatSessionNotFound
from spoilerless.app.repository.user_content import (
    UserContentConflict,
    UserContentForbidden,
    UserContentNotFound,
    UserContentValidationError,
)
from spoilerless.app.services.change_set import ChangeSetValidationError
from spoilerless.app.services.chat import ConcurrentGenerationLimitExceeded
from spoilerless.app.services.progress import ProgressNotFoundError
from spoilerless.app.revisions.service import (
    RevisionAlreadyExists,
    RevisionCannotRevertCanonical,
    RevisionCannotRevertCreate,
    RevisionForbidden,
    RevisionNotFound,
)

# (exception type, status, code, message) — the uniform sentinel mapping.
_SENTINEL_SPECS: tuple[tuple[type[Exception], int, str, str], ...] = (
    (UserContentNotFound, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (ChangeSetNotFound, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (ChangeSetSessionNotFound, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (ChatSessionNotFound, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (ProgressNotFoundError, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (RevisionNotFound, 404, "RESOURCE_NOT_FOUND", "Resource not found."),
    (UserContentValidationError, 422, "INVALID_REQUEST", "Request validation failed."),
    (ChangeSetValidationError, 422, "INVALID_REQUEST", "Request validation failed."),
    (ChangeSetOperationInvalid, 422, "INVALID_REQUEST", "Request validation failed."),
    (ChangeSetRevertUnsupported, 422, "INVALID_REQUEST", "Request validation failed."),
    (RevisionCannotRevertCreate, 422, "CANNOT_REVERT_CREATE", "Cannot revert a Creation revision."),
    (
        UserContentConflict,
        409,
        "RESOURCE_CONFLICT",
        "The request conflicts with the current resource state.",
    ),
    (RevisionCannotRevertCanonical, 409, "CANNOT_REVERT_CANONICAL", "Cannot revert a canonical or candidate resource."),
    (RevisionAlreadyExists, 409, "RESOURCE_ALREADY_EXISTS", "This resource has already been re-created."),
    (UserContentForbidden, 403, "FORBIDDEN", "This resource belongs to another user."),
    (RevisionForbidden, 403, "FORBIDDEN", "This resource belongs to another user."),
    (
        ChangeSetStale,
        409,
        "CHANGESET_STALE",
        "This ChangeSet was proposed at a higher progress boundary than the "
        "current progress and must be regenerated before it can be confirmed.",
    ),
    (ConcurrentGenerationLimitExceeded, 429, "TOO_MANY_REQUESTS", "Too many concurrent requests."),
)


def install_repository_error_handlers(app: FastAPI) -> None:
    """Register every uniform repository sentinel -> envelope translation."""

    def _make_handler(status_code: int, code: str, message: str) -> Any:
        async def _handler(_request: Request, _exc: Exception) -> JSONResponse:
            error = http_error(status_code, code, message)
            return JSONResponse(status_code=status_code, content={"detail": error.detail})

        return _handler

    for exc_type, status_code, code, message in _SENTINEL_SPECS:
        app.add_exception_handler(exc_type, _make_handler(status_code, code, message))
