from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

import yaml

ONTOLOGY_VERSION = "0.1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"


class OntologyValidationError(ValueError):
    pass


def _flatten(groups: dict[str, list[str]]) -> frozenset[str]:
    return frozenset(value for values in groups.values() for value in values)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise OntologyValidationError(f"Ontology file must contain a mapping: {path.name}")
    if value.get("ontology_version") != ONTOLOGY_VERSION:
        raise OntologyValidationError(
            f"Ontology version mismatch in {path.name}: expected {ONTOLOGY_VERSION}"
        )
    return value


@dataclass(frozen=True)
class Ontology:
    node_types: frozenset[str]
    relationship_types: frozenset[str]
    claim_types: frozenset[str]
    claim_statuses: frozenset[str]
    confidence_levels: frozenset[str]
    node_type_groups: Mapping[str, frozenset[str]]
    relationship_type_groups: Mapping[str, frozenset[str]]
    version: str = ONTOLOGY_VERSION

    @property
    def node_groups(self) -> Mapping[str, frozenset[str]]:
        return self.node_type_groups

    @property
    def relationship_groups(self) -> Mapping[str, frozenset[str]]:
        return self.relationship_type_groups

    @property
    def user_safe_relationship_types(self) -> frozenset[str]:
        return self.relationship_type_groups["participation"] | self.relationship_type_groups["character"]

    @property
    def user_safe_node_types(self) -> frozenset[str]:
        return frozenset({"Character", "Event", "Location", "Organization", "Object"})

    def require_node_type(self, value: str) -> None:
        self._require(value, self.node_types, "node type")

    def require_relationship_type(self, value: str) -> None:
        self._require(value, self.relationship_types, "relationship type")

    def require_claim_type(self, value: str) -> None:
        self._require(value, self.claim_types, "claim type")

    def require_claim_status(self, value: str) -> None:
        self._require(value, self.claim_statuses, "claim status")

    def require_confidence_level(self, value: str) -> None:
        self._require(value, self.confidence_levels, "confidence level")

    @staticmethod
    def _require(value: str, allowed: Iterable[str], kind: str) -> None:
        if value not in allowed:
            raise OntologyValidationError(f"Undeclared {kind}: {value}")


def load_ontology(directory: Path = ONTOLOGY_DIR) -> Ontology:
    nodes = _read_yaml(directory / "node_types.yaml")
    relationships = _read_yaml(directory / "relation_types.yaml")
    claims = _read_yaml(directory / "claim_types.yaml")
    node_groups = MappingProxyType(
        {name: frozenset(values) for name, values in nodes["node_types"].items()}
    )
    relationship_groups = MappingProxyType(
        {name: frozenset(values) for name, values in relationships["relation_types"].items()}
    )
    return Ontology(
        node_types=_flatten(nodes["node_types"]),
        relationship_types=_flatten(relationships["relation_types"]),
        claim_types=frozenset(claims["claim_types"]),
        claim_statuses=frozenset(claims["claim_statuses"]),
        confidence_levels=frozenset(claims["confidence_levels"]),
        node_type_groups=node_groups,
        relationship_type_groups=relationship_groups,
    )
