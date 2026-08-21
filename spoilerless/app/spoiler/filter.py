"""Parameterized Cypher for fail-closed spoiler and temporal filtering."""


def visible_claim_where(claim_var: str = "claim") -> str:
    """Fail-closed visibility + temporal predicate for story claims (D-20).

    The single spoiler-drift hotspot (PROB-09/#62): every claim-selecting
    query must gate on non-null boundary, the canonical/candidate origin
    allowlist, a non-user claim type, and the validity window. One
    definition, seven call sites — a spoiler-bug fix applies once, not
    seven times. The fragment is an f-string over a literal variable name;
    no runtime value is ever interpolated (D-20 plain-constant rule).
    """
    return f"""{claim_var}.visible_from_order IS NOT NULL
  AND {claim_var}.visible_from_order <= $visible_until_order
  AND {claim_var}.origin IN ['canonical', 'candidate']
  AND {claim_var}.claim_type <> 'user_authored'
  AND ({claim_var}.valid_from_order IS NULL OR {claim_var}.valid_from_order <= $visible_until_order)
  AND ({claim_var}.valid_until_order IS NULL OR {claim_var}.valid_until_order >= $visible_until_order)"""


def claim_projection(claim_var: str = "claim") -> str:
    """The 12-column compact claim row shared by the retrieval tools.

    Semantically identical to VISIBLE_CLAIMS_QUERY's richer projection
    (which additionally carries relationship_effect, the validity window,
    and joined evidence/source ids for the graph response — kept inline).
    """
    return f"""{claim_var}.id AS id,
       {claim_var}.label AS label,
       {claim_var}.subject_id AS subject_id,
       {claim_var}.object_id AS object_id,
       {claim_var}.predicate AS predicate,
       {claim_var}.claim_type AS claim_type,
       {claim_var}.status AS status,
       {claim_var}.confidence_level AS confidence_level,
       {claim_var}.episode_id AS episode_id,
       {claim_var}.source_id AS source_id,
       {claim_var}.visible_from_order AS visible_from_order,
       {claim_var}.origin AS origin"""


SERIES_LIST_QUERY = """\
MATCH (series:Series)
WHERE EXISTS { MATCH (:Episode)-[:PART_OF]->(series) }
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
       episode.visible_from_order AS visible_from_order,
       episode.title_is_spoiler AS title_is_spoiler,
       episode.title_visible_from_order AS title_visible_from_order,
       episode.synopsis_visible_from_order AS synopsis_visible_from_order,
       episode.image_visible_from_order AS image_visible_from_order
ORDER BY episode.episode_order
"""

SERIES_QUERY = """\
MATCH (series:Series {id: $series_id})
RETURN series.id AS id, series.title AS title, series.slug AS slug
"""

BOUNDARY_QUERY = """
MATCH (:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
WHERE episode.episode_order = $visible_until_order
  AND episode.visible_from_order IS NOT NULL
  AND episode.visible_from_order >= 1
  AND episode.visible_from_order <= $visible_until_order
RETURN episode.id AS episode_id
"""

NODES_QUERY = """
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $node_labels)
  AND node.visible_from_order IS NOT NULL
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
  AND source.visible_from_order IS NOT NULL
  AND source.visible_from_order <= $visible_until_order
  AND target.visible_from_order IS NOT NULL
  AND target.visible_from_order <= $visible_until_order
  AND edge.visible_from_order IS NOT NULL
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

VISIBLE_CLAIMS_QUERY = (
    """\
MATCH (claim:Claim {series_id: $series_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
MATCH (claim)-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
MATCH (claim)-[ref:REFERS_TO]->(source:Source {id: evidence.source_id})
WHERE """
    + visible_claim_where()
    + """
  AND subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order <= $visible_until_order
  AND supported.visible_from_order IS NOT NULL
  AND supported.visible_from_order <= $visible_until_order
  AND ref.visible_from_order IS NOT NULL
  AND ref.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order IS NOT NULL
  AND evidence.visible_from_order <= $visible_until_order
  AND source.visible_from_order IS NOT NULL
  AND source.visible_from_order <= $visible_until_order
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
)

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

SOURCES_QUERY = (
    """\
MATCH (claim:Claim {series_id: $series_id})-[ref:REFERS_TO]->(source:Source {series_id: $series_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
WHERE """
    + visible_claim_where()
    + """
  AND subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order <= $visible_until_order
  AND ref.visible_from_order IS NOT NULL
  AND ref.visible_from_order <= $visible_until_order
  AND source.visible_from_order IS NOT NULL
  AND source.visible_from_order <= $visible_until_order
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
)

EVIDENCE_QUERY = (
    """\
MATCH (claim:Claim {series_id: $series_id})-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment {series_id: $series_id})
MATCH (claim)-[ref:REFERS_TO]->(source:Source {id: evidence.source_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
WHERE """
    + visible_claim_where()
    + """
  AND subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order <= $visible_until_order
  AND supported.visible_from_order IS NOT NULL
  AND supported.visible_from_order <= $visible_until_order
  AND ref.visible_from_order IS NOT NULL
  AND ref.visible_from_order <= $visible_until_order
  AND evidence.visible_from_order IS NOT NULL
  AND evidence.visible_from_order <= $visible_until_order
  AND source.visible_from_order IS NOT NULL
  AND source.visible_from_order <= $visible_until_order
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
)
