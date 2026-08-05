"""Parameterized Neo4j persistence for API-owned user content.

This module intentionally contains no FastAPI dependencies.  Public values are
parameters; only closed, server-owned query maps select Cypher text.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping
from uuid import uuid4

from spoilerless.app.domain.revision import RevisionAction
from spoilerless.app.domain.user_content import (
    CustomNodeCreate,
    CustomNodeType,
    CustomRelationshipCreate,
    CustomRelationshipType,
    NoteCreate,
    NoteTargetType,
    NoteUpdate,
    CustomNodeUpdate,
    CustomRelationshipUpdate,
)
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.revisions import RevisionRepository


class UserContentValidationError(ValueError):
    """A request failed repository-level safety validation."""


class UserContentConflict(RuntimeError):
    pass


class UserContentNotFound(LookupError):
    pass


class UserContentForbidden(RuntimeError):
    """The resource exists but is owned by a different user (PROB-02, #4).

    Mapped to the API layer's 403 ``forbidden`` envelope. Distinct from
    ``UserContentNotFound`` so a cross-owner mutation attempt is explicit
    and testable — a resource that exists but is not the acting user's is
    not the same as a resource that does not exist.
    """


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _native(value: Any) -> Any:
    if hasattr(value, "to_native"):
        return value.to_native()
    if isinstance(value, dict):
        return {key: _native(item) for key, item in value.items()}
    return value


def _parse_dt(value: str) -> datetime:
    """Parse an ISO 8601 datetime string into a Python datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _run_create(tx: Any, query: str, error_msg: str, **params: Any) -> dict[str, Any]:
    """Execute ``tx.run``, consume a single result, and raise if absent.

    Shared by all ``UserContentRepository`` write callbacks — eliminates
    the repeated ``run → single → raise → return`` pattern.
    """
    record = await (await tx.run(query, **params)).single()
    if record is None:
        raise UserContentNotFound(error_msg)
    return _native(record.data())


def _raise_on_ownership_conflict(
    ownership: Any, actor_user_id: str, is_admin: bool, not_found_msg: str
) -> None:
    """Classify a failed owner-scoped mutation (PROB-02, #4).

    ``ownership`` is the single Neo4j record from ``OWNERSHIP_QUERY`` (or
    None). A record whose stored ``origin`` is not ``'user'`` is the
    pre-existing canonical/candidate-tamper conflict (409); a record whose
    stored ``user_id`` differs from the acting user's id is a cross-owner
    mutation attempt (403, admin bypass); anything else is a genuine
    not-found (404).
    """
    if ownership is None:
        raise UserContentNotFound(not_found_msg)
    origin = ownership.data().get("origin")
    if origin != "user":
        raise UserContentConflict("resource ownership conflict")
    if ownership.data().get("user_id") != actor_user_id and not is_admin:
        raise UserContentForbidden("resource owned by another user")
    raise UserContentNotFound(not_found_msg)


def _namespace(value: str, prefix: str) -> None:
    if (
        not isinstance(value, str)
        or not re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9._-]+", value)
    ):
        raise UserContentValidationError(f"Expected {prefix} namespace")


def _resource_id(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise UserContentValidationError("Invalid resource identifier")


def _series(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise UserContentValidationError("Invalid series identifier")


@dataclass(frozen=True)
class NoteCreateCommand:
    id: str
    series_id: str
    user_id: str
    target_type: NoteTargetType
    target_id: str
    content: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NoteUpdateCommand:
    id: str
    series_id: str
    user_id: str
    content: str
    updated_at: datetime
    is_admin: bool = False


@dataclass(frozen=True)
class CustomNodeCreateCommand:
    id: str
    series_id: str
    user_id: str
    node_type: CustomNodeType
    label: str
    episode_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CustomRelationshipCreateCommand:
    id: str
    series_id: str
    user_id: str
    source_id: str
    target_id: str
    predicate: CustomRelationshipType
    episode_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CustomUpdateCommand:
    id: str
    series_id: str
    user_id: str
    value: str
    updated_at: datetime
    is_admin: bool = False


NOTE_CREATE_QUERIES: Mapping[NoteTargetType, str] = {
    NoteTargetType.CHARACTER: """
        MATCH (series:Series {id: $series_id})
        MATCH (target:Character {id: $target_id, series_id: $series_id})
        WHERE target.origin IN ['canonical', 'candidate', 'user']
          AND target.visible_from_order IS NOT NULL AND target.visible_from_order >= 1
        CREATE (note:UserNote {id: $id, series_id: $series_id, user_id: $user_id,
          target_type: $target_type, target_id: $target_id, content: $content,
          visible_from_order: target.visible_from_order, origin: 'user',
          created_at: $created_at, updated_at: $updated_at})
        CREATE (note)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
          visible_from_order: target.visible_from_order, origin: 'user'}]->(target)
        RETURN note.id AS id, note.series_id AS series_id, note.user_id AS user_id,
          note.target_type AS target_type, note.target_id AS target_id,
          note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order, note.created_at AS created_at,
          note.updated_at AS updated_at
    """,
    NoteTargetType.CLAIM: """
        MATCH (series:Series {id: $series_id})
        MATCH (target:Claim {id: $target_id, series_id: $series_id})
        WHERE target.origin IN ['canonical', 'candidate', 'user']
          AND target.visible_from_order IS NOT NULL AND target.visible_from_order >= 1
        CREATE (note:UserNote {id: $id, series_id: $series_id, user_id: $user_id,
          target_type: $target_type, target_id: $target_id, content: $content,
          visible_from_order: target.visible_from_order, origin: 'user',
          created_at: $created_at, updated_at: $updated_at})
        CREATE (note)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
          visible_from_order: target.visible_from_order, origin: 'user'}]->(target)
        RETURN note.id AS id, note.series_id AS series_id, note.user_id AS user_id,
          note.target_type AS target_type, note.target_id AS target_id,
          note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order, note.created_at AS created_at,
          note.updated_at AS updated_at
    """,
}

CUSTOM_NODE_CREATE_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""
        MATCH (episode:Episode {{id: $episode_id, series_id: $series_id}})
        WHERE episode.episode_order IS NOT NULL AND episode.episode_order >= 1
        CREATE (node:{node_type.value} {{id: $id, series_id: $series_id, user_id: $user_id,
          label: $label, episode_id: $episode_id, visible_from_order: episode.episode_order,
          origin: 'user', created_at: $created_at, updated_at: $updated_at}})
        RETURN node.id AS id, node.series_id AS series_id, node.user_id AS user_id,
          '{node_type.value}' AS type, node.label AS label,
          node.episode_id AS episode_id, node.visible_from_order AS visible_from_order,
          node.origin AS origin, node.created_at AS created_at, node.updated_at AS updated_at
    """ for node_type in CustomNodeType
}

CUSTOM_RELATIONSHIP_CREATE_QUERY = """
    MATCH (episode:Episode {id: $episode_id, series_id: $series_id})
    MATCH (source {id: $source_id, series_id: $series_id})
    MATCH (target {id: $target_id, series_id: $series_id})
    WHERE source.visible_from_order IS NOT NULL AND source.visible_from_order >= 1
      AND target.visible_from_order IS NOT NULL AND target.visible_from_order >= 1
      AND episode.episode_order IS NOT NULL AND episode.episode_order >= 1
    CREATE (claim:Claim {id: $id, series_id: $series_id, user_id: $user_id,
      subject_id: $source_id, object_id: $target_id, predicate: $predicate,
      claim_type: 'user_authored', episode_id: $episode_id, visible_from_order:
        CASE WHEN source.visible_from_order > target.visible_from_order
          AND source.visible_from_order > episode.episode_order THEN source.visible_from_order
          WHEN target.visible_from_order > episode.episode_order THEN target.visible_from_order
          ELSE episode.episode_order END,
      origin: 'user', created_at: $created_at, updated_at: $updated_at})
        RETURN claim.id AS id, claim.series_id AS series_id, claim.user_id AS user_id,
      claim.subject_id AS source, claim.object_id AS target, claim.predicate AS type,
      claim.episode_id AS episode_id, claim.visible_from_order AS visible_from_order,
      claim.origin AS origin, claim.created_at AS created_at, claim.updated_at AS updated_at
"""

CUSTOM_NODE_READ_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""
        MATCH (node:{node_type.value} {{id: $id, series_id: $series_id}})
        WHERE node.origin = 'user' AND node.id STARTS WITH 'user-node:'
          AND node.visible_from_order IS NOT NULL AND node.visible_from_order >= 1
          AND node.visible_from_order <= $visible_until_order
        RETURN node.id AS id, node.series_id AS series_id, node.user_id AS user_id,
          '{node_type.value}' AS type,
          node.label AS label, node.visible_from_order AS visible_from_order,
          node.origin AS origin, node.episode_id AS episode_id,
          node.created_at AS created_at, node.updated_at AS updated_at
    """ for node_type in CustomNodeType
}

CUSTOM_NODE_UPDATE_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""
        MATCH (node:{node_type.value} {{id: $id, series_id: $series_id}})
        WHERE node.origin = 'user' AND node.id STARTS WITH 'user-node:'
          AND ($is_admin = true OR node.user_id = $user_id)
        SET node.label = $label, node.updated_at = $updated_at
        RETURN node.id AS id, node.series_id AS series_id, node.user_id AS user_id,
          '{node_type.value}' AS type,
          node.label AS label, node.visible_from_order AS visible_from_order,
          node.origin AS origin, node.episode_id AS episode_id,
          node.created_at AS created_at, node.updated_at AS updated_at
    """ for node_type in CustomNodeType
}

CUSTOM_NODE_DELETE_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""
        MATCH (node:{node_type.value} {{id: $id, series_id: $series_id}})
        WHERE node.origin = 'user' AND node.id STARTS WITH 'user-node:'
          AND ($is_admin = true OR node.user_id = $user_id)
        OPTIONAL MATCH (note:UserNote {{origin: 'user', target_id: node.id}})
        OPTIONAL MATCH (claim:Claim {{origin: 'user', claim_type: 'user_authored'}})
        WHERE claim.subject_id = node.id OR claim.object_id = node.id
        WITH node, count(note) + count(claim) AS dependencies
        WITH node.id AS deleted_id, dependencies, node
        FOREACH (_ IN CASE WHEN dependencies = 0 THEN [1] ELSE [] END | DETACH DELETE node)
        RETURN deleted_id AS id, dependencies
    """ for node_type in CustomNodeType
}

CUSTOM_RELATIONSHIP_READ_QUERY = """
    MATCH (claim:Claim {id: $id, series_id: $series_id, origin: 'user', claim_type: 'user_authored'})
    WHERE claim.id STARTS WITH 'user-rel:' AND claim.visible_from_order IS NOT NULL
      AND claim.visible_from_order >= 1 AND claim.visible_from_order <= $visible_until_order
    RETURN claim.id AS id, claim.series_id AS series_id, claim.user_id AS user_id,
      claim.subject_id AS source,
      claim.object_id AS target, claim.predicate AS type,
      claim.visible_from_order AS visible_from_order, claim.origin AS origin,
      claim.episode_id AS episode_id, claim.created_at AS created_at,
      claim.updated_at AS updated_at
"""

CUSTOM_RELATIONSHIP_UPDATE_QUERY = """
    MATCH (claim:Claim {id: $id, series_id: $series_id, origin: 'user', claim_type: 'user_authored'})
    WHERE claim.id STARTS WITH 'user-rel:'
      AND ($is_admin = true OR claim.user_id = $user_id)
    SET claim.predicate = $predicate, claim.updated_at = $updated_at
    RETURN claim.id AS id, claim.series_id AS series_id, claim.user_id AS user_id,
      claim.subject_id AS source,
      claim.object_id AS target, claim.predicate AS type,
      claim.visible_from_order AS visible_from_order, claim.origin AS origin,
      claim.episode_id AS episode_id, claim.created_at AS created_at,
      claim.updated_at AS updated_at
"""

CUSTOM_RELATIONSHIP_DELETE_QUERY = """
    MATCH (claim:Claim {id: $id, series_id: $series_id, origin: 'user', claim_type: 'user_authored'})
    WHERE claim.id STARTS WITH 'user-rel:'
      AND ($is_admin = true OR claim.user_id = $user_id)
    DELETE claim RETURN $id AS id
"""

OWNERSHIP_QUERY = """
    MATCH (resource {id: $id, series_id: $series_id})
    RETURN resource.origin AS origin, resource.user_id AS user_id, resource.id AS id LIMIT 1
"""

NOTE_UPDATE_QUERY = """
    MATCH (note:UserNote {id: $id, series_id: $series_id, origin: 'user'})
    WHERE note.visible_from_order IS NOT NULL AND note.visible_from_order >= 1
      AND ($is_admin = true OR note.user_id = $user_id)
    SET note.content = $content, note.updated_at = $updated_at
    RETURN note.id AS id, note.series_id AS series_id,
      note.user_id AS user_id, note.target_type AS target_type, note.target_id AS target_id,
      note.content AS content, note.origin AS origin,
      note.visible_from_order AS visible_from_order,
      note.created_at AS created_at, note.updated_at AS updated_at
"""

NOTE_LIST_QUERIES: Mapping[NoteTargetType, str] = {
    target_type: f"""
        MATCH (note:UserNote {{series_id: $series_id, origin: 'user'}})
        MATCH (note)-[:REFERS_TO]->(target:{target_type.value} {{id: note.target_id,
          series_id: $series_id}})
        WHERE note.target_type = '{target_type.value}'
          AND note.visible_from_order IS NOT NULL
          AND note.visible_from_order >= 1
          AND target.visible_from_order IS NOT NULL
          AND target.visible_from_order >= 1
          AND note.visible_from_order <= $visible_until_order
          AND target.visible_from_order <= $visible_until_order
          AND ($target_id IS NULL OR note.target_id = $target_id)
        RETURN note.id AS id, note.series_id AS series_id, note.user_id AS user_id,
          note.target_type AS target_type, note.target_id AS target_id,
          note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order,
          note.created_at AS created_at, note.updated_at AS updated_at
        ORDER BY note.updated_at DESC, note.id ASC
    """ for target_type in NoteTargetType
}

NOTE_GET_QUERIES = NOTE_LIST_QUERIES

NOTE_DELETE_QUERY = """
    MATCH (note:UserNote {id: $id, series_id: $series_id, origin: 'user'})
    WHERE $is_admin = true OR note.user_id = $user_id
    MATCH (note)-[attachment:REFERS_TO {origin: 'user', series_id: $series_id}]->()
    WITH note.id AS deleted_id, attachment, note
    DELETE attachment, note
    RETURN deleted_id AS id
"""

BOUNDARY_VALIDATION_QUERY = """
    MATCH (:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
    WHERE episode.episode_order = $visible_until_order
      AND episode.visible_from_order IS NOT NULL
      AND episode.visible_from_order >= 1
      AND episode.visible_from_order <= $visible_until_order
    RETURN episode.id AS episode_id
"""


class UserContentRepository:
    def __init__(self, database: Neo4jDatabase) -> None:
        self.database = database

    @staticmethod
    def note_command(series_id: str, user_id: str, request: NoteCreate) -> NoteCreateCommand:
        _series(series_id)
        return NoteCreateCommand(
            f"user-note:{uuid4()}", series_id, user_id, request.target_type,
            request.target_id, request.content, (now := _utc_now()), now
        )

    async def create_note(self, series_id: str, user_id: str, request: NoteCreate) -> Any:
        command = self.note_command(series_id, user_id, request)
        query = NOTE_CREATE_QUERIES.get(command.target_type)
        if query is None:
            raise UserContentValidationError("Unsupported note target")
        return await self.database.execute_write(self._create_note, (command, query))

    @staticmethod
    def custom_node_command(
        series_id: str, user_id: str, request: CustomNodeCreate
    ) -> CustomNodeCreateCommand:
        _series(series_id)
        return CustomNodeCreateCommand(
            f"user-node:{uuid4()}", series_id, user_id, request.node_type,
            request.label, request.episode_id, (now := _utc_now()), now
        )

    async def create_custom_node(self, series_id: str, user_id: str, request: CustomNodeCreate) -> Any:
        command = self.custom_node_command(series_id, user_id, request)
        query = CUSTOM_NODE_CREATE_QUERIES.get(command.node_type)
        if query is None:
            raise UserContentValidationError("Unsupported custom node type")
        return await self.database.execute_write(self._create_custom_node, (command, query))

    @staticmethod
    async def _create_custom_node(tx: Any, payload: tuple[CustomNodeCreateCommand, str]) -> Any:
        command, query = payload
        result = await _run_create(tx, query,
            "episode not found",
            id=command.id, series_id=command.series_id,
            user_id=command.user_id,
            label=command.label, episode_id=command.episode_id,
            created_at=command.created_at, updated_at=command.updated_at)
        snapshot = RevisionRepository.take_snapshot(result)
        await RevisionRepository.log_revision(
            tx, series_id=command.series_id,
            resource_type=command.node_type.value,
            resource_id=command.id, action=RevisionAction.CREATED,
            before=None, after=snapshot,
            visible_from_order=result["visible_from_order"],
            created_at=command.created_at)
        return result

    @staticmethod
    def custom_relationship_command(
        series_id: str, user_id: str, request: CustomRelationshipCreate
    ) -> CustomRelationshipCreateCommand:
        _series(series_id)
        return CustomRelationshipCreateCommand(
            f"user-rel:{uuid4()}", series_id, user_id, request.source_id,
            request.target_id, request.predicate, request.episode_id,
            (now := _utc_now()), now
        )

    async def create_custom_relationship(
        self, series_id: str, user_id: str, request: CustomRelationshipCreate
    ) -> Any:
        command = self.custom_relationship_command(series_id, user_id, request)
        return await self.database.execute_write(self._create_custom_relationship, command)

    @staticmethod
    async def _create_custom_relationship(tx: Any, command: CustomRelationshipCreateCommand) -> Any:
        result = await _run_create(tx, CUSTOM_RELATIONSHIP_CREATE_QUERY,
            "relationship endpoint not found",
            id=command.id, series_id=command.series_id, source_id=command.source_id,
            target_id=command.target_id, predicate=command.predicate.value,
            episode_id=command.episode_id, user_id=command.user_id,
            created_at=command.created_at,
            updated_at=command.updated_at)
        snapshot = RevisionRepository.take_snapshot(result)
        await RevisionRepository.log_revision(
            tx, series_id=command.series_id, resource_type="Claim",
            resource_id=command.id, action=RevisionAction.CREATED,
            before=None, after=snapshot,
            visible_from_order=result["visible_from_order"],
            created_at=command.created_at)
        return result

    async def _custom_read(self, series_id: str, resource_id: str, boundary: int, queries: list[str]) -> Any:
        _series(series_id)
        boundary = await self._require_persisted_boundary(series_id, boundary)
        rows: list[dict[str, Any]] = []
        for query in queries:
            rows.extend(await self.database.execute_query(query, id=resource_id, series_id=series_id,
                                                          visible_until_order=boundary))
        if not rows:
            raise UserContentNotFound("resource not found")
        return _native(rows[0])

    async def get_custom_node(self, series_id: str, node_id: str, boundary: int) -> Any:
        _resource_id(node_id)
        return await self._custom_read(series_id, node_id, boundary, list(CUSTOM_NODE_READ_QUERIES.values()))

    async def update_custom_node(
        self, series_id: str, node_id: str, user_id: str,
        request: CustomNodeUpdate, *, is_admin: bool = False,
    ) -> Any:
        _series(series_id); _resource_id(node_id)
        command = CustomUpdateCommand(
            node_id, series_id, user_id, request.label, _utc_now(), is_admin
        )
        return await self.database.execute_write(self._update_custom_node, command)

    @staticmethod
    async def _update_custom_node(tx: Any, command: CustomUpdateCommand) -> Any:
        # Capture state before mutation
        old_row = await (await tx.run(
            "MATCH (node {id: $id, series_id: $series_id}) "
            "RETURN node.id AS id, node.series_id AS series_id, "
            "labels(node)[0] AS type, node.label AS label, "
            "node.visible_from_order AS visible_from_order, "
            "node.origin AS origin, node.episode_id AS episode_id, "
            "node.user_id AS user_id",
            id=command.id, series_id=command.series_id)).single()
        old_state = _native(old_row.data()) if old_row else None
        resource_type = old_state.get("type", "?") if old_state else "?"

        for query in CUSTOM_NODE_UPDATE_QUERIES.values():
            record = await (await tx.run(query, id=command.id, series_id=command.series_id,
                                         label=command.value, updated_at=command.updated_at,
                                         user_id=command.user_id,
                                         is_admin=command.is_admin)).single()
            if record is not None:
                result_data = _native(record.data())
                before = RevisionRepository.take_snapshot(old_state) if old_state else None
                after = RevisionRepository.take_snapshot(result_data)
                await RevisionRepository.log_revision(
                    tx, series_id=command.series_id,
                    resource_type=resource_type,
                    resource_id=command.id, action=RevisionAction.UPDATED,
                    before=before, after=after,
                    visible_from_order=result_data["visible_from_order"],
                    created_at=command.updated_at)
                return result_data
        ownership = await (await tx.run(OWNERSHIP_QUERY, id=command.id, series_id=command.series_id)).single()
        _raise_on_ownership_conflict(ownership, command.user_id, command.is_admin, "node not found")

    async def delete_custom_node(
        self, series_id: str, node_id: str, user_id: str, *, is_admin: bool = False
    ) -> None:
        _series(series_id); _resource_id(node_id)
        result = await self.database.execute_write(
            self._delete_custom_node, (series_id, node_id, user_id, is_admin)
        )
        if result == "conflict":
            raise UserContentConflict("resource in use")
        if result is None:
            raise UserContentNotFound("node not found")

    @staticmethod
    async def _delete_custom_node(tx: Any, payload: tuple[str, str, str, bool]) -> Any:
        series_id, node_id, user_id, is_admin = payload
        # Capture state before deletion
        old_row = await (await tx.run(
            "MATCH (node {id: $id, series_id: $series_id}) "
            "RETURN node.id AS id, node.series_id AS series_id, "
            "labels(node)[0] AS type, node.label AS label, "
            "node.visible_from_order AS visible_from_order, "
            "node.origin AS origin, node.episode_id AS episode_id, "
            "node.user_id AS user_id",
            id=node_id, series_id=series_id)).single()
        old_state = _native(old_row.data()) if old_row else None
        resource_type = old_state.get("type", "?") if old_state else "?"

        for query in CUSTOM_NODE_DELETE_QUERIES.values():
            record = await (await tx.run(
                query, id=node_id, series_id=series_id,
                user_id=user_id, is_admin=is_admin,
            )).single()
            if record is not None:
                data = record.data()
                if data.get("dependencies", 0):
                    return "conflict"
                deleted_id = data.get("id")
                if old_state and deleted_id:
                    before = RevisionRepository.take_snapshot(old_state)
                    await RevisionRepository.log_revision(
                        tx, series_id=series_id,
                        resource_type=resource_type,
                        resource_id=node_id, action=RevisionAction.DELETED,
                        before=before, after=None,
                        visible_from_order=old_state["visible_from_order"],
                        created_at=_utc_now())
                return deleted_id
        ownership = await (await tx.run(OWNERSHIP_QUERY, id=node_id, series_id=series_id)).single()
        _raise_on_ownership_conflict(ownership, user_id, is_admin, "node not found")

    async def get_custom_relationship(self, series_id: str, relationship_id: str, boundary: int) -> Any:
        _resource_id(relationship_id)
        return await self._custom_read(series_id, relationship_id, boundary, [CUSTOM_RELATIONSHIP_READ_QUERY])

    async def update_custom_relationship(
        self, series_id: str, relationship_id: str, user_id: str,
        request: CustomRelationshipUpdate, *, is_admin: bool = False,
    ) -> Any:
        _series(series_id); _resource_id(relationship_id)
        command = CustomUpdateCommand(
            relationship_id, series_id, user_id, request.predicate.value, _utc_now(), is_admin
        )
        return await self.database.execute_write(self._update_custom_relationship, command)

    @staticmethod
    async def _update_custom_relationship(tx: Any, command: CustomUpdateCommand) -> Any:
        # Capture state before mutation
        old_row = await (await tx.run(
            "MATCH (claim:Claim {id: $id, series_id: $series_id}) "
            "RETURN claim.id AS id, claim.series_id AS series_id, "
            "claim.subject_id AS source, claim.object_id AS target, "
            "claim.predicate AS type, claim.episode_id AS episode_id, "
            "claim.visible_from_order AS visible_from_order, "
            "claim.origin AS origin, claim.user_id AS user_id",
            id=command.id, series_id=command.series_id)).single()
        old_state = _native(old_row.data()) if old_row else None
        before = RevisionRepository.take_snapshot(old_state) if old_state else None

        record = await (await tx.run(CUSTOM_RELATIONSHIP_UPDATE_QUERY, id=command.id,
                                     series_id=command.series_id, predicate=command.value,
                                     updated_at=command.updated_at,
                                     user_id=command.user_id,
                                     is_admin=command.is_admin)).single()
        if record is None:
            ownership = await (await tx.run(OWNERSHIP_QUERY, id=command.id, series_id=command.series_id)).single()
            _raise_on_ownership_conflict(
                ownership, command.user_id, command.is_admin, "relationship not found"
            )
        result_data = _native(record.data())
        after = RevisionRepository.take_snapshot(result_data)

        await RevisionRepository.log_revision(
            tx, series_id=command.series_id, resource_type="Claim",
            resource_id=command.id, action=RevisionAction.UPDATED,
            before=before, after=after,
            visible_from_order=result_data["visible_from_order"],
            created_at=command.updated_at)
        return result_data

    async def delete_custom_relationship(
        self, series_id: str, relationship_id: str, user_id: str, *, is_admin: bool = False
    ) -> None:
        _series(series_id); _resource_id(relationship_id)
        result = await self.database.execute_write(
            self._delete_custom_relationship, (series_id, relationship_id, user_id, is_admin)
        )
        if result is None:
            raise UserContentNotFound("relationship not found")

    @staticmethod
    async def _delete_custom_relationship(tx: Any, payload: tuple[str, str, str, bool]) -> Any:
        series_id, relationship_id, user_id, is_admin = payload
        # Capture state before deletion
        old_row = await (await tx.run(
            "MATCH (claim:Claim {id: $id, series_id: $series_id}) "
            "RETURN claim.id AS id, claim.series_id AS series_id, "
            "claim.subject_id AS source, claim.object_id AS target, "
            "claim.predicate AS type, claim.episode_id AS episode_id, "
            "claim.visible_from_order AS visible_from_order, "
            "claim.origin AS origin, claim.user_id AS user_id",
            id=relationship_id, series_id=series_id)).single()
        old_state = _native(old_row.data()) if old_row else None

        record = await (await tx.run(CUSTOM_RELATIONSHIP_DELETE_QUERY, id=relationship_id,
                                     series_id=series_id, user_id=user_id,
                                     is_admin=is_admin)).single()
        deleted_id = None if record is None else record.data().get("id")

        if old_state and deleted_id:
            before = RevisionRepository.take_snapshot(old_state)
            await RevisionRepository.log_revision(
                tx, series_id=series_id, resource_type="Claim",
                resource_id=relationship_id, action=RevisionAction.DELETED,
                before=before, after=None,
                visible_from_order=old_state["visible_from_order"],
                created_at=_utc_now())

        if record is None:
            ownership = await (await tx.run(OWNERSHIP_QUERY, id=relationship_id, series_id=series_id)).single()
            _raise_on_ownership_conflict(ownership, user_id, is_admin, "relationship not found")
        return deleted_id

    @staticmethod
    async def _create_note(tx: Any, payload: tuple[NoteCreateCommand, str]) -> Any:
        command, query = payload
        result = await _run_create(tx, query,
            "note target not found",
            id=command.id, series_id=command.series_id,
            user_id=command.user_id,
            target_type=command.target_type.value, target_id=command.target_id,
            content=command.content, created_at=command.created_at,
            updated_at=command.updated_at)
        snapshot = RevisionRepository.take_snapshot(result)
        await RevisionRepository.log_revision(
            tx, series_id=command.series_id, resource_type="UserNote",
            resource_id=command.id, action=RevisionAction.CREATED,
            before=None, after=snapshot,
            visible_from_order=result["visible_from_order"],
            created_at=command.created_at)
        return result

    async def update_note(
        self, series_id: str, note_id: str, user_id: str,
        request: NoteUpdate, *, is_admin: bool = False,
    ) -> Any:
        _series(series_id); _namespace(note_id, "user-note:")
        command = NoteUpdateCommand(note_id, series_id, user_id, request.content, _utc_now(), is_admin)
        return await self.database.execute_write(self._update_note, command)

    @staticmethod
    async def _update_note(tx: Any, command: NoteUpdateCommand) -> Any:
        # Capture state before mutation
        old_row = await (await tx.run(
            "MATCH (note:UserNote {id: $id, series_id: $series_id}) "
            "RETURN note.id AS id, note.series_id AS series_id, "
            "note.target_type AS target_type, note.target_id AS target_id, "
            "note.content AS content, note.origin AS origin, "
            "note.visible_from_order AS visible_from_order, "
            "note.created_at AS created_at, note.updated_at AS updated_at, "
            "note.user_id AS user_id",
            id=command.id, series_id=command.series_id)).single()
        before = RevisionRepository.take_snapshot(
            _native(old_row.data())) if old_row else None

        result = await tx.run(NOTE_UPDATE_QUERY, id=command.id, series_id=command.series_id,
            content=command.content, updated_at=command.updated_at,
            user_id=command.user_id, is_admin=command.is_admin)
        record = await result.single()
        if record is None:
            ownership = await (await tx.run(
                OWNERSHIP_QUERY, id=command.id, series_id=command.series_id
            )).single()
            _raise_on_ownership_conflict(ownership, command.user_id, command.is_admin, "note not found")
        result_data = _native(record.data())
        after = RevisionRepository.take_snapshot(result_data)

        await RevisionRepository.log_revision(
            tx, series_id=command.series_id, resource_type="UserNote",
            resource_id=command.id, action=RevisionAction.UPDATED,
            before=before, after=after,
            visible_from_order=result_data["visible_from_order"],
            created_at=command.updated_at)
        return result_data

    async def delete_note(
        self, series_id: str, note_id: str, user_id: str, *, is_admin: bool = False
    ) -> None:
        _series(series_id)
        _namespace(note_id, "user-note:")
        result = await self.database.execute_write(
            self._delete_note, (series_id, note_id, user_id, is_admin)
        )
        if result is None:
            raise UserContentNotFound("note not found")

    @staticmethod
    async def _delete_note(tx: Any, payload: tuple[str, str, str, bool]) -> Any:
        series_id, note_id, user_id, is_admin = payload
        # Capture state before deletion
        old_row = await (await tx.run(
            "MATCH (note:UserNote {id: $id, series_id: $series_id}) "
            "RETURN note.id AS id, note.series_id AS series_id, "
            "note.target_type AS target_type, note.target_id AS target_id, "
            "note.content AS content, note.origin AS origin, "
            "note.visible_from_order AS visible_from_order, "
            "note.created_at AS created_at, note.updated_at AS updated_at, "
            "note.user_id AS user_id",
            id=note_id, series_id=series_id)).single()
        if old_row is None:
            return None

        old_state = _native(old_row.data())
        # Owner-scoped delete — a cross-owner or legacy-non-admin attempt
        # yields zero rows and is classified via OWNERSHIP_QUERY below.
        result = await tx.run(
            NOTE_DELETE_QUERY, id=note_id, series_id=series_id,
            user_id=user_id, is_admin=is_admin,
        )
        record = await result.single()
        if record is None:
            ownership = await (await tx.run(
                OWNERSHIP_QUERY, id=note_id, series_id=series_id
            )).single()
            _raise_on_ownership_conflict(ownership, user_id, is_admin, "note not found")
        # Log the DELETED revision only after the owner-scoped delete
        # actually matched — no ghost revisions for failed cross-owner deletes.
        before = RevisionRepository.take_snapshot(old_state)
        await RevisionRepository.log_revision(
            tx, series_id=series_id, resource_type="UserNote",
            resource_id=note_id, action=RevisionAction.DELETED,
            before=before, after=None,
            visible_from_order=old_state["visible_from_order"],
            created_at=_utc_now())
        return record.data().get("id")

    @staticmethod
    def validate_boundary(visible_until_order: int) -> int:
        if type(visible_until_order) is not int or visible_until_order <= 0:
            raise UserContentValidationError("visible_until_order must be positive")
        return visible_until_order

    async def _require_persisted_boundary(
        self, series_id: str, visible_until_order: int
    ) -> int:
        boundary = self.validate_boundary(visible_until_order)
        rows = await self.database.execute_query(
            BOUNDARY_VALIDATION_QUERY,
            series_id=series_id,
            visible_until_order=boundary,
        )
        if not rows:
            raise UserContentValidationError(
                "visible_until_order must identify a persisted episode"
            )
        return boundary

    async def get_note(self, series_id: str, note_id: str, visible_until_order: int) -> Any:
        _series(series_id); _namespace(note_id, "user-note:")
        boundary = await self._require_persisted_boundary(series_id, visible_until_order)
        # A UNION is intentionally avoided: target labels are selected only from
        # this closed server-owned map, never from request text.
        query = "\nUNION\n".join(NOTE_GET_QUERIES.values())
        records = await self.database.execute_query(query, id=note_id, series_id=series_id,
            visible_until_order=boundary, target_id=None)
        if not records:
            raise UserContentNotFound("note not found")
        return _native(records[0])

    async def list_notes(
        self,
        series_id: str,
        visible_until_order: int,
        target_type: NoteTargetType | None = None,
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        _series(series_id)
        boundary = await self._require_persisted_boundary(series_id, visible_until_order)
        if (target_type is None) != (target_id is None):
            raise UserContentValidationError("target_type and target_id must be provided together")
        queries = [NOTE_LIST_QUERIES[target_type]] if target_type else list(NOTE_LIST_QUERIES.values())
        rows: list[dict[str, Any]] = []
        for query in queries:
            rows.extend(await self.database.execute_query(
                query, series_id=series_id, visible_until_order=boundary,
                target_id=target_id,
            ))
        if target_id is not None:
            rows = [row for row in rows if row.get("target_id") == target_id]
        return sorted(
            (_native(row) for row in rows),
            key=lambda row: (
                -(_parse_dt(row["updated_at"]).timestamp() if isinstance(row["updated_at"], str) else row["updated_at"].timestamp()),
                row["id"],
            ),
        )
