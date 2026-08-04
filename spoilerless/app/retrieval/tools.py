"""Allowlisted retrieval tools (RAG-02, RAG-03) — the full ten-tool allowlist.

Every tool independently enforces the spoiler boundary:
``visible_until_order`` is a keyword parameter supplied by the pipeline caller
(the server-resolved persisted boundary) — it is NEVER read from the model's
tool-call JSON arguments.  Queries are fully parameterized; labels come from a
server allowlist derived from ``spoilerless/app/graph/ontology.py`` (the
``narrative`` group), never from request/model input.  Hidden resources behave
exactly like missing ones (fail closed) — both return the same empty result.
No tool accepts a raw Cypher fragment at any layer (06-PRD-SOURCE.md §5).
"""

from __future__ import annotations

from typing import Any

from spoilerless.app.core.config import get_settings
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.graph.ontology import load_ontology

# Server-owned allowlist of story node labels, derived from the ontology's
# narrative group (Character, Location, Organization, Object, Event).
_ONTOLOGY = load_ontology()
STORY_NODE_LABELS = frozenset(_ONTOLOGY.node_type_groups["narrative"])

MAX_TRAVERSAL_DEPTH = 3
# Fixed server-side ceilings: requested depths/hops/limits are clamped to
# these, never honored above them (RAG-02 bounded traversal / result counts).
MAX_PATH_HOPS = 4
MAX_SEARCH_RESULTS = 25
MAX_RESULT_LIMIT = 50

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
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND (claim.subject_id IN $frontier OR claim.object_id IN $frontier)
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
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
  AND supported.visible_from_order IS NOT NULL
  AND supported.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order IS NOT NULL
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
  AND ref.visible_from_order IS NOT NULL
  AND ref.visible_from_order <= $visible_until_order
  AND source.visible_from_order IS NOT NULL
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

SEARCH_ENTITIES_QUERY = """\
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
  AND (
    toLower(coalesce(node.label, '')) CONTAINS toLower($search_term)
    OR any(alias IN coalesce(node.aliases, []) WHERE toLower(alias) CONTAINS toLower($search_term))
  )
RETURN node.id AS id,
       [label IN labels(node) WHERE label IN $allowed_labels][0] AS type,
       node.label AS label,
       node.visible_from_order AS visible_from_order,
       node.origin AS origin
ORDER BY node.visible_from_order, node.id
LIMIT $limit
"""

TIMELINE_QUERY = """\
MATCH (episode:Episode {series_id: $series_id})
WHERE episode.visible_from_order IS NOT NULL
  AND episode.visible_from_order <= $visible_until_order
RETURN episode.id AS id,
       episode.code AS code,
       episode.title AS title,
       episode.episode_order AS episode_order,
       episode.visible_from_order AS visible_from_order
ORDER BY episode.episode_order
LIMIT $limit
"""

# Standalone list variants of the shared queries with a server-bounded LIMIT
# (the shared forms are used by get_neighborhood, which bounds per level).
GET_CLAIMS_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND (claim.subject_id IN $entity_ids OR claim.object_id IN $entity_ids)
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
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
LIMIT $limit
"""

GET_EVIDENCE_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
WHERE claim.id IN $claim_ids
  AND supported.visible_from_order IS NOT NULL
  AND supported.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order IS NOT NULL
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
LIMIT $limit
"""

GET_SOURCES_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})-[ref:REFERS_TO]->(source:Source)
WHERE claim.id IN $claim_ids
  AND ref.visible_from_order IS NOT NULL
  AND ref.visible_from_order <= $visible_until_order
  AND source.visible_from_order IS NOT NULL
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
LIMIT $limit
"""

GRAPH_SUMMARY_COUNTS_QUERY = """\
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
WITH count(node) AS entities
OPTIONAL MATCH (claim:Claim {series_id: $series_id})
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
  AND EXISTS {
    MATCH (subject {id: claim.subject_id, series_id: $series_id})
    WHERE subject.visible_from_order IS NOT NULL
      AND subject.visible_from_order <= $visible_until_order
  }
  AND EXISTS {
    MATCH (object {id: claim.object_id, series_id: $series_id})
    WHERE object.visible_from_order IS NOT NULL
      AND object.visible_from_order <= $visible_until_order
  }
WITH entities, count(claim) AS claims
OPTIONAL MATCH (evidence:EvidenceFragment {series_id: $series_id})
WHERE evidence.visible_from_order IS NOT NULL
  AND evidence.visible_from_order <= $visible_until_order
WITH entities, claims, count(evidence) AS evidence
OPTIONAL MATCH (source:Source {series_id: $series_id})
WHERE source.visible_from_order IS NOT NULL
  AND source.visible_from_order <= $visible_until_order
RETURN entities, claims, evidence, count(source) AS sources
"""

ALL_VISIBLE_NODES_QUERY = """\
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id,
       [label IN labels(node) WHERE label IN $allowed_labels][0] AS type,
       node.label AS label,
       node.visible_from_order AS visible_from_order,
       node.origin AS origin
ORDER BY node.visible_from_order, node.id
LIMIT $limit
"""

ALL_VISIBLE_CLAIMS_QUERY = """\
MATCH (claim:Claim {series_id: $series_id})
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
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
LIMIT $limit
"""

USER_NOTES_QUERY = """\
MATCH (note:UserNote {series_id: $series_id, origin: 'user'})
MATCH (note)-[attachment:REFERS_TO]->(target)
WHERE note.user_id = $user_id
  AND note.target_id IN $entity_or_claim_ids
  AND note.visible_from_order IS NOT NULL
  AND note.visible_from_order <= $visible_until_order
  AND attachment.visible_from_order IS NOT NULL
  AND attachment.visible_from_order <= $visible_until_order
  AND target.visible_from_order IS NOT NULL
  AND target.visible_from_order <= $visible_until_order
RETURN note.id AS id,
       note.target_type AS target_type,
       note.target_id AS target_id,
       note.content AS content,
       note.visible_from_order AS visible_from_order
ORDER BY note.visible_from_order, note.id
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
            "id": claim["id"] + ":edge",
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


async def search_entities(
    database: Neo4jDatabase,
    *,
    query: str,
    allowed_entity_types: list[str],
    limit: int,
    series_id: str,
    visible_until_order: int,
) -> list[dict[str, Any]]:
    """Return visible entities whose label — or any alias — contains *query*.

    The type allowlist is intersected with the server-owned narrative labels —
    a bogus type from the model simply narrows the result to nothing (fail
    closed).  An empty/whitespace query returns an empty list rather than
    dumping the visible graph.  Order is deterministic (visible_from_order, id).

    D-15 indistinguishability (SEARCH-01): a hidden entity — by name, alias,
    or exact ID — behaves exactly like a nonexistent one.  There is
    deliberately NO timing alternation, NO distinct error code, and NO
    log/response difference for hidden vs. missing ids: a hidden id flows
    through the same empty-result path as an unknown id.  The query-level
    ``visible_from_order IS NOT NULL AND <= boundary`` predicate on the
    matched node gates both the label and the alias channel, so a hidden
    node's aliases can never surface it, and ``LIMIT``/``ORDER BY`` keep the
    result set deterministic and bounded (autocomplete-style lookups reuse
    this same boundary-filtered primitive).
    """
    if not query or not query.strip():
        return []
    allowed = STORY_NODE_LABELS & frozenset(allowed_entity_types)
    if not allowed:
        return []
    limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))
    return await database.execute_query(
        SEARCH_ENTITIES_QUERY,
        search_term=query.strip(),
        allowed_labels=sorted(allowed),
        limit=limit,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )


async def find_path(
    database: Neo4jDatabase,
    *,
    source_entity_id: str,
    target_entity_id: str,
    max_hops: int,
    series_id: str,
    visible_until_order: int,
) -> dict[str, Any]:
    """Return the shortest visible path between two entities, if one exists.

    Traversal walks only *visible* claims (both endpoints already pass the
    boundary in ``CLAIMS_FOR_FRONTIER_QUERY``), so a path that exists only
    through a hidden intermediate node is indistinguishable from no path at
    all — hidden path existence is never revealed (RAG-03).  ``max_hops`` is
    clamped to the server ceiling ``MAX_PATH_HOPS``.  Result shape:
    ``{"found", "path", "edges", "hops"}``.
    """
    hops = max(1, min(int(max_hops), MAX_PATH_HOPS))

    source = await get_entity(
        database,
        entity_id=source_entity_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    if source is None:
        return {"found": False, "path": [], "edges": [], "hops": 0}
    if source_entity_id == target_entity_id:
        return {"found": True, "path": [source_entity_id], "edges": [], "hops": 0}
    target = await get_entity(
        database,
        entity_id=target_entity_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    if target is None:
        return {"found": False, "path": [], "edges": [], "hops": 0}

    # BFS over the visible claim graph.  Every returned claim touches the
    # current frontier (which is a subset of already-discovered nodes), so a
    # claim can never connect two brand-new nodes and the parent chain always
    # terminates at the source.
    parent: dict[str, str | None] = {source_entity_id: None}
    edge_to: dict[str, str] = {}
    frontier: list[str] = [source_entity_id]

    for _ in range(hops):
        rows = await database.execute_query(
            CLAIMS_FOR_FRONTIER_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
            frontier=frontier,
        )
        if not rows:
            break
        next_frontier: list[str] = []
        for row in rows:
            subject_id, object_id = row["subject_id"], row["object_id"]
            if subject_id not in parent:
                parent[subject_id] = object_id
                edge_to[subject_id] = row["id"]
                next_frontier.append(subject_id)
            if object_id not in parent:
                parent[object_id] = subject_id
                edge_to[object_id] = row["id"]
                next_frontier.append(object_id)
        if target_entity_id in parent:
            break
        frontier = next_frontier

    if target_entity_id not in parent:
        return {"found": False, "path": [], "edges": [], "hops": 0}

    path: list[str] = [target_entity_id]
    edges: list[str] = []
    current = target_entity_id
    while current != source_entity_id:
        previous = parent[current]
        if previous is None:
            # Unreachable given the invariant above; fail closed anyway.
            return {"found": False, "path": [], "edges": [], "hops": 0}
        edges.append(edge_to[current])
        path.append(previous)
        current = previous
    path.reverse()
    edges.reverse()
    return {"found": True, "path": path, "edges": edges, "hops": len(edges)}


async def get_character_context(
    database: Neo4jDatabase,
    *,
    character_id: str,
    series_id: str,
    visible_until_order: int,
    limit: int = 10,
) -> dict[str, Any]:
    """Bounded interpretive-context pack for one visible Character.

    Composes the existing visibility-filtered primitives — the character
    itself, its visible neighborhood (nodes, claim edges, claims, evidence,
    sources), and the character's most recent visible Events ordered by
    recency — so a future-looking or interpretive question gets the visible
    material it needs in one allowlisted, bounded call (conversational-tone
    brief §4). Every resource is series-scoped and visibility-filtered; a
    hidden or missing character yields an all-empty result (fail closed),
    exactly like ``get_neighborhood``.

    Result shape: ``{entity, recent_events, nodes, edges, claims, evidence,
    sources}`` — the ``nodes/claims/evidence/sources/edges`` keys match
    ``get_neighborhood`` so the pipeline's accumulator merges them unchanged.
    """
    hood = await get_neighborhood(
        database,
        entity_id=character_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
        depth=1,
    )
    limit = max(1, min(int(limit), MAX_RESULT_LIMIT))
    events = [
        node
        for node in hood.get("nodes") or []
        if node.get("type") == "Event"
    ]
    events.sort(
        key=lambda event: (
            event.get("visible_from_order") or 0,
            event.get("id") or "",
        ),
        reverse=True,
    )
    return {
        **hood,
        "recent_events": events[:limit],
    }


async def get_timeline(
    database: Neo4jDatabase,
    *,
    series_id: str,
    visible_until_order: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the visible episode timeline up to the boundary, in order.

    An episode one order above the boundary is excluded entirely — never a
    redacted or partial row (RAG-03).
    """
    limit = max(1, min(int(limit), MAX_RESULT_LIMIT))
    return await database.execute_query(
        TIMELINE_QUERY,
        series_id=series_id,
        visible_until_order=visible_until_order,
        limit=limit,
    )


async def get_claims(
    database: Neo4jDatabase,
    *,
    entity_ids: list[str],
    series_id: str,
    visible_until_order: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return visible claims touching any of *entity_ids*.

    Hidden entity IDs and cross-series IDs yield the same empty list as
    genuinely nonexistent IDs (fail closed).
    """
    if not entity_ids:
        return []
    limit = max(1, min(int(limit), MAX_RESULT_LIMIT))
    return await database.execute_query(
        GET_CLAIMS_QUERY,
        entity_ids=sorted(set(entity_ids)),
        series_id=series_id,
        visible_until_order=visible_until_order,
        limit=limit,
    )


async def get_evidence(
    database: Neo4jDatabase,
    *,
    claim_ids: list[str],
    series_id: str,
    visible_until_order: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return visible evidence supporting any of *claim_ids*."""
    if not claim_ids:
        return []
    limit = max(1, min(int(limit), MAX_RESULT_LIMIT))
    return await database.execute_query(
        GET_EVIDENCE_QUERY,
        claim_ids=sorted(set(claim_ids)),
        series_id=series_id,
        visible_until_order=visible_until_order,
        limit=limit,
    )


async def get_sources(
    database: Neo4jDatabase,
    *,
    claim_ids: list[str],
    series_id: str,
    visible_until_order: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return visible sources referenced by any of *claim_ids*."""
    if not claim_ids:
        return []
    limit = max(1, min(int(limit), MAX_RESULT_LIMIT))
    return await database.execute_query(
        GET_SOURCES_QUERY,
        claim_ids=sorted(set(claim_ids)),
        series_id=series_id,
        visible_until_order=visible_until_order,
        limit=limit,
    )


async def get_current_visible_graph_summary(
    database: Neo4jDatabase,
    *,
    focus_entity_ids: list[str],
    series_id: str,
    visible_until_order: int,
) -> dict[str, Any]:
    """Summarize the visible graph, truncated to a strict server-owned size.

    The sample limit comes from ``settings.llm_max_context_items`` — never
    from model input.  Counts cover only visible resources (hidden counts are
    never exposed) and samples are bounded even when the visible graph is
    large.
    """
    limit = max(1, get_settings().llm_max_context_items)
    counts_rows = await database.execute_query(
        GRAPH_SUMMARY_COUNTS_QUERY,
        series_id=series_id,
        visible_until_order=visible_until_order,
        allowed_labels=sorted(STORY_NODE_LABELS),
    )
    counts = counts_rows[0] if counts_rows else {}
    episodes = await database.execute_query(
        TIMELINE_QUERY,
        series_id=series_id,
        visible_until_order=visible_until_order,
        limit=limit,
    )
    if focus_entity_ids:
        entities = await database.execute_query(
            NODES_BY_IDS_QUERY,
            node_ids=sorted(set(focus_entity_ids)),
            series_id=series_id,
            visible_until_order=visible_until_order,
            allowed_labels=sorted(STORY_NODE_LABELS),
        )
        claims = await database.execute_query(
            CLAIMS_FOR_FRONTIER_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
            frontier=sorted(set(focus_entity_ids)),
        )
    else:
        entities = await database.execute_query(
            ALL_VISIBLE_NODES_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
            allowed_labels=sorted(STORY_NODE_LABELS),
            limit=limit,
        )
        claims = await database.execute_query(
            ALL_VISIBLE_CLAIMS_QUERY,
            series_id=series_id,
            visible_until_order=visible_until_order,
            limit=limit,
        )
    claim_ids = [row["id"] for row in claims[:limit]]
    evidence = await database.execute_query(
        EVIDENCE_FOR_CLAIMS_QUERY,
        claim_ids=claim_ids,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    sources = await database.execute_query(
        SOURCES_FOR_CLAIMS_QUERY,
        claim_ids=claim_ids,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
    return {
        "series_id": series_id,
        "visible_until_order": visible_until_order,
        "counts": {
            key: counts.get(key, 0)
            for key in ("entities", "claims", "evidence", "sources")
        },
        "episodes": episodes[:limit],
        "entities": entities[:limit],
        "claims": claims[:limit],
        "evidence": evidence[:limit],
        "sources": sources[:limit],
    }


async def get_user_notes(
    database: Neo4jDatabase,
    *,
    entity_or_claim_ids: list[str],
    user_id: str,
    series_id: str,
    visible_until_order: int,
) -> list[dict[str, Any]]:
    """Return the requesting user's own notes on currently visible targets.

    Scoped by both ``user_id`` (only the requester's notes) and the current
    visibility of the referenced entity/claim; notes without a known owner are
    never returned to anyone (fail closed).
    """
    if not entity_or_claim_ids:
        return []
    return await database.execute_query(
        USER_NOTES_QUERY,
        entity_or_claim_ids=sorted(set(entity_or_claim_ids)),
        user_id=user_id,
        series_id=series_id,
        visible_until_order=visible_until_order,
    )
