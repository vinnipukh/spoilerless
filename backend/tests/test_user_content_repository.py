from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.domain.user_content import (
    CustomNodeCreate,
    CustomRelationshipCreate,
    NoteCreate,
)
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.user_content import (
    NOTE_CREATE_QUERIES,
    UserContentRepository,
    UserContentValidationError,
)


class FakeRecord:
    def __init__(self, data: dict):
        self._data = data

    def data(self) -> dict:
        return self._data


class FakeResult:
    def __init__(self, data: dict | None = None):
        self.record = FakeRecord(data) if data is not None else None

    async def single(self):
        return self.record


class FakeTransaction:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **parameters):
        self.calls.append((query, parameters))
        return FakeResult({"id": parameters.get("id", "mock"), "origin": "user", "visible_from_order": 1, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)})


class FakeSession:
    def __init__(self):
        self.commands = []
        self.tx = FakeTransaction()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def execute_write(self, work, command):
        self.commands.append(command)
        # Neo4j may retry the callback. Both invocations receive the same command.
        first = await work(self.tx, command)
        second = await work(self.tx, command)
        assert first["id"] == second["id"]
        return second


class FakeDriver:
    def __init__(self):
        self.sessions: list[FakeSession] = []

    def session(self, *, database: str):
        session = FakeSession()
        self.sessions.append(session)
        return session


@pytest.mark.asyncio
async def test_execute_write_uses_database_scoped_async_session_and_retries_stably():
    database = Neo4jDatabase.__new__(Neo4jDatabase)
    database._driver = FakeDriver()
    database._settings = type("Settings", (), {"neo4j_database": "story-db"})()
    calls = []

    async def work(tx, command):
        calls.append((tx, command))
        return command

    command = {
        "id": "user-note:fixed",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await database.execute_write(work, command)
    assert result is command
    assert len(database.driver.sessions) == 1
    assert database.driver.sessions[0].commands == [command]
    assert len(calls) == 2
    assert calls[0][1] is calls[1][1] is command


@pytest.mark.asyncio
async def test_note_command_id_and_utc_timestamps_survive_callback_retry():
    database = Neo4jDatabase.__new__(Neo4jDatabase)
    database._driver = FakeDriver()
    database._settings = type("Settings", (), {"neo4j_database": "story-db"})()
    repository = UserContentRepository(database)

    result = await repository.create_note(
        "series_dexter",
        NoteCreate(target_type="Character", target_id="character:dexter", content="text"),
    )
    command = database.driver.sessions[0].commands[0][0]
    assert result["id"].startswith("user-note:")
    # calls[0] is the mutation query (calls[1] is the revision log)
    mutation_call_id = database.driver.sessions[0].tx.calls[0][1]["id"]
    assert command.id == mutation_call_id
    assert command.created_at.tzinfo == timezone.utc
    assert command.updated_at.tzinfo == timezone.utc


def test_query_maps_are_closed_and_public_values_are_parameters():
    assert set(NOTE_CREATE_QUERIES) == {"Character", "Claim"}
    for query in NOTE_CREATE_QUERIES.values():
        assert "$target_id" in query
        assert "SET +=" not in query
        assert "{target_id}" not in query
        assert "{target_type}" not in query


@pytest.mark.asyncio
async def test_unsafe_series_or_ownership_input_rejects_before_query_selection():
    database = Neo4jDatabase.__new__(Neo4jDatabase)
    database._driver = FakeDriver()
    database._settings = type("Settings", (), {"neo4j_database": "story-db"})()
    repository = UserContentRepository(database)
    request = NoteCreate(target_type="Character", target_id="character:one", content="x")

    with pytest.raises(UserContentValidationError):
        await repository.create_note("series bad label", request)
    with pytest.raises(UserContentValidationError):
        await repository.update_note("series_dexter", "canonical:note", request.model_copy(update={"content": "y"}))
    assert database.driver.sessions == []


@pytest.mark.asyncio
async def test_reads_validate_positive_boundary_before_query_execution():
    class NoQueryDatabase:
        async def execute_query(self, *_args, **_kwargs):
            raise AssertionError("query must not run")

    repository = UserContentRepository(NoQueryDatabase())
    with pytest.raises(UserContentValidationError):
        await repository.get_note("series_dexter", "user-note:one", 0)


@pytest.mark.asyncio
async def test_custom_node_and_relationship_writes_use_static_queries_and_parameters():
    database = Neo4jDatabase.__new__(Neo4jDatabase)
    database._driver = FakeDriver()
    database._settings = type("Settings", (), {"neo4j_database": "story-db"})()
    repository = UserContentRepository(database)
    await repository.create_custom_node(
        "series_dexter",
        CustomNodeCreate(node_type="Object", label="Blood slide", episode_id="dexter_s01e01"),
    )
    await repository.create_custom_relationship(
        "series_dexter",
        CustomRelationshipCreate(
            source_id="character:dexter", target_id="character:debra",
            predicate="FAMILY_OF", episode_id="dexter_s01e01",
        ),
    )
    calls = [call for session in database.driver.sessions for call in session.tx.calls]
    # Each callback is retried twice by the fake. With revision logging each callback
    # runs the mutation query + log_revision query = 2 queries. 2 retries × 2 queries = 4.
    # Two operations (custom_node + custom_relationship) = 8 calls total.
    assert len(calls) == 8
    # Filter to mutation queries only (revision queries use "revision:" prefix)
    mutation_calls = [(q, p) for q, p in calls if p.get("id", "").startswith(("user-node:", "user-rel:"))]
    assert len(mutation_calls) == 4  # 2 per operation × 2 retries
    for query, parameters in mutation_calls:
        assert "SET +=" not in query
        assert "label" not in query.lower() or "$label" in query
        assert "FAMILY_OF" not in query
