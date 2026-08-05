"""Direct unit tests for the settings module (PROB-18/#40, PROB-30).

Covers production-safe defaults, ALLOWED_EMAILS parsing, the lru_cached
singleton, and the 09-05 google-client-id equality check (both-set-only).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from spoilerless.app.core.config import Settings, get_settings


def _settings(**kwargs: object) -> Settings:
    """Build a Settings instance without touching the ambient .env.

    The Neo4j credential fields are required (no defaults) — pass dummy
    values, mirroring test_database.py::_settings.
    """
    base: dict[str, object] = {
        "_env_file": None,
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_username": "u",
        "neo4j_password": "p",
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def test_settings_production_safe_defaults() -> None:
    settings = _settings()  # no .env — pure defaults
    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "lax"
    assert settings.redis_url == ""
    assert settings.allowed_emails == ""
    assert settings.frontend_origins == "http://localhost:5173"


def test_settings_parses_allowed_emails() -> None:
    # Parsing lives in api/auth.py::_allowed_emails (lowercased, stripped,
    # empty = unrestricted) — exercised through the Settings source field.
    from spoilerless.app.api.auth import _allowed_emails

    with patch(
        "spoilerless.app.api.auth.get_settings",
        return_value=_settings(
            allowed_emails="a@example.com, b@example.com , C@EXAMPLE.com",
        ),
    ):
        assert _allowed_emails() == {
            "a@example.com",
            "b@example.com",
            "c@example.com",
        }

    with patch(
        "spoilerless.app.api.auth.get_settings",
        return_value=_settings(allowed_emails=""),
    ):
        assert _allowed_emails() == frozenset()  # empty = unrestricted


def test_get_settings_is_lru_cached_singleton() -> None:
    first = get_settings()
    second = get_settings()
    assert first is second


def test_google_client_id_equality_check_fires_only_when_both_set() -> None:
    from spoilerless.app.core.config import verify_google_client_id_equality

    # Both unset / both set-and-equal → no raise.
    with patch.dict(os.environ, {}, clear=False):
        verify_google_client_id_equality(
            _settings(google_client_id="", frontend_origins="x")
        )
    with patch.dict(
        os.environ, {"VITE_GOOGLE_CLIENT_ID": "client-123"}, clear=False
    ):
        verify_google_client_id_equality(
            _settings(google_client_id="client-123", frontend_origins="x")
        )

    # Both set but MISMATCHED → RuntimeError (the 01N52-class drift guard).
    with patch.dict(
        os.environ, {"VITE_GOOGLE_CLIENT_ID": "client-other"}, clear=False
    ):
        with pytest.raises(RuntimeError):
            verify_google_client_id_equality(
                _settings(
                    google_client_id="client-123",
                    frontend_origins="x",
                )
            )

    # Backend set but frontend var ABSENT → no raise (local dev without the
    # VITE var must not crash).
    with patch.dict(os.environ, {}, clear=False):
        verify_google_client_id_equality(
            _settings(
                google_client_id="client-123",
                frontend_origins="x",
            )
        )
