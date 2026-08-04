"""Tests for Google Sign-In authentication, sessions, and logout."""

from __future__ import annotations

import re
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.api.auth import (
    AUTH_INVALID_GOOGLE_CREDENTIAL,
    AUTH_UNAUTHENTICATED,
    AUTH_ORIGIN_NOT_ALLOWED,
    AUTH_DISABLED,
    get_auth_service,
    router as auth_router,
    verify_origin,
)
from backend.app.core.config import get_settings
from backend.app.core.errors import install_database_error_handlers
from backend.app.domain.auth import GoogleAuthRequest, UserPublic, UserResponse
from backend.app.repository.session import InMemorySessionRepository, SessionRecord
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
        role: str = "user",
    ) -> dict[str, Any]:
        existing = self._store.get(google_sub)
        if existing:
            existing["email"] = email
            existing["display_name"] = display_name
            existing["avatar_url"] = avatar_url
            # Role re-syncs to the caller-supplied value on every login,
            # mirroring the real repository's ON MATCH SET u.role = $role.
            existing["role"] = role
            return dict(existing)
        self._id_counter += 1
        record = {
            "id": f"user:{self._id_counter}",
            "google_sub": google_sub,
            "email": email,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "role": role,
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
    """Build a minimal FastAPI app with auth routes and overridden dependencies.

    By default the CSRF ``verify_origin`` dependency is bypassed (set
    ``FRONTEND_ORIGINS=*``) so tests that don't care about origin validation
    pass without a custom header.  CSRF-specific tests override this.
    """

    _set_env_raw(
        GOOGLE_CLIENT_ID="test-client-id.apps.googleusercontent.com",
        SESSION_TTL_SECONDS=3600,
        SESSION_COOKIE_NAME="session",
        FRONTEND_ORIGINS="http://localhost:5173",
    )

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
    r"^(AUTH_INVALID_GOOGLE_CREDENTIAL|AUTH_UNAUTHENTICATED|AUTH_DISABLED|AUTH_ORIGIN_NOT_ALLOWED)$"
)


def _assert_cookie_attr(set_cookie: str, attr: str) -> None:
    """Assert cookie attribute exists, case-insensitively."""
    lower = set_cookie.lower()
    assert attr.lower() in lower, f"Expected '{attr}' in cookie: {set_cookie}"


def _assert_cookie_expired(set_cookie: str) -> bool:
    """Check if a Set-Cookie header tells the browser to delete the cookie."""
    lower = set_cookie.lower()
    return "max-age=0" in lower or "expires=thu, 01 jan 1970" in lower or "expires=thu, 01 jan 197" in lower


def _set_env_raw(**kwargs: str | int | bool) -> None:
    """Set env vars without monkeypatch — for fixture-level setup."""
    import os
    get_settings.cache_clear()
    for key, value in kwargs.items():
        os.environ[key] = str(value)


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
            FRONTEND_ORIGINS="*",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
            headers={"Origin": "http://localhost:5173"},
        )

        assert response.status_code == 200
        body = response.json()
        user = body["user"]
        assert user["email"] == "user@example.com"
        assert user["display_name"] == "Test User"
        assert user["avatar_url"] == "https://example.com/avatar.png"
        assert "id" in user
        assert "created_at" in user
        assert "updated_at" in user
        # google_sub must NOT be exposed to clients
        assert "google_sub" not in user

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
            FRONTEND_ORIGINS="*",
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
            FRONTEND_ORIGINS="*",
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
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        response = client.post(
            "/api/auth/google",
            json={"credential": "malformed-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_INVALID_GOOGLE_CREDENTIAL

    def test_expired_token_returns_401(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        response = client.post(
            "/api/auth/google",
            json={"credential": "expired-token"},
        )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["code"] == AUTH_INVALID_GOOGLE_CREDENTIAL
        # Generic message — no token validation details leaked
        assert "expired" not in detail["message"].lower()

    def test_auth_disabled_when_no_client_id(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        response = client.post(
            "/api/auth/google",
            json={"credential": "any-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_DISABLED

    def test_user_creation(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200
        user = response.json()["user"]
        assert user["email"] == "user@example.com"
        # google_sub is not in the response
        assert "google_sub" not in user

    def test_returning_user_does_not_create_duplicate(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        first = client.post("/api/auth/google", json={"credential": "valid-token"})
        second = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["user"]["id"] == second.json()["user"]["id"]

    def test_updated_profile_fields_on_returning_user(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_verifier: FakeGoogleVerifier
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

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
        # google_sub is not in the response
        assert "google_sub" not in user


# ===================================================================
# GET /api/auth/me
# ===================================================================


class TestGetCurrentUser:
    def test_returns_user_with_valid_session(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session", FRONTEND_ORIGINS="*")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        response = client.get("/api/auth/me", cookies={"session": cookie})

        assert response.status_code == 200
        assert response.json()["user"]["email"] == "user@example.com"
        assert "google_sub" not in response.json()["user"]

    def test_returns_401_without_cookie(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_UNAUTHENTICATED

    def test_returns_401_with_invalid_cookie(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, SESSION_COOKIE_NAME="session")

        response = client.get("/api/auth/me", cookies={"session": "invalid-token"})

        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_UNAUTHENTICATED


# ===================================================================
# POST /api/auth/logout
# ===================================================================


class TestLogout:
    def test_logout_invalidates_session(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session", FRONTEND_ORIGINS="*")

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
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session", FRONTEND_ORIGINS="*")

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
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session", FRONTEND_ORIGINS="*")

        response = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        _assert_cookie_attr(set_cookie, "httponly")
        _assert_cookie_attr(set_cookie, "samesite=lax")
        _assert_cookie_attr(set_cookie, "path=/")

    def test_cookie_configurable_name(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="myapp_session", FRONTEND_ORIGINS="*")

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
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, SESSION_COOKIE_NAME="session", FRONTEND_ORIGINS="*")

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        me1 = client.get("/api/auth/me", cookies={"session": cookie})
        me2 = client.get("/api/auth/me", cookies={"session": cookie})

        assert me1.status_code == 200
        assert me2.status_code == 200
        assert me1.json()["user"]["id"] == me2.json()["user"]["id"]


# ===================================================================
# Session token hashing
# ===================================================================


class TestSessionTokenHashing:
    def test_raw_token_not_stored_in_memory(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, session_repo: InMemorySessionRepository
    ) -> None:
        """Verify the in-memory store holds hashed tokens, not raw ones."""
        _set_env(monkeypatch, GOOGLE_CLIENT_ID="test-client-id", SESSION_TTL_SECONDS=3600, FRONTEND_ORIGINS="*")

        client.post("/api/auth/google", json={"credential": "valid-token"})

        for key in session_repo._store:
            # Keys in the in-memory store are SHA-256 hashes (64 hex chars)
            assert len(key) == 64, f"Expected SHA-256 hash, got: {key}"
            assert all(c in "0123456789abcdef" for c in key)


# ===================================================================
# CSRF / Origin validation
# ===================================================================


class TestCSRFOriginValidation:
    def test_post_google_rejects_unexpected_origin(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="http://localhost:5173",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
            headers={"Origin": "http://evil.com"},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == AUTH_ORIGIN_NOT_ALLOWED

    def test_post_google_accepts_allowed_origin(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="http://localhost:5173,http://example.com",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
            headers={"Origin": "http://example.com"},
        )

        assert response.status_code == 200

    def test_wildcard_origin_bypasses_csrf(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
        )

        # Without Origin header — should pass because wildcard bypasses CSRF
        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200


# ===================================================================
# Auth error codes are stable
# ===================================================================


class TestAuthErrorCodes:
    def test_error_code_constants_defined(self) -> None:
        """All error code constants are importable and non-empty."""
        from backend.app.api.auth import (
            AUTH_INVALID_GOOGLE_CREDENTIAL,
            AUTH_UNAUTHENTICATED,
            AUTH_SESSION_EXPIRED,
            AUTH_SESSION_INVALID,
            AUTH_ORIGIN_NOT_ALLOWED,
            AUTH_EMAIL_NOT_ALLOWED,
            AUTH_DISABLED,
        )
        assert AUTH_INVALID_GOOGLE_CREDENTIAL == "AUTH_INVALID_GOOGLE_CREDENTIAL"
        assert AUTH_UNAUTHENTICATED == "AUTH_UNAUTHENTICATED"
        assert AUTH_SESSION_EXPIRED == "AUTH_SESSION_EXPIRED"
        assert AUTH_SESSION_INVALID == "AUTH_SESSION_INVALID"
        assert AUTH_ORIGIN_NOT_ALLOWED == "AUTH_ORIGIN_NOT_ALLOWED"
        assert AUTH_EMAIL_NOT_ALLOWED == "AUTH_EMAIL_NOT_ALLOWED"
        assert AUTH_DISABLED == "AUTH_DISABLED"


# ===================================================================
# POST /api/auth/google — email allowlist
# ===================================================================


class TestEmailAllowlist:
    def test_login_rejected_when_email_not_on_allowlist(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ALLOWED_EMAILS="alice@example.com,bob@example.com",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "AUTH_EMAIL_NOT_ALLOWED"

    def test_login_allowed_when_allowlist_empty(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ALLOWED_EMAILS="",
        )

        response = client.post(
            "/api/auth/google",
            json={"credential": "valid-token"},
        )

        assert response.status_code == 200


# ===================================================================
# POST /api/auth/google — admin role derived from ADMIN_EMAILS (AUTH-03, D-03)
# ===================================================================


class TestAdminRole:
    """Role is derived server-side from ADMIN_EMAILS membership at login.

    No request body can set or override ``role``: it is computed only after
    Google verification succeeds, from a server-controlled env var, and
    re-synced on every login (so removing an email from ADMIN_EMAILS demotes
    that user on their next sign-in — no self-service grant path exists).
    """

    def test_login_with_admin_email_grants_admin_role_on_first_login(
        self,
        client: TestClient,
        fake_verifier: FakeGoogleVerifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_verifier.set_claims(email="admin@example.com")
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="admin@example.com,user@example.com",
        )

        response = client.post(
            "/api/auth/google", json={"credential": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"

    def test_admin_role_persists_and_re_syncs_on_relogin(
        self,
        client: TestClient,
        fake_verifier: FakeGoogleVerifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_verifier.set_claims(email="admin@example.com")
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="admin@example.com",
        )

        first = client.post("/api/auth/google", json={"credential": "valid-token"})
        second = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert first.status_code == 200
        assert second.status_code == 200
        # Same user record, role re-synced to admin on every login.
        assert first.json()["user"]["id"] == second.json()["user"]["id"]
        assert first.json()["user"]["role"] == "admin"
        assert second.json()["user"]["role"] == "admin"

    def test_me_returns_admin_role(
        self,
        client: TestClient,
        fake_verifier: FakeGoogleVerifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_verifier.set_claims(email="admin@example.com")
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            SESSION_COOKIE_NAME="session",
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="admin@example.com",
        )

        auth_resp = client.post("/api/auth/google", json={"credential": "valid-token"})
        cookie = auth_resp.cookies.get("session")

        response = client.get("/api/auth/me", cookies={"session": cookie})

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"

    def test_login_with_email_absent_from_admin_emails_grants_user_role(
        self,
        client: TestClient,
        fake_verifier: FakeGoogleVerifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_verifier.set_claims(email="regular@example.com")
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="admin@example.com",
        )

        response = client.post(
            "/api/auth/google", json={"credential": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "user"

    def test_admin_demoted_when_email_removed_from_admin_emails(
        self,
        client: TestClient,
        fake_verifier: FakeGoogleVerifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_verifier.set_claims(email="admin@example.com")
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="admin@example.com",
        )
        first = client.post("/api/auth/google", json={"credential": "valid-token"})
        assert first.status_code == 200
        assert first.json()["user"]["role"] == "admin"

        # Operator removes the email from ADMIN_EMAILS; the next login
        # re-syncs the persisted role back to "user" (nothing prevents
        # demotion when membership is revoked).
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="",
        )
        second = client.post("/api/auth/google", json={"credential": "valid-token"})

        assert second.status_code == 200
        assert second.json()["user"]["id"] == first.json()["user"]["id"]
        assert second.json()["user"]["role"] == "user"

    def test_empty_admin_emails_means_no_implicit_admin(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_env(
            monkeypatch,
            GOOGLE_CLIENT_ID="test-client-id",
            SESSION_TTL_SECONDS=3600,
            FRONTEND_ORIGINS="*",
            ADMIN_EMAILS="",
        )

        response = client.post(
            "/api/auth/google", json={"credential": "valid-token"}
        )

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "user"

    def test_user_public_model_validates_and_exposes_role(self) -> None:
        user = UserPublic.model_validate(
            {
                "id": "user:1",
                "email": "admin@example.com",
                "display_name": "Admin",
                "avatar_url": "",
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "role": "admin",
            }
        )
        assert user.role == "admin"
        assert user.model_dump()["role"] == "admin"

    def test_user_public_defaults_role_to_user(self) -> None:
        # A pre-migration record that somehow lacks the role property must
        # still validate (default "user").
        user = UserPublic.model_validate(
            {
                "id": "user:1",
                "email": "user@example.com",
                "display_name": "User",
                "avatar_url": "",
                "created_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        )
        assert user.role == "user"

    def test_google_auth_request_rejects_client_supplied_role(self) -> None:
        # extra="forbid": no request body field can carry a role value —
        # role is never client-input (T-08-03-03).
        with pytest.raises(ValidationError):
            GoogleAuthRequest(credential="valid-token", role="admin")


# ===================================================================
# Application integration — module loads cleanly
# ===================================================================


def test_auth_module_imports() -> None:
    """Verify the auth module and dependencies import without errors."""
    from backend.app.api.auth import router  # noqa: F811
    from backend.app.domain.auth import GoogleAuthRequest, UserPublic, UserResponse  # noqa: F811
    from backend.app.repository.session import InMemorySessionRepository, Neo4jSessionRepository, SessionRecord  # noqa: F811
    from backend.app.repository.user import UserRepository  # noqa: F811
    from backend.app.services.auth import AuthService, ProductionGoogleVerifier  # noqa: F811
    assert router.prefix == "/api/auth"
