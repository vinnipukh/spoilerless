from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.labels import NODE_LABELS  # noqa: F401 — inventory re-exported for importers
from spoilerless.app.graph.ontology import Ontology, load_ontology

PROJECT_ROOT = Path(__file__).resolve().parents[3]
METADATA_DIR = PROJECT_ROOT / "data" / "dexter" / "metadata"
SEED_DIR = PROJECT_ROOT / "data" / "dexter" / "seed"


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
        # PROB-20/#44: a null reveal-point in episodes.json must be stored as
        # the episode's own visible_from_order, never dropped — the driver
        # omits None properties, and a missing key is exactly the 01N52
        # "property key does not exist" class filter.py tripped on live.
        for reveal_key in ("synopsis_visible_from_order", "image_visible_from_order"):
            if episode.get(reveal_key) is None:
                episode[reveal_key] = episode["visible_from_order"]
    return {
        "series": series,
        "episodes": episodes,
        "characters": read_json(SEED_DIR, "characters.json"),
        "events": read_json(SEED_DIR, "events.json"),
        "locations": read_json(SEED_DIR, "locations.json"),
        "organizations": _read_optional_json(SEED_DIR, "organizations.json"),
        "objects": _read_optional_json(SEED_DIR, "objects.json"),
        "claims": read_json(SEED_DIR, "claims.json"),
        "sources": read_json(SEED_DIR, "sources.json"),
        "evidence": read_json(SEED_DIR, "evidence_fragments.json"),
    }


def _read_optional_json(directory: Path, filename: str) -> list[Any]:
    """Read a seed list that may not exist yet (Organization/Object are optional)."""
    path = directory / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def validate_seed(data: dict[str, Any], ontology: Ontology) -> None:
    typed_records: Iterable[dict[str, Any]] = (
        [data["series"]]
        + data["episodes"]
        + data["characters"]
        + data["events"]
        + data["locations"]
        + data["organizations"]
        + data["objects"]
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
    """Create uniqueness constraints and indexes compatible with Neo4j Community.

    Property existence constraints (REQUIRE … IS NOT NULL) require Neo4j
    Enterprise and are intentionally omitted.  Null visibility is prevented
    through Pydantic validation, service-layer guards, and a post-seed
    integrity audit instead.
    """
    for label in NODE_LABELS:
        normalized = label.lower()
        await database.execute_query(
            f"CREATE CONSTRAINT {normalized}_id_unique IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    for label in NODE_LABELS:
        normalized = label.lower()
        await database.execute_query(
            f"CREATE INDEX {normalized}_visible_idx IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.visible_from_order)"
        )
    await database.execute_query(
        "CREATE INDEX episode_order_idx IF NOT EXISTS FOR (n:Episode) ON (n.episode_order)"
    )
    await database.execute_query(
        "CREATE INDEX episode_series_idx IF NOT EXISTS FOR (n:Episode) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX character_series_idx IF NOT EXISTS FOR (n:Character) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX event_series_idx IF NOT EXISTS FOR (n:Event) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX location_series_idx IF NOT EXISTS FOR (n:Location) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX claim_series_idx IF NOT EXISTS FOR (n:Claim) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX source_series_idx IF NOT EXISTS FOR (n:Source) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX evidence_series_idx IF NOT EXISTS FOR (n:EvidenceFragment) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX organization_series_idx IF NOT EXISTS FOR (n:Organization) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX object_series_idx IF NOT EXISTS FOR (n:Object) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX usernote_series_idx IF NOT EXISTS FOR (n:UserNote) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX usernote_target_idx IF NOT EXISTS FOR (n:UserNote) ON (n.series_id, n.target_type, n.target_id)"
    )

    # Revision constraints and indexes
    await database.execute_query(
        "CREATE CONSTRAINT revision_id_unique IF NOT EXISTS FOR (r:Revision) REQUIRE r.id IS UNIQUE"
    )
    await database.execute_query(
        "CREATE INDEX revision_series_idx IF NOT EXISTS FOR (r:Revision) ON (r.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX revision_resource_idx IF NOT EXISTS FOR (r:Revision) ON (r.resource_type, r.resource_id)"
    )
    await database.execute_query(
        "CREATE INDEX revision_created_idx IF NOT EXISTS FOR (r:Revision) ON (r.created_at)"
    )

    # Authentication constraints and indexes
    await database.execute_query(
        "CREATE CONSTRAINT appuser_id_unique IF NOT EXISTS FOR (u:AppUser) REQUIRE u.id IS UNIQUE"
    )
    await database.execute_query(
        "CREATE CONSTRAINT appuser_google_sub_unique IF NOT EXISTS FOR (u:AppUser) REQUIRE u.google_sub IS UNIQUE"
    )
    await database.execute_query(
        "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE"
    )
    await database.execute_query(
        "CREATE CONSTRAINT session_token_hash_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.token_hash IS UNIQUE"
    )
    await database.execute_query(
        "CREATE INDEX session_expires_at_idx IF NOT EXISTS FOR (s:Session) ON (s.expires_at)"
    )

    # Share token constraints and indexes
    await database.execute_query(
        "CREATE CONSTRAINT sharetoken_id_unique IF NOT EXISTS FOR (s:ShareToken) REQUIRE s.id IS UNIQUE"
    )
    await database.execute_query(
        "CREATE CONSTRAINT sharetoken_token_hash_unique IF NOT EXISTS FOR (s:ShareToken) REQUIRE s.token_hash IS UNIQUE"
    )
    await database.execute_query(
        "CREATE INDEX sharetoken_expires_at_idx IF NOT EXISTS FOR (s:ShareToken) ON (s.expires_at)"
    )

    # Chat and watch-progress constraints and indexes (phase 06 GraphRAG chat)
    # UserSeriesProgress is queried by the authenticated user and by series
    # (progress repository); ChatSession denormalizes user_id onto the node
    # (see graph/chat.py) and ChatMessage is listed per session.
    await database.execute_query(
        "CREATE INDEX progress_user_idx IF NOT EXISTS FOR (n:UserSeriesProgress) ON (n.user_id)"
    )
    await database.execute_query(
        "CREATE INDEX progress_series_idx IF NOT EXISTS FOR (n:UserSeriesProgress) ON (n.series_id)"
    )
    await database.execute_query(
        "CREATE INDEX chatsession_user_idx IF NOT EXISTS FOR (n:ChatSession) ON (n.user_id)"
    )
    await database.execute_query(
        "CREATE INDEX chatmessage_session_idx IF NOT EXISTS FOR (n:ChatMessage) ON (n.session_id)"
    )


async def audit_visibility_integrity(database: Neo4jDatabase, series_id: str) -> None:
    """Fail if any node under *series_id* has a null ``visible_from_order``.

    This replaces the Enterprise-only property-existence constraint with a
    run-time integrity gate that fires once during setup — before any
    spoiler-sensitive read could silently leak or hide data.

    ``UserSeriesProgress`` and ``ChatSession`` nodes are excluded: they are
    per-user state, not story content — progress carries the D-05 split
    boundary fields (``watched_through_order``/``view_as_of_order``/
    ``visible_until_order``) and chat sessions carry a
    ``visible_until_order_snapshot``, neither of which is a story reveal-point.
    Including them would fail the gate on every real user's rows (07-02).

    ``ChangeSet`` nodes are excluded for the same reason: they are user
    review-action records (proposed candidate edits), not story content, and
    the domain contract explicitly forbids them from ever declaring
    ``visible_from_order`` (``spoilerless/app/domain/change_set.py``). A real
    user ChangeSet on the seeded series must not trip the seed gate.
    """
    records = await database.execute_query(
        """
        MATCH (node {series_id: $series_id})
        WHERE node.visible_from_order IS NULL
          AND NOT node:UserSeriesProgress
          AND NOT node:ChatSession
          AND NOT node:ChangeSet
        RETURN labels(node) AS labels, node.id AS id
        ORDER BY id
        """,
        series_id=series_id,
    )
    if records:
        offenders = "\n  ".join(
            f"{r['labels'][0] if r['labels'] else '?'} ({r['id']})"
            for r in records
        )
        raise ValueError(
            f"Seed integrity audit failed: {len(records)} node(s) "
            f"with null visible_from_order:\n  {offenders}"
        )


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
    await _upsert_nodes(database, "Organization", data["organizations"])
    await _upsert_nodes(database, "Object", data["objects"])
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
    # Remove stale OCCURRED_IN edges left behind when an event's location_id
    # changes (MERGE only adds; the old edge would otherwise dangle and be
    # rendered as a second, wrong location for the event).
    await database.execute_query(
        """
        MATCH (event:Event)-[rel:OCCURRED_IN]->(location:Location)
        WHERE event.location_id IS NOT NULL AND location.id <> event.location_id
        DELETE rel
        """
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
    await audit_visibility_integrity(database, data["series"]["id"])
    records = await database.execute_query(
        """
        MATCH (node)
        WHERE node.series_id = $series_id
          AND NOT node:UserSeriesProgress
          AND NOT node:ChatSession
          AND NOT node:ChatMessage
        WITH count(node) AS nodes
        MATCH ()-[relationship]->()
        WHERE relationship.series_id = $series_id
        RETURN nodes, count(relationship) AS relationships
        """,
        series_id=data["series"]["id"],
    )
    return records[0]
