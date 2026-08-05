"""Direct unit tests for SeriesService (PROB-18/#40).

Service-level masking rules are exercised with a fake database (no live
Neo4j); route-level anonymous-boundary behavior is covered in
test_api_series.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from spoilerless.app.services.series import SeriesService


class FakeDatabase:
    """Minimal fake: returns canned rows for the queries the service uses."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]:
        series_id = parameters.get("series_id")
        if series_id is None:
            return self._records  # SERIES_LIST_QUERY — no params
        if "PART_OF" in query:
            # SERIES_EPISODES_QUERY — episodes of the series.
            return [r for r in self._records if r.get("series_id") == series_id]
        # SERIES_BY_ID_QUERY — the series row itself.
        return [r for r in self._records if r.get("id") == series_id]


def _episode(order: int, title: str, visible_from_order: int) -> dict[str, Any]:
    return {
        "id": f"dexter_s01e0{order}",
        "series_id": "series_dexter",
        "episode_order": order,
        "season_number": 1,
        "episode_number": order,
        "code": f"S01E0{order}",
        "title": title,
        "visible_from_order": visible_from_order,
        "synopsis_visible_from_order": visible_from_order,
        "image_visible_from_order": visible_from_order,
    }


@pytest.mark.asyncio
async def test_list_series_returns_all() -> None:
    records = [
        {"id": "series_dexter", "title": "Dexter", "origin": "canonical"},
        {"id": "series_other", "title": "Other", "origin": "canonical"},
    ]
    service = SeriesService(FakeDatabase(records))  # type: ignore[arg-type]
    assert await service.list_series() == records


@pytest.mark.asyncio
async def test_get_series_found_and_missing() -> None:
    records = [{"id": "series_dexter", "title": "Dexter", "origin": "canonical"}]
    service = SeriesService(FakeDatabase(records))  # type: ignore[arg-type]
    found = await service.get_series("series_dexter")
    assert found is not None and found["id"] == "series_dexter"
    assert await service.get_series("series_missing") is None


@pytest.mark.asyncio
async def test_list_episodes_masks_future_titles() -> None:
    records = [
        _episode(1, "Dexter", 1),
        _episode(2, "Crocodile", 2),
        _episode(3, "Popping Cherry", 3),
    ]
    service = SeriesService(FakeDatabase(records))  # type: ignore[arg-type]

    at_one = await service.list_episodes("series_dexter", effective_view_order=1)
    assert at_one[0]["display_title"] == "Dexter"
    assert at_one[1]["display_title"] == "S01E02 — Episode 2"
    assert at_one[1]["is_unlocked"] is False
    assert at_one[2]["display_title"] == "S01E03 — Episode 3"
    # META-02: no synopsis/runtime/image fields synthesized above the boundary.
    for episode in at_one:
        assert "synopsis" not in episode
        assert "runtime_minutes" not in episode

    at_three = await service.list_episodes("series_dexter", effective_view_order=3)
    assert at_three[1]["display_title"] == "Crocodile"
    assert at_three[2]["display_title"] == "Popping Cherry"
    assert all(e["is_unlocked"] for e in at_three)


@pytest.mark.asyncio
async def test_list_episodes_without_boundary_returns_raw() -> None:
    records = [_episode(1, "Dexter", 1)]
    service = SeriesService(FakeDatabase(records))  # type: ignore[arg-type]
    raw = await service.list_episodes("series_dexter")
    assert raw == records  # no masking shape injected
