#!/usr/bin/env python3
"""Verify markdown link targets and GitHub-style anchor slugs in a doc set.

Usage:  python check-doc-links.py [file ...]
Default: the hdgrafcehennemi final-state doc set (roots + docs/ tree).
Checks that every relative ](...) target file exists and every #anchor slug
matches a heading in the target file (same-file and cross-file). Prints any
problems and exits 1; prints "N links checked" and exits 0 when clean.
Run from the repo root. Re-run after ANY docs edit (counts are baselines only).
"""
import os
import re
import sys


def gslug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def check(f: str, base: str):
    bad_files, bad_anchors = [], []
    with open(f, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    heads = {gslug(h) for h in re.findall(r"^#{1,6}\s+(.+)$", txt, re.M)}
    for m in re.finditer(r"\]\(([^)]*)\)", txt):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:", "javascript:")):
            continue
        path, _, anch = t.partition("#")
        target = os.path.normpath(os.path.join(base, path)) if path else f
        if not os.path.exists(target):
            bad_files.append(t)
            continue
        if not anch:
            continue
        if not path and gslug(anch) not in heads:
            bad_anchors.append((t, "same-file"))
            continue
        if path:
            if os.path.isdir(target):
                continue
            with open(target, encoding="utf-8", errors="replace") as th:
                theads = {gslug(h) for h in re.findall(r"^#{1,6}\s+(.+)$", th.read(), re.M)}
            if gslug(anch) not in theads:
                bad_anchors.append((t, "cross-file"))
    return bad_files, bad_anchors


def main(argv):
    files = argv or [
        "README.md",
        "CONTRIBUTING.md",
        "docs/README.md",
        "docs/API.md",
        "docs/ARCHITECTURE.md",
        "docs/CONFIGURATION.md",
        "docs/DEPLOYMENT.md",
        "docs/DEVELOPMENT.md",
        "docs/GETTING-STARTED.md",
        "docs/PROBLEMS.md",
        "docs/ROADMAP.md",
        "docs/TESTING.md",
        "docs/architecture/project-spec.md",
        "docs/architecture/spoiler-deferred-design.md",
        "docs/architecture/spoiler-terminology.md",
        "docs/architecture/spoiler-threat-model.md",
        "docs/reference/backend-modules.md",
        "docs/reference/frontend-api-contract.md",
        "docs/reference/frontend-components.md",
        "docs/ops/runbook.md",
    ]
    total, bad = 0, 0
    for f in files:
        base = os.path.dirname(f) or "."
        try:
            bf, ba = check(f, base)
        except FileNotFoundError:
            print(f"MISSING {f}")
            bad += 1
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            n = len(re.findall(r"\]\(([^)]*)\)", fh.read()))
        total += n
        if bf or ba:
            bad += 1
            print(f"{f}: broken_file_targets={bf} bad_anchors={ba}")
    print(f"{total} links checked across {len(files)} files, {bad} files with problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
