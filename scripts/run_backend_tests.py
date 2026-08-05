"""Run the spoilerless backend test suite in 10 named chunks.

Why this exists
---------------
The full ``uv run pytest spoilerless/tests/`` run takes 15+ minutes, so
coding agents time out mid-run and broken backend code ships without being
caught (see docs/BACKEND_DEPLOY_FIX.md). This runner splits the suite into
10 named chunks and can launch them **in parallel** — total wall time then
tracks the slowest chunk, not the sum.

Critical environment note
-------------------------
The Hermes terminal exports ``PYTHONPATH`` pointing at the hermes-agent
package dir, which SHADOWS the venv and breaks ``import spoilerless``. This
runner strips ``PYTHONPATH`` from every child environment, so it works
regardless of the ambient shell.

Shared-DB warning
-----------------
Chunks run against the shared live AuraDB (root `.env`). Parallel execution
is safe for chunks whose tests do not re-seed the dexter graph or assert
exact global node counts; the ``seed_idempotency`` / ``setup_schema_check``
tests re-seed and assert exact counts, so prefer running those alone
(``--chunk 1``, ``--chunk 4``) before a parallel batch, or accept the
small race risk.

Usage
-----
    uv run python scripts/run_backend_tests.py            # all 10 chunks, sequential
    uv run python scripts/run_backend_tests.py --parallel # all 10 chunks at once
    uv run python scripts/run_backend_tests.py --list     # show chunks
    uv run python scripts/run_backend_tests.py --chunk 7  # one chunk by index
    uv run python scripts/run_backend_tests.py --chunk auth,graph  # a few
    uv run python scripts/run_backend_tests.py --chunk 7 -x -k foo  # extra pytest args

Exit code is non-zero if any chunk fails.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS = PROJECT_ROOT / "spoilerless" / "tests"

# 10 chunks — every test file appears exactly once. Names match the
# "Backend Tests — Break Up Strategy" table in docs/BACKEND_DEPLOY_FIX.md.
CHUNKS: dict[str, list[str]] = {
    "core": [
        "test_config.py",
        "test_deps.py",
        "test_database.py",
        "test_main_lifespan.py",
        "test_setup_schema_check.py",
        "test_ontology.py",
        "test_visibility.py",
        "test_series_service.py",
    ],
    "domain-models": [
        "test_revision_models.py",
        "test_user_content_models.py",
        "test_extraction_models.py",
        "test_episode_ordering.py",
        "test_episode_masking.py",
        "test_spoiler_policy.py",
        "test_conversational_tone.py",
        "test_s01e01_enrichment.py",
    ],
    "series-api": [
        "test_api_series.py",
        "test_progress_api.py",
    ],
    "graph": [
        "test_graph_api.py",
        "test_citations.py",
        "test_seed_idempotency.py",
    ],
    "change-set": [
        "test_change_set_api.py",
        "test_change_set_confirmation.py",
        "test_change_set_protection.py",
        "test_change_set_revision.py",
        "test_revisions.py",
    ],
    "candidates": [
        "test_candidate_ingest.py",
        "test_candidate_review.py",
    ],
    "auth": [
        "test_auth.py",
        "test_google_verifier.py",
        "test_session_repository.py",
        "test_settings_api.py",
    ],
    "user-content": [
        "test_user_content_api.py",
        "test_user_content_repository.py",
    ],
    "chat-llm": [
        "test_chat_api.py",
        "test_chat_persistence.py",
        "test_retrieval_pipeline.py",
        "test_retrieval_tools.py",
        "test_prompt_injection.py",
        "test_llm_provider.py",
    ],
    "contract-ops": [
        "test_frontend_contract_doc.py",
        "test_openapi_contract.py",
        "test_share_api.py",
        "test_error_handlers.py",
        "test_rate_limit.py",
    ],
}


def _chunk_files(names: list[str]) -> list[str]:
    return [str(TESTS / n) for n in names]


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # hermes terminal shadows the venv — see docstring
    return env


def _pytest_cmd(files: list[str], extra: list[str]) -> list[str]:
    return [sys.executable, "-m", "pytest", *_chunk_files(files), "-q", "--no-header", *extra]


def _run_chunk(name: str, files: list[str], extra: list[str]) -> tuple[int, float, str]:
    """Run one chunk synchronously; returns (exit_code, seconds, output_tail)."""
    start = time.monotonic()
    proc = subprocess.run(
        _pytest_cmd(files, extra),
        cwd=str(PROJECT_ROOT),
        env=_child_env(),
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - start
    tail = (proc.stdout or "").strip().splitlines()
    tail = tail[-25:] + (proc.stderr or "").strip().splitlines()[-5:]
    return proc.returncode, elapsed, "\n".join(tail)


def _spawn_chunk(name: str, files: list[str], extra: list[str]) -> subprocess.Popen:
    """Launch one chunk as a detached subprocess (parallel mode)."""
    return subprocess.Popen(
        _pytest_cmd(files, extra),
        cwd=str(PROJECT_ROOT),
        env=_child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _resolve_chunks(spec: str | None) -> list[str]:
    order = list(CHUNKS)
    if not spec:
        return order
    selected: list[str] = []
    for part in spec.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            if not 1 <= idx <= len(order):
                print(f"chunk index out of range: {part} (1..{len(order)})", file=sys.stderr)
                raise SystemExit(2)
            selected.append(order[idx - 1])
        elif part in CHUNKS:
            selected.append(part)
        else:
            print(f"unknown chunk: {part} — use --list", file=sys.stderr)
            raise SystemExit(2)
    # dedupe, keep order
    return list(dict.fromkeys(selected))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="show chunks and exit")
    parser.add_argument("--chunk", help="chunk(s) to run: index, name, or comma list")
    parser.add_argument("--parallel", action="store_true", help="launch all selected chunks at once")
    parser.add_argument("extra", nargs="*", help="extra args passed through to pytest")
    args = parser.parse_args()

    order = list(CHUNKS)
    if args.list:
        width = max(len(n) for n in order)
        for i, name in enumerate(order, 1):
            print(f"{i:>2}  {name:<{width}}  {', '.join(CHUNKS[name])}")
        return 0

    selected = _resolve_chunks(args.chunk)
    failures: list[str] = []
    started = time.monotonic()

    if args.parallel:
        procs = {name: _spawn_chunk(name, CHUNKS[name], args.extra) for name in selected}
        results: dict[str, tuple[int, float, str]] = {}
        remaining = dict(procs)
        while remaining:
            for name in list(remaining):
                code = remaining[name].poll()
                if code is not None:
                    out = remaining[name].stdout.read() if remaining[name].stdout else ""
                    elapsed = time.monotonic() - started
                    tail = "\n".join(out.strip().splitlines()[-25:])
                    results[name] = (code, elapsed, tail)
                    del remaining[name]
            time.sleep(0.5)
        for name in selected:
            code, seconds, tail = results[name]
            mark = "PASS" if code == 0 else "FAIL"
            print(f"[{mark}] {name} ({seconds:6.1f}s)")
            if code != 0:
                failures.append(name)
                print(f"----- {name} output tail -----")
                print(tail)
                print("-----------------------------")
    else:
        for name in selected:
            code, seconds, tail = _run_chunk(name, CHUNKS[name], args.extra)
            mark = "PASS" if code == 0 else "FAIL"
            print(f"[{mark}] {name} ({seconds:6.1f}s)")
            if code != 0:
                failures.append(name)
                print(f"----- {name} output tail -----")
                print(tail)
                print("-----------------------------")

    total = time.monotonic() - started
    print()
    if failures:
        print(f"FAILED chunks: {', '.join(failures)}")
        print(f"total wall time: {total:6.1f}s")
        return 1
    print(f"All {len(selected)} chunk(s) passed in {total:.1f}s wall time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
