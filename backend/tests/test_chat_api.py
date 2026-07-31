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
from backend.app.services.chat import get_llm_provider

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


def test_message_without_progress_returns_generic_404(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """No persisted progress must fail closed to the generic 404 — never a
    raw 500 (RAG-01)."""
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_session(client)

    # Wipe the just-created progress row so the session exists but the user
    # has no persisted boundary — the scenario this endpoint must fail closed
    # for (distinct from "session not found").
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
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "resource_not_found"


def test_stream_message_without_progress_returns_404_not_a_broken_stream(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> None:
    """Missing progress must be caught before the SSE stream opens — once
    headers are sent an in-stream exception cannot become a clean 404."""
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
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "resource_not_found"


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
