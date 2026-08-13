"""Verify the Phase 10 multi-source coverage audit table.

The machine-readable coverage table lives in
``docs/decision-logs/phase-10-visualization.md`` between the literal markers

    <!-- PHASE10-COVERAGE:START -->
    <!-- PHASE10-COVERAGE:END -->

The table maps every authoritative Phase 10 source item — the phase goal, the
13 VIZ/POLISH requirements, the 49 CONTEXT decisions (D-01..D-49), the 17
UI-SPEC items, the 8 RESEARCH items, the 5 PATTERNS items, and the 5
VALIDATION items — to the plan that delivered it, the artifact or test that
implements it, and a real evidence reference. The ``EXACT_SOURCE_IDS`` set is
the literal inventory from 10-11-PLAN.md Task 2: no inferred prefixes, no
document scraping. The parser reads only the delimited block, requires the
exact header ``source_id|plan_id|artifact_or_test|evidence_ref``, skips the
header and separator, and rejects duplicate IDs, missing/extra IDs, malformed
rows, empty fields, and an ``evidence_ref`` equal to its ``source_id``.

Usage::

    uv run python scripts/verify_phase10_coverage.py docs/decision-logs/phase-10-visualization.md

Exit code 0 when every source id is mapped exactly once with well-formed rows;
non-zero with a report otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

START_MARKER = "<!-- PHASE10-COVERAGE:START -->"
END_MARKER = "<!-- PHASE10-COVERAGE:END -->"

# Literal inventory from 10-11-PLAN.md Task 2 — the exact authoritative set.
EXACT_SOURCE_IDS: frozenset[str] = frozenset({
    "GOAL:PHASE-10",
    "REQ:VIZ-01", "REQ:VIZ-02", "REQ:VIZ-03", "REQ:VIZ-04", "REQ:VIZ-05",
    "REQ:VIZ-06", "REQ:VIZ-07", "REQ:VIZ-08", "REQ:VIZ-09", "REQ:VIZ-10",
    "REQ:POLISH-01", "REQ:POLISH-02", "REQ:POLISH-03",
    "DEC:D-01", "DEC:D-02", "DEC:D-03", "DEC:D-04", "DEC:D-05", "DEC:D-06",
    "DEC:D-07", "DEC:D-08", "DEC:D-09", "DEC:D-10", "DEC:D-11", "DEC:D-12",
    "DEC:D-13", "DEC:D-14", "DEC:D-15", "DEC:D-16", "DEC:D-17", "DEC:D-18",
    "DEC:D-19", "DEC:D-20", "DEC:D-21", "DEC:D-22", "DEC:D-23", "DEC:D-24",
    "DEC:D-25", "DEC:D-26", "DEC:D-27", "DEC:D-28", "DEC:D-29", "DEC:D-30",
    "DEC:D-31", "DEC:D-32", "DEC:D-33", "DEC:D-34", "DEC:D-35", "DEC:D-36",
    "DEC:D-37", "DEC:D-38", "DEC:D-39", "DEC:D-40", "DEC:D-41", "DEC:D-42",
    "DEC:D-43", "DEC:D-44", "DEC:D-45", "DEC:D-46", "DEC:D-47", "DEC:D-48",
    "DEC:D-49",
    "UI:DESIGN-SYSTEM", "UI:INFORMATION-ARCHITECTURE", "UI:COPYWRITING",
    "UI:VISUALS", "UI:COLOR", "UI:TYPOGRAPHY", "UI:SPACING",
    "UI:ACCESSIBILITY", "UI:INTERACTION",
    "UI:CONSIDERATION-ZERO-ONE-MANY", "UI:CONSIDERATION-LONG-TEXT",
    "UI:STATE-ROWS", "UI:ACCEPTANCE-EVIDENCE",
    "UI:BACKSTOP-OVERFLOW", "UI:BACKSTOP-MOBILE-INSPECTOR",
    "UI:BACKSTOP-RESPONSIVE", "UI:BACKSTOP-CYTOSCAPE-A11Y",
    "RESEARCH:FILE-MAP", "RESEARCH:ARCHITECTURE", "RESEARCH:DONT-HAND-ROLL",
    "RESEARCH:PITFALLS", "RESEARCH:VALIDATION", "RESEARCH:SECURITY",
    "RESEARCH:CONSTRAINTS", "RESEARCH:ASSUMPTIONS",
    "PATTERNS:FILE-CLASSIFICATION", "PATTERNS:ASSIGNMENTS",
    "PATTERNS:SHARED", "PATTERNS:PITFALLS", "PATTERNS:SAFETY",
    "VALIDATION:INFRASTRUCTURE", "VALIDATION:SAMPLING",
    "VALIDATION:PER-PLAN-MAP", "VALIDATION:MANUAL-ONLY", "VALIDATION:SIGN-OFF",
})

HEADER_CELLS = ("source_id", "plan_id", "artifact_or_test", "evidence_ref")

Row = tuple[str, str, str, str]


def extract_block(text: str) -> tuple[str | None, list[str]]:
    """Return (block_content, problems). Absent/duplicate markers are problems."""
    problems: list[str] = []
    if text.count(START_MARKER) != 1:
        problems.append(
            f"START marker must appear exactly once (found {text.count(START_MARKER)})"
        )
    if text.count(END_MARKER) != 1:
        problems.append(
            f"END marker must appear exactly once (found {text.count(END_MARKER)})"
        )
    if problems:
        return None, problems
    start = text.index(START_MARKER) + len(START_MARKER)
    end = text.index(END_MARKER)
    if start > end:
        problems.append("START marker appears after END marker")
        return None, problems
    return text[start:end], problems


def _cells(line: str) -> list[str]:
    parts = [cell.strip() for cell in line.split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def _is_separator(line: str) -> bool:
    cells = _cells(line)
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", c) for c in cells)


def parse_rows(block: str) -> tuple[list[Row], list[str]]:
    """Parse data rows from the block. Returns (rows, problems)."""
    problems: list[str] = []
    rows: list[Row] = []
    lines = [ln for ln in block.splitlines() if ln.strip()]

    if not lines:
        return [], ["coverage block is empty (no header)"]
    if _cells(lines[0]) != list(HEADER_CELLS):
        return [], [
            "first non-blank line must be the exact header "
            f"'| {' | '.join(HEADER_CELLS)} |' (got: {lines[0].strip()!r})"
        ]

    for line in lines[1:]:
        if _is_separator(line):
            continue  # the markdown table separator row
        cells = _cells(line)
        if len(cells) != 4:
            problems.append(f"malformed row (expected 4 columns, got {len(cells)}): {line.strip()!r}")
            continue
        if any(not c for c in cells):
            problems.append(f"empty field in row: {line.strip()!r}")
            continue
        rows.append((cells[0], cells[1], cells[2], cells[3]))
    return rows, problems


def validate(
    rows: list[Row], source_ids: frozenset[str] = EXACT_SOURCE_IDS
) -> list[str]:
    """Check the parsed rows against the exact inventory. Returns problems."""
    problems: list[str] = []
    present = [row[0] for row in rows]

    dupes = sorted({sid for sid in present if present.count(sid) > 1})
    if dupes:
        problems.append(f"duplicate source_id rows: {', '.join(dupes)}")

    missing = sorted(source_ids - set(present))
    if missing:
        problems.append(f"missing source ids ({len(missing)}): {', '.join(missing)}")

    extra = sorted(set(present) - source_ids)
    if extra:
        problems.append(f"extra/unknown source ids: {', '.join(extra)}")

    self_refs = [row[0] for row in rows if row[3] == row[0]]
    if self_refs:
        problems.append(f"evidence_ref equals source_id: {', '.join(self_refs)}")

    return problems


def verify_document(text: str) -> tuple[int, list[str]]:
    """Verify one document. Returns (mapped_count, problems)."""
    block, problems = extract_block(text)
    if problems:
        return 0, problems
    assert block is not None
    rows, parse_problems = parse_rows(block)
    problems.extend(parse_problems)
    if not problems:
        problems.extend(validate(rows))
    return len({row[0] for row in rows}), problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("doc", help="path to the decision-log markdown file")
    args = parser.parse_args(argv)

    path = Path(args.doc)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    mapped, problems = verify_document(text)
    total = len(EXACT_SOURCE_IDS)

    if problems:
        print(f"FAIL: {path} — {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK: {mapped}/{total} exact Phase 10 source ids mapped (goal, 13 requirements, "
          f"49 decisions, 17 UI items, 8 research items, 5 patterns items, 5 validation items).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
