"""ChangeSet API routes — Stage 1 (Propose) and Stage 2 (Confirm/Apply)
(RAG-11, RAG-12, RAG-13, RAG-14).

``POST /api/series/{series_id}/change-sets`` is Stage 1 (propose, 06-05).
``POST .../{change_set_id}/confirm`` and ``POST .../{change_set_id}/reject``
are Stage 2 (06-06) — confirm re-validates everything fresh and applies the
whole ChangeSet in one Neo4j write transaction; reject makes zero graph
mutation. Every request is user-scoped via ``require_current_user``, exactly
like ``api/progress.py``/``api/chat.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from spoilerless.app.api.deps import (
    CsrfGuardDependency,
    CurrentUserDependency,
    DatabaseDependency,
    RequireAdminDependency,
)
from spoilerless.app.cache.graph_cache import invalidate_series
from spoilerless.app.core.errors import error_responses, http_error
from spoilerless.app.domain.change_set import ChangeSetCreateRequest, ChangeSetResponse
from spoilerless.app.services.change_set import (
    ChangeSetConflict,
    ChangeSetNotRevertible,
    ChangeSetRevertConflict,
    ChangeSetService,
)

router = APIRouter(prefix="/api/series/{series_id}/change-sets", tags=["change-sets"])


def get_change_set_service(database: DatabaseDependency) -> ChangeSetService:
    return ChangeSetService(database)


ChangeSetServiceDependency = Annotated[ChangeSetService, Depends(get_change_set_service)]


def _conflict(message: str = "The request conflicts with the current resource state.") -> None:
    raise http_error(409, "RESOURCE_CONFLICT", message)


@router.post(
    "",
    response_model=ChangeSetResponse,
    status_code=201,
    summary="Propose a ChangeSet for graph modification",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        422: error_responses(422)[422],
    },
)
async def propose_change_set(
    series_id: str,
    payload: ChangeSetCreateRequest,
    user: CurrentUserDependency,
    service: ChangeSetServiceDependency,
    _csrf: CsrfGuardDependency,
) -> ChangeSetResponse:
    """Validate every operation server-side and persist only the draft.

    No target node/relationship/claim is ever mutated here — propose writes
    only the ``ChangeSet`` draft resource itself (Stage 2/06-06 applies it).
    """
    if payload.series_id != series_id:
        raise http_error(422, "INVALID_REQUEST", "Request validation failed.")
    # PROB-10/#70: ProgressNotFoundError/ChangeSetSessionNotFound/ChangeSet
    # ValidationError translate via the api/exceptions.py registry.
    return await service.propose(user["id"], series_id, payload)


@router.post(
    "/{change_set_id}/confirm",
    response_model=ChangeSetResponse,
    status_code=200,
    summary="Confirm and apply a ChangeSet",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        409: error_responses(409)[409],
        422: error_responses(422)[422],
    },
)
async def confirm_change_set(
    series_id: str,
    change_set_id: str,
    user: CurrentUserDependency,
    service: ChangeSetServiceDependency,
    _admin: RequireAdminDependency,
    _csrf: CsrfGuardDependency,
) -> ChangeSetResponse:
    """Re-validate everything fresh and apply the whole ChangeSet transactionally.

    Admin-only since 08-03 (AUTH-03, T-08-03-02) — confirming applies an
    AI-proposed ChangeSet to the shared canonical graph, so a non-admin gets
    403 before any mutation. propose/reject/revert are intentionally NOT gated.

    Confirming an already-``applied`` ChangeSet is a safe idempotent no-op
    (the original stored result is returned). A stale ChangeSet (proposed at
    a higher progress boundary than the current, since-lowered, progress) is
    rejected with a distinct ``409 changeset_stale`` — never silently applied.
    """
    # PROB-10/#70: ChangeSetNotFound/ChangeSetStale/ChangeSetOperationInvalid
    # translate via the registry; ChangeSetConflict keeps its context-specific
    # message here.
    try:
        result = await service.confirm(user["id"], series_id, change_set_id)
    except ChangeSetConflict:
        _conflict("This ChangeSet has already been resolved and cannot be confirmed again.")
    await invalidate_series(series_id)
    return result


@router.post(
    "/{change_set_id}/reject",
    response_model=ChangeSetResponse,
    status_code=200,
    summary="Reject a ChangeSet",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        409: error_responses(409)[409],
    },
)
async def reject_change_set(
    series_id: str,
    change_set_id: str,
    user: CurrentUserDependency,
    service: ChangeSetServiceDependency,
    _csrf: CsrfGuardDependency,
) -> ChangeSetResponse:
    """Reject a ChangeSet — zero graph mutation, cannot be confirmed afterward."""
    try:
        return await service.reject(user["id"], series_id, change_set_id)
    except ChangeSetConflict:
        _conflict("This ChangeSet has already been resolved and cannot be rejected again.")


@router.post(
    "/{change_set_id}/revert",
    response_model=ChangeSetResponse,
    status_code=200,
    summary="Revert a previously applied ChangeSet",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        409: error_responses(409)[409],
        422: error_responses(422)[422],
    },
)
async def revert_change_set(
    series_id: str,
    change_set_id: str,
    user: CurrentUserDependency,
    service: ChangeSetServiceDependency,
    _csrf: CsrfGuardDependency,
) -> ChangeSetResponse:
    """Revert a previously applied ChangeSet's create-shaped operations.

    Deletes every resource this ChangeSet created — restoring pre-apply
    state — and logs a new ``Reverted``-action Revision; the original
    apply-time Revision is never edited or deleted. Requires its own
    explicit call, distinct from the original apply confirmation. Only
    ChangeSets whose operations are entirely create-shaped support revert
    (RAG-15's minimal-revert allowance — an update/delete-shaped operation
    has no stored prior state to restore and returns **422**). A resource
    modified or removed by a later, unrelated change since this ChangeSet
    was applied causes revert to fail with **409** rather than silently
    overwrite that change.
    """
    # PROB-10/#70: ChangeSetNotFound / ChangeSetRevertUnsupported translate
    # via the registry; NotRevertible/RevertConflict keep context messages.
    try:
        result = await service.revert(user["id"], series_id, change_set_id)
    except ChangeSetNotRevertible:
        _conflict("This ChangeSet has no applied Revision to revert.")
    except ChangeSetRevertConflict:
        _conflict(
            "A resource this ChangeSet created was modified or removed by a later, "
            "unrelated change; revert was aborted to avoid overwriting it."
        )
    await invalidate_series(series_id)
    return result
