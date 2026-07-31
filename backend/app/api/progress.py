"""Watch-progress API routes (RAG-01).

``visible_until_order`` is never accepted as request input on any GraphRAG
path — this explicit progress endpoint is the only place a client may request
a change, and the boundary is always resolved server-side from the persisted
``UserSeriesProgress`` record for the authenticated user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.deps import CurrentUserDependency, DatabaseDependency
from backend.app.core.errors import error_responses, http_error
from backend.app.domain.progress import (
    ProgressUpdateRequest,
    UserSeriesProgressResponse,
)
from backend.app.services.progress import ProgressService

router = APIRouter(prefix="/api/series/{series_id}", tags=["progress"])


def get_progress_service(database: DatabaseDependency) -> ProgressService:
    return ProgressService(database)


ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]


@router.get(
    "/progress",
    response_model=UserSeriesProgressResponse,
    summary="Get the authenticated user's persisted watch progress",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
    },
)
async def get_progress(
    series_id: str,
    user: CurrentUserDependency,
    service: ProgressServiceDependency,
) -> UserSeriesProgressResponse:
    """Return the current progress record, or a generic 404 when none exists.

    Hidden-or-missing must never reveal whether the series exists — the
    generic ``resource_not_found`` envelope is used for both.
    """
    progress = await service.get(user["id"], series_id)
    if progress is None:
        raise http_error(404, "resource_not_found", "Resource not found.")
    return progress


@router.post(
    "/progress",
    response_model=UserSeriesProgressResponse,
    summary="Create or update the authenticated user's watch progress",
    responses={
        401: error_responses(401)[401],
        422: error_responses(422)[422],
    },
)
async def update_progress(
    series_id: str,
    payload: ProgressUpdateRequest,
    user: CurrentUserDependency,
    service: ProgressServiceDependency,
) -> UserSeriesProgressResponse:
    """Upsert the progress record (idempotent for equal values) and return it."""
    return await service.upsert(
        user["id"], series_id, payload.visible_until_order
    )
