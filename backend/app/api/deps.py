"""Shared FastAPI dependencies — auth service provider and current-user guard.

The auth dependency providers previously lived in ``backend/app/api/auth.py``
and are re-exported from there for backward compatibility.  ``require_current_user``
is the ownership guard every new per-user resource router (progress, chat,
change_set) uses — it reads the session cookie and resolves the authenticated
``AppUser`` record server-side, exactly like the ``/api/auth/me`` route.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request

from backend.app.core.config import get_settings
from backend.app.core.errors import http_error
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.repository.session import SessionRepository
from backend.app.repository.user import UserRepository
from backend.app.services.auth import AuthService

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
    with the existing route handler of that name in ``backend/app/api/auth.py``.
    """
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    user = await service.get_current_user(
        raw_token, session_ttl=settings.session_ttl_seconds
    )
    if user is None:
        raise http_error(401, AUTH_UNAUTHENTICATED, "Authentication required.")
    return user


CurrentUserDependency = Annotated[dict[str, Any], Depends(require_current_user)]
