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
