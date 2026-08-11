"""Parameterized Cypher for ChangeSet propose and confirm/apply (RAG-11, RAG-12).

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

Stage 2 (Confirm and Apply, RAG-12) queries below are used **only** inside a
single ``execute_write`` callback (``repository/change_set.py``'s
``_apply_change_set``) — every create query hardcodes ``origin: 'user'`` and
binds ``visible_from_order`` from a server-computed parameter (the freshly
re-read current progress), never from the operation payload itself
(06-PATTERNS.md's "Origin-tagging pattern"). Every update/delete query
re-checks ``origin = 'user'`` in its own ``WHERE`` clause as a second,
independent enforcement layer beyond the repository's pre-flight
``TARGET_VISIBILITY_QUERY`` re-validation.
"""

from __future__ import annotations

from typing import Mapping

from spoilerless.app.domain.user_content import CustomNodeType, NoteTargetType

CHANGE_SET_CREATE_QUERY = """\
MERGE (u:AppUser {id: $user_id})
MERGE (s:Series {id: $series_id})
WITH u, s
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
    revert_revision_id: null,
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
       cs.revert_revision_id AS revert_revision_id,
       cs.idempotency_key AS idempotency_key
"""

TARGET_VISIBILITY_QUERY = """\
MATCH (target {id: $target_id, series_id: $series_id})
WHERE target.visible_from_order IS NOT NULL
  AND target.visible_from_order <= $visible_until_order
RETURN target.id AS id,
       target.origin AS origin,
       target.visible_from_order AS visible_from_order,
       labels(target) AS node_labels
"""

# ---------------------------------------------------------------------------
# Stage 2 — Confirm and Apply (RAG-12)
# ---------------------------------------------------------------------------

_CHANGE_SET_FIELDS = """\
       cs.id AS id,
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
       cs.revert_revision_id AS revert_revision_id,
       cs.idempotency_key AS idempotency_key
"""

# User-scoped read of a ChangeSet by id — a foreign/missing/cross-series
# change_set_id yields zero rows, indistinguishable, exactly like the
# propose-stage chat-session lookup.
CHANGE_SET_READ_FOR_APPLY_QUERY = f"""\
MATCH (u:AppUser {{id: $user_id}})-[:PROPOSED_CHANGE_SET]->
      (cs:ChangeSet {{id: $change_set_id, series_id: $series_id}})
RETURN {_CHANGE_SET_FIELDS}
"""

# The sole source of "current progress" at confirm time — read fresh inside
# the same transaction, never trusted from the ChangeSet's stored snapshot
# (RAG-14 "never trusts the stored snapshot alone").
CURRENT_PROGRESS_QUERY = """\
MATCH (:AppUser {id: $user_id})-[:HAS_PROGRESS]->
      (p:UserSeriesProgress {series_id: $series_id})
RETURN p.view_as_of_order AS view_as_of_order,
       p.watched_through_order AS watched_through_order
"""

MARK_CHANGE_SET_FAILED_QUERY = f"""\
MATCH (cs:ChangeSet {{id: $id, series_id: $series_id}})
SET cs.status = 'failed', cs.confirmed_at = $now
RETURN {_CHANGE_SET_FIELDS}
"""

# Reject only succeeds from 'awaiting_confirmation' — a rejected/applied/
# failed ChangeSet (or one owned by another user) yields zero rows.
MARK_CHANGE_SET_REJECTED_QUERY = f"""\
MATCH (u:AppUser {{id: $user_id}})-[:PROPOSED_CHANGE_SET]->
      (cs:ChangeSet {{id: $id, series_id: $series_id}})
WHERE cs.status = 'awaiting_confirmation'
SET cs.status = 'rejected', cs.confirmed_at = $now
RETURN {_CHANGE_SET_FIELDS}
"""

MARK_CHANGE_SET_APPLIED_QUERY = f"""\
MATCH (cs:ChangeSet {{id: $id, series_id: $series_id}})
SET cs.status = 'applied',
    cs.confirmed_at = $now,
    cs.applied_at = $now,
    cs.revision_id = $revision_id,
    cs.idempotency_key = $idempotency_key
RETURN {_CHANGE_SET_FIELDS}
"""

# ---------------------------------------------------------------------------
# Stage 3 — Revert (RAG-15)
# ---------------------------------------------------------------------------

# Read the ChangeSet's own apply-time Revision by id (never the user-facing,
# visibility-filtered ``REVISION_GET_QUERY`` in ``api/revisions.py`` — this is
# a server-internal read inside the revert transaction, not a user-facing
# list/get). ``after`` carries the JSON-encoded ``{operation_types,
# affected_ids}`` payload ``_apply_change_set`` logged at apply time.
CHANGE_SET_REVISION_GET_QUERY = """\
MATCH (revision:Revision {id: $revision_id, series_id: $series_id})
RETURN revision.id AS id, revision.action AS action,
  revision.before AS before, revision.after AS after,
  revision.created_at AS created_at
"""

# Undoes exactly one create-shaped operation's target: only a resource this
# ChangeSet itself created (`origin = 'user'`) and that has not been touched
# since (`updated_at` still equal to this ChangeSet's own `applied_at`, both
# read fresh from the *same* Neo4j `ChangeSet` node inside this one query —
# never a Python-side value, which would compare a driver-native datetime
# property against a re-serialized string and never match — every create-
# stage query sets `created_at == updated_at == $now` from the same apply
# transaction, so `applied_at` on the ChangeSet is exactly that same instant)
# is deleted. Zero rows back means the resource was modified or removed by a
# later, unrelated change since this ChangeSet was applied — the caller must
# treat that as a conflict, never as "nothing to do". Label-agnostic and
# works for every create-shaped operation type (node, relationship/claim,
# evidence, note) because ``DETACH DELETE`` also removes the
# ``REFERS_TO``/``SUPPORTED_BY`` relationships those creates add.
CHANGE_SET_REVERT_DELETE_QUERY = """\
MATCH (cs:ChangeSet {id: $change_set_id, series_id: $series_id})
MATCH (resource {id: $resource_id, series_id: $series_id})
WHERE resource.origin = 'user' AND resource.updated_at = cs.applied_at
WITH resource, resource.id AS deleted_id
DETACH DELETE resource
RETURN deleted_id AS id
"""

# Revert only succeeds from 'applied' — an unapplied/rejected/failed/already-
# reverted ChangeSet (or one owned by another user) yields zero rows.
# PROB-27/#51: preserve BOTH links — the apply-time `revision_id` stays intact
# (the audit trail of what was applied), and the newly logged revert Revision
# is recorded separately in `revert_revision_id`. The old query overwrote
# `revision_id`, destroying the apply link.
MARK_CHANGE_SET_REVERTED_QUERY = f"""\
MATCH (u:AppUser {{id: $user_id}})-[:PROPOSED_CHANGE_SET]->
      (cs:ChangeSet {{id: $id, series_id: $series_id}})
WHERE cs.status = 'applied'
SET cs.status = 'reverted', cs.revert_revision_id = $revert_revision_id
RETURN {_CHANGE_SET_FIELDS}
"""

# Every CREATE below hardcodes origin: 'user' and binds visible_from_order
# from $visible_from_order — a server-computed parameter (current progress,
# read fresh inside the transaction), never sourced from the operation
# payload (06-PATTERNS.md's "Origin-tagging pattern", RAG-12).
CHANGE_SET_CREATE_NODE_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""\
        MATCH (episode:Episode {{id: $episode_id, series_id: $series_id}})
        CREATE (node:{node_type.value} {{id: $id, series_id: $series_id, label: $label,
          episode_id: $episode_id, description: $description,
          visible_from_order: $visible_from_order, origin: 'user',
          created_by: $user_id, created_at: $now, updated_at: $now}})
        RETURN node.id AS id, node.series_id AS series_id, '{node_type.value}' AS type,
          node.label AS label, node.episode_id AS episode_id,
          node.visible_from_order AS visible_from_order, node.origin AS origin,
          node.created_at AS created_at, node.updated_at AS updated_at
    """
    for node_type in CustomNodeType
}

CHANGE_SET_UPDATE_NODE_QUERY = """\
MATCH (node {id: $node_id, series_id: $series_id})
WHERE node.origin = 'user'
SET node.label = COALESCE($label, node.label),
    node.description = COALESCE($description, node.description),
    node.updated_at = $now
RETURN node.id AS id, node.series_id AS series_id, labels(node)[0] AS type,
  node.label AS label, node.episode_id AS episode_id,
  node.visible_from_order AS visible_from_order, node.origin AS origin,
  node.created_at AS created_at, node.updated_at AS updated_at
"""

CHANGE_SET_DELETE_NODE_QUERY = """\
MATCH (node {id: $node_id, series_id: $series_id})
WHERE node.origin = 'user'
WITH node, node.id AS deleted_id, labels(node)[0] AS type,
     node.visible_from_order AS visible_from_order
DETACH DELETE node
RETURN deleted_id AS id, type, visible_from_order
"""

CHANGE_SET_CREATE_RELATIONSHIP_QUERY = """\
MATCH (source {id: $source_id, series_id: $series_id})
MATCH (target {id: $target_id, series_id: $series_id})
MATCH (episode:Episode {id: $episode_id, series_id: $series_id})
CREATE (claim:Claim {id: $id, series_id: $series_id, subject_id: $source_id,
  object_id: $target_id, predicate: $relationship_type, claim_type: 'user_authored',
  episode_id: $episode_id, description: $description,
  visible_from_order: $visible_from_order, origin: 'user',
  created_by: $user_id, created_at: $now, updated_at: $now})
RETURN claim.id AS id, claim.series_id AS series_id, claim.subject_id AS source,
  claim.object_id AS target, claim.predicate AS type, claim.episode_id AS episode_id,
  claim.visible_from_order AS visible_from_order, claim.origin AS origin,
  claim.created_at AS created_at, claim.updated_at AS updated_at
"""

CHANGE_SET_UPDATE_RELATIONSHIP_QUERY = """\
MATCH (claim:Claim {id: $relationship_id, series_id: $series_id})
WHERE claim.origin = 'user'
SET claim.predicate = COALESCE($relationship_type, claim.predicate),
    claim.description = COALESCE($description, claim.description),
    claim.updated_at = $now
RETURN claim.id AS id, claim.series_id AS series_id, claim.subject_id AS source,
  claim.object_id AS target, claim.predicate AS type, claim.episode_id AS episode_id,
  claim.visible_from_order AS visible_from_order, claim.origin AS origin,
  claim.created_at AS created_at, claim.updated_at AS updated_at
"""

CHANGE_SET_DELETE_RELATIONSHIP_QUERY = """\
MATCH (claim:Claim {id: $relationship_id, series_id: $series_id})
WHERE claim.origin = 'user'
WITH claim, claim.id AS deleted_id, claim.visible_from_order AS visible_from_order
DELETE claim
RETURN deleted_id AS id, visible_from_order
"""

CHANGE_SET_CREATE_CLAIM_QUERY = """\
MATCH (subject {id: $subject_id, series_id: $series_id})
MATCH (object {id: $object_id, series_id: $series_id})
MATCH (episode:Episode {id: $episode_id, series_id: $series_id})
CREATE (claim:Claim {id: $id, series_id: $series_id, subject_id: $subject_id,
  object_id: $object_id, predicate: $predicate, claim_type: $claim_type,
  confidence_level: $confidence_level, episode_id: $episode_id,
  description: $description, visible_from_order: $visible_from_order,
  origin: 'user', created_by: $user_id, created_at: $now, updated_at: $now})
RETURN claim.id AS id, claim.series_id AS series_id, claim.subject_id AS subject_id,
  claim.object_id AS object_id, claim.predicate AS predicate,
  claim.claim_type AS claim_type, claim.confidence_level AS confidence_level,
  claim.episode_id AS episode_id, claim.visible_from_order AS visible_from_order,
  claim.origin AS origin, claim.created_at AS created_at, claim.updated_at AS updated_at
"""

CHANGE_SET_UPDATE_CLAIM_QUERY = """\
MATCH (claim:Claim {id: $claim_id, series_id: $series_id})
WHERE claim.origin = 'user'
SET claim.predicate = COALESCE($predicate, claim.predicate),
    claim.confidence_level = COALESCE($confidence_level, claim.confidence_level),
    claim.description = COALESCE($description, claim.description),
    claim.updated_at = $now
RETURN claim.id AS id, claim.series_id AS series_id, claim.subject_id AS subject_id,
  claim.object_id AS object_id, claim.predicate AS predicate,
  claim.claim_type AS claim_type, claim.confidence_level AS confidence_level,
  claim.episode_id AS episode_id, claim.visible_from_order AS visible_from_order,
  claim.origin AS origin, claim.created_at AS created_at, claim.updated_at AS updated_at
"""

CHANGE_SET_DELETE_CLAIM_QUERY = """\
MATCH (claim:Claim {id: $claim_id, series_id: $series_id})
WHERE claim.origin = 'user'
WITH claim, claim.id AS deleted_id, claim.visible_from_order AS visible_from_order
DETACH DELETE claim
RETURN deleted_id AS id, visible_from_order
"""

CHANGE_SET_ATTACH_EVIDENCE_QUERY = """\
MATCH (claim:Claim {id: $claim_id, series_id: $series_id})
MATCH (source:Source {id: $source_id, series_id: $series_id})
CREATE (evidence:EvidenceFragment {id: $id, series_id: $series_id, label: $locator,
  episode_id: $episode_id, source_id: $source_id, text: $text, locator: $locator,
  content_hash: $content_hash, visible_from_order: $visible_from_order,
  origin: 'user', created_by: $user_id, created_at: $now, updated_at: $now})
CREATE (evidence)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
  visible_from_order: $visible_from_order, origin: 'user'}]->(source)
CREATE (claim)-[:SUPPORTED_BY {id: $id + ':supported_by', series_id: $series_id,
  visible_from_order: $visible_from_order, origin: 'user'}]->(evidence)
RETURN evidence.id AS id, evidence.series_id AS series_id,
  evidence.episode_id AS episode_id, evidence.source_id AS source_id,
  evidence.text AS text, evidence.locator AS locator,
  evidence.content_hash AS content_hash, evidence.visible_from_order AS visible_from_order,
  evidence.origin AS origin, evidence.created_at AS created_at,
  evidence.updated_at AS updated_at
"""

CHANGE_SET_CREATE_NOTE_QUERIES: Mapping[NoteTargetType, str] = {
    target_type: f"""\
        MATCH (target:{target_type.value} {{id: $target_id, series_id: $series_id}})
        CREATE (note:UserNote {{id: $id, series_id: $series_id,
          target_type: $target_type, target_id: $target_id, content: $content,
          visible_from_order: $visible_from_order, origin: 'user',
          created_by: $user_id, created_at: $now, updated_at: $now}})
        CREATE (note)-[:REFERS_TO {{id: $id + ':refers_to', series_id: $series_id,
          visible_from_order: $visible_from_order, origin: 'user'}}]->(target)
        RETURN note.id AS id, note.series_id AS series_id, note.target_type AS target_type,
          note.target_id AS target_id, note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order, note.created_at AS created_at,
          note.updated_at AS updated_at
    """
    for target_type in NoteTargetType
}
