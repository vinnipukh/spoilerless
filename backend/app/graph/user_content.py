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

from backend.app.domain.user_content import (
    CustomNodeCreate,
    CustomNodeType,
    CustomRelationshipCreate,
    CustomRelationshipType,
    NoteCreate,
    NoteTargetType,
    NoteUpdate,
)
from backend.app.graph.database import Neo4jDatabase


class UserContentValidationError(ValueError):
    """A request failed repository-level safety validation."""


class UserContentConflict(RuntimeError):
    pass


class UserContentNotFound(LookupError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _namespace(value: str, prefix: str) -> None:
    if (
        not isinstance(value, str)
        or not re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9._-]+", value)
    ):
        raise UserContentValidationError(f"Expected {prefix} namespace")


def _series(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
        raise UserContentValidationError("Invalid series identifier")


@dataclass(frozen=True)
class NoteCreateCommand:
    id: str
    series_id: str
    target_type: NoteTargetType
    target_id: str
    content: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NoteUpdateCommand:
    id: str
    series_id: str
    content: str
    updated_at: datetime


@dataclass(frozen=True)
class CustomNodeCreateCommand:
    id: str
    series_id: str
    node_type: CustomNodeType
    label: str
    episode_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CustomRelationshipCreateCommand:
    id: str
    series_id: str
    source_id: str
    target_id: str
    predicate: CustomRelationshipType
    episode_id: str
    created_at: datetime
    updated_at: datetime


NOTE_CREATE_QUERIES: Mapping[NoteTargetType, str] = {
    NoteTargetType.CHARACTER: """
        MATCH (series:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
        MATCH (target:Character {id: $target_id, series_id: $series_id})
        WHERE target.origin IN ['canonical', 'candidate', 'user']
          AND target.visible_from_order IS NOT NULL AND target.visible_from_order >= 1
          AND episode.episode_order = target.visible_from_order
        CREATE (note:UserNote {id: $id, series_id: $series_id,
          target_type: $target_type, target_id: $target_id, content: $content,
          visible_from_order: target.visible_from_order, origin: 'user',
          created_at: $created_at, updated_at: $updated_at})
        CREATE (note)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
          visible_from_order: target.visible_from_order, origin: 'user'}]->(target)
        RETURN note.id AS id, note.series_id AS series_id, note.target_type AS target_type,
          note.target_id AS target_id, note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order, note.created_at AS created_at,
          note.updated_at AS updated_at
    """,
    NoteTargetType.CLAIM: """
        MATCH (series:Series {id: $series_id})<-[:PART_OF]-(episode:Episode)
        MATCH (target:Claim {id: $target_id, series_id: $series_id})
        WHERE target.origin IN ['canonical', 'candidate', 'user']
          AND target.visible_from_order IS NOT NULL AND target.visible_from_order >= 1
          AND episode.episode_order = target.visible_from_order
        CREATE (note:UserNote {id: $id, series_id: $series_id,
          target_type: $target_type, target_id: $target_id, content: $content,
          visible_from_order: target.visible_from_order, origin: 'user',
          created_at: $created_at, updated_at: $updated_at})
        CREATE (note)-[:REFERS_TO {id: $id + ':refers_to', series_id: $series_id,
          visible_from_order: target.visible_from_order, origin: 'user'}]->(target)
        RETURN note.id AS id, note.series_id AS series_id, note.target_type AS target_type,
          note.target_id AS target_id, note.content AS content, note.origin AS origin,
          note.visible_from_order AS visible_from_order, note.created_at AS created_at,
          note.updated_at AS updated_at
    """,
}

CUSTOM_NODE_CREATE_QUERIES: Mapping[CustomNodeType, str] = {
    node_type: f"""
        MATCH (episode:Episode {{id: $episode_id, series_id: $series_id}})
        WHERE episode.episode_order IS NOT NULL AND episode.episode_order >= 1
        CREATE (node:{node_type.value} {{id: $id, series_id: $series_id, label: $label,
          episode_id: $episode_id, visible_from_order: episode.episode_order,
          origin: 'user', created_at: $created_at, updated_at: $updated_at}})
        RETURN node.id AS id, node.series_id AS series_id, node.label AS label,
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
    CREATE (claim:Claim {id: $id, series_id: $series_id, subject_id: $source_id,
      object_id: $target_id, predicate: $predicate, claim_type: 'user_authored',
      episode_id: $episode_id, visible_from_order:
        CASE WHEN source.visible_from_order > target.visible_from_order
          AND source.visible_from_order > episode.episode_order THEN source.visible_from_order
          WHEN target.visible_from_order > episode.episode_order THEN target.visible_from_order
          ELSE episode.episode_order END,
      origin: 'user', created_at: $created_at, updated_at: $updated_at})
    RETURN claim.id AS id, claim.series_id AS series_id, claim.subject_id AS source,
      claim.object_id AS target, claim.predicate AS type, claim.episode_id AS episode_id,
      claim.visible_from_order AS visible_from_order, claim.origin AS origin,
      claim.created_at AS created_at, claim.updated_at AS updated_at
"""

NOTE_UPDATE_QUERY = """
    MATCH (note:UserNote {id: $id, series_id: $series_id, origin: 'user'})
    WHERE note.visible_from_order IS NOT NULL AND note.visible_from_order >= 1
    SET note.content = $content, note.updated_at = $updated_at
    RETURN note.id AS id, note.content AS content, note.updated_at AS updated_at
"""


class UserContentRepository:
    def __init__(self, database: Neo4jDatabase) -> None:
        self.database = database

    @staticmethod
    def note_command(series_id: str, request: NoteCreate) -> NoteCreateCommand:
        _series(series_id)
        return NoteCreateCommand(
            f"user-note:{uuid4()}", series_id, request.target_type, request.target_id,
            request.content, _utc_now(), _utc_now()
        )

    async def create_note(self, series_id: str, request: NoteCreate) -> Any:
        command = self.note_command(series_id, request)
        query = NOTE_CREATE_QUERIES.get(command.target_type)
        if query is None:
            raise UserContentValidationError("Unsupported note target")
        return await self.database.execute_write(self._create_note, (command, query))

    @staticmethod
    def custom_node_command(series_id: str, request: CustomNodeCreate) -> CustomNodeCreateCommand:
        _series(series_id)
        return CustomNodeCreateCommand(
            f"user-node:{uuid4()}", series_id, request.node_type, request.label,
            request.episode_id, _utc_now(), _utc_now()
        )

    async def create_custom_node(self, series_id: str, request: CustomNodeCreate) -> Any:
        command = self.custom_node_command(series_id, request)
        query = CUSTOM_NODE_CREATE_QUERIES.get(command.node_type)
        if query is None:
            raise UserContentValidationError("Unsupported custom node type")
        return await self.database.execute_write(self._create_custom_node, (command, query))

    @staticmethod
    async def _create_custom_node(tx: Any, payload: tuple[CustomNodeCreateCommand, str]) -> Any:
        command, query = payload
        result = await tx.run(query, id=command.id, series_id=command.series_id,
            label=command.label, episode_id=command.episode_id,
            created_at=command.created_at, updated_at=command.updated_at)
        record = await result.single()
        if record is None:
            raise UserContentNotFound("episode not found")
        return record.data()

    @staticmethod
    def custom_relationship_command(
        series_id: str, request: CustomRelationshipCreate
    ) -> CustomRelationshipCreateCommand:
        _series(series_id)
        return CustomRelationshipCreateCommand(
            f"user-rel:{uuid4()}", series_id, request.source_id, request.target_id,
            request.predicate, request.episode_id, _utc_now(), _utc_now()
        )

    async def create_custom_relationship(
        self, series_id: str, request: CustomRelationshipCreate
    ) -> Any:
        command = self.custom_relationship_command(series_id, request)
        return await self.database.execute_write(self._create_custom_relationship, command)

    @staticmethod
    async def _create_custom_relationship(tx: Any, command: CustomRelationshipCreateCommand) -> Any:
        result = await tx.run(
            CUSTOM_RELATIONSHIP_CREATE_QUERY,
            id=command.id, series_id=command.series_id, source_id=command.source_id,
            target_id=command.target_id, predicate=command.predicate.value,
            episode_id=command.episode_id, created_at=command.created_at,
            updated_at=command.updated_at,
        )
        record = await result.single()
        if record is None:
            raise UserContentNotFound("relationship endpoint not found")
        return record.data()

    @staticmethod
    async def _create_note(tx: Any, payload: tuple[NoteCreateCommand, str]) -> Any:
        command, query = payload
        result = await tx.run(query, id=command.id, series_id=command.series_id,
            target_type=command.target_type.value, target_id=command.target_id,
            content=command.content, created_at=command.created_at,
            updated_at=command.updated_at)
        record = await result.single()
        if record is None:
            raise UserContentNotFound("note target not found")
        return record.data()

    async def update_note(self, series_id: str, note_id: str, request: NoteUpdate) -> Any:
        _series(series_id); _namespace(note_id, "user-note:")
        command = NoteUpdateCommand(note_id, series_id, request.content, _utc_now())
        return await self.database.execute_write(self._update_note, command)

    @staticmethod
    async def _update_note(tx: Any, command: NoteUpdateCommand) -> Any:
        result = await tx.run(NOTE_UPDATE_QUERY, id=command.id, series_id=command.series_id,
            content=command.content, updated_at=command.updated_at)
        record = await result.single()
        if record is None:
            raise UserContentNotFound("note not found")
        return record.data()

    @staticmethod
    def validate_boundary(visible_until_order: int) -> int:
        if type(visible_until_order) is not int or visible_until_order <= 0:
            raise UserContentValidationError("visible_until_order must be positive")
        return visible_until_order

    async def get_note(self, series_id: str, note_id: str, visible_until_order: int) -> Any:
        _series(series_id); _namespace(note_id, "user-note:")
        boundary = self.validate_boundary(visible_until_order)
        query = """
            MATCH (note:UserNote {id: $id, series_id: $series_id, origin: 'user'})
            WHERE note.visible_from_order IS NOT NULL AND note.visible_from_order >= 1
              AND note.visible_from_order <= $visible_until_order
            RETURN note.id AS id, note.series_id AS series_id, note.target_type AS target_type,
              note.target_id AS target_id, note.content AS content, note.origin AS origin,
              note.visible_from_order AS visible_from_order, note.created_at AS created_at,
              note.updated_at AS updated_at
        """
        records = await self.database.execute_query(query, id=note_id, series_id=series_id,
            visible_until_order=boundary)
        if not records:
            raise UserContentNotFound("note not found")
        return records[0]
