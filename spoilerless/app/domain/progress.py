"""Watch-progress persistence domain models (RAG-01).

The persisted ``UserSeriesProgress`` record is backend-authoritative: every
GraphRAG request resolves its spoiler boundary from this record server-side,
never from client input.  The D-05 split (07-02) separates the confirmed
``watched_through_order`` from the temporary ``view_as_of_order``; the
``effective_view_order`` (min of the two, computed by the policy service) is
the boundary every consumer must use.  The boundary type is the existing
``VisibleUntilOrder`` Annotated type from ``spoilerless/app/domain/user_content.py``
— never redefined here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from spoilerless.app.domain.user_content import (
    Identifier,
    StrictModel,
    UserResponseModel,
    VisibleUntilOrder,
)


class UserSeriesProgressResponse(UserResponseModel):
    """The persisted per-user, per-series watch-progress record (D-21).

    ``visible_until_order`` is kept as a backward-compatible echo of the
    confirmed watched boundary (PROG-04); the D-05 split fields
    ``watched_through_order`` / ``view_as_of_order`` and the policy-computed
    ``effective_view_order`` are the authoritative boundary fields.
    """

    id: Identifier
    user_id: Identifier
    series_id: Identifier
    visible_until_order: VisibleUntilOrder
    watched_through_order: VisibleUntilOrder
    view_as_of_order: VisibleUntilOrder
    effective_view_order: VisibleUntilOrder
    updated_at: datetime


class ProgressUpdateRequest(StrictModel):
    """Client-requested progress change (D-06, PROG-01, PROG-04).

    ``extra=forbid``: the server derives ``user_id``/``series_id`` from the
    authenticated session and the URL path, never from the payload.  Exactly
    one of ``watched_through_order`` or the legacy ``visible_until_order``
    alias confirms progress (both map to the same semantics); sending
    ``view_as_of_order`` alone is a view-only change that must never lower
    ``watched_through_order`` (PROG-01).  ``view_as_of_order`` defaults to
    ``watched_through_order`` when omitted.
    """

    watched_through_order: VisibleUntilOrder | None = None
    view_as_of_order: VisibleUntilOrder | None = None
    visible_until_order: VisibleUntilOrder | None = Field(
        default=None,
        description=(
            "Deprecated alias of watched_through_order, kept for backward "
            "compatibility (PROG-04, D-21)."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_boundary_field(self) -> "ProgressUpdateRequest":
        watched = self.watched_through_order
        legacy = self.visible_until_order
        if watched is not None and legacy is not None:
            raise ValueError(
                "Provide either watched_through_order or the legacy "
                "visible_until_order, not both."
            )
        if watched is None and legacy is None and self.view_as_of_order is None:
            raise ValueError(
                "Provide watched_through_order (or the legacy "
                "visible_until_order) to confirm progress, or view_as_of_order "
                "alone for a view-only change."
            )
        return self
