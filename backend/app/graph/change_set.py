"""Parameterized Cypher for ChangeSet propose-stage persistence (RAG-11).

Schema shape: ``(:AppUser)-[:PROPOSED_CHANGE_SET]->(:ChangeSet)-[:IN_SERIES]->
(:Series)`` and ``(:ChangeSet)-[:FOR_SESSION]->(:ChatSession)``. The
authenticated user node is always ``(:AppUser)`` — never ``(:User)``
(06-PATTERNS.md). ``operations_json`` stores the validated operation list as
JSON text (Neo4j node properties cannot hold nested objects), mirroring
``graph/chat.py``'s ``citations_json``/``graph_focus_json`` convention.

``CHANGE_SET_CREATE_QUERY`` writes only the ``ChangeSet`` draft node itself
plus its ``AppUser``/``ChatSession``/``Series`` linking relationships — it
never touches a target node/relationship/claim (that is Stage 2, 06-06).
Because the chat-session MATCH is user-scoped, a foreign or missing
``chat_session_id`` yields zero rows — indistinguishable, by design, exactly
like ``graph/chat.py``'s session queries.

``TARGET_VISIBILITY_QUERY`` is intentionally label-agnostic (no ``:Label`` on
``target``) so ONE query serves every operation's target kind — narrative
nodes (Character/Location/...), Claim nodes (relationships and claims are
both stored as ``Claim`` in this schema), and UserNote nodes — exactly the
same ``visible_from_order <= $visible_until_order`` boundary shape composed
elsewhere (``retrieval/tools.py``'s ``GET_ENTITY_QUERY``), never
reimplemented. A hidden target, a cross-series target, and a genuinely
nonexistent target all return zero rows — identical, by design (RAG-03).
"""

from __future__ import annotations

CHANGE_SET_CREATE_QUERY = """\
MERGE (u:AppUser {id: $user_id})
MERGE (s:Series {id: $series_id})
MATCH (u)-[:HAS_CHAT_SESSION]->(session:ChatSession {id: $chat_session_id, series_id: $series_id})
CREATE (u)-[:PROPOSED_CHANGE_SET]->(cs:ChangeSet {
    id: $id,
    user_id: $user_id,
    series_id: $series_id,
    chat_session_id: $chat_session_id,
    status: 'awaiting_confirmation',
    visible_until_order_snapshot: $visible_until_order_snapshot,
    summary: $summary,
    operations_json: $operations_json,
    created_at: $created_at,
    confirmed_at: null,
    applied_at: null,
    revision_id: null,
    idempotency_key: null
})-[:IN_SERIES]->(s)
CREATE (cs)-[:FOR_SESSION]->(session)
RETURN cs.id AS id,
       cs.user_id AS user_id,
       cs.series_id AS series_id,
       cs.chat_session_id AS chat_session_id,
       cs.status AS status,
       cs.visible_until_order_snapshot AS visible_until_order_snapshot,
       cs.summary AS summary,
       cs.operations_json AS operations_json,
       cs.created_at AS created_at,
       cs.confirmed_at AS confirmed_at,
       cs.applied_at AS applied_at,
       cs.revision_id AS revision_id,
       cs.idempotency_key AS idempotency_key
"""

TARGET_VISIBILITY_QUERY = """\
MATCH (target {id: $target_id, series_id: $series_id})
WHERE target.visible_from_order IS NOT NULL
  AND target.visible_from_order <= $visible_until_order
RETURN target.id AS id,
       target.origin AS origin,
       labels(target) AS node_labels
"""
