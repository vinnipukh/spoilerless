from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.domain.revision import RevisionAction, RevisionResponse


NOW = datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc)


def test_revision_action_enum_values() -> None:
    assert RevisionAction.CREATED.value == "Created"
    assert RevisionAction.UPDATED.value == "Updated"
    assert RevisionAction.DELETED.value == "Deleted"
    assert RevisionAction.REVERTED.value == "Reverted"
    assert len(RevisionAction) == 4


def test_revision_response_construction() -> None:
    revision = RevisionResponse(
        id="revision:abc123",
        series_id="series:dexter",
        resource_type="UserNote",
        resource_id="user-note:2a1f4c7e",
        action=RevisionAction.CREATED,
        before=None,
        after={"id": "user-note:2a1f4c7e", "content": "Remember this.", "visible_from_order": 1},
        created_at=NOW,
        visible_from_order=1,
    )
    assert revision.id == "revision:abc123"
    assert revision.series_id == "series:dexter"
    assert revision.resource_type == "UserNote"
    assert revision.resource_id == "user-note:2a1f4c7e"
    assert revision.action is RevisionAction.CREATED
    assert revision.before is None
    assert revision.after == {"id": "user-note:2a1f4c7e", "content": "Remember this.", "visible_from_order": 1}
    assert revision.created_at == NOW
    assert revision.visible_from_order == 1


def test_revision_response_before_after_default_to_none() -> None:
    revision = RevisionResponse(
        id="revision:abc123",
        series_id="series:dexter",
        resource_type="UserNote",
        resource_id="user-note:2a1f4c7e",
        action=RevisionAction.UPDATED,
        created_at=NOW,
        visible_from_order=2,
    )
    assert revision.before is None
    assert revision.after is None


def test_revision_response_with_before_and_after() -> None:
    revision = RevisionResponse(
        id="revision:def456",
        series_id="series:dexter",
        resource_type="UserNote",
        resource_id="user-note:2a1f4c7e",
        action=RevisionAction.UPDATED,
        before={"id": "user-note:2a1f4c7e", "content": "Old content", "visible_from_order": 1},
        after={"id": "user-note:2a1f4c7e", "content": "New content", "visible_from_order": 1},
        created_at=NOW,
        visible_from_order=1,
    )
    assert revision.before == {"id": "user-note:2a1f4c7e", "content": "Old content", "visible_from_order": 1}
    assert revision.after == {"id": "user-note:2a1f4c7e", "content": "New content", "visible_from_order": 1}


def test_revision_response_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RevisionResponse(
            id="revision:abc",
            series_id="series:dexter",
            resource_type="UserNote",
            resource_id="user-note:1",
            action=RevisionAction.CREATED,
            created_at=NOW,
            visible_from_order=1,
            unknown_field=True,
        )


def test_revision_response_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="Datetime must include a UTC offset"):
        RevisionResponse(
            id="revision:abc",
            series_id="series:dexter",
            resource_type="UserNote",
            resource_id="user-note:1",
            action=RevisionAction.CREATED,
            created_at=datetime(2026, 7, 29, 10, 0),
            visible_from_order=1,
        )


@pytest.mark.parametrize("action", list(RevisionAction))
def test_revision_response_all_actions_valid(action: RevisionAction) -> None:
    revision = RevisionResponse(
        id="revision:test",
        series_id="series:dexter",
        resource_type="UserNote",
        resource_id="user-note:1",
        action=action,
        created_at=NOW,
        visible_from_order=1,
    )
    assert revision.action is action
