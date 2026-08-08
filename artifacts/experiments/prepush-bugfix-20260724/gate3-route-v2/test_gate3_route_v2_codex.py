from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_route_v2 as route
import gate3_route_v2_codex as codex


RUN_ID = "gate3-v2-codex-synthetic-0001"


def _contained(
    *, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
) -> codex._ContainedResult:
    return codex._ContainedResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        tree_terminated=True,
    )


class Probe:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.environments: list[dict[str, str]] = []

    def __call__(
        self, command: list[str] | tuple[str, ...], cwd: Path, env: dict[str, str]
    ) -> codex._ContainedResult:
        self.commands.append(tuple(command))
        self.environments.append(dict(env))
        if command[-1] == "--version":
            return _contained(stdout=(codex.PINNED_CLI_VERSION + "\n").encode())
        return _contained(stdout=(" ".join(codex.REQUIRED_FLAGS) + "\n").encode())


def _measure(tmp_path: Path, probe: Probe | None = None) -> tuple[bytes, Path, Probe]:
    selected = probe or Probe()
    payload, snapshot = codex._measure_preflight(
        run_id=RUN_ID,
        executable=Path(sys.executable),
        expected_executable_sha256=route._sha256_file(Path(sys.executable)),
        preflight_root=tmp_path / "preflight",
        probe=selected,
    )
    return payload, snapshot, selected


def test_preflight_measures_exact_snapshot_version_help_and_closed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross")
    monkeypatch.setenv("CODEX_UNCONTROLLED", "must-not-cross")
    payload, snapshot, probe = _measure(tmp_path)
    receipt = json.loads(payload)
    assert snapshot.is_file()
    assert route._sha256_file(snapshot) == route._sha256_file(Path(sys.executable))
    assert [command[-1] for command in probe.commands] == [
        "--version", "--help", "--help"
    ]
    assert probe.commands[2][-2:] == ("exec", "--help")
    assert receipt["checks"] == {
        "cleanup": "PASS",
        "exec_help": "PASS",
        "root_help": "PASS",
        "version": "PASS",
    }
    assert receipt["compatibility"] == {
        "required_flag_presence": {flag: True for flag in sorted(codex.REQUIRED_FLAGS)},
        "root_help_nonempty": True,
        "version_match": True,
    }
    assert receipt["required_flags"] == sorted(codex.REQUIRED_FLAGS)
    assert receipt["execution_identity"]["cli_version"] == codex.PINNED_CLI_VERSION
    assert receipt["execution_identity"]["executable_sha256"] == route._sha256_file(
        snapshot
    )
    assert receipt["environment_policy_sha256"] == codex._environment_policy_sha256()
    assert route.SHA256_RE.fullmatch(receipt["environment_projection_sha256"])
    for env in probe.environments:
        assert "OPENAI_API_KEY" not in env
        assert "CODEX_UNCONTROLLED" not in env
        assert set(env) <= set(codex.ENVIRONMENT_SOURCE_KEYS) | {"CODEX_HOME", "NO_COLOR"}


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("version", "version"),
        ("flag", "required flag"),
        ("residue", "residue"),
    ],
)
def test_preflight_fails_closed_before_credentials(
    tmp_path: Path, mutation: str, message: str
) -> None:
    def probe(command: list[str] | tuple[str, ...], cwd: Path, env: dict[str, str]):
        if mutation == "residue" and command[-1] == "--version":
            (Path(env["CODEX_HOME"]) / "unexpected").write_text("x")
        if command[-1] == "--version":
            value = "wrong-version" if mutation == "version" else codex.PINNED_CLI_VERSION
            return _contained(stdout=(value + "\n").encode())
        flags = list(codex.REQUIRED_FLAGS)
        if mutation == "flag":
            flags.pop()
        return _contained(stdout=(" ".join(flags) + "\n").encode())

    with pytest.raises(route.RouteV2Error, match=message):
        codex._measure_preflight(
            run_id=RUN_ID,
            executable=Path(sys.executable),
            expected_executable_sha256=route._sha256_file(Path(sys.executable)),
            preflight_root=tmp_path / "preflight",
            probe=probe,
        )
    assert not (tmp_path / "preflight").exists()


def test_executable_digest_is_checked_before_any_probe(tmp_path: Path) -> None:
    probe = Probe()
    with pytest.raises(route.RouteV2Error, match="pinned identity"):
        codex._measure_preflight(
            run_id=RUN_ID,
            executable=Path(sys.executable),
            expected_executable_sha256="0" * 64,
            preflight_root=tmp_path / "preflight",
            probe=probe,
        )
    assert probe.commands == []


def test_preflight_probe_exception_leaves_zero_private_residue(tmp_path: Path) -> None:
    def exploding_probe(*args: object, **kwargs: object) -> codex._ContainedResult:
        raise RuntimeError("synthetic probe failure")

    root = tmp_path / "preflight"
    with pytest.raises(RuntimeError, match="synthetic probe failure"):
        codex._measure_preflight(
            run_id=RUN_ID,
            executable=Path(sys.executable),
            expected_executable_sha256=route._sha256_file(Path(sys.executable)),
            preflight_root=root,
            probe=exploding_probe,
        )
    assert not root.exists()


def test_root_help_cannot_supply_flag_missing_from_exec_help(tmp_path: Path) -> None:
    def split_scope_probe(
        command: list[str] | tuple[str, ...], cwd: Path, env: dict[str, str]
    ) -> codex._ContainedResult:
        if command[-1] == "--version":
            return _contained(stdout=(codex.PINNED_CLI_VERSION + "\n").encode())
        flags = list(codex.REQUIRED_FLAGS)
        if command[-2:] == ("exec", "--help"):
            flags.remove("--dangerously-bypass-approvals-and-sandbox")
        return _contained(stdout=(" ".join(flags) + "\n").encode())

    with pytest.raises(route.RouteV2Error, match="required flag"):
        codex._measure_preflight(
            run_id=RUN_ID,
            executable=Path(sys.executable),
            expected_executable_sha256=route._sha256_file(Path(sys.executable)),
            preflight_root=tmp_path / "preflight",
            probe=split_scope_probe,
        )


def test_runner_rejects_snapshot_changed_after_preflight(tmp_path: Path) -> None:
    payload, snapshot, _ = _measure(tmp_path)
    snapshot.write_bytes(snapshot.read_bytes() + b"mutation")
    with pytest.raises(route.RouteV2Error, match="measured preflight"):
        codex.CodexExecRunner(
            run_id=RUN_ID,
            executable_snapshot=snapshot,
            private_root=tmp_path / "private",
            auth_payload=b"{}\n",
            measured_preflight=payload,
        )


def test_live_authorization_rejects_caller_relabelled_runner(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="cannot be subclassed"):
        class ForbiddenSubclass(route.TrustedLiveRunner):
            pass

    class Relabelled:
        def execution_identity(self) -> dict[str, str]:
            return {
                "cli_version": codex.PINNED_CLI_VERSION,
                "command_contract_sha256": "1" * 64,
                "executable_sha256": "2" * 64,
                "kind": "codex_exec",
                "runner_sha256": "3" * 64,
            }

        def preflight_bytes(self) -> bytes:
            return b"{}"

        def __call__(self) -> route.SyntheticResult:
            raise AssertionError("must not invoke")

    payload, _, _ = _measure(tmp_path)
    relabelled = Relabelled()
    with pytest.raises(route.RouteV2Error, match="provenance"):
        route._trusted_live_runner(
            execution_identity=relabelled.execution_identity(),
            preflight=payload,
            invoke=relabelled.__call__,
        )
    Spoofed = type(
        "CodexExecRunner",
        (),
        {
            "__module__": "gate3_route_v2_codex",
            "execution_identity": Relabelled.execution_identity,
            "preflight_bytes": lambda self: payload,
            "__call__": Relabelled.__call__,
        },
    )
    spoofed = Spoofed()
    with pytest.raises(route.RouteV2Error, match="provenance"):
        route._trusted_live_runner(
            execution_identity=spoofed.execution_identity(),
            preflight=payload,
            invoke=spoofed.__call__,
        )

    root = tmp_path / "root"
    with pytest.raises(route.RouteV2Error, match="trusted runner"):
        route.orchestrate(
            root / "public" / RUN_ID,
            locator_root=root / "locators",
            external_root=root / "external",
            run_id=RUN_ID,
            authorization=route.LIVE_AUTHORIZATION,
            prompt=codex.PROMPT,
            output_schema=codex.OUTPUT_SCHEMA,
            expected_workspace=codex.EXPECTED_WORKSPACE,
            runner=Relabelled(),
            _trusted_route_root=root,
        )


def test_exact_codex_runner_builds_capability_and_live_action_binds_preflight(
    tmp_path: Path,
) -> None:
    payload, snapshot, _ = _measure(tmp_path)
    runner = codex.CodexExecRunner(
        run_id=RUN_ID,
        executable_snapshot=snapshot,
        private_root=tmp_path / "private" / f"gate3-v2-{RUN_ID}",
        auth_payload=b"{}\n",
        measured_preflight=payload,
    )
    trusted = runner.trusted_capability()
    assert type(trusted) is route.TrustedLiveRunner
    identity = runner.execution_identity()
    action = json.loads(route.action_bytes(
        run_id=RUN_ID,
        authorization=route.LIVE_AUTHORIZATION,
        prompt=codex.PROMPT,
        output_schema=codex.OUTPUT_SCHEMA,
        expected_workspace=codex.EXPECTED_WORKSPACE,
        execution_identity=identity,
        preflight_sha256=route._sha256_bytes(payload),
    ))
    assert action["preflight_sha256"] == route._sha256_bytes(payload)
    assert action["execution_identity"] == identity


def test_subprocess_cli_entrypoint_uses_canonical_module_provenance(
    tmp_path: Path,
) -> None:
    """Regression: direct file execution must not construct an __main__ runner."""
    sentinel = "CANONICAL_MAIN_SELECTED"
    (tmp_path / "sitecustomize.py").write_text(
        "import gate3_route_v2_codex as canonical\n"
        "def fake_main(*args, **kwargs):\n"
        f"    print({sentinel!r})\n"
        "    return 23\n"
        "canonical.main = fake_main\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(HERE)))
    completed = subprocess.run(
        [sys.executable, str(Path(codex.__file__).resolve())],
        cwd=HERE,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 23
    assert completed.stdout == sentinel + "\n"
    assert "trusted live runner provenance is invalid" not in completed.stderr


def test_invalid_probe_digest_is_rejected_offline(tmp_path: Path) -> None:
    payload, _, _ = _measure(tmp_path)
    value = json.loads(payload)
    value["probe_outputs"]["exec_help"]["stdout_sha256"] = "not-a-digest"
    mutated = route._json_bytes(value)
    with pytest.raises(route.RouteV2Error, match="probe output"):
        route._validate_preflight(mutated, RUN_ID, route.LIVE_AUTHORIZATION)


def test_private_surface_in_help_is_not_projected_publicly(tmp_path: Path) -> None:
    private_surface = "C:\\Users\\operator\\private-tool-home"

    def probe(command: list[str] | tuple[str, ...], cwd: Path, env: dict[str, str]):
        if command[-1] == "--version":
            return _contained(stdout=(codex.PINNED_CLI_VERSION + "\n").encode())
        return _contained(
            stdout=(" ".join(codex.REQUIRED_FLAGS) + "\n" + private_surface).encode()
        )

    payload, _, _ = _measure(tmp_path, probe=probe)
    receipt = json.loads(payload)
    assert private_surface.encode() not in payload
    assert all(
        not key.endswith("_b64")
        for output in receipt["probe_outputs"].values()
        for key in output
    )
    route._validate_preflight(payload, RUN_ID, route.LIVE_AUTHORIZATION)


@pytest.mark.parametrize("mutation", ["version", "flag", "extra_flag", "raw_output"])
def test_closed_compatibility_mutations_are_rejected_offline(
    tmp_path: Path, mutation: str
) -> None:
    payload, _, _ = _measure(tmp_path)
    value = json.loads(payload)
    if mutation == "version":
        value["compatibility"]["version_match"] = False
    elif mutation == "flag":
        first = sorted(codex.REQUIRED_FLAGS)[0]
        value["compatibility"]["required_flag_presence"][first] = False
    elif mutation == "extra_flag":
        value["compatibility"]["required_flag_presence"]["--future-flag"] = True
    else:
        value["probe_outputs"]["exec_help"]["stdout_b64"] = ""
    with pytest.raises(route.RouteV2Error, match="preflight"):
        route._validate_preflight(
            route._json_bytes(value), RUN_ID, route.LIVE_AUTHORIZATION
        )


@pytest.mark.parametrize("numeric", [1, 1.0])
@pytest.mark.parametrize("target", ["version", "root_help", "one_flag", "all_flags"])
def test_numeric_compatibility_values_are_rejected_offline(
    tmp_path: Path, target: str, numeric: int | float
) -> None:
    payload, _, _ = _measure(tmp_path)
    value = json.loads(payload)
    if target == "version":
        value["compatibility"]["version_match"] = numeric
    elif target == "root_help":
        value["compatibility"]["root_help_nonempty"] = numeric
    elif target == "one_flag":
        first = sorted(codex.REQUIRED_FLAGS)[0]
        value["compatibility"]["required_flag_presence"][first] = numeric
    else:
        value["compatibility"]["required_flag_presence"] = {
            flag: numeric for flag in codex.REQUIRED_FLAGS
        }
    with pytest.raises(route.RouteV2Error, match="compatibility"):
        route._validate_preflight(
            route._json_bytes(value), RUN_ID, route.LIVE_AUTHORIZATION
        )


def test_preflight_v1_schema_is_rejected_offline(tmp_path: Path) -> None:
    payload, _, _ = _measure(tmp_path)
    value = json.loads(payload)
    value["schema"] = "gate3-route-v2.preflight.v1"
    with pytest.raises(route.RouteV2Error, match="preflight receipt"):
        route._validate_preflight(
            route._json_bytes(value), RUN_ID, route.LIVE_AUTHORIZATION
        )


@pytest.mark.parametrize(
    "target",
    ["output", "private", "locator_run", "external_terminal", "final_pin", "terminal_pin"],
)
def test_every_fixed_path_collision_precedes_probe_and_credential_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    monkeypatch.setattr(route, "TRUSTED_ROUTE_ROOT", tmp_path / "fixed")
    paths = codex._fixed_paths(RUN_ID)
    collision = {
        "output": paths["output"],
        "private": paths["private"],
        "locator_run": paths["locator"] / RUN_ID,
        "external_terminal": paths["external"] / f"{RUN_ID}.terminal.json",
        "final_pin": paths["final_pin"],
        "terminal_pin": paths["terminal_pin"],
    }[target]
    if target in {"output", "private", "locator_run"}:
        collision.mkdir(parents=True)
    else:
        collision.parent.mkdir(parents=True, exist_ok=True)
        collision.write_text("occupied", encoding="ascii")
    probe = Probe()
    auth = tmp_path / "auth.json"
    with pytest.raises(route.RouteV2Error, match="collision"):
        codex.main(
            [
                "--run-id", RUN_ID,
                "--authorization", route.LIVE_AUTHORIZATION,
                "--codex-exe", str(Path(sys.executable)),
                "--expected-executable-sha256", route._sha256_file(Path(sys.executable)),
                "--auth-file", str(auth),
            ],
            _probe=probe,
        )
    assert probe.commands == []
    assert not auth.exists()


def test_cli_exposes_no_caller_controlled_roots_or_pins() -> None:
    options = {action.dest for action in codex._parser()._actions}
    assert not {
        "output_root", "locator_root", "external_root", "trusted_route_root",
        "final_pin", "terminal_pin",
    } & options


def test_publication_parent_probe_precedes_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(route, "TRUSTED_ROUTE_ROOT", tmp_path / "fixed")
    called = False

    def fail_probe(paths: dict[str, Path]) -> None:
        nonlocal called
        called = True
        raise route.RouteV2Error("publication unavailable")

    monkeypatch.setattr(codex, "_probe_publication_parents", fail_probe)
    auth = tmp_path / "auth.json"
    with pytest.raises(route.RouteV2Error, match="publication unavailable"):
        codex.main(
            [
                "--run-id", RUN_ID,
                "--authorization", route.LIVE_AUTHORIZATION,
                "--codex-exe", str(Path(sys.executable)),
                "--expected-executable-sha256", route._sha256_file(Path(sys.executable)),
                "--auth-file", str(auth),
            ]
        )
    assert called
    assert not auth.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_timeout_terminates_entire_windows_process_tree(tmp_path: Path) -> None:
    marker = tmp_path / "grandchild-marker"
    grandchild = tmp_path / "grandchild.py"
    grandchild.write_text(
        "import pathlib,sys,time\ntime.sleep(2)\npathlib.Path(sys.argv[1]).write_text('alive')\n",
        encoding="utf-8",
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import subprocess,sys,time\n"
        "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
        "time.sleep(20)\n",
        encoding="utf-8",
    )
    result = codex._run_contained(
        [sys.executable, str(parent), str(grandchild), str(marker)],
        input_bytes=b"",
        cwd=tmp_path,
        env=codex._closed_environment(tmp_path),
        timeout_seconds=1,
    )
    assert result.timed_out
    assert result.tree_terminated
    time.sleep(2.5)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
@pytest.mark.parametrize("failure", ["create", "set-policy", "assign"])
def test_every_job_setup_failure_kills_started_guard_before_target_executes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    marker = tmp_path / "target-executed"
    target = tmp_path / "target.py"
    target.write_text(
        "import pathlib,sys\npathlib.Path(sys.argv[1]).write_text('ran')\n",
        encoding="utf-8",
    )
    observed: list[subprocess.Popen[bytes]] = []
    real_popen = subprocess.Popen

    def recording_popen(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        process = real_popen(*args, **kwargs)
        observed.append(process)
        return process

    def fail_assignment(process: subprocess.Popen[bytes]) -> int:
        raise route.RouteV2Error(f"injected {failure} failure")

    monkeypatch.setattr(subprocess, "Popen", recording_popen)
    monkeypatch.setattr(codex, "_assign_kill_on_close_job", fail_assignment)
    with pytest.raises(route.RouteV2Error, match=failure):
        codex._run_contained(
            [sys.executable, str(target), str(marker)],
            input_bytes=b"",
            cwd=tmp_path,
            env=codex._closed_environment(tmp_path),
            timeout_seconds=5,
        )
    assert len(observed) == 1
    assert observed[0].poll() is not None
    assert not marker.exists()


def test_closed_environment_does_not_inherit_uncontrolled_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("CODEX_CONFIG", "uncontrolled")
    env = codex._closed_environment(tmp_path)
    assert "OPENAI_API_KEY" not in env
    assert "CODEX_CONFIG" not in env
    assert env["CODEX_HOME"] == str(tmp_path)
    assert env["NO_COLOR"] == "1"
