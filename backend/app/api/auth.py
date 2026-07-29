"""Authentication API routes — Google Sign-In, session, and logout."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.core.config import get_settings
from backend.app.core.errors import error_responses, http_error
from backend.app.domain.auth import GoogleAuthRequest, UserPublic, UserResponse
from backend.app.repository.session import InMemorySessionRepository, SessionRepository
from backend.app.repository.user import UserRepository
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


def get_session_repo(request: Request) -> SessionRepository:
    return request.app.state.session_repo


SessionRepoDependency = Annotated[SessionRepository, Depends(get_session_repo)]


def get_auth_service(
    database: DatabaseDependency,
    session_repo: SessionRepoDependency,
) -> AuthService:
    return AuthService(
        user_repo=UserRepository(database),
        session_repo=session_repo,
    )


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


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
            401, "auth_disabled", "Google authentication is not configured."
        )

    if not settings.session_ttl_seconds or settings.session_ttl_seconds <= 0:
        raise http_error(
            401, "auth_disabled", "Session TTL is not configured."
        )

    try:
        user, raw_token = await service.authenticate(
            credential=payload.credential,
            client_id=settings.google_client_id,
            session_ttl=settings.session_ttl_seconds,
        )
    except Exception:
        raise http_error(
            401,
            "authentication_failed",
            "Authentication failed. Please try again.",
        )

    _make_cookie(
        response,
        raw_token,
        secure=settings.session_cookie_secure,
        cookie_name=settings.session_cookie_name,
    )

    return UserResponse(user=UserPublic.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    responses={
        401: error_responses(401)[401],
    },
)
async def get_current_user(
    request: Request,
    service: AuthServiceDependency,
) -> UserResponse:
    """Return the authenticated user identified by the session cookie.

    Raises 401 with the standard error envelope when no valid session exists.
    """
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)

    user = await service.get_current_user(
        raw_token, session_ttl=settings.session_ttl_seconds
    )
    if user is None:
        raise http_error(401, "unauthenticated", "Authentication required.")

    return UserResponse(user=UserPublic.model_validate(user))


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
