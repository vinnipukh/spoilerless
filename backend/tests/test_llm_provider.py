"""Unit tests for the LLM provider abstraction (RAG-04).

Covers: deterministic FakeLLMProvider with zero network usage, OpenAI-compatible
SSE streaming (text deltas, tool-call accumulation, [DONE] handling), provider
failure mapping (timeout / non-2xx / connection error -> LLMProviderUnavailable),
and the 503 error-handler mapping (never 401/403).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.errors import install_database_error_handlers
from backend.app.llm.provider import (
    FakeLLMProvider,
    GeminiProvider,
    LLMEvent,
    LLMProviderDisabled,
    LLMProviderUnavailable,
    OpenAICompatibleProvider,
    install_llm_error_handlers,
)


def _sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload)}"


def _chunk(delta: dict, finish_reason: str | None = None) -> dict:
    choice: dict = {"index": 0, "delta": delta}
    if finish_reason:
        choice["finish_reason"] = finish_reason
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "model": "test-model",
        "choices": [choice],
    }


def _transport(*events: dict) -> httpx.MockTransport:
    body = "\n\n".join(_sse_line(event) for event in events) + "\n\ndata: [DONE]\n\n"
    return httpx.MockTransport(lambda request: httpx.Response(200, text=body))


def _provider(transport: httpx.MockTransport) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://llm.test",
        api_key="test-secret-key",
        model="test-model",
        client=httpx.AsyncClient(transport=transport, base_url="https://llm.test"),
    )


def _stream_kwargs() -> dict:
    return {
        "system_prompt": "system",
        "messages": [{"role": "user", "content": "question"}],
        "tools": [],
        "max_output_tokens": 100,
        "temperature": 0.0,
        "timeout_seconds": 5,
    }


# ---------------------------------------------------------------------------
# FakeLLMProvider — deterministic, zero network
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fake_provider_yields_scripted_events_and_records_calls() -> None:
    scripted = [
        LLMEvent.text_delta("Dexter "),
        LLMEvent.tool_call("get_neighborhood", {"entity_id": "dexter:character:dexter_morgan", "depth": 1}),
        LLMEvent.done(
            "Dexter and Debra are siblings.",
            citations=[{"claim_id": "dexter:claim:s01e01:dexter_debra_family"}],
        ),
    ]
    provider = FakeLLMProvider(scripted_events=scripted)

    collected = [event async for event in provider.stream_chat(**_stream_kwargs())]

    assert collected == scripted
    assert len(provider.calls) == 1
    assert provider.calls[0]["system_prompt"] == "system"
    assert provider.calls[0]["messages"][0]["content"] == "question"


@pytest.mark.asyncio
async def test_fake_provider_empty_script_yields_nothing() -> None:
    provider = FakeLLMProvider(scripted_events=[])
    collected = [event async for event in provider.stream_chat(**_stream_kwargs())]
    assert collected == []


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider — SSE streaming over httpx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_provider_streams_text_deltas_then_done() -> None:
    provider = _provider(
        _transport(
            _chunk({"content": "Dexter "}),
            _chunk({"content": "works with Batista."}),
            _chunk({}, finish_reason="stop"),
        )
    )

    events = [event async for event in provider.stream_chat(**_stream_kwargs())]

    assert [event.kind for event in events] == ["text_delta", "text_delta", "done"]
    assert events[0].text == "Dexter "
    assert events[1].text == "works with Batista."
    assert events[-1].content == "Dexter works with Batista."


@pytest.mark.asyncio
async def test_openai_provider_accumulates_streamed_tool_call_arguments() -> None:
    provider = _provider(
        _transport(
            _chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_neighborhood",
                                "arguments": '{"entity_id": "dexter:character:dexter_morgan"',
                            },
                        }
                    ]
                }
            ),
            _chunk(
                {
                    "tool_calls": [
                        {"index": 0, "function": {"arguments": ', "depth": 1}'}}
                    ]
                }
            ),
            _chunk({}, finish_reason="tool_calls"),
        )
    )

    events = [event async for event in provider.stream_chat(**_stream_kwargs())]

    assert [event.kind for event in events] == ["tool_call"]
    tool_call = events[0]
    assert tool_call.tool_name == "get_neighborhood"
    assert tool_call.arguments == {
        "entity_id": "dexter:character:dexter_morgan",
        "depth": 1,
    }


@pytest.mark.asyncio
async def test_openai_provider_handles_done_marker_without_event() -> None:
    provider = _provider(_transport(_chunk({"content": "ok"}, finish_reason="stop")))
    events = [event async for event in provider.stream_chat(**_stream_kwargs())]
    assert events[-1].kind == "done"
    assert events[-1].content == "ok"


@pytest.mark.asyncio
async def test_openai_provider_non_2xx_raises_unavailable() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="boom"))
    provider = _provider(transport)

    with pytest.raises(LLMProviderUnavailable):
        _ = [event async for event in provider.stream_chat(**_stream_kwargs())]


@pytest.mark.asyncio
async def test_openai_provider_connection_error_raises_unavailable() -> None:
    def _refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider(httpx.MockTransport(_refuse))

    with pytest.raises(LLMProviderUnavailable):
        _ = [event async for event in provider.stream_chat(**_stream_kwargs())]


@pytest.mark.asyncio
async def test_openai_provider_timeout_raises_unavailable() -> None:
    async def _slow(request: httpx.Request) -> httpx.Response:
        # MockTransport handlers bypass httpx timeout enforcement, so raise
        # the transport-level timeout directly — this exercises the provider's
        # exception mapping (httpx.TimeoutException -> LLMProviderUnavailable).
        raise httpx.ReadTimeout("simulated read timeout", request=request)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_slow), timeout=0.05, base_url="https://llm.test"
    )
    provider = OpenAICompatibleProvider(
        base_url="https://llm.test", api_key="k", model="m", client=client
    )

    with pytest.raises(LLMProviderUnavailable):
        _ = [
            event
            async for event in provider.stream_chat(
                **{**_stream_kwargs(), "timeout_seconds": 0.05}
            )
        ]


@pytest.mark.asyncio
async def test_openai_provider_never_exposes_api_key_in_events() -> None:
    provider = _provider(_transport(_chunk({"content": "answer"}, finish_reason="stop")))
    events = [event async for event in provider.stream_chat(**_stream_kwargs())]
    serialized = json.dumps([event.model_dump() for event in events])
    assert "test-secret-key" not in serialized


# ---------------------------------------------------------------------------
# Error-handler mapping — 503, never 401/403
# ---------------------------------------------------------------------------


def test_llm_error_handlers_map_to_503_with_distinct_codes() -> None:
    app = FastAPI()
    install_database_error_handlers(app)
    install_llm_error_handlers(app)

    @app.get("/disabled")
    async def disabled() -> None:
        raise LLMProviderDisabled("LLM is disabled.")

    @app.get("/unavailable")
    async def unavailable() -> None:
        raise LLMProviderUnavailable("provider timeout")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/disabled")
    assert response.status_code == 503
    assert response.json() == {
        "detail": {"code": "LLM_DISABLED", "message": "The LLM provider is disabled."}
    }

    response = client.get("/unavailable")
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "LLM_PROVIDER_UNAVAILABLE",
            "message": "The LLM provider is unavailable.",
        }
    }


# ---------------------------------------------------------------------------
# GeminiProvider — v1beta REST, SSE streaming, function calling
# ---------------------------------------------------------------------------


def _gemini_sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload)}"


def _gemini_text_chunk(text: str, finish: str | None = "STOP") -> dict:
    chunk: dict = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    if finish:
        chunk["candidates"][0]["finishReason"] = finish
    return chunk


def _gemini_tool_chunk(name: str, args: dict) -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"functionCall": {"name": name, "args": args}}]},
                "finishReason": "STOP",
            }
        ]
    }


def _gemini_transport(*events: dict) -> httpx.MockTransport:
    body = "\n\n".join(_gemini_sse_line(event) for event in events) + "\n\n"
    return httpx.MockTransport(lambda request: httpx.Response(200, text=body))


def _gemini_provider(transport: httpx.MockTransport) -> GeminiProvider:
    return GeminiProvider(
        api_key="test-gemini-key",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.test",
        client=httpx.AsyncClient(transport=transport, base_url="https://generativelanguage.test"),
    )


def _captured_request(transport: httpx.MockTransport) -> dict:
    requests = transport.handler.calls if hasattr(transport.handler, "calls") else []
    if requests:
        return json.loads(requests[0].request.content)
    return {}


@pytest.mark.asyncio
async def test_openai_provider_deepseek_model_disables_thinking_mode() -> None:
    """DeepSeek reasoning models 400 on tool-call round-trips unless thinking
    mode is disabled (the pipeline cannot echo `reasoning_content` back)."""
    recorded: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, text="")

    provider = OpenAICompatibleProvider(
        base_url="https://api.deepseek.test",
        api_key="test-secret-key",
        model="deepseek-v4-flash",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url="https://api.deepseek.test"),
    )
    try:
        [event async for event in provider.stream_chat(**_stream_kwargs())]
    except Exception:
        pass  # empty transport response — we only inspect the request payload

    payload = json.loads(recorded[0].content)
    assert payload["thinking"] == {"type": "disabled"}


@pytest.mark.asyncio
async def test_openai_provider_non_deepseek_model_has_no_thinking_param() -> None:
    recorded: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, text="")

    provider = OpenAICompatibleProvider(
        base_url="https://llm.test",
        api_key="test-secret-key",
        model="gpt-4.1-mini",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url="https://llm.test"),
    )
    try:
        [event async for event in provider.stream_chat(**_stream_kwargs())]
    except Exception:
        pass

    payload = json.loads(recorded[0].content)
    assert "thinking" not in payload


@pytest.mark.asyncio
async def test_gemini_provider_streams_text_deltas_then_done() -> None:
    transport = _gemini_transport(
        _gemini_text_chunk("Dexter ", finish=None),
        _gemini_text_chunk("Morgan", finish="STOP"),
    )
    provider = _gemini_provider(transport)

    events = [event async for event in provider.stream_chat(**_stream_kwargs())]

    assert [event.kind for event in events] == ["text_delta", "text_delta", "done"]
    assert events[0].text == "Dexter "
    assert events[2].content == "Dexter Morgan"


@pytest.mark.asyncio
async def test_gemini_provider_yields_tool_calls_without_done() -> None:
    transport = _gemini_transport(
        _gemini_tool_chunk("get_entity", {"entity_id": "dexter:character:dexter_morgan"})
    )
    provider = _gemini_provider(transport)

    events = [event async for event in provider.stream_chat(**_stream_kwargs())]

    assert [event.kind for event in events] == ["tool_call"]
    assert events[0].tool_name == "get_entity"
    assert events[0].arguments == {"entity_id": "dexter:character:dexter_morgan"}


@pytest.mark.asyncio
async def test_gemini_provider_translates_messages_and_tools_in_payload() -> None:
    recorded: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return httpx.Response(200, text="")

    provider = _gemini_provider(httpx.MockTransport(_handler))
    messages = [
        {"role": "user", "content": "Who is Dexter?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_entity", "arguments": '{"entity_id": "dexter:character:dexter_morgan"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"label": "Dexter Morgan"}'},
        {"role": "user", "content": "Retrieved graph context for this question..."},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_entity",
                "description": "Resolve one entity",
                "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}},
            },
        }
    ]

    try:
        [event async for event in provider.stream_chat(
            system_prompt="sys",
            messages=messages,
            tools=tools,
            max_output_tokens=100,
            temperature=0.0,
            timeout_seconds=5,
        )]
    except Exception:
        pass  # empty transport response — we only inspect the request payload

    request = recorded[0]
    payload = json.loads(request.content)
    assert request.headers["x-goog-api-key"] == "test-gemini-key"
    assert payload["systemInstruction"] == {"parts": [{"text": "sys"}]}
    assert payload["tools"] == [
        {
            "functionDeclarations": [
                {
                    "name": "get_entity",
                    "description": "Resolve one entity",
                    "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}},
                }
            ]
        }
    ]
    contents = payload["contents"]
    assert contents[0] == {"role": "user", "parts": [{"text": "Who is Dexter?"}]}
    assert contents[1] == {
        "role": "model",
        "parts": [
            {"functionCall": {"name": "get_entity", "args": {"entity_id": "dexter:character:dexter_morgan"}}}
        ],
    }
    # The tool response and the following user context message are BOTH role
    # "user" — they must be merged into one content, not sent back-to-back
    # (Gemini rejects consecutive same-role contents).
    assert len(contents) == 3
    assert contents[2]["role"] == "user"
    assert len(contents[2]["parts"]) == 2
    assert contents[2]["parts"][0]["functionResponse"]["name"] == "get_entity"
    assert contents[2]["parts"][0]["functionResponse"]["response"] == {
        "result": {"label": "Dexter Morgan"}
    }
    assert contents[2]["parts"][1]["text"] == "Retrieved graph context for this question..."


@pytest.mark.asyncio
async def test_gemini_provider_maps_non_2xx_to_unavailable() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(400, text='{"error": "invalid api key"}')
    )
    provider = _gemini_provider(transport)

    with pytest.raises(LLMProviderUnavailable):
        [event async for event in provider.stream_chat(**_stream_kwargs())]
