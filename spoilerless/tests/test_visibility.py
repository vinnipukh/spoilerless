"""Unit tests for the single shared visibility-derivation rule (PROB-25, #49).

These are pure-function tests (no DB) that pin the ONE rule both create paths
now call — the direct user-content API (``repository/user_content.py``'s custom
node create) and the ChangeSet apply path (``repository/change_set.py``'s five
create operations). If either path ever forks its own derivation again, the
integration suites (test_user_content_api, test_change_set_api) enforce
equality on live data; this file pins the rule's contract in isolation.
"""
from __future__ import annotations

import pytest

from spoilerless.app.spoiler.visibility import derive_visible_from_order


@pytest.mark.parametrize(
    ("episode_order", "current_progress", "expected"),
    [
        # max(episode order, current progress)
        (3, 1, 3),   # episode floor dominates (authored about a later episode)
        (1, 3, 3),   # progress floor dominates (authored while further along)
        (2, 2, 2),   # equal
        (5, 5, 5),
        # single-signal paths
        (4, None, 4),   # direct API custom node: episode order only, no progress
        (None, 4, 4),   # ChangeSet note: progress only, no episode signal
        # fail-closed to 1
        (None, None, 1),
        (0, 0, 1),          # non-positive inputs never yield 0/None
        (0, None, 1),
        (None, 0, 1),
    ],
)
def test_derive_visible_from_order(episode_order, current_progress, expected):
    assert derive_visible_from_order(episode_order, current_progress) == expected


def test_result_is_always_positive_int():
    for a in (None, 0, 1, 7):
        for b in (None, 0, 1, 7):
            result = derive_visible_from_order(a, b)
            assert isinstance(result, int)
            assert result >= 1
