"""Authentication service — Google Sign-In verification, user upsert, session management."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from spoilerless.app.repository.session import SessionRepository, InMemorySessionRepository
from spoilerless.app.repository.user import UserRepository

logger = logging.getLogger(__name__)


class GoogleTokenVerifier(Protocol):
    """Abstraction over Google ID token verification.

    The production implementation delegates to ``google.oauth2.id_token``;
    tests provide a fake that returns controlled claims.
    """

    async def verify(self, credential: str, client_id: str) -> dict[str, Any]:
        """Verify a Google ID token and return decoded claims.

        Raises ``GoogleVerificationError`` on any verification failure.
        """
        ...


class GoogleVerificationError(ValueError):
    """Token verification failed (invalid signature, wrong audience, expired, etc.)."""


class GoogleTransportError(Exception):
    """Infrastructure failure — certificate fetch, network, import, or SSL error.

    Separated from GoogleVerificationError so callers can return the correct
    HTTP status (503) instead of 401.
    """


class EmailNotAllowedError(ValueError):
    """Verified Google identity's email is not on the configured allowlist."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email not allowed: {email}")


def _sanitize_avatar_url(url: str) -> str:
    """Reject dangerous avatar URL schemes (PROB-19/#41).

    Only ``http``/``https`` survive — ``javascript:``, ``data:``, and any
    other scheme (or scheme-less value) strip to empty, so a compromised
    identity-provider claim can never inject an executable URL into a
    rendered profile-image attribute.
    """
    if not url:
        return ""
    scheme = url.split(":", 1)[0].strip().lower() if ":" in url else ""
    if scheme not in {"http", "https"}:
        return ""
    return url


@dataclass(frozen=True)
class ProductionGoogleVerifier:
    """Production verifier using the official ``google-auth`` library.

    Uses ``google.oauth2.id_token.verify_oauth2_token`` which handles
    signature verification, audience, issuer, and expiry checks.
    """

    async def verify(self, credential: str, client_id: str) -> dict[str, Any]:
        try:
            import google.auth.exceptions  # noqa: F401  # binds `google` in function scope so the except clause below can never NameError (#42)
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
        except ImportError as exc:
            raise GoogleTransportError(
                "google.auth.transport.requests failed to import — "
                "install the `requests` package or use `google-auth[requests]`."
            ) from exc

        try:
            request = google_requests.Request()
            info = id_token.verify_oauth2_token(credential, request, client_id)
            return info
        except google.auth.exceptions.TransportError as exc:
            raise GoogleTransportError(
                f"Failed to fetch Google signing certificates: {type(exc).__name__}"
            ) from exc
        except ValueError as exc:
            msg = str(exc)
            # Map common ValueError messages to safe log categories.
            lower_msg = msg.lower()
            if "audience" in lower_msg:
                raise GoogleVerificationError(
                    "audience_mismatch"
                ) from exc
            if "expire" in lower_msg or "before" in lower_msg:
                raise GoogleVerificationError("token_expired") from exc
            if "issuer" in lower_msg or "iss" in lower_msg:
                raise GoogleVerificationError("issuer_mismatch") from exc
            raise GoogleVerificationError(f"verification_failed__{type(exc).__name__}") from exc
        except Exception as exc:
            raise GoogleTransportError(
                f"Google certificate fetch failed: {type(exc).__name__}"
            ) from exc


class AuthService:
    """Orchestrates Google authentication, user upsert, and session lifecycle.

    ``verifier`` is injectable so tests can substitute ``FakeGoogleVerifier``.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository | None = None,
        verifier: GoogleTokenVerifier | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._session_repo = session_repo or InMemorySessionRepository()
        self._verifier = verifier or ProductionGoogleVerifier()

    async def authenticate(
        self,
        credential: str,
        client_id: str,
        session_ttl: int,
        allowed_emails: frozenset[str] | None = None,
        admin_emails: frozenset[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Verify Google token, upsert user, create session.

        Returns (user_record, raw_session_token).
        Identity is derived solely from the verified ``sub`` claim.

        ``allowed_emails``, when non-empty, restricts sign-in to that set
        (case-insensitive). Checked after verification so the rejection is
        based on a Google-attested email, not client-supplied input. Raises
        ``EmailNotAllowedError`` for a verified-but-unlisted email.

        ``admin_emails``, when non-empty, determines the user's ``role``
        (case-insensitive membership). Like ``allowed_emails``, it is
        checked after Google verification succeeds, so role assignment is
        driven by Google-attested identity plus a server-controlled env
        var — never client input. An empty set grants ``"user"`` to every
        login (no implicit admin).
        """
        info = await self._verifier.verify(credential, client_id)

        google_sub: str = info["sub"]
        email: str = info.get("email", "")
        display_name: str = info.get("name", "")
        avatar_url: str = _sanitize_avatar_url(info.get("picture", ""))

        if allowed_emails and email.lower() not in allowed_emails:
            raise EmailNotAllowedError(email)

        role = "admin" if email.lower() in (admin_emails or frozenset()) else "user"

        user = await self._user_repo.upsert(
            google_sub=google_sub,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            role=role,
        )

        raw_token = await self._session_repo.create(
            user_id=user["id"], ttl_seconds=session_ttl
        )

        return user, raw_token

    async def get_current_user(
        self, raw_token: str | None, session_ttl: int
    ) -> dict[str, Any] | None:
        """Validate session and return user record, or None.

        Refreshes the session's last_seen_at on valid access (never the
        expiry — no slide-on-read, PROB-03/#9).
        """
        if raw_token is None:
            return None

        record = await self._session_repo.get(raw_token)
        if record is None:
            return None

        await self._session_repo.refresh(raw_token, session_ttl)
        return await self._user_repo.get_by_id(record.user_id)

    async def logout(self, raw_token: str | None) -> None:
        """Revoke the session if a raw token was provided."""
        if raw_token is not None:
            await self._session_repo.revoke(raw_token)
