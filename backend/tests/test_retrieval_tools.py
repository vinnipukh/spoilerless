"""Integration tests for the allowlisted retrieval tools (RAG-02, RAG-03).

Runs against the live local Neo4j instance seeded with Dexter S01E01-03.
Every tool independently enforces the visibility boundary: ``visible_until_order``
is a keyword parameter supplied by the pipeline caller (never model input), and
hidden resources behave exactly like missing ones (fail closed).
"""

from __future__ import annotations

from typing import AsyncIterator

import pytest

from backend.app.graph.database import Neo4jDatabase
from backend.app.retrieval.tools import get_entity, get_neighborhood

SERIES_ID = "series_dexter"
DEXTER = "dexter:character:dexter_morgan"
DEBRA = "dexter:character:debra_morgan"
HARRY = "dexter:character:harry_morgan"
PAUL = "dexter:character:paul_bennett"

CLAIM_DEBRA_FAMILY = "dexter:claim:s01e01:dexter_debra_family"
CLAIM_HARRY_FAMILY = "dexter:claim:s01e03:dexter_harry_family"
EVIDENCE_S01E01_01 = "dexter:evidence:s01e01:01"
SOURCE_S01E01 = "dexter:source:s01e01"


@pytest.fixture
def database() -> AsyncIterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db


def _ids(rows: list[dict]) -> set[str]:
    return {row["id"] for row in rows}


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
