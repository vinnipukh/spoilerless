"""Parameterized Cypher for fail-closed spoiler and temporal filtering."""

SERIES_LIST_QUERY = """\
MATCH (series:Series)
RETURN series.id AS id,
       series.title AS title,
       series.slug AS slug
ORDER BY series.title
"""

SERIES_BY_ID_QUERY = """\
MATCH (series:Series {id: $series_id})
RETURN series.id AS id,
       series.title AS title,
       series.slug AS slug
"""

SERIES_EPISODES_QUERY = """\
MATCH (episode:Episode)-[:PART_OF]->(series:Series {id: $series_id})
RETURN episode.id AS id,
       episode.series_id AS series_id,
       episode.season_number AS season_number,
       episode.episode_number AS episode_number,
       episode.episode_order AS episode_order,
       episode.code AS code,
       episode.title AS title,
       episode.visible_from_order AS visible_from_order
ORDER BY episode.episode_order
"""

SERIES_QUERY = """\
MATCH (series:Series {id: $series_id})
RETURN series.id AS id, series.title AS title, series.slug AS slug
"""

BOUNDARY_QUERY = """
MATCH (:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
WHERE episode.episode_order = $visible_until_order
  AND episode.visible_from_order <= $visible_until_order
RETURN episode.id AS episode_id
"""

NODES_QUERY = """
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $node_labels)
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id,
       [label IN labels(node) WHERE label IN $node_labels][0] AS type,
       node.label AS label,
       node.visible_from_order AS visible_from_order,
       node.origin AS origin,
       node.episode_id AS episode_id,
       node.image_url AS image_url,
       node.image_source_url AS image_source_url
ORDER BY node.visible_from_order, id
"""

STRUCTURAL_EDGES_QUERY = """
MATCH (source)-[edge:PART_OF|PRECEDES|OCCURRED_IN]->(target)
WHERE source.series_id = $series_id
  AND target.series_id = $series_id
  AND edge.series_id = $series_id
  AND source.visible_from_order <= $visible_until_order
  AND target.visible_from_order <= $visible_until_order
  AND edge.visible_from_order <= $visible_until_order
RETURN edge.id AS id,
       source.id AS source,
       target.id AS target,
       type(edge) AS type,
       edge.visible_from_order AS visible_from_order,
       edge.origin AS origin,
       null AS claim_id
ORDER BY edge.visible_from_order, id
"""

VISIBLE_CLAIMS_QUERY = """
MATCH (claim:Claim {series_id: $series_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
MATCH (claim)-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
MATCH (claim)-[ref:REFERS_TO]->(source:Source {id: evidence.source_id})
WHERE claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order <= $visible_until_order
  AND supported.visible_from_order <= $visible_until_order
  AND ref.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order <= $visible_until_order
  AND source.visible_from_order <= $visible_until_order
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
RETURN claim.id AS id,
       claim.label AS label,
       claim.subject_id AS subject_id,
       claim.predicate AS predicate,
       claim.object_id AS object_id,
       claim.claim_type AS claim_type,
       claim.status AS status,
       claim.confidence_level AS confidence_level,
       claim.relationship_effect AS relationship_effect,
       claim.visible_from_order AS visible_from_order,
       claim.valid_from_order AS valid_from_order,
       claim.valid_until_order AS valid_until_order,
       source.id AS source_id,
       collect(DISTINCT evidence.id) AS evidence_ids,
       claim.origin AS origin
ORDER BY claim.visible_from_order, id
"""

VISIBLE_USER_RELATIONSHIPS_QUERY = """
MATCH (claim:Claim {series_id: $series_id, origin: 'user', claim_type: 'user_authored'})
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE claim.id STARTS WITH 'user-rel:'
  AND claim.predicate IN $user_relationship_types
  AND claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order >= 1
  AND claim.visible_from_order <= $visible_until_order
  AND subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order >= 1
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order >= 1
  AND object.visible_from_order <= $visible_until_order
RETURN claim.id AS id,
       claim.subject_id AS source,
       claim.object_id AS target,
       claim.predicate AS type,
       claim.visible_from_order AS visible_from_order,
       claim.origin AS origin,
       null AS claim_id
ORDER BY claim.visible_from_order, id
"""

SOURCES_QUERY = """
MATCH (claim:Claim {series_id: $series_id})-[ref:REFERS_TO]->(source:Source)
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
WHERE claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order <= $visible_until_order
  AND ref.visible_from_order <= $visible_until_order
  AND source.visible_from_order <= $visible_until_order
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
RETURN DISTINCT source.id AS id,
       source.label AS label,
       source.episode_id AS episode_id,
       source.source_type AS source_type,
       source.locator AS locator,
       source.retrieved_at AS retrieved_at,
       source.visible_from_order AS visible_from_order,
       source.origin AS origin
ORDER BY source.visible_from_order, id
"""

EVIDENCE_QUERY = """
MATCH (claim:Claim {series_id: $series_id})-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
MATCH (claim)-[ref:REFERS_TO]->(source:Source {id: evidence.source_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
WHERE claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND claim.claim_type <> 'user_authored'
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order <= $visible_until_order
  AND supported.visible_from_order <= $visible_until_order
  AND ref.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order <= $visible_until_order
  AND source.visible_from_order <= $visible_until_order
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
RETURN DISTINCT evidence.id AS id,
       evidence.label AS label,
       evidence.episode_id AS episode_id,
       evidence.source_id AS source_id,
       evidence.text AS text,
       evidence.locator AS locator,
       evidence.content_hash AS content_hash,
       evidence.visible_from_order AS visible_from_order,
       evidence.origin AS origin
ORDER BY evidence.visible_from_order, id
"""
