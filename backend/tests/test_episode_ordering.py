"""Publication-order + title-safety metadata tests (07-03 Task 1, D-08/D-09, VIS-02).

Locks the D-09 rules: the single stable global episode order is the numeric
``episode_order`` — never episode-code strings or season-number strings.
Also locks the D-08/META-03 seed-metadata contract: seeded episodes carry
``title_is_spoiler`` / ``title_visible_from_order``, and a future episode
missing title-safety metadata fails conservatively (treated as
spoiler-sensitive, generic label above the boundary).
"""

from __future__ import annotations

from typing import Any

from backend.app.graph.seed import load_seed_data
from backend.app.spoiler.policy import is_visible, mask_episode_metadata


def sort_by_publication_order(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """D-09: the ONE stable global order is numeric ``episode_order``.

    Deliberately ignores episode codes, season numbers, and any fictional
    chronology field — publication/release order is authoritative.
    """
    return sorted(episodes, key=lambda episode: episode["episode_order"])


def test_s01e09_ranks_below_s01e10_numerically() -> None:
    # String comparison of the codes would order S01E10 FIRST ("S01E10" >
    # "S01E09" lexically because '1' < '9' at the fourth char) — the D-09 rule
    # is numeric episode_order, so S01E09 must rank below S01E10.
    e09 = {"code": "S01E09", "season_number": 1, "episode_number": 9, "episode_order": 9}
    e10 = {"code": "S01E10", "season_number": 1, "episode_number": 10, "episode_order": 10}

    assert e10["code"] > e09["code"]  # string comparison disagrees
    assert e09["episode_order"] < e10["episode_order"]  # numeric authority
    ordered = sort_by_publication_order([e10, e09])
    assert [e["code"] for e in ordered] == ["S01E09", "S01E10"]


def test_season_end_ranks_below_next_season_start() -> None:
    season1_end = {
        "code": "S01E12",
        "season_number": 1,
        "episode_number": 12,
        "episode_order": 12,
    }
    season2_start = {
        "code": "S02E01",
        "season_number": 2,
        "episode_number": 1,
        "episode_order": 13,
    }

    assert season1_end["episode_order"] < season2_start["episode_order"]
    ordered = sort_by_publication_order([season2_start, season1_end])
    assert [e["code"] for e in ordered] == ["S01E12", "S02E01"]


def test_flashback_revealed_later_stays_hidden_until_reveal_order() -> None:
    # An event shown as a flashback in Episode 5 (fictional chronology
    # earlier) must stay hidden until 5 — never earlier (D-09).
    flashback_revealed_in_episode_5 = {"visible_from_order": 5}

    assert not is_visible(flashback_revealed_in_episode_5, 4)
    assert is_visible(flashback_revealed_in_episode_5, 5)
    assert is_visible(flashback_revealed_in_episode_5, 6)


def test_out_of_order_fictional_chronology_never_changes_reveal_order() -> None:
    # Episode 1 contains a flash-forward to a fictional day AFTER Episode 2's
    # events; reveal order still follows publication order (episode_order),
    # never the fictional timeline.
    episodes = [
        {"code": "S01E02", "episode_order": 2, "fictional_day": 1},
        {"code": "S01E01", "episode_order": 1, "fictional_day": 30},  # flash-forward
    ]

    ordered = sort_by_publication_order(episodes)
    assert [e["code"] for e in ordered] == ["S01E01", "S01E02"]
    # The out-of-order fictional chronology is preserved in the data but must
    # not influence reveal order:
    assert ordered[0]["fictional_day"] > ordered[1]["fictional_day"]
    assert ordered[0]["episode_order"] < ordered[1]["episode_order"]


def test_seed_episodes_carry_title_safety_metadata() -> None:
    episodes = {e["code"]: e for e in load_seed_data()["episodes"]}
    assert set(episodes) == {"S01E01", "S01E02", "S01E03"}

    for episode in episodes.values():
        assert isinstance(episode["title_is_spoiler"], bool)
        assert isinstance(episode["title_visible_from_order"], int)
        assert episode["title_visible_from_order"] >= 1
        # D-08: the synopsis/image reveal-point fields document the rule for
        # the (currently absent) synopsis/image fields.
        assert "synopsis_visible_from_order" in episode
        assert "image_visible_from_order" in episode

    assert episodes["S01E01"]["title_is_spoiler"] is False
    assert episodes["S01E01"]["title_visible_from_order"] == 1
    assert episodes["S01E02"]["title_is_spoiler"] is True
    assert episodes["S01E02"]["title_visible_from_order"] == 2
    assert episodes["S01E03"]["title_is_spoiler"] is True
    assert episodes["S01E03"]["title_visible_from_order"] == 3


def test_missing_title_safety_metadata_fails_conservatively() -> None:
    # META-03: a future episode with no title_is_spoiler is treated as
    # spoiler-sensitive — above the boundary it gets the generic D-08 label,
    # never the real title.
    future_episode = {
        "id": "dexter_s01e99",
        "code": "S01E99",
        "season_number": 1,
        "episode_number": 99,
        "episode_order": 99,
        "visible_from_order": 99,
        "title": "Spoiler Title",
    }

    masked = mask_episode_metadata(future_episode, 1)
    assert masked["display_title"] == "S01E99 — Episode 99"
    assert masked["is_unlocked"] is False

    # Once the boundary reaches the episode's reveal order the real title may
    # surface — but only then.
    unlocked = mask_episode_metadata(future_episode, 99)
    assert unlocked["display_title"] == "Spoiler Title"
    assert unlocked["is_unlocked"] is True
