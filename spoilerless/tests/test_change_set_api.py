"""Tests for the ChangeSet Stage 1 (Propose) vertical slice (RAG-11, RAG-13).

Task 1 tests exercise the domain-level discriminated union directly (no HTTP,
no database) — closed-field rejection and the empty-operations guard.

Task 2 tests exercise the full ``POST /api/series/{series_id}/change-sets``
integration path against the live local Neo4j instance: server-side
ontology/visibility/series validation, and the invariant that propose never
mutates a target resource.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from spoilerless.app.api import deps
from spoilerless.app.api.change_set import router as change_set_router
from spoilerless.app.api.chat import router as chat_router
from spoilerless.app.api.progress import router as progress_router
from spoilerless.app.core.errors import install_database_error_handlers
from spoilerless.app.domain.change_set import (
    ChangeSetCreateRequest,
    CreateRelationshipOperation,
)
from spoilerless.app.graph.database import Neo4jDatabase
from spoilerless.app.repository.session import InMemorySessionRepository
from spoilerless.app.services.auth import AuthService

from conftest import cleanup_with_fresh_driver, module_cleanup_fixture, run_query  # noqa: E402


def _fresh_query(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* on the suite-shared helper driver (see conftest.run_query).

    The app's async Neo4j driver connections are bound to ``TestClient``'s
    portal loop; reusing them from a bare ``asyncio.run()`` call crashes with
    a cross-loop error. The shared runner keeps one loop for all probes, so
    the suite pays one TLS handshake instead of one per probe.
    """
    return run_query(query, **params)


SERIES_ID = "series_dexter"
OTHER_SERIES_ID = "series_other_show"
DEXTER = "dexter:character:dexter_morgan"
DEBRA = "dexter:character:debra_morgan"
RUDY_COOPER = "dexter:character:rudy_cooper"  # visible_from_order=3, canonical
EPISODE_1 = "dexter_s01e01"
CROSS_SERIES_NODE = "other-series:character:ghost"


# ---------------------------------------------------------------------------
# Task 1 — domain-level discriminated union (no HTTP, no database)
# ---------------------------------------------------------------------------


def _valid_create_relationship_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "operation_type": "create_relationship",
        "source_id": DEXTER,
        "target_id": DEBRA,
        "relationship_type": "WORKS_WITH",
        "episode_id": EPISODE_1,
    }
    payload.update(overrides)
    return payload


def test_operation_model_forbids_origin_field() -> None:
    with pytest.raises(ValidationError):
        CreateRelationshipOperation(**_valid_create_relationship_payload(origin="user"))


def test_operation_model_forbids_visible_from_order_field() -> None:
    with pytest.raises(ValidationError):
        CreateRelationshipOperation(
            **_valid_create_relationship_payload(visible_from_order=1)
        )


def test_operation_model_forbids_id_field() -> None:
    with pytest.raises(ValidationError):
        CreateRelationshipOperation(
            **_valid_create_relationship_payload(id="change-set-op:forged")
        )


def test_discriminator_rejects_unknown_operation_type() -> None:
    with pytest.raises(ValidationError):
        ChangeSetCreateRequest(
            series_id=SERIES_ID,
            chat_session_id="chat-session:x",
            summary="test",
            operations=[
                {
                    "operation_type": "drop_database",
                    "source_id": DEXTER,
                    "target_id": DEBRA,
                }
            ],
        )


def test_operation_model_rejects_non_allowlisted_relationship_type() -> None:
    with pytest.raises(ValidationError):
        CreateRelationshipOperation(
            **_valid_create_relationship_payload(relationship_type="FRIEND_OF")
        )


def test_operation_model_requires_at_least_one_operation() -> None:
    with pytest.raises(ValidationError):
        ChangeSetCreateRequest(
            series_id=SERIES_ID,
            chat_session_id="chat-session:x",
            summary="test",
            operations=[],
        )


# ---------------------------------------------------------------------------
# Task 2 — POST /api/series/{series_id}/change-sets integration tests
# ---------------------------------------------------------------------------


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
    (
        "MATCH (n) WHERE n.id STARTS WITH 'user-node:' "
        "AND n.series_id = $series_id DETACH DELETE n",
        {"series_id": SERIES_ID},
    ),
    ("MATCH (n) WHERE n.id = $id DETACH DELETE n", {"id": CROSS_SERIES_NODE}),
]


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db



_cleanup_after_module = module_cleanup_fixture(_CHANGE_SET_CLEANUP_QUERIES)
@pytest.fixture(autouse=True)
def _cleanup_cross_series_node() -> Iterator[None]:
    """The cross-series ghost node has a FIXED id; the next test re-creating
    it would hit an index conflict (22N80), so it needs per-test cleanup —
    unlike the uuid-suffixed residue the module-scoped cleanup handles."""
    yield
    cleanup_with_fresh_driver(
        [("MATCH (n) WHERE n.id = $id DETACH DELETE n", {"id": CROSS_SERIES_NODE})]
    )


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
) -> FastAPI:
    app = FastAPI()
    install_database_error_handlers(app)
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo)

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    app.include_router(progress_router)
    app.include_router(chat_router)
    app.include_router(change_set_router)
    return app


@pytest.fixture
def change_set_app(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> FastAPI:
    return _build_app(database, fake_user_repo, session_repo)


@pytest.fixture
def client(change_set_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(change_set_app, raise_server_exceptions=False) as client:
        yield client


def _authed(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    progress: int = 1,
    role: str = "admin",
) -> dict[str, Any]:
    # This suite exercises confirm (and the propose→confirm pipeline), which
    # is admin-only since 08-03 (AUTH-03) — the actor defaults to an admin.
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


def _create_chat_session(client: TestClient, title: str = "Change-set session") -> dict[str, Any]:
    response = client.post(f"/api/series/{SERIES_ID}/chat/sessions", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


def _create_node_op(**overrides: Any) -> dict[str, Any]:
    op = {
        "operation_type": "create_node",
        "node_type": "Location",
        "label": f"Rita's second home {uuid4()}",
        "episode_id": EPISODE_1,
    }
    op.update(overrides)
    return op


def _propose(client: TestClient, session_id: str, operations: list[dict[str, Any]], summary: str = "Test change") -> Any:
    return client.post(
        f"/api/series/{SERIES_ID}/change-sets",
        json={
            "series_id": SERIES_ID,
            "chat_session_id": session_id,
            "summary": summary,
            "operations": operations,
        },
    )


def _insert_cross_series_node() -> None:
    _fresh_query(
        "CREATE (n:Character {id: $id, series_id: $series_id, label: 'Cross', "
        "visible_from_order: 1, origin: 'canonical'})",
        id=CROSS_SERIES_NODE,
        series_id=OTHER_SERIES_ID,
    )


def test_propose_requires_authentication(client: TestClient) -> None:
    response = _propose(client, "chat-session:nope", [_create_node_op()])
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_UNAUTHENTICATED"


def _location_count(label: str) -> int:
    rows = _fresh_query(
        "MATCH (n:Location {series_id: $series_id, label: $label}) RETURN count(n) AS c",
        series_id=SERIES_ID,
        label=label,
    )
    return rows[0]["c"]


def _change_set_count(session_id: str) -> int:
    rows = _fresh_query(
        "MATCH (cs:ChangeSet {series_id: $series_id, chat_session_id: $session_id}) "
        "RETURN count(cs) AS c",
        series_id=SERIES_ID,
        session_id=session_id,
    )
    return rows[0]["c"]


def _dexter_debra_works_with_claim_count() -> int:
    rows = _fresh_query(
        "MATCH (c:Claim {series_id: $series_id, subject_id: $subject_id, "
        "object_id: $object_id, predicate: 'WORKS_WITH'}) RETURN count(c) AS c",
        series_id=SERIES_ID,
        subject_id=DEXTER,
        object_id=DEBRA,
    )
    return rows[0]["c"]


def test_propose_create_node_returns_awaiting_confirmation_and_creates_no_target(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Rita's second home {uuid4()}"

    response = _propose(client, session["id"], [_create_node_op(label=label)])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "awaiting_confirmation"
    assert body["series_id"] == SERIES_ID
    assert body["chat_session_id"] == session["id"]
    assert body["operations"][0]["operation_type"] == "create_node"
    assert body["visible_until_order_snapshot"] == 1

    assert _location_count(label) == 0


def test_propose_create_relationship_creates_no_claim(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    before = _dexter_debra_works_with_claim_count()
    response = _propose(
        client,
        session["id"],
        [
            {
                "operation_type": "create_relationship",
                "source_id": DEXTER,
                "target_id": DEBRA,
                "relationship_type": "WORKS_WITH",
                "episode_id": EPISODE_1,
            }
        ],
    )
    assert response.status_code == 201, response.text
    after = _dexter_debra_works_with_claim_count()
    assert after == before


def test_propose_hidden_target_rejected_like_nonexistent(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    hidden = _propose(
        client,
        session["id"],
        [{"operation_type": "delete_node", "node_id": RUDY_COOPER}],
    )
    nonexistent = _propose(
        client,
        session["id"],
        [{"operation_type": "delete_node", "node_id": "dexter:character:nope"}],
    )
    assert hidden.status_code == nonexistent.status_code == 422
    assert hidden.json()["detail"]["code"] == nonexistent.json()["detail"]["code"]


def test_propose_cross_series_target_rejected_identically_to_hidden(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _insert_cross_series_node()
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    cross_series = _propose(
        client,
        session["id"],
        [{"operation_type": "delete_node", "node_id": CROSS_SERIES_NODE}],
    )
    hidden = _propose(
        client,
        session["id"],
        [{"operation_type": "delete_node", "node_id": RUDY_COOPER}],
    )
    assert cross_series.status_code == hidden.status_code == 422
    assert cross_series.json()["detail"]["code"] == hidden.json()["detail"]["code"]


def test_propose_operations_validated_in_list_order_no_partial_persistence(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Never persisted {uuid4()}"

    response = _propose(
        client,
        session["id"],
        [
            _create_node_op(label=label),
            {"operation_type": "delete_node", "node_id": RUDY_COOPER},
        ],
    )
    assert response.status_code == 422

    assert _location_count(label) == 0
    assert _change_set_count(session["id"]) == 0


def test_propose_same_content_twice_creates_distinct_change_sets(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    op = _create_node_op()

    first = _propose(client, session["id"], [op], summary="Same content")
    second = _propose(client, session["id"], [op], summary="Same content")

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


# ---------------------------------------------------------------------------
# Task 1 — Stage 2 (Confirm/Apply): transactional apply, full rollback,
# server-derived origin/creator/visible_from_order, single Revision (RAG-12)
# ---------------------------------------------------------------------------


def _confirm(client: TestClient, change_set_id: str) -> Any:
    return client.post(f"/api/series/{SERIES_ID}/change-sets/{change_set_id}/confirm")


def _revision_count_for_change_set(change_set_id: str) -> int:
    rows = _fresh_query(
        "MATCH (r:Revision {resource_type: 'ChangeSet', resource_id: $id}) "
        "RETURN count(r) AS c",
        id=change_set_id,
    )
    return rows[0]["c"]


def _location_row(label: str) -> dict[str, Any] | None:
    rows = _fresh_query(
        "MATCH (n:Location {series_id: $series_id, label: $label}) "
        "RETURN n.id AS id, n.origin AS origin, n.created_by AS created_by, "
        "n.visible_from_order AS visible_from_order",
        series_id=SERIES_ID,
        label=label,
    )
    return rows[0] if rows else None


def _change_set_status(change_set_id: str) -> str | None:
    rows = _fresh_query(
        "MATCH (cs:ChangeSet {id: $id}) RETURN cs.status AS status", id=change_set_id
    )
    return rows[0]["status"] if rows else None


def _revision_before_for_change_set(change_set_id: str) -> Any:
    rows = _fresh_query(
        "MATCH (r:Revision {resource_type: 'ChangeSet', resource_id: $id}) "
        "RETURN r.before AS before",
        id=change_set_id,
    )
    return rows[0]["before"] if rows else "MISSING"


def _insert_user_node(node_id: str, label: str) -> None:
    _fresh_query(
        "CREATE (n:Location {id: $id, series_id: $series_id, label: $label, "
        "episode_id: $episode_id, visible_from_order: 1, origin: 'user', "
        "created_by: 'someone-else', created_at: datetime(), updated_at: datetime()})",
        id=node_id,
        series_id=SERIES_ID,
        label=label,
        episode_id=EPISODE_1,
    )


def _delete_node_by_id(node_id: str) -> None:
    _fresh_query("MATCH (n {id: $id}) DETACH DELETE n", id=node_id)


def test_confirm_applies_all_operations_and_logs_exactly_one_revision(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label_a = f"Confirm apply A {uuid4()}"
    label_b = f"Confirm apply B {uuid4()}"

    proposed = _propose(
        client, session["id"], [_create_node_op(label=label_a), _create_node_op(label=label_b)]
    )
    assert proposed.status_code == 201, proposed.text
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "applied"
    assert body["revision_id"] is not None
    assert body["applied_at"] is not None
    assert body["confirmed_at"] is not None

    row_a = _location_row(label_a)
    row_b = _location_row(label_b)
    assert row_a is not None and row_b is not None

    assert _revision_count_for_change_set(change_set_id) == 1


def test_confirm_rolls_back_entirely_when_an_operation_fails_apply_time_revalidation(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Never applied — rollback proof {uuid4()}"
    target_node_id = f"user-node:rollback-target-{uuid4()}"
    _insert_user_node(target_node_id, "Original label")

    proposed = _propose(
        client,
        session["id"],
        [
            _create_node_op(label=label),
            {
                "operation_type": "update_node",
                "node_id": target_node_id,
                "label": "Updated after propose",
            },
        ],
    )
    assert proposed.status_code == 201, proposed.text
    change_set_id = proposed.json()["id"]

    # Simulate the target being deleted by another action between propose
    # and confirm — the second operation must now fail fresh re-validation.
    _delete_node_by_id(target_node_id)

    response = _confirm(client, change_set_id)
    assert response.status_code == 422, response.text

    # Zero of the ChangeSet's operations were applied — not even the first,
    # otherwise-valid create_node.
    assert _location_row(label) is None
    assert _revision_count_for_change_set(change_set_id) == 0
    # The ChangeSet itself is untouched — still awaiting_confirmation, not a
    # partial/failed state, so a corrected retry remains possible.
    assert _change_set_status(change_set_id) == "awaiting_confirmation"


def test_confirm_assigns_origin_user_and_creator_server_side_never_from_payload(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    user = _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Origin/creator proof {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 200, response.text

    row = _location_row(label)
    assert row is not None
    assert row["origin"] == "user"
    assert row["created_by"] == user["id"]


def test_confirm_derives_visible_from_order_from_current_progress(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"visible_from_order proof {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 200, response.text

    row = _location_row(label)
    assert row is not None
    assert row["visible_from_order"] == 1


def test_confirm_revision_before_snapshot_is_null_for_create_operations(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    proposed = _propose(client, session["id"], [_create_node_op()])
    change_set_id = proposed.json()["id"]

    response = _confirm(client, change_set_id)
    assert response.status_code == 200, response.text

    before = _revision_before_for_change_set(change_set_id)
    assert before is None
