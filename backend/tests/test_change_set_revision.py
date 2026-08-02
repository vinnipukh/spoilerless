"""Tests for ChangeSet Stage 3 (Revert) — RAG-15.

``POST /api/series/{series_id}/change-sets/{change_set_id}/revert`` reuses
``api/revisions.py::revert_revision``'s read-branch-apply-log shape, adapted
to Stage 2's coarser one-Revision-per-apply model (06-06): only ChangeSets
whose applied operations are entirely create-shaped (``create_node``,
``create_relationship``, ``create_claim``, ``attach_evidence``,
``create_note``) have a well-defined pre-apply state to restore (the
resource simply did not exist) without any stored per-operation snapshot.
Reverting one deletes every resource it created, logs a new
``Reverted``-action Revision, and never edits the original apply-time
Revision. A ChangeSet containing any update/delete-shaped operation has no
stored prior state to restore and is rejected with **422** — the same
"no prior state to restore" discipline Phase 4 applies to a plain Creation
revision. A resource modified or removed by a later, unrelated change since
this ChangeSet was applied causes revert to fail with **409** rather than
silently overwrite that change.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import deps
from backend.app.api.change_set import router as change_set_router
from backend.app.api.chat import router as chat_router
from backend.app.api.progress import router as progress_router
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase
from backend.app.llm.provider import FakeLLMProvider, LLMEvent, install_llm_error_handlers
from backend.app.repository.session import InMemorySessionRepository
from backend.app.services.auth import AuthService
from backend.app.services.chat import get_llm_provider

SERIES_ID = "series_dexter"
EPISODE_1 = "dexter_s01e01"
DEXTER = "dexter:character:dexter_morgan"  # canonical, visible_from_order=1


async def _fresh_query(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* on a brand-new driver/loop — never the app's shared driver.

    Same cross-loop-avoidance pattern as ``test_change_set_confirmation.py``.
    """
    db = Neo4jDatabase()
    db.open()
    try:
        return await db.execute_query(query, **params)
    finally:
        await db.close()


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


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()
    yield db

    async def _cleanup() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query(
                "MATCH (n:Revision {resource_type: 'ChangeSet'}) DETACH DELETE n"
            )
            await clean.execute_query("MATCH (n:ChangeSet) DETACH DELETE n")
            await clean.execute_query("MATCH (n:ChatSession) DETACH DELETE n")
            await clean.execute_query("MATCH (n:ChatMessage) DETACH DELETE n")
            await clean.execute_query("MATCH (n:UserSeriesProgress) DETACH DELETE n")
            await clean.execute_query("MATCH (n:UserNote) DETACH DELETE n")
            await clean.execute_query(
                "MATCH (n:Location {series_id: $series_id}) "
                "WHERE NOT n.id STARTS WITH 'dexter:location:' DETACH DELETE n",
                series_id=SERIES_ID,
            )
        finally:
            await clean.close()

    asyncio.run(_cleanup())


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
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo)

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


def _create_chat_session(client: TestClient, title: str = "Revert session") -> dict[str, Any]:
    response = client.post(f"/api/series/{SERIES_ID}/chat/sessions", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


def _create_node_op(**overrides: Any) -> dict[str, Any]:
    op = {
        "operation_type": "create_node",
        "node_type": "Location",
        "label": f"Revert test {uuid4()}",
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


def _revert(client: TestClient, change_set_id: str) -> Any:
    return client.post(f"/api/series/{SERIES_ID}/change-sets/{change_set_id}/revert")


async def _location_row(label: str) -> dict[str, Any] | None:
    rows = await _fresh_query(
        "MATCH (n:Location {series_id: $series_id, label: $label}) "
        "RETURN n.id AS id, n.label AS label, n.origin AS origin, n.updated_at AS updated_at",
        series_id=SERIES_ID,
        label=label,
    )
    return rows[0] if rows else None


async def _location_count(label: str) -> int:
    rows = await _fresh_query(
        "MATCH (n:Location {series_id: $series_id, label: $label}) RETURN count(n) AS c",
        series_id=SERIES_ID,
        label=label,
    )
    return rows[0]["c"]


async def _change_set_status(change_set_id: str) -> str | None:
    rows = await _fresh_query(
        "MATCH (cs:ChangeSet {id: $id}) RETURN cs.status AS status", id=change_set_id
    )
    return rows[0]["status"] if rows else None


async def _revisions_for_change_set(change_set_id: str) -> list[dict[str, Any]]:
    rows = await _fresh_query(
        "MATCH (r:Revision {resource_type: 'ChangeSet', resource_id: $id}) "
        "RETURN r.id AS id, r.action AS action, r.before AS before, r.after AS after, "
        "r.visible_from_order AS visible_from_order, r.created_at AS created_at "
        "ORDER BY r.created_at ASC",
        id=change_set_id,
    )
    return rows


async def _dexter_row() -> dict[str, Any]:
    rows = await _fresh_query(
        "MATCH (n {id: $id}) RETURN n.origin AS origin, n.label AS label",
        id=DEXTER,
    )
    return rows[0]


async def _user_note_count_for_target(target_id: str) -> int:
    rows = await _fresh_query(
        "MATCH (n:UserNote {series_id: $series_id, target_id: $target_id}) RETURN count(n) AS c",
        series_id=SERIES_ID,
        target_id=target_id,
    )
    return rows[0]["c"]


# ---------------------------------------------------------------------------
# Revert succeeds for a single applied (create-shaped) ChangeSet — restores
# pre-apply state, logs a new Revision, never edits the original.
# ---------------------------------------------------------------------------


def test_revert_after_single_applied_change_set_deletes_created_resource(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Single applied revert {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    confirmed = _confirm(client, change_set_id)
    assert confirmed.status_code == 200, confirmed.text
    assert asyncio.run(_location_count(label)) == 1

    response = _revert(client, change_set_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "reverted"

    # Pre-apply state restored: the created resource is gone.
    assert asyncio.run(_location_count(label)) == 0

    # A second, new Revision (Reverted) was logged — never a mutation of the
    # original apply-time (Created) Revision.
    revisions = asyncio.run(_revisions_for_change_set(change_set_id))
    assert len(revisions) == 2
    assert revisions[0]["action"] == "Created"
    assert revisions[1]["action"] == "Reverted"


def test_revert_rejected_when_change_set_was_never_applied(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    proposed = _propose(client, session["id"], [_create_node_op()])
    change_set_id = proposed.json()["id"]

    response = _revert(client, change_set_id)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "resource_conflict"
    assert asyncio.run(_change_set_status(change_set_id)) == "awaiting_confirmation"


def test_reverting_an_already_reverted_change_set_is_rejected(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Double revert {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    assert _confirm(client, change_set_id).status_code == 200

    first = _revert(client, change_set_id)
    assert first.status_code == 200, first.text

    second = _revert(client, change_set_id)
    assert second.status_code == 409, second.text
    assert second.json()["detail"]["code"] == "resource_conflict"


# ---------------------------------------------------------------------------
# Revert never edits or deletes the original Revision — it remains in
# history exactly as recorded, appended-after by the new Revision.
# ---------------------------------------------------------------------------


def test_revert_never_edits_the_original_apply_revision(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Original revision untouched {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    assert _confirm(client, change_set_id).status_code == 200

    before_revert = asyncio.run(_revisions_for_change_set(change_set_id))
    assert len(before_revert) == 1
    original = before_revert[0]

    revert_response = _revert(client, change_set_id)
    assert revert_response.status_code == 200, revert_response.text

    after_revert = asyncio.run(_revisions_for_change_set(change_set_id))
    assert len(after_revert) == 2
    # The original Revision's every field is byte-identical before and after.
    original_again = next(r for r in after_revert if r["id"] == original["id"])
    assert original_again == original


# ---------------------------------------------------------------------------
# Revert validates current state before reverting — a resource further
# modified by a later, unrelated change causes a conflict, not an overwrite.
# ---------------------------------------------------------------------------


def test_revert_conflicts_when_resource_modified_by_later_unrelated_change(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Modified since apply {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    assert _confirm(client, change_set_id).status_code == 200

    created = asyncio.run(_location_row(label))
    assert created is not None
    node_id = created["id"]

    # A later, unrelated ChangeSet mutates the resource this one created.
    later_proposed = _propose(
        client,
        session["id"],
        [{"operation_type": "update_node", "node_id": node_id, "label": "Mutated by later change"}],
        summary="A later, unrelated update",
    )
    assert later_proposed.status_code == 201, later_proposed.text
    later_change_set_id = later_proposed.json()["id"]
    assert _confirm(client, later_change_set_id).status_code == 200

    response = _revert(client, change_set_id)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "resource_conflict"

    # The later change's state is left completely untouched by the failed revert.
    row_after_failed_revert = asyncio.run(_location_row("Mutated by later change"))
    assert row_after_failed_revert is not None
    assert row_after_failed_revert["id"] == node_id
    assert asyncio.run(_change_set_status(change_set_id)) == "applied"


# ---------------------------------------------------------------------------
# Revert requires its own explicit call, distinct from apply confirmation.
# ---------------------------------------------------------------------------


def test_revert_requires_explicit_call_never_triggered_by_a_chat_message(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Chat never reverts {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    assert _confirm(client, change_set_id).status_code == 200

    message_response = client.post(
        f"/api/series/{SERIES_ID}/chat/sessions/{session['id']}/messages",
        json={"question": "Please revert that change for me."},
    )
    assert message_response.status_code == 200, message_response.text

    # Still applied — only a dedicated revert call can move it to reverted.
    assert asyncio.run(_change_set_status(change_set_id)) == "applied"
    assert asyncio.run(_location_count(label)) == 1


# ---------------------------------------------------------------------------
# Only create-shaped ChangeSets support revert — an update/delete-shaped
# operation has no stored prior state to restore (422, not a silent no-op).
# ---------------------------------------------------------------------------


def test_revert_rejected_for_change_set_with_no_stored_prior_state(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Base node for update {uuid4()}"

    created_change_set = _propose(client, session["id"], [_create_node_op(label=label)])
    created_id = created_change_set.json()["id"]
    assert _confirm(client, created_id).status_code == 200
    node_id = asyncio.run(_location_row(label))["id"]

    update_proposed = _propose(
        client,
        session["id"],
        [{"operation_type": "update_node", "node_id": node_id, "label": "Updated label"}],
        summary="Update — no prior state stored",
    )
    assert update_proposed.status_code == 201, update_proposed.text
    update_change_set_id = update_proposed.json()["id"]
    assert _confirm(client, update_change_set_id).status_code == 200

    response = _revert(client, update_change_set_id)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_request"

    # The failed revert attempt made zero mutation — the update stands.
    row = asyncio.run(_location_row("Updated label"))
    assert row is not None
    assert row["id"] == node_id
    assert asyncio.run(_change_set_status(update_change_set_id)) == "applied"


# ---------------------------------------------------------------------------
# Generic 404 for a missing/cross-user ChangeSet — same discipline as
# confirm/reject.
# ---------------------------------------------------------------------------


def test_revert_generic_404_for_missing_or_cross_user_change_set(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)
    label = f"Owned by first user {uuid4()}"

    proposed = _propose(client, session["id"], [_create_node_op(label=label)])
    change_set_id = proposed.json()["id"]
    assert _confirm(client, change_set_id).status_code == 200

    missing = _revert(client, "change-set:does-not-exist")
    assert missing.status_code == 404

    # A second, different user cannot revert the first user's ChangeSet.
    _authed(client, fake_user_repo, session_repo, progress=1)
    cross_user = _revert(client, change_set_id)
    assert cross_user.status_code == 404
    assert asyncio.run(_change_set_status(change_set_id)) == "applied"


# ---------------------------------------------------------------------------
# Only user-origin changes support revert — a canonical/candidate-protected
# resource is never itself mutated by revert, consistent with the existing
# RAG-13 protection invariant (the transparent create_note override is the
# only thing ever created; reverting it never touches the canonical target).
# ---------------------------------------------------------------------------


def test_revert_of_canonical_override_note_leaves_canonical_resource_untouched(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo, progress=1)
    session = _create_chat_session(client)

    before = asyncio.run(_dexter_row())
    assert before["origin"] == "canonical"

    # A direct-mutation op against a canonical target is transparently
    # substituted into a create_note override at propose time (RAG-13) — the
    # canonical resource itself is never touched by propose or confirm.
    proposed = _propose(
        client,
        session["id"],
        [{"operation_type": "update_node", "node_id": DEXTER, "label": "Attempted overwrite"}],
        summary="Attempted canonical overwrite -> transparent override note",
    )
    assert proposed.status_code == 201, proposed.text
    change_set_id = proposed.json()["id"]
    assert proposed.json()["operations"][0]["operation_type"] == "create_note"

    assert _confirm(client, change_set_id).status_code == 200
    assert asyncio.run(_user_note_count_for_target(DEXTER)) == 1

    response = _revert(client, change_set_id)
    assert response.status_code == 200, response.text

    # The override note is gone; the canonical resource was never touched by
    # either the apply or the revert.
    assert asyncio.run(_user_note_count_for_target(DEXTER)) == 0
    after = asyncio.run(_dexter_row())
    assert after == before
