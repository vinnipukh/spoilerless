"""LLM provider abstraction (RAG-04).

A small ``Protocol``-based provider layer with one real OpenAI-compatible
implementation over ``httpx`` and one deterministic fake for tests.  Provider
failures (timeout, non-2xx, connection error) raise ``LLMProviderUnavailable``;
a disabled provider raises ``LLMProviderDisabled``.  Both map to HTTP 503 via
:func:`install_llm_error_handlers` — never 401/403.

The API key is read only inside ``OpenAICompatibleProvider.__init__`` from
caller-supplied settings and never appears in events, response models, or logs.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Literal, Protocol

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class LLMEvent(BaseModel):
    """One streamed event from an LLM provider call.

    ``kind`` discriminates the event:

    - ``text_delta`` — incremental answer text (``text``)
    - ``tool_call`` — a requested allowlisted tool invocation (``tool_name``,
      ``arguments`` — the parsed JSON arguments object)
    - ``done`` — the final answer for this call (``content``), plus any
      model-supplied citation IDs (``citations``) carried through.
    """

    kind: Literal["text_delta", "tool_call", "done"]
    text: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    content: str | None = None
    # Model-side citation IDs are raw dicts (e.g. {"claim_id": "..."}); the
    # pipeline validates them against this turn's retrieved context and builds
    # the public Citation objects server-side.
    citations: list[dict[str, Any]] | None = None
    graph_focus: dict[str, Any] | None = None
    # The persisted ChangeSet draft produced by the allowlisted
    # ``propose_changeset`` tool this turn (server-validated at the
    # effective boundary, D-13); the service layer places it on the
    # done-envelope's ``proposed_change_set``.
    proposed_change_set: dict[str, Any] | None = None

    @classmethod
    def text_delta(cls, text: str) -> "LLMEvent":
        return cls(kind="text_delta", text=text)

    @classmethod
    def tool_call(cls, tool_name: str, arguments: dict[str, Any]) -> "LLMEvent":
        return cls(kind="tool_call", tool_name=tool_name, arguments=arguments)

    @classmethod
    def done(
        cls,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        graph_focus: dict[str, Any] | None = None,
        proposed_change_set: dict[str, Any] | None = None,
    ) -> "LLMEvent":
        return cls(
            kind="done",
            content=content,
            citations=citations,
            graph_focus=graph_focus,
            proposed_change_set=proposed_change_set,
        )


class LLMProviderUnavailable(Exception):
    """The LLM provider failed (timeout, non-2xx, connection error).

    Maps to HTTP 503 with code ``LLM_PROVIDER_UNAVAILABLE``.
    """


class LLMProviderDisabled(Exception):
    """The LLM provider is disabled (``LLM_ENABLED=false``).

    Maps to HTTP 503 with code ``LLM_DISABLED`` — a distinct, clear code that
    is never confused with an authentication error.
    """


class LLMProvider(Protocol):
    """Interface for streaming chat completions with optional tool calling."""

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: int,
    ) -> AsyncIterator[LLMEvent]:
        """Yield ``LLMEvent`` items for one completion call.

        When ``tools`` is non-empty the call may yield one or more ``tool_call``
        events instead of a ``done`` event.  When ``tools`` is empty the call
        yields ``text_delta`` events followed by a final ``done`` event.
        """
        ...


class OpenAICompatibleProvider:
    """OpenAI-compatible ``/chat/completions`` streaming provider via httpx.

    ``client`` is injectable so tests can pass an ``httpx.AsyncClient`` backed
    by ``httpx.MockTransport`` (no network).  The API key is stored only on the
    client and is never included in yielded events.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self._model = model

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: int,
    ) -> AsyncIterator[LLMEvent]:
        payload: dict[str, Any] = {
            "model": self._model,
            "stream": True,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": max_output_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # DeepSeek's reasoning models (e.g. deepseek-v4-flash) default to
        # "thinking mode": every assistant chunk carries `reasoning_content`,
        # and the NEXT request in a tool-calling round MUST echo it back or
        # DeepSeek rejects the call with HTTP 400 ("The `reasoning_content`
        # in the thinking mode must be passed back to the API."). The pipeline
        # does not preserve that field across rounds, so disable thinking mode
        # entirely — the model then streams plain `content` deltas and
        # tool-call round-trips work. Gated on the model name because other
        # OpenAI-compatible endpoints may reject the unknown `thinking` param.
        if self._model.startswith("deepseek"):
            payload["thinking"] = {"type": "disabled"}

        text_parts: list[str] = []
        pending_tool_calls: dict[int, dict[str, str]] = {}
        emitted_done = False
        emitted_tool_calls = False

        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                timeout=timeout_seconds,
            ) as response:
                if response.status_code >= 400:
                    raise LLMProviderUnavailable(
                        f"LLM provider returned HTTP {response.status_code}."
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: "):]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        # Parity with GeminiProvider: a malformed/truncated
                        # SSE chunk (keep-alive noise, proxy artifacts,
                        # foreign payload) must never crash the stream —
                        # skip it and continue (PROB-28/#52).
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}

                    content = delta.get("content")
                    if content:
                        text_parts.append(content)
                        yield LLMEvent.text_delta(content)

                    for item in delta.get("tool_calls") or []:
                        index = item.get("index", 0)
                        slot = pending_tool_calls.setdefault(
                            index, {"name": "", "arguments": ""}
                        )
                        function = item.get("function") or {}
                        if function.get("name"):
                            slot["name"] = function["name"]
                        if function.get("arguments"):
                            slot["arguments"] += function["arguments"]

                    finish_reason = choice.get("finish_reason")
                    if finish_reason == "tool_calls":
                        for index in sorted(pending_tool_calls):
                            slot = pending_tool_calls[index]
                            try:
                                parsed = (
                                    json.loads(slot["arguments"])
                                    if slot["arguments"]
                                    else {}
                                )
                            except json.JSONDecodeError:
                                parsed = {}
                            yield LLMEvent.tool_call(slot["name"], parsed)
                        pending_tool_calls.clear()
                        emitted_tool_calls = True
                    elif finish_reason in ("stop", "length"):
                        yield LLMEvent.done("".join(text_parts))
                        emitted_done = True
                # Stream ended without an explicit finish_reason (e.g. only the
                # [DONE] marker): still emit whatever text accumulated.  A
                # tool-calling stream must not synthesize a trailing done event.
                if not emitted_done and not emitted_tool_calls and not pending_tool_calls:
                    yield LLMEvent.done("".join(text_parts))
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise LLMProviderUnavailable(
                f"LLM provider request failed: {type(exc).__name__}"
            ) from exc


def _to_gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate the pipeline's OpenAI-shaped messages to Gemini contents.

    Role mapping: ``user`` -> ``user``, ``assistant`` -> ``model``. Assistant
    ``tool_calls`` become ``functionCall`` parts; ``tool`` messages become
    ``functionResponse`` parts (the call id -> tool name mapping is tracked
    while translating). Consecutive same-role contents are merged, because the
    Gemini API rejects back-to-back messages with the same role (the pipeline
    can emit e.g. a tool response followed by the retrieved-context message,
    both ``user``).
    """

    call_names: dict[str, str] = {}
    contents: list[dict[str, Any]] = []

    def _append(role: str, parts: list[dict[str, Any]]) -> None:
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": role, "parts": parts})

    for message in messages:
        role = message.get("role")
        if role == "user":
            content = message.get("content")
            if content:
                _append("user", [{"text": content}])
        elif role == "assistant":
            tool_calls = message.get("tool_calls")
            if tool_calls:
                parts: list[dict[str, Any]] = []
                for call in tool_calls:
                    function = call.get("function") or {}
                    name = function.get("name", "")
                    call_id = call.get("id", "")
                    if call_id:
                        call_names[call_id] = name
                    try:
                        arguments = (
                            json.loads(function.get("arguments") or "{}")
                            if function.get("arguments")
                            else {}
                        )
                    except json.JSONDecodeError:
                        arguments = {}
                    parts.append({"functionCall": {"name": name, "args": arguments}})
                _append("model", parts)
            elif message.get("content"):
                _append("model", [{"text": message["content"]}])
        elif role == "tool":
            name = call_names.get(message.get("tool_call_id", ""), "unknown_tool")
            raw = message.get("content") or "{}"
            try:
                response: Any = json.loads(raw)
            except json.JSONDecodeError:
                response = {"value": raw}
            _append(
                "user",
                [{"functionResponse": {"name": name, "response": {"result": response}}}],
            )
    return contents


class GeminiProvider:
    """Google Gemini REST provider via httpx (v1beta, ``x-goog-api-key``).

    Implements the same :class:`LLMProvider` contract as
    ``OpenAICompatibleProvider`` using the ``:streamGenerateContent?alt=sse``
    streaming endpoint (ai.google.dev/gemini-api/docs). Tool calls round-trip
    through Gemini function calling: assistant ``tool_calls`` become
    ``functionCall`` parts and ``tool`` results become ``functionResponse``
    parts.

    ``client`` is injectable so tests can pass an ``httpx.AsyncClient`` backed
    by ``httpx.MockTransport`` (no network). The API key is stored only on the
    client and never included in yielded events.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://generativelanguage.googleapis.com",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url)
        self._model = model
        # The API key is applied per-request (not on the client) so an
        # injected test client without headers still authenticates.
        self._api_key = api_key

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: int,
    ) -> AsyncIterator[LLMEvent]:
        payload: dict[str, Any] = {
            "contents": _to_gemini_contents(messages),
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if tools:
            # TOOL_SCHEMAS are OpenAI-shaped ({type, function}); Gemini wants
            # functionDeclarations, so unwrap each function object.
            payload["tools"] = [
                {"functionDeclarations": [tool["function"] for tool in tools]}
            ]

        text_parts: list[str] = []
        tool_calls: list[tuple[str, dict[str, Any]]] = []
        emitted = False

        try:
            async with self._client.stream(
                "POST",
                f"/v1beta/models/{self._model}:streamGenerateContent?alt=sse",
                json=payload,
                headers={"x-goog-api-key": self._api_key},
                timeout=timeout_seconds,
            ) as response:
                if response.status_code >= 400:
                    raise LLMProviderUnavailable(
                        f"LLM provider returned HTTP {response.status_code}."
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: "):]
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    candidates = chunk.get("candidates") or []
                    if not candidates:
                        continue
                    candidate = candidates[0]
                    for part in (candidate.get("content") or {}).get("parts") or []:
                        if "text" in part and part["text"]:
                            text_parts.append(part["text"])
                            yield LLMEvent.text_delta(part["text"])
                        elif "functionCall" in part:
                            call = part["functionCall"] or {}
                            tool_calls.append(
                                (call.get("name", ""), call.get("args") or {})
                            )
                    if candidate.get("finishReason"):
                        break

                # Response ended: either a tool round (tool_call events only)
                # or a final text answer (text_delta events + one done event).
                if tool_calls:
                    emitted = True
                    for name, arguments in tool_calls:
                        yield LLMEvent.tool_call(name, arguments)
                else:
                    yield LLMEvent.done("".join(text_parts))
                    emitted = True
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise LLMProviderUnavailable(
                f"LLM provider request failed: {type(exc).__name__}"
            ) from exc


class FakeLLMProvider:
    """Deterministic test double — yields a fixed event sequence per call.

    Never touches the network and never imports an HTTP client.  Every call is
    recorded on ``self.calls`` so tests can assert on the exact prompt/context
    the pipeline assembled (used by the prompt-injection tests).
    """

    def __init__(self, scripted_events: list[LLMEvent] | None = None) -> None:
        self.scripted_events: list[LLMEvent] = list(scripted_events or [])
        self.calls: list[dict[str, Any]] = []

    async def stream_chat(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_output_tokens: int,
        temperature: float,
        timeout_seconds: int,
    ) -> AsyncIterator[LLMEvent]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "messages": messages,
                "tools": tools,
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                "timeout_seconds": timeout_seconds,
            }
        )
        for event in self.scripted_events:
            yield event


# ---------------------------------------------------------------------------
# Error-handler mapping (503, never 401/403)
# ---------------------------------------------------------------------------


def install_llm_error_handlers(app: FastAPI) -> None:
    """Install shared handlers mapping LLM provider failures to HTTP 503.

    Both a disabled provider and an unavailable provider are infrastructure
    failures — never authentication errors (RAG-04).
    """

    async def disabled_handler(
        _request: Request, _exc: LLMProviderDisabled
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "LLM_DISABLED",
                    "message": "The LLM provider is disabled.",
                }
            },
        )

    async def unavailable_handler(
        _request: Request, _exc: LLMProviderUnavailable
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "LLM_PROVIDER_UNAVAILABLE",
                    "message": "The LLM provider is unavailable.",
                }
            },
        )

    app.add_exception_handler(LLMProviderDisabled, disabled_handler)
    app.add_exception_handler(LLMProviderUnavailable, unavailable_handler)
