"""Integration tests for the allowlisted retrieval tools (RAG-02, RAG-03).

Runs against the live local Neo4j instance seeded with Dexter S01E01-03.
Every tool independently enforces the visibility boundary: ``visible_until_order``
is a keyword parameter supplied by the pipeline caller (never model input), and
hidden resources behave exactly like missing ones (fail closed).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator

import pytest

from backend.app.core.config import get_settings
from backend.app.graph.database import Neo4jDatabase
from backend.app.retrieval import tools as tools_module
from backend.app.retrieval.tools import (
    find_path,
    get_claims,
    get_current_visible_graph_summary,
    get_entity,
    get_evidence,
    get_neighborhood,
    get_sources,
    get_timeline,
    get_user_notes,
    search_entities,
)

SERIES_ID = "series_dexter"
DEXTER = "dexter:character:dexter_morgan"
DEBRA = "dexter:character:debra_morgan"
HARRY = "dexter:character:harry_morgan"
PAUL = "dexter:character:paul_bennett"

CLAIM_DEBRA_FAMILY = "dexter:claim:s01e01:dexter_debra_family"
CLAIM_BATISTA_WORK = "dexter:claim:s01e01:dexter_batista_work"
CLAIM_DOAKES_DISTRUSTS = "dexter:claim:s01e01:doakes_distrusts_dexter"
CLAIM_HARRY_FAMILY = "dexter:claim:s01e03:dexter_harry_family"
EVIDENCE_S01E01_01 = "dexter:evidence:s01e01:01"
SOURCE_S01E01 = "dexter:source:s01e01"

# The ten allowlisted tools from 06-PRD-SOURCE.md section 5 (exact names).
ALL_TEN_TOOLS = (
    "search_entities",
    "get_entity",
    "get_neighborhood",
    "find_path",
    "get_timeline",
    "get_claims",
    "get_evidence",
    "get_sources",
    "get_current_visible_graph_summary",
    "get_user_notes",
)

# Scratch series for leakage tests that need cross-series / hidden-intermediate
# resources.  The seed-integrity audit only scans the seeded series, so nodes
# here never trip it; the fixture still deletes everything it creates.
SCRATCH_SERIES = "series_scratch_retrieval"


@pytest.fixture
def database() -> AsyncIterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db


@pytest.fixture
async def scratch_series(database: Neo4jDatabase) -> AsyncIterator[str]:
    """Yield the scratch series id, deleting everything created there after."""
    yield SCRATCH_SERIES
    await database.execute_query(
        "MATCH (n {series_id: $series_id}) DETACH DELETE n",
        series_id=SCRATCH_SERIES,
    )


def _ids(rows: list[dict]) -> set[str]:
    return {row["id"] for row in rows}


async def _create_chain(
    database: Neo4jDatabase,
    *,
    node_ids: list[str],
    claim_ids: list[str],
    series_id: str = SCRATCH_SERIES,
    hidden_orders: set[str] | None = None,
) -> None:
    """Create ``Character`` nodes + ``Claim`` edges forming a linear chain.

    ``hidden_orders`` names node/claim ids whose ``visible_from_order`` is 99
    (hidden at any realistic boundary); everything else is visible from order 1.
    """
    hidden_orders = hidden_orders or set()
    nodes = [
        {
            "id": node_id,
            "visible_from_order": 99 if node_id in hidden_orders else 1,
        }
        for node_id in node_ids
    ]
    await database.execute_query(
        """
        UNWIND $nodes AS n
        CREATE (node:Character {id: n.id, series_id: $series_id,
                label: n.id, visible_from_order: n.visible_from_order,
                origin: 'canonical'})
        """,
        nodes=nodes,
        series_id=series_id,
    )
    claims = [
        {
            "id": claim_id,
            "subject_id": node_ids[index],
            "object_id": node_ids[index + 1],
            "visible_from_order": 99 if claim_id in hidden_orders else 1,
        }
        for index, claim_id in enumerate(claim_ids)
    ]
    await database.execute_query(
        """
        UNWIND $claims AS c
        MATCH (subject {id: c.subject_id, series_id: $series_id})
        MATCH (object {id: c.object_id, series_id: $series_id})
        CREATE (claim:Claim {id: c.id, series_id: $series_id, label: c.id,
                subject_id: c.subject_id, predicate: 'KNOWS',
                object_id: c.object_id, claim_type: 'observed_event',
                status: 'corroborated', confidence_level: 'high',
                visible_from_order: c.visible_from_order, origin: 'canonical'})
        """,
        claims=claims,
        series_id=series_id,
    )


async def _create_note(
    database: Neo4jDatabase,
    *,
    note_id: str,
    user_id: str,
    target_id: str,
    visible_from_order: int,
    content: str = "remember this",
) -> None:
    """Create one user note on a visible Character node (test-only user_id)."""
    await database.execute_query(
        """
        MATCH (target:Character {id: $target_id, series_id: $series_id})
        CREATE (note:UserNote {id: $id, series_id: $series_id,
                target_type: 'Character', target_id: $target_id,
                content: $content, visible_from_order: $visible_from_order,
                origin: 'user', user_id: $user_id,
                created_at: '2026-01-01T00:00:00+00:00',
                updated_at: '2026-01-01T00:00:00+00:00'})
        CREATE (note)-[:REFERS_TO {id: $id + ':refers_to',
                series_id: $series_id,
                visible_from_order: $visible_from_order,
                origin: 'user'}]->(target)
        """,
        id=note_id,
        series_id=SERIES_ID,
        target_id=target_id,
        content=content,
        visible_from_order=visible_from_order,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Tool surface (acceptance criteria 1-2): all ten exported, fail-closed
# signatures, no raw Cypher parameter anywhere.
# ---------------------------------------------------------------------------


def test_all_ten_allowlisted_tools_are_exported() -> None:
    for name in ALL_TEN_TOOLS:
        assert hasattr(tools_module, name), f"missing tool export: {name}"


def test_every_tool_requires_series_scope_and_boundary_keywords() -> None:
    """``series_id``/``visible_until_order`` are keyword-only, caller-supplied,
    never model-sourced, and never defaulted on the tool functions."""
    for name in ALL_TEN_TOOLS:
        signature = inspect.signature(getattr(tools_module, name))
        for required in ("series_id", "visible_until_order"):
            parameter = signature.parameters.get(required)
            assert parameter is not None, f"{name} missing {required}"
            assert (
                parameter.kind == inspect.Parameter.KEYWORD_ONLY
            ), f"{name}.{required} must be keyword-only"
            assert (
                parameter.default is inspect.Parameter.empty
            ), f"{name}.{required} must not have a default"


def test_no_tool_accepts_raw_cypher() -> None:
    """By construction: no parameter accepts a Cypher fragment anywhere."""
    for name in ALL_TEN_TOOLS:
        signature = inspect.signature(getattr(tools_module, name))
        for parameter_name in signature.parameters:
            assert "cypher" not in parameter_name.lower(), (
                f"{name} exposes a cypher-accepting parameter: {parameter_name}"
            )
        # The only "query" parameter in the whole surface is search_entities'
        # plain substring matcher — a value, never a query language fragment.
        if name == "search_entities":
            assert "query" in signature.parameters
        else:
            assert "query" not in signature.parameters, (
                f"{name} must not accept a query parameter"
            )


@pytest.mark.asyncio
async def test_cypher_injection_strings_are_treated_as_data(database: Neo4jDatabase) -> None:
    injection = "'; MATCH (n) DETACH DELETE n //"
    hidden = await get_entity(
        database,
        entity_id=injection,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    missing = await get_entity(
        database,
        entity_id="dexter:character:no-such-entity",
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden is None
    assert hidden == missing
    assert await search_entities(
        database,
        query=injection,
        allowed_entity_types=["Character"],
        limit=5,
        series_id=SERIES_ID,
        visible_until_order=1,
    ) == []
    # The graph is still intact — the injection string was bound as data.
    assert await get_entity(
        database, entity_id=DEXTER, series_id=SERIES_ID, visible_until_order=1
    ) is not None


# ---------------------------------------------------------------------------
# search_entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_entities_returns_visible_matches_in_stable_order(
    database: Neo4jDatabase,
) -> None:
    first = await search_entities(
        database,
        query="morgan",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    second = await search_entities(
        database,
        query="morgan",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    # Deterministic order (visible_from_order, id) across repeated identical calls.
    assert [row["id"] for row in first] == [DEBRA, DEXTER, HARRY]
    assert first == second


@pytest.mark.asyncio
async def test_search_entities_hides_future_matches(database: Neo4jDatabase) -> None:
    hidden = await search_entities(
        database,
        query="harry",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    missing = await search_entities(
        database,
        query="zzzz-no-such-name",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden == []
    assert hidden == missing  # hidden behaves exactly like nonexistent

    revealed = await search_entities(
        database,
        query="harry",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    assert [row["id"] for row in revealed] == [HARRY]


@pytest.mark.asyncio
async def test_search_entities_bounded_by_limit_and_type_allowlist(
    database: Neo4jDatabase,
) -> None:
    bounded = await search_entities(
        database,
        query="morgan",
        allowed_entity_types=["Character"],
        limit=2,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    assert len(bounded) == 2

    only_locations = await search_entities(
        database,
        query="miami",
        allowed_entity_types=["Location"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    assert {row["type"] for row in only_locations} == {"Location"}
    assert "dexter:location:miami_metro" in _ids(only_locations)

    no_characters = await search_entities(
        database,
        query="miami",
        allowed_entity_types=["Character"],
        limit=10,
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    assert no_characters == []


@pytest.mark.asyncio
async def test_search_entities_empty_query_fails_closed(database: Neo4jDatabase) -> None:
    for empty in ("", "   "):
        assert await search_entities(
            database,
            query=empty,
            allowed_entity_types=["Character"],
            limit=10,
            series_id=SERIES_ID,
            visible_until_order=3,
        ) == []


# ---------------------------------------------------------------------------
# find_path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_path_returns_visible_path(database: Neo4jDatabase) -> None:
    result = await find_path(
        database,
        source_entity_id=DEXTER,
        target_entity_id=DEBRA,
        max_hops=2,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert result == {
        "found": True,
        "path": [DEXTER, DEBRA],
        "edges": [CLAIM_DEBRA_FAMILY],
        "hops": 1,
    }


@pytest.mark.asyncio
async def test_find_path_clamps_requested_hops_to_server_ceiling(
    database: Neo4jDatabase,
) -> None:
    # max_hops=99 must be clamped, never raise, and never change the result.
    clamped = await find_path(
        database,
        source_entity_id=DEXTER,
        target_entity_id=DEBRA,
        max_hops=99,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert clamped == {
        "found": True,
        "path": [DEXTER, DEBRA],
        "edges": [CLAIM_DEBRA_FAMILY],
        "hops": 1,
    }


@pytest.mark.asyncio
async def test_find_path_through_hidden_intermediate_reveals_nothing(
    database: Neo4jDatabase, scratch_series: str
) -> None:
    # A -> H -> B where H is hidden: the path exists in the database but every
    # claim touching H is invisible, so the visible graph has no path.
    await _create_chain(
        database,
        node_ids=["scratch:a", "scratch:h", "scratch:b"],
        claim_ids=["scratch:claim:a_h", "scratch:claim:h_b"],
        hidden_orders={"scratch:h", "scratch:claim:a_h", "scratch:claim:h_b"},
    )
    through_hidden = await find_path(
        database,
        source_entity_id="scratch:a",
        target_entity_id="scratch:b",
        max_hops=3,
        series_id=SCRATCH_SERIES,
        visible_until_order=1,
    )
    target_missing = await find_path(
        database,
        source_entity_id="scratch:a",
        target_entity_id="scratch:no-such-target",
        max_hops=3,
        series_id=SCRATCH_SERIES,
        visible_until_order=1,
    )
    assert through_hidden == {"found": False, "path": [], "edges": [], "hops": 0}
    assert through_hidden == target_missing  # hidden path existence never revealed


@pytest.mark.asyncio
async def test_find_path_multi_hop_bounded_by_max_hops(
    database: Neo4jDatabase, scratch_series: str
) -> None:
    # A -> B -> C -> D -> E: 4 hops end to end.
    await _create_chain(
        database,
        node_ids=["scratch:a", "scratch:b", "scratch:c", "scratch:d", "scratch:e"],
        claim_ids=[
            "scratch:claim:a_b",
            "scratch:claim:b_c",
            "scratch:claim:c_d",
            "scratch:claim:d_e",
        ],
    )
    too_shallow = await find_path(
        database,
        source_entity_id="scratch:a",
        target_entity_id="scratch:e",
        max_hops=2,
        series_id=SCRATCH_SERIES,
        visible_until_order=1,
    )
    assert too_shallow == {"found": False, "path": [], "edges": [], "hops": 0}

    exact = await find_path(
        database,
        source_entity_id="scratch:a",
        target_entity_id="scratch:e",
        max_hops=4,
        series_id=SCRATCH_SERIES,
        visible_until_order=1,
    )
    assert exact["found"] is True
    assert exact["path"] == ["scratch:a", "scratch:b", "scratch:c", "scratch:d", "scratch:e"]
    assert exact["hops"] == 4

    over_ceiling = await find_path(
        database,
        source_entity_id="scratch:a",
        target_entity_id="scratch:e",
        max_hops=99,
        series_id=SCRATCH_SERIES,
        visible_until_order=1,
    )
    assert over_ceiling == exact  # clamped at the server ceiling


# ---------------------------------------------------------------------------
# get_timeline / get_claims / get_evidence / get_sources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_timeline_returns_only_visible_episodes(database: Neo4jDatabase) -> None:
    timeline = await get_timeline(
        database, series_id=SERIES_ID, visible_until_order=2
    )
    assert [row["id"] for row in timeline] == ["dexter_s01e01", "dexter_s01e02"]
    assert [row["code"] for row in timeline] == ["S01E01", "S01E02"]
    # Episode 3 is one order above the boundary — excluded entirely.
    assert all(row["episode_order"] <= 2 for row in timeline)

    unknown_series = await get_timeline(
        database, series_id="series_does_not_exist", visible_until_order=2
    )
    assert unknown_series == []


@pytest.mark.asyncio
async def test_get_claims_returns_visible_claims_for_entities(
    database: Neo4jDatabase,
) -> None:
    claims = await get_claims(
        database, entity_ids=[DEXTER], series_id=SERIES_ID, visible_until_order=1
    )
    claim_ids = _ids(claims)
    assert CLAIM_DEBRA_FAMILY in claim_ids
    assert CLAIM_BATISTA_WORK in claim_ids
    assert CLAIM_DOAKES_DISTRUSTS in claim_ids
    assert CLAIM_HARRY_FAMILY not in claim_ids  # future claim hidden


@pytest.mark.asyncio
async def test_get_claims_hidden_and_missing_ids_identical(
    database: Neo4jDatabase,
) -> None:
    hidden = await get_claims(
        database, entity_ids=[HARRY], series_id=SERIES_ID, visible_until_order=1
    )
    missing = await get_claims(
        database,
        entity_ids=["dexter:character:no-such"],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden == []
    assert hidden == missing


@pytest.mark.asyncio
async def test_get_claims_rejects_cross_series_ids_identically(
    database: Neo4jDatabase, scratch_series: str
) -> None:
    await _create_chain(
        database,
        node_ids=["scratch:x", "scratch:y"],
        claim_ids=["scratch:claim:x_y"],
    )
    cross_series = await get_claims(
        database,
        entity_ids=["scratch:x"],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    missing = await get_claims(
        database,
        entity_ids=["dexter:character:no-such"],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert cross_series == []
    assert cross_series == missing  # no series-boundary leak


@pytest.mark.asyncio
async def test_get_evidence_visible_only(database: Neo4jDatabase) -> None:
    evidence = await get_evidence(
        database,
        claim_ids=[CLAIM_DEBRA_FAMILY],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert _ids(evidence) == {EVIDENCE_S01E01_01}

    hidden = await get_evidence(
        database,
        claim_ids=[CLAIM_HARRY_FAMILY],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    missing = await get_evidence(
        database,
        claim_ids=["dexter:claim:no-such"],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden == []
    assert hidden == missing


@pytest.mark.asyncio
async def test_get_sources_visible_only(database: Neo4jDatabase) -> None:
    sources = await get_sources(
        database,
        claim_ids=[CLAIM_DEBRA_FAMILY],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert _ids(sources) == {SOURCE_S01E01}

    hidden = await get_sources(
        database,
        claim_ids=[CLAIM_HARRY_FAMILY],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    missing = await get_sources(
        database,
        claim_ids=["dexter:claim:no-such"],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden == []
    assert hidden == missing


# ---------------------------------------------------------------------------
# get_current_visible_graph_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_visible_graph_summary_respects_server_size_limit(
    database: Neo4jDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_max_context_items", 2)
    summary = await get_current_visible_graph_summary(
        database,
        focus_entity_ids=[DEXTER],
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    assert summary["series_id"] == SERIES_ID
    assert summary["visible_until_order"] == 3
    assert set(summary["counts"]) == {"entities", "claims", "evidence", "sources"}
    # Strict server-owned truncation even though the boundary-3 graph is larger.
    assert len(summary["entities"]) <= 2
    assert len(summary["claims"]) <= 2
    assert len(summary["evidence"]) <= 2
    assert len(summary["sources"]) <= 2
    assert len(summary["episodes"]) <= 2


@pytest.mark.asyncio
async def test_get_current_visible_graph_summary_hides_future_resources(
    database: Neo4jDatabase,
) -> None:
    at_one = await get_current_visible_graph_summary(
        database,
        focus_entity_ids=[DEXTER],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    at_three = await get_current_visible_graph_summary(
        database,
        focus_entity_ids=[DEXTER],
        series_id=SERIES_ID,
        visible_until_order=3,
    )
    # Future resources are excluded entirely from the boundary-1 summary.
    assert PAUL not in _ids(at_one["entities"])
    assert HARRY not in _ids(at_one["entities"])
    # Hidden counts are never exposed: every count grows only with visibility.
    for key in ("entities", "claims", "evidence", "sources"):
        assert at_one["counts"][key] < at_three["counts"][key], key


@pytest.mark.asyncio
async def test_get_current_visible_graph_summary_counts_match_visible_graph(
    database: Neo4jDatabase,
) -> None:
    summary = await get_current_visible_graph_summary(
        database,
        focus_entity_ids=[DEXTER],
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    rows = await database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id
          AND any(label IN labels(node) WHERE label IN $allowed_labels)
          AND node.visible_from_order IS NOT NULL
          AND node.visible_from_order <= $visible_until_order
        RETURN count(node) AS count
        """,
        series_id=SERIES_ID,
        visible_until_order=1,
        allowed_labels=sorted(
            ["Character", "Event", "Location", "Organization", "Object"]
        ),
    )
    assert summary["counts"]["entities"] == rows[0]["count"]


# ---------------------------------------------------------------------------
# get_user_notes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_notes_only_returns_own_notes_on_visible_targets(
    database: Neo4jDatabase,
) -> None:
    note_ids = [
        "user-note:test:a-dexter",
        "user-note:test:b-dexter",
        "user-note:test:a-harry",
    ]
    try:
        await _create_note(
            database,
            note_id=note_ids[0],
            user_id="user:a",
            target_id=DEXTER,
            visible_from_order=1,
        )
        await _create_note(
            database,
            note_id=note_ids[1],
            user_id="user:b",
            target_id=DEXTER,
            visible_from_order=1,
        )
        await _create_note(
            database,
            note_id=note_ids[2],
            user_id="user:a",
            target_id=HARRY,
            visible_from_order=3,
        )

        at_one = await get_user_notes(
            database,
            entity_or_claim_ids=[DEXTER, HARRY],
            user_id="user:a",
            series_id=SERIES_ID,
            visible_until_order=1,
        )
        # Only user a's note on the currently-visible Dexter; the note on the
        # hidden Harry is excluded, and user b's note never appears.
        assert _ids(at_one) == {note_ids[0]}

        at_three = await get_user_notes(
            database,
            entity_or_claim_ids=[DEXTER, HARRY],
            user_id="user:a",
            series_id=SERIES_ID,
            visible_until_order=3,
        )
        assert _ids(at_three) == {note_ids[0], note_ids[2]}

        other_user = await get_user_notes(
            database,
            entity_or_claim_ids=[DEXTER, HARRY],
            user_id="user:nobody",
            series_id=SERIES_ID,
            visible_until_order=3,
        )
        assert other_user == []
    finally:
        await database.execute_query(
            "MATCH (n:UserNote) WHERE n.id IN $ids DETACH DELETE n",
            ids=note_ids,
        )


# ---------------------------------------------------------------------------
# get_entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entity_returns_visible_character(database: Neo4jDatabase) -> None:
    row = await get_entity(
        database,
        entity_id=DEXTER,
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert row is not None
    assert row["id"] == DEXTER
    assert row["type"] == "Character"
    assert row["visible_from_order"] == 1


@pytest.mark.asyncio
async def test_get_entity_boundary_is_inclusive(database: Neo4jDatabase) -> None:
    """A node whose visible_from_order equals the resolved boundary IS returned."""
    row = await get_entity(
        database,
        entity_id=PAUL,
        series_id=SERIES_ID,
        visible_until_order=2,
    )
    assert row is not None
    assert row["id"] == PAUL
    assert row["visible_from_order"] == 2


@pytest.mark.asyncio
async def test_get_entity_hidden_character_behaves_as_nonexistent(
    database: Neo4jDatabase,
) -> None:
    # Harry Morgan is visible from order 3; at boundary 1 he must not exist.
    hidden = await get_entity(
        database, entity_id=HARRY, series_id=SERIES_ID, visible_until_order=1
    )
    missing = await get_entity(
        database,
        entity_id="dexter:character:does-not-exist",
        series_id=SERIES_ID,
        visible_until_order=1,
    )
    assert hidden is None
    assert missing is None
    assert hidden == missing  # indistinguishable, by design


# ---------------------------------------------------------------------------
# get_neighborhood
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_neighborhood_returns_visible_neighbors_claims_evidence_sources(
    database: Neo4jDatabase,
) -> None:
    result = await get_neighborhood(
        database,
        entity_id=DEXTER,
        series_id=SERIES_ID,
        visible_until_order=1,
        depth=1,
    )
    assert result["entity"] is not None
    assert result["entity"]["id"] == DEXTER

    node_ids = _ids(result["nodes"])
    assert DEXTER in node_ids
    assert DEBRA in node_ids  # visible neighbor via FAMILY_OF claim

    claim_ids = _ids(result["claims"])
    assert CLAIM_DEBRA_FAMILY in claim_ids

    evidence_ids = _ids(result["evidence"])
    assert EVIDENCE_S01E01_01 in evidence_ids

    source_ids = _ids(result["sources"])
    assert SOURCE_S01E01 in source_ids

    edge_ids = _ids(result["edges"])
    assert f"{CLAIM_DEBRA_FAMILY}:edge" in edge_ids


@pytest.mark.asyncio
async def test_get_neighborhood_excludes_hidden_claims(
    database: Neo4jDatabase,
) -> None:
    # dexter_harry_family is visible from order 3 — excluded at boundary 1.
    result = await get_neighborhood(
        database,
        entity_id=DEXTER,
        series_id=SERIES_ID,
        visible_until_order=1,
        depth=1,
    )
    assert CLAIM_HARRY_FAMILY not in _ids(result["claims"])
    assert HARRY not in _ids(result["nodes"])


@pytest.mark.asyncio
async def test_get_neighborhood_inclusive_boundary(database: Neo4jDatabase) -> None:
    # Rita's neighborhood at boundary 2 includes Paul (claim visible from order 2).
    result = await get_neighborhood(
        database,
        entity_id="dexter:character:rita_bennett",
        series_id=SERIES_ID,
        visible_until_order=2,
        depth=1,
    )
    assert PAUL in _ids(result["nodes"])
    assert "dexter:claim:s01e02:rita_paul_family" in _ids(result["claims"])

    # Same question at boundary 1: Paul and the claim are gone.
    lowered = await get_neighborhood(
        database,
        entity_id="dexter:character:rita_bennett",
        series_id=SERIES_ID,
        visible_until_order=1,
        depth=1,
    )
    assert PAUL not in _ids(lowered["nodes"])
    assert "dexter:claim:s01e02:rita_paul_family" not in _ids(lowered["claims"])


@pytest.mark.asyncio
async def test_get_neighborhood_hidden_entity_fails_closed(
    database: Neo4jDatabase,
) -> None:
    result = await get_neighborhood(
        database,
        entity_id=HARRY,
        series_id=SERIES_ID,
        visible_until_order=1,
        depth=1,
    )
    assert result["entity"] is None
    assert result["nodes"] == []
    assert result["edges"] == []
    assert result["claims"] == []
    assert result["evidence"] == []
    assert result["sources"] == []


# ===================================================================
# 07-04 VIS-03 / D-20: relationship-level gating + static Cypher scan
# ===================================================================

def test_story_sensitive_query_constants_are_boundary_gated() -> None:
    """Static scan (D-20): every story-sensitive query constant selects only
    non-null, boundary-satisfied rows and carries a boundary parameter —
    no story data can be selected by a missing/null visibility value, and no
    runtime value is ever interpolated (constants are plain strings)."""
    from backend.app.spoiler import filter as filter_module

    constants = [
        "BOUNDARY_QUERY",
        "NODES_QUERY",
        "STRUCTURAL_EDGES_QUERY",
        "VISIBLE_CLAIMS_QUERY",
        "VISIBLE_USER_RELATIONSHIPS_QUERY",
        "CLAIMS_FOR_FRONTIER_QUERY",
        "GET_CLAIMS_QUERY",
        "GRAPH_SUMMARY_COUNTS_QUERY",
        "ALL_VISIBLE_CLAIMS_QUERY",
        "ALL_VISIBLE_NODES_QUERY",
        "NODES_BY_IDS_QUERY",
        "EVIDENCE_FOR_CLAIMS_QUERY",
        "SOURCES_FOR_CLAIMS_QUERY",
        "GET_EVIDENCE_QUERY",
        "GET_SOURCES_QUERY",
        "USER_NOTES_QUERY",
    ]
    checked = 0
    for module in (tools_module, filter_module):
        for name in constants:
            query = getattr(module, name, None)
            if query is None:
                continue
            checked += 1
            assert "visible_from_order IS NOT NULL" in query, f"{module.__name__}.{name}"
            assert (
                "$visible_until_order" in query or "$effective_view_order" in query
            ), f"{module.__name__}.{name}"
    assert checked >= 12


async def test_null_visible_from_order_claim_relationship_hidden_with_visible_endpoints(
    database: Neo4jDatabase,
    scratch_series: str,
) -> None:
    """VIS-03: a claim relationship whose own visibility is null is never
    returned even when both endpoint nodes are visible (fail closed)."""
    await _create_chain(database, node_ids=["n_a", "n_b"], claim_ids=["claim_ab"])
    await database.execute_query(
        "MATCH (c:Claim {id: 'claim_ab'}) SET c.visible_from_order = NULL",
    )
    claims = await get_claims(
        database, entity_ids=["n_a"], series_id=SCRATCH_SERIES, visible_until_order=3
    )
    assert "claim_ab" not in _ids(claims)


async def test_satisfied_claim_relationship_hidden_when_endpoint_hidden(
    database: Neo4jDatabase,
    scratch_series: str,
) -> None:
    """VIS-03: a satisfied relationship is still hidden when an endpoint node
    is hidden (independent endpoint gating)."""
    await _create_chain(database, node_ids=["n_c", "n_d"], claim_ids=["claim_cd"])
    await database.execute_query(
        "MATCH (n:Character {id: 'n_d'}) SET n.visible_from_order = 99",
    )
    claims = await get_claims(
        database, entity_ids=["n_c"], series_id=SCRATCH_SERIES, visible_until_order=3
    )
    assert "claim_cd" not in _ids(claims)


async def test_hidden_claims_do_not_change_graph_summary_counts(
    database: Neo4jDatabase,
    scratch_series: str,
) -> None:
    """D-16: hidden relationships do not influence count projections."""
    await _create_chain(
        database,
        node_ids=["n_e", "n_f", "n_g"],
        claim_ids=["claim_ef_visible", "claim_ef_hidden"],
    )
    await database.execute_query(
        "MATCH (c:Claim {id: 'claim_ef_hidden'}) SET c.visible_from_order = 99",
    )
    low = await get_current_visible_graph_summary(
        database, focus_entity_ids=["n_e"], series_id=SCRATCH_SERIES, visible_until_order=3
    )
    high = await get_current_visible_graph_summary(
        database, focus_entity_ids=["n_e"], series_id=SCRATCH_SERIES, visible_until_order=99
    )
    assert low["counts"]["claims"] == 1
    assert high["counts"]["claims"] == 2
