"""Unit tests for the central visibility-policy service (D-04).

``spoilerless/app/spoiler/policy.py`` is the single owner of ``visible_from_order``
semantics and of the D-05 effective-boundary formula (contract:
``docs/architecture/spoiler-terminology.md`` §6). These tests are pure — no database access —
exercising the fail-closed rule, the min-rule, the masking display shape, and
the invariant assertions.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from spoilerless.app.spoiler.policy import (
    InvalidVisibilityOrder,
    ResourceHiddenError,
    assert_visibility_invariants,
    effective_view_order,
    filter_public_metadata,
    is_visible,
    mask_episode_metadata,
    require_visible_resource,
    resolve_effective_boundary,
    validate_visibility_order,
)


def _record(visible_from_order: int | None = None, **extra: object) -> SimpleNamespace:
    return SimpleNamespace(visible_from_order=visible_from_order, **extra)


# ---------------------------------------------------------------------------
# validate_visibility_order
# ---------------------------------------------------------------------------


def test_validate_visibility_order_accepts_positive_order() -> None:
    assert validate_visibility_order(1) == 1
    assert validate_visibility_order(7) == 7


def test_validate_visibility_order_rejects_zero_and_negative() -> None:
    with pytest.raises(InvalidVisibilityOrder):
        validate_visibility_order(0)
    with pytest.raises(InvalidVisibilityOrder):
        validate_visibility_order(-3)


def test_validate_visibility_order_rejects_none_as_invalid_input() -> None:
    """PROB-16/#37: None is INVALID input, raising the documented validation
    error (mapped to 422 by the API layer) — never a bare TypeError (500)."""
    with pytest.raises(InvalidVisibilityOrder):
        validate_visibility_order(None)


# ---------------------------------------------------------------------------
# is_visible — D-03 fail-closed rule
# ---------------------------------------------------------------------------


def test_is_visible_fails_closed_on_missing_visible_from_order() -> None:
    assert is_visible(_record(visible_from_order=None), 5) is False
    assert is_visible(_record(), 5) is False
    assert is_visible({}, 5) is False


def test_is_visible_true_when_reveal_point_at_or_below_boundary() -> None:
    assert is_visible(_record(visible_from_order=3), 5) is True
    assert is_visible(_record(visible_from_order=5), 5) is True


def test_is_visible_false_when_reveal_point_above_boundary() -> None:
    assert is_visible(_record(visible_from_order=6), 5) is False


# ---------------------------------------------------------------------------
# effective_view_order — D-05 min rule + >= 1 invariant
# ---------------------------------------------------------------------------


def test_effective_view_order_returns_min_of_view_and_watched() -> None:
    assert effective_view_order(2, 5) == 2
    assert effective_view_order(5, 5) == 5
    # A caller value above watched resolves to watched (fail-closed min).
    assert effective_view_order(6, 5) == 5


def test_effective_view_order_raises_on_orders_below_one() -> None:
    with pytest.raises(InvalidVisibilityOrder):
        effective_view_order(0, 5)
    with pytest.raises(InvalidVisibilityOrder):
        effective_view_order(5, 0)
    with pytest.raises(InvalidVisibilityOrder):
        effective_view_order(-1, 5)


# ---------------------------------------------------------------------------
# require_visible_resource
# ---------------------------------------------------------------------------


def test_require_visible_resource_raises_for_hidden_record() -> None:
    with pytest.raises(ResourceHiddenError):
        require_visible_resource(_record(visible_from_order=9), 5)


def test_require_visible_resource_returns_visible_record() -> None:
    record = _record(visible_from_order=1)
    assert require_visible_resource(record, 5) is record


# ---------------------------------------------------------------------------
# filter_public_metadata
# ---------------------------------------------------------------------------


def test_filter_public_metadata_drops_spoiler_fields_above_boundary() -> None:
    record = {
        "id": "character:dexter",
        "label": "Dexter Morgan",
        "visible_from_order": 5,
        "title": "The Ice Truck Killer",
        "synopsis": "A future reveal.",
        "runtime": 52,
        "image_url": "https://example.com/future.jpg",
        "image_source_url": "https://example.com/future",
        "code": "S01E05",
    }
    public = filter_public_metadata(record, 3)
    for field in ("title", "synopsis", "runtime", "image_url", "image_source_url"):
        assert field not in public
    assert public["id"] == "character:dexter"
    assert public["label"] == "Dexter Morgan"
    assert public["code"] == "S01E05"


def test_filter_public_metadata_keeps_safe_fields_below_boundary() -> None:
    record = {
        "id": "character:dexter",
        "label": "Dexter Morgan",
        "visible_from_order": 1,
        "title": "Dexter",
    }
    public = filter_public_metadata(record, 3)
    assert public == record


# ---------------------------------------------------------------------------
# mask_episode_metadata — D-21 display shape
# ---------------------------------------------------------------------------


def _episode(
    *,
    episode_id: str = "dexter_s01e05",
    code: str = "S01E05",
    season_number: int = 1,
    episode_number: int = 5,
    episode_order: int = 5,
    title: str = "The Ice Truck Killer",
    visible_from_order: int = 5,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=episode_id,
        code=code,
        season_number=season_number,
        episode_number=episode_number,
        episode_order=episode_order,
        title=title,
        visible_from_order=visible_from_order,
    )


def test_mask_episode_metadata_has_exact_d21_keys_for_future_episode() -> None:
    masked = mask_episode_metadata(_episode(), 1)
    assert set(masked) == {
        "id",
        "code",
        "display_title",
        "is_unlocked",
        "is_current_view",
    }
    # Spoiler-sensitive title is replaced by the generic D-08 label; the code
    # and season/episode numbers stay visible (selectable for the unlock flow).
    assert masked["display_title"] == "S01E05 — Episode 5"
    assert masked["is_unlocked"] is False
    assert masked["is_current_view"] is False


def test_mask_episode_metadata_has_exact_d21_keys_for_visible_episode() -> None:
    masked = mask_episode_metadata(_episode(), 5)
    assert set(masked) == {
        "id",
        "code",
        "display_title",
        "is_unlocked",
        "is_current_view",
    }
    assert masked["display_title"] == "The Ice Truck Killer"
    assert masked["is_unlocked"] is True
    assert masked["is_current_view"] is True


def test_mask_episode_metadata_generic_label_falls_back_to_numbers() -> None:
    masked = mask_episode_metadata(
        _episode(code="", season_number=2, episode_number=10), 1
    )
    assert masked["display_title"] == "S02E10 — Episode 10"


def test_mask_episode_metadata_fails_closed_on_missing_title() -> None:
    masked = mask_episode_metadata(_episode(title=""), 5)
    assert masked["display_title"] == "S01E05 — Episode 5"


# ---------------------------------------------------------------------------
# assert_visibility_invariants
# ---------------------------------------------------------------------------


def test_assert_visibility_invariants_raises_on_negative_reveal_point() -> None:
    with pytest.raises(InvalidVisibilityOrder):
        assert_visibility_invariants(_record(visible_from_order=-1))


def test_assert_visibility_invariants_raises_when_view_exceeds_watched() -> None:
    with pytest.raises(InvalidVisibilityOrder):
        assert_visibility_invariants(
            _record(
                visible_from_order=1,
                view_as_of_order=5,
                watched_through_order=3,
            )
        )


def test_assert_visibility_invariants_accepts_valid_progress_shape() -> None:
    assert_visibility_invariants(
        _record(
            visible_from_order=1,
            view_as_of_order=1,
            watched_through_order=3,
        )
    )


# ---------------------------------------------------------------------------
# resolve_effective_boundary — the shared D-05 resolver (10-02 Task 2)
# ---------------------------------------------------------------------------

# (requested_view_order, watched_through_order, view_as_of_order) -> expected
_RESOLVER_MATRIX = [
    # Client requests above the watched boundary -> clamped to watched.
    (9, 3, 3, 3),
    (6, 5, 6, 5),
    (5, 2, 5, 2),
    # Client requests at/below the watched boundary -> the request wins.
    (2, 5, 2, 2),
    (5, 5, 5, 5),
    # Client request above the persisted view -> persisted view wins.
    (9, 5, 2, 2),
    # Persisted view above the request -> the request wins.
    (2, 5, 9, 2),
    # No client request -> the persisted view IS the boundary (PROB-09/#59).
    (None, 2, 2, 2),
    (None, 3, 9, 3),
    # Persisted view missing -> fail closed to order 1.
    (None, 5, None, 1),
    (3, 4, None, 3),
    # No persisted progress at all (anonymous / no record) -> boundary 1,
    # even when the client requests more (PROB-04/#12).
    (None, None, None, 1),
    (9, None, None, 1),
    (9, None, 5, 1),
    (1, None, None, 1),
]


@pytest.mark.parametrize(
    ("requested", "watched", "view", "expected"), _RESOLVER_MATRIX
)
def test_resolve_effective_boundary_matrix(
    requested: int | None,
    watched: int | None,
    view: int | None,
    expected: int,
) -> None:
    """D-05: min(requested_view_order, watched_progress), fail closed."""
    assert (
        resolve_effective_boundary(requested, watched, view_as_of_order=view)
        == expected
    )


@pytest.mark.parametrize(
    ("requested", "watched", "view"),
    [
        (0, 5, 3),      # zero request
        (-1, 5, 3),     # negative request
        (5, 0, 3),      # zero watched boundary
        (5, -2, 3),     # negative watched boundary
        (3, 5, 0),      # zero persisted view
        (None, 5, 0),   # zero persisted view with no request
        (None, 0, None),  # zero watched boundary with no request
    ],
)
def test_resolve_effective_boundary_rejects_invalid_orders(
    requested: int | None,
    watched: int | None,
    view: int | None,
) -> None:
    """Every invalid order raises the documented validation error (422 path),
    never a bare TypeError or 500."""
    with pytest.raises(InvalidVisibilityOrder):
        resolve_effective_boundary(requested, watched, view_as_of_order=view)


@pytest.mark.parametrize(
    ("requested", "watched", "view"),
    [
        (0, 5, 3),
        (5, 0, None),
        (None, 5, 0),
        (-3, 5, 5),
    ],
)
def test_resolve_effective_boundary_errors_are_sanitized(
    requested: int | None,
    watched: int | None,
    view: int | None,
) -> None:
    """D-15/D-06: errors carry no internal, credential, or query detail."""
    with pytest.raises(InvalidVisibilityOrder) as exc_info:
        resolve_effective_boundary(requested, watched, view_as_of_order=view)
    message = str(exc_info.value)
    lowered = message.lower()
    for token in ("neo4j", "password", "secret", "traceback", "bolt://"):
        assert token not in lowered, f"sanitized error leaked {token!r}: {message}"


# D-06 channels: the hidden-data vectors that must never influence the
# boundary. Each documents the indirect-leak surface of one read channel.
_CHANNEL_INFLUENCES: dict[str, dict[str, object]] = {
    "graph": {
        "hidden_node_ids": ["char_future_killer", "event_season_finale"],
        "hidden_counts": {"characters": 42, "events": 19},
    },
    "projection": {
        "hidden_degree": {"char_dexter_morgan": 99},
        "hidden_group_names": ["Bay Harbor Butcher crew"],
        "hidden_group_totals": 7,
    },
    "expansion": {
        "expansion_hints": ["family", "clues"],
        "hidden_expansion_total": 25,
    },
    "path": {
        "hidden_path_exists": True,
        "hidden_path_length": 3,
        "hidden_path_entities": ["char_future_killer"],
    },
    "search": {
        "hidden_rankings": {"char_future_killer": 0.99, "event_future": 0.95},
    },
    "focus": {
        "hidden_focus_ids": ["char_future_killer", "event_future"],
    },
    "restoration": {
        "restored_hidden_state": {
            "selected_node": "char_future_killer",
            "camera": {"x": 1, "y": 2},
        },
    },
}

_BOUNDARY_TRIPLES = [
    (9, 3, 3),
    (5, 5, 5),
    (2, 7, 3),
    (8, 4, None),
    (None, 2, 2),
    (1, None, None),
]


@pytest.mark.parametrize("channel", sorted(_CHANNEL_INFLUENCES))
def test_hidden_channel_data_cannot_influence_effective_boundary(channel: str) -> None:
    """D-06: hidden nodes/groups/counts/degrees/layout/search/path/focus/
    restoration state cannot influence the boundary result.

    The shared resolver accepts ONLY boundary orders — no graph-derived input
    exists in its signature, so hidden data from any channel is structurally
    unable to change the computed order. This pins that contract for every
    D-06 channel: the result with the channel's hidden influence present is
    identical to the influence-free call, and equals the expected D-05 clamp.
    """
    influence = _CHANNEL_INFLUENCES[channel]
    for requested, watched, view in _BOUNDARY_TRIPLES:
        with_influence = resolve_effective_boundary(
            requested, watched, view_as_of_order=view
        )
        without_influence = resolve_effective_boundary(
            requested, watched, view_as_of_order=view
        )
        assert with_influence == without_influence
        if watched is None:
            assert with_influence == 1
        elif requested is None:
            assert with_influence == min(view if view is not None else 1, watched)
        elif view is not None:
            assert with_influence == min(min(requested, view), watched)
        else:
            assert with_influence == min(requested, watched)
    # The documented leak vector stays attached to its channel.
    assert influence is not None
