from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from spoilerless.app.domain.graph import GraphEdge, GraphNode, GraphResponse
from spoilerless.app.domain.series import SeriesResponse
from spoilerless.app.domain.user_content import (
    CustomNodeCreate,
    CustomNodeResponse,
    CustomNodeType,
    CustomNodeUpdate,
    CustomRelationshipCreate,
    CustomRelationshipResponse,
    CustomRelationshipType,
    CustomRelationshipUpdate,
    NoteCreate,
    NoteResponse,
    NoteTargetType,
    NoteUpdate,
    Origin,
    VisibleUntilOrder,
)
from spoilerless.app.graph.ontology import ONTOLOGY_DIR, load_ontology


NOW = datetime(2026, 7, 29, 10, 0, tzinfo=timezone.utc)


def _enum_values(enum_type: type[StrEnum]) -> set[str]:
    return {member.value for member in enum_type}


def _yaml_groups(path: Path, key: str) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    return document[key]


def test_model_public_enums_are_exact_and_ontology_locked() -> None:
    ontology = load_ontology()
    node_groups = _yaml_groups(ONTOLOGY_DIR / "node_types.yaml", "node_types")
    relation_groups = _yaml_groups(ONTOLOGY_DIR / "relation_types.yaml", "relation_types")

    assert _enum_values(Origin) == {"canonical", "candidate", "user"}
    assert _enum_values(NoteTargetType) == {"Character", "Claim"}
    assert _enum_values(CustomNodeType) == {
        "Character",
        "Event",
        "Location",
        "Organization",
        "Object",
    }
    safe_relationships = set(relation_groups["participation"] + relation_groups["character"])
    assert _enum_values(CustomRelationshipType) == safe_relationships
    assert _enum_values(CustomRelationshipType) <= ontology.relationship_types
    assert _enum_values(CustomRelationshipType).isdisjoint(
        relation_groups["structural"]
        + relation_groups["provenance"]
        + relation_groups["revision"]
    )
    assert _enum_values(CustomNodeType) == set(node_groups["narrative"])
    assert _enum_values(NoteTargetType) <= ontology.node_types


def test_model_create_requests_accept_only_locked_fields() -> None:
    note = NoteCreate(target_type="Character", target_id="character:dexter", content="  note  ")
    node = CustomNodeCreate(
        node_type="Organization", label="  Miami Metro  ", episode_id="dexter:s01e01"
    )
    relationship = CustomRelationshipCreate(
        source_id="character:dexter",
        target_id="character:debra",
        predicate="FAMILY_OF",
        episode_id="dexter:s01e01",
    )

    assert note.content == "note"
    assert node.label == "Miami Metro"
    assert relationship.predicate is CustomRelationshipType.FAMILY_OF
    assert set(NoteCreate.model_fields) == {"target_type", "target_id", "content"}
    assert set(CustomNodeCreate.model_fields) == {"node_type", "label", "episode_id"}
    assert set(CustomRelationshipCreate.model_fields) == {
        "source_id",
        "target_id",
        "predicate",
        "episode_id",
    }
    for model in (NoteCreate, CustomNodeCreate, CustomRelationshipCreate):
        assert "properties" not in model.model_fields


@pytest.mark.parametrize(
    ("model", "valid", "forbidden_field", "forbidden_value"),
    [
        (
            NoteCreate,
            {"target_type": "Claim", "target_id": "claim:one", "content": "text"},
            "id",
            "user-note:chosen",
        ),
        (
            NoteCreate,
            {"target_type": "Claim", "target_id": "claim:one", "content": "text"},
            "visible_from_order",
            1,
        ),
        (
            CustomNodeCreate,
            {"node_type": "Character", "label": "Dexter", "episode_id": "episode:1"},
            "origin",
            "user",
        ),
        (
            CustomNodeCreate,
            {"node_type": "Character", "label": "Dexter", "episode_id": "episode:1"},
            "properties",
            {"unsafe": True},
        ),
        (
            CustomRelationshipCreate,
            {
                "source_id": "character:one",
                "target_id": "character:two",
                "predicate": "KNOWS",
                "episode_id": "episode:1",
            },
            "series_id",
            "series:dexter",
        ),
        (
            CustomRelationshipCreate,
            {
                "source_id": "character:one",
                "target_id": "character:two",
                "predicate": "KNOWS",
                "episode_id": "episode:1",
            },
            "created_at",
            NOW.isoformat(),
        ),
    ],
)
def test_model_create_requests_reject_server_owned_fields(
    model: type, valid: dict[str, object], forbidden_field: str, forbidden_value: object
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate({**valid, forbidden_field: forbidden_value})


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (NoteCreate, {"target_type": "Episode", "target_id": "episode:1", "content": "x"}),
        (
            CustomNodeCreate,
            {"node_type": "UserNote", "label": "x", "episode_id": "episode:1"},
        ),
        (
            CustomRelationshipCreate,
            {
                "source_id": "character:one",
                "target_id": "character:two",
                "predicate": "SUPPORTED_BY",
                "episode_id": "episode:1",
            },
        ),
    ],
)
def test_model_create_requests_reject_values_outside_public_allowlists(
    model: type, payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (NoteCreate, {"target_type": "Character", "target_id": "character:one", "content": "  "}),
        (NoteCreate, {"target_type": "Character", "target_id": "character:one", "content": "x" * 4001}),
        (CustomNodeCreate, {"node_type": "Event", "label": "  ", "episode_id": "episode:1"}),
        (CustomNodeCreate, {"node_type": "Event", "label": "x" * 201, "episode_id": "episode:1"}),
        (CustomRelationshipCreate, {"source_id": " ", "target_id": "b", "predicate": "KNOWS", "episode_id": "e"}),
    ],
)
def test_model_bounded_strings_reject_blank_or_oversized_values(
    model: type, payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "valid_payload", "immutable"),
    [
        (NoteUpdate, {"content": "changed"}, {"target_id": "character:two"}),
        (CustomNodeUpdate, {"label": "changed"}, {"node_type": "Event"}),
        (CustomRelationshipUpdate, {"predicate": "TRUSTS"}, {"source_id": "character:two"}),
    ],
)
def test_model_patch_contracts_reject_empty_null_and_immutable_fields(
    model: type, valid_payload: dict[str, object], immutable: dict[str, object]
) -> None:
    assert model.model_validate(valid_payload)
    with pytest.raises(ValidationError):
        model.model_validate({})
    field = next(iter(valid_payload))
    with pytest.raises(ValidationError):
        model.model_validate({field: None})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate({**valid_payload, **immutable})


def test_model_responses_are_graph_compatible_and_use_typed_origin() -> None:
    note = NoteResponse(
        id="user-note:one",
        series_id="series:dexter",
        target_type="Character",
        target_id="character:dexter",
        content="Remember this",
        origin="user",
        visible_from_order=1,
        created_at=NOW,
        updated_at=NOW,
    )
    node = CustomNodeResponse(
        id="user-node:one",
        series_id="series:dexter",
        type="Object",
        label="Blood slide",
        episode_id="episode:1",
        visible_from_order=1,
        origin="user",
        created_at=NOW,
        updated_at=NOW,
    )
    relationship = CustomRelationshipResponse(
        id="user-rel:one",
        series_id="series:dexter",
        source="character:dexter",
        target="user-node:one",
        type="TARGETED",
        episode_id="episode:1",
        visible_from_order=1,
        origin="user",
        created_at=NOW,
        updated_at=NOW,
    )

    assert note.origin is Origin.USER
    assert GraphNode.model_validate(node.model_dump()).origin is Origin.USER
    edge = GraphEdge.model_validate(relationship.model_dump())
    assert edge.origin is Origin.USER
    assert edge.claim_id is None


def test_model_responses_reject_unknown_origins_naive_datetimes_and_extras() -> None:
    base = {
        "id": "user-note:one",
        "series_id": "series:dexter",
        "target_type": "Character",
        "target_id": "character:dexter",
        "content": "text",
        "origin": "user",
        "visible_from_order": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    for changes in (
        {"origin": "curated"},
        {"created_at": datetime(2026, 7, 29, 10, 0)},
        {"is_custom": True},
    ):
        with pytest.raises(ValidationError):
            NoteResponse.model_validate({**base, **changes})


def test_model_visible_until_order_is_positive() -> None:
    from pydantic import TypeAdapter

    adapter = TypeAdapter(VisibleUntilOrder)
    assert adapter.validate_python(1) == 1
    for invalid in (0, -1):
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)


def test_model_graph_closure_still_rejects_user_dangling_edges() -> None:
    with pytest.raises(ValidationError, match="dangling edges"):
        GraphResponse(
            series=SeriesResponse(id="series:dexter", title="Dexter", slug="dexter"),
            visible_until_order=1,
            effective_view_order=1,
            nodes=[
                GraphNode(
                    id="user-node:one",
                    type="Character",
                    label="One",
                    visible_from_order=1,
                    origin="user",
                )
            ],
            edges=[
                GraphEdge(
                    id="user-rel:dangling",
                    source="user-node:one",
                    target="user-node:missing",
                    type="KNOWS",
                    visible_from_order=1,
                    origin="user",
                )
            ],
            claims=[],
            sources=[],
            evidence=[],
        )
