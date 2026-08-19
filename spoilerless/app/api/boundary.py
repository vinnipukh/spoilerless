"""Shared async fail-closed boundary resolver for spoiler-sensitive reads.

D-01: EVERY spoiler-sensitive read route resolves its effective boundary
through this one function. Anonymous readers are FIXED at order 1; an
authenticated reader WITHOUT a persisted progress record is also fixed at
order 1 (fail closed, SEC-BE-001); an authenticated reader WITH a record is
clamped to min(requested, view_as_of, watched_through) via
policy.effective_view_order. The pure formula lives in spoiler/policy.py
(resolve_effective_boundary); this module adds the DB reads (progress record
+ persisted-episode validation) and the 422 envelope.
"""

from __future__ import annotations

from fastapi import HTTPException

from spoilerless.app.spoiler.policy import effective_view_order


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


async def resolve_effective_boundary(
    service,
    progress_service,
    series_id: str,
    user: dict | None,
    requested_order: int | None = None,
    *,
    boundary_label: str = "visible_until_order",
) -> int:
    """Resolve the effective boundary for a client request (D-01, fail closed).

    Mirrors the graph GET exactly: anonymous readers are FIXED at order 1
    (PROB-04/#12); authenticated readers without a persisted progress record
    are fixed at order 1 (SEC-BE-001 — the graph.py:124-140 clamp and the
    series.py:87-94 clamp are deleted in favor of this path); authenticated
    readers with a record get min(requested, view_as_of, watched_through).
    ``requested_order=None`` (no client-chosen boundary) resolves from
    persisted progress alone (PROB-09/#59). Every return value is validated
    to identify a persisted episode of the series (422 otherwise).
    """
    if user is None:
        requested = 1
    else:
        record = await progress_service.get(user["id"], series_id)
        if record is None:
            requested = 1  # fail closed: same read surface as anonymous
        elif requested_order is None:
            requested = effective_view_order(
                record.view_as_of_order, record.watched_through_order
            )
        else:
            requested_view = min(requested_order, record.view_as_of_order)
            requested = effective_view_order(
                requested_view, record.watched_through_order
            )
    boundary_episode = await service.resolve_boundary(series_id, requested)
    if boundary_episode is None:
        raise _error(
            422,
            "INVALID_VISIBLE_UNTIL_ORDER",
            f"{boundary_label} must identify a persisted episode order.",
        )
    return requested
