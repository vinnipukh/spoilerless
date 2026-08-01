"""Conversational-tone policy tests (product brief: friendly, grounded,
spoiler-safe interpretation instead of the robotic insufficient-information
refusal).

Covers the brief's §9 scenarios that were not already covered by the existing
spoiler/citation regressions: a future-looking question with visible context
must NOT short-circuit to the fallback, the provider must receive the visible
recent events and claims, the localized fallback must follow the user's
language (EN/TR), and the new bounded ``get_character_context`` tool must
deliver only visible material.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.llm.fallbacks import (
    DEFAULT_FALLBACKS,
    detect_language,
    INSUFFICIENT_EVIDENCE_FALLBACK_EN,
    INSUFFICIENT_EVIDENCE_FALLBACK_TR,
)
from backend.app.llm.provider import LLMEvent
from backend.app.retrieval.pipeline import RetrievalPipeline

SERIES_ID = "series_dexter"
NODE_DEXTER = {"id": "dexter:character:dexter_morgan", "label": "Dexter Morgan", "type": "Character"}
NODE_DEBRA = {"id": "dexter:character:debra_morgan", "label": "Debra Morgan", "type": "Character"}
EVENT_ICE_TRUCK = {
    "id": "dexter:event:s01e01_ice_truck_case",
    "label": "Ice-truck case begins",
    "type": "Event",
    "visible_from_order": 1,
}
CLAIM_C1 = {
    "id": "dexter:claim:s01e01:dexter_debra_family",
    "label": "Dexter and Debra are siblings",
    "subject_id": NODE_DEXTER["id"],
    "object_id": NODE_DEBRA["id"],
    "predicate": "FAMILY_OF",
    "visible_from_order": 1,
    "origin": "canonical",
}
EVIDENCE_E1 = {"id": "dexter:evidence:s01e01:01", "label": "S01E01", "text": "Debra calls Dexter her brother."}
SOURCE_S1 = {
    "id": "dexter:source:s01e01",
    "label": "S01E01",
    "source_type": "episode_notes",
    "locator": "S01E01",
}


class _StubProgressService:
    def __init__(self, boundary: int = 1) -> None:
        self._boundary = boundary

    async def resolve(self, user_id: str, series_id: str) -> int:
        del user_id, series_id
        return self._boundary


class _ScriptedDatabase:
    """Minimal fail-closed DB stub mirroring test_citations.py's harness."""

    def __init__(
        self,
        *,
        entity_rows: list[dict[str, Any]] | None = None,
        claim_rows: list[dict[str, Any]] | None = None,
        node_rows: list[dict[str, Any]] | None = None,
        evidence_rows: list[dict[str, Any]] | None = None,
        source_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.entity_rows = entity_rows or []
        self.claim_rows = claim_rows or []
        self.node_rows = node_rows or []
        self.evidence_rows = evidence_rows or []
        self.source_rows = source_rows or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        self.calls.append((query, parameters))
        if "node.id = $entity_id" in query:
            return [
                row
                for row in self.entity_rows
                if row.get("visible_from_order", 1) <= parameters.get("visible_until_order", 0)
            ]
        if "claim.claim_type" in query:
            return list(self.claim_rows)
        if "node.id IN $node_ids" in query:
            return list(self.node_rows)
        if "SUPPORTED_BY" in query:
            return list(self.evidence_rows)
        if "REFERS_TO" in query:
            return list(self.source_rows)
        if "episode.id IN $episode_ids" in query:
            return []
        return []


class _ScriptedProvider:
    def __init__(self, per_call: list[list[LLMEvent]]) -> None:
        self.per_call = per_call
        self.calls: list[dict[str, Any]] = []

    async def stream_chat(self, **kwargs: Any):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.per_call) - 1)
        for event in self.per_call[index]:
            yield event


async def _run_pipeline(
    *,
    database: _ScriptedDatabase,
    provider: _ScriptedProvider,
    question: str,
    boundary: int = 1,
    prompt_language: str = "english",
) -> list[LLMEvent]:
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=boundary)
    )
    return [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id=SERIES_ID,
            chat_session_id="chat-session:test",
            question=question,
            history=[],
            provider=provider,
            prompt_language=prompt_language,
        )
    ]


def _final_done(events: list[LLMEvent]) -> LLMEvent:
    done_events = [event for event in events if event.kind == "done"]
    assert len(done_events) == 1
    return done_events[0]


# ---------------------------------------------------------------------------
# Language detection and fallback selection
# ---------------------------------------------------------------------------


def test_detect_language_english() -> None:
    assert detect_language("How do you feel about Dexter's future?") == "en"
    assert detect_language("Why does Doakes distrust Dexter?") == "en"


def test_detect_language_turkish() -> None:
    assert detect_language("Sence Dexter'ın işleri iyiye mi kötüye mi gidiyor?") == "tr"
    assert detect_language("Doakes neden Dexter'a güvenmiyor olabilir?") == "tr"


def test_fallback_templates_are_friendly_and_localized() -> None:
    # Never the old robotic phrasing, in either language.
    assert "watched graph" not in INSUFFICIENT_EVIDENCE_FALLBACK_EN
    assert "watched graph" not in INSUFFICIENT_EVIDENCE_FALLBACK_TR
    assert DEFAULT_FALLBACKS["en"] == INSUFFICIENT_EVIDENCE_FALLBACK_EN
    assert DEFAULT_FALLBACKS["tr"] == INSUFFICIENT_EVIDENCE_FALLBACK_TR
    assert DEFAULT_FALLBACKS["en"] != DEFAULT_FALLBACKS["tr"]


# ---------------------------------------------------------------------------
# Future-looking question WITH visible context: no robotic refusal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_future_question_with_context_does_not_short_circuit_to_fallback() -> None:
    """The model may answer a future-looking question from visible clues —
    the pipeline must not replace its answer with the fallback, and the final
    call must carry the visible events and claims."""
    database = _ScriptedDatabase(
        entity_rows=[NODE_DEXTER | {"visible_from_order": 1, "origin": "canonical"}],
        claim_rows=[CLAIM_C1],
        node_rows=[NODE_DEXTER, NODE_DEBRA, EVENT_ICE_TRUCK],
        evidence_rows=[EVIDENCE_E1],
        source_rows=[SOURCE_S1],
    )
    provider = _ScriptedProvider(
        [
            # Round 1: model calls the interpretation-pack tool.
            [
                LLMEvent.tool_call(
                    "get_character_context",
                    {"character_id": NODE_DEXTER["id"]},
                )
            ],
            # Round 2 (final): a grounded interpretive answer with one valid citation.
            [
                LLMEvent.done(
                    "Based on what we have seen so far, I would not expect "
                    "everything to remain simple. His controlled relationships "
                    "suggest the pressure is growing.",
                    citations=[
                        {"claim_id": CLAIM_C1["id"]},
                    ],
                )
            ],
        ]
    )

    events = await _run_pipeline(
        database=database,
        provider=provider,
        question="How do you feel about Dexter's future?",
    )
    done = _final_done(events)

    # The interpretive answer passes through — never replaced by a fallback.
    assert "I would not expect everything to remain simple" in done.content
    assert done.content != DEFAULT_FALLBACKS["en"]
    assert done.content != DEFAULT_FALLBACKS["tr"]

    # The final call's context carries the visible event and claim.
    final_messages = provider.calls[-1]["messages"]
    final_context = "\n".join(m.get("content") or "" for m in final_messages)
    assert "Ice-truck case begins" in final_context
    assert "Dexter and Debra are siblings" in final_context

    # The tool round received the interpretation pack (recent events present).
    tool_result = "\n".join(
        m.get("content") or ""
        for m in provider.calls[0]["messages"]
        if m.get("role") == "tool"
    )
    assert "recent_events" in tool_result
    assert "Ice-truck case begins" in tool_result

    # The validated citation survived.
    assert [c["claim_id"] for c in done.citations] == [CLAIM_C1["id"]]


# ---------------------------------------------------------------------------
# No useful context: friendly localized fallback, never fabrication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_future_question_without_context_returns_friendly_english_fallback() -> None:
    database = _ScriptedDatabase()  # nothing retrieved
    provider = _ScriptedProvider(
        [
            # Round 1: the model answers immediately, no tool calls, no citation.
            [LLMEvent.done("")],
        ]
    )

    done = _final_done(
        await _run_pipeline(
            database=database,
            provider=provider,
            question="How do you feel about Dexter's future?",
        )
    )

    assert done.content == DEFAULT_FALLBACKS["en"]
    assert "watched graph" not in done.content


@pytest.mark.asyncio
async def test_turkish_question_gets_turkish_fallback() -> None:
    database = _ScriptedDatabase()
    provider = _ScriptedProvider([[LLMEvent.done("")]])

    # The fallback follows the SELECTED prompt language (Settings "Assistant
    # language"), not the question heuristic: a Turkish prompt means the
    # fallback is Turkish even when the stored question is not.
    events = await _run_pipeline(
        database=database,
        provider=provider,
        question="What do you think will happen next?",
        prompt_language="turkish",
    )
    done = _final_done(events)

    assert done.content == DEFAULT_FALLBACKS["tr"]
    assert "watched graph" not in done.content


@pytest.mark.asyncio
async def test_english_question_gets_english_fallback() -> None:
    database = _ScriptedDatabase()
    provider = _ScriptedProvider([[LLMEvent.done("")]])

    done = _final_done(
        await _run_pipeline(
            database=database,
            provider=provider,
            question="Why does Doakes distrust Dexter?",
        )
    )

    assert done.content == DEFAULT_FALLBACKS["en"]
    assert done.content != DEFAULT_FALLBACKS["tr"]


# ---------------------------------------------------------------------------
# Language selection: the Settings choice picks the system prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_english_prompt_is_sent_by_default() -> None:
    database = _ScriptedDatabase()
    provider = _ScriptedProvider([[LLMEvent.done("Hello!")]])

    await _run_pipeline(
        database=database,
        provider=provider,
        question="How do you feel about Dexter's future?",
    )

    for call in provider.calls:
        prompt = call["system_prompt"]
        assert "Always respond in English" in prompt
        assert "Her zaman Türkçe cevap ver" not in prompt
        # The security framing is always appended.
        assert "<series_context>" in prompt


@pytest.mark.asyncio
async def test_turkish_prompt_is_sent_when_selected() -> None:
    database = _ScriptedDatabase()
    provider = _ScriptedProvider([[LLMEvent.done("Merhaba!")]])

    await _run_pipeline(
        database=database,
        provider=provider,
        question="Dexter hakkında ne düşünüyorsun?",
        prompt_language="turkish",
    )

    for call in provider.calls:
        prompt = call["system_prompt"]
        assert "Her zaman Türkçe cevap ver" in prompt
        assert "Always respond in English" not in prompt
        assert "<series_context>" in prompt


# ---------------------------------------------------------------------------
# get_character_context tool: bounded, visibility-filtered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_character_context_tool_hidden_character_fails_closed() -> None:
    """A hidden character yields an empty interpretation pack — no existence
    leak, no hidden events (RAG-01 fail-closed)."""
    database = _ScriptedDatabase(entity_rows=[])  # hidden/nonexistent character
    provider = _ScriptedProvider(
        [
            [LLMEvent.tool_call("get_character_context", {"character_id": "dexter:character:hidden"})],
            [LLMEvent.done("", citations=[])],
        ]
    )

    done = _final_done(
        await _run_pipeline(
            database=database,
            provider=provider,
            question="What do you think will happen to this character?",
        )
    )

    assert done.content == DEFAULT_FALLBACKS["en"]
    # The tool result contains no events for the hidden character.
    tool_result = "\n".join(
        m.get("content") or ""
        for m in provider.calls[0]["messages"]
        if m.get("role") == "tool"
    )
    assert '"recent_events": []' in tool_result
