"""Tests for structured exception logging and redacting request middleware (08-07, Task 2).

TDD RED phase: these tests MUST FAIL until logging + middleware are added.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import ConstraintError, ServiceUnavailable

from spoilerless.app.api.exceptions import install_repository_error_handlers


# ---------------------------------------------------------------------------
# Helpers — error-handler test app
# ---------------------------------------------------------------------------


def _build_error_test_app() -> FastAPI:
    """Build a minimal FastAPI app with error handlers installed."""
    from spoilerless.app.core.errors import install_database_error_handlers

    app = FastAPI()

    @app.get("/trigger-constraint")
    async def trigger_constraint() -> None:
        from neo4j.exceptions import ConstraintError

        raise ConstraintError("duplicate key")

    @app.get("/trigger-database")
    async def trigger_database() -> None:
        from neo4j.exceptions import ServiceUnavailable

        raise ServiceUnavailable("connection lost")

    @app.get("/trigger-validation")
    async def trigger_validation() -> None:
        from fastapi.exceptions import RequestValidationError

        raise RequestValidationError(errors=[])

    @app.get("/trigger-general-db-error")
    async def trigger_general_db_error() -> None:
        from neo4j.exceptions import Neo4jError

        raise Neo4jError("GENERAL", "general error")

    install_database_error_handlers(app)
    install_repository_error_handlers(app)
    return app


# ---------------------------------------------------------------------------
# Helpers — middleware test app
# ---------------------------------------------------------------------------


def _build_middleware_test_app() -> FastAPI:
    """Build a minimal FastAPI app with ONLY the request-logging middleware.

    Uses the same import as the real app so that when we add the middleware
    to main.py's module, these tests exercise it.
    """
    from spoilerless.app.main import app as real_app

    # Build a fresh minimal app rather than importing the real app
    # (which requires a live Neo4j connection at startup).
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/echo")
    async def echo() -> dict:
        return {"ok": True}

    # If the request-logging middleware has been added to main.py, import and
    # apply it here.  Until then, the "must have a log line" assertion fails
    # (RED).
    try:
        from spoilerless.app.main import _request_logging_middleware  # type: ignore[attr-defined]
    except ImportError:
        _request_logging_middleware = None

    if _request_logging_middleware is not None:
        app.middleware("http")(_request_logging_middleware)

    return app


# ---------------------------------------------------------------------------
# RED tests — exception logging
# ---------------------------------------------------------------------------


class TestExceptionLogging:
    """Tests that every exception handler logs before sanitising (docs/PROBLEMS.md #39)."""

    def test_constraint_error_logs_before_409(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Triggering ConstraintError logs ERROR with exc_info before the 409 response."""
        app = _build_error_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.ERROR):
            resp = client.get("/trigger-constraint")

        assert resp.status_code == 409
        constraint_logs = [
            r for r in caplog.records if r.levelno >= logging.ERROR and r.exc_info
        ]
        assert constraint_logs, (
            "Expected an ERROR log record with exc_info from constraint_handler "
            "but found none."
        )

    def test_database_error_logs_before_503(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Triggering ServiceUnavailable logs ERROR with exc_info before 503."""
        app = _build_error_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.ERROR):
            resp = client.get("/trigger-database")

        assert resp.status_code == 503
        db_logs = [
            r for r in caplog.records if r.levelno >= logging.ERROR and r.exc_info
        ]
        assert db_logs, (
            "Expected an ERROR log record with exc_info from database_handler "
            "but found none."
        )

    def test_validation_error_logs_before_422(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Triggering RequestValidationError logs before 422."""
        app = _build_error_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.ERROR):
            resp = client.get("/trigger-validation")

        assert resp.status_code == 422
        validation_logs = [
            r for r in caplog.records if r.levelno >= logging.ERROR
        ]
        assert validation_logs, (
            "Expected an ERROR log record from validation_handler "
            "but found none."
        )

    def test_neo4jerror_logs_before_503(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Triggering a generic Neo4jError logs ERROR with exc_info before 503."""
        app = _build_error_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.ERROR):
            resp = client.get("/trigger-general-db-error")

        assert resp.status_code == 503
        neo4j_logs = [
            r for r in caplog.records if r.levelno >= logging.ERROR and r.exc_info
        ]
        assert neo4j_logs, (
            "Expected an ERROR log record with exc_info from database_handler "
            "for Neo4jError but found none."
        )


# ---------------------------------------------------------------------------
# RED tests — redacting request-logging middleware
# ---------------------------------------------------------------------------


class TestRequestLoggingMiddleware:
    """The request-logging middleware must log method/path/status/duration
    (INFO level) and NEVER log BYOK keys or cookies."""

    def test_middleware_logs_request_info(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A request produces at least one INFO log with method and path."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.INFO):
            resp = client.get("/health")

        assert resp.status_code == 200

        # Find log records produced by the request-logging middleware.
        # Use getMessage() because the log uses printf-style formatting.
        request_logs = [
            r for r in caplog.records
            if r.levelno == logging.INFO
            and "GET" in r.getMessage()
            and "/health" in r.getMessage()
        ]
        assert request_logs, (
            "Expected a request-logging INFO record with method=GET path=/health, "
            "but found none. The middleware hasn't been added yet."
        )

    def test_middleware_never_logs_byok_api_key(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A request with X-LLM-Api-Key must not leak the key into logs."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        secret = "sk-test-secret-key-should-never-appear-in-logs"
        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/health",
                headers={"X-LLM-Api-Key": secret},
            )

        assert resp.status_code == 200
        full_log = caplog.text
        assert secret not in full_log, (
            f"X-LLM-Api-Key value leaked into logs:\n{full_log}"
        )

    def test_middleware_never_logs_cookie_token(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A request with a session cookie must not log the raw token value."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        session_token = "raw-session-token-should-not-be-logged"
        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/health",
                cookies={"session": session_token},
            )

        assert resp.status_code == 200
        full_log = caplog.text
        assert session_token not in full_log, (
            f"Session cookie value leaked into logs:\n{full_log}"
        )

    def test_middleware_never_logs_byok_base_url(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A request with X-LLM-Base-URL must not leak the URL into logs."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        secret_url = "https://my-private-llm.internal/v1"
        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/health",
                headers={"X-LLM-Base-URL": secret_url},
            )

        assert resp.status_code == 200
        full_log = caplog.text
        assert secret_url not in full_log, (
            f"X-LLM-Base-URL value leaked into logs:\n{full_log}"
        )

    def test_middleware_never_logs_byok_model(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A request with X-LLM-Model must not leak the model name into logs."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        secret_model = "claude-4-enterprise-secret-model"
        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/health",
                headers={"X-LLM-Model": secret_model},
            )

        assert resp.status_code == 200
        full_log = caplog.text
        assert secret_model not in full_log, (
            f"X-LLM-Model value leaked into logs:\n{full_log}"
        )

    def test_middleware_logs_safe_headers(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Safe headers like User-Agent may appear in logs; unsafe ones must not."""
        app = _build_middleware_test_app()
        client = TestClient(app, raise_server_exceptions=False)

        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/health",
                headers={
                    "User-Agent": "test-agent/1.0",
                    "X-LLM-Api-Key": "sk-secret-12345",
                    "Cookie": "session=token-abc",
                },
            )

        assert resp.status_code == 200
        full_log = caplog.text
        # Safe: User-Agent
        assert "User-Agent" in full_log or "test-agent" in full_log, (
            "Expected User-Agent to be safe for logging but it wasn't found"
        )
        # Unsafe: secrets
        assert "sk-secret-12345" not in full_log
        assert "token-abc" not in full_log
