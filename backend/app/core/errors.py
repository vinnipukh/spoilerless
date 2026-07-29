from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import AuthError, ClientError, Neo4jError, ServiceUnavailable


_SAFE_ERRORS: tuple[type[BaseException], ...] = (
    ServiceUnavailable,
    AuthError,
    ClientError,
    Neo4jError,
)


def database_error_response(exc: BaseException) -> JSONResponse:
    unavailable = isinstance(exc, (ServiceUnavailable, AuthError, OSError))
    code = "database_unavailable" if unavailable else "database_error"
    message = (
        "The graph database is unavailable."
        if unavailable
        else "The graph database request could not be completed."
    )
    return JSONResponse(
        status_code=503,
        content={"detail": {"code": code, "message": message}},
    )


def install_database_error_handlers(app: FastAPI) -> None:
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return database_error_response(exc)

    for error_type in _SAFE_ERRORS:
        app.add_exception_handler(error_type, handler)
