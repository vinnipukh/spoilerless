from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ConstraintError,
    Neo4jError,
    ServiceUnavailable,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# Canonical error-code registry (PROB-09/#20). Every code the API emits —
# the shared HTTP-status envelope below, route-level http_error() calls,
# the auth routes, and the LLM chat paths — must be listed here and match
# ^[A-Z][A-Z0-9_]*$. ErrorDetail validation AND the OpenAPI contract test
# both reference this set, so a future code that is unregistered (or a
# legacy lowercase code) fails fast instead of silently drifting.
ERROR_CODES: frozenset[str] = frozenset({
    # Shared HTTP-status envelope codes (see _ERROR_SPECS below)
    "UNAUTHENTICATED",
    "FORBIDDEN",
    "RESOURCE_NOT_FOUND",
    "RESOURCE_CONFLICT",
    "INVALID_REQUEST",
    "TOO_MANY_REQUESTS",
    "DATABASE_UNAVAILABLE",
    "DATABASE_ERROR",
    "CONSTRAINT_VIOLATION",
    # Route-level codes (api/graph.py, api/series.py, api/candidates.py,
    # api/change_set.py, api/revisions.py, api/progress.py, graph/candidates.py, api/share.py)
    "SERIES_NOT_FOUND",
    "INVALID_VISIBLE_UNTIL_ORDER",
    "INVALID_EXTRACTION_PAYLOAD",
    "CANDIDATE_NOT_FOUND",
    "CANNOT_APPROVE_NON_CANDIDATE",
    "CHANGESET_STALE",
    "INVALID_ACTION",
    "CANNOT_REVERT_CREATE",
    "CANNOT_REVERT_CANONICAL",
    "RESOURCE_ALREADY_EXISTS",
    "INGEST_ERROR",
    "TOKEN_NOT_FOUND",

    # Auth codes (api/auth.py)
    "AUTH_INVALID_GOOGLE_CREDENTIAL",
    "AUTH_UNAUTHENTICATED",
    "AUTH_SESSION_EXPIRED",
    "AUTH_SESSION_INVALID",
    "AUTH_ORIGIN_NOT_ALLOWED",
    "AUTH_EMAIL_NOT_ALLOWED",
    "AUTH_DISABLED",
    "AUTH_SERVICE_UNAVAILABLE",
    # LLM codes (api/chat.py, llm/provider.py)
    "LLM_DISABLED",
    "LLM_PROVIDER_UNAVAILABLE",
    "LLM_STREAM_FAILED",
})


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Stable machine-readable error code.",
        examples=["INVALID_REQUEST"],
    )
    message: str = Field(
        min_length=1,
        max_length=500,
        description="Sanitized human-readable error message.",
        examples=["Request validation failed."],
    )

    @field_validator("code")
    @classmethod
    def _code_must_be_registered(cls, value: str) -> str:
        """Reject codes outside the canonical registry (PROB-09/#20).

        Keeps the validation pattern and the registry in agreement: a code
        that matches the shape but is not registered fails here, so the
        contract cannot drift one code at a time.
        """
        if value not in ERROR_CODES:
            raise ValueError(
                f"code {value!r} is not in the canonical ERROR_CODES registry"
            )
        return value


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "detail": {
                        "code": "INVALID_REQUEST",
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
    401: ("UNAUTHENTICATED", "Authentication required.", "Authentication is required for this resource."),
    403: ("FORBIDDEN", "Forbidden.", "The request is forbidden."),
    404: ("RESOURCE_NOT_FOUND", "Resource not found.", "The resource was not found."),
    409: (
        "RESOURCE_CONFLICT",
        "The request conflicts with the current resource state.",
        "The request conflicts with the current resource state.",
    ),
    422: ("INVALID_REQUEST", "Request validation failed.", "The request is invalid."),
    429: (
        "TOO_MANY_REQUESTS",
        "Too many concurrent requests.",
        "The request was rejected because of a concurrency limit.",
    ),
    503: (
        "DATABASE_UNAVAILABLE",
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
    code = "DATABASE_UNAVAILABLE" if unavailable else "DATABASE_ERROR"
    message = (
        "The graph database is unavailable."
        if unavailable
        else "The graph database request could not be completed."
    )
    return JSONResponse(status_code=503, content=_envelope(code, message))


def request_validation_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_envelope("INVALID_REQUEST", "Request validation failed."),
    )


def install_error_handlers(app: FastAPI) -> None:
    """Install sanitized validation and Neo4j handlers on a FastAPI application."""

    async def constraint_handler(
        _request: Request, exc: ConstraintError
    ) -> JSONResponse:
        logger.error("constraint_error", exc_info=exc)
        return JSONResponse(
            status_code=409,
            content=_envelope(
                "CONSTRAINT_VIOLATION",
                "The request violates a database constraint.",
            ),
        )

    async def database_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("DATABASE_ERROR", exc_info=exc)
        return database_error_response(exc)

    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.error("validation_error", exc_info=exc)
        return request_validation_error_response()

    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(ConstraintError, constraint_handler)
    for error_type in _SAFE_ERRORS:
        app.add_exception_handler(error_type, database_handler)


def install_database_error_handlers(app: FastAPI) -> None:
    """Backward-compatible installer name; installs the complete shared contract."""
    install_error_handlers(app)
