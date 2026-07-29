from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.errors import (
    ErrorResponse,
    error_responses,
    http_error,
    install_error_handlers,
)


class _StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(gt=0, examples=[1])


def assert_error_envelope(payload: dict[str, Any], *, code: str, message: str) -> None:
    assert payload == {"detail": {"code": code, "message": message}}


def assert_error_response_reference(
    schema: dict[str, Any], *, path: str, method: str, status_code: int
) -> None:
    response = schema["paths"][path][method]["responses"][str(status_code)]
    response_schema = response["content"]["application/json"]["schema"]
    assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}


def _contract_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.post(
        "/items",
        responses=error_responses(404, 409, 422, 503),
        summary="Create a contract item",
    )
    async def create_item(payload: _StrictPayload) -> dict[str, int]:
        return {"count": payload.count}

    @app.get("/missing", responses=error_responses(404))
    async def missing() -> None:
        raise http_error(404, "resource_not_found", "Resource not found.")

    return app


def test_error_response_schema_has_component_reference_and_examples() -> None:
    schema = _contract_app().openapi()

    assert "ErrorDetail" in schema["components"]["schemas"]
    assert "ErrorResponse" in schema["components"]["schemas"]
    for status_code in (404, 409, 422, 503):
        assert_error_response_reference(
            schema, path="/items", method="post", status_code=status_code
        )
        response = schema["paths"]["/items"]["post"]["responses"][str(status_code)]
        example = response["content"]["application/json"]["example"]
        ErrorResponse.model_validate(example)
        assert set(example) == {"detail"}
        assert set(example["detail"]) == {"code", "message"}


def test_validation_error_uses_stable_sanitized_envelope() -> None:
    client = TestClient(_contract_app())
    secret = "private-rejected-value"

    response = client.post("/items", json={"count": 0, "unexpected": secret})

    assert response.status_code == 422
    assert_error_envelope(
        response.json(), code="invalid_request", message="Request validation failed."
    )
    assert secret not in response.text
    assert "input" not in response.text.lower()
    assert not isinstance(response.json()["detail"], list)


def test_validation_error_sanitizes_malformed_json_without_echoing_input() -> None:
    secret = "private-malformed-value"
    response = TestClient(_contract_app()).post(
        "/items",
        content=f'{{"count": "{secret}"',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert_error_envelope(
        response.json(), code="invalid_request", message="Request validation failed."
    )
    assert secret not in response.text


def test_http_error_uses_exact_runtime_envelope() -> None:
    response = TestClient(_contract_app()).get("/missing")

    assert response.status_code == 404
    assert_error_envelope(
        response.json(), code="resource_not_found", message="Resource not found."
    )
