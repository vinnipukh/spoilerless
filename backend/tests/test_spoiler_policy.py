"""Unit tests for the central visibility-policy service (D-04).

``backend/app/spoiler/policy.py`` is the single owner of ``visible_from_order``
semantics and of the D-05 effective-boundary formula (contract:
``docs/SPOILER-TERMINOLOGY.md`` §6). These tests are pure — no database access —
exercising the fail-closed rule, the min-rule, the masking display shape, and
the invariant assertions.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app.spoiler.policy import (
    InvalidVisibilityOrder,
    ResourceHiddenError,
    assert_visibility_invariants,
    effective_view_order,
    filter_public_metadata,
    is_visible,
    mask_episode_metadata,
    require_visible_resource,
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
