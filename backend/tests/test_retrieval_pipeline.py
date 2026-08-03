"""Retrieval-pipeline hardening tests (RAG-05, RAG-06, RAG-07, RAG-08).

Covers the context-normalization contract: deduplication by stable ID, the
fixed eight-section rendering order, server-side item/character budget with
direct-evidence prioritization, Unicode-code-point size accounting (Turkish
text), auth/session-field exclusion by construction, and the hard tool-round
ceiling.  Pipeline-level tests use the deterministic FakeLLMProvider and a
stub database — no network, no live graph.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.core.config import get_settings
from backend.app.llm.provider import FakeLLMProvider, LLMEvent
from backend.app.retrieval.pipeline import CONTEXT_SECTIONS, RetrievalPipeline, assemble_context

# The eight documented context sections in their exact documented sequence
# (06-CONTEXT.md RAG-05: series context, current watched boundary, relevant
# entities, relevant relationships, claims, evidence fragments, sources, user
# notes).  chat_history is a trailing ninth section.
DOCUMENTED_SECTIONS = (
    "series_context",
    "boundary",
    "entities",
    "relationships",
    "claims",
    "evidence",
    "sources",
    "notes",
)

CLAIM_C1 = {
    "id": "dexter:claim:s01e01:dexter_debra_family",
    "label": "Dexter and Debra are siblings",
    "subject_id": "dexter:character:dexter_morgan",
    "object_id": "dexter:character:debra_morgan",
    "predicate": "FAMILY_OF",
    "visible_from_order": 1,
    "origin": "canonical",
}
NODE_N1 = {"id": "dexter:character:dexter_morgan", "label": "Dexter Morgan", "type": "Character", "visible_from_order": 1}
NODE_N2 = {"id": "dexter:character:debra_morgan", "label": "Debra Morgan", "type": "Character", "visible_from_order": 1}
EVIDENCE_E1 = {"id": "dexter:evidence:s01e01:01", "label": "S01E01", "text": "Debra calls Dexter her brother.", "visible_from_order": 1}
SOURCE_S1 = {
    "id": "dexter:source:s01e01",
    "label": "S01E01",
    "source_type": "episode_notes",
    "locator": "S01E01",
    "visible_from_order": 1,
}


class _StubProgressService:
    """Duck-typed stand-in for ProgressService — no database access."""

    def __init__(self, boundary: int = 1) -> None:
        self._boundary = boundary

    async def resolve(self, user_id: str, series_id: str) -> int:
        del user_id, series_id
        return self._boundary


class _CallScriptedProvider:
    """Yields a distinct event list per call index (last list repeats)."""

    def __init__(self, per_call: list[list[LLMEvent]]) -> None:
        self.per_call = per_call
        self.calls: list[dict[str, Any]] = []

    async def stream_chat(self, **kwargs: Any):
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.per_call) - 1)
        for event in self.per_call[index]:
            yield event


class _StubDatabase:
    """Canned rows per query intent; records every call for assertions."""

    def __init__(
        self,
        *,
        entity_rows: list[dict[str, Any]] | None = None,
        claim_rows: list[dict[str, Any]] | None = None,
        node_rows: list[dict[str, Any]] | None = None,
        evidence_rows: list[dict[str, Any]] | None = None,
        source_rows: list[dict[str, Any]] | None = None,
        series_rows: list[dict[str, Any]] | None = None,
        search_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._rows = {
            # Routed by distinctive Cypher fragments of the actual query
            # text (constant names never appear in the SQL).  get_entity
            # falls back to node_rows when no entity_rows are supplied —
            # the neighborhood tests provide entities via node_rows.
            "node.id = $entity_id": entity_rows or node_rows or [],
            "claim.claim_type": claim_rows or [],
            "node.id IN $node_ids": node_rows or [],
            "SUPPORTED_BY": evidence_rows or [],
            "REFERS_TO": source_rows or [],
            "episode.id IN $episode_ids": [],
            "series:Series": series_rows or [],
            "toLower(coalesce(node.label": search_rows or [],
        }
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        self.calls.append((query, parameters))
        for fragment, rows in self._rows.items():
            if fragment in query:
                return list(rows)
        return []


def _final_context(provider: Any) -> str:
    """Extract the assembled context from the last recorded provider call."""
    return provider.calls[-1]["messages"][-1]["content"]


# ---------------------------------------------------------------------------
# Deduplication by stable ID
# ---------------------------------------------------------------------------


def test_assemble_context_deduplicates_entities_claims_evidence_by_id() -> None:
    context = assemble_context(
        nodes=[NODE_N1, NODE_N1, NODE_N2],
        claims=[CLAIM_C1, CLAIM_C1],
        evidence=[EVIDENCE_E1, EVIDENCE_E1],
        sources=[SOURCE_S1, SOURCE_S1],
        notes=[],
        history=[],
        max_items=40,
        max_characters=12000,
    )
    # Each stable ID renders exactly once, no matter how many tool calls
    # returned it.
    assert context.count("(dexter:character:dexter_morgan, Character)") == 1
    assert context.count("(dexter:character:debra_morgan, Character)") == 1
    assert context.count("(dexter:claim:s01e01:dexter_debra_family)") == 1
    assert context.count("(dexter:evidence:s01e01:01)") == 1
    assert context.count("(dexter:source:s01e01,") == 1


@pytest.mark.asyncio
async def test_pipeline_deduplicates_overlapping_tool_results() -> None:
    """Two neighborhood calls returning the same claim yield it once."""
    database = _StubDatabase(
        claim_rows=[CLAIM_C1],
        node_rows=[NODE_N1, NODE_N2],
        evidence_rows=[EVIDENCE_E1],
        source_rows=[SOURCE_S1],
    )
    provider = _CallScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N2["id"], "depth": 1})],
            [LLMEvent.done("overlapping neighborhoods deduped")],
        ]
    )
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=1)
    )
    events = [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id="series_dexter",
            chat_session_id="chat-session:test",
            question="Who is Debra?",
            history=[],
            provider=provider,
        )
    ]
    context = _final_context(provider)
    assert context.count("(dexter:claim:s01e01:dexter_debra_family)") == 1
    assert context.count("(dexter:character:dexter_morgan, Character)") == 1
    done_events = [event for event in events if event.kind == "done"]
    assert done_events[0].content == "overlapping neighborhoods deduped"


# ---------------------------------------------------------------------------
# Fixed section order
# ---------------------------------------------------------------------------


def test_context_sections_render_in_fixed_documented_order() -> None:
    context = assemble_context(
        nodes=[NODE_N1],
        claims=[CLAIM_C1],
        evidence=[EVIDENCE_E1],
        sources=[SOURCE_S1],
        notes=[{"id": "user-note:1", "content": "remember this"}],
        history=[{"role": "user", "content": "hi"}],
        edges=[{"id": f"{CLAIM_C1['id']}:edge", "source": NODE_N1["id"], "target": NODE_N2["id"], "type": "FAMILY_OF"}],
        series={"id": "series_dexter", "title": "Dexter"},
        boundary=1,
        max_items=40,
        max_characters=12000,
    )
    # All nine labeled sections (eight documented + chat_history) appear in
    # the documented sequence.
    positions = [context.index(f"<{name}>") for name in CONTEXT_SECTIONS]
    assert positions == sorted(positions)
    documented_positions = [
        context.index(f"<{name}>") for name in DOCUMENTED_SECTIONS
    ]
    assert documented_positions == sorted(documented_positions)
    assert context.index("<chat_history>") > context.index("</notes>")


def test_series_context_and_boundary_sections_render_values() -> None:
    context = assemble_context(
        nodes=[],
        claims=[],
        evidence=[],
        sources=[],
        notes=[],
        history=[],
        series={"id": "series_dexter", "title": "Dexter"},
        boundary=3,
        max_items=40,
        max_characters=12000,
    )
    assert "Dexter (series_dexter)" in context
    assert context.index("</series_context>") < context.index("<boundary>")
    assert "- 3" in context


# ---------------------------------------------------------------------------
# Item budget: direct evidence before distant neighborhood results
# ---------------------------------------------------------------------------


def test_context_item_budget_prefers_direct_evidence() -> None:
    context = assemble_context(
        nodes=[],
        claims=[],
        evidence=[
            {"id": "e-distant", "label": "far", "text": "distant", "distance": 2},
            {"id": "e-direct", "label": "near", "text": "direct", "distance": 0},
            {"id": "e-mid", "label": "middle", "text": "middle", "distance": 1},
        ],
        sources=[],
        notes=[],
        history=[],
        max_items=1,
        max_characters=12000,
    )
    # With a budget of one, only the direct evidence survives — distant
    # neighborhood results are trimmed first.
    assert "(e-direct)" in context
    assert "(e-mid)" not in context
    assert "(e-distant)" not in context


def test_context_direct_results_precede_distant_ones_within_section() -> None:
    context = assemble_context(
        nodes=[
            {"id": "n-distant", "label": "far", "type": "Character", "distance": 2},
            {"id": "n-direct", "label": "near", "type": "Character", "distance": 0},
            {"id": "n-mid", "label": "middle", "type": "Character", "distance": 1},
        ],
        claims=[],
        evidence=[],
        sources=[],
        notes=[],
        history=[],
        max_items=40,
        max_characters=12000,
    )
    assert context.index("(n-direct") < context.index("(n-mid")
    assert context.index("(n-mid") < context.index("(n-distant")


# ---------------------------------------------------------------------------
# Character budget: Unicode code points (Turkish text)
# ---------------------------------------------------------------------------


def test_context_character_budget_measured_in_unicode_code_points() -> None:
    """Truncation is by Python ``len()`` — code points, never bytes.

    A byte-oriented truncation would split multi-byte characters; the
    truncated output must equal the code-point slice of the full context.
    """
    turkish_evidence = (
        "İstanbul'da ıslak bir akşam Dexter kanıtları inceliyor ve "
        "Debra'ya 'ıslak iş' diyor."
    )
    full = assemble_context(
        nodes=[],
        claims=[],
        evidence=[
            {"id": "e-tr", "label": "Kanıt", "text": turkish_evidence},
            {"id": "e-tr2", "label": "Kanıt", "text": turkish_evidence},
        ],
        sources=[],
        notes=[],
        history=[],
        max_items=40,
        max_characters=0,  # 0 disables truncation — build the full context
    )
    # Cut in the middle of a Turkish word (right after an "ı").
    cut = full.index("ıslak") + 3
    truncated = assemble_context(
        nodes=[],
        claims=[],
        evidence=[
            {"id": "e-tr", "label": "Kanıt", "text": turkish_evidence},
            {"id": "e-tr2", "label": "Kanıt", "text": turkish_evidence},
        ],
        sources=[],
        notes=[],
        history=[],
        max_items=40,
        max_characters=cut,
    )
    assert len(truncated) == cut
    assert truncated == full[:cut]
    # The truncated text round-trips through UTF-8 — no split code points.
    assert truncated.encode("utf-8").decode("utf-8") == truncated
    assert "İ" in full and "ı" in full


# ---------------------------------------------------------------------------
# Empty/whitespace-only text fields
# ---------------------------------------------------------------------------


def test_empty_or_whitespace_note_evidence_claim_render_without_error() -> None:
    context = assemble_context(
        nodes=[],
        claims=[
            {
                "id": "dexter:claim:empty-label",
                "label": "",
                "subject_id": NODE_N1["id"],
                "predicate": "KNOWS",
                "object_id": NODE_N2["id"],
            }
        ],
        evidence=[{"id": "dexter:evidence:empty-text", "label": "S01E01", "text": ""}],
        sources=[],
        notes=[{"id": "user-note:ws", "content": "   "}],
        history=[],
        max_items=40,
        max_characters=12000,
    )
    # Every section still renders as a framed block — never omitted, never
    # raising on empty/whitespace text.
    assert "<claims>" in context and "</claims>" in context
    assert "<evidence>" in context and "</evidence>" in context
    assert "<notes>" in context and "</notes>" in context
    assert "dexter:claim:empty-label" in context
    assert "dexter:evidence:empty-text" in context


# ---------------------------------------------------------------------------
# Auth/session data excluded by construction
# ---------------------------------------------------------------------------


def test_assemble_context_never_renders_auth_or_session_fields() -> None:
    context = assemble_context(
        nodes=[
            {
                "id": "dexter:character:dexter_morgan",
                "label": "Dexter Morgan",
                "type": "Character",
                "user_id": "user:secret",
                "session_id": "session:secret",
                "auth_token": "token:secret",
            }
        ],
        claims=[],
        evidence=[],
        sources=[],
        notes=[],
        history=[
            {"role": "user", "content": "hi", "user_id": "user:secret2", "session_id": "session:secret2"}
        ],
        max_items=40,
        max_characters=12000,
    )
    for secret in (
        "user:secret",
        "session:secret",
        "token:secret",
        "user:secret2",
        "session:secret2",
    ):
        assert secret not in context


@pytest.mark.asyncio
async def test_pipeline_context_excludes_auth_and_session_data() -> None:
    database = _StubDatabase(
        entity_rows=[
            {
                "id": NODE_N1["id"],
                "type": "Character",
                "label": "Dexter Morgan",
                "visible_from_order": 1,
                "origin": "canonical",
                "user_id": "user:leak",
                "session_id": "session:leak",
            }
        ]
    )
    provider = _CallScriptedProvider(
        [
            [LLMEvent.tool_call("get_entity", {"entity_id": NODE_N1["id"]})],
            [LLMEvent.done("answer")],
        ]
    )
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=1)
    )
    _ = [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id="series_dexter",
            chat_session_id="chat-session:test",
            question="Who is Dexter?",
            history=[{"role": "user", "content": "hi", "session_id": "session:leak2"}],
            provider=provider,
        )
    ]
    context = _final_context(provider)
    assert "user:leak" not in context
    assert "session:leak" not in context
    assert "session:leak2" not in context


# ---------------------------------------------------------------------------
# Tool-round ceiling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_rounds_stop_exactly_at_ceiling_and_final_answer_produced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_max_tool_rounds", 3)

    database = _StubDatabase()  # every tool call resolves to nothing
    provider = _CallScriptedProvider(
        [
            [LLMEvent.tool_call("get_entity", {"entity_id": "dexter:character:x1"})],
            [LLMEvent.tool_call("get_entity", {"entity_id": "dexter:character:x2"})],
            [LLMEvent.tool_call("get_entity", {"entity_id": "dexter:character:x3"})],
            [LLMEvent.done("final answer produced after the round ceiling")],
        ]
    )
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=1)
    )
    events = [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id="series_dexter",
            chat_session_id="chat-session:test",
            question="Keep calling tools.",
            history=[],
            provider=provider,
        )
    ]
    # Exactly llm_max_tool_rounds tool rounds + one final no-tools call.
    assert len(provider.calls) == 4
    assert provider.calls[-1]["tools"] == []
    done_events = [event for event in events if event.kind == "done"]
    assert len(done_events) == 1
    assert done_events[0].content == "final answer produced after the round ceiling"


def test_assemble_context_drops_above_boundary_or_missing_visibility_items() -> None:
    """07-04 defense-in-depth (D-03 fail-closed): assemble_context never
    renders an item whose visible_from_order is missing or above the
    boundary, even if the queries upstream were bypassed."""
    context = assemble_context(
        nodes=[NODE_N1, {"id": "hidden:node", "label": "Hidden", "type": "Character", "visible_from_order": 99}],
        claims=[
            CLAIM_C1,
            {"id": "hidden:claim", "label": "Hidden", "visible_from_order": 99},
            {"id": "null:claim", "label": "Hidden", "visible_from_order": None},
        ],
        evidence=[EVIDENCE_E1, {"id": "hidden:evidence", "label": "S01E02", "text": "leak", "visible_from_order": 99}],
        sources=[SOURCE_S1, {"id": "hidden:source", "label": "S01E03", "locator": "S01E03", "visible_from_order": 99}],
        notes=[{"id": "note:1", "content": "safe", "visible_from_order": 1}, {"id": "note:hidden", "content": "leak", "visible_from_order": 99}],
        history=[],
        series={"id": "series_dexter", "title": "Dexter"},
        boundary=1,
        max_items=40,
        max_characters=12000,
    )
    assert "Dexter Morgan" in context
    assert "Debra calls Dexter her brother." in context
    assert "Hidden" not in context
    assert "leak" not in context
    assert "safe" in context


# ---------------------------------------------------------------------------
# 07-05 D-15: search results assembled into context contain no hidden entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_search_context_contains_no_hidden_entity() -> None:
    """07-05 D-15: context assembled from search results contains no hidden
    entity line.

    ``search_entities`` returns only boundary-visible rows; the assembled
    context additionally drops any row whose ``visible_from_order`` is
    missing or above the boundary (defense in depth), so a hidden entity can
    never reach the provider call through the search channel.
    """
    database = _StubDatabase(
        search_rows=[
            {
                "id": "dexter:character:dexter_morgan",
                "type": "Character",
                "label": "Dexter Morgan",
                "visible_from_order": 1,
                "origin": "canonical",
            },
            {
                "id": "dexter:character:harry_morgan",
                "type": "Character",
                "label": "Harry Morgan",
                "visible_from_order": 3,
                "origin": "canonical",
            },
        ]
    )
    provider = _CallScriptedProvider(
        [
            [LLMEvent.tool_call("search_entities", {"query": "morgan"})],
            [LLMEvent.done("search answered")],
        ]
    )
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=1)
    )
    events = [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id="series_dexter",
            chat_session_id="chat-session:test",
            question="Who is in the visible graph?",
            history=[],
            provider=provider,
        )
    ]
    context = _final_context(provider)
    # The visible search hit is assembled into the entities section…
    assert "Dexter Morgan" in context
    # …and the hidden search hit (visible_from_order 3 > boundary 1) is not.
    assert "Harry Morgan" not in context
    done_events = [event for event in events if event.kind == "done"]
    assert done_events[0].content == "search answered"
