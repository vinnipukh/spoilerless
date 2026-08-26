"""Shared FastAPI dependencies — auth service provider and current-user guard.

The auth dependency providers previously lived in ``spoilerless/app/api/auth.py``
and are re-exported from there for backward compatibility.  ``require_current_user``
is the ownership guard every new per-user resource router (progress, chat,
change_set) uses — it reads the session cookie and resolves the authenticated
``AppUser`` record server-side, exactly like the ``/api/auth/me`` route.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Depends, Request

from spoilerless.app.core.config import get_settings
from spoilerless.app.core.errors import http_error
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.repository.session import SessionRepository
from spoilerless.app.repository.share import ShareRepository
from spoilerless.app.repository.user import UserRepository
from spoilerless.app.services.auth import AuthService, ProductionGoogleVerifier
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService

AUTH_UNAUTHENTICATED = "AUTH_UNAUTHENTICATED"

DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


def get_graph_service(database: DatabaseDependency) -> GraphService:
    return GraphService(database)


def get_progress_service(database: DatabaseDependency) -> ProgressService:
    return ProgressService(database)


GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]



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
        # Explicit production verifier — AuthService has no silent fallback
        # (PROB-09/#77); a missed dependency now fails at startup.
        verifier=ProductionGoogleVerifier(),
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


def get_share_repo(request: Request, database: DatabaseDependency) -> ShareRepository:
    from spoilerless.app.repository.share import Neo4jShareRepository

    repo = getattr(request.app.state, "share_repo", None)
    if repo is not None:
        return repo
    return Neo4jShareRepository(database)


ShareRepoDependency = Annotated[ShareRepository, Depends(get_share_repo)]


# ---------------------------------------------------------------------------
# CSRF origin guard — shared by every cookie-authenticated state-changing
# route (moved here from api/auth.py so non-auth routers do not reach into
# the auth module; auth.py re-exports it for backward compatibility).
# ---------------------------------------------------------------------------
AUTH_ORIGIN_NOT_ALLOWED = "AUTH_ORIGIN_NOT_ALLOWED"


def _allowed_origins() -> list[str]:
    """Parse and return the configured frontend origins, stripping empties."""
    settings = get_settings()
    return [
        o.strip()
        for o in settings.frontend_origins.split(",")
        if o.strip()
    ]


async def verify_origin(request: Request) -> None:
    """Verify ``Origin`` (preferred) or ``Referer`` matches a configured
    frontend origin to protect state-changing requests against CSRF.

    The check is deliberately performed as a FastAPI dependency on each
    state-changing route (auth + every cookie-authenticated write) so it
    composes naturally with the existing dependency graph.  Reads
    ``FRONTEND_ORIGINS`` from config, so the same setting controls both
    CORS and CSRF validation.

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
            parsed = urlparse(referer)
            candidate = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port is not None:
                candidate += f":{parsed.port}"
        except Exception:
            candidate = None

    # Fail closed: a request with neither Origin nor Referer is rejected —
    # header absence is no longer trusted (SEC-02, docs/PROBLEMS.md #10).
    # Browsers send Origin on cross-origin and same-origin POSTs alike, so
    # a missing header signals a non-browser client; SameSite remains the
    # complementary cookie-level defense.
    if candidate is None:
        raise http_error(
            403, AUTH_ORIGIN_NOT_ALLOWED,
            "Request origin is not allowed.",
        )

    if candidate in origins:
        return

    raise http_error(
        403, AUTH_ORIGIN_NOT_ALLOWED,
        "Request origin is not allowed.",
    )


# The named dependency every state-changing cookie-authenticated route
# declares as ``_csrf`` (an underscore-ignored parameter) — one line per
# route, same semantics as the auth routes' original ``Depends(verify_origin)``.
CsrfGuardDependency = Annotated[None, Depends(verify_origin)]

