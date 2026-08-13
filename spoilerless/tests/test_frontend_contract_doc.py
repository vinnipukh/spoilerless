from __future__ import annotations

import re
from pathlib import Path

from spoilerless.app.main import app

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "reference" / "frontend-api-contract.md"
HTTP_METHODS = {"get", "post", "patch", "delete", "put", "options", "head", "trace"}
EXPECTED_OPERATIONS: set[tuple[str, str]] = {
    ("get", "/health"),
    ("get", "/api/series"),
    ("get", "/api/series/{series_id}"),
    ("get", "/api/series/{series_id}/episodes"),
    ("get", "/api/series/{series_id}/graph"),
    # User notes
    ("post", "/api/series/{series_id}/notes"),
    ("get", "/api/series/{series_id}/notes"),
    ("get", "/api/series/{series_id}/notes/{note_id}"),
    ("patch", "/api/series/{series_id}/notes/{note_id}"),
    ("delete", "/api/series/{series_id}/notes/{note_id}"),
    # Custom nodes
    ("post", "/api/series/{series_id}/custom-nodes"),
    ("get", "/api/series/{series_id}/custom-nodes/{node_id}"),
    ("patch", "/api/series/{series_id}/custom-nodes/{node_id}"),
    ("delete", "/api/series/{series_id}/custom-nodes/{node_id}"),
    # Custom relationships
    ("post", "/api/series/{series_id}/custom-relationships"),
    ("get", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
    ("patch", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
    ("delete", "/api/series/{series_id}/custom-relationships/{relationship_id}"),
    # Revisions
    ("get", "/api/series/{series_id}/revisions"),
    ("get", "/api/series/{series_id}/revisions/{revision_id}"),
    ("post", "/api/series/{series_id}/revisions/{revision_id}/revert"),
    # Candidate claims
    ("post", "/api/series/{series_id}/candidates/ingest"),
    ("get", "/api/series/{series_id}/candidates"),
    ("get", "/api/series/{series_id}/candidates/{claim_id}"),
    ("patch", "/api/series/{series_id}/candidates/{claim_id}"),
    ("post", "/api/series/{series_id}/candidates/{claim_id}/approve"),
    ("post", "/api/series/{series_id}/candidates/{claim_id}/reject"),
    # Chat sessions and watch progress (phase 06 GraphRAG chat)
    ("get", "/api/series/{series_id}/progress"),
    ("post", "/api/series/{series_id}/progress"),
    ("get", "/api/series/{series_id}/chat/sessions"),
    ("post", "/api/series/{series_id}/chat/sessions"),
    ("get", "/api/series/{series_id}/chat/sessions/{session_id}"),
    ("delete", "/api/series/{series_id}/chat/sessions/{session_id}"),
    ("post", "/api/series/{series_id}/chat/sessions/{session_id}/messages"),
    ("post", "/api/series/{series_id}/chat/sessions/{session_id}/messages/stream"),
    # ChangeSets (phase 06 graph-editing agent, Stage 1 propose + Stage 2
    # confirm/apply + Stage 3 revert)
    ("post", "/api/series/{series_id}/change-sets"),
    ("post", "/api/series/{series_id}/change-sets/{change_set_id}/confirm"),
    ("post", "/api/series/{series_id}/change-sets/{change_set_id}/reject"),
    ("post", "/api/series/{series_id}/change-sets/{change_set_id}/revert"),
    # Authentication
    ("post", "/api/auth/google"),
    ("get", "/api/auth/me"),
    ("post", "/api/auth/logout"),
    # Settings (LLM provider configuration)
    ("get", "/api/settings/llm"),
    ("put", "/api/settings/llm"),
    # Phase 9: Path, Export, Share
    ("post", "/api/series/{series_id}/graph/path"),
    ("get", "/api/series/{series_id}/export"),
    # Phase 10 (10-03): typed visualization projections (D-29)
    ("get", "/api/series/{series_id}/graph/visualization"),
    ("post", "/api/share"),
    ("get", "/api/share"),
    ("get", "/api/share/{token}/graph"),
    ("delete", "/api/share/{token}"),
}
EXPECTED_TEMPLATES = {path for _, path in EXPECTED_OPERATIONS}


def _documented_operations(document: str) -> set[tuple[str, str]]:
    section = document.split("## Exact OpenAPI operation inventory", 1)[1].split("\n## ", 1)[0]
    return {
        (method.lower(), path)
        for method, path in re.findall(
            r"^\| (GET|POST|PATCH|DELETE|PUT) \| `([^`]+)` \|$", section, re.MULTILINE
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
    assert len(documented) == len(generated) == 51
    assert len(EXPECTED_TEMPLATES) == 38
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
        "SERIES_NOT_FOUND",
        "RESOURCE_NOT_FOUND",
        "RESOURCE_CONFLICT",
        "INVALID_REQUEST",
        "INVALID_VISIBLE_UNTIL_ORDER",
        "DATABASE_UNAVAILABLE",
    ):
        assert f"`{code}`" in document
    assert '{"detail":{"code":"RESOURCE_NOT_FOUND","message":"Resource not found."}}' in document

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
        "passwords",
        "account linking",
        "refresh-token",
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
    # roles/permissions are no longer non-goals: UserPublic.role (admin|user),
    # ADMIN_EMAILS assignment, and admin gates (candidate approve/reject/edit,
    # ChangeSet confirm, LLM settings) are implemented (PROBLEMS #5/#14 —
    # refreshed TWELFTH-PASS contract; the doc asserts this positively).
    assert "Roles **are** implemented" in document
    assert "admin gates protect candidate approve/reject/edit" in document
    assert "react/cytoscape/frontend integration" in lower
    assert "distinct visual treatment" in lower
    assert "overall phase 03 completion" in lower
    assert "remain pending" in lower
    assert "frontend-work" in document
