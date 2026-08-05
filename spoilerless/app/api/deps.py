"""Shared FastAPI dependencies — auth service provider and current-user guard.

The auth dependency providers previously lived in ``spoilerless/app/api/auth.py``
and are re-exported from there for backward compatibility.  ``require_current_user``
is the ownership guard every new per-user resource router (progress, chat,
change_set) uses — it reads the session cookie and resolves the authenticated
``AppUser`` record server-side, exactly like the ``/api/auth/me`` route.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request

from spoilerless.app.core.config import get_settings
from spoilerless.app.core.errors import http_error
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.repository.session import SessionRepository
from spoilerless.app.repository.user import UserRepository
from spoilerless.app.services.auth import AuthService

AUTH_UNAUTHENTICATED = "AUTH_UNAUTHENTICATED"

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


async def require_current_user(
    request: Request,
    service: AuthServiceDependency,
) -> dict[str, Any]:
    """Resolve the authenticated user from the session cookie, or 401.

    Named ``require_current_user`` (not ``get_current_user``) to avoid colliding
    with the existing route handler of that name in ``spoilerless/app/api/auth.py``.
    """
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    user = await service.get_current_user(
        raw_token, session_ttl=settings.session_ttl_seconds
    )
    if user is None:
        raise http_error(401, AUTH_UNAUTHENTICATED, "Authentication required.")
    # Stamp the resolved user on the request so rate-limit identifiers and
    # other per-request dependencies can key on the authenticated user id
    # (services/rate_limit.py::rate_limit_identifier) instead of the IP.
    request.state.user = user
    return user


async def get_optional_current_user(
    request: Request,
    service: AuthServiceDependency,
) -> dict[str, Any] | None:
    """Resolve the authenticated user from the session cookie, or None.

    Same resolution as :func:`require_current_user` but never raises — used by
    read routes that must stay anonymous-capable (e.g. the graph API) while
    clamping the effective boundary to the authenticated user's persisted
    progress when a session is present (D-05).
    """
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    return await service.get_current_user(
        raw_token, session_ttl=settings.session_ttl_seconds
    )


OptionalUserDependency = Annotated[dict[str, Any] | None, Depends(get_optional_current_user)]


CurrentUserDependency = Annotated[dict[str, Any], Depends(require_current_user)]


async def require_admin(user: CurrentUserDependency) -> dict[str, Any]:
    """Require the authenticated user to carry the admin role (AUTH-03/AUTH-04).

    ``role`` is derived server-side from ``ADMIN_EMAILS`` membership at login
    (never read from any request body), so this gate is the enforcement half
    of the D-03 design: only a trusted operator-designated admin can commit
    candidate claims or AI-proposed ChangeSets to the shared canonical graph,
    or mutate the shared LLM settings. Uses the existing lowercase
    ``"FORBIDDEN"`` error code from ``spoilerless/app/core/errors.py``'s
    ``_ERROR_SPECS[403]`` (docs/PROBLEMS.md #20 already flags the casing
    inconsistency — do not add a new uppercase code).
    """
    if user.get("role") != "admin":
        raise http_error(403, "FORBIDDEN", "Admin role required for this action.")
    return user


RequireAdminDependency = Annotated[dict[str, Any], Depends(require_admin)]
