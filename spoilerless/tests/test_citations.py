"""Citation-validation hardening tests (RAG-07, RAG-08 / T-06-09).

The citation validator must reject any model-scripted citation that does not
reference this turn's actually-retrieved claim/evidence/source IDs — including
real-and-visible-but-never-retrieved-this-turn IDs (06-RESEARCH.md Pitfall 3),
not just hidden IDs.  When every citation is stripped, the pipeline answers
with the fixed ``INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE`` — a deterministic
uncertainty string that is byte-identical whether the queried entity does not
exist anywhere, exists but is hidden, is exactly one episode-order beyond the
boundary, or is many orders beyond: no existence leak, no distance leak, no
"you haven't met them yet" phrasing.
"""

from __future__ import annotations

from typing import Any

import pytest

from spoilerless.app.llm.provider import LLMEvent
from spoilerless.app.retrieval import pipeline as pipeline_module
from spoilerless.app.retrieval.pipeline import RetrievalPipeline

SERIES_ID = "series_dexter"
NODE_N1 = {"id": "dexter:character:dexter_morgan", "label": "Dexter Morgan", "type": "Character"}
NODE_N2 = {"id": "dexter:character:debra_morgan", "label": "Debra Morgan", "type": "Character"}
CLAIM_C1 = {
    "id": "dexter:claim:s01e01:dexter_debra_family",
    "label": "Dexter and Debra are siblings",
    "subject_id": NODE_N1["id"],
    "object_id": NODE_N2["id"],
    "predicate": "FAMILY_OF",
    "visible_from_order": 1,
    "origin": "canonical",
}
# A real, visible claim that exists in the graph but is NOT part of this
# turn's retrieved neighborhood (it touches nodes outside the frontier).
CLAIM_C2_REAL_UNRETRIEVED = {
    "id": "dexter:claim:s01e01:dexter_batista_work",
    "label": "Dexter works with Batista",
    "subject_id": "dexter:character:dexter_morgan",
    "object_id": "dexter:character:angel_batista",
    "predicate": "WORKS_WITH",
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
FUTURE_ENTITY = "dexter:character:future_killer"


class _StubProgressService:
    """Duck-typed stand-in for ProgressService — no database access."""

    def __init__(self, boundary: int = 1) -> None:
        self._boundary = boundary

    async def resolve(self, user_id: str, series_id: str) -> int:
        del user_id, series_id
        return self._boundary


class _ScriptedDatabase:
    """Minimal fail-closed DB stub.

    Entity lookups honor the visibility filter (a hidden entity returns no
    row, exactly like a nonexistent one); claim/evidence/source queries
    return canned visible rows.  Every query is recorded for assertions.
    """

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
    """Yields a distinct event list per call index (last list repeats)."""

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
    boundary: int = 1,
) -> LLMEvent:
    """Run one full pipeline turn and return the final done event."""
    pipeline = RetrievalPipeline(
        database=database, progress_service=_StubProgressService(boundary=boundary)
    )
    events = [
        event
        async for event in pipeline.answer(
            user_id="user:test",
            series_id=SERIES_ID,
            chat_session_id="chat-session:test",
            question="Who is Dexter related to?",
            history=[],
            provider=provider,
        )
    ]
    done_events = [event for event in events if event.kind == "done"]
    assert len(done_events) == 1
    return done_events[0]


# ---------------------------------------------------------------------------
# Real-but-not-retrieved-this-turn rejection (Pitfall 3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_visible_but_unretrieved_claim_citation_is_rejected() -> None:
    """A citation to a claim that is real and visible but was never retrieved
    this turn is stripped — the validator checks this turn's retrieved ID set,
    not DB existence (06-RESEARCH.md Pitfall 3)."""
    database = _ScriptedDatabase(
        entity_rows=[NODE_N1 | {"visible_from_order": 1, "origin": "canonical"}],
        claim_rows=[CLAIM_C1],  # only C1 is in this turn's retrieved set
        node_rows=[NODE_N1, NODE_N2],
        evidence_rows=[EVIDENCE_E1],
        source_rows=[SOURCE_S1],
    )
    provider = _ScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [
                LLMEvent.done(
                    "Dexter and Debra are siblings.",
                    citations=[
                        {"claim_id": CLAIM_C1["id"]},  # retrieved this turn -> survives
                        {"claim_id": CLAIM_C2_REAL_UNRETRIEVED["id"]},  # real but unretrieved -> stripped
                    ],
                )
            ],
        ]
    )
    done = await _run_pipeline(database=database, provider=provider)
    assert done.citations is not None
    assert [c["claim_id"] for c in done.citations] == [CLAIM_C1["id"]]
    assert CLAIM_C2_REAL_UNRETRIEVED["id"] not in {c["claim_id"] for c in done.citations}


@pytest.mark.asyncio
async def test_hidden_claim_evidence_source_citations_are_rejected() -> None:
    """Citations referencing hidden claim/evidence/source IDs are stripped —
    hidden resources were never retrieved this turn, so every ID fails the
    this-turn membership check."""
    database = _ScriptedDatabase(
        entity_rows=[NODE_N1 | {"visible_from_order": 1, "origin": "canonical"}],
        claim_rows=[CLAIM_C1],
        node_rows=[NODE_N1, NODE_N2],
        evidence_rows=[],
        source_rows=[],
    )
    provider = _ScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [
                LLMEvent.done(
                    "They are related.",
                    citations=[
                        {
                            "claim_id": CLAIM_C1["id"],
                            "evidence_id": "dexter:evidence:hidden:99",
                            "source_id": "dexter:source:hidden:99",
                        }
                    ],
                )
            ],
        ]
    )
    done = await _run_pipeline(database=database, provider=provider)
    # Every citation referenced hidden IDs -> all stripped -> explicit
    # uncertainty template, empty citation list, empty graph focus.
    assert done.citations == []
    assert done.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert done.graph_focus == {"node_ids": [], "edge_ids": []}


# ---------------------------------------------------------------------------
# Zero surviving citations -> deterministic uncertainty response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_valid_citations_produces_insufficient_evidence_response() -> None:
    """An answer whose citations are all fabricated is replaced by the fixed
    template — the pipeline never passes an ungrounded answer through."""
    database = _ScriptedDatabase(
        entity_rows=[NODE_N1 | {"visible_from_order": 1, "origin": "canonical"}],
        claim_rows=[CLAIM_C1],
        node_rows=[NODE_N1, NODE_N2],
    )
    provider = _ScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [
                LLMEvent.done(
                    "Dexter's secret future is revealed.",
                    citations=[{"claim_id": "dexter:claim:fabricated:999"}],
                )
            ],
        ]
    )
    done = await _run_pipeline(database=database, provider=provider)
    assert done.citations == []
    assert done.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert done.graph_focus == {"node_ids": [], "edge_ids": []}


# ---------------------------------------------------------------------------
# Existence invariance: nonexistent vs hidden-but-real
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nonexistent_and_hidden_entity_get_byte_identical_response() -> None:
    """A question about an entity that does not exist anywhere and a question
    about an entity that exists but is hidden produce byte-identical response
    text — hidden-entity existence is never revealed."""
    nonexistent_db = _ScriptedDatabase()  # entity nowhere in the DB
    hidden_db = _ScriptedDatabase(
        entity_rows=[
            {
                "id": FUTURE_ENTITY,
                "label": "The Future Killer",
                "type": "Character",
                "visible_from_order": 99,  # hidden at boundary 1
                "origin": "canonical",
            }
        ]
    )
    script = [
        [LLMEvent.tool_call("get_entity", {"entity_id": FUTURE_ENTITY})],
        [
            LLMEvent.done(
                "Their future is a secret.",
                citations=[{"claim_id": "dexter:claim:fabricated:999"}],
            )
        ],
    ]
    done_nonexistent = await _run_pipeline(
        database=nonexistent_db, provider=_ScriptedProvider([list(c) for c in script]), boundary=1
    )
    done_hidden = await _run_pipeline(
        database=hidden_db, provider=_ScriptedProvider([list(c) for c in script]), boundary=1
    )
    assert done_nonexistent.content == done_hidden.content
    assert done_nonexistent.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert done_nonexistent.citations == done_hidden.citations == []


# ---------------------------------------------------------------------------
# Distance invariance: one order beyond vs many orders beyond
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_order_beyond_and_many_orders_beyond_get_byte_identical_response() -> None:
    """A future entity exactly one episode-order beyond the boundary and one
    many orders beyond produce byte-identical response text — no
    boundary-distance leak."""
    future_db = _ScriptedDatabase(
        entity_rows=[
            {
                "id": FUTURE_ENTITY,
                "label": "The Future Killer",
                "type": "Character",
                "visible_from_order": 3,  # hidden at boundaries 1 and 2
                "origin": "canonical",
            }
        ]
    )
    script = [
        [LLMEvent.tool_call("get_entity", {"entity_id": FUTURE_ENTITY})],
        [
            LLMEvent.done(
                "Their future is a secret.",
                citations=[{"claim_id": "dexter:claim:fabricated:999"}],
            )
        ],
    ]
    # boundary=2: entity is exactly one order beyond.  boundary=1: many beyond.
    done_one_beyond = await _run_pipeline(
        database=future_db, provider=_ScriptedProvider([list(c) for c in script]), boundary=2
    )
    done_many_beyond = await _run_pipeline(
        database=future_db, provider=_ScriptedProvider([list(c) for c in script]), boundary=1
    )
    assert done_one_beyond.content == done_many_beyond.content
    assert done_one_beyond.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert done_one_beyond.citations == done_many_beyond.citations == []


# ---------------------------------------------------------------------------
# No "you haven't met them yet" phrasing
# ---------------------------------------------------------------------------


def test_template_never_hints_hidden_entity_exists() -> None:
    """The uncertainty template contains no phrasing resembling 'you haven't
    met them yet' and never hints that a hidden entity specifically exists.
    Note: 'spoiler-free' IS allowed — the product brief mandates spoiler-safe
    language in the fallback; the guard targets hints about hidden content,
    not the word spoiler itself."""
    template = pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    for forbidden in ("haven't met", "haven’t met", "not yet", "future", "will meet"):
        assert forbidden.lower() not in template.lower()
    assert "enough information" not in template
    assert "watched" in template


@pytest.mark.asyncio
async def test_pipeline_output_never_hints_hidden_entity_exists() -> None:
    """The pipeline's replaced answer (all citations stripped) contains no
    hint that a hidden entity specifically exists."""
    database = _ScriptedDatabase(
        entity_rows=[NODE_N1 | {"visible_from_order": 1, "origin": "canonical"}],
        claim_rows=[CLAIM_C1],
        node_rows=[NODE_N1, NODE_N2],
    )
    provider = _ScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [
                LLMEvent.done(
                    "You haven't met them yet.",
                    citations=[{"claim_id": "dexter:claim:fabricated:999"}],
                )
            ],
        ]
    )
    done = await _run_pipeline(database=database, provider=provider)
    assert done.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert "haven't met" not in done.content


# ---------------------------------------------------------------------------
# Deterministic wording: the model is instructed to use the exact template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_echoing_template_with_zero_citations_passes_through() -> None:
    """When the model (per the final-answer instruction) answers with the
    exact template text and no citations, the pipeline passes it through
    unmodified — the uncertainty wording is deterministic, not model
    creativity."""
    provider = _ScriptedProvider(
        [
            [
                LLMEvent.done(
                    pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE,
                    citations=[],
                )
            ]
        ]
    )
    done = await _run_pipeline(
        database=_ScriptedDatabase(), provider=provider, boundary=1
    )
    assert done.content == pipeline_module.INSUFFICIENT_EVIDENCE_RESPONSE_TEMPLATE
    assert done.citations == []
