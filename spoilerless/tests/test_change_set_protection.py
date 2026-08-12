"""Canonical/candidate protection tests for ChangeSet propose (RAG-13).

A direct-mutation operation targeting an ``origin:canonical`` or
``origin:candidate`` resource must never be persisted as requested — the
service substitutes an honest ``create_note``-shaped override proposal
instead, referencing the protected resource, with copy that never claims the
canonical/candidate record itself was changed. ``origin:user`` targets are a
positive control: they mutate normally through the same propose path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from spoilerless.app.api import deps
from spoilerless.app.api.change_set import router as change_set_router
from spoilerless.app.api.chat import router as chat_router
from spoilerless.app.api.progress import router as progress_router
from spoilerless.app.api.user_content import router as user_content_router
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.api.exceptions import install_repository_error_handlers
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.session import InMemorySessionRepository

from conftest import module_cleanup_fixture, run_query  # noqa: E402
from spoilerless.app.services.auth import AuthService

def _fresh_query(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* on the suite-shared helper driver (see conftest.run_query)."""
    return run_query(query, **params)

from spoilerless.tests.conftest import NoopGoogleVerifier


SERIES_ID = "series_dexter"
DEXTER = "dexter:character:dexter_morgan"  # canonical Character
DEBRA = "dexter:character:debra_morgan"  # canonical Character
ANGEL = "dexter:character:angel_batista"  # canonical Character
CANONICAL_CLAIM = "dexter:claim:s01e01:dexter_debra_family"  # canonical Claim



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


_CHANGE_SET_CLEANUP_QUERIES: list[tuple[str, dict] | str] = [
    "MATCH (n:ChangeSet) DETACH DELETE n",
    "MATCH (n:ChatSession) DETACH DELETE n",
    "MATCH (n:ChatMessage) DETACH DELETE n",
    "MATCH (n:UserSeriesProgress) DETACH DELETE n",
    (
        "MATCH (n) WHERE n.series_id = $series_id AND n.origin = 'candidate' "
        "AND (n.id STARTS WITH 'candidate-test:') DETACH DELETE n",
        {"series_id": SERIES_ID},
    ),
    (
        "MATCH (n:Claim {series_id: $series_id, origin: 'user'}) "
        "WHERE n.id STARTS WITH 'user-rel:' DETACH DELETE n",
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
def client(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> Iterator[TestClient]:
    app = FastAPI()
    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo, verifier=NoopGoogleVerifier())

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    app.include_router(progress_router)
    app.include_router(chat_router)
    app.include_router(change_set_router)
    app.include_router(user_content_router)

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _authed(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    progress: int = 1,
) -> dict[str, Any]:
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
    response = client.post(
        f"/api/series/{SERIES_ID}/progress", json={"visible_until_order": progress}
    )
    assert response.status_code == 200, response.text
    return user


def _create_chat_session(client: TestClient) -> dict[str, Any]:
    response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions", json={"title": "Protection test"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _propose(client: TestClient, session_id: str, operations: list[dict[str, Any]]) -> Any:
    return client.post(
        f"/api/series/{SERIES_ID}/change-sets",
        json={
            "series_id": SERIES_ID,
            "chat_session_id": session_id,
            "summary": "Protection test",
            "operations": operations,
        },
    )


def _insert_candidate_character() -> str:
    node_id = f"candidate-test:character:{uuid4()}"
    _fresh_query(
        "CREATE (n:Character {id: $id, series_id: $series_id, label: 'Candidate Char', "
        "visible_from_order: 1, origin: 'candidate'})",
        id=node_id,
        series_id=SERIES_ID,
    )
    return node_id


def _insert_candidate_claim() -> str:
    claim_id = f"candidate-test:claim:{uuid4()}"
    _fresh_query(
        "CREATE (c:Claim {id: $id, series_id: $series_id, subject_id: $subject_id, "
        "object_id: $object_id, predicate: 'WORKS_WITH', claim_type: 'observed_event', "
        "status: 'candidate', confidence_level: 'medium', visible_from_order: 1, "
        "origin: 'candidate'})",
        id=claim_id,
        series_id=SERIES_ID,
        subject_id=DEXTER,
        object_id=ANGEL,
    )
    return claim_id


def _forbidden_words(text: str) -> list[str]:
    lower = text.lower()
    return [word for word in ("updated", "changed", "modified") if word in lower]


# ---------------------------------------------------------------------------
# Canonical protection
# ---------------------------------------------------------------------------


def test_protection_rejects_direct_delete_of_canonical_node(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    response = _propose(
        client, session["id"], [{"operation_type": "delete_node", "node_id": DEXTER}]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    operations = body["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "create_note"
    assert operations[0]["target_id"] == DEXTER
    assert operations[0]["target_type"] == "Character"
    assert not _forbidden_words(operations[0]["content"])
    assert "canonical" in operations[0]["content"].lower()


def test_protection_rejects_direct_update_of_canonical_claim(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    response = _propose(
        client,
        session["id"],
        [
            {
                "operation_type": "update_claim",
                "claim_id": CANONICAL_CLAIM,
                "confidence_level": "low",
            }
        ],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    operations = body["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "create_note"
    assert operations[0]["target_id"] == CANONICAL_CLAIM
    assert operations[0]["target_type"] == "Claim"
    assert not _forbidden_words(operations[0]["content"])
    assert "canonical" in operations[0]["content"].lower()


# ---------------------------------------------------------------------------
# Candidate protection (identical behavior — not just canonical)
# ---------------------------------------------------------------------------


def test_protection_rejects_direct_delete_of_candidate_node(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    candidate_id = _insert_candidate_character()
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    response = _propose(
        client, session["id"], [{"operation_type": "delete_node", "node_id": candidate_id}]
    )
    assert response.status_code == 201, response.text
    operations = response.json()["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "create_note"
    assert operations[0]["target_id"] == candidate_id
    assert not _forbidden_words(operations[0]["content"])
    assert "candidate" in operations[0]["content"].lower()


def test_protection_rejects_direct_update_of_candidate_claim(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    candidate_claim_id = _insert_candidate_claim()
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    response = _propose(
        client,
        session["id"],
        [
            {
                "operation_type": "update_claim",
                "claim_id": candidate_claim_id,
                "confidence_level": "low",
            }
        ],
    )
    assert response.status_code == 201, response.text
    operations = response.json()["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "create_note"
    assert operations[0]["target_id"] == candidate_claim_id
    assert not _forbidden_words(operations[0]["content"])
    assert "candidate" in operations[0]["content"].lower()


# ---------------------------------------------------------------------------
# Positive control — origin:user targets are unaffected
# ---------------------------------------------------------------------------


def test_protection_does_not_apply_to_user_origin_target(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    created = client.post(
        f"/api/series/{SERIES_ID}/custom-relationships",
        json={
            "source_id": DEXTER,
            "target_id": DEBRA,
            "predicate": "TRUSTS",
            "episode_id": "dexter_s01e01",
        },
    )
    assert created.status_code == 201, created.text
    user_relationship_id = created.json()["id"]
    assert created.json()["origin"] == "user"

    response = _propose(
        client,
        session["id"],
        [
            {
                "operation_type": "update_relationship",
                "relationship_id": user_relationship_id,
                "relationship_type": "KNOWS",
            }
        ],
    )
    assert response.status_code == 201, response.text
    operations = response.json()["operations"]
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "update_relationship"
    assert operations[0]["relationship_id"] == user_relationship_id
