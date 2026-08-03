"""Parameterized Cypher for the persisted watch-progress record (RAG-01).

Follows the exact pattern in 06-PATTERNS.md: the authenticated user node is
always ``(:AppUser)`` — never ``(:User)`` (that label does not exist in this
schema; the label-mismatch correction in 06-RESEARCH.md Q6).  All values are
``$params``; no request data is ever interpolated into the query text.

The D-05 split (07-02) persists ``watched_through_order`` and
``view_as_of_order``; ``visible_until_order`` is kept as a backward-compatible
echo of the confirmed watched boundary (D-21).  The migration statement is a
WHERE-guarded, idempotent backfill (D-07): it only touches records missing the
new split properties and never deletes or resets anything.
"""

from __future__ import annotations

PROGRESS_UPSERT_QUERY = """\
MERGE (u:AppUser {id: $user_id})
MERGE (s:Series {id: $series_id})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $user_id, series_id: $series_id})
ON CREATE SET p.id = $id, p.created_at = $now
SET p.watched_through_order = $watched_through_order,
    p.view_as_of_order = $view_as_of_order,
    p.visible_until_order = $watched_through_order,
    p.updated_at = $now
MERGE (p)-[:FOR_SERIES]->(s)
RETURN p.id AS id,
       p.user_id AS user_id,
       p.series_id AS series_id,
       p.visible_until_order AS visible_until_order,
       p.watched_through_order AS watched_through_order,
       p.view_as_of_order AS view_as_of_order,
       p.updated_at AS updated_at
"""

PROGRESS_GET_QUERY = """\
MATCH (u:AppUser {id: $user_id})-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $user_id, series_id: $series_id})
RETURN p.id AS id,
       p.user_id AS user_id,
       p.series_id AS series_id,
       p.visible_until_order AS visible_until_order,
       p.watched_through_order AS watched_through_order,
       p.view_as_of_order AS view_as_of_order,
       p.updated_at AS updated_at
"""

PROGRESS_MIGRATE_QUERY = """\
MATCH (p:UserSeriesProgress)
WHERE p.watched_through_order IS NULL
  AND p.visible_until_order IS NOT NULL
SET p.watched_through_order = p.visible_until_order,
    p.view_as_of_order = p.visible_until_order
"""
