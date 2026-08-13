from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from spoilerless.app.api.deps import (
    OptionalUserDependency,
    get_optional_current_user,
)
from spoilerless.app.cache.graph_cache import (
    get_cached_graph,
    get_cached_visualization,
    set_cached_graph,
    set_cached_visualization,
)
from spoilerless.app.domain.graph import (
    GraphResponse,
)
from spoilerless.app.core.errors import error_responses
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.domain.user_content import VisibleUntilOrder
from spoilerless.app.domain.visualization import (
    GRAPHRAG_FOCUS_VIEW_TYPE,
    PROJECTION_VERSION,
    VisualizationDTO,
)
from spoilerless.app.graph.database import Neo4jDatabase, get_database
from spoilerless.app.graph.ontology import load_ontology
from spoilerless.app.retrieval.tools import MAX_PATH_HOPS, find_path
from spoilerless.app.services.graph import GraphService
from spoilerless.app.services.progress import ProgressService
from spoilerless.app.services.visualization import VisualizationProjectionService
from spoilerless.app.spoiler.policy import InvalidVisibilityOrder, effective_view_order

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

# D-29: the exact view vocabulary of the visualization route. ``Literal``
# keeps the OpenAPI enum and the route's runtime validation in lockstep; the
# projection service additionally refuses unknown view types (fail closed).
VisualizationView = Literal[
    "episode_overview",
    "character_network",
    "plot_threads",
    "investigation",
    "full",
    "graphrag_focus",
]

# Stateless projection service; one shared instance per process.
_visualization_service = VisualizationProjectionService()


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
# 10-03 (D-29): typed read contract for the task-specific visualization
# projections. One route, six concrete views; the effective boundary resolves
# through the SAME shared block as graph/path/export (anonymous fixed at
# order 1, authenticated clamped by persisted progress — never a
# client-trusted order), the projection runs over the complete safe graph
# read, and cache-aside keys on every dimension a projection must not cross
# (series, effective order, view, projection version, user scope; D-30 adds
# the graph_revision epoch and focus signature in Task 2).
# ---------------------------------------------------------------------------

@router.get(
    "/{series_id}/graph/visualization",
    response_model=VisualizationDTO,
    summary="Read a typed spoiler-safe visualization projection",
    responses=error_responses(404, 422, 503),
)
async def get_visualization(
    series_id: str,
    view: VisualizationView,
    episode_order: int = Query(
        gt=0,
        description="Required positive episode order used as the requested "
        "spoiler boundary for the projection.",
    ),
    focus_id: list[str] = Query(
        default_factory=list,
        description="Optional repeated focus ids; accepted only for the "
        "graphrag_focus view and capped at 20 distinct ids.",
    ),
    service: GraphService = Depends(get_graph_service),
    progress_service: ProgressService = Depends(get_progress_service),
    user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> VisualizationDTO:
    """Read one typed visualization projection at the effective boundary.

    ``view`` selects one of six concrete projections (episode_overview,
    character_network, plot_threads, investigation, full, graphrag_focus).
    ``episode_order`` is the requested spoiler boundary — anonymous readers
    are fixed at order 1 (PROB-04/#12), authenticated readers are clamped to
    their persisted progress (D-05), and a boundary that does not identify a
    persisted episode is refused (422 ``INVALID_VISIBLE_UNTIL_ORDER``).
    """
    series = await service.get_series_meta(series_id)
    if series is None:
        raise _error(404, "SERIES_NOT_FOUND", "Series not found.")

    # D-29 focus contract: repeated focus_id values are accepted ONLY for
    # graphrag_focus (T10-FOCUS-02/03); the 20-id cap and hidden/unknown-id
    # rejection are enforced by the projection service below.
    if view != GRAPHRAG_FOCUS_VIEW_TYPE and focus_id:
        raise _error(
            422,
            "INVALID_REQUEST",
            "focus_id is only accepted for the graphrag_focus view.",
        )
    if view == GRAPHRAG_FOCUS_VIEW_TYPE and not focus_id:
        raise _error(
            422,
            "INVALID_REQUEST",
            "graphrag_focus requires at least one focus_id.",
        )

    effective = await _resolve_effective_boundary(
        service,
        progress_service,
        series_id,
        user,
        episode_order,
        boundary_label="episode_order",
    )

    # Cache-aside (D-30/T10-CACHE-02): the key carries series, effective
    # order, view, projection version, and user scope, and every cached DTO
    # is re-validated against its own metadata on read.
    user_id = user["id"] if user is not None else None
    cached = await get_cached_visualization(
        series_id, effective, view, PROJECTION_VERSION, user_id
    )
    if cached is not None:
        return VisualizationDTO.model_validate(cached)

    result = await service.fetch_graph(
        series_id,
        effective,
        node_labels=VISIBLE_NODE_LABELS,
        user_relationship_types=USER_RELATIONSHIP_TYPES,
        effective_view_order=effective,
    )
    try:
        dto = _visualization_service.project_view(result, view, focus_ids=focus_id)
    except InvalidVisibilityOrder as exc:
        # Hidden/unknown focus ids and hidden projection rows are client
        # request problems; sanitized, never echoing the offending id.
        raise _error(
            422,
            "INVALID_REQUEST",
            "The requested projection is not visible at the effective boundary.",
        ) from exc
    except ValueError as exc:
        raise _error(
            422,
            "INVALID_REQUEST",
            "The requested projection could not be produced.",
        ) from exc

    # Write-through on miss (best-effort; swallows Redis errors).
    await set_cached_visualization(
        series_id,
        effective,
        view,
        PROJECTION_VERSION,
        user_id,
        dto.model_dump(mode="json"),
    )
    return dto


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
    requested_order: int | None = None,
    *,
    boundary_label: str = "visible_until_order",
) -> int:
    """Resolve the effective boundary for a client request.

    Mirrors the graph GET exactly: anonymous readers are FIXED at order 1
    (PROB-04/#12); authenticated readers are clamped to their persisted
    progress. ``requested_order=None`` (no client-chosen boundary — e.g. the
    path route) resolves the boundary from persisted progress alone, never
    from a hop-count constant (PROB-09/#59). Returns the effective order.
    """
    if user is None:
        requested = 1
        boundary_episode = await service.resolve_boundary(series_id, requested)
        if boundary_episode is None:
            raise _error(
                422,
                "INVALID_VISIBLE_UNTIL_ORDER",
                f"{boundary_label} must identify a persisted episode order.",
            )
        return requested

    record = await progress_service.get(user["id"], series_id)
    if record is None:
        # No persisted progress: fail closed to the same read surface an
        # anonymous visitor gets (boundary 1), never an unbounded guess.
        requested = 1
        boundary_episode = await service.resolve_boundary(series_id, requested)
        if boundary_episode is None:
            raise _error(
                422,
                "INVALID_VISIBLE_UNTIL_ORDER",
                f"{boundary_label} must identify a persisted episode order.",
            )
        return requested

    if requested_order is None:
        # No client boundary: the persisted progress IS the boundary.
        effective = effective_view_order(
            record.view_as_of_order, record.watched_through_order
        )
    else:
        requested_view = min(requested_order, record.view_as_of_order)
        effective = effective_view_order(
            requested_view, record.watched_through_order
        )

    boundary_episode = await service.resolve_boundary(series_id, effective)
    if boundary_episode is None:
        raise _error(
            422,
            "INVALID_VISIBLE_UNTIL_ORDER",
            f"{boundary_label} must identify a persisted episode order.",
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

    # PROB-09/#59: no client-chosen boundary exists on this route, so the
    # effective boundary resolves from persisted progress alone — never from
    # the MAX_PATH_HOPS hop constant (which would clamp every authenticated
    # reader to order 4).
    effective = await _resolve_effective_boundary(
        service, progress_service, series_id, user
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
