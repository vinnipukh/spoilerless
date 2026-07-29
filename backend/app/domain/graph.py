from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from backend.app.domain.series import SeriesResponse
from backend.app.domain.user_content import Origin


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    visible_from_order: int = Field(ge=1)
    origin: Origin
    episode_id: str | None = None
    image_url: str | None = None
    image_source_url: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    visible_from_order: int = Field(ge=1)
    origin: Origin
    claim_id: str | None = None


class GraphClaim(BaseModel):
    id: str
    label: str
    subject_id: str
    predicate: str
    object_id: str
    claim_type: str
    status: str
    confidence_level: str
    relationship_effect: float
    visible_from_order: int = Field(ge=1)
    valid_from_order: int | None = None
    valid_until_order: int | None = None
    source_id: str
    evidence_ids: list[str]
    origin: Origin


class GraphSource(BaseModel):
    id: str
    label: str
    episode_id: str
    source_type: str
    locator: str
    retrieved_at: str
    visible_from_order: int = Field(ge=1)
    origin: Origin


class GraphEvidence(BaseModel):
    id: str
    label: str
    episode_id: str
    source_id: str
    text: str
    locator: str
    content_hash: str
    visible_from_order: int = Field(ge=1)
    origin: Origin


class GraphResponse(BaseModel):
    series: SeriesResponse
    visible_until_order: int = Field(ge=1)
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    claims: list[GraphClaim]
    sources: list[GraphSource]
    evidence: list[GraphEvidence]

    @model_validator(mode="after")
    def enforce_graph_closure(self) -> "GraphResponse":
        node_ids = {node.id for node in self.nodes}
        dangling = [
            edge.id
            for edge in self.edges
            if edge.source not in node_ids or edge.target not in node_ids
        ]
        if dangling:
            raise ValueError(f"Graph contains dangling edges: {', '.join(dangling)}")
        return self


def model_records(model: type[BaseModel], rows: list[dict[str, Any]]) -> list[Any]:
    return [model.model_validate(row) for row in rows]
