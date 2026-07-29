from __future__ import annotations

import re
from pathlib import Path

from backend.app.main import app

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "frontend-api-contract.md"
HTTP_METHODS = {"get", "post", "patch", "delete", "put", "options", "head", "trace"}
EXPECTED_OPERATIONS = {
    ("get", "/health"),
    ("get", "/api/series"),
    ("get", "/api/series/{series_id}"),
    ("get", "/api/series/{series_id}/episodes"),
    ("get", "/api/series/{series_id}/graph"),
    ("post", "/api/series/{series_id}/notes"),
    ("get", "/api/series/{series_id}/notes"),
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
}
EXPECTED_TEMPLATES = {path for _, path in EXPECTED_OPERATIONS}


def _documented_operations(document: str) -> set[tuple[str, str]]:
    section = document.split("## Exact OpenAPI operation inventory", 1)[1].split("\n## ", 1)[0]
    return {
        (method.lower(), path)
        for method, path in re.findall(
            r"^\| (GET|POST|PATCH|DELETE) \| `([^`]+)` \|$", section, re.MULTILINE
        )
    }


def _openapi_operations() -> set[tuple[str, str]]:
    schema = app.openapi()
    return {
        (method, path)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    }


def test_document_and_openapi_have_exact_locked_inventory() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")
    documented = _documented_operations(document)
    generated = _openapi_operations()

    assert documented == EXPECTED_OPERATIONS
    assert generated == EXPECTED_OPERATIONS
    assert {path for _, path in documented} == EXPECTED_TEMPLATES
    assert set(app.openapi()["paths"]) == EXPECTED_TEMPLATES
    assert len(documented) == len(generated) == 18
    assert len(EXPECTED_TEMPLATES) == 11
    assert all("?" not in path for path in EXPECTED_TEMPLATES)


def test_document_locks_origins_boundaries_errors_and_compatibility() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")
    lower = document.lower()

    assert "canonical|candidate|user" in document
    assert "required positive integer" in lower
    assert "persisted episode order" in lower
    assert "fail-closed" in lower
    assert "hidden and missing direct reads are indistinguishable" in lower
    assert "no totals/counts" in lower
    assert "deterministic" in lower

    for status in ("404", "409", "422", "503"):
        assert status in document
    for code in (
        "series_not_found",
        "resource_not_found",
        "resource_conflict",
        "invalid_request",
        "invalid_visible_until_order",
        "database_unavailable",
    ):
        assert f"`{code}`" in document
    assert '{"detail":{"code":"resource_not_found","message":"Resource not found."}}' in document

    assert "## D-28 compatibility corrections" in document
    assert "required positive integer, not a nullable string" in lower
    assert "graph and series 404" in lower
    assert "database 503" in lower
    assert "health has typed 200 and 503" in lower
    assert "## PATCH boundary limitation" in document
    assert "D-09 conservative POST interpretation" in document


def test_document_has_examples_projection_rules_non_goals_and_pending_status() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")
    lower = document.lower()

    for marker in (
        "## UserNote routes and schemas",
        "## Custom-node routes and schemas",
        "## Custom-relationship routes and schemas",
        "Example hidden direct read",
        '"origin":"user"',
        '"node_type":"Object"',
        '"predicate":"FAMILY_OF"',
    ):
        assert marker in document
    assert "existing `GraphNode` shape" in document
    assert "existing `GraphEdge` shape exactly once" in document
    assert "not exposed as `GraphClaim`, `GraphSource`, or `GraphEvidence`" in document
    assert "both endpoints in `nodes`" in document
    assert "server owns ids" in lower
    assert "immutable" in lower
    assert "hard delete" in lower
    assert "dependency" in lower and "409" in document

    for non_goal in (
        "auth or permissions",
        "revisions",
        "soft delete",
        "rich text",
        "uploads",
        "collaboration",
        "llm/extraction",
        "moderation",
        "queues",
        "vector stores",
        "ontology expansion",
        "orm",
        "frontend implementation",
    ):
        assert non_goal in lower
    assert "react/cytoscape/frontend integration" in lower
    assert "distinct visual treatment" in lower
    assert "overall phase 03 completion" in lower
    assert "remain pending" in lower
    assert "frontend-work" in document
