"""Authentication API routes — Google Sign-In, session, and logout."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from backend.app.api.deps import (
    AuthServiceDependency,
    CurrentUserDependency,
    get_auth_service,  # noqa: F401 — re-exported for backward compatibility
    get_session_repo,  # noqa: F401 — re-exported for backward compatibility
    require_current_user,
)
from backend.app.core.config import get_settings
from backend.app.core.errors import error_responses, http_error
from backend.app.domain.auth import (
    GoogleAuthRequest,
    UserPublic,
    UserResponse,
)
from backend.app.services.auth import (
    EmailNotAllowedError,
    GoogleTransportError,
    GoogleVerificationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Error codes — stable machine-readable strings for the error envelope
# ---------------------------------------------------------------------------
AUTH_INVALID_GOOGLE_CREDENTIAL = "AUTH_INVALID_GOOGLE_CREDENTIAL"
AUTH_UNAUTHENTICATED = "AUTH_UNAUTHENTICATED"
AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
AUTH_SESSION_INVALID = "AUTH_SESSION_INVALID"
AUTH_ORIGIN_NOT_ALLOWED = "AUTH_ORIGIN_NOT_ALLOWED"
AUTH_EMAIL_NOT_ALLOWED = "AUTH_EMAIL_NOT_ALLOWED"
AUTH_DISABLED = "AUTH_DISABLED"


def _allowed_origins() -> list[str]:
    """Parse and return the configured frontend origins, stripping empties."""
    settings = get_settings()
    return [
        o.strip()
        for o in settings.frontend_origins.split(",")
        if o.strip()
    ]


def _allowed_emails() -> frozenset[str]:
    """Parse the configured email allowlist, lowercased. Empty means unrestricted."""
    settings = get_settings()
    return frozenset(
        e.strip().lower()
        for e in settings.allowed_emails.split(",")
        if e.strip()
    )


def _admin_emails() -> frozenset[str]:
    """Parse the configured admin email allowlist, lowercased. Empty means no admin exists."""
    settings = get_settings()
    return frozenset(
        e.strip().lower()
        for e in settings.admin_emails.split(",")
        if e.strip()
    )


async def verify_origin(request: Request) -> None:
    """Verify ``Origin`` (preferred) or ``Referer`` matches a configured
    frontend origin to protect state-changing requests against CSRF.

    The check is deliberately performed as a FastAPI dependency on each
    state-changing auth route so it composes naturally with the existing
    dependency graph.  Reads ``FRONTEND_ORIGINS`` from config, so the same
    setting controls both CORS and CSRF validation.

    ``SameSite=Lax`` on the session cookie prevents most cross-site form
    POSTs but does **not** protect against subdomain-based attacks or
    top-level navigations.  Origin/referer validation is the complementary
    defence.
    """
    origins = _allowed_origins()

    # Wildcard — no protection (not recommended, explicit setting required).
    if "*" in origins:
        return

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    candidate = None
    if origin:
        candidate = origin
    elif referer:
        # Take scheme + host from the Referer URL.
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            candidate = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port is not None:
                candidate += f":{parsed.port}"
        except Exception:
            candidate = None

    # If neither Origin nor Referer is present, allow the request through.
    # SameSite=Lax on the session cookie blocks cross-site POSTs without
    # needing header validation; this check is defense-in-depth for cases
    # where SameSite is insufficient (subdomain attacks, legacy browsers).
    if candidate is None:
        return

    if candidate in origins:
        return

    raise http_error(
        403, AUTH_ORIGIN_NOT_ALLOWED,
        "Request origin is not allowed.",
    )


def _make_cookie(response: Response, raw_token: str, secure: bool, cookie_name: str) -> None:
    """Set the HttpOnly session cookie on the response."""
    response.set_cookie(
        key=cookie_name,
        value=raw_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _delete_cookie(response: Response, secure: bool, cookie_name: str) -> None:
    """Clear the session cookie by setting an expired value."""
    response.delete_cookie(
        key=cookie_name,
        path="/",
        secure=secure,
        samesite="lax",
        httponly=True,
    )


@router.post(
    "/google",
    response_model=UserResponse,
    status_code=200,
    summary="Sign in with Google",
    responses={
        401: error_responses(401)[401],
        422: error_responses(422)[422],
    },
)
async def google_auth(
    payload: GoogleAuthRequest,
    response: Response,
    service: AuthServiceDependency,
    _csrf: Annotated[None, Depends(verify_origin)],
) -> UserResponse:
    """Authenticate via a Google ID token.

    Verifies the token signature, issuer, audience, and expiration against the
    configured ``GOOGLE_CLIENT_ID``.  Creates or updates a local user record
    keyed on Google's ``sub`` claim.  Returns the user and sets a secure
    HttpOnly session cookie.
    """
    settings = get_settings()

    if not settings.google_client_id:
        raise http_error(
            401, AUTH_DISABLED, "Google authentication is not configured."
        )

    if not settings.session_ttl_seconds or settings.session_ttl_seconds <= 0:
        raise http_error(
            401, AUTH_DISABLED, "Session TTL is not configured."
        )

    try:
        user, raw_token = await service.authenticate(
            credential=payload.credential,
            client_id=settings.google_client_id,
            session_ttl=settings.session_ttl_seconds,
            allowed_emails=_allowed_emails(),
            admin_emails=_admin_emails(),
        )
    except EmailNotAllowedError as exc:
        logger.warning("google_auth: email_not_allowed (%s)", exc.email)
        raise http_error(
            403,
            AUTH_EMAIL_NOT_ALLOWED,
            "This account is not authorized to access this application.",
        )
    except GoogleVerificationError as exc:
        logger.warning("google_auth: %s", str(exc))
        raise http_error(
            401,
            AUTH_INVALID_GOOGLE_CREDENTIAL,
            "Authentication failed. Please try again.",
        )
    except GoogleTransportError as exc:
        logger.warning("google_auth: transport_error (%s)", str(exc))
        raise http_error(
            503,
            "AUTH_SERVICE_UNAVAILABLE",
            "Authentication service is temporarily unavailable.",
        )
    except Exception as exc:
        logger.warning("google_auth: internal_error (%s)", type(exc).__name__)
        raise http_error(
            503,
            "AUTH_SERVICE_UNAVAILABLE",
            "Authentication service is temporarily unavailable.",
        )

    _make_cookie(
        response,
        raw_token,
        secure=settings.session_cookie_secure,
        cookie_name=settings.session_cookie_name,
    )

    return UserResponse(user=UserPublic.model_validate(
        {k: v for k, v in user.items() if k in UserPublic.model_fields}
    ))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    responses={
        401: error_responses(401)[401],
    },
)
async def get_current_user(
    user: CurrentUserDependency,
) -> UserResponse:
    """Return the authenticated user identified by the session cookie.

    Delegates to the shared ``require_current_user`` dependency (same body the
    route previously inlined); raises 401 with the standard error envelope when
    no valid session exists.
    """
    return UserResponse(user=UserPublic.model_validate(
        {k: v for k, v in user.items() if k in UserPublic.model_fields}
    ))


@router.post(
    "/logout",
    status_code=204,
    summary="Log out and invalidate session",
    responses={
        204: {"description": "Session invalidated and cookie deleted."},
    },
)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> Response:
    """Invalidate the server-side session and delete the browser cookie."""
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)

    await service.logout(raw_token)

    _delete_cookie(
        response,
        secure=settings.session_cookie_secure,
        cookie_name=settings.session_cookie_name,
    )

    response.status_code = 204
    return response
