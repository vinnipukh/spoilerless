"""Direct unit tests for the ontology loader (PROB-18/#40).

Covers the 09-05 ``lru_cache`` behavior (same object across calls, no
re-read) and the import-time crash protection for a missing/version-mismatched
ontology directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spoilerless.app.graph.ontology import (
    ONTOLOGY_DIR,
    Ontology,
    OntologyValidationError,
    load_ontology,
)


def test_load_ontology_returns_expected_structure() -> None:
    ontology = load_ontology(ONTOLOGY_DIR)
    assert isinstance(ontology, Ontology)
    assert "Character" in ontology.node_types
    assert "Character" in ontology.user_safe_node_types
    assert ontology.node_type_groups["narrative"] & {"Character", "Event", "Location"}
    assert ontology.relationship_types  # non-empty
    assert ontology.claim_types
    assert ontology.claim_statuses
    assert ontology.confidence_levels


def test_load_ontology_is_cached_single_object() -> None:
    # 09-05 added @lru_cache: two calls return the SAME object — the YAML is
    # parsed once, never re-read per call.
    first = load_ontology(ONTOLOGY_DIR)
    second = load_ontology(ONTOLOGY_DIR)
    assert first is second


def test_load_ontology_missing_directory_raises() -> None:
    # Import-time crash protection: a missing ontology file must fail loudly
    # (FileNotFoundError from the path read — never a silent empty ontology).
    with pytest.raises(FileNotFoundError):
        load_ontology(Path("data/dexter/does-not-exist"))


def test_load_ontology_version_mismatch_raises(tmp_path: Path) -> None:
    import yaml

    bad_dir = tmp_path / "ontology"
    bad_dir.mkdir()
    (bad_dir / "node_types.yaml").write_text(
        yaml.safe_dump({"ontology_version": "0.0.0", "types": []}),
        encoding="utf-8",
    )
    with pytest.raises(OntologyValidationError, match="version mismatch"):
        load_ontology(bad_dir)


def test_ontology_require_guards() -> None:
    ontology = load_ontology(ONTOLOGY_DIR)
    ontology.require_node_type("Character")
    ontology.require_relationship_type("FAMILY_OF")
    with pytest.raises(OntologyValidationError):
        ontology.require_node_type("NotARealType")
