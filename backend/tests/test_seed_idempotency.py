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


async def _layer_snapshot(database: Neo4jDatabase, origin: str) -> dict:
    nodes = await database.execute_query(
        """
        MATCH (resource)
        WHERE resource.series_id = $series_id AND resource.origin = $origin
        RETURN resource.id AS id, labels(resource) AS labels, properties(resource) AS properties
        ORDER BY id
        """,
        series_id="series_dexter",
        origin=origin,
    )
    relationships = await database.execute_query(
        """
        MATCH (source)-[relationship]->(target)
        WHERE relationship.series_id = $series_id AND relationship.origin = $origin
        RETURN relationship.id AS id, source.id AS source, target.id AS target,
               type(relationship) AS type, properties(relationship) AS properties
        ORDER BY id
        """,
        series_id="series_dexter",
        origin=origin,
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
        WHERE NOT (claim.origin = 'user' AND claim.claim_type = 'user_authored')
          AND (NOT EXISTS { (claim)-[:SUPPORTED_BY]->(:EvidenceFragment) }
           OR NOT EXISTS { (claim)-[:REFERS_TO]->(:Source) })
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
        "Organization",
        "Object",
        "Claim",
        "Source",
        "EvidenceFragment",
        "UserNote",
    }
    assert missing_visibility == [{"count": 0}]
    assert incomplete_claims == [{"count": 0}]


def test_ontology_rejects_undeclared_seed_type() -> None:
    data = copy.deepcopy(load_seed_data())
    data["characters"][0]["node_type"] = "SpoilerMonster"

    with pytest.raises(OntologyValidationError, match="Undeclared node type"):
        validate_seed(data, load_ontology())


USER_LAYER_CREATE_QUERY = """
MATCH (dexter:Character {id: 'dexter:character:dexter_morgan'})
CREATE (note:UserNote {id: 'user-note:setup-preservation', series_id: 'series_dexter',
  target_type: 'Character', target_id: dexter.id, content: 'preserve me',
  visible_from_order: 1, origin: 'user', created_at: datetime('2026-07-29T12:00:00Z'),
  updated_at: datetime('2026-07-29T12:00:00Z')})
CREATE (note)-[:REFERS_TO {id: 'user-note:setup-preservation:refers_to',
  series_id: 'series_dexter', visible_from_order: 1, origin: 'user'}]->(dexter)
CREATE (character:Character {id: 'user-node:setup-character', series_id: 'series_dexter',
  label: 'User Character', episode_id: 'dexter_s01e01', visible_from_order: 1,
  origin: 'user', created_at: datetime('2026-07-29T12:00:00Z'), updated_at: datetime('2026-07-29T12:00:00Z')})
CREATE (:Event {id: 'user-node:setup-event', series_id: 'series_dexter', label: 'User Event',
  episode_id: 'dexter_s01e01', visible_from_order: 1, origin: 'user'})
CREATE (:Location {id: 'user-node:setup-location', series_id: 'series_dexter', label: 'User Location',
  episode_id: 'dexter_s01e01', visible_from_order: 1, origin: 'user'})
CREATE (:Organization {id: 'user-node:setup-organization', series_id: 'series_dexter',
  label: 'User Organization', episode_id: 'dexter_s01e01', visible_from_order: 1, origin: 'user'})
CREATE (object:Object {id: 'user-node:setup-object', series_id: 'series_dexter', label: 'User Object',
  episode_id: 'dexter_s01e01', visible_from_order: 1, origin: 'user'})
CREATE (:Claim {id: 'user-rel:setup-preservation', series_id: 'series_dexter',
  subject_id: character.id, object_id: object.id, predicate: 'KNOWS',
  claim_type: 'user_authored', episode_id: 'dexter_s01e01', visible_from_order: 1,
  origin: 'user', created_at: datetime('2026-07-29T12:00:00Z'), updated_at: datetime('2026-07-29T12:00:00Z')})
"""

USER_LAYER_CLEANUP_QUERY = """
MATCH (resource)
WHERE resource.origin = 'user' AND (
  coalesce(resource.id, '') STARTS WITH 'user-node:setup-'
  OR resource.id IN ['user-note:setup-preservation', 'user-rel:setup-preservation'])
DETACH DELETE resource
"""


@pytest.mark.asyncio
async def test_setup_preserves_user_layer_and_deleted_resources_stay_deleted(
    live_database: Neo4jDatabase,
) -> None:
    await live_database.execute_query(USER_LAYER_CLEANUP_QUERY)
    try:
        await setup_database(live_database)
        canonical_before = await _layer_snapshot(live_database, "canonical")
        assert sum(len(layer) for layer in canonical_before.values()) == 67

        await live_database.execute_query(USER_LAYER_CREATE_QUERY)
        user_before = await _layer_snapshot(live_database, "user")
        first_report = await setup_database(live_database)
        second_report = await setup_database(live_database)

        assert first_report == second_report == {"nodes": 48, "relationships": 27}
        assert await _layer_snapshot(live_database, "canonical") == canonical_before
        assert await _layer_snapshot(live_database, "user") == user_before

        incomplete = await live_database.execute_query(
            """
            MATCH (claim:Claim {series_id: 'series_dexter'})
            WHERE NOT EXISTS { (claim)-[:SUPPORTED_BY]->(:EvidenceFragment) }
               OR NOT EXISTS { (claim)-[:REFERS_TO]->(:Source) }
            RETURN claim.id AS id, claim.origin AS origin, claim.claim_type AS claim_type
            ORDER BY id
            """
        )
        assert incomplete == [{
            "id": "user-rel:setup-preservation",
            "origin": "user",
            "claim_type": "user_authored",
        }]

        constraints = await live_database.execute_query(
            "SHOW CONSTRAINTS YIELD name RETURN name ORDER BY name"
        )
        indexes = await live_database.execute_query(
            "SHOW INDEXES YIELD name RETURN name ORDER BY name"
        )
        constraint_names = [row["name"] for row in constraints]
        index_names = [row["name"] for row in indexes]
        assert len(constraint_names) == len(set(constraint_names))
        assert len(index_names) == len(set(index_names))

        await live_database.execute_query(
            "MATCH (node:Object {id: 'user-node:setup-object', origin: 'user'}) DETACH DELETE node"
        )
        await setup_database(live_database)
        deleted = await live_database.execute_query(
            "MATCH (node {id: 'user-node:setup-object'}) RETURN node.id AS id"
        )
        assert deleted == []
        assert await _layer_snapshot(live_database, "canonical") == canonical_before
    finally:
        await live_database.execute_query(USER_LAYER_CLEANUP_QUERY)
