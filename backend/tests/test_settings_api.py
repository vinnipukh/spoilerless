"""Tests for the settings API (LLM provider configuration).

Covers: auth guard, masked GET response, PUT persistence with blank-key-keeps-
old semantics, provider/model/base_url updates, and that the full API key never
appears in any response (T-06-07). The auth layer is overridden with the
in-memory fake (same pattern as test_chat_api.py); the SettingsService reads
and writes the real Neo4j ``:AppSetting`` node.
"""

from __future__ import annotations

import asyncio
from typing import Any, Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import deps
from backend.app.api.settings import router as settings_router
from backend.app.core.errors import install_database_error_handlers
from backend.app.graph.database import Neo4jDatabase
from backend.app.repository.session import InMemorySessionRepository
from backend.app.services.auth import AuthService


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


@pytest.fixture
def database() -> Iterator[Neo4jDatabase]:
    db = Neo4jDatabase()
    db.open()

    # Backup the pre-existing AppSetting node (the user's real LLM config —
    # this suite runs against the shared live Neo4j, so deleting the node in
    # teardown would silently wipe the user's stored API key/enabled state,
    # which is exactly what happened once: the stored `enabled:true` vanished
    # and chat regressed to LLM_DISABLED until re-entered).
    async def _backup() -> str | None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            rows = await clean.execute_query(
                "MATCH (s:AppSetting {key: $k}) RETURN s.value AS value", k="llm"
            )
            return rows[0]["value"] if rows and rows[0].get("value") else None
        finally:
            await clean.close()

    backup = asyncio.run(_backup())

    yield db

    # Restore the pre-existing value (or remove the node when none existed)
    # with a fresh driver + loop (the app's driver is bound to TestClient's
    # portal loop; reusing it here would crash cross-loop — same pattern as
    # test_chat_api.py).
    async def _cleanup() -> None:
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
) -> FastAPI:
    app = FastAPI()
    install_database_error_handlers(app)
    app.state.neo4j = database
    app.state.session_repo = session_repo

    def _override_auth_service() -> AuthService:
        return AuthService(user_repo=fake_user_repo, session_repo=session_repo)

    app.dependency_overrides[deps.get_auth_service] = _override_auth_service
    app.include_router(settings_router)
    return app


@pytest.fixture
def client(
    database: Neo4jDatabase,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> Iterator[TestClient]:
    # Context-managed TestClient keeps ONE portal loop alive for the whole
    # test — the app's async Neo4j driver is only ever used inside that loop
    # (test_graph_api.py/test_progress_api.py pattern). Without `with`,
    # starlette starts a fresh per-request loop and pooled driver connections
    # die with the first one ('NoneType' object has no attribute 'send').
    with TestClient(
        _build_app(database, fake_user_repo, session_repo),
        raise_server_exceptions=False,
    ) as client:
        yield client


def _authed(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    role: str = "admin",
) -> None:
    # The /api/settings/llm endpoint is admin-only since 08-03 (AUTH-04), so
    # the roundtrip tests act as an admin operator; the 403 tests below pass
    # role="user" explicitly.
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


def test_get_settings_requires_auth(client: TestClient) -> None:
    response = client.get("/api/settings/llm")
    assert response.status_code == 401


def test_get_and_update_llm_settings_roundtrip(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    # The suite runs against the shared live Neo4j — a real user-configured
    # :AppSetting node may exist. Clear it for a deterministic start; the
    # database fixture's teardown restores whatever was there.
    async def _clear() -> None:
        clean = Neo4jDatabase()
        clean.open()
        try:
            await clean.execute_query("MATCH (s:AppSetting {key: 'llm'}) DETACH DELETE s")
        finally:
            await clean.close()

    asyncio.run(_clear())

    _authed(client, fake_user_repo, session_repo)

    # Initial state: no stored settings -> env defaults, no key configured.
    response = client.get("/api/settings/llm")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api_key_configured"] is False
    assert body["api_key_masked"] is None
    assert body["enabled"] is False  # LLM_ENABLED env default (unset in tests)

    # PUT a gemini config with a key + enabled.
    response = client.put(
        "/api/settings/llm",
        json={
            "provider": "gemini",
            "api_key": "AIzaSyTestKey1234567890",
            "model": "gemini-2.5-flash",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "gemini"
    assert body["model"] == "gemini-2.5-flash"
    assert body["enabled"] is True
    assert body["api_key_configured"] is True
    assert body["api_key_masked"] == "••••7890"
    # The full key must never appear in the response (T-06-07).
    assert "AIzaSyTestKey1234567890" not in response.text

    # GET reflects the stored config.
    response = client.get("/api/settings/llm")
    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"
    assert response.json()["api_key_masked"] == "••••7890"
    assert response.json()["enabled"] is True

    # Blank api_key keeps the stored one (client only ever sees the masked form).
    response = client.put(
        "/api/settings/llm",
        json={"provider": "gemini", "model": "gemini-3.6-flash", "api_key": ""},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model"] == "gemini-3.6-flash"
    assert body["enabled"] is True  # not sent -> kept
    assert body["api_key_masked"] == "••••7890"
    assert "AIzaSyTestKey1234567890" not in response.text

    # Switch to openai_compatible with base_url; key still kept.
    response = client.put(
        "/api/settings/llm",
        json={
            "provider": "openai_compatible",
            "base_url": "https://llm.example/v1",
            "model": "gpt-4.1-mini",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "openai_compatible"
    assert body["base_url"] == "https://llm.example/v1"
    assert body["model"] == "gpt-4.1-mini"
    assert body["api_key_masked"] == "••••7890"


def test_update_llm_settings_rejects_unknown_fields(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    _authed(client, fake_user_repo, session_repo)
    response = client.put(
        "/api/settings/llm",
        json={"provider": "gemini", "sneaky": "field"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_url",
    [
        "file:///etc/passwd",
        "gopher://internal:70/",
        "ftp://internal/",
        "javascript:alert(1)",
        "not-a-url",
        "://missing-scheme",
    ],
)
def test_update_llm_settings_rejects_non_http_base_url(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
    bad_url: str,
) -> None:
    # SSRF-via-scheme guard (see domain/settings.py's _validate_base_url):
    # only http/https may reach the provider client.
    _authed(client, fake_user_repo, session_repo)
    response = client.put(
        "/api/settings/llm",
        json={"provider": "openai_compatible", "base_url": bad_url},
    )
    assert response.status_code == 422, response.text


def test_update_llm_settings_accepts_local_http_base_url(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    # Local vLLM/Ollama endpoints remain a documented, supported deployment —
    # the scheme guard must not regress this (see docs/GETTING-STARTED.md 7.8).
    _authed(client, fake_user_repo, session_repo)
    response = client.put(
        "/api/settings/llm",
        json={
            "provider": "openai_compatible",
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "llama3",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["base_url"] == "http://127.0.0.1:11434/v1"


def test_get_and_update_llm_settings_require_admin_role(
    client: TestClient,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> None:
    """GET and PUT /api/settings/llm are admin-only (AUTH-04, T-08-03-04)."""
    _authed(client, fake_user_repo, session_repo, role="user")

    get_response = client.get("/api/settings/llm")
    assert get_response.status_code == 403, get_response.text
    assert get_response.json()["detail"]["code"] == "forbidden"

    put_response = client.put(
        "/api/settings/llm",
        json={
            "provider": "gemini",
            "api_key": "AIzaSyTestKey1234567890",
            "model": "gemini-2.5-flash",
            "enabled": True,
        },
    )
    assert put_response.status_code == 403, put_response.text
    assert put_response.json()["detail"]["code"] == "forbidden"
