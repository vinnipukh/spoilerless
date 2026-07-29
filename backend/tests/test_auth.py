"""Tests for Google Sign-In authentication, sessions, and logout."""

from __future__ import annotations

import re
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.api.auth import get_auth_service, router as auth_router
from backend.app.core.config import get_settings
from backend.app.core.errors import install_database_error_handlers
from backend.app.domain.auth import GoogleAuthRequest, UserPublic, UserResponse
from backend.app.repository.session import InMemorySessionRepository
from backend.app.services.auth import GoogleVerificationError


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeUserRepo:
    """In-memory user repository that stores users keyed by google_sub."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._id_counter = 0

    async def upsert(
        self,
        google_sub: str,
        email: str,
        display_name: str,
        avatar_url: str,
    ) -> dict[str, Any]:
        existing = self._store.get(google_sub)
        if existing:
            existing["email"] = email
            existing["display_name"] = display_name
            existing["avatar_url"] = avatar_url
            return dict(existing)
        self._id_counter += 1
        record = {
            "id": f"user:{self._id_counter}",
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        }
        self._store[google_sub] = record
        return dict(record)

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        for record in self._store.values():
            if record["id"] == user_id:
                return dict(record)
        return None

    def set_upsert_error(self, error: Exception) -> None:
        self._upsert_error = error


class FakeGoogleVerifier:
    """Returns controlled claims; call ``set_failure`` to simulate errors."""

    def __init__(self) -> None:
        self._claims: dict[str, Any] = {
            "sub": "google_sub_12345",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.png",
            "aud": "test-client-id.apps.googleusercontent.com",
        }
        self._fail: GoogleVerificationError | None = None

    def set_claims(self, **overrides: Any) -> None:
        self._claims.update(overrides)

    def set_failure(self, message: str = "Token verification failed.") -> None:
        self._fail = GoogleVerificationError(message)

    async def verify(self, credential: str, client_id: str) -> dict[str, Any]:
        if self._fail:
            raise self._fail
        if credential == "wrong-audience":
            return {"sub": "sub_wrong_aud", "aud": "different-client-id"}
        if credential == "expired-token":
            raise GoogleVerificationError("Token has expired.")
        if credential == "malformed-token":
            raise GoogleVerificationError("Token verification failed.")
        return dict(self._claims)


@pytest.fixture
def fake_verifier() -> FakeGoogleVerifier:
    return FakeGoogleVerifier()


@pytest.fixture
def fake_user_repo() -> FakeUserRepo:
    return FakeUserRepo()


@pytest.fixture
def session_repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.fixture
def auth_app(
    fake_verifier: FakeGoogleVerifier,
    fake_user_repo: FakeUserRepo,
    session_repo: InMemorySessionRepository,
) -> FastAPI:
    """Build a minimal FastAPI app with auth routes and overridden dependencies."""

    app = FastAPI()
    install_database_error_handlers(app)
    app.state.session_repo = session_repo

    def _override_service() -> Any:
        from backend.app.services.auth import AuthService

        return AuthService(
            user_repo=fake_user_repo,
            session_repo=session_repo,
            verifier=fake_verifier,
        )

    app.dependency_overrides[get_auth_service] = _override_service
    app.include_router(auth_router)
    app.state.neo4j = None  # Satisfy any remaining deps that read app.state

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(auth_app: FastAPI) -> TestClient:
    return TestClient(auth_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_ERROR_PATTERN = re.compile(
    r"^authentication_failed$|^unauthenticated$|^auth_disabled$"
)


def _assert_cookie_attr(set_cookie: str, attr: str) -> None:
    """Assert cookie attribute exists, case-insensitively."""
    lower = set_cookie.lower()
    assert attr.lower() in lower, f"Expected '{attr}' in cookie: {set_cookie}"


def _assert_cookie_expired(set_cookie: str) -> bool:
    """Check if a Set-Cookie header tells the browser to delete the cookie."""
    lower = set_cookie.lower()
    return "max-age=0" in lower or "expires=thu, 01 jan 1970" in lower or "expires=thu, 01 jan 197" in lower


def _set_env(monkeypatch: pytest.MonkeyPatch, **kwargs: str | int | bool) -> None:
    get_settings.cache_clear()
    for key, value in kwargs.items():
        monkeypatch.setenv(key, str(value))


# ===================================================================
# POST /api/auth/google
# ===================================================================


class TestGoogleAuth:
    def test_successful_authentication(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id.apps.googleusercontent.com",
            SESSION_TTL_SECONDS=3600,
            SESSION_COOKIE_NAME="session",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        body = response.json()
        user = body["user"]
        assert user["google_sub"] == "google_sub_12345"
        assert user["email"] == "user@example.com"
        assert user["display_name"] == "Test User"
        assert user["avatar_url"] == "https://example.com/avatar.png"
        assert "id" in user
        assert "created_at" in user
        assert "updated_at" in user

        set_cookie = response.headers.get("set-cookie")
        assert set_cookie is not None
        assert "session=" in set_cookie
        _assert_cookie_attr(set_cookie, "httponly")
        _assert_cookie_attr(set_cookie, "samesite=lax")
        _assert_cookie_attr(set_cookie, "path=/")

    def test_authentication_without_secure_flag_in_dev(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            SESSION_COOKIE_SECURE=False,
            SESSION_COOKIE_NAME="session",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "secure" not in set_cookie

    def test_authentication_with_secure_flag(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_NAME="session",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        _assert_cookie_attr(set_cookie, "secure")

    def test_invalid_token_returns_401(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_verifier: FakeGoogleVerifier
    ) -> None:
        fake_verifier.set_failure("Invalid signature.")
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600)

        response = client.post(
            "/api/auth/google",
            json={"credential": "malformed-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "authentication_failed"

    def test_expired_token_returns_401(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600)

        response = client.post(
            "/api/auth/google",
            json={"credential": "expired-token"},
        )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["code"] == "authentication_failed"
        # Generic message — no token validation details leaked
        assert "expired" not in detail["message"].lower()

    def test_auth_disabled_when_no_client_id(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="", SESSION_TTL_SECONDS=3600)

        response = client.post(
            "/api/auth/google",
            json={"credential": "any-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "auth_disabled"

    def test_user_creation(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600)

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        user = response.json()["user"]
        assert user["google_sub"] == "google_sub_12345"

    def test_returning_user_does_not_create_duplicate(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600)

        first = client.post("/api/auth/google", json={"credential": "valid-token"})
        second = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["user"]["id"] == second.json()["user"]["id"]

    def test_updated_profile_fields_on_returning_user(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_verifier: FakeGoogleVerifier
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600)

        # First sign-in
        client.post("/api/auth/google", json={"credential": "valid-token"})

        # Change profile
        fake_verifier.set_claims(
            name="Updated Name", email="updated@example.com", picture="https://example.com/new.png"
        )

        response = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert response.status_code == 200
        user = response.json()["user"]
        assert user["display_name"] == "Updated Name"
        assert user["email"] == "updated@example.com"
        assert user["avatar_url"] == "https://example.com/new.png"
        # ID should remain the same
        assert user["google_sub"] == "google_sub_12345"


# ===================================================================
# GET /api/auth/me
# ===================================================================


class TestGetCurrentUser:
    def test_returns_user_with_valid_session(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        response = client.get("/api/auth/me", cookies={"session": cookie})

        assert response.status_code == 200
        assert response.json()["user"]["google_sub"] == "google_sub_12345"

    def test_returns_401_without_cookie(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "unauthenticated"

    def test_returns_401_with_invalid_cookie(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.get("/api/auth/me", cookies={"session": "invalid-token"})

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "unauthenticated"


# ===================================================================
# POST /api/auth/logout
# ===================================================================


class TestLogout:
    def test_logout_invalidates_session(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        logout_resp = client.post("/api/auth/logout", cookies={"session": cookie})
        assert logout_resp.status_code == 204

        me_resp = client.get("/api/auth/me", cookies={"session": cookie})
        assert me_resp.status_code == 401

    def test_logout_without_session_returns_204(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.post("/api/auth/logout")
        assert response.status_code == 204

    def test_logout_deletes_cookie(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        response = client.post("/api/auth/logout", cookies={"session": cookie})

        assert response.status_code == 204
        set_cookie = response.headers.get("set-cookie", "")
        assert "session=" in set_cookie
        # Should expire the cookie
        assert _assert_cookie_expired(set_cookie), f"Expected expired cookie, got: {set_cookie}"


# ===================================================================
# Cookie attribute assertions
# ===================================================================


class TestCookieAttributes:
    def test_cookie_httponly_samesite_lax(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session")

        response = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        _assert_cookie_attr(set_cookie, "httponly")
        _assert_cookie_attr(set_cookie, "samesite=lax")
        _assert_cookie_attr(set_cookie, "path=/")

    def test_cookie_configurable_name(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="myapp_session")

        response = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert response.status_code == 200
        assert "myapp_session=" in response.headers.get("set-cookie", "")


# ===================================================================
# Error response contract
# ===================================================================


class TestAuthErrorContract:
    def test_auth_error_uses_project_envelope(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.get("/api/auth/me")

        assert response.status_code == 401
        body = response.json()
        assert "detail" in body
        assert "code" in body["detail"]
        assert "message" in body["detail"]
        assert len(body["detail"]["message"]) <= 500


# ===================================================================
# Session lifecycle (server-side)
# ===================================================================


class TestSessionLifecycle:
    def test_session_persists_across_endpoints(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        me1 = client.get("/api/auth/me", cookies={"session": cookie})
        me2 = client.get("/api/auth/me", cookies={"session": cookie})

        assert me1.status_code == 200
        assert me2.status_code == 200
        assert me1.json()["user"]["id"] == me2.json()["user"]["id"]


# ===================================================================
# Application integration — module loads cleanly
# ===================================================================


def test_auth_module_imports() -> None:
    """Verify the auth module and dependencies import without errors."""
    from backend.app.api.auth import router  # noqa: F811
    from backend.app.domain.auth import GoogleAuthRequest, UserPublic, UserResponse  # noqa: F811
    from backend.app.repository.session import InMemorySessionRepository, SessionRecord  # noqa: F811
    from backend.app.repository.user import UserRepository  # noqa: F811
    from backend.app.services.auth import AuthService, ProductionGoogleVerifier  # noqa: F811
    assert router.prefix == "/api/auth"
