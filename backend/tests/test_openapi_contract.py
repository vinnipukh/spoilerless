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


def test_user_route_openapi_has_exact_operations_and_templates() -> None:
    from backend.app.main import app

    schema = app.openapi()
    expected_paths = {
        "/health", "/api/series", "/api/series/{series_id}",
        "/api/series/{series_id}/episodes", "/api/series/{series_id}/graph",
        "/api/series/{series_id}/notes", "/api/series/{series_id}/notes/{note_id}",
        "/api/series/{series_id}/custom-nodes", "/api/series/{series_id}/custom-nodes/{node_id}",
        "/api/series/{series_id}/custom-relationships",
        "/api/series/{series_id}/custom-relationships/{relationship_id}",
        # Revisions
        "/api/series/{series_id}/revisions",
        "/api/series/{series_id}/revisions/{revision_id}",
        "/api/series/{series_id}/revisions/{revision_id}/revert",
        # Authentication
        "/api/auth/google", "/api/auth/me", "/api/auth/logout",
    }
    assert set(schema["paths"]) == expected_paths
    methods = {(method, path) for path, item in schema["paths"].items()
               for method in item if method in {"get", "post", "patch", "delete"}}
    assert methods == {
        ("get", "/health"), ("get", "/api/series"), ("get", "/api/series/{series_id}"),
        ("get", "/api/series/{series_id}/episodes"), ("get", "/api/series/{series_id}/graph"),
        ("post", "/api/series/{series_id}/notes"), ("get", "/api/series/{series_id}/notes"),
        ("get", "/api/series/{series_id}/notes/{note_id}"),
        ("patch", "/api/series/{series_id}/notes/{note_id}"),
        ("delete", "/api/series/{series_id}/notes/{note_id}"),
        ("post", "/api/series/{series_id}/custom-nodes"),
        ("get", "/api/series/{series_id}/custom-nodes/{node_id}"),
        ("patch", "/api/series/{series_id}/custom-nodes/{node_id}"),
        ("delete", "/api/series/{series_id}/custom-nodes/{node_id}"),
        ("post", "/api/series/{series_id}/custom-relationships"),
        ("get", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
        ("patch", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
        ("delete", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
        # Revisions
        ("get", "/api/series/{series_id}/revisions"),
        ("get", "/api/series/{series_id}/revisions/{revision_id}"),
        ("post", "/api/series/{series_id}/revisions/{revision_id}/revert"),
        ("post", "/api/auth/google"),
        ("get", "/api/auth/me"),
        ("post", "/api/auth/logout"),
    }
    assert len(schema["paths"]) == 17
    for path, item in schema["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "patch", "delete"}:
                continue
            if "custom-" not in path:
                continue
            for status in ("404", "422", "503"):
                if status in operation["responses"]:
                    assert_error_response_reference(schema, path=path, method=method, status_code=int(status))
    for path in (
        "/api/series/{series_id}/custom-nodes",
        "/api/series/{series_id}/custom-nodes/{node_id}",
        "/api/series/{series_id}/custom-relationships",
        "/api/series/{series_id}/custom-relationships/{relationship_id}",
    ):
        for method in paths_for_contract(schema, path):
            operation = schema["paths"][path][method]
            if method == "delete":
                assert operation["responses"]["204"].get("content") in (None, {})
            else:
                status = "201" if method == "post" else "200"
                assert operation["responses"][status]["content"]["application/json"]["schema"]["$ref"].startswith("#/components/schemas/")


def paths_for_contract(schema: dict[str, Any], path: str) -> list[str]:
    return [method for method in schema["paths"][path] if method in {"get", "post", "patch", "delete"}]


def test_user_route_openapi_shapes_enums_examples_and_positive_boundaries() -> None:
    from backend.app.main import app

    schema = app.openapi()
    paths = schema["paths"]
    for path, method in (
        ("/api/series/{series_id}/custom-nodes", "post"),
        ("/api/series/{series_id}/custom-nodes/{node_id}", "get"),
        ("/api/series/{series_id}/custom-relationships", "post"),
        ("/api/series/{series_id}/custom-relationships/{relationship_id}", "get"),
    ):
        operation = paths[path][method]
        assert "summary" in operation
        assert ("200" if method == "get" else "201") in operation["responses"]
    for path in paths:
        for method, operation in paths[path].items():
            if method not in {"get", "post", "patch", "delete"} or "custom-" not in path:
                continue
            if method == "delete":
                assert operation["responses"]["204"].get("content") in (None, {})
            if method == "get":
                boundary = next(p for p in operation["parameters"] if p["name"] == "visible_until_order")
                assert boundary["required"] is True
                assert boundary["schema"]["exclusiveMinimum"] == 0
                assert boundary["schema"].get("examples") == [1]
    assert schema["components"]["schemas"]["CustomNodeType"]["enum"] == ["Character", "Event", "Location", "Organization", "Object"]
    assert schema["components"]["schemas"]["CustomRelationshipType"]["enum"] == [
        "PARTICIPATED_IN", "WITNESSED", "CAUSED", "AFFECTED", "TARGETED", "MENTIONED",
        "KNOWS", "FAMILY_OF", "WORKS_WITH", "TRUSTS", "DISTRUSTS", "HELPS", "OPPOSES",
        "THREATENS", "ATTACKS", "KILLS",
    ]


def test_all_story_reads_graph_errors_health_and_deletes_are_fully_typed() -> None:
    from backend.app.main import app

    schema = app.openapi()
    story_reads = {
        ("/api/series/{series_id}/graph", "get"),
        ("/api/series/{series_id}/notes", "get"),
        ("/api/series/{series_id}/notes/{note_id}", "get"),
        ("/api/series/{series_id}/custom-nodes/{node_id}", "get"),
        ("/api/series/{series_id}/custom-relationships/{relationship_id}", "get"),
    }
    for path, method in story_reads:
        operation = schema["paths"][path][method]
        boundary = next(item for item in operation["parameters"] if item["name"] == "visible_until_order")
        assert boundary["required"] is True
        assert boundary["schema"]["type"] == "integer"
        assert boundary["schema"]["exclusiveMinimum"] == 0

    graph = schema["paths"]["/api/series/{series_id}/graph"]["get"]
    assert graph["summary"] == "Read the spoiler-safe series graph"
    assert graph["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/GraphResponse"
    }
    for status in (404, 422, 503):
        assert_error_response_reference(
            schema,
            path="/api/series/{series_id}/graph",
            method="get",
            status_code=status,
        )

    health = schema["paths"]["/health"]["get"]["responses"]
    assert health["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert health["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    for path, item in schema["paths"].items():
        if "delete" in item:
            assert item["delete"]["responses"]["204"].get("content") in (None, {})
