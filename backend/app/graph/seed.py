from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from neo4j.exceptions import DatabaseError

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.ontology import Ontology, load_ontology

PROJECT_ROOT = Path(__file__).resolve().parents[3]
METADATA_DIR = PROJECT_ROOT / "data" / "dexter" / "metadata"
SEED_DIR = PROJECT_ROOT / "data" / "dexter" / "seed"

NODE_LABELS = (
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
)
SPOILER_LABELS = NODE_LABELS
RELATIONSHIP_TYPES = (
    "PART_OF",
    "PRECEDES",
    "OCCURRED_IN",
    "SUPPORTED_BY",
    "REFERS_TO",
)


def read_json(directory: Path, filename: str) -> Any:
    path = directory / filename
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_seed_data() -> dict[str, Any]:
    series = read_json(METADATA_DIR, "series.json")
    series.update(
        {
            "node_type": "Series",
            "series_id": series["id"],
            "label": series["title"],
            "visible_from_order": 1,
            "origin": "canonical",
        }
    )
    episodes = read_json(METADATA_DIR, "episodes.json")
    for episode in episodes:
        episode.update(
            {
                "node_type": "Episode",
                "label": f'{episode["code"]}: {episode["title"]}',
                "origin": "canonical",
            }
        )
    return {
        "series": series,
        "episodes": episodes,
        "characters": read_json(SEED_DIR, "characters.json"),
        "events": read_json(SEED_DIR, "events.json"),
        "locations": read_json(SEED_DIR, "locations.json"),
        "claims": read_json(SEED_DIR, "claims.json"),
        "sources": read_json(SEED_DIR, "sources.json"),
        "evidence": read_json(SEED_DIR, "evidence_fragments.json"),
    }


def validate_seed(data: dict[str, Any], ontology: Ontology) -> None:
    typed_records: Iterable[dict[str, Any]] = (
        [data["series"]]
        + data["episodes"]
        + data["characters"]
        + data["events"]
        + data["locations"]
        + data["claims"]
        + data["sources"]
        + data["evidence"]
    )
    ids: set[str] = set()
    for record in typed_records:
        ontology.require_node_type(record["node_type"])
        if not isinstance(record.get("visible_from_order"), int):
            raise ValueError(f'visible_from_order must be INTEGER: {record.get("id")}')
        if record["id"] in ids:
            raise ValueError(f'Duplicate deterministic ID: {record["id"]}')
        ids.add(record["id"])

    for relationship_type in RELATIONSHIP_TYPES:
        ontology.require_relationship_type(relationship_type)

    for claim in data["claims"]:
        ontology.require_claim_type(claim["claim_type"])
        ontology.require_claim_status(claim["status"])
        ontology.require_confidence_level(claim["confidence_level"])
        ontology.require_relationship_type(claim["predicate"])
        if claim.get("ontology_version") != ontology.version:
            raise ValueError(f'Claim ontology version mismatch: {claim["id"]}')
        if claim["subject_id"] not in ids or claim["object_id"] not in ids:
            raise ValueError(f'Claim endpoint is missing: {claim["id"]}')
        if not claim.get("evidence_ids") or claim["source_id"] not in ids:
            raise ValueError(f'Claim provenance is incomplete: {claim["id"]}')
        if any(evidence_id not in ids for evidence_id in claim["evidence_ids"]):
            raise ValueError(f'Claim evidence is missing: {claim["id"]}')


async def create_constraints(database: Neo4jDatabase) -> None:
    queries: list[str] = []
    for label in NODE_LABELS:
        normalized = label.lower()
        queries.append(
            f"CREATE CONSTRAINT {normalized}_id_unique IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    for label in SPOILER_LABELS:
        normalized = label.lower()
        queries.append(
            f"CREATE CONSTRAINT {normalized}_visible_exists IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.visible_from_order IS NOT NULL"
        )
        queries.append(
            f"CREATE INDEX {normalized}_visible_idx IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.visible_from_order)"
        )
    queries.extend(
        [
            "CREATE INDEX episode_order_idx IF NOT EXISTS FOR (n:Episode) ON (n.episode_order)",
            "CREATE INDEX episode_series_idx IF NOT EXISTS FOR (n:Episode) ON (n.series_id)",
            "CREATE INDEX character_series_idx IF NOT EXISTS FOR (n:Character) ON (n.series_id)",
            "CREATE INDEX event_series_idx IF NOT EXISTS FOR (n:Event) ON (n.series_id)",
            "CREATE INDEX location_series_idx IF NOT EXISTS FOR (n:Location) ON (n.series_id)",
            "CREATE INDEX claim_series_idx IF NOT EXISTS FOR (n:Claim) ON (n.series_id)",
            "CREATE INDEX source_series_idx IF NOT EXISTS FOR (n:Source) ON (n.series_id)",
            "CREATE INDEX evidence_series_idx IF NOT EXISTS FOR (n:EvidenceFragment) ON (n.series_id)",
            "CREATE INDEX organization_series_idx IF NOT EXISTS FOR (n:Organization) ON (n.series_id)",
            "CREATE INDEX object_series_idx IF NOT EXISTS FOR (n:Object) ON (n.series_id)",
            "CREATE INDEX usernote_series_idx IF NOT EXISTS FOR (n:UserNote) ON (n.series_id)",
            "CREATE INDEX usernote_target_idx IF NOT EXISTS FOR (n:UserNote) ON (n.series_id, n.target_type, n.target_id)",
        ]
    )
    for query in queries:
        try:
            await database.execute_query(query)
        except DatabaseError as exc:
            if "existence constraint" not in str(exc).lower():
                raise
            # Neo4j Community does not support property-existence constraints.
            # Fixture validation and acceptance queries enforce the same invariant.


async def _upsert_nodes(
    database: Neo4jDatabase,
    label: str,
    rows: list[dict[str, Any]],
) -> None:
    await database.execute_query(
        f"""
        UNWIND $rows AS row
        MERGE (node:{label} {{id: row.id}})
        SET node += row
        """,
        rows=rows,
    )


async def seed_graph(database: Neo4jDatabase, data: dict[str, Any]) -> None:
    await _upsert_nodes(database, "Series", [data["series"]])
    await _upsert_nodes(database, "Episode", data["episodes"])
    await _upsert_nodes(database, "Character", data["characters"])
    await _upsert_nodes(database, "Event", data["events"])
    await _upsert_nodes(database, "Location", data["locations"])
    await _upsert_nodes(database, "Source", data["sources"])
    await _upsert_nodes(database, "EvidenceFragment", data["evidence"])
    await _upsert_nodes(database, "Claim", data["claims"])

    await database.execute_query(
        """
        MATCH ()-[legacy:PART_OF|PRECEDES]->()
        WHERE legacy.id IS NULL
        DELETE legacy
        """
    )
    await database.execute_query(
        """
        UNWIND $episodes AS row
        MATCH (episode:Episode {id: row.id})
        MATCH (series:Series {id: row.series_id})
        MERGE (episode)-[rel:PART_OF]->(series)
        SET rel.id = row.id + ':part_of',
            rel.series_id = row.series_id,
            rel.visible_from_order = row.visible_from_order,
            rel.origin = 'canonical'
        """,
        episodes=data["episodes"],
    )
    await database.execute_query(
        """
        UNWIND $episodes AS row
        MATCH (first:Episode {series_id: row.series_id, episode_order: row.episode_order})
        MATCH (second:Episode {series_id: row.series_id, episode_order: row.episode_order + 1})
        MERGE (first)-[rel:PRECEDES]->(second)
        SET rel.id = first.id + ':precedes:' + second.id,
            rel.series_id = row.series_id,
            rel.visible_from_order = second.visible_from_order,
            rel.origin = 'canonical'
        """,
        episodes=data["episodes"],
    )
    await database.execute_query(
        """
        UNWIND $events AS row
        MATCH (event:Event {id: row.id})
        MATCH (location:Location {id: row.location_id})
        MERGE (event)-[rel:OCCURRED_IN {id: row.id + ':occurred_in:' + row.location_id}]->(location)
        SET rel.series_id = row.series_id,
            rel.visible_from_order = row.visible_from_order,
            rel.origin = 'canonical'
        """,
        events=data["events"],
    )
    await database.execute_query(
        """
        UNWIND $claims AS row
        MATCH (claim:Claim {id: row.id})
        UNWIND row.evidence_ids AS evidence_id
        MATCH (evidence:EvidenceFragment {id: evidence_id})
        MERGE (claim)-[rel:SUPPORTED_BY {id: row.id + ':supported_by:' + evidence_id}]->(evidence)
        SET rel.series_id = row.series_id,
            rel.visible_from_order = row.visible_from_order,
            rel.origin = 'canonical'
        """,
        claims=data["claims"],
    )
    await database.execute_query(
        """
        UNWIND $claims AS row
        MATCH (claim:Claim {id: row.id})
        MATCH (source:Source {id: row.source_id})
        MERGE (claim)-[rel:REFERS_TO {id: row.id + ':refers_to:' + row.source_id}]->(source)
        SET rel.series_id = row.series_id,
            rel.visible_from_order = row.visible_from_order,
            rel.origin = 'canonical'
        """,
        claims=data["claims"],
    )


async def setup_database(database: Neo4jDatabase) -> dict[str, int]:
    data = load_seed_data()
    validate_seed(data, load_ontology())
    await create_constraints(database)
    await seed_graph(database, data)
    records = await database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id
        WITH count(node) AS nodes
        MATCH ()-[relationship]->()
        WHERE relationship.series_id = $series_id
        RETURN nodes, count(relationship) AS relationships
        """,
        series_id="series_dexter",
    )
    return records[0]
