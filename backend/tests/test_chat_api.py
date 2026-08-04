"""Integration tests for the chat API vertical slice (RAG-04..RAG-10).

Runs against the live local Neo4j instance. The LLM is always the deterministic
FakeLLMProvider (zero network); provider failure and disabled-provider paths are
exercised explicitly and must map to HTTP 503, never 401/403.

All tests are synchronous TestClient calls (the working pattern in
test_graph_api.py): the app's async Neo4j driver is only ever touched inside
TestClient's portal loop.  In-memory repo awaits (FakeUserRepo.upsert,
InMemorySessionRepository.create) run via asyncio.run; progress persistence in
the auth helper goes through the real HTTP endpoint, so no driver call ever
crosses an event loop.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import deps
from backend.app.api.chat import router as chat_router
from backend.app.api.progress import router as progress_router
from backend.app.core.config import get_settings
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase
from backend.app.llm.provider import (
    FakeLLMProvider,
    LLMEvent,
    LLMProviderUnavailable,
    install_llm_error_handlers,
)
from backend.app.repository.session import InMemorySessionRepository
from backend.app.services.auth import AuthService
from backend.app.services.chat import ChatService, get_llm_provider

SERIES_ID = "series_dexter"
DEXTER = "dexter:character:dexter_morgan"
DEBRA = "dexter:character:debra_morgan"
CLAIM_DEBRA_FAMILY = "dexter:claim:s01e01:dexter_debra_family"
EVIDENCE_S01E01_01 = "dexter:evidence:s01e01:01"
SOURCE_S01E01 = "dexter:source:s01e01"
CLAIM_HARRY_FAMILY = "dexter:claim:s01e03:dexter_harry_family"
EVIDENCE_S01E03_02 = "dexter:evidence:s01e03:02"
SOURCE_S01E03 = "dexter:source:s01e03"


class FakeUserRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def upsert(
        self, google_sub: str, email: str, display_name: str, avatar_url: str
    ) -> dict[str, Any]:
        record = {
            "id": f"user:{uuid4()}",
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        self._store[google_sub] = record
        return dict(record)

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        for record in self._store.values():
            if record["id"] == user_id:
                return dict(record)
        return None


class TimeoutLLMProvider:
    """Simulates a provider that times out — infra failure, never auth."""

    async def stream_chat(self, **kwargs: Any) -> AsyncIterator[LLMEvent]:
        raise LLMProviderUnavailable("simulated provider timeout")
        yield  # pragma: no cover — unreachable; marks this as an async generator


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db

    # Clean up test-created chat/progress nodes so the seed-integrity audit
    # in test_graph_api.py stays green.  A FRESH driver + loop is required:
    # the app's driver connections are bound to TestClient's portal loop and
    # would crash if reused here (cross-loop 'NoneType' send).
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


@pytest.fixture
def fake_user_repo() -> FakeUserRepo:
    return FakeUserRepo()


@pytest.fixture
def session_repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


def _build_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    provider: Any | None = None,
) -> FastAPI:
    app = FastAPI()
    install_database_error_handlers(app)
    install_llm_error_handlers(app)
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo)

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    if provider is not None:
        app.dependency_overrides[get_llm_provider] = lambda: provider
    app.include_router(progress_router)
    app.include_router(chat_router)
    return app


@pytest.fixture
def chat_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> FastAPI:
    return _build_app(database, fake_user_repo, session_repo, provider=fake_provider)


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    return FakeLLMProvider(scripted_events=[])


@pytest.fixture
def client(chat_app: FastAPI) -> Iterator[TestClient]:
    # Context-managed TestClient keeps ONE portal loop alive for the whole
    # test — the app's async Neo4j driver is only ever used inside that loop
    # (test_graph_api.py pattern). Without `with`, starlette starts a fresh
    # per-request loop and pooled driver connections die with the first one.
    with TestClient(chat_app, raise_server_exceptions=False) as client:
        yield client


def _authed(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    progress: int | None = 1,
) -> dict[str, Any]:
    """Create a user, authenticate via session cookie, and persist progress.

    Progress is persisted through the real HTTP endpoint (TestClient's portal
    loop) so the app's driver is never touched from another event loop.
    """
    user = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="user@example.com",
            display_name="Test User",
            avatar_url="",
        )
    )
    raw_token = asyncio.run(session_repo.create(user["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)
    if progress is not None:
        response = client.post(
            f"/api/series/{SERIES_ID}/progress",
            json={"visible_until_order": progress},
        )
        assert response.status_code == 200, response.text
    return user


def _llm_settings_backup() -> str | None:
    """Read the live :AppSetting {key:'llm'} payload (or None when absent)."""

    async def _read() -> str | None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            rows = await clean.execute_query(
                "MATCH (s:AppSetting {key: $k}) RETURN s.value AS value", k="llm"
            )
            return rows[0]["value"] if rows and rows[0].get("value") else None
        finally:
            await clean.close()

    return asyncio.run(_read())


def _llm_settings_clear() -> None:
    async def _clear() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query(
                "MATCH (s:AppSetting {key: $k}) DETACH DELETE s", k="llm"
            )
        finally:
            await clean.close()

    asyncio.run(_clear())


def _llm_settings_restore(backup: str | None) -> None:
    async def _restore() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            if backup is None:
                await clean.execute_query(
                    "MATCH (s:AppSetting {key: $k}) DETACH DELETE s", k="llm"
                )
            else:
                await clean.execute_query(
                    "MERGE (s:AppSetting {key: $k}) SET s.value = $v", k="llm", v=backup
                )
        finally:
            await clean.close()

    asyncio.run(_restore())


def _create_session(client: TestClient, title: str = "Test session") -> dict[str, Any]:
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions", json={"title": title}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _parse_sse(text: str) -> list[tuple[str | None, dict[str, Any]]]:
    events: list[tuple[str | None, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type: str | None = None
        data_parts: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data_parts.append(line[len("data: "):])
        if data_parts:
            events.append((event_type, json.loads("\n".join(data_parts))))
    return events


def _neighborhood_scripted_events(
    entity_id: str = DEXTER,
    content: str = "Dexter and Debra are siblings.",
    citations: list[dict[str, Any]] | None = None,
) -> list[LLMEvent]:
    return [
        LLMEvent.tool_call("get_neighborhood", {"entity_id": entity_id, "depth": 1}),
        LLMEvent.done(content, citations=citations or []),
    ]


# ---------------------------------------------------------------------------
# Auth and ownership
# ---------------------------------------------------------------------------


def test_chat_requires_authentication(client: TestClient) -> None:
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions", json={"title": "x"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_UNAUTHENTICATED"


def test_cross_user_session_is_generic_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    user_a = _authed(client, fake_user_repo, session_repo)
    session = _create_session(client)

    other = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="other@example.com",
            display_name="Other",
            avatar_url="",
        )
    )
    raw_token = asyncio.run(session_repo.create(other["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)

    response = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "resource_not_found"
    assert user_a["id"] != other["id"]


# ---------------------------------------------------------------------------
# Test 1 (plan): grounded streamed answer with citation validation + graph focus
# ---------------------------------------------------------------------------


def test_streaming_answer_citations_validated_against_this_turn_context(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    fake_provider.scripted_events = _neighborhood_scripted_events(
        citations=[
            # Real IDs returned by this turn's get_neighborhood call.
            {
                "claim_id": CLAIM_DEBRA_FAMILY,
                "evidence_id": EVIDENCE_S01E01_01,
                "source_id": SOURCE_S01E01,
            },
            # Hallucinated citation — never retrieved this turn, must be stripped.
            {"claim_id": "claim:never-retrieved", "evidence_id": "evidence:never-retrieved"},
        ]
    )

    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    done_events = [payload for kind, payload in events if kind == "done"]
    assert len(done_events) == 1
    envelope = done_events[0]

    # Envelope field names match the public contract exactly.
    assert set(envelope) == {"message", "citations", "graph_focus", "proposed_change_set"}
    assert envelope["proposed_change_set"] is None
    assert envelope["message"]["content"] == "Dexter and Debra are siblings."
    assert envelope["message"]["visible_until_order_snapshot"] == 1

    # The hallucinated citation is gone; the grounded one survives with full data.
    citations = envelope["citations"]
    assert len(citations) == 1
    citation = citations[0]
    assert citation["claim_id"] == CLAIM_DEBRA_FAMILY
    assert citation["evidence_id"] == EVIDENCE_S01E01_01
    assert citation["source_id"] == SOURCE_S01E01
    assert citation["source_label"]
    assert citation["episode_code"] == "S01E01"
    assert citation["excerpt"]

    # graph_focus covers Dexter and the visible neighbor(s) from this turn.
    assert DEXTER in envelope["graph_focus"]["node_ids"]
    assert DEBRA in envelope["graph_focus"]["node_ids"]

    # The assistant message was persisted with the exact boundary snapshot used.
    detail = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [m["content"] for m in messages] == [
        "Who is Dexter related to?",
        "Dexter and Debra are siblings.",
    ]
    assert all(m["visible_until_order_snapshot"] == 1 for m in messages)


# ---------------------------------------------------------------------------
# Test 2 (plan): lowering progress hides the claim → citation disappears
# ---------------------------------------------------------------------------


def test_lowering_progress_removes_citations_to_now_hidden_claims(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=3)
    session = _create_session(client)

    def _script() -> None:
        fake_provider.scripted_events = _neighborhood_scripted_events(
            citations=[
                {
                    "claim_id": CLAIM_HARRY_FAMILY,
                    "evidence_id": EVIDENCE_S01E03_02,
                    "source_id": SOURCE_S01E03,
                }
            ]
        )

    # Boundary 3: the order-3 claim is retrieved and cited.
    _script()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
        json={"question": "Who is Dexter related to?"},
    )
    envelope = [p for kind, p in _parse_sse(response.text) if kind == "done"][0]
    assert len(envelope["citations"]) == 1
    assert envelope["citations"][0]["claim_id"] == CLAIM_HARRY_FAMILY

    # Lower progress below the boundary that made the claim visible.
    lowered = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": 1}
    )
    assert lowered.status_code == 200

    # Same question again: the tool no longer returns the claim, so the final
    # answer carries no citation to it.
    _script()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
        json={"question": "Who is Dexter related to?"},
    )
    envelope = [p for kind, p in _parse_sse(response.text) if kind == "done"][0]
    assert envelope["citations"] == []
    assert envelope["graph_focus"]["node_ids"] == []

    # The boundary-3 answer is hidden from history (not deleted): reopening the
    # session at boundary 1 must not leak the Episode-3 answer.
    detail = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    visible_contents = [m["content"] for m in messages]
    assert "Dexter and Debra are siblings." not in visible_contents
    assert all(m["visible_until_order_snapshot"] == 1 for m in messages)


# ---------------------------------------------------------------------------
# Test 3 (plan): LLM_ENABLED=false → 503 with distinct disabled-provider code
# ---------------------------------------------------------------------------


def test_disabled_provider_returns_503_never_401(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_ENABLED", "false")
    get_settings.cache_clear()
    # Isolate from any stored LLM settings: a user-configured :AppSetting
    # node (key + enabled:true) legitimately overrides the env flag, so the
    # test must back up, clear, and restore it — never assume an empty DB
    # (this suite runs against the shared live Neo4j).
    backup = _llm_settings_backup()
    _llm_settings_clear()
    try:
        app = _build_app(database, fake_user_repo, session_repo, provider=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            user = _authed(client, fake_user_repo, session_repo, progress=1)
            session = _create_session(client)

            response = client.post(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
                json={"question": "Who is Dexter related to?"},
            )
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "LLM_DISABLED"
            assert user["id"]
    finally:
        _llm_settings_restore(backup)
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Test 4 (plan): provider timeout → 503, never 401/403
# ---------------------------------------------------------------------------


def test_provider_timeout_returns_503_never_401(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    app = _build_app(database, fake_user_repo, session_repo, provider=TimeoutLLMProvider())
    with TestClient(app, raise_server_exceptions=False) as client:
        _authed(client, fake_user_repo, session_repo, progress=1)
        session = _create_session(client)

        response = client.post(
            f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
            json={"question": "Who is Dexter related to?"},
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "LLM_PROVIDER_UNAVAILABLE"


def test_stream_provider_failure_emits_error_event_never_silent_close(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    """A provider failure mid-stream must arrive as a structured
    ``event: error`` chunk — never a silent connection close that leaves the
    client's streaming state (Stop button) stuck forever."""
    app = _build_app(database, fake_user_repo, session_repo, provider=TimeoutLLMProvider())
    with TestClient(app, raise_server_exceptions=False) as client:
        _authed(client, fake_user_repo, session_repo, progress=1)
        session = _create_session(client)

        response = client.post(
            f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
            json={"question": "Who is Dexter related to?"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        errors = [
            payload
            for kind, payload in _parse_sse(response.text)
            if kind == "error"
        ]
        assert errors, "expected an event: error chunk, got a silent close"
        assert errors[0]["code"] == "LLM_PROVIDER_UNAVAILABLE"
        assert "done" not in [kind for kind, _ in _parse_sse(response.text)]


# ---------------------------------------------------------------------------
# Test 5 (plan): zero-message session returns an empty list, never an error
# ---------------------------------------------------------------------------


def test_zero_message_session_returns_empty_messages(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    detail = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["session"]["id"] == session["id"]
    assert body["session"]["series_id"] == SERIES_ID
    assert body["messages"] == []


# ---------------------------------------------------------------------------
# Session CRUD and non-streaming message path
# ---------------------------------------------------------------------------


def test_session_list_is_user_scoped(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    first = _create_session(client, title="First")
    second = _create_session(client, title="Second")

    response = client.get(f"/api/series/{SERIES_ID}/chat/sessions")
    assert response.status_code == 200
    titles = {s["title"] for s in response.json()}
    assert titles == {"First", "Second"}
    assert first["id"] != second["id"]


def test_empty_title_creates_session_with_default_title(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    """An empty/whitespace title must not 422 — the backend relaxes the
    request model and normalizes to the default 'New conversation' label
    (the frontend's default payload shape)."""
    _authed(client, fake_user_repo, session_repo, progress=1)

    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions", json={"title": ""}
    )
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "New conversation"

    # A whitespace-only title is stripped to empty, then normalized the same.
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions", json={"title": "   "}
    )
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "New conversation"


def test_non_streaming_message_returns_envelope(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)
    fake_provider.scripted_events = _neighborhood_scripted_events()

    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert set(envelope) == {"message", "citations", "graph_focus", "proposed_change_set"}
    assert envelope["message"]["content"] == "Dexter and Debra are siblings."


def test_message_without_progress_auto_creates_order_1_progress(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """No persisted progress must not block sending — the chat path
    auto-creates the row at ``visible_until_order=1`` (the app's implied
    default state, the graph already loads order 1) instead of failing
    closed with a generic 404 (RAG-01)."""
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    # Wipe the just-created progress row so the session exists but the user
    # has no persisted boundary — the scenario that used to 404.
    reset = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": 1}
    )
    assert reset.status_code == 200
    from backend.app.graph.database import Neo4jDatabase as _Neo4jDatabase

    async def _delete_progress() -> None:
        db = _Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                "MATCH (p:UserSeriesProgress {series_id: $sid}) DETACH DELETE p",
                sid=SERIES_ID,
            )
        finally:
            await db.close()

    asyncio.run(_delete_progress())

    fake_provider.scripted_events = _neighborhood_scripted_events()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["message"]["content"] == "Dexter and Debra are siblings."

    # The chat path auto-created the missing progress row at order 1.
    progress = client.get(f"/api/series/{SERIES_ID}/progress")
    assert progress.status_code == 200
    assert progress.json()["visible_until_order"] == 1


def test_stream_message_without_progress_auto_creates_order_1_progress(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """Missing progress is resolved-or-created before the SSE stream opens —
    the pre-check auto-creates the order-1 row, so the stream starts cleanly
    and delivers a done envelope (never a 404, never a broken stream)."""
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    from backend.app.graph.database import Neo4jDatabase as _Neo4jDatabase

    async def _delete_progress() -> None:
        db = _Neo4jDatabase()
        db.open()
        try:
            await db.execute_query(
                "MATCH (p:UserSeriesProgress {series_id: $sid}) DETACH DELETE p",
                sid=SERIES_ID,
            )
        finally:
            await db.close()

    asyncio.run(_delete_progress())

    fake_provider.scripted_events = _neighborhood_scripted_events()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    done_events = [
        payload for kind, payload in _parse_sse(response.text) if kind == "done"
    ]
    assert len(done_events) == 1
    assert done_events[0]["message"]["visible_until_order_snapshot"] == 1

    # The chat path auto-created the missing progress row at order 1.
    progress = client.get(f"/api/series/{SERIES_ID}/progress")
    assert progress.status_code == 200
    assert progress.json()["visible_until_order"] == 1


def test_unknown_session_is_generic_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/chat-session:nope/messages",
        json={"question": "hello"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "resource_not_found"


def test_zero_sessions_returns_empty_list_not_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    response = client.get(f"/api/series/{SERIES_ID}/chat/sessions")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# DELETE session (Task 2, RAG-10) — ownership, cross-series, and generic 404s
# ---------------------------------------------------------------------------


def test_delete_session_requires_authentication(client: TestClient) -> None:
    response = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/chat-session:nope")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_UNAUTHENTICATED"


def test_delete_session_removes_it_and_its_messages_from_subsequent_get(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)
    fake_provider.scripted_events = _neighborhood_scripted_events()
    posted = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Who is Dexter related to?"},
    )
    assert posted.status_code == 200, posted.text

    response = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert response.status_code == 204
    assert response.content == b""

    after = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert after.status_code == 404
    assert after.json()["detail"]["code"] == "resource_not_found"


def test_delete_session_cross_user_and_nonexistent_return_identical_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    other = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="other@example.com",
            display_name="Other",
            avatar_url="",
        )
    )
    raw_token = asyncio.run(session_repo.create(other["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)

    cross_user = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    nonexistent = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/chat-session:nope")

    assert cross_user.status_code == nonexistent.status_code == 404
    assert cross_user.json() == nonexistent.json()
    assert cross_user.json()["detail"]["code"] == "resource_not_found"


def test_delete_session_cross_series_is_generic_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    response = client.delete(
        f"/api/series/series_other_show/chat/sessions/{session['id']}"
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "resource_not_found"


def test_delete_session_retried_twice_returns_204_then_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    """Retrying a DELETE twice returns the same terminal result both times —
    204 then 404, never a duplicate side effect."""
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    first = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    second = client.delete(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")

    assert first.status_code == 204
    assert second.status_code == 404
    assert second.json()["detail"]["code"] == "resource_not_found"


# ---------------------------------------------------------------------------
# Bounded concurrent generations (Task 2, T-06-13)
# ---------------------------------------------------------------------------


def test_concurrent_generation_for_same_user_is_rejected_with_clear_error(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
    chat_app: FastAPI,
) -> None:
    """A second concurrent POST .../messages for the same user while one is
    already in-flight is rejected with a clear, non-500 error — never
    silently queued or dropped."""
    user = _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)
    fake_provider.scripted_events = _neighborhood_scripted_events()

    service = ChatService(chat_app.state.neo4j)
    service.acquire_generation_slot(user["id"])
    try:
        response = client.post(
            f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
            json={"question": "Who is Dexter related to?"},
        )
        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "too_many_requests"
    finally:
        service.release_generation_slot(user["id"])

    # After releasing, a normal request for the same user succeeds again.
    fake_provider.scripted_events = _neighborhood_scripted_events()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text


def test_concurrent_generation_does_not_block_a_different_user(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
    chat_app: FastAPI,
) -> None:
    other_user_id = f"user:{uuid4()}"
    service = ChatService(chat_app.state.neo4j)
    service.acquire_generation_slot(other_user_id)
    try:
        _authed(client, fake_user_repo, session_repo, progress=1)
        session = _create_session(client)
        fake_provider.scripted_events = _neighborhood_scripted_events()

        response = client.post(
            f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
            json={"question": "Who is Dexter related to?"},
        )
        assert response.status_code == 200, response.text
    finally:
        service.release_generation_slot(other_user_id)


def test_answer_stream_releases_generation_slot_on_client_disconnect(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """Starlette calls ``aclose()`` on the SSE body generator when a client
    disconnects mid-stream — the concurrency slot must release exactly the
    same way it does on normal completion, never leaking (T-06-13)."""
    user = _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)
    fake_provider.scripted_events = _neighborhood_scripted_events()

    from backend.app.graph.database import Neo4jDatabase as _Neo4jDatabase

    async def _simulate_disconnect() -> None:
        db = _Neo4jDatabase()
        db.open()
        try:
            service = ChatService(db)
            generator = service.answer_stream(
                user_id=user["id"],
                series_id=SERIES_ID,
                chat_session_id=session["id"],
                question="Who is Dexter related to?",
                provider=fake_provider,
            )
            await generator.__anext__()  # start the generation (slot acquired)
            await generator.aclose()  # Starlette's client-disconnect path
        finally:
            await db.close()

    asyncio.run(_simulate_disconnect())

    # If the slot had leaked, this second generation for the same user would
    # be rejected instead of succeeding.
    fake_provider.scripted_events = _neighborhood_scripted_events()
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Who is Dexter related to?"},
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Turkish-language bounded length + count-leakage (Task 3)
# ---------------------------------------------------------------------------


def test_turkish_question_length_bound_counts_unicode_code_points_not_bytes(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """The 4000-character question bound is enforced with Python ``len()``
    (Unicode code points) — Turkish text is accepted right up to the limit
    and rejected exactly one code point over, never truncated mid-character."""
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)
    fake_provider.scripted_events = _neighborhood_scripted_events()

    turkish_chars = "İıŞşĞğÇçÖöÜü"
    at_limit = (turkish_chars * ((4000 // len(turkish_chars)) + 1))[:4000]
    assert len(at_limit) == 4000
    # Every character here is multi-byte in UTF-8 but a single Unicode code
    # point — the byte length exceeds the code-point length, proving the
    # bound is code-point-based, not byte-based.
    assert len(at_limit.encode("utf-8")) > len(at_limit)

    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": at_limit},
    )
    assert response.status_code == 200, response.text

    over_limit = at_limit + "x"
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": over_limit},
    )
    assert response.status_code == 422


def test_session_message_count_never_leaks_hidden_message_count(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """Comparing a visible-only count against the true persisted total
    (including hidden messages) must show they differ — proving the exposed
    count is always boundary-scoped, never the raw total (RAG-09/RAG-13)."""
    _authed(client, fake_user_repo, session_repo, progress=3)
    session = _create_session(client)

    fake_provider.scripted_events = _neighborhood_scripted_events()
    first = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "q1"},
    )
    assert first.status_code == 200, first.text
    fake_provider.scripted_events = _neighborhood_scripted_events()
    second = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "q2"},
    )
    assert second.status_code == 200, second.text

    # Lower progress: the 4 messages just persisted become hidden.
    lowered = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": 1}
    )
    assert lowered.status_code == 200

    # One new visible turn at the lowered boundary.
    fake_provider.scripted_events = _neighborhood_scripted_events()
    third = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "q3"},
    )
    assert third.status_code == 200, third.text

    detail = client.get(f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}")
    assert detail.status_code == 200
    visible_count = len(detail.json()["messages"])
    assert visible_count == 2  # only the boundary-1 turn is visible

    from backend.app.graph.database import Neo4jDatabase as _Neo4jDatabase

    async def _true_total() -> int:
        db = _Neo4jDatabase()
        db.open()
        try:
            rows = await db.execute_query(
                "MATCH (:ChatSession {id: $sid})-[:HAS_MESSAGE]->(m:ChatMessage) "
                "RETURN count(m) AS total",
                sid=session["id"],
            )
            return rows[0]["total"]
        finally:
            await db.close()

    true_total = asyncio.run(_true_total())
    assert true_total == 6
    assert visible_count != true_total


# ---------------------------------------------------------------------------
# BYOK (bring-your-own-key) — request-scoped provider from X-LLM-* headers
# (08-02, D-04..D-08). The real get_llm_provider dependency runs (no
# dependency override); OpenAICompatibleProvider is monkeypatched so tests
# capture exactly what the dependency would construct while the pipeline
# still streams deterministically with zero network.
# ---------------------------------------------------------------------------

BYOK_API_KEY = "sk-byok-secret-1234"
BYOK_BASE_URL = "https://byok.example/v1"
BYOK_MODEL = "byok-model-7"
STORED_API_KEY = "sk-stored-secret-9999"
STORED_BASE_URL = "https://stored.example/v1"
STORED_MODEL = "stored-model-1"
ENV_API_KEY = "sk-env-secret-5555"
ENV_BASE_URL = "https://env.example/v1"
ENV_MODEL = "env-model-2"


def _llm_settings_write(payload: dict[str, Any]) -> None:
    """Persist an :AppSetting {key:'llm'} payload (test-created row)."""

    async def _write() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query(
                "MERGE (s:AppSetting {key: $k}) SET s.value = $v",
                k="llm",
                v=json.dumps(payload),
            )
        finally:
            await clean.close()

    asyncio.run(_write())


class CapturingBYOKProvider:
    """Records the constructor kwargs get_llm_provider passes to
    OpenAICompatibleProvider, then behaves like FakeLLMProvider (scripted
    events, recorded ``.calls``) so the pipeline runs end-to-end.

    The header-supplied API key must appear ONLY in the constructor kwargs —
    never in ``.calls``, a response, or a persisted record (T-08-02-01/02).
    """

    scripted_events: list[LLMEvent] = []
    constructed: list[dict[str, Any]] = []
    instances: list["CapturingBYOKProvider"] = []

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: Any = None,
    ) -> None:
        CapturingBYOKProvider.constructed.append(
            {"base_url": base_url, "api_key": api_key, "model": model}
        )
        self.scripted_events: list[LLMEvent] = list(type(self).scripted_events)
        self.calls: list[dict[str, Any]] = []
        CapturingBYOKProvider.instances.append(self)

    async def stream_chat(self, **kwargs: Any) -> AsyncIterator[LLMEvent]:
        self.calls.append(kwargs)
        for event in self.scripted_events:
            yield event


@pytest.fixture(autouse=True)
def _reset_byok_capture() -> None:
    CapturingBYOKProvider.scripted_events = _neighborhood_scripted_events()
    CapturingBYOKProvider.constructed = []
    CapturingBYOKProvider.instances = []


def _build_byok_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    """App with the REAL get_llm_provider dependency and a capturing
    OpenAICompatibleProvider (no network, no dependency override)."""
    monkeypatch.setattr(
        "backend.app.services.chat.OpenAICompatibleProvider",
        CapturingBYOKProvider,
    )
    return _build_app(database, fake_user_repo, session_repo, provider=None)


def _byok_headers() -> dict[str, str]:
    return {
        "X-LLM-Api-Key": BYOK_API_KEY,
        "X-LLM-Base-URL": BYOK_BASE_URL,
        "X-LLM-Model": BYOK_MODEL,
    }


def test_byok_headers_build_provider_from_headers_bypassing_stored_and_env(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """X-LLM-* headers win over BOTH the stored settings and the
    LLM_ENABLED env switch: the provider is built purely from the header
    values (D-06), and the stored key never reaches the constructor. The
    header key never appears in the response, the provider's recorded
    ``.calls``, or the persisted message row."""
    backup = _llm_settings_backup()
    _llm_settings_clear()
    try:
        # Stored settings say DISABLED with a different key — the BYOK path
        # must ignore them entirely.
        _llm_settings_write(
            {
                "provider": "openai_compatible",
                "api_key": STORED_API_KEY,
                "base_url": STORED_BASE_URL,
                "model": STORED_MODEL,
                "enabled": False,
                "system_prompt_language": "english",
            }
        )
        monkeypatch.setenv("LLM_ENABLED", "false")
        get_settings.cache_clear()

        app = _build_byok_app(database, fake_user_repo, session_repo, monkeypatch)
        with TestClient(app, raise_server_exceptions=False) as client:
            _authed(client, fake_user_repo, session_repo, progress=1)
            session = _create_session(client)

            response = client.post(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
                json={"question": "Who is Dexter related to?"},
                headers=_byok_headers(),
            )
            assert response.status_code == 200, response.text
            envelope = response.json()
            assert envelope["message"]["content"] == "Dexter and Debra are siblings."

            # Built from exactly the header values — nothing else.
            assert CapturingBYOKProvider.constructed == [
                {
                    "base_url": BYOK_BASE_URL,
                    "api_key": BYOK_API_KEY,
                    "model": BYOK_MODEL,
                }
            ]
            # The stored key never reached the constructor.
            assert STORED_API_KEY not in json.dumps(CapturingBYOKProvider.constructed)
            # The header key never appears in the response, the recorded
            # provider calls, or the persisted message row.
            assert BYOK_API_KEY not in response.text
            assert BYOK_API_KEY not in json.dumps(
                CapturingBYOKProvider.instances[-1].calls
            )
            detail = client.get(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}"
            )
            assert detail.status_code == 200
            assert BYOK_API_KEY not in detail.text
    finally:
        _llm_settings_restore(backup)
        get_settings.cache_clear()


def test_byok_headers_stream_endpoint_builds_provider_and_never_leaks_key(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SSE streaming endpoint uses the same request-scoped BYOK
    construction; the key never appears in the stream text or the persisted
    assistant message."""
    backup = _llm_settings_backup()
    _llm_settings_clear()
    try:
        app = _build_byok_app(database, fake_user_repo, session_repo, monkeypatch)
        with TestClient(app, raise_server_exceptions=False) as client:
            _authed(client, fake_user_repo, session_repo, progress=1)
            session = _create_session(client)

            response = client.post(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages/stream",
                json={"question": "Who is Dexter related to?"},
                headers=_byok_headers(),
            )
            assert response.status_code == 200, response.text
            done_events = [
                payload
                for kind, payload in _parse_sse(response.text)
                if kind == "done"
            ]
            assert len(done_events) == 1
            assert done_events[0]["message"]["content"] == "Dexter and Debra are siblings."

            assert CapturingBYOKProvider.constructed[-1]["api_key"] == BYOK_API_KEY
            assert BYOK_API_KEY not in response.text
            detail = client.get(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}"
            )
            assert detail.status_code == 200
            assert BYOK_API_KEY not in detail.text
    finally:
        _llm_settings_restore(backup)


def test_malformed_byok_base_url_scheme_is_rejected_like_stored_settings(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed BYOK base_url (non-http(s) scheme) fails the same way a
    malformed stored one does — HTTP 422 via the shared
    LLMSettingsUpdate._validate_base_url logic (T-08-02-03) — and the key is
    never echoed in the error body."""
    backup = _llm_settings_backup()
    _llm_settings_clear()
    try:
        app = _build_byok_app(database, fake_user_repo, session_repo, monkeypatch)
        with TestClient(app, raise_server_exceptions=False) as client:
            _authed(client, fake_user_repo, session_repo, progress=1)
            session = _create_session(client)

            response = client.post(
                f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
                json={"question": "Who is Dexter related to?"},
                headers={
                    "X-LLM-Api-Key": BYOK_API_KEY,
                    "X-LLM-Base-URL": "gopher://evil.example",
                    "X-LLM-Model": BYOK_MODEL,
                },
            )
            assert response.status_code == 422, response.text
            assert "base_url" in response.text.lower()
            assert BYOK_API_KEY not in response.text
    finally:
        _llm_settings_restore(backup)
