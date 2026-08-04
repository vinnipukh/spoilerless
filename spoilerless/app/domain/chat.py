"""Chat session/message domain models (RAG-09, RAG-10).

The public response shape matches 06-CONTEXT.md's "Suggested public response
shape" exactly: ``{message, citations, graph_focus, proposed_change_set}``.
``citations``/``graph_focus`` are stored on the ``ChatMessage`` node as JSON
text properties (Neo4j node properties cannot hold nested objects) and are
deserialized at the repository boundary; the public models below are the wire
format both the SSE final event and the non-streaming endpoint return.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from spoilerless.app.domain.change_set import ChangeSetResponse
from spoilerless.app.domain.user_content import Identifier, StrictModel


class Citation(StrictModel):
    """A grounded citation referencing this turn's actually-retrieved context.

    Every ID is validated against the set of IDs the retrieval tools returned
    in this turn — hallucinated or remembered IDs are stripped by the pipeline
    before this model is ever built.
    """

    claim_id: str | None = None
    evidence_id: str | None = None
    source_id: str | None = None
    source_label: str
    source_type: str
    episode_code: str
    locator: str
    excerpt: str | None = None
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)


class GraphFocus(StrictModel):
    """Node/edge IDs the answer's citations reference, for graph highlighting."""

    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)


class ChatMessageResponse(StrictModel):
    id: Identifier
    role: str
    content: str
    created_at: datetime
    visible_until_order_snapshot: int = Field(
        ge=1,
        description="The exact persisted boundary used to generate this message.",
    )


class ChatSessionResponse(StrictModel):
    id: Identifier
    series_id: Identifier
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponseEnvelope(StrictModel):
    """The public response shape for one assistant turn (streamed or not)."""

    message: ChatMessageResponse
    citations: list[Citation] = Field(default_factory=list)
    graph_focus: GraphFocus = Field(default_factory=GraphFocus)
    proposed_change_set: ChangeSetResponse | None = None


class ChatSessionCreateRequest(StrictModel):
    title: str = Field(default='', max_length=200)


class ChatMessageCreateRequest(StrictModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatSessionDetailResponse(StrictModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse] = Field(default_factory=list)


# Re-exported for callers that need the raw dict shape of a done event.
ChatEventPayload = dict[str, Any]
