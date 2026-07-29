"""Parameterized Cypher for fail-closed spoiler and temporal filtering."""

SERIES_QUERY = """
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
       node.episode_id AS episode_id
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
WHERE claim.visible_from_order <= $visible_until_order
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order <= $visible_until_order
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
       claim.source_id AS source_id,
       claim.evidence_ids AS evidence_ids,
       claim.origin AS origin
ORDER BY claim.visible_from_order, id
"""

SOURCES_QUERY = """
MATCH (claim:Claim {series_id: $series_id})-[ref:REFERS_TO]->(source:Source)
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
WHERE claim.visible_from_order <= $visible_until_order
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
