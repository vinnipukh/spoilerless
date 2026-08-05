from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from spoilerless.app.api.deps import OptionalUserDependency
from spoilerless.app.cache.graph_cache import (
    get_cached_graph,
    set_cached_graph,
)
from spoilerless.app.domain.graph import (
    GraphResponse,
)
from spoilerless.app.core.errors import error_responses
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.domain.user_content import VisibleUntilOrder
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.graph.ontology import load_ontology
from spoilerless.app.retrieval.tools import MAX_PATH_HOPS, find_path
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.spoiler.policy import effective_view_order

router = APIRouter(prefix="/api/series", tags=["graph"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
VISIBLE_NODE_LABELS = [
    "Series",
    "Episode",
    "Character",
    "Event",
    "Location",
    "Organization",
    "Object",
]
USER_RELATIONSHIP_TYPES = sorted(load_ontology().user_safe_relationship_types)


def get_graph_service(database: DatabaseDependency) -> GraphService:
    return GraphService(database)


def get_progress_service(database: DatabaseDependency) -> ProgressService:
    return ProgressService(database)


GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@router.get(
    "/{series_id}/graph",
    response_model=GraphResponse,
    summary="Read the spoiler-safe series graph",
    responses=error_responses(404, 422, 503),
)
async def get_graph(
    series_id: str,
    service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: VisibleUntilOrder,
) -> GraphResponse:
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "SERIES_NOT_FOUND", "Series not found.")

    # PROB-04/#12: the effective boundary for an ANONYMOUS reader is FIXED at
    # order 1 — a client-chosen visible_until_order must never widen the
    # spoiler window without a session. The persisted-episode check resolves
    # against the effective (not the requested) order, so an anonymous client
    # cannot even probe episode ids above boundary 1.
    requested = 1 if user is None else visible_until_order
    boundary_episode = await service.resolve_boundary(series_id, requested)
    if boundary_episode is None:
        raise _error(
            422,
            "INVALID_VISIBLE_UNTIL_ORDER",
            "visible_until_order must identify a persisted episode order.",
        )

    effective = requested
    if user is not None:
        record = await progress_service.get(user["id"], series_id)
        if record is not None:
            requested_view = min(visible_until_order, record.view_as_of_order)
            effective = effective_view_order(
                requested_view, record.watched_through_order
            )

    # Cache-aside (INFRA-02): check hit before the Neo4j query. The
    # cache key encodes the effective boundary + user_id, so a boundary
    # change is always a cache miss with no need to invalidate (T-08-06-02).
    user_id = user["id"] if user is not None else None
    cached = await get_cached_graph(series_id, effective, user_id)
    if cached is not None:
        return GraphResponse.model_validate(cached)

    result = await service.fetch_graph(
        series_id,
        effective,
        node_labels=VISIBLE_NODE_LABELS,
        user_relationship_types=USER_RELATIONSHIP_TYPES,
        effective_view_order=effective,
    )

    # Write-through on miss (best-effort; swallows Redis errors).
    await set_cached_graph(series_id, effective, user_id, result.model_dump(mode="json"))
    return result


# ---------------------------------------------------------------------------
# FEAT-06 / FEAT-05 backend (plan 09-11): shared boundary resolution, the
# shortest-path POST, and the Markdown-only export GET. Both routes resolve
# the boundary through the SAME block the graph GET uses (effective_view_order
# with persisted progress — never client-trusted, T-09-11-01) and read
# through the single filtered read path (T-09-11-02).
# ---------------------------------------------------------------------------

async def _resolve_effective_boundary(
    service: GraphService,
    progress_service: ProgressService,
    series_id: str,
    user: dict | None,
    requested_order: int,
) -> int:
    """Resolve the effective boundary for a client request.

    Mirrors the graph GET exactly: anonymous readers are FIXED at order 1
    (PROB-04/#12); authenticated readers are clamped to their persisted
    progress. Returns the effective order.
    """
    requested = 1 if user is None else requested_order
    boundary_episode = await service.resolve_boundary(series_id, requested)
    if boundary_episode is None:
        raise _error(
            422,
            "INVALID_VISIBLE_UNTIL_ORDER",
            "visible_until_order must identify a persisted episode order.",
        )
    effective = requested
    if user is not None:
        record = await progress_service.get(user["id"], series_id)
        if record is not None:
            requested_view = min(requested_order, record.view_as_of_order)
            effective = effective_view_order(
                requested_view, record.watched_through_order
            )
    return effective


class PathRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    max_hops: int = Field(default=MAX_PATH_HOPS, ge=1, le=MAX_PATH_HOPS)


@router.post(
    "/{series_id}/graph/path",
    summary="Find the shortest visible path between two entities",
    responses=error_responses(404, 422, 503),
)
async def find_shortest_path(
    series_id: str,
    body: PathRequest,
    service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
) -> dict:
    """POST /graph/path — allowlisted find_path executor with server-injected
    params (no new retrieval logic, T-09-11-03: max_hops capped)."""
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "SERIES_NOT_FOUND", "Series not found.")

    effective = await _resolve_effective_boundary(
        service, progress_service, series_id, user, MAX_PATH_HOPS
    )
    result = await find_path(
        service._database,
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        max_hops=body.max_hops,
        series_id=series_id,
        visible_until_order=effective,
    )
    return result


@router.get(
    "/{series_id}/export",
    summary="Export the visible graph as Markdown (D-11)",
    responses=error_responses(404, 422, 503),
)
async def export_markdown(
    series_id: str,
    service: GraphServiceDependency,
    progress_service: ProgressServiceDependency,
    user: OptionalUserDependency,
    visible_until_order: VisibleUntilOrder = 1,
    target_id: str | None = None,
) -> PlainTextResponse:
    """GET /export — render Markdown from the SAME filtered read path
    (fetch_graph); never a second filter implementation."""
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "SERIES_NOT_FOUND", "Series not found.")

    effective = await _resolve_effective_boundary(
        service, progress_service, series_id, user, visible_until_order
    )
    graph = await service.fetch_graph(
        series_id,
        effective,
        node_labels=VISIBLE_NODE_LABELS,
        user_relationship_types=USER_RELATIONSHIP_TYPES,
        effective_view_order=effective,
    )
    markdown = _render_export_markdown(graph, target_id)
    filename = _export_filename(graph, target_id)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="' + filename + '"'},
    )


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "export"


def _export_filename(graph: GraphResponse, target_id: str | None) -> str:
    if target_id is not None:
        node = next((n for n in graph.nodes if n.id == target_id), None)
        label = _slugify(node.label) if node is not None else "node"
        return "spoilerless-" + label + ".md"
    slug = _slugify(graph.series.slug)
    return "spoilerless-" + slug + "-order-" + str(graph.visible_until_order) + ".md"


def _render_export_markdown(graph: GraphResponse, target_id: str | None) -> str:
    """Zero-dep Markdown assembler (D-11: Markdown-only export). Section order
    mirrors the frontend fallback renderer (exportMarkdown.ts)."""
    lines: list[str] = ["# " + graph.series.title, ""]
    if target_id is not None:
        node = next((n for n in graph.nodes if n.id == target_id), None)
        if node is None:
            return (
                lines[0]
                + "\n\n_Requested resource is not visible at the current boundary._\n"
            )
        lines.append("## " + node.label)
        lines.append("")
        lines.append("- Type: `" + node.type + "`")
        lines.append("- Visible from order: " + str(node.visible_from_order))
        lines.append("")
        _append_claims_for(lines, graph, target_id)
        return "\n".join(lines).rstrip() + "\n"

    # Whole-visible-graph export: episodes, then characters, then claims.
    episodes = [n for n in graph.nodes if n.type == "Episode"]
    if episodes:
        lines.append("## Episodes")
        lines.append("")
        for episode in episodes:
            lines.append("- " + episode.label)
        lines.append("")
    characters = [n for n in graph.nodes if n.type == "Character"]
    if characters:
        lines.append("## Characters")
        lines.append("")
        for character in characters:
            lines.append("- " + character.label)
        lines.append("")
    if graph.claims:
        lines.append("## Claims")
        lines.append("")
        for claim in graph.claims:
            lines.append("- **" + claim.label + "** (" + claim.predicate + ")")
            _append_evidence_for(lines, graph, claim)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _append_claims_for(lines: list[str], graph: GraphResponse, node_id: str) -> None:
    claims = [
        c for c in graph.claims if c.subject_id == node_id or c.object_id == node_id
    ]
    if not claims:
        lines.append("_No visible claims for this resource._")
        lines.append("")
        return
    lines.append("### Claims")
    lines.append("")
    for claim in claims:
        lines.append(
            "- **" + claim.label + "** (" + claim.predicate + ", " + claim.confidence_level + ")"
        )
        _append_evidence_for(lines, graph, claim)
    lines.append("")


def _append_evidence_for(lines: list[str], graph: GraphResponse, claim) -> None:
    """Append evidence fragments + source locators for a claim (D-11)."""
    evidence_by_id = {e.id: e for e in graph.evidence}
    sources_by_id = {s.id: s for s in graph.sources}
    for evidence_id in claim.evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            continue
        lines.append("  - Evidence: " + evidence.label)
        source = sources_by_id.get(evidence.source_id)
        if source is not None and source.locator:
            lines.append("    - Source: " + source.label + " — " + source.locator)
