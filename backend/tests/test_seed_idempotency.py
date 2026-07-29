from __future__ import annotations

import copy
from typing import AsyncIterator

import pytest
import pytest_asyncio

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.ontology import OntologyValidationError, load_ontology
from backend.app.graph.seed import load_seed_data, setup_database, validate_seed


@pytest_asyncio.fixture
async def live_database() -> AsyncIterator[Neo4jDatabase]:
    database = Neo4jDatabase()
    database.open()
    await database.verify_connection()
    try:
        yield database
    finally:
        await database.close()


async def _snapshot(database: Neo4jDatabase) -> dict:
    nodes = await database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id
        RETURN labels(node)[0] AS label, collect(node.id) AS ids, count(node) AS count
        ORDER BY label
        """,
        series_id="series_dexter",
    )
    relationships = await database.execute_query(
        """
        MATCH ()-[relationship]->()
        WHERE relationship.series_id = $series_id
        RETURN type(relationship) AS type,
               collect(relationship.id) AS ids,
               count(relationship) AS count
        ORDER BY type
        """,
        series_id="series_dexter",
    )
    return {"nodes": nodes, "relationships": relationships}


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_complete(live_database: Neo4jDatabase) -> None:
    first_counts = await setup_database(live_database)
    first = await _snapshot(live_database)
    second_counts = await setup_database(live_database)
    second = await _snapshot(live_database)

    assert first_counts == second_counts == {"nodes": 41, "relationships": 26}
    assert first == second
    assert {row["label"]: row["count"] for row in first["nodes"]} == {
        "Character": 9,
        "Claim": 9,
        "Episode": 3,
        "Event": 3,
        "EvidenceFragment": 9,
        "Location": 4,
        "Series": 1,
        "Source": 3,
    }
    assert all(len(row["ids"]) == len(set(row["ids"])) for row in first["nodes"])
    assert all(
        len(row["ids"]) == len(set(row["ids"])) for row in first["relationships"]
    )


@pytest.mark.asyncio
async def test_constraints_visibility_and_provenance(live_database: Neo4jDatabase) -> None:
    await setup_database(live_database)
    constraints = await live_database.execute_query(
        """
        SHOW CONSTRAINTS YIELD type, labelsOrTypes, properties
        WHERE type = 'NODE_PROPERTY_UNIQUENESS' AND properties = ['id']
        RETURN labelsOrTypes[0] AS label
        ORDER BY label
        """
    )
    missing_visibility = await live_database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id AND node.visible_from_order IS NULL
        RETURN count(node) AS count
        """,
        series_id="series_dexter",
    )
    incomplete_claims = await live_database.execute_query(
        """
        MATCH (claim:Claim {series_id: $series_id})
        WHERE NOT EXISTS { (claim)-[:SUPPORTED_BY]->(:EvidenceFragment) }
           OR NOT EXISTS { (claim)-[:REFERS_TO]->(:Source) }
        RETURN count(claim) AS count
        """,
        series_id="series_dexter",
    )

    assert {row["label"] for row in constraints} == {
        "Series",
        "Episode",
        "Character",
        "Event",
        "Location",
        "Claim",
        "Source",
        "EvidenceFragment",
    }
    assert missing_visibility == [{"count": 0}]
    assert incomplete_claims == [{"count": 0}]


def test_ontology_rejects_undeclared_seed_type() -> None:
    data = copy.deepcopy(load_seed_data())
    data["characters"][0]["node_type"] = "SpoilerMonster"

    with pytest.raises(OntologyValidationError, match="Undeclared node type"):
        validate_seed(data, load_ontology())
