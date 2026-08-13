"""Unit tests for the Phase 10 multi-source coverage audit verifier.

Locks the fail-closed parsing contract of
``scripts/verify_phase10_coverage.py`` (10-11 Task 2): the machine-readable
coverage table is read only between the literal PHASE10-COVERAGE markers, the
header is exact, and duplicate/missing/extra/malformed rows, empty fields,
self-referencing evidence, and absent/duplicate markers are all rejected.
Mock-driven: no live files beyond the script itself.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verifier = _load_module(
    "verify_phase10_coverage", SCRIPTS_DIR / "verify_phase10_coverage.py"
)


def _table(rows: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "| source_id | plan_id | artifact_or_test | evidence_ref |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _document(block: str) -> str:
    return (
        "# Decision Log — Phase 10\n\n"
        "Some unrelated prose with a table:\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        f"{verifier.START_MARKER}\n{block}\n{verifier.END_MARKER}\n\n"
        "More unrelated prose after the block, including another table:\n\n"
        "| x | y |\n|---|---|\n| 3 | 4 |\n"
    )


def _all_rows() -> list[tuple[str, str, str, str]]:
    """One well-formed row per exact source id with distinct evidence refs."""
    rows = []
    for i, sid in enumerate(sorted(verifier.EXACT_SOURCE_IDS)):
        rows.append((sid, "10-11", f"artifact for {sid}", f"evidence:{i:03d}"))
    return rows


# ── Happy path ──────────────────────────────────────────────────────────────


def test_valid_block_maps_all_exact_source_ids() -> None:
    doc = _document(_table(_all_rows()))
    mapped, problems = verifier.verify_document(doc)
    assert problems == []
    assert mapped == len(verifier.EXACT_SOURCE_IDS) == 98


def test_markers_are_literal_and_table_is_delimited() -> None:
    rows = _all_rows()
    # Rows contain no marker-like text by construction; the parser must ignore
    # everything outside the markers, including other markdown tables.
    doc = _document(_table(rows))
    block, problems = verifier.extract_block(doc)
    assert problems == []
    assert block is not None
    assert verifier.START_MARKER not in block
    assert verifier.END_MARKER not in block
    assert "| a | b |" not in block  # unrelated table outside markers ignored
    assert "| x | y |" not in block


# ── Header handling ─────────────────────────────────────────────────────────


def test_missing_header_is_rejected() -> None:
    lines = ["| source_id | plan_id | artifact_or_test | evidence_ref |",
             "|---|---|---|---|"]
    lines = lines[1:]  # drop header; separator then data rows
    rows = _all_rows()
    body = "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows[:2]])
    doc = _document(body)
    mapped, problems = verifier.verify_document(doc)
    assert mapped == 0
    assert any("header" in p for p in problems)


def test_wrong_header_is_rejected() -> None:
    wrong = "| id | plan | artifact | ref |"
    rows = _all_rows()[:2]
    body = "\n".join([wrong, "|---|---|---|---|"] +
                     ["| " + " | ".join(r) + " |" for r in rows])
    doc = _document(body)
    _, problems = verifier.verify_document(doc)
    assert any("header" in p for p in problems)


# ── Duplicate / missing / extra ids ─────────────────────────────────────────


def test_duplicate_source_id_is_rejected() -> None:
    rows = _all_rows()
    rows.append(("REQ:VIZ-01", "10-11", "dup artifact", "evidence:999"))
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("duplicate" in p and "REQ:VIZ-01" in p for p in problems)


def test_missing_source_id_is_rejected() -> None:
    rows = [r for r in _all_rows() if r[0] != "REQ:VIZ-03"]
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("missing" in p and "REQ:VIZ-03" in p for p in problems)


def test_extra_unknown_source_id_is_rejected() -> None:
    rows = _all_rows()
    rows.append(("REQ:VIZ-99", "10-11", "not in inventory", "evidence:999"))
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("extra" in p and "REQ:VIZ-99" in p for p in problems)


# ── Malformed rows and fields ───────────────────────────────────────────────


def test_malformed_row_column_count_is_rejected() -> None:
    rows = _all_rows()
    rows.append(("REQ:VIZ-01", "10-11", "only three cells"))
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("malformed row" in p for p in problems)


def test_empty_field_is_rejected() -> None:
    rows = _all_rows()
    rows.append(("REQ:VIZ-01", "", "empty plan id", "evidence:999"))
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("empty field" in p for p in problems)


def test_evidence_ref_equal_to_source_id_is_rejected() -> None:
    rows = _all_rows()
    rows.append(("REQ:VIZ-01", "10-11", "self-referencing", "REQ:VIZ-01"))
    doc = _document(_table(rows))
    _, problems = verifier.verify_document(doc)
    assert any("evidence_ref equals source_id" in p for p in problems)


# ── Markers ─────────────────────────────────────────────────────────────────


def test_absent_markers_are_rejected() -> None:
    doc = "# No coverage block here\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    _, problems = verifier.verify_document(doc)
    assert any("START marker" in p for p in problems)
    assert any("END marker" in p for p in problems)


def test_duplicate_markers_are_rejected() -> None:
    block = _table(_all_rows())
    doc = (
        f"{verifier.START_MARKER}\n{block}\n{verifier.START_MARKER}\n{block}\n"
        f"{verifier.END_MARKER}\n"
    )
    _, problems = verifier.verify_document(doc)
    assert any("START marker must appear exactly once" in p for p in problems)
    # END appears exactly once here, so only START is flagged; a duplicate END
    # marker is covered by the symmetric case below.
    assert not any("END marker must appear exactly once" in p for p in problems)

    doc2 = (
        f"{verifier.START_MARKER}\n{block}\n{verifier.END_MARKER}\n{block}\n"
        f"{verifier.END_MARKER}\n"
    )
    _, problems2 = verifier.verify_document(doc2)
    assert any("END marker must appear exactly once" in p for p in problems2)


def test_reversed_marker_order_is_rejected() -> None:
    doc = (
        f"{verifier.END_MARKER}\n{_table(_all_rows())}\n{verifier.START_MARKER}\n"
    )
    _, problems = verifier.verify_document(doc)
    assert any("after END marker" in p for p in problems)


# ── CLI ─────────────────────────────────────────────────────────────────────


def test_cli_exit_codes(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text(_document(_table(_all_rows())), encoding="utf-8")
    assert verifier.main([str(good)]) == 0

    bad = tmp_path / "bad.md"
    bad.write_text(_document(_table(_all_rows())[:40]), encoding="utf-8")
    assert verifier.main([str(bad)]) == 1

    assert verifier.main([str(tmp_path / "missing.md")]) == 2
