"""Tests for ChangeSet Stage 2 idempotency, staleness, and reject (RAG-12, RAG-14).

Task 2 exercises three invariants beyond Task 1's core transactional apply:

- Replaying ``confirm`` on an already-``applied`` ChangeSet is a safe no-op
  (no second mutation, no second Revision) — the natural consequence of the
  status check in ``ChangeSetRepository._apply_change_set`` (idempotency-key
  replay protection, RAG-12).
- A ChangeSet whose ``visible_until_order_snapshot`` now exceeds the current
  (since-lowered) progress is rejected as stale rather than silently applied
  (RAG-14) — and the ChangeSet is marked ``failed``, not left retriable.
- ``reject`` makes zero graph mutation and permanently forecloses a later
  ``confirm`` on the same ChangeSet; a chat message alone never moves a
  ChangeSet out of ``awaiting_confirmation`` (the two-stage design itself is
  the guarantee — this is a regression test for that architectural
  invariant, not a new code path).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spoilerless.app.api import deps
from spoilerless.app.api.change_set import router as change_set_router
from spoilerless.app.api.chat import router as chat_router
from spoilerless.app.api.progress import router as progress_router
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.llm.provider import FakeLLMProvider, LLMEvent, install_llm_error_handlers
from spoilerless.app.repository.session import InMemorySessionRepository

from conftest import module_cleanup_fixture, run_query  # noqa: E402
from spoilerless.app.services.auth import AuthService
from spoilerless.app.services.chat import get_llm_provider

SERIES_ID = "series_dexter"
EPISODE_1 = "dexter_s01e01"

from spoilerless.tests.conftest import NoopGoogleVerifier


def _fresh_query(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* on the suite-shared helper driver (see conftest.run_query)."""
    return run_query(query, **params)



class FakeUserRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def upsert(
        self,
        google_sub: str,
        email: str,
        display_name: str,
        avatar_url: str,
        role: str = "user",
    ) -> dict[str, Any]:
        record = {
            "id": f"user:{uuid4()}",
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "role": role,
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


_CHANGE_SET_CLEANUP_QUERIES: list[tuple[str, dict] | str] = [
    "MATCH (n:Revision {resource_type: 'ChangeSet'}) DETACH DELETE n",
    "MATCH (n:ChangeSet) DETACH DELETE n",
    "MATCH (n:ChatSession) DETACH DELETE n",
    "MATCH (n:ChatMessage) DETACH DELETE n",
    "MATCH (n:UserSeriesProgress) DETACH DELETE n",
    (
        "MATCH (n:Location {series_id: $series_id}) "
        "WHERE NOT n.id STARTS WITH 'dexter:location:' DETACH DELETE n",
        {"series_id": SERIES_ID},
    ),
]


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db



_cleanup_after_module = module_cleanup_fixture(_CHANGE_SET_CLEANUP_QUERIES)
@pytest.fixture
def fake_user_repo() -> FakeUserRepo:
    return FakeUserRepo()


@pytest.fixture
def session_repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    return FakeLLMProvider(scripted_events=[LLMEvent.done("A grounded answer.")])


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
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo, verifier=NoopGoogleVerifier())

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    if provider is not None:
        app.dependency_overrides[get_llm_provider] = lambda: provider
    app.include_router(progress_router)
    app.include_router(chat_router)
    app.include_router(change_set_router)
    return app


@pytest.fixture
def change_set_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    fake_provider: FakeLLMProvider,
) -> FastAPI:
    return _build_app(database, fake_user_repo, session_repo, provider=fake_provider)


@pytest.fixture
def client(change_set_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(change_set_app, raise_server_exceptions=False) as client:
        yield client


def _authed(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    progress: int = 1,
    role: str = "user",
) -> dict[str, Any]:
    user = asyncio.run(
        fake_user_repo.upsert(
            google_sub=f"sub-{uuid4()}",
            email="user@example.com",
            display_name="Test User",
            avatar_url="",
            role=role,
        )
    )
    raw_token = asyncio.run(session_repo.create(user["id"], ttl_seconds=3600))
    client.cookies.set("session", raw_token)
    response = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": progress}
    )
    assert response.status_code == 200, response.text
    return user


def _set_progress(client: TestClient, progress: int) -> None:
    response = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": progress}
    )
    assert response.status_code == 200, response.text


def _create_chat_session(client: TestClient, title: str = "Confirmation session") -> dict[str, Any]:
    response = client.post(f"/api/series/{SERIES_ID}/chat/sessions", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


def _create_node_op(**overrides: Any) -> dict[str, Any]:
    op = {
        "operation_type": "create_node",
        "node_type": "Location",
        "label": f"Confirmation stage test {uuid4()}",
        "episode_id": EPISODE_1,
    }
    op.update(overrides)
    return op


def _propose(
    client: TestClient, session_id: str, operations: list[dict[str, Any]], summary: str = "Test change"
) -> Any:
    return client.post(
        f"/api/series/{SERIES_ID}/change-sets",
        json={
            "series_id": SERIES_ID,
            "chat_session_id": session_id,
            "summary": summary,
            "operations": operations,
        },
    )


def _confirm(client: TestClient, change_set_id: str) -> Any:
    return client.post(f"/api/series/{SERIES_ID}/change-sets/{change_set_id}/confirm")


def _reject(client: TestClient, change_set_id: str) -> Any:
    return client.post(f"/api/series/{SERIES_ID}/change-sets/{change_set_id}/reject")


def _location_count(label: str) -> int:
    rows = _fresh_query(
        "MATCH (n:Location {series_id: $series_id, label: $label}) RETURN count(n) AS c",
        series_id=SERIES_ID,
        label=label,
    )
    return rows[0]["c"]


def _revision_count_for_change_set(change_set_id: str) -> int:
    rows = _fresh_query(
        "MATCH (r:Revision {resource_type: 'ChangeSet', resource_id: $id}) RETURN count(r) AS c",
        id=change_set_id,
    )
    return rows[0]["c"]


def _change_set_status(change_set_id: str) -> str | None:
    rows = _fresh_query(
        "MATCH (cs:ChangeSet {id: $id}) RETURN cs.status AS status", id=change_set_id
    )
    return rows[0]["status"] if rows else None


# ---------------------------------------------------------------------------
# Idempotency-key replay protection (RAG-12)
# ---------------------------------------------------------------------------


def test_confirming_an_already_applied_change_set_is_a_safe_idempotent_replay(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1, role="admin")
    session = _create_chat_session(client)
    label = f"Idempotent replay {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]

    first = _confirm(client, change_set_id)
    assert first.status_code == 200, first.text
    second = _confirm(client, change_set_id)
    assert second.status_code == 200, second.text

    assert first.json()["revision_id"] == second.json()["revision_id"]
    assert first.json()["applied_at"] == second.json()["applied_at"]

    # Exactly one Location node was created (not two), and exactly one
    # Revision was logged (not two) — the replay is a true no-op.
    assert _location_count(label) == 1
    assert _revision_count_for_change_set(change_set_id) == 1


# ---------------------------------------------------------------------------
# Staleness rejection on lowered progress (RAG-14)
# ---------------------------------------------------------------------------


def test_confirm_rejects_stale_change_set_after_progress_is_lowered(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=3, role="admin")
    session = _create_chat_session(client)
    label = f"Stale after lowered progress {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    assert proposed.status_code == 201, proposed.text
    assert proposed.json()["visible_until_order_snapshot"] == 3
    change_set_id = proposed.json()["id"]

    # Progress drops back to 1 after the ChangeSet was proposed at 3.
    _set_progress(client, 1)

    response = _confirm(client, change_set_id)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "CHANGESET_STALE"

    # Nothing was applied — the target resource never came into existence.
    assert _location_count(label) == 0
    assert _revision_count_for_change_set(change_set_id) == 0
    assert _change_set_status(change_set_id) == "failed"


def test_confirm_succeeds_when_progress_is_unchanged_since_propose(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=3, role="admin")
    session = _create_chat_session(client)
    label = f"Unchanged progress succeeds {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "applied"
    assert _location_count(label) == 1


# ---------------------------------------------------------------------------
# Reject — zero mutation, forecloses a later confirm (RAG-14)
# ---------------------------------------------------------------------------


def test_reject_makes_no_mutation_and_a_subsequent_confirm_fails(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1, role="admin")
    session = _create_chat_session(client)
    label = f"Rejected, never applied {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]

    rejected = _reject(client, change_set_id)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert _location_count(label) == 0

    confirm_after_reject = _confirm(client, change_set_id)
    assert confirm_after_reject.status_code == 409, confirm_after_reject.text
    assert _location_count(label) == 0


def test_confirm_and_reject_are_generic_404_for_unowned_or_missing_change_set(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1, role="admin")

    missing_confirm = _confirm(client, "change-set:does-not-exist")
    missing_reject = _reject(client, "change-set:does-not-exist")

    assert missing_confirm.status_code == 404
    assert missing_reject.status_code == 404


# ---------------------------------------------------------------------------
# Admin gating of confirm (AUTH-03, T-08-03-02) — only the confirm/apply
# action is gated; propose/reject/revert stay reachable by any authenticated
# user per the plan's scoped reading of AUTH-03.
# ---------------------------------------------------------------------------


def test_confirm_requires_admin_role_403_for_non_admin(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1, role="user")
    session = _create_chat_session(client)

    proposed = _propose(client, session["id"], [_create_node_op()])
    assert proposed.status_code == 201, proposed.text
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "FORBIDDEN"

    # The gate rejected the request before any mutation — the ChangeSet is
    # exactly where propose left it, and reject remains reachable for the
    # same non-admin user.
    assert _change_set_status(change_set_id) == "awaiting_confirmation"
    rejected = _reject(client, change_set_id)
    assert rejected.status_code == 200, rejected.text


# ---------------------------------------------------------------------------
# A chat message alone never confirms a ChangeSet (RAG-14 architectural
# invariant) — regression test, not a new code path: ChatService never
# references ChangeSetService at all.
# ---------------------------------------------------------------------------


def test_posting_a_chat_message_alone_never_moves_a_change_set_past_awaiting_confirmation(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    # A destructive, single-operation ChangeSet — the highest-stakes case.
    proposed = _propose(
        client,
        session["id"],
        [_create_node_op()],
        summary="Destructive-shaped proposal for chat-message-alone regression test",
    )
    assert proposed.status_code == 201, proposed.text
    change_set_id = proposed.json()["id"]

    message_response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Please confirm and apply that change for me."},
    )
    assert message_response.status_code == 200, message_response.text

    # The chat message never applied anything — the ChangeSet is exactly
    # where propose left it, and only a dedicated confirm call can move it.
    assert _change_set_status(change_set_id) == "awaiting_confirmation"
