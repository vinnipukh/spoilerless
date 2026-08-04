from __future__ import annotations

import copy
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.ontology import OntologyValidationError, load_ontology
from backend.app.graph.seed import (
    audit_visibility_integrity,
    load_seed_data,
    setup_database,
    validate_seed,
)


@pytest_asyncio.fixture
async def live_database() -> AsyncIterator[Neo4jDatabase]:
    database = Neo4jDatabase()
    database.open()
    await database.verify_connection()
    try:
        yield database
    finally:
        await database.close()


SERIES_ID = "series_dexter"
NULLABLE_ID = "seed-test:null-visibility"
CLEANUP_NULL_NODE = """
MATCH (resource {id: $id}) DETACH DELETE resource
"""


async def _snapshot(database: Neo4jDatabase) -> dict:
    nodes = await database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id
        RETURN labels(node)[0] AS label, collect(node.id) AS ids, count(node) AS count
        ORDER BY label
        """,
        series_id=SERIES_ID,
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
        series_id=SERIES_ID,
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
        series_id=SERIES_ID,
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
        series_id=SERIES_ID,
        origin=origin,
    )
    return {"nodes": nodes, "relationships": relationships}


# ── Seed idempotency & completeness ──


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_complete(live_database: Neo4jDatabase) -> None:
    # Clean any leftover user content + revisions from other test modules
    await live_database.execute_query(
        "MATCH (n:UserNote) DETACH DELETE n"
    )
    await live_database.execute_query(
        "MATCH (r:Revision) DETACH DELETE r"
    )
    await live_database.execute_query(
        "MATCH (c:Claim) WHERE c.claim_type = 'user_authored' OR c.id STARTS WITH 'user-' DETACH DELETE c"
    )
    await live_database.execute_query(
        "MATCH (n) WHERE n.origin = 'user' OR n.id STARTS WITH 'user-' DETACH DELETE n"
    )
    first_counts = await setup_database(live_database)
    first = await _snapshot(live_database)
    second_counts = await setup_database(live_database)
    second = await _snapshot(live_database)

    assert first_counts == second_counts == {"nodes": 265, "relationships": 254}
    assert first == second
    assert {row["label"]: row["count"] for row in first["nodes"]} == {
        "Character": 32,
        "Claim": 105,
        "Episode": 3,
        "Event": 39,
        "EvidenceFragment": 36,
        "Location": 24,
        "Object": 17,
        "Organization": 5,
        "Series": 1,
        "Source": 3,
    }
    assert all(len(row["ids"]) == len(set(row["ids"])) for row in first["nodes"])
    assert all(
        len(row["ids"]) == len(set(row["ids"])) for row in first["relationships"]
    )


# ── Community-compatible schema ──


@pytest.mark.asyncio
async def test_community_schema_creates_only_unique_and_index(
    live_database: Neo4jDatabase,
) -> None:
    """Uniqueness constraints and indexes work on Community; no property-existence constraints."""
    await setup_database(live_database)

    constraint_types = await live_database.execute_query(
        """
        SHOW CONSTRAINTS YIELD type, labelsOrTypes, properties
        RETURN type, labelsOrTypes[0] AS label, properties
        ORDER BY label
        """
    )
    for ct in constraint_types:
        assert ct["type"] in ("NODE_PROPERTY_UNIQUENESS", "NODE_KEY"), (
            f"Unexpected constraint type {ct['type']} on {ct['label']}"
        )
        # Every unique/node-key constraint must cover `id` (our schema invariant),
        # except AppUser (google_sub is the identity key) and Session (token_hash).
        if ct["label"] not in ("AppUser", "Session"):
            assert "id" in ct["properties"], (
                f"Constraint on {ct['label']} missing id property: {ct['properties']}"
            )

    unique_labels = {ct["label"] for ct in constraint_types}
    expected_labels = {
        "Series", "Episode", "Character", "Event", "Location",
        "Organization", "Object", "Claim", "Source", "EvidenceFragment", "UserNote",
        "AppUser", "Session", "Revision",
    }
    assert unique_labels == expected_labels, (
        f"Missing uniqueness constraints for: {expected_labels - unique_labels}"
    )

    # Verify no property-existence constraints exist
    existence = await live_database.execute_query(
        """
        SHOW CONSTRAINTS YIELD type
        WHERE type = 'NODE_PROPERTY_EXISTENCE'
        RETURN count(*) AS count
        """
    )
    assert existence == [{"count": 0}], "Property existence constraints should not exist on Community"


# ── Seed integrity audit ──


@pytest.mark.asyncio
async def test_audit_visibility_integrity_passes_after_seed(
    live_database: Neo4jDatabase,
) -> None:
    await setup_database(live_database)
    # The audit runs inside setup_database automatically; this confirms
    # a direct call also passes.
    await audit_visibility_integrity(live_database, SERIES_ID)


@pytest.mark.asyncio
async def test_audit_visibility_integrity_rejects_null_visibility(
    live_database: Neo4jDatabase,
) -> None:
    await setup_database(live_database)
    await live_database.execute_query(
        """
        CREATE (:Character {id: $id, series_id: $series_id, label: 'Ghost',
                origin: 'canonical', visible_from_order: null})
        """,
        id=NULLABLE_ID,
        series_id=SERIES_ID,
    )
    try:
        with pytest.raises(ValueError, match="null visible_from_order"):
            await audit_visibility_integrity(live_database, SERIES_ID)
    finally:
        await live_database.execute_query(CLEANUP_NULL_NODE, id=NULLABLE_ID)


# ── Null visibility → fail-closed reads ──


@pytest.mark.asyncio
async def test_read_never_returns_null_visibility_node(
    live_database: Neo4jDatabase,
) -> None:
    """A node with null visible_from_order must never appear in graph reads."""
    await setup_database(live_database)
    await live_database.execute_query(
        """
        CREATE (:Character {id: $id, series_id: $series_id, label: 'Invisible Ghost',
                origin: 'canonical', visible_from_order: null})
        """,
        id=NULLABLE_ID,
        series_id=SERIES_ID,
    )
    try:
        nodes = await live_database.execute_query(
            """
            MATCH (node {series_id: $series_id})
            WHERE node.visible_from_order <= $boundary
            RETURN node.id AS id
            """,
            series_id=SERIES_ID,
            boundary=999,
        )
        assert NULLABLE_ID not in {row["id"] for row in nodes}, (
            f"Node with null visibility should not appear in read results"
        )
    finally:
        await live_database.execute_query(CLEANUP_NULL_NODE, id=NULLABLE_ID)


# ── Write rejection when visibility cannot be derived ──


@pytest.mark.asyncio
async def test_note_write_rejects_null_visibility_target(
    live_database: Neo4jDatabase,
) -> None:
    """Creating a note against a null-visibility target must raise UserContentNotFound."""
    await setup_database(live_database)
    await live_database.execute_query(
        """
        CREATE (:Character {id: $id, series_id: $series_id, label: 'Ghost',
                origin: 'canonical', visible_from_order: null})
        """,
        id=NULLABLE_ID,
        series_id=SERIES_ID,
    )
    try:
        from backend.app.graph.database import Neo4jDatabase as DB
        from backend.app.repository.user_content import (
            UserContentRepository,
            UserContentNotFound,
        )
        from backend.app.domain.user_content import NoteCreate

        repo = UserContentRepository(live_database)
        note = NoteCreate(
            target_type="Character",
            target_id=NULLABLE_ID,
            content="This should not be creatable",
        )
        with pytest.raises(UserContentNotFound, match="note target not found"):
            await repo.create_note(SERIES_ID, note)
    finally:
        await live_database.execute_query(CLEANUP_NULL_NODE, id=NULLABLE_ID)


@pytest.mark.asyncio
async def test_custom_node_write_rejects_null_episode(
    live_database: Neo4jDatabase,
) -> None:
    """Creating a custom node against a null-order episode must raise UserContentNotFound."""
    await setup_database(live_database)
    null_ep_id = "seed-test:null-episode"
    await live_database.execute_query(
        """
        CREATE (:Episode {id: $eid, series_id: $series_id, code: 'GHOST',
                title: 'Ghost Episode', episode_order: null, visible_from_order: 1,
                origin: 'canonical'})
        """,
        eid=null_ep_id,
        series_id=SERIES_ID,
    )
    try:
        from backend.app.graph.database import Neo4jDatabase as DB
        from backend.app.repository.user_content import (
            UserContentRepository,
            UserContentNotFound,
        )
        from backend.app.domain.user_content import CustomNodeCreate, CustomNodeType

        repo = UserContentRepository(live_database)
        custom = CustomNodeCreate(
            node_type=CustomNodeType.OBJECT,
            label="Null Object",
            episode_id=null_ep_id,
        )
        with pytest.raises(UserContentNotFound, match="episode not found"):
            await repo.create_custom_node(SERIES_ID, custom)
    finally:
        await live_database.execute_query(
            "MATCH (n:Episode {id: $id}) DETACH DELETE n", id=null_ep_id
        )


# ── Claim provenance ──


@pytest.mark.asyncio
async def test_constraints_visibility_and_provenance(live_database: Neo4jDatabase) -> None:
    """Uniqueness constraints exist, no node has null visibility, all claims have provenance."""
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
        series_id=SERIES_ID,
    )
    incomplete_claims = await live_database.execute_query(
        """
        MATCH (claim:Claim {series_id: $series_id})
        WHERE NOT (claim.origin = 'user' AND claim.claim_type = 'user_authored')
          AND (NOT EXISTS { (claim)-[:SUPPORTED_BY]->(:EvidenceFragment) }
           OR NOT EXISTS { (claim)-[:REFERS_TO]->(:Source) })
        RETURN count(claim) AS count
        """,
        series_id=SERIES_ID,
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
        "AppUser",
        "Session",
        "Revision",
    }
    assert missing_visibility == [{"count": 0}]
    assert incomplete_claims == [{"count": 0}]


# ── Seed validation ──


def test_ontology_rejects_undeclared_seed_type() -> None:
    data = copy.deepcopy(load_seed_data())
    data["characters"][0]["node_type"] = "SpoilerMonster"

    with pytest.raises(OntologyValidationError, match="Undeclared node type"):
        validate_seed(data, load_ontology())


# ── User-layer preservation ──


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
