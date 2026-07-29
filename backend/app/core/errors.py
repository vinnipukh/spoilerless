from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import AuthError, ClientError, Neo4jError, ServiceUnavailable
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Stable machine-readable error code.",
        examples=["invalid_request"],
    )
    message: str = Field(
        min_length=1,
        max_length=500,
        description="Sanitized human-readable error message.",
        examples=["Request validation failed."],
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "detail": {
                        "code": "invalid_request",
                        "message": "Request validation failed.",
                    }
                }
            ]
        },
    )

    detail: ErrorDetail


_SAFE_ERRORS: tuple[type[BaseException], ...] = (
    ServiceUnavailable,
    AuthError,
    ClientError,
    Neo4jError,
)

_ERROR_SPECS: dict[int, tuple[str, str, str]] = {
    404: ("resource_not_found", "Resource not found.", "The resource was not found."),
    409: (
        "resource_conflict",
        "The request conflicts with the current resource state.",
        "The request conflicts with the current resource state.",
    ),
    422: ("invalid_request", "Request validation failed.", "The request is invalid."),
    503: (
        "database_unavailable",
        "The graph database is unavailable.",
        "The graph database is unavailable.",
    ),
}


def _envelope(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"detail": {"code": code, "message": message}}


def http_error(status_code: int, code: str, message: str) -> HTTPException:
    """Create an HTTPException using the one stable public error envelope."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def error_response(
    status_code: int,
    *,
    code: str | None = None,
    message: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Build a reusable FastAPI response declaration backed by ErrorResponse."""
    try:
        default_code, default_message, default_description = _ERROR_SPECS[status_code]
    except KeyError as exc:
        raise ValueError(f"Unsupported shared error response status: {status_code}") from exc

    resolved_code = code or default_code
    resolved_message = message or default_message
    return {
        "model": ErrorResponse,
        "description": description or default_description,
        "content": {
            "application/json": {
                "example": _envelope(resolved_code, resolved_message),
            }
        },
    }


def error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    """Return independent response declarations for common 404/409/422/503 errors."""
    return {status_code: deepcopy(error_response(status_code)) for status_code in status_codes}


def database_error_response(exc: BaseException) -> JSONResponse:
    unavailable = isinstance(exc, (ServiceUnavailable, AuthError, OSError))
    code = "database_unavailable" if unavailable else "database_error"
    message = (
        "The graph database is unavailable."
        if unavailable
        else "The graph database request could not be completed."
    )
    return JSONResponse(status_code=503, content=_envelope(code, message))


def request_validation_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_envelope("invalid_request", "Request validation failed."),
    )


def install_error_handlers(app: FastAPI) -> None:
    """Install sanitized validation and Neo4j handlers on a FastAPI application."""

    async def database_handler(_request: Request, exc: Exception) -> JSONResponse:
        return database_error_response(exc)

    async def validation_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return request_validation_error_response()

    app.add_exception_handler(RequestValidationError, validation_handler)
    for error_type in _SAFE_ERRORS:
        app.add_exception_handler(error_type, database_handler)


def install_database_error_handlers(app: FastAPI) -> None:
    """Backward-compatible installer name; installs the complete shared contract."""
    install_error_handlers(app)
