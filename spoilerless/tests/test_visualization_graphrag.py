"""Phase 10-07 (D-26/D-27/D-28): GraphRAG focus contract tests.

Three layers, all offline (no live LLM, no Neo4j, no keys):

1. ``build_graphrag_focus`` unit tests — the pure classifier maps a turn's
   focus ids against THIS turn's retrieved set (entity vs investigation vs
   dropped; ``<claim_id>:edge`` validation; deterministic order).
2. ``project_graphrag_focus`` tests — micro-Event focus substitution onto
   visible major Events + Inspector timeline entry; the 5-20 element bound.
3. FakeLLM end-to-end — the pipeline's final ``done.graph_focus`` rides the
   contract while the COMPLETE retrieved set stays intact (D-04: visual
   bounds never reduce retrieval).
"""

from __future__ import annotations

from typing import Any

import pytest

from spoilerless.app.domain.visualization import (
    GRAPHRAG_FOCUS_MAX_NODES,
    GRAPHRAG_FOCUS_VIEW_TYPE,
)
from spoilerless.app.retrieval.pipeline import (
    GraphRagFocusContract,
    RetrievalPipeline,
    build_graphrag_focus,
)
from spoilerless.app.services.visualization import (
    VisualizationProjectionService,
)
from spoilerless.tests.test_retrieval_pipeline import (
    CLAIM_C1,
    EVIDENCE_E1,
    NODE_N1,
    NODE_N2,
    SOURCE_S1,
    _CallScriptedProvider,
    _StubDatabase,
    _StubProgressService,
)
from spoilerless.app.llm.provider import LLMEvent
from spoilerless.tests.test_visualization_projection import _load_fixture

service = VisualizationProjectionService()


# ---------------------------------------------------------------------------
# build_graphrag_focus unit tests
# ---------------------------------------------------------------------------


def _retrieved(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "nodes": [NODE_N1, NODE_N2],
        "claims": [CLAIM_C1],
        "evidence": [EVIDENCE_E1],
        "sources": [SOURCE_S1],
        "edges": [{"id": f"{CLAIM_C1['id']}:edge", "source": NODE_N1["id"], "target": NODE_N2["id"], "type": "FAMILY_OF"}],
    }
    base.update(overrides)
    return base


def test_build_graphrag_focus_classifies_entity_investigation_and_dropped() -> None:
    contract = build_graphrag_focus(
        _retrieved(),
        node_ids=[NODE_N1["id"], EVIDENCE_E1["id"], SOURCE_S1["id"], "never_fetched"],
        edge_ids=[],
    )
    assert contract.entity_ids == [NODE_N1["id"]]
    assert contract.event_ids == []  # NODE_N1 is a Character row
    assert contract.investigation_ids == [EVIDENCE_E1["id"], SOURCE_S1["id"]]
    assert contract.dropped_ids == ["never_fetched"]
    assert contract.edge_ids == []


def test_build_graphrag_focus_claim_endpoints_count_as_entity_refs() -> None:
    # The claim was retrieved but its subject/object node rows were not:
    # endpoints are still valid in-place highlight targets (same row class
    # the citation validator accepts).
    retrieved = _retrieved(nodes=[])
    contract = build_graphrag_focus(
        retrieved,
        node_ids=[CLAIM_C1["subject_id"], CLAIM_C1["object_id"]],
        edge_ids=[],
    )
    assert sorted(contract.entity_ids) == sorted(
        [CLAIM_C1["subject_id"], CLAIM_C1["object_id"]]
    )
    assert contract.dropped_ids == []


def test_build_graphrag_focus_validates_claim_edge_ids_and_drops_unknown() -> None:
    contract = build_graphrag_focus(
        _retrieved(),
        node_ids=[],
        edge_ids=[f"{CLAIM_C1['id']}:edge", "edge_not_retrieved"],
    )
    assert contract.edge_ids == [f"{CLAIM_C1['id']}:edge"]
    assert contract.dropped_ids == ["edge_not_retrieved"]


def test_build_graphrag_focus_event_rows_land_in_event_ids() -> None:
    event_row = {"id": "event_first_kill", "type": "Event", "label": "First kill"}
    retrieved = _retrieved(nodes=[NODE_N1, event_row])
    contract = build_graphrag_focus(retrieved, node_ids=["event_first_kill"], edge_ids=[])
    assert contract.entity_ids == ["event_first_kill"]
    assert contract.event_ids == ["event_first_kill"]


# ---------------------------------------------------------------------------
# project_graphrag_focus: micro-Event substitution + bound (D-26/D-27/D-37)
# ---------------------------------------------------------------------------


def test_graphrag_focus_micro_event_substitutes_visible_major_event() -> None:
    from spoilerless.app.domain.graph import GraphNode
    from spoilerless.app.domain.visualization import SafeEventContext

    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    # The fixture's editorial contexts: event_first_kill (major, s01e01) and
    # event_croc_discovery (major, s01e02). A micro event on s01e02 must map
    # to event_croc_discovery, never draw itself in-graph.
    graph.nodes.append(
        GraphNode(
            id="event_micro_s01e02",
            type="Event",
            label="A passing detail",
            visible_from_order=2,
            origin="canonical",
            episode_id="dexter_s01e02",
        )
    )
    micro = {
        "id": "event_micro_s01e02",
        "label": "A passing detail",
        "episode_id": "dexter_s01e02",
        "tier": "micro",
        "participants": [],
        "location": None,
        "visible_from_order": 2,
    }
    events = events + [SafeEventContext.model_validate(micro)]
    dto = service.project_graphrag_focus(
        graph, focus_ids=["event_micro_s01e02"], events=events
    )
    ids = [node.id for node in dto.nodes]
    assert "event_micro_s01e02" not in ids
    assert "event_croc_discovery" in ids
    # The micro event still surfaces as Inspector detail via the timeline.
    assert any(item.id == "event_micro_s01e02" for item in dto.timeline)
    assert dto.metadata.view_type == GRAPHRAG_FOCUS_VIEW_TYPE
    # Primary focus reference resolves inside the DTO (substituted major).
    assert dto.focus is not None
    assert dto.focus.node_id in ids


def test_graphrag_focus_major_event_stays_in_place() -> None:
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    dto = service.project_graphrag_focus(
        graph, focus_ids=["event_croc_discovery"], events=events
    )
    ids = [node.id for node in dto.nodes]
    assert "event_croc_discovery" in ids
    # No substitution timeline entries for an already-major event.
    assert all(item.id != "event_croc_discovery" for item in dto.timeline)


def test_graphrag_focus_respects_element_bound() -> None:
    graph, events = _load_fixture("s01e02_cumulative_safe.json")
    # Focus on the most-connected node: neighbors are truncated at the bound.
    dto = service.project_graphrag_focus(
        graph, focus_ids=["char_dexter_morgan"], events=events
    )
    # D-27: the Answer Graph bound is a hard MAX; sparse fixtures may yield
    # fewer than the 5-element target without violating safety.
    assert 1 <= len(dto.nodes) <= GRAPHRAG_FOCUS_MAX_NODES
    assert dto.groups == []
    # No hidden totals anywhere in the payload.
    for key, value in _walk(dto.model_dump(mode="json")):
        del key, value  # key/value only used for iteration


def _walk(obj: Any):
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert not any(
                word in key for word in ("total", "count", "degree", "restoration")
            )
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


# ---------------------------------------------------------------------------
# FakeLLM end-to-end: complete retrieval survives visual focus (D-04, T10-LEAK-07)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_done_focus_rides_contract_while_retrieval_stays_complete() -> None:
    database = _StubDatabase(
        node_rows=[NODE_N1, NODE_N2],
        claim_rows=[CLAIM_C1],
        evidence_rows=[EVIDENCE_E1],
        source_rows=[SOURCE_S1],
    )
    provider = _CallScriptedProvider(
        [
            [LLMEvent.tool_call("get_neighborhood", {"entity_id": NODE_N1["id"], "depth": 1})],
            [
                LLMEvent.done(
                    "Dexter and Debra are siblings.",
                    citations=[{"claim_id": CLAIM_C1["id"]}],
                )
            ],
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
    done = next(event for event in events if event.kind == "done")
    assert done.content == "Dexter and Debra are siblings."

    # The final focus is a GraphRagFocusContract-mapped, citation-validated set:
    # claim endpoints as in-place entity ids + the claim's :edge id. The
    # contract dropped nothing that was retrieved.
    contract = build_graphrag_focus(
        {
            "nodes": [NODE_N1, NODE_N2],
            "claims": [CLAIM_C1],
            "evidence": [EVIDENCE_E1],
            "sources": [SOURCE_S1],
            "edges": [],
        },
        node_ids=done.graph_focus["node_ids"],
        edge_ids=done.graph_focus["edge_ids"],
    )
    assert contract.dropped_ids == []
    assert sorted(contract.entity_ids) == sorted(
        [CLAIM_C1["subject_id"], CLAIM_C1["object_id"]]
    )
    assert contract.edge_ids == [f"{CLAIM_C1['id']}:edge"]

    # D-04: the COMPLETE retrieved set was assembled into context regardless
    # of the focus classification (retrieval is never reduced to visual
    # bounds).
    context = provider.calls[-1]["messages"][-1]["content"]
    assert CLAIM_C1["id"] in context
    assert EVIDENCE_E1["id"] in context
    assert SOURCE_S1["id"] in context
    assert NODE_N1["id"] in context
    assert NODE_N2["id"] in context
