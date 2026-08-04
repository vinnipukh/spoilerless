"""Chat service — session CRUD, grounded answer orchestration, provider wiring.

``get_llm_provider`` is the FastAPI dependency that builds the configured
provider; tests override it via ``app.dependency_overrides`` with the
deterministic ``FakeLLMProvider`` (zero network).  A disabled provider
(``LLM_ENABLED=false``) raises ``LLMProviderDisabled`` and an unconfigured or
unavailable provider raises ``LLMProviderUnavailable`` — both map to HTTP 503
via :func:`install_llm_error_handlers`, never 401/403.
"""

from __future__ import annotations

from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, Header
from pydantic import ValidationError

from backend.app.api.deps import DatabaseDependency
from backend.app.core.config import get_settings
from backend.app.core.errors import http_error
from backend.app.domain.chat import (
    ChatMessageResponse,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    Citation,
    GraphFocus,
    MessageResponseEnvelope,
)
from backend.app.domain.settings import DEFAULT_GEMINI_BASE_URL, LLMSettingsUpdate
from backend.app.graph.database import Neo4jDatabase
from backend.app.llm.provider import (
    GeminiProvider,
    LLMProvider,
    LLMProviderDisabled,
    LLMProviderUnavailable,
    OpenAICompatibleProvider,
)
from backend.app.repository.chat import ChatRepository, ChatSessionNotFound
from backend.app.repository.settings import SettingsRepository
from backend.app.retrieval.pipeline import RetrievalPipeline
from backend.app.services.progress import ProgressNotFoundError, ProgressService


# Bounded concurrent generations per user (T-06-13, DoS mitigation).  A plain
# module-level dict is sufficient here: this app is single-process/single-
# worker for local dev, and every mutation is a synchronous dict write with no
# ``await`` in between check-and-increment, so no separate lock is needed —
# asyncio guarantees no other coroutine runs between two non-await statements.
_MAX_CONCURRENT_GENERATIONS_PER_USER = 1
_concurrent_generations: dict[str, int] = {}


class ConcurrentGenerationLimitExceeded(RuntimeError):
    """The user already has a generation in flight (T-06-13).

    Maps to HTTP 429 (``too_many_requests``) at the API boundary — a clear,
    non-500 rejection, never a silently dropped or overwritten request.
    """


def _acquire_generation_slot(user_id: str) -> None:
    current = _concurrent_generations.get(user_id, 0)
    if current >= _MAX_CONCURRENT_GENERATIONS_PER_USER:
        raise ConcurrentGenerationLimitExceeded(
            f"User {user_id} already has a generation in progress."
        )
    _concurrent_generations[user_id] = current + 1


def _release_generation_slot(user_id: str) -> None:
    current = _concurrent_generations.get(user_id, 0)
    if current > 0:
        _concurrent_generations[user_id] = current - 1


async def get_llm_provider(
    database: DatabaseDependency,
    x_llm_api_key: Annotated[str | None, Header(alias="X-LLM-Api-Key")] = None,
    x_llm_base_url: Annotated[str | None, Header(alias="X-LLM-Base-URL")] = None,
    x_llm_model: Annotated[str | None, Header(alias="X-LLM-Model")] = None,
) -> LLMProvider:
    """Build the LLM provider for one request (request-scoped, D-06).

    BYOK (bring-your-own-key): when the request carries a non-blank
    ``X-LLM-Api-Key`` header, the provider is built EXCLUSIVELY from the
    ``X-LLM-Api-Key`` / ``X-LLM-Base-URL`` / ``X-LLM-Model`` header values —
    the persisted ``:AppSetting {key: 'llm'}`` node and the ``LLM_*`` env
    fallback are never consulted for that request, and BYOK only supports
    the OpenAI-compatible interface (provider type is fixed to
    ``openai_compatible``). This closes the shared-key SSRF/theft surface
    (docs/PROBLEMS.md #5): a user can only ever spend or redirect their own
    key to their own chosen host (T-08-02-01). The header values reach ONLY
    the ``OpenAICompatibleProvider`` constructor — never a response model, a
    log line, or a persisted record (T-08-02-02).

    Without BYOK headers the resolution order is unchanged — persisted
    stored settings first, then the ``LLM_*`` env fallback (now the optional
    server-side fallback tier per D-06, not the primary path). The API key
    is read only here, inside the provider constructor — it never appears in
    a response model, a log line, or a Revision record (T-06-07). ``gemini``
    falls back to the official Google endpoint when no ``base_url`` is
    configured anywhere.
    """
    if x_llm_api_key and x_llm_api_key.strip():
        base_url = (x_llm_base_url or "").strip()
        model = (x_llm_model or "").strip()
        if base_url:
            # Reuse LLMSettingsUpdate._validate_base_url (http/https only,
            # host required) so a malformed BYOK base_url fails the same way
            # a malformed stored one does — HTTP 422, never silently
            # reaching an unintended scheme (T-08-02-03). The api key is
            # never part of the error payload.
            try:
                validated = LLMSettingsUpdate(base_url=base_url)
            except ValidationError as exc:
                error = exc.errors()[0]
                raise http_error(422, "invalid_request", error["msg"]) from exc
            base_url = validated.base_url
        if not base_url or not model:
            raise LLMProviderUnavailable("The LLM provider is not configured.")
        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=x_llm_api_key.strip(),
            model=model,
        )
    settings = get_settings()
    stored = await SettingsRepository(database).get_llm() or {}
    # The on/off switch is part of the persisted settings (UI-controllable);
    # the LLM_ENABLED env fallback applies only when never stored.
    enabled = stored.get("enabled", settings.llm_enabled)
    if not enabled:
        raise LLMProviderDisabled("The LLM provider is disabled.")
    provider = stored.get("provider") or settings.llm_provider
    api_key = stored.get("api_key") or settings.llm_api_key
    model = stored.get("model") or settings.llm_model
    base_url = stored.get("base_url") or settings.llm_base_url
    if provider == "gemini":
        if not api_key or not model:
            raise LLMProviderUnavailable("The LLM provider is not configured.")
        return GeminiProvider(
            api_key=api_key,
            model=model,
            base_url=base_url or DEFAULT_GEMINI_BASE_URL,
        )
    if provider != "openai_compatible":
        raise LLMProviderUnavailable(
            f"Unsupported LLM provider: {provider}"
        )
    if not base_url or not api_key or not model:
        raise LLMProviderUnavailable("The LLM provider is not configured.")
    return OpenAICompatibleProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


class ChatService:
    """Orchestrates chat sessions, persistence, and grounded answers."""

    def __init__(
        self,
        database: Neo4jDatabase,
        progress_service: ProgressService | None = None,
        pipeline: RetrievalPipeline | None = None,
    ) -> None:
        self._database = database
        self._repository = ChatRepository(database)
        self._progress = progress_service or ProgressService(database)
        self._pipeline = pipeline or RetrievalPipeline(
            database, progress_service=self._progress
        )

    async def create_session(
        self, user_id: str, series_id: str, title: str
    ) -> ChatSessionResponse:
        return await self._repository.create_session(user_id, series_id, title)

    async def list_sessions(
        self, user_id: str, series_id: str
    ) -> list[ChatSessionResponse]:
        return await self._repository.list_sessions(user_id, series_id)

    async def delete_session(
        self, user_id: str, series_id: str, session_id: str
    ) -> None:
        await self._repository.delete_session(user_id, series_id, session_id)

    def acquire_generation_slot(self, user_id: str) -> None:
        """Reserve one concurrent-generation slot for ``user_id``.

        Raises ``ConcurrentGenerationLimitExceeded`` when the user already
        has a generation in flight.  Callers that acquire explicitly (the
        streaming API route, ahead of opening the SSE response) MUST release
        via :meth:`release_generation_slot` in a ``finally`` — including on
        client disconnect — so the slot never leaks.
        """
        _acquire_generation_slot(user_id)

    def release_generation_slot(self, user_id: str) -> None:
        _release_generation_slot(user_id)

    async def ensure_progress_for_chat(self, user_id: str, series_id: str) -> None:
        """Resolve-or-create the boundary up-front so chat can run.

        Used by the streaming route's pre-check: a missing progress row can
        never surface as a mid-stream failure because the row is created
        here at order 1 (see :meth:`_resolve_or_create_progress`); the
        session-not-found check in the same pre-check remains the only 404
        this path produces (RAG-01).
        """
        await self._resolve_or_create_progress(user_id, series_id)

    async def _resolve_or_create_progress(self, user_id: str, series_id: str) -> int:
        """Resolve the persisted boundary; auto-create order-1 when absent.

        A user with no persisted watch-progress row is the app's implied
        default state — the graph already loads order 1 — so the chat
        message paths create the row at ``visible_until_order=1`` instead of
        failing closed with ``ProgressNotFoundError``. The pipeline itself
        already tolerates a missing boundary (empty context →
        INSUFFICIENT_EVIDENCE answer, RAG-01 fail-closed), so the old 404
        was purely a route-level UX wall.
        """
        try:
            return await self._progress.resolve(user_id, series_id)
        except ProgressNotFoundError:
            await self._progress.upsert(
                user_id, series_id, watched_through_order=1, view_as_of_order=1
            )
            return 1

    async def get_session_detail(
        self, user_id: str, series_id: str, session_id: str
    ) -> ChatSessionDetailResponse:
        """Return the session plus messages visible at the current boundary.

        Raises ``ChatSessionNotFound`` for foreign or missing sessions (the
        identical generic not-found).  With no persisted progress the message
        list fails closed to empty — never an error that reveals existence.
        """
        session = await self._repository.get_session(user_id, series_id, session_id)
        try:
            boundary = await self._progress.resolve(user_id, series_id)
        except ProgressNotFoundError:
            boundary = None
        if boundary is None:
            messages: list[ChatMessageResponse] = []
        else:
            messages = await self._repository.list_messages_for_response(
                user_id, series_id, session_id, boundary
            )
        return ChatSessionDetailResponse(session=session, messages=messages)

    async def answer_stream(
        self,
        *,
        user_id: str,
        series_id: str,
        chat_session_id: str,
        question: str,
        provider: LLMProvider,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run one grounded turn; yield stream chunks then a final done chunk.

        Yields ``{"type": "text_delta", "text": ...}`` chunks followed by one
        ``{"type": "done", "envelope": {...}}`` chunk carrying the full
        ``MessageResponseEnvelope``.  Persists the user message before
        streaming and the assistant message (with the exact boundary snapshot
        used) after the pipeline completes.

        Acquires the per-user concurrent-generation slot for the duration of
        the call and always releases it in ``finally`` — on normal
        completion, on any exception, and on ``aclose()`` (the ``GeneratorExit``
        Starlette raises here when a streaming client disconnects mid-turn) —
        so the slot never leaks (T-06-13).
        """
        self.acquire_generation_slot(user_id)
        try:
            boundary = await self._resolve_or_create_progress(user_id, series_id)
            history = await self._repository.list_messages_for_context(
                user_id, series_id, chat_session_id, boundary
            )
            await self._repository.create_message(
                user_id,
                series_id,
                chat_session_id,
                role="user",
                content=question,
                visible_until_order_snapshot=boundary,
            )

            # The Settings "Assistant language" choice selects which system
            # prompt the agent receives (english | turkish).
            stored = await SettingsRepository(self._database).get_llm() or {}
            prompt_language = (
                stored.get("system_prompt_language") or "english"
            )

            final_done: Any = None
            async for event in self._pipeline.answer(
                user_id=user_id,
                series_id=series_id,
                chat_session_id=chat_session_id,
                question=question,
                history=history,
                provider=provider,
                prompt_language=prompt_language,
            ):
                if event.kind == "text_delta" and event.text:
                    yield {"type": "text_delta", "text": event.text}
                elif event.kind == "done":
                    final_done = event

            citations = [
                Citation.model_validate(citation)
                for citation in (final_done.citations or [])
            ]
            graph_focus = GraphFocus(
                node_ids=(final_done.graph_focus or {}).get("node_ids", []),
                edge_ids=(final_done.graph_focus or {}).get("edge_ids", []),
            )
            assistant_message = await self._repository.create_message(
                user_id,
                series_id,
                chat_session_id,
                role="assistant",
                content=final_done.content or "",
                visible_until_order_snapshot=boundary,
                citations=[citation.model_dump() for citation in citations],
                graph_focus=graph_focus.model_dump(),
            )
            envelope = MessageResponseEnvelope(
                message=assistant_message,
                citations=citations,
                graph_focus=graph_focus,
                proposed_change_set=final_done.proposed_change_set,
            )
            yield {"type": "done", "envelope": envelope.model_dump(mode="json")}
        finally:
            self.release_generation_slot(user_id)

    async def answer(
        self,
        *,
        user_id: str,
        series_id: str,
        chat_session_id: str,
        question: str,
        provider: LLMProvider,
    ) -> MessageResponseEnvelope:
        """Non-streaming variant: consume the stream and return the envelope."""
        done_chunk: dict[str, Any] | None = None
        async for chunk in self.answer_stream(
            user_id=user_id,
            series_id=series_id,
            chat_session_id=chat_session_id,
            question=question,
            provider=provider,
        ):
            if chunk["type"] == "done":
                done_chunk = chunk
        if done_chunk is None:
            raise LLMProviderUnavailable("The LLM provider returned no answer.")
        return MessageResponseEnvelope.model_validate(done_chunk["envelope"])


LLMProviderDependency = Annotated[LLMProvider, Depends(get_llm_provider)]
