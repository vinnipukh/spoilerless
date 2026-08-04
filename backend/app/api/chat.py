"""Chat API routes (RAG-09, RAG-10).

Series-scoped session/message REST family plus the SSE streaming variant.
Every route is user-scoped via ``require_current_user``; foreign or missing
sessions produce the identical generic 404.  The streaming endpoint ends with
an ``event: done`` SSE event carrying the full ``MessageResponseEnvelope``
(message, citations, graph_focus, proposed_change_set).
"""

from __future__ import annotations

import json
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from backend.app.api.deps import CurrentUserDependency, DatabaseDependency
from backend.app.core.errors import error_responses, http_error
from backend.app.domain.chat import (
    ChatMessageCreateRequest,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    MessageResponseEnvelope,
)
from backend.app.llm.provider import LLMProvider, LLMProviderUnavailable
from backend.app.repository.chat import ChatSessionNotFound
from backend.app.services.chat import (
    ConcurrentGenerationLimitExceeded,
    LLMProviderDependency,
    ChatService,
)
from backend.app.services.progress import ProgressNotFoundError
from backend.app.services.rate_limit import chat_send_rate_limiter

router = APIRouter(prefix="/api/series/{series_id}/chat", tags=["chat"])


def get_chat_service(database: DatabaseDependency) -> ChatService:
    return ChatService(database)


ChatServiceDependency = Annotated[ChatService, Depends(get_chat_service)]


def _not_found() -> None:
    raise http_error(404, "resource_not_found", "Resource not found.")


def _too_many_requests() -> None:
    raise http_error(429, "too_many_requests", "Too many concurrent requests.")


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=201,
    summary="Create a chat session for the series",
    responses={
        401: error_responses(401)[401],
        422: error_responses(422)[422],
    },
)
async def create_session(
    series_id: str,
    payload: ChatSessionCreateRequest,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
) -> ChatSessionResponse:
    return await service.create_session(user["id"], series_id, payload.title)


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="List the authenticated user's chat sessions for the series",
    responses={
        401: error_responses(401)[401],
    },
)
async def list_sessions(
    series_id: str,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
) -> list[ChatSessionResponse]:
    return await service.list_sessions(user["id"], series_id)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    summary="Get a chat session with its boundary-visible messages",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
    },
)
async def get_session(
    series_id: str,
    session_id: str,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
) -> ChatSessionDetailResponse:
    try:
        return await service.get_session_detail(user["id"], series_id, session_id)
    except ChatSessionNotFound:
        _not_found()


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Delete a chat session and its messages",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        204: {"description": "Session deleted."},
    },
)
async def delete_session(
    series_id: str,
    session_id: str,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
) -> Response:
    """Hard-delete the session and its messages.

    Foreign, cross-series, and missing sessions all return the identical
    generic 404 as ``GET`` (no separate ownership existence-check query is
    needed — a single user-scoped MATCH already makes those three cases
    indistinguishable; see 06-PATTERNS.md note in ``graph/chat.py``).
    """
    try:
        await service.delete_session(user["id"], series_id, session_id)
    except ChatSessionNotFound:
        _not_found()
    return Response(status_code=204)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponseEnvelope,
    summary="Send a message and receive the grounded answer envelope",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        429: error_responses(429)[429],
        503: error_responses(503)[503],
    },
)
async def post_message(
    series_id: str,
    session_id: str,
    payload: ChatMessageCreateRequest,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
    provider: LLMProviderDependency,
    _rate_limit: Annotated[None, Depends(chat_send_rate_limiter)],
) -> MessageResponseEnvelope:
    try:
        return await service.answer(
            user_id=user["id"],
            series_id=series_id,
            chat_session_id=session_id,
            question=payload.question,
            provider=provider,
        )
    except (ChatSessionNotFound, ProgressNotFoundError):
        _not_found()
    except ConcurrentGenerationLimitExceeded:
        _too_many_requests()


@router.post(
    "/sessions/{session_id}/messages/stream",
    summary="Stream a grounded answer as server-sent events",
    responses={
        401: error_responses(401)[401],
        404: error_responses(404)[404],
        429: error_responses(429)[429],
        503: error_responses(503)[503],
    },
)
async def stream_message(
    series_id: str,
    session_id: str,
    payload: ChatMessageCreateRequest,
    user: CurrentUserDependency,
    service: ChatServiceDependency,
    provider: LLMProviderDependency,
    _rate_limit: Annotated[None, Depends(chat_send_rate_limiter)],
) -> StreamingResponse:
    """Stream text deltas, then a final ``event: done`` with the envelope."""
    # Resolve session ownership and progress existence up-front so a
    # not-found (foreign/missing session, or no persisted progress yet)
    # surfaces as a normal HTTP 404 before any streaming begins — once SSE
    # headers are sent an in-stream exception cannot become a clean error
    # status (RAG-01 fail-closed guarantee). The concurrent-generation limit
    # cannot be given this same pre-check treatment: acquiring the slot must
    # happen atomically with the generation itself (inside
    # ``ChatService.answer_stream``) or two genuinely concurrent requests
    # could both pass a separate pre-check and double-book the one slot. A
    # rejection that happens after headers are already sent is instead
    # surfaced as a structured ``event: error`` below — the clearest signal
    # this transport can give once the 200 status line has already gone out.
    try:
        await service.get_session_detail(user["id"], series_id, session_id)
        await service.ensure_progress_for_chat(user["id"], series_id)
    except (ChatSessionNotFound, ProgressNotFoundError):
        _not_found()

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for chunk in service.answer_stream(
                user_id=user["id"],
                series_id=series_id,
                chat_session_id=session_id,
                question=payload.question,
                provider=provider,
            ):
                if chunk["type"] == "done":
                    yield f"event: done\ndata: {json.dumps(chunk['envelope'])}\n\n"
                else:
                    yield f"data: {json.dumps(chunk)}\n\n"
        except ConcurrentGenerationLimitExceeded:
            error_payload = {
                "code": "too_many_requests",
                "message": "Too many concurrent requests.",
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
        except LLMProviderUnavailable:
            # Provider failures happen mid-stream, after the 200 status line
            # has gone out — surface them as a structured `event: error` chunk
            # instead of silently dropping the connection (which would leave
            # the client's streaming state stuck forever).
            error_payload = {
                "code": "LLM_PROVIDER_UNAVAILABLE",
                "message": "The LLM provider is unavailable. Check your API key and model in Settings, then try again.",
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
        except Exception:
            # Never leak internals; the client must always receive a terminal
            # event so it can leave the streaming state.
            error_payload = {
                "code": "LLM_STREAM_FAILED",
                "message": "The response ended unexpectedly. Please try again.",
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
