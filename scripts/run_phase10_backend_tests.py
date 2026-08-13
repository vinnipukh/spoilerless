"""Guarded Phase 10 backend-test runner — the ONLY Phase 10 backend entrypoint.

Why this exists (POLISH-01 / T10-LEAK-09)
-----------------------------------------
Phase 10 closeout requires the full backend suite to run with **zero known
failures** against disposable data. The legacy default target (root ``.env``
AuraDB, or the developer container ``spoilerless-neo4j`` via
``scripts/env-local.sh``) is a shared/live database and must never receive
regression-test writes. This runner therefore:

1. **Provisions its own target**: a uniquely named ``neo4j:2026.06.0-community``
   container (the same pinned image as docker-compose and CI), with a random
   password and *no volume mounts* — Docker creates only anonymous volumes,
   which are removed at teardown.
2. **Refuses every forbidden target, fail-closed**, before creating anything:
   - ambient ``NEO4J_*``/``aura_*`` connection overrides (user-provided),
   - remote/Aura hosts (non-loopback URI),
   - the developer container port (``:7687``) and the running developer
     containers ``spoilerless-neo4j`` / ``hdgraf-neo4j``,
   - a pre-existing container or named volume with our generated name,
   - inconsistent alias-family values (the ``aura_*`` alias wins in
     ``Settings``; a bypass attempt must not redirect the run).
3. **Proves the target is its own container**: a settings+driver probe asserts
   the effective ``Settings`` (after both alias families resolve) equals the
   ephemeral credentials AND that the database holds 0 nodes before tests run.
4. **Exports both alias families** for children: uppercase ``NEO4J_*`` and
   lowercase ``aura_*`` (pydantic-settings matches env names case-insensitively;
   ``aura_*`` is the winning alias). ``PYTHONPATH`` is stripped so the ambient
   Hermes export can never shadow the venv.
5. **Always tears down**: ``docker rm -f -v <name>`` runs in ``finally`` —
   even when provisioning, seeding, or the tests fail — and the absence of the
   container afterwards is verified and printed.

Usage
-----
    uv run python scripts/run_phase10_backend_tests.py               # all chunks
    uv run python scripts/run_phase10_backend_tests.py --all         # explicit
    uv run python scripts/run_phase10_backend_tests.py --files \
        spoilerless/tests/test_graph_api.py spoilerless/tests/test_seed_idempotency.py
    uv run python scripts/run_phase10_backend_tests.py --files ... -- -k "not slow"

Exit codes: 0 all green, 1 test failures, 2 forbidden target / usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "spoilerless" / "tests"
CHUNK_RUNNER = PROJECT_ROOT / "scripts" / "run_backend_tests.py"
SETUP_MODULE = "spoilerless.app.graph.setup"

IMAGE = "neo4j:2026.06.0-community"
CONTAINER_PREFIX = "hdgraf-phase10-tests"
FORBIDDEN_CONTAINERS = {"spoilerless-neo4j", "hdgraf-neo4j"}
DEV_CONTAINER_PORT = 7687  # docker-compose developer container's bolt port
DATABASE = "neo4j"
USERNAME = "neo4j"

# Canonical connection env names (pydantic-settings matches case-insensitively;
# aura_* is the WINNING alias family in Settings AliasChoices).
NEO4J_VARS = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")
AURA_VARS = ("AURA_URI", "AURA_USERNAME", "AURA_PASSWORD", "AURA_DATABASE")
CONNECTION_VARS = NEO4J_VARS + AURA_VARS
URI_VARS = {"NEO4J_URI", "AURA_URI"}

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class TargetRefusal(Exception):
    """Fail-closed refusal: the requested target is forbidden or overridden."""


@dataclass(frozen=True)
class Target:
    """The ephemeral test target this runner owns and always destroys."""

    name: str
    image: str
    username: str
    password: str
    database: str
    bolt_port: int
    http_port: int

    @property
    def uri(self) -> str:
        return f"neo4j://127.0.0.1:{self.bolt_port}"

    @property
    def connection_map(self) -> dict[str, str]:
        """Effective values every child must resolve to for each env name."""
        return {
            "NEO4J_URI": self.uri,
            "NEO4J_USERNAME": self.username,
            "NEO4J_PASSWORD": self.password,
            "NEO4J_DATABASE": self.database,
            "AURA_URI": self.uri,
            "AURA_USERNAME": self.username,
            "AURA_PASSWORD": self.password,
            "AURA_DATABASE": self.database,
        }


# ── Pure helpers (unit-testable without docker) ─────────────────────────────


def _free_port() -> int:
    """Grab a currently-free loopback TCP port for the container mapping."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def compute_target() -> Target:
    """Generate a unique, disposable target; never a shared/developer name."""
    name = f"{CONTAINER_PREFIX}-{secrets.token_hex(6)}"
    if name in FORBIDDEN_CONTAINERS:
        raise TargetRefusal(f"generated container name {name!r} collides with a forbidden name")
    return Target(
        name=name,
        image=IMAGE,
        username=USERNAME,
        password=secrets.token_hex(16),
        database=DATABASE,
        bolt_port=_free_port(),
        http_port=_free_port(),
    )


def _env_get(env: dict[str, str], name: str) -> str | None:
    """Case-insensitive env lookup (pydantic-settings and Windows both are)."""
    wanted = name.lower()
    for key, value in env.items():
        if key.lower() == wanted:
            return value
    return None


def parse_neo4j_uri(uri: str) -> tuple[str, int]:
    """Parse ``neo4j://host:port`` variants; raises ValueError on garbage."""
    value = uri.strip()
    for scheme in ("neo4j+s://", "neo4j+ssc://", "neo4j://", "bolt+s://", "bolt://"):
        if value.startswith(scheme):
            value = value[len(scheme):]
            break
    host, _, port_part = value.partition(":")
    if not host:
        raise ValueError(f"unparseable Neo4j URI: {uri!r}")
    port = int(port_part) if port_part else 7687
    return host.strip("[]"), port


def _classify_ambient_conflict(var: str, value: str, target: Target) -> str:
    """Human-readable refusal reason for an ambient connection override."""
    if var.upper() in URI_VARS:
        try:
            host, port = parse_neo4j_uri(value)
        except ValueError:
            return f"{var} carries an unparseable URI {value!r}"
        if host not in LOOPBACK_HOSTS:
            return (
                f"{var}={value!r} points at a REMOTE/Aura host {host!r} — "
                "shared/live targets are forbidden (T10-LEAK-09)"
            )
        if port == DEV_CONTAINER_PORT:
            return (
                f"{var}={value!r} uses port {DEV_CONTAINER_PORT} — the "
                "developer container (docker-compose `spoilerless-neo4j`) port; "
                "pre-existing/shared targets are forbidden"
            )
    return (
        f"{var}={value!r} is a user-provided connection override; "
        "the runner owns the connection and refuses ambient overrides "
        "(T10-LEAK-09)"
    )


def assert_no_ambient_connection_overrides(env: dict[str, str], target: Target) -> None:
    """Fail closed on ANY ambient connection var not equal to the ephemeral target."""
    for var in CONNECTION_VARS:
        ambient = _env_get(env, var)
        if ambient is None:
            continue
        expected = target.connection_map[var]
        if ambient != expected:
            raise TargetRefusal(
                f"forbidden target/override: {_classify_ambient_conflict(var, ambient, target)}"
            )


def docker_run_args(target: Target) -> list[str]:
    """Args for provisioning the ephemeral container (no volume mounts)."""
    return [
        "docker", "run", "-d",
        "--name", target.name,
        "-e", f"NEO4J_AUTH={target.username}/{target.password}",
        "-p", f"127.0.0.1:{target.bolt_port}:7687",
        "-p", f"127.0.0.1:{target.http_port}:7474",
        target.image,
    ]


def child_env(env: dict[str, str], target: Target) -> dict[str, str]:
    """Child environment: ephemeral connection for BOTH alias families, no PYTHONPATH.

    ``aura_*`` is the winning alias family in ``Settings`` (AliasChoices order),
    so both families must carry the same ephemeral values — a child can never
    resolve to the developer container or Aura even if its code reads only one
    family.
    """
    merged = dict(env)
    merged.pop("PYTHONPATH", None)
    merged.update(
        {
            "NEO4J_URI": target.uri,
            "NEO4J_USERNAME": target.username,
            "NEO4J_PASSWORD": target.password,
            "NEO4J_DATABASE": target.database,
            "aura_uri": target.uri,
            "aura_username": target.username,
            "aura_password": target.password,
            "aura_database": target.database,
        }
    )
    return merged


_PROBE_CODE = """
import asyncio, json, os, sys
from spoilerless.app.core.config import Settings

expected = json.loads(sys.argv[1])
settings = Settings(_env_file=None)  # env vars alone must resolve correctly
actual = {
    "uri": settings.neo4j_uri,
    "username": settings.neo4j_username,
    "password": settings.neo4j_password,
    "database": settings.neo4j_database,
}
assert actual == expected, f"effective Settings mismatch: {actual} != {expected}"

from spoilerless.app.graph.database import Neo4jDatabase

async def probe() -> None:
    db = Neo4jDatabase(settings)
    db.open()
    try:
        await db.verify_connection()
        rows = await db.execute_query("MATCH (n) RETURN count(n) AS count")
        assert rows == [{"count": 0}], (
            f"target is NOT a fresh ephemeral container: {rows} nodes present"
        )
        print("probe OK: effective Settings resolved to ephemeral target; 0 nodes")
    finally:
        await db.close()

asyncio.run(probe())
"""


# ── Docker shim (monkeypatchable in unit tests) ─────────────────────────────


def _docker(args: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=capture, text=True, check=check)


def _docker_quiet(args: list[str]) -> str:
    proc = _docker(args, check=False, capture=True)
    return (proc.stdout or "").strip()


def _container_exists(name: str) -> bool:
    # docker prints "[]" on stdout with rc=1 for a missing container —
    # trust the exit code, not the output.
    proc = _docker(["docker", "container", "inspect", name], check=False, capture=True)
    return proc.returncode == 0


def _named_volume_exists(name: str) -> bool:
    proc = _docker(["docker", "volume", "inspect", name], check=False, capture=True)
    return proc.returncode == 0


def _container_running(name: str) -> bool:
    return _docker_quiet(
        ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"]
    ) != ""


def _wait_ready(target: Target, timeout: float = 180.0) -> None:
    """Wait until the container's HTTP endpoint and the bolt port are reachable."""
    deadline = time.monotonic() + timeout
    http_ok = False
    bolt_ok = False
    last_error = ""
    while time.monotonic() < deadline:
        if not http_ok:
            proc = _docker(
                [
                    "docker", "exec", target.name, "wget",
                    "--no-verbose", "--tries=1", "--spider", "http://localhost:7474",
                ],
                check=False,
                capture=True,
            )
            http_ok = proc.returncode == 0
            if not http_ok and (proc.stderr or "").strip():
                last_error = (proc.stderr or "").strip().splitlines()[-1]
        if http_ok and not bolt_ok:
            try:
                with socket.create_connection(("127.0.0.1", target.bolt_port), timeout=2.0):
                    bolt_ok = True
            except OSError:
                bolt_ok = False
        if http_ok and bolt_ok:
            print(f"ephemeral container {target.name} ready (bolt {target.bolt_port}, http {target.http_port})")
            return
        time.sleep(2.0)
    raise TargetRefusal(
        f"container {target.name} did not become ready in {timeout:.0f}s — {last_error}"
    )


def _teardown(target: Target) -> bool:
    """Always run: remove container + its anonymous volumes, then verify absence."""
    removed = False
    try:
        proc = _docker(["docker", "rm", "-f", "-v", target.name], check=False, capture=True)
        removed = proc.returncode == 0
    except Exception as exc:  # pragma: no cover — docker shim failure
        print(f"teardown: docker rm failed ({exc}); retrying with kill", file=sys.stderr)
        _docker(["docker", "kill", target.name], check=False, capture=True)
        proc = _docker(["docker", "rm", "-f", "-v", target.name], check=False, capture=True)
        removed = proc.returncode == 0
    gone = not _container_exists(target.name)
    if removed and gone:
        print(f"teardown verified: container {target.name} and its anonymous volumes removed")
    elif gone:
        print(f"teardown: container {target.name} absent (nothing to remove)")
    else:
        print(
            f"teardown FAILED: container {target.name} still exists — "
            "inspect and remove it manually before rerunning",
            file=sys.stderr,
        )
    return gone


# ── Runner steps ────────────────────────────────────────────────────────────


def _verify_effective_settings(env: dict[str, str], target: Target) -> None:
    expected = {
        "uri": target.uri,
        "username": target.username,
        "password": target.password,
        "database": target.database,
    }
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE_CODE, json.dumps(expected)],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stdout + proc.stderr).strip()[-2000:]
        raise TargetRefusal(
            "settings/target probe failed — the effective Settings did not resolve to "
            f"the ephemeral container (alias-precedence bypass?):\n{detail}"
        )
    print(proc.stdout.strip())


def _seed_database(env: dict[str, str]) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", SETUP_MODULE],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise TargetRefusal(
            f"graph setup failed against the ephemeral target:\n"
            f"{(proc.stdout + proc.stderr).strip()[-2000:]}"
        )
    print((proc.stdout or proc.stderr).strip().splitlines()[-1] if proc.stdout else "graph setup complete")


def _run_tests(args: argparse.Namespace, env: dict[str, str]) -> int:
    if args.files:
        missing = [f for f in args.files if not (PROJECT_ROOT / f).is_file()]
        if missing:
            print(f"test files do not exist: {', '.join(missing)}", file=sys.stderr)
            return 2
        cmd = [sys.executable, "-m", "pytest", *args.files, "-q", "--no-header", *args.extra]
    else:
        cmd = [sys.executable, str(CHUNK_RUNNER), *args.extra]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return proc.returncode


def run(args: argparse.Namespace) -> int:
    target = compute_target()
    print(
        f"Phase 10 guarded backend runner: ephemeral target {target.name} "
        f"({target.image}) on 127.0.0.1:{target.bolt_port} — no live/shared data"
    )

    # 1. Fail-closed refusal of every forbidden target BEFORE creating anything.
    assert_no_ambient_connection_overrides(os.environ, target)
    if _container_exists(target.name):
        raise TargetRefusal(f"pre-existing container {target.name!r} — refusing to reuse it")
    if _named_volume_exists(target.name):
        raise TargetRefusal(f"pre-existing named volume {target.name!r} — refusing to reuse it")
    for forbidden in sorted(FORBIDDEN_CONTAINERS):
        if _container_running(forbidden):
            raise TargetRefusal(
                f"developer/shared container {forbidden!r} is running — "
                "refusing to run tests while a shared target is live (T10-LEAK-09)"
            )

    # 2. Provision the ephemeral container.
    proc = _docker(docker_run_args(target), check=False, capture=True)
    if proc.returncode != 0:
        raise TargetRefusal(
            f"docker run failed: {(proc.stdout + proc.stderr).strip()[-2000:]}"
        )

    # 3. Run everything under a finally-guarded teardown.
    try:
        _wait_ready(target)
        env = child_env(os.environ, target)
        _verify_effective_settings(env, target)
        _seed_database(env)
        return _run_tests(args, env)
    finally:
        _teardown(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--files", nargs="*", metavar="TEST",
        help="run these spoilerless test files instead of all chunks",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="explicitly run every chunk (default behavior)",
    )
    parser.add_argument("extra", nargs="*", help="extra args passed to pytest/chunk runner")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except TargetRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
