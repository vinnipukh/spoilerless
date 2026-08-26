from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from spoilerless.app.api.boundary import resolve_effective_boundary
from spoilerless.app.api.deps import (
    CsrfGuardDependency,
    CurrentUserDependency,
    DatabaseDependency,
    GraphServiceDependency,
    OptionalUserDependency,
    ProgressServiceDependency,
)
from spoilerless.app.core.errors import error_responses
from spoilerless.app.cache.graph_cache import invalidate_series
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.domain.user_content import (
    NoteCreate,
    NoteResponse,
    NoteTargetType,
    NoteUpdate,
    VisibleUntilOrder,
    CustomNodeCreate, CustomNodeResponse, CustomNodeUpdate,
    CustomRelationshipCreate, CustomRelationshipResponse, CustomRelationshipUpdate,
)
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.repository.user_content import UserContentRepository
from spoilerless.app.services.rate_limit import content_write_rate_limiter

router = APIRouter(prefix="/api/series", tags=["user-content"])
Boundary = Annotated[int, Query(gt=0, description="Persisted positive spoiler boundary.", examples=[1])]


def _repository(database: Neo4jDatabase) -> UserContentRepository:
    return UserContentRepository(database)


def _owner_id(user: dict | None) -> str | None:
    return user["id"] if user is not None else None


def _shape_note_response(row: dict, user: dict | None) -> dict:
    """Non-owner responses never carry another user's id (D-02)."""
    owner = _owner_id(user)
    is_admin = bool(user and user.get("role") == "admin")
    if row.get("user_id") and row["user_id"] != owner and not is_admin:
        row = dict(row)
        row.pop("user_id", None)
    return row


def _actor(user: dict) -> tuple[str, bool]:
    """Return ``(user_id, is_admin)`` for the acting authenticated user."""
    return user["id"], user.get("role") == "admin"


@router.post(
    "/{series_id}/notes", response_model=NoteResponse, status_code=201,
    summary="Create a spoiler-safe user note", responses=error_responses(403, 404, 409, 422, 503),
)
async def create_note(
    series_id: str, payload: NoteCreate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> NoteResponse:
    row = await _repository(database).create_note(series_id, user["id"], payload)
    return NoteResponse.model_validate(row)


@router.get(
    "/{series_id}/notes", response_model=list[NoteResponse],
    summary="List visible user notes", responses=error_responses(404, 422, 503),
)
async def list_notes(
    series_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    target_type: NoteTargetType | None = Query(default=None),
    target_id: str | None = Query(default=None),
) -> list[NoteResponse]:
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    rows = await _repository(database).list_notes(
        series_id, effective, target_type, target_id
    )
    return [NoteResponse.model_validate(_shape_note_response(dict(row), user)) for row in rows]


@router.get(
    "/{series_id}/notes/{note_id}", response_model=NoteResponse,
    summary="Read one visible user note", responses=error_responses(404, 422, 503),
)
async def get_note(
    series_id: str,
    note_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
) -> NoteResponse:
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    row = await _repository(database).get_note(series_id, note_id, effective)
    return NoteResponse.model_validate(_shape_note_response(dict(row), user))


@router.patch(
    "/{series_id}/notes/{note_id}", response_model=NoteResponse,
    summary="Update note content", responses=error_responses(403, 404, 409, 422, 503),
)
async def update_note(
    series_id: str, note_id: str, payload: NoteUpdate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> NoteResponse:
    actor_id, is_admin = _actor(user)
    row = await _repository(database).update_note(
        series_id, note_id, actor_id, payload, is_admin=is_admin
    )
    return NoteResponse.model_validate(row)


@router.delete(
    "/{series_id}/notes/{note_id}", status_code=204,
    summary="Hard-delete a user note", responses={**error_responses(403, 404, 409, 422, 503), 204: {"description": "Note deleted."}},
)
async def delete_note(
    series_id: str, note_id: str, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> Response:
    actor_id, is_admin = _actor(user)
    await _repository(database).delete_note(
        series_id, note_id, actor_id, is_admin=is_admin
    )
    return Response(status_code=204)


@router.post("/{series_id}/custom-nodes", response_model=CustomNodeResponse, status_code=201,
             summary="Create a user-owned custom node", responses=error_responses(403, 404, 409, 422, 503))
async def create_custom_node(
    series_id: str, payload: CustomNodeCreate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> CustomNodeResponse:
    row = await _repository(database).create_custom_node(series_id, user["id"], payload)
    await invalidate_series(series_id)
    return CustomNodeResponse.model_validate(row)


@router.get("/{series_id}/custom-nodes/{node_id}", response_model=CustomNodeResponse,
            summary="Read one visible custom node", responses=error_responses(404, 422, 503))
async def get_custom_node(
    series_id: str,
    node_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
) -> CustomNodeResponse:
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    row = await _repository(database).get_custom_node(series_id, node_id, effective)
    # Custom nodes are user-owned; hide user_id for non-owners
    shaped = _shape_note_response(dict(row), user)
    return CustomNodeResponse.model_validate(shaped)


@router.patch("/{series_id}/custom-nodes/{node_id}", response_model=CustomNodeResponse,
              summary="Update a custom node label", responses=error_responses(403, 404, 409, 422, 503))
async def update_custom_node(
    series_id: str, node_id: str, payload: CustomNodeUpdate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> CustomNodeResponse:
    actor_id, is_admin = _actor(user)
    row = await _repository(database).update_custom_node(
        series_id, node_id, actor_id, payload, is_admin=is_admin
    )
    await invalidate_series(series_id)
    return CustomNodeResponse.model_validate(row)


@router.delete("/{series_id}/custom-nodes/{node_id}", status_code=204,
               summary="Hard-delete a custom node", responses={**error_responses(403, 404, 409, 422, 503), 204: {"description": "Node deleted."}})
async def delete_custom_node(
    series_id: str, node_id: str, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> Response:
    actor_id, is_admin = _actor(user)
    await _repository(database).delete_custom_node(
        series_id, node_id, actor_id, is_admin=is_admin
    )
    await invalidate_series(series_id)
    return Response(status_code=204)


@router.post("/{series_id}/custom-relationships", response_model=CustomRelationshipResponse, status_code=201,
             summary="Create a user-authored relationship", responses=error_responses(403, 404, 409, 422, 503))
async def create_custom_relationship(
    series_id: str, payload: CustomRelationshipCreate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> CustomRelationshipResponse:
    row = await _repository(database).create_custom_relationship(series_id, user["id"], payload)
    await invalidate_series(series_id)
    return CustomRelationshipResponse.model_validate(row)


@router.get("/{series_id}/custom-relationships/{relationship_id}", response_model=CustomRelationshipResponse,
            summary="Read one visible custom relationship", responses=error_responses(404, 422, 503))
async def get_custom_relationship(
    series_id: str,
    relationship_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    graph_service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
) -> CustomRelationshipResponse:
    effective = await resolve_effective_boundary(
        graph_service, progress_service, series_id, user, visible_until_order
    )
    row = await _repository(database).get_custom_relationship(series_id, relationship_id, effective)
    shaped = _shape_note_response(dict(row), user)
    return CustomRelationshipResponse.model_validate(shaped)


@router.patch("/{series_id}/custom-relationships/{relationship_id}", response_model=CustomRelationshipResponse,
              summary="Update a custom relationship predicate", responses=error_responses(403, 404, 409, 422, 503))
async def update_custom_relationship(
    series_id: str, relationship_id: str, payload: CustomRelationshipUpdate, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> CustomRelationshipResponse:
    actor_id, is_admin = _actor(user)
    row = await _repository(database).update_custom_relationship(
        series_id, relationship_id, actor_id, payload, is_admin=is_admin
    )
    await invalidate_series(series_id)
    return CustomRelationshipResponse.model_validate(row)


@router.delete("/{series_id}/custom-relationships/{relationship_id}", status_code=204,
               summary="Hard-delete a custom relationship", responses={**error_responses(403, 404, 409, 422, 503), 204: {"description": "Relationship deleted."}})
async def delete_custom_relationship(
    series_id: str, relationship_id: str, database: DatabaseDependency,
    user: CurrentUserDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
    _csrf: CsrfGuardDependency,
) -> Response:
    actor_id, is_admin = _actor(user)
    await _repository(database).delete_custom_relationship(
        series_id, relationship_id, actor_id, is_admin=is_admin
    )
    await invalidate_series(series_id)
    return Response(status_code=204)
