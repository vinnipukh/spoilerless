"""Allowlisted retrieval tools (RAG-02, RAG-03) — this plan ships exactly two.

Every tool independently enforces the spoiler boundary:
``visible_until_order`` is a keyword parameter supplied by the pipeline caller
(the server-resolved persisted boundary) — it is NEVER read from the model's
tool-call JSON arguments.  Queries are fully parameterized; labels come from a
server allowlist derived from ``backend/app/graph/ontology.py`` (the
``narrative`` group), never from request/model input.  Hidden resources behave
exactly like missing ones (fail closed) — both return the same empty result.
"""

from __future__ import annotations

from typing import Any

from backend.app.graph.database import Neo4jDatabase
from backend.app.graph.ontology import load_ontology

# Server-owned allowlist of story node labels, derived from the ontology's
# narrative group (Character, Location, Organization, Object, Event).
_ONTOLOGY = load_ontology()
STORY_NODE_LABELS = frozenset(_ONTOLOGY.node_type_groups["narrative"])

MAX_TRAVERSAL_DEPTH = 3

GET_ENTITY_QUERY = """\
MATCH (node)
WHERE node.id = $entity_id
  AND node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id,
       [label IN labels(node) WHERE label IN $allowed_labels][0] AS type,
       node.label AS label,
       node.visible_from_order AS visible_from_order,
       node.origin AS origin
"""

CLAIMS_FOR_FRONTIER_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})
WHERE claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND (claim.subject_id IN $frontier OR claim.object_id IN $frontier)
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order <= $visible_until_order
RETURN claim.id AS id,
       claim.label AS label,
       claim.subject_id AS subject_id,
       claim.object_id AS object_id,
       claim.predicate AS predicate,
       claim.claim_type AS claim_type,
       claim.status AS status,
       claim.confidence_level AS confidence_level,
       claim.episode_id AS episode_id,
       claim.source_id AS source_id,
       claim.visible_from_order AS visible_from_order,
       claim.origin AS origin
ORDER BY claim.visible_from_order, claim.id
"""

NODES_BY_IDS_QUERY = """\
MATCH (node)
WHERE node.id IN $node_ids
  AND node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id,
       [label IN labels(node) WHERE label IN $allowed_labels][0] AS type,
       node.label AS label,
       node.visible_from_order AS visible_from_order,
       node.origin AS origin
ORDER BY node.visible_from_order, node.id
"""

EVIDENCE_FOR_CLAIMS_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
WHERE claim.id IN $claim_ids
  AND supported.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order <= $visible_until_order
RETURN evidence.id AS id,
       evidence.label AS label,
       evidence.episode_id AS episode_id,
       evidence.source_id AS source_id,
       evidence.text AS text,
       evidence.locator AS locator,
       evidence.visible_from_order AS visible_from_order,
       evidence.origin AS origin,
       claim.id AS claim_id
ORDER BY evidence.visible_from_order, evidence.id
"""

SOURCES_FOR_CLAIMS_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})-[ref:REFERS_TO]->(source:Source)
WHERE claim.id IN $claim_ids
  AND ref.visible_from_order <= $visible_until_order
  AND source.visible_from_order <= $visible_until_order
RETURN source.id AS id,
       source.label AS label,
       source.episode_id AS episode_id,
       source.source_type AS source_type,
       source.locator AS locator,
       source.visible_from_order AS visible_from_order,
       source.origin AS origin,
       claim.id AS claim_id
ORDER BY source.visible_from_order, source.id
"""

EPISODE_CODES_QUERY = """\
MATCH (episode:Episode)
WHERE episode.id IN $episode_ids
RETURN episode.id AS id, episode.code AS code
"""


async def get_entity(
    database: Neo4jDatabase,
    *,
    entity_id: str,
    series_id: str,
    visible_until_order: int,
) -> dict[str, Any] | None:
    """Return one story node visible at the boundary, or ``None``.

    ``None`` covers both hidden and missing — indistinguishable, by design.
    """
    records = await database.execute_query(
        GET_ENTITY_QUERY,
        entity_id=entity_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
        allowed_labels=sorted(STORY_NODE_LABELS),
    )
    return records[0] if records else None


async def get_neighborhood(
    database: Neo4jDatabase,
    *,
    entity_id: str,
    series_id: str,
    visible_until_order: int,
    depth: int = 1,
) -> dict[str, Any]:
    """Return the visible neighborhood around *entity_id* up to *depth* hops.

    Result shape: ``{entity, nodes, edges, claims, evidence, sources}`` where
    every list contains only resources visible at *visible_until_order* and
    ``edges`` are projected from the visible claims (``{claim.id}:edge``).
    A hidden or missing entity yields an all-empty result (fail closed).
    """
    depth = max(1, min(int(depth), MAX_TRAVERSAL_DEPTH))

    entity = await get_entity(
        database,
        entity_id=entity_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    if entity is None:
        return {
            "entity": None,
            "nodes": [],
            "edges": [],
            "claims": [],
            "evidence": [],
            "sources": [],
        }

    frontier: list[str] = [entity_id]
    visited: set[str] = {entity_id}
    claims: list[dict[str, Any]] = []
    claim_ids: set[str] = set()

    for _ in range(depth):
        rows = await database.execute_query(
            CLAIMS_FOR_FRONTIER_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
            frontier=frontier,
        )
        new_claims = [row for row in rows if row["id"] not in claim_ids]
        if not new_claims:
            break
        claims.extend(new_claims)
        claim_ids.update(row["id"] for row in new_claims)

        next_frontier: set[str] = set()
        for row in new_claims:
            if row["subject_id"] not in visited:
                next_frontier.add(row["subject_id"])
            if row["object_id"] not in visited:
                next_frontier.add(row["object_id"])
        if not next_frontier:
            break
        visited.update(next_frontier)
        frontier = sorted(next_frontier)

    nodes = await database.execute_query(
        NODES_BY_IDS_QUERY,
        node_ids=sorted(visited),
        series_id=series_id,
        visible_until_order=visible_until_order,
        allowed_labels=sorted(STORY_NODE_LABELS),
    )
    evidence = await database.execute_query(
        EVIDENCE_FOR_CLAIMS_QUERY,
        claim_ids=sorted(claim_ids),
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    sources = await database.execute_query(
        SOURCES_FOR_CLAIMS_QUERY,
        claim_ids=sorted(claim_ids),
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    edges = [
        {
            "id": f"{claim['id']}:edge",
            "source": claim["subject_id"],
            "target": claim["object_id"],
            "type": claim["predicate"],
            "visible_from_order": claim["visible_from_order"],
            "origin": claim["origin"],
            "claim_id": claim["id"],
        }
        for claim in claims
    ]

    return {
        "entity": entity,
        "nodes": nodes,
        "edges": edges,
        "claims": claims,
        "evidence": evidence,
        "sources": sources,
    }


async def fetch_episode_codes(
    database: Neo4jDatabase, episode_ids: set[str]
) -> dict[str, str]:
    """Map episode node ids (``dexter_s01e01``) to display codes (``S01E01``)."""
    if not episode_ids:
        return {}
    records = await database.execute_query(
        EPISODE_CODES_QUERY, episode_ids=sorted(episode_ids)
    )
    return {record["id"]: record["code"] for record in records}
