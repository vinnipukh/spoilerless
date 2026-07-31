"""Watch-progress persistence domain models (RAG-01).

The persisted ``UserSeriesProgress`` record is backend-authoritative: every
GraphRAG request resolves its spoiler boundary from this record server-side,
never from client input.  The boundary type is the existing
``VisibleUntilOrder`` Annotated type from ``backend/app/domain/user_content.py``
— never redefined here.
"""

from __future__ import annotations

from datetime import datetime

from backend.app.domain.user_content import (
    Identifier,
    StrictModel,
    UserResponseModel,
    VisibleUntilOrder,
)


class UserSeriesProgressResponse(UserResponseModel):
    """The persisted per-user, per-series watch-progress record."""

    id: Identifier
    user_id: Identifier
    series_id: Identifier
    visible_until_order: VisibleUntilOrder
    updated_at: datetime


class ProgressUpdateRequest(StrictModel):
    """Client-requested progress change.

    ``visible_until_order`` is the only accepted field (``extra=forbid``);
    the server derives ``user_id``/``series_id`` from the authenticated
    session and the URL path, never from the payload.
    """

    visible_until_order: VisibleUntilOrder
