"""Central visibility-policy service (D-04).

The single owner of ``visible_from_order`` semantics and of the D-05
effective-boundary formula. Every repository, service, retrieval tool, and API
route that decides visibility delegates to this module — the rule is never
reimplemented per query. Pure functions only, no database access (D-01), so the
module is trivially unit-testable. Contract:
``docs/architecture/spoiler-terminology.md`` §6 (written in 07-01).

Phase 10-02 adds the shared resolver :func:`resolve_effective_boundary` —
the one function every read channel (graph, visualization projection,
expansion, path, search/autocomplete, GraphRAG focus, saved restoration)
computes its effective boundary through (D-05/D-06).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "InvalidVisibilityOrder",
    "ResourceHiddenError",
    "assert_visibility_invariants",
    "effective_view_order",
    "filter_public_metadata",
    "is_visible",
    "mask_episode_metadata",
    "require_visible_resource",
    "resolve_effective_boundary",
    "validate_visibility_order",
]


class InvalidVisibilityOrder(ValueError):
    """An order outside the D-05 invariant (orders must be >= 1; persisted
    ``view_as_of_order`` must never exceed ``watched_through_order``)."""


class ResourceHiddenError(ValueError):
    """A story-sensitive resource is not visible at the effective boundary.

    Mapped to the API layer's generic hidden/404 envelope per D-15 — hidden
    and missing must be indistinguishable to the caller.
    """


# Spoiler-sensitive fields dropped by ``filter_public_metadata`` when the
# record is above the boundary. Hidden fields are ABSENT from responses
# (D-16), never returned masked or as placeholders.
_SPOILER_SENSITIVE_FIELDS = (
    "title",
    "synopsis",
    "runtime",
    "image_url",
    "image_source_url",
    "counts",
    "locator",
)


def _get(record: Any, field: str) -> Any:
    """Read a field from a dict-like or attribute-like record."""
    if isinstance(record, dict):
        return record.get(field)
    return getattr(record, field, None)


def validate_visibility_order(order: int) -> int:
    """Return ``order`` unchanged, or raise on ``order < 1``.

    The non-persisted-order check (an order that is not a real episode's
    global publication order in this series) lives in the calling service,
    which has database access; this function owns the numeric invariant only.

    PROB-16/#37: ``None`` is treated as INVALID input (raises the documented
    ``InvalidVisibilityOrder``, mapped to 422 by the API layer) — never a
    bare ``TypeError`` (which surfaces as an uncaught 500).
    """
    if order is None or order < 1:
        raise InvalidVisibilityOrder(
            f"Visibility order must be >= 1, got {order!r}."
        )
    return order


def is_visible(record: Any, effective_view_order: int) -> bool:
    """D-03 rule: True iff ``record.visible_from_order IS NOT NULL`` and
    ``record.visible_from_order <= effective_view_order``.

    FAILS CLOSED: a record with a null/missing ``visible_from_order`` returns
    False. Never applies ``coalesce(visible_from_order, 1)`` — a missing
    reveal point is hidden, never visible from order 1 (D-03).
    """
    visible_from_order = _get(record, "visible_from_order")
    if visible_from_order is None:
        return False
    return visible_from_order <= effective_view_order


def effective_view_order(view_as_of_order: int, watched_through_order: int) -> int:
    """D-05: return ``min(view_as_of_order, watched_through_order)``.

    Both inputs must be >= 1 (raise ``InvalidVisibilityOrder`` otherwise).
    The min rule is fail-closed: the effective boundary can never exceed the
    watched boundary even if a caller passes a higher view, and never exceeds
    the view boundary even when the user has watched further. Persisted
    records must additionally satisfy ``view <= watched`` — enforced by
    :func:`assert_visibility_invariants` on writes.
    """
    validate_visibility_order(view_as_of_order)
    validate_visibility_order(watched_through_order)
    return min(view_as_of_order, watched_through_order)


def resolve_effective_boundary(
    requested_view_order: int | None,
    watched_through_order: int | None,
    view_as_of_order: int | None = None,
) -> int:
    """D-05 shared boundary resolver: ``min(requested_view_order,
    watched_progress)``, fail closed.

    This is the single resolver every read channel computes its effective
    boundary through — graph reads, visualization projection, expansion,
    path/search, GraphRAG focus, and saved restoration (D-05). It makes the
    per-route boundary logic (``api/graph.py::_resolve_effective_boundary``)
    one pure function:

    - **No persisted progress** (``watched_through_order`` is None —
      anonymous reader or authenticated reader without a progress record):
      returns 1. A client-chosen order must never widen the spoiler window
      without a session (PROB-04/#12).
    - **Persisted progress, no client request**: the persisted view
      (``view_as_of_order``) IS the boundary — never a hop-count constant
      (PROB-09/#59).
    - **Both present**: ``min(requested, view)`` then ``min(..., watched)`` —
      the effective boundary can never exceed the watched boundary even when
      the caller requests more (fail-closed min, D-05).
    - **Missing ``view_as_of_order`` fails closed to order 1.**
    - Invalid orders raise :class:`InvalidVisibilityOrder` (sanitized; the
      API layer maps it to its generic 422 envelope).

    Hidden graph data — counts, degrees, groups, layout inputs, rankings,
    path existence, focus ids, restoration state — is never an input to this
    function, so it cannot influence the boundary (D-06).
    """
    if watched_through_order is None:
        return 1
    if requested_view_order is None:
        requested_view = view_as_of_order if view_as_of_order is not None else 1
    elif view_as_of_order is not None:
        requested_view = min(requested_view_order, view_as_of_order)
    else:
        requested_view = requested_view_order
    return effective_view_order(requested_view, watched_through_order)


def require_visible_resource(record: Any, effective_view_order: int) -> Any:
    """Raise :class:`ResourceHiddenError` when ``is_visible`` is False;
    otherwise return the record (safe to project)."""
    if not is_visible(record, effective_view_order):
        raise ResourceHiddenError(
            "Resource is not visible at the effective view boundary."
        )
    return record


def filter_public_metadata(record: Any, effective_view_order: int) -> dict[str, Any]:
    """Return the record's public projection.

    Spoiler-sensitive fields (title, synopsis, runtime, image_url,
    image_source_url, counts, locator) are DROPPED when the record is above
    the boundary (D-16: hidden fields are absent, never masked placeholders);
    below the boundary the projection is the record unchanged.
    """
    if isinstance(record, dict):
        result: dict[str, Any] = dict(record)
    else:
        result = {
            key: value
            for key, value in vars(record).items()
            if not key.startswith("_")
        }
    if not is_visible(record, effective_view_order):
        for field in _SPOILER_SENSITIVE_FIELDS:
            result.pop(field, None)
    return result


def _generic_episode_label(
    code: str | None, season_number: int | None, episode_number: int | None
) -> str:
    """D-08 generic label: the episode code and season/episode numbers stay
    visible so the episode remains selectable for the unlock flow; only the
    spoiler-sensitive title is replaced."""
    if code:
        return f"{code} — Episode {episode_number}"
    if season_number is not None and episode_number is not None:
        return f"S{season_number:02d}E{episode_number:02d} — Episode {episode_number}"
    return f"Episode {episode_number}"


def mask_episode_metadata(episode: Any, effective_view_order: int) -> dict[str, Any]:
    """Produce the D-21 display shape:

    ``{id, code, display_title, is_unlocked, is_current_view}``

    - ``display_title``: the generic ``'S01E05 — Episode 5'``-style label when
      the real title is spoiler-sensitive above the boundary (D-08) or missing
      (fail closed); the real title otherwise.
    - ``is_unlocked``: ``visible_from_order <= effective_view_order``.
    - ``is_current_view``: ``episode_order == effective_view_order``.
    """
    code = _get(episode, "code")
    season_number = _get(episode, "season_number")
    episode_number = _get(episode, "episode_number")
    episode_order = _get(episode, "episode_order")
    visible_from_order = _get(episode, "visible_from_order")
    title = _get(episode, "title")

    is_unlocked = (
        visible_from_order is not None
        and visible_from_order <= effective_view_order
    )
    if is_unlocked and title:
        display_title = title
    else:
        display_title = _generic_episode_label(code, season_number, episode_number)

    return {
        "id": _get(episode, "id"),
        "code": code,
        "display_title": display_title,
        "is_unlocked": is_unlocked,
        "is_current_view": episode_order == effective_view_order,
    }


def assert_visibility_invariants(record: Any) -> None:
    """Validate a record's own invariants and raise on violation.

    - ``visible_from_order`` is a positive int (or None).
    - On a progress-shaped record, ``1 <= view_as_of_order <=
      watched_through_order`` (D-05).
    """
    visible_from_order = _get(record, "visible_from_order")
    if visible_from_order is not None and visible_from_order < 1:
        raise InvalidVisibilityOrder(
            f"visible_from_order must be a positive int or None, got "
            f"{visible_from_order!r}."
        )
    view_as_of_order = _get(record, "view_as_of_order")
    watched_through_order = _get(record, "watched_through_order")
    if view_as_of_order is not None or watched_through_order is not None:
        validate_visibility_order(view_as_of_order)
        validate_visibility_order(watched_through_order)
        if view_as_of_order > watched_through_order:
            raise InvalidVisibilityOrder(
                f"view_as_of_order ({view_as_of_order}) must not exceed "
                f"watched_through_order ({watched_through_order})."
            )
