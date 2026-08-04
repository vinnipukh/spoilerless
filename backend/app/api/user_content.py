from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from backend.app.core.errors import error_responses, http_error
from backend.app.domain.user_content import (
    NoteCreate,
    NoteResponse,
    NoteTargetType,
    NoteUpdate,
    VisibleUntilOrder,
    CustomNodeCreate, CustomNodeResponse, CustomNodeUpdate,
    CustomRelationshipCreate, CustomRelationshipResponse, CustomRelationshipUpdate,
)
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.repository.user_content import (
    UserContentNotFound,
    UserContentConflict,
    UserContentRepository,
    UserContentValidationError,
)
from backend.app.services.rate_limit import content_write_rate_limiter

router = APIRouter(prefix="/api/series", tags=["user-content"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
Boundary = Annotated[int, Query(gt=0, description="Persisted positive spoiler boundary.", examples=[1])]


def _repository(database: Neo4jDatabase) -> UserContentRepository:
    return UserContentRepository(database)


def _not_found() -> Exception:
    return http_error(404, "resource_not_found", "Resource not found.")


def _invalid(exc: UserContentValidationError) -> Exception:
    return http_error(422, "invalid_request", "Request validation failed.")


def _conflict(exc: UserContentConflict) -> Exception:
    return http_error(409, "resource_conflict", "The request conflicts with the current resource state.")


@router.post(
    "/{series_id}/notes", response_model=NoteResponse, status_code=201,
    summary="Create a spoiler-safe user note", responses=error_responses(404, 409, 422, 503),
)
async def create_note(
    series_id: str, payload: NoteCreate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> NoteResponse:
    try:
        row = await _repository(database).create_note(series_id, payload)
    except UserContentValidationError as exc:
        raise _invalid(exc) from exc
    except UserContentNotFound as exc:
        raise _not_found() from exc
    return NoteResponse.model_validate(row)


@router.get(
    "/{series_id}/notes", response_model=list[NoteResponse],
    summary="List visible user notes", responses=error_responses(404, 422, 503),
)
async def list_notes(
    series_id: str,
    visible_until_order: Boundary,
    database: DatabaseDependency,
    target_type: NoteTargetType | None = Query(default=None),
    target_id: str | None = Query(default=None),
) -> list[NoteResponse]:
    try:
        rows = await _repository(database).list_notes(
            series_id, visible_until_order, target_type, target_id
        )
    except UserContentValidationError as exc:
        raise _invalid(exc) from exc
    return [NoteResponse.model_validate(row) for row in rows]


@router.get(
    "/{series_id}/notes/{note_id}", response_model=NoteResponse,
    summary="Read one visible user note", responses=error_responses(404, 422, 503),
)
async def get_note(
    series_id: str, note_id: str, visible_until_order: Boundary, database: DatabaseDependency
) -> NoteResponse:
    try:
        row = await _repository(database).get_note(series_id, note_id, visible_until_order)
    except (UserContentNotFound, UserContentValidationError) as exc:
        raise (_not_found() if isinstance(exc, UserContentNotFound) else _invalid(exc)) from exc
    return NoteResponse.model_validate(row)


@router.patch(
    "/{series_id}/notes/{note_id}", response_model=NoteResponse,
    summary="Update note content", responses=error_responses(404, 409, 422, 503),
)
async def update_note(
    series_id: str, note_id: str, payload: NoteUpdate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> NoteResponse:
    try:
        row = await _repository(database).update_note(series_id, note_id, payload)
    except UserContentValidationError as exc:
        raise _invalid(exc) from exc
    except UserContentNotFound as exc:
        raise _not_found() from exc
    return NoteResponse.model_validate(row)


@router.delete(
    "/{series_id}/notes/{note_id}", status_code=204,
    summary="Hard-delete a user note", responses={**error_responses(404, 409, 422, 503), 204: {"description": "Note deleted."}},
)
async def delete_note(
    series_id: str, note_id: str, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> Response:
    try:
        await _repository(database).delete_note(series_id, note_id)
    except UserContentValidationError as exc:
        raise _invalid(exc) from exc
    except UserContentNotFound as exc:
        raise _not_found() from exc
    return Response(status_code=204)


@router.post("/{series_id}/custom-nodes", response_model=CustomNodeResponse, status_code=201,
             summary="Create a user-owned custom node", responses=error_responses(404, 409, 422, 503))
async def create_custom_node(
    series_id: str, payload: CustomNodeCreate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> CustomNodeResponse:
    try:
        return CustomNodeResponse.model_validate(await _repository(database).create_custom_node(series_id, payload))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.get("/{series_id}/custom-nodes/{node_id}", response_model=CustomNodeResponse,
            summary="Read one visible custom node", responses=error_responses(404, 422, 503))
async def get_custom_node(series_id: str, node_id: str, visible_until_order: Boundary, database: DatabaseDependency) -> CustomNodeResponse:
    try:
        return CustomNodeResponse.model_validate(await _repository(database).get_custom_node(series_id, node_id, visible_until_order))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.patch("/{series_id}/custom-nodes/{node_id}", response_model=CustomNodeResponse,
              summary="Update a custom node label", responses=error_responses(404, 409, 422, 503))
async def update_custom_node(
    series_id: str, node_id: str, payload: CustomNodeUpdate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> CustomNodeResponse:
    try:
        return CustomNodeResponse.model_validate(await _repository(database).update_custom_node(series_id, node_id, payload))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.delete("/{series_id}/custom-nodes/{node_id}", status_code=204,
               summary="Hard-delete a custom node", responses={**error_responses(404, 409, 422, 503), 204: {"description": "Node deleted."}})
async def delete_custom_node(
    series_id: str, node_id: str, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> Response:
    try:
        await _repository(database).delete_custom_node(series_id, node_id)
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc
    return Response(status_code=204)


@router.post("/{series_id}/custom-relationships", response_model=CustomRelationshipResponse, status_code=201,
             summary="Create a user-authored relationship", responses=error_responses(404, 409, 422, 503))
async def create_custom_relationship(
    series_id: str, payload: CustomRelationshipCreate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> CustomRelationshipResponse:
    try:
        return CustomRelationshipResponse.model_validate(await _repository(database).create_custom_relationship(series_id, payload))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.get("/{series_id}/custom-relationships/{relationship_id}", response_model=CustomRelationshipResponse,
            summary="Read one visible custom relationship", responses=error_responses(404, 422, 503))
async def get_custom_relationship(series_id: str, relationship_id: str, visible_until_order: Boundary, database: DatabaseDependency) -> CustomRelationshipResponse:
    try:
        return CustomRelationshipResponse.model_validate(await _repository(database).get_custom_relationship(series_id, relationship_id, visible_until_order))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.patch("/{series_id}/custom-relationships/{relationship_id}", response_model=CustomRelationshipResponse,
              summary="Update a custom relationship predicate", responses=error_responses(404, 409, 422, 503))
async def update_custom_relationship(
    series_id: str, relationship_id: str, payload: CustomRelationshipUpdate, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> CustomRelationshipResponse:
    try:
        return CustomRelationshipResponse.model_validate(await _repository(database).update_custom_relationship(series_id, relationship_id, payload))
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc


@router.delete("/{series_id}/custom-relationships/{relationship_id}", status_code=204,
               summary="Hard-delete a custom relationship", responses={**error_responses(404, 409, 422, 503), 204: {"description": "Relationship deleted."}})
async def delete_custom_relationship(
    series_id: str, relationship_id: str, database: DatabaseDependency,
    _rate_limit: Annotated[None, Depends(content_write_rate_limiter)],
) -> Response:
    try:
        await _repository(database).delete_custom_relationship(series_id, relationship_id)
    except UserContentValidationError as exc: raise _invalid(exc) from exc
    except UserContentConflict as exc: raise _conflict(exc) from exc
    except UserContentNotFound as exc: raise _not_found() from exc
    return Response(status_code=204)
