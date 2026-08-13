"""Guard tests for the Phase 10 ephemeral-container backend test runner.

These tests are mock-driven: no docker daemon and no live database are
touched. They lock the fail-closed behavior of
``scripts/run_phase10_backend_tests.py`` (T10-LEAK-09): forbidden targets are
refused before anything is created, children see both alias families
pointing at the ephemeral target only, and teardown always runs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_module("run_phase10_backend_tests", SCRIPTS_DIR / "run_phase10_backend_tests.py")
chunk_runner = _load_module("run_backend_tests", SCRIPTS_DIR / "run_backend_tests.py")


def _target(**overrides) -> runner.Target:
    kwargs = {
        "name": "hdgraf-phase10-tests-abc123",
        "image": runner.IMAGE,
        "username": "neo4j",
        "password": "ephemeral-password",
        "database": "neo4j",
        "bolt_port": 17687,
        "http_port": 17474,
    }
    kwargs.update(overrides)
    return runner.Target(**kwargs)


class FakeDocker:
    """Records docker calls; scripted responses by substring match."""

    def __init__(self, responses: list[tuple[str, str, int]] | None = None) -> None:
        self.calls: list[list[str]] = []
        self._responses = list(responses or [])

    def __call__(self, args, *, check=True, capture=True):
        self.calls.append(list(args))
        for needle, stdout, code in self._responses:
            joined = " ".join(args)
            if needle in joined:
                return _CompletedProcess(code, stdout)
        return _CompletedProcess(0, "")


class _CompletedProcess:
    def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ── Target generation ───────────────────────────────────────────────────────


def test_generated_target_is_unique_and_never_a_forbidden_name() -> None:
    targets = [runner.compute_target() for _ in range(5)]
    names = {target.name for target in targets}
    assert len(names) == 5
    for target in targets:
        assert target.name.startswith(runner.CONTAINER_PREFIX)
        assert target.name not in runner.FORBIDDEN_CONTAINERS
        assert target.image == "neo4j:2026.06.0-community"
        assert target.bolt_port >= 1024
        assert target.http_port >= 1024
        assert target.bolt_port != target.http_port
        assert target.uri == f"neo4j://127.0.0.1:{target.bolt_port}"


# ── Fail-closed ambient-override refusals ───────────────────────────────────


def test_ambient_aura_uri_pointing_at_remote_host_is_refused() -> None:
    env = {"AURA_URI": "neo4j+s://abc123.databases.neo4j.io"}
    with pytest.raises(runner.TargetRefusal, match="REMOTE/Aura host"):
        runner.assert_no_ambient_connection_overrides(env, _target())


def test_ambient_neo4j_uri_on_developer_container_port_is_refused() -> None:
    env = {"NEO4J_URI": "neo4j://localhost:7687"}
    with pytest.raises(runner.TargetRefusal, match="developer container"):
        runner.assert_no_ambient_connection_overrides(env, _target())


def test_any_ambient_connection_override_is_refused() -> None:
    for var, value in (
        ("NEO4J_URI", "neo4j://127.0.0.1:19999"),
        ("NEO4J_USERNAME", "someone-else"),
        ("NEO4J_PASSWORD", "someone-elses-password"),
        ("AURA_URI", "neo4j://127.0.0.1:19999"),
        ("AURA_PASSWORD", "other"),
    ):
        with pytest.raises(runner.TargetRefusal, match="override"):
            runner.assert_no_ambient_connection_overrides({var: value}, _target())


def test_clean_ambient_env_is_accepted() -> None:
    # A clean shell (no connection vars at all) must be allowed through.
    runner.assert_no_ambient_connection_overrides({}, _target())
    runner.assert_no_ambient_connection_overrides({"PYTHONPATH": "/some/other"}, _target())


def test_ambient_matching_ephemeral_values_are_accepted() -> None:
    target = _target()
    env = {var: target.connection_map[var] for var in runner.CONNECTION_VARS}
    runner.assert_no_ambient_connection_overrides(env, target)


# ── Provisioning shape ──────────────────────────────────────────────────────


def test_docker_run_args_have_no_volume_mounts_and_bind_loopback_only() -> None:
    args = runner.docker_run_args(_target())
    assert args[0:2] == ["docker", "run"]
    assert "--name" in args and "hdgraf-phase10-tests-abc123" in args
    assert any(arg == "NEO4J_AUTH=neo4j/ephemeral-password" for arg in args) or any(
        "NEO4J_AUTH=neo4j/ephemeral-password" in arg for arg in args
    )
    port_mappings = [
        args[i + 1] for i, arg in enumerate(args) if arg == "-p" and i + 1 < len(args)
    ]
    assert port_mappings == ["127.0.0.1:17687:7687", "127.0.0.1:17474:7474"]
    assert all(mapping.startswith("127.0.0.1:") for mapping in port_mappings), (
        "ports must bind loopback only"
    )
    # No persistent storage of any kind: no bind mounts, no named volumes.
    for arg in args:
        assert arg not in ("-v", "--volume", "--mount")
        assert not arg.startswith(("-v", "--volume=", "--mount="))
    assert args[-1] == "neo4j:2026.06.0-community"


# ── Child environment ───────────────────────────────────────────────────────


def test_child_env_exports_both_alias_families_and_strips_pythonpath() -> None:
    target = _target()
    base = {
        "PYTHONPATH": "/hermes/shadow",
        "NEO4J_URI": "neo4j://bad-host:7687",  # must be overridden, not inherited
        "LLM_API_KEY": "irrelevant-but-kept",
    }
    env = runner.child_env(base, target)

    assert "PYTHONPATH" not in env
    assert env["NEO4J_URI"] == target.uri
    assert env["NEO4J_USERNAME"] == "neo4j"
    assert env["NEO4J_PASSWORD"] == target.password
    assert env["NEO4J_DATABASE"] == "neo4j"
    # The winning lowercase aura_* aliases must carry the SAME ephemeral values.
    assert env["aura_uri"] == target.uri
    assert env["aura_username"] == "neo4j"
    assert env["aura_password"] == target.password
    assert env["aura_database"] == "neo4j"
    assert env["LLM_API_KEY"] == "irrelevant-but-kept"


# ── Pre-existing / shared target refusals (docker-shim driven) ──────────────


def test_preexisting_container_name_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDocker([("container inspect", "[]\n", 0)])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: _target())
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)
    with pytest.raises(runner.TargetRefusal, match="pre-existing container"):
        runner.run(_args())
    assert not any("docker run" in " ".join(c) for c in fake.calls)


def test_preexisting_named_volume_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDocker([
        ("container inspect", "", 1),
        ("volume inspect", "[]\n", 0),
    ])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: _target())
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)
    with pytest.raises(runner.TargetRefusal, match="pre-existing named volume"):
        runner.run(_args())
    assert not any("docker run" in " ".join(c) for c in fake.calls)


def test_running_developer_container_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDocker([
        ("container inspect", "", 1),
        ("volume inspect", "", 1),
        ("ps", "spoilerless-neo4j\n", 0),
    ])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: _target())
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)
    with pytest.raises(runner.TargetRefusal, match="developer/shared container .* is running"):
        runner.run(_args())
    assert not any("docker run" in " ".join(c) for c in fake.calls)


def test_ambient_remote_override_refuses_before_any_docker_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeDocker()
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: _target())
    monkeypatch.setenv("AURA_URI", "neo4j+s://abc123.databases.neo4j.io")
    assert runner.main(["--all"]) == 2
    assert fake.calls == []


# ── Teardown: always runs, even when the tests fail ─────────────────────────


def _args(files: list[str] | None = None):
    return runner.main.__globals__["argparse"].Namespace(
        files=files, all=True, extra=[]
    )


def test_teardown_runs_when_tests_fail_and_verifies_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _target()
    fake = FakeDocker([
        ("docker run", target.name, 0),
        ("docker exec", "", 0),          # readiness wget OK
        ("docker rm", target.name, 0),   # teardown rm -f -v succeeds
        ("container inspect", "", 1),    # absence verified afterwards
        ("ps", "", 0),                   # no forbidden containers running
        ("volume inspect", "", 1),       # no pre-existing volume
    ])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: target)
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)
    monkeypatch.setattr(runner, "_wait_ready", lambda t, timeout=180.0: None)
    monkeypatch.setattr(runner, "_verify_effective_settings", lambda env, t: None)
    monkeypatch.setattr(runner, "_seed_database", lambda env: None)
    monkeypatch.setattr(runner, "_run_tests", lambda args, env: 1)  # tests FAIL

    assert runner.run(_args()) == 1  # failure exit code propagates
    rm_calls = [" ".join(c) for c in fake.calls if c[:2] == ["docker", "rm"]]
    assert rm_calls, "teardown must run docker rm even when tests fail"
    assert all("-v" in call for call in rm_calls), "rm must include -v (anonymous volumes)"


def test_teardown_runs_when_provisioning_step_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _target()
    fake = FakeDocker([
        ("docker run", target.name, 0),
        ("docker rm", target.name, 0),
        ("container inspect", "", 1),
        ("ps", "", 0),
        ("volume inspect", "", 1),
    ])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "compute_target", lambda: target)
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("readiness exploded")

    monkeypatch.setattr(runner, "_wait_ready", _boom)
    with pytest.raises(RuntimeError, match="readiness exploded"):
        runner.run(_args())
    assert any(c[:2] == ["docker", "rm"] for c in fake.calls), "teardown must run on exceptions"


# ── Chunk inventory assertion ───────────────────────────────────────────────


def test_chunk_inventory_covers_every_test_file_exactly_once() -> None:
    chunk_runner.assert_chunk_inventory_matches_disk()
    listed = [name for files in chunk_runner.CHUNKS.values() for name in files]
    assert len(listed) == len(set(listed)), "no duplicate chunk entries allowed"


def test_phase10_chunk_lists_all_five_phase10_test_files() -> None:
    assert set(chunk_runner.CHUNKS["phase10-viz"]) == {
        "test_visualization_baseline.py",
        "test_visualization_projection.py",
        "test_visualization_cache.py",
        "test_visualization_graphrag.py",
        "test_phase10_test_runner.py",
    }


def test_inventory_assertion_detects_missing_and_duplicate_files(monkeypatch: pytest.MonkeyPatch) -> None:
    original = dict(chunk_runner.CHUNKS)
    broken = {name: list(files) for name, files in original.items()}
    broken["core"] = broken["core"] + ["test_nonexistent_ghost.py"]
    broken["auth"] = broken["auth"] + ["test_auth.py"]  # duplicate
    monkeypatch.setattr(chunk_runner, "CHUNKS", broken)
    with pytest.raises(AssertionError, match="not on disk"):
        chunk_runner.assert_chunk_inventory_matches_disk()
    with pytest.raises(AssertionError, match="listed more than once"):
        chunk_runner.assert_chunk_inventory_matches_disk()
    monkeypatch.setattr(chunk_runner, "CHUNKS", original)


# ── Files-mode validation ───────────────────────────────────────────────────


def test_files_mode_rejects_nonexistent_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _target()
    monkeypatch.setattr(runner, "_docker", FakeDocker())
    monkeypatch.setattr(runner, "compute_target", lambda: target)
    monkeypatch.setattr(runner, "assert_no_ambient_connection_overrides", lambda env, t: None)
    monkeypatch.setattr(runner, "_container_exists", lambda name: False)
    monkeypatch.setattr(runner, "_named_volume_exists", lambda name: False)
    monkeypatch.setattr(runner, "_container_running", lambda name: False)
    monkeypatch.setattr(runner, "_wait_ready", lambda t, timeout=180.0: None)
    monkeypatch.setattr(runner, "_verify_effective_settings", lambda env, t: None)
    monkeypatch.setattr(runner, "_seed_database", lambda env: None)
    monkeypatch.setattr(
        runner,
        "_docker",
        FakeDocker([
            ("docker run", target.name, 0),
            ("docker rm", target.name, 0),
            ("container inspect", "", 1),
        ]),
    )
    import argparse

    result = runner.run(argparse.Namespace(files=["spoilerless/tests/does_not_exist.py"], all=False, extra=[]))
    assert result == 2
