"""ChangeSet API routes — Stage 1 (Propose) (RAG-11, RAG-13).

``POST /api/series/{series_id}/change-sets`` is the only route this plan
adds; Stage 2 (confirm/apply) is 06-06. Every request is user-scoped via
``require_current_user``, exactly like ``api/progress.py``/``api/chat.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.deps import CurrentUserDependency, DatabaseDependency
from backend.app.core.errors import error_responses, http_error
from backend.app.domain.change_set import ChangeSetCreateRequest, ChangeSetResponse
from backend.app.services.change_set import (
    ChangeSetService,
    ChangeSetSessionNotFound,
    ChangeSetValidationError,
)
from backend.app.services.progress import ProgressNotFoundError

router = APIRouter(prefix="/api/series/{series_id}/change-sets", tags=["change-sets"])


def get_change_set_service(database: DatabaseDependency) -> ChangeSetService:
    return ChangeSetService(database)


ChangeSetServiceDependency = Annotated[ChangeSetService, Depends(get_change_set_service)]


def _not_found() -> None:
    raise http_error(404, "resource_not_found", "Resource not found.")


def _invalid() -> None:
    raise http_error(422, "invalid_request", "Request validation failed.")


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
) -> ChangeSetResponse:
    """Validate every operation server-side and persist only the draft.

    No target node/relationship/claim is ever mutated here — propose writes
    only the ``ChangeSet`` draft resource itself (Stage 2/06-06 applies it).
    """
    if payload.series_id != series_id:
        _invalid()
    try:
        return await service.propose(user["id"], series_id, payload)
    except (ProgressNotFoundError, ChangeSetSessionNotFound):
        _not_found()
    except ChangeSetValidationError:
        _invalid()
