"""Repository-level persistence tests for chat sessions/messages (RAG-09).

Runs against the live local Neo4j instance directly through ``ChatRepository``
/``ProgressRepository`` — no HTTP layer, no LLM.  The single most
spoiler-safety-load-bearing test in this phase lives here: the
Episode-3-then-Episode-1 hide-not-delete regression named verbatim by
06-CONTEXT.md's "Critical regression scenario."

Each test opens its own short-lived ``Neo4jDatabase`` and cleans up the
``ChatSession``/``ChatMessage``/``UserSeriesProgress`` nodes it creates — the
same pattern ``test_chat_api.py`` and ``test_progress_api.py`` use, so no test
in this file crosses an event loop or leaks state into the seed-integrity
audit in ``test_graph_api.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.chat import ChatRepository
from spoilerless.app.repository.progress import ProgressRepository

SERIES_ID = "series_dexter"
CLAIM_HARRY_FAMILY = "dexter:claim:s01e03:dexter_harry_family"
EVIDENCE_S01E03_02 = "dexter:evidence:s01e03:02"
SOURCE_S01E03 = "dexter:source:s01e03"


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db

    async def _cleanup() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query("MATCH (n:ChatSession) DETACH DELETE n")
            await clean.execute_query("MATCH (n:ChatMessage) DETACH DELETE n")
            await clean.execute_query("MATCH (n:UserSeriesProgress) DETACH DELETE n")
        finally:
            await clean.close()

    asyncio.run(_cleanup())


def _fresh_user_id(label: str) -> str:
    return f"user:{label}-{uuid4()}"


# ---------------------------------------------------------------------------
# Task 1: the RAG-09 critical regression scenario (verbatim from CONTEXT.md)
# ---------------------------------------------------------------------------


def test_episode_3_then_episode_1_regression_hides_not_deletes(
    database: Neo4jDatabase,
) -> None:
    """The named regression scenario, all five steps in one test body:

    1. User reaches progress=3.
    2. Asks a question.
    3. Receives and persists an Episode-3-boundary answer with a citation to
       an Episode-3-only claim (``visible_until_order_snapshot=3``).
    4. Moves progress back to Episode 1.
    5. Reopens the session — the Episode-3 answer must not leak through the
       message list (API-shaped), and the identical shared filter used for
       LLM conversation-memory loading must also exclude it.

    Then: raising progress back to 3 re-reveals the same message (same id,
    same content, not duplicated) — hidden, never deleted, confirmed directly
    against Neo4j via the repository (not the API).
    """

    async def _run() -> None:
        chat_repo = ChatRepository(database)
        progress_repo = ProgressRepository(database)
        user_id = _fresh_user_id("regression")
        series_id = SERIES_ID

        # Step 1: progress to 3.
        await progress_repo.upsert(
            user_id, series_id, watched_through_order=3, view_as_of_order=3
        )

        session = await chat_repo.create_session(
            user_id, series_id, "Episode 3 regression session"
        )

        # Step 2/3: ask a question, receive and persist an Episode-3-boundary
        # answer with a citation to an Episode-3-only claim.
        await chat_repo.create_message(
            user_id,
            series_id,
            session.id,
            role="user",
            content="What does Harry reveal to Dexter in Episode 3?",
            visible_until_order_snapshot=3,
        )
        episode_3_citation = [
            {
                "claim_id": CLAIM_HARRY_FAMILY,
                "evidence_id": EVIDENCE_S01E03_02,
                "source_id": SOURCE_S01E03,
                "source_label": "S01E03",
                "source_type": "episode",
                "episode_code": "S01E03",
                "locator": "S01E03 00:20:00",
                "excerpt": "Harry reveals a family secret to Dexter.",
                "related_node_ids": [],
                "related_edge_ids": [],
            }
        ]
        assistant_message = await chat_repo.create_message(
            user_id,
            series_id,
            session.id,
            role="assistant",
            content="Harry reveals a family secret to Dexter in Episode 3.",
            visible_until_order_snapshot=3,
            citations=episode_3_citation,
        )

        # Step 4: lower progress to 1.
        await progress_repo.upsert(
            user_id, series_id, watched_through_order=1, view_as_of_order=1
        )

        # Step 5: reopen the session (GET-shaped read) at the new boundary —
        # the Episode-3 message is absent from the response.
        response_messages = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 1
        )
        response_ids = {m.id for m in response_messages}
        response_contents = {m.content for m in response_messages}
        assert assistant_message.id not in response_ids
        assert (
            "Harry reveals a family secret to Dexter in Episode 3."
            not in response_contents
        )

        # The LLM conversation-memory load uses the identical shared filter
        # — it must also exclude the hidden message from anything sent to
        # the provider.
        context_messages = await chat_repo.list_messages_for_context(
            user_id, series_id, session.id, 1
        )
        context_ids = {m["id"] for m in context_messages}
        context_contents = {m["content"] for m in context_messages}
        assert assistant_message.id not in context_ids
        assert (
            "Harry reveals a family secret to Dexter in Episode 3."
            not in context_contents
        )

        # Direct repository-level existence check: the ChatMessage node was
        # never deleted — hidden is purely a read-time filter, never a write.
        rows = await database.execute_query(
            "MATCH (m:ChatMessage {id: $id}) RETURN m.id AS id",
            id=assistant_message.id,
        )
        assert len(rows) == 1

        # Raising progress back to 3 re-reveals the same message — same id,
        # same content, not re-created / duplicated.
        restored_messages = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 3
        )
        assert len(restored_messages) == 2
        restored_assistant = next(
            m for m in restored_messages if m.role == "assistant"
        )
        assert restored_assistant.id == assistant_message.id
        assert restored_assistant.content == assistant_message.content

    asyncio.run(_run())


def test_no_delete_cypher_targets_chat_message_on_progress_decrease() -> None:
    """Structural guard (mirrors the acceptance criterion's grep check):

    ``spoilerless/app/repository/chat.py`` must contain no Cypher ``DELETE``
    clause targeting a ``ChatMessage`` node triggered by any progress-related
    code path — hiding is purely a read-time filter, never a write.  The only
    Cypher ``DELETE`` this module's query text may reference at all is the
    distinct, explicitly user-initiated session-delete action
    (``CHAT_SESSION_DELETE_QUERY`` in ``spoilerless/app/graph/chat.py``), which
    is itself never invoked by any progress-decrease code path.
    """
    import inspect

    from spoilerless.app.graph import chat as chat_queries
    from spoilerless.app.repository import chat as chat_repository_module

    # The only query constant whose Cypher text contains a DELETE clause is
    # the explicit session-delete query — never a message-list or
    # message-create query (what any progress-decrease read/write path uses).
    query_constants = {
        name: value
        for name, value in vars(chat_queries).items()
        if name.isupper() and isinstance(value, str)
    }
    delete_bearing = {
        name for name, cypher in query_constants.items() if "DELETE" in cypher
    }
    assert delete_bearing == {"CHAT_SESSION_DELETE_QUERY"}
    assert "DELETE" not in chat_queries.CHAT_MESSAGE_LIST_QUERY
    assert "DELETE" not in chat_queries.CHAT_MESSAGE_CREATE_QUERY

    # The repository methods reachable from any progress-decrease read/write
    # path (listing or creating messages) never call the session-delete path.
    list_source = inspect.getsource(chat_repository_module.ChatRepository._list_messages)
    create_message_source = inspect.getsource(
        chat_repository_module.ChatRepository.create_message
    )
    assert "delete_session" not in list_source
    assert "delete_session" not in create_message_source


# ---------------------------------------------------------------------------
# Task 1: boundary-exactness matrix
# ---------------------------------------------------------------------------


def test_boundary_exactness_matrix(database: Neo4jDatabase) -> None:
    """Equal-to-boundary is visible; one order above is hidden; one order
    below is visible."""

    async def _run() -> None:
        chat_repo = ChatRepository(database)
        user_id = _fresh_user_id("boundary")
        series_id = SERIES_ID
        session = await chat_repo.create_session(user_id, series_id, "Boundary session")

        equal = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="assistant", content="equal to boundary",
            visible_until_order_snapshot=2,
        )
        above = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="assistant", content="one above boundary",
            visible_until_order_snapshot=3,
        )
        below = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="assistant", content="one below boundary",
            visible_until_order_snapshot=1,
        )

        visible = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 2
        )
        visible_ids = {m.id for m in visible}

        assert equal.id in visible_ids
        assert above.id not in visible_ids
        assert below.id in visible_ids

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Task 3: Turkish-text round-trip + stable ordering
# ---------------------------------------------------------------------------


def test_turkish_message_content_round_trips_without_corruption(
    database: Neo4jDatabase,
) -> None:
    """Persisting and re-reading Turkish-language content must not mangle
    non-ASCII characters (İ, ı, ş, ğ)."""

    async def _run() -> None:
        chat_repo = ChatRepository(database)
        user_id = _fresh_user_id("turkish")
        series_id = SERIES_ID
        session = await chat_repo.create_session(user_id, series_id, "Türkçe oturum")

        turkish_content = (
            "Dexter'ın kız kardeşi kimdir? İstanbul'da değil, Miami'de "
            "yaşıyor ve şüpheli bir geçmişi var, değil mi?"
        )
        message = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="user", content=turkish_content,
            visible_until_order_snapshot=1,
        )
        assert message.content == turkish_content

        fetched = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 1
        )
        assert fetched[0].content == turkish_content

    asyncio.run(_run())


def test_messages_return_in_stable_created_at_ascending_order_across_repeated_reads(
    database: Neo4jDatabase,
) -> None:
    """Messages come back in stable created_at-ascending order for both the
    API response and the LLM conversation-memory load, on repeated reads."""

    async def _run() -> None:
        chat_repo = ChatRepository(database)
        user_id = _fresh_user_id("ordering")
        series_id = SERIES_ID
        session = await chat_repo.create_session(user_id, series_id, "Ordering session")

        first = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="user", content="first", visible_until_order_snapshot=1,
        )
        second = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="assistant", content="second", visible_until_order_snapshot=1,
        )
        third = await chat_repo.create_message(
            user_id, series_id, session.id,
            role="user", content="third", visible_until_order_snapshot=1,
        )
        expected_order = [first.id, second.id, third.id]

        response_read_1 = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 1
        )
        response_read_2 = await chat_repo.list_messages_for_response(
            user_id, series_id, session.id, 1
        )
        context_read = await chat_repo.list_messages_for_context(
            user_id, series_id, session.id, 1
        )

        assert [m.id for m in response_read_1] == expected_order
        assert [m.id for m in response_read_2] == expected_order
        assert [m["id"] for m in context_read] == expected_order

    asyncio.run(_run())


def test_sessions_list_newest_updated_first(database: Neo4jDatabase) -> None:
    """``list_sessions`` orders newest-``updated_at`` first."""

    async def _run() -> None:
        chat_repo = ChatRepository(database)
        user_id = _fresh_user_id("session-order")
        series_id = SERIES_ID

        first = await chat_repo.create_session(user_id, series_id, "First")
        second = await chat_repo.create_session(user_id, series_id, "Second")

        sessions = await chat_repo.list_sessions(user_id, series_id)
        assert [s.id for s in sessions] == [second.id, first.id]

    asyncio.run(_run())
