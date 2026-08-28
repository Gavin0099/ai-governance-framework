from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent


def _module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXECUTOR = _module("c1_capability_executor", "capability_probe_executor.py")
BOOTSTRAP = _module("c1_capability_bootstrap", "capability_probe_bootstrap.py")


def manifest() -> dict:
    return json.loads((BASE / "capability-probe-manifest.json").read_text(encoding="utf-8"))


def test_manifest_freezes_every_file_except_itself() -> None:
    data = manifest()
    entries = {entry["path"]: entry for entry in data["frozen_files"]}
    actual = {path.name for path in BASE.iterdir() if path.is_file()}
    assert actual == set(entries) | {"capability-probe-manifest.json"}
    for name, entry in entries.items():
        payload = (BASE / name).read_bytes()
        assert len(payload) == entry["bytes"]
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
        oid = subprocess.check_output(
            ["git", "hash-object", "--no-filters", str(BASE / name)], text=True
        ).strip()
        assert oid == entry["git_blob_oid"]


def test_revision_packets_are_bound_as_separate_immutable_files() -> None:
    data = manifest()
    external = {entry["label"]: entry for entry in data["external_bindings"]}
    assert external["design_rev1"]["bytes"] == 20163
    assert external["design_rev1"]["sha256"] == "2ffa7379bd5a306bed05afa51c6ee2a29ba4744d6212160ed05f23baafaa349e"
    assert external["design_rev2"]["bytes"] == 7221
    assert external["design_rev2"]["sha256"] == "43690fea0dfd378ea4eca4064ec722416406bd60f2e7a810b78ecbe81b6babff"
    assert external["design_rev1"]["path"] != external["design_rev2"]["path"]
    assert external["qualification_01_terminal"]["sha256"] == "a1392ed5d91bbebab036ba0ffc7266b368eecb973ccef512ca65d05bb4d3bdcf"
    assert external["qualification_02_terminal"]["sha256"] == "0a2a1a378a01fd38cdcd87646f01e5900863952d8bcc99812e6221b9dc4da928"


@pytest.mark.parametrize(
    "raw",
    ["", "../escape", "a/../../b", "C:/Windows", "c:\\windows", "//server/share/x", "\\rooted"],
)
def test_repo_path_guard_rejects_escape_forms(raw: str) -> None:
    with pytest.raises(EXECUTOR.ProbeError):
        EXECUTOR._safe_repo_path(raw, "probe")


def test_command_projection_uses_exact_sandbox_surface() -> None:
    argv = EXECUTOR._command(
        Path("C:/staged/codex.exe"),
        Path("D:/workspace"),
        "D:/python.exe",
        Path("D:/workspace/positive.marker"),
    )
    assert argv[1] == "sandbox"
    assert argv[2] == "-C"
    assert argv.count("--") == 1
    assert argv[argv.index("--") + 1] == "D:/python.exe"
    assert argv[1:3] != ["sandbox", "windows"]
    assert "sandbox windows" not in " ".join(argv)


def test_minimal_environment_excludes_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", "C:/untrusted")
    environment = EXECUTOR._minimal_environment(tmp_path)
    assert "PATH" not in environment
    assert set(environment) <= set(EXECUTOR.INHERITED_ENV_KEYS) | {"CODEX_HOME", "NO_COLOR"}


def _result(returncode: int | None, *, timed_out: bool = False, stdout: bytes = b"", stderr: bytes = b""):
    return EXECUTOR.LaunchResult(returncode, timed_out, stdout, stderr)


def test_negative_control_unexpected_success_is_ambiguous() -> None:
    status = EXECUTOR._classify(_result(0), None, None, None)
    assert status == "CAPABILITY_PROBE_AMBIGUOUS"


def test_negative_control_marker_is_ambiguous_even_on_nonzero() -> None:
    status = EXECUTOR._classify(_result(1), None, EXECUTOR.MARKER_BYTES, None)
    assert status == "CAPABILITY_PROBE_AMBIGUOUS"


def test_positive_exact_marker_and_empty_streams_is_launchable() -> None:
    status = EXECUTOR._classify(_result(1), _result(0), None, EXECUTOR.MARKER_BYTES)
    assert status == "ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE"


@pytest.mark.parametrize("stdout,stderr,marker", [(b"noise", b"", EXECUTOR.MARKER_BYTES), (b"", b"noise", EXECUTOR.MARKER_BYTES), (b"", b"", b"wrong")])
def test_positive_non_exact_evidence_is_ambiguous(stdout: bytes, stderr: bytes, marker: bytes) -> None:
    status = EXECUTOR._classify(_result(1), _result(0, stdout=stdout, stderr=stderr), None, marker)
    assert status == "CAPABILITY_PROBE_AMBIGUOUS"


def test_positive_nonzero_without_bounded_denial_evidence_is_ambiguous() -> None:
    status = EXECUTOR._classify(_result(1), _result(1, stderr=b"bounded"), None, None)
    assert status == "CAPABILITY_PROBE_AMBIGUOUS"


def test_timeout_is_surface_unavailable() -> None:
    assert EXECUTOR._classify(_result(None, timed_out=True), None, None, None) == "CAPABILITY_PROBE_SURFACE_UNAVAILABLE"
    assert EXECUTOR._classify_with_stage(_result(None, timed_out=True), None, None, None)[1] == "bare_control_result"


def test_positive_nonzero_is_stage_derived_ambiguous() -> None:
    assert EXECUTOR._classify_with_stage(_result(1), _result(1), None, None) == (
        "CAPABILITY_PROBE_AMBIGUOUS",
        "absolute_control_result",
    )


def test_terminal_retains_only_bounded_stream_evidence() -> None:
    payload = EXECUTOR._terminal(
        status="ABSOLUTE_PYTHON_TASK_PLANE_DENIED",
        commit="1" * 40,
        negative=_result(1, stderr=b"negative secret"),
        positive=_result(1, stderr=b"positive secret"),
        cleanup="COMPLETE",
        diagnostic="absolute Python did not launch in the task plane",
        failure_stage="absolute_control_result",
        exception_class="NONE",
    )
    value = json.loads(payload)
    assert value["hosted_request_attempted"] is False
    assert value["auth_payload_read"] is False
    assert value["negative_control"]["stderr_bytes"] == 15
    assert b"negative secret" not in payload
    assert b"positive secret" not in payload


def _synthetic_manifest() -> dict:
    return {
        "runtime": {
            "cli_executable_bytes": 3,
            "cli_executable_sha256": hashlib.sha256(b"cli").hexdigest(),
        },
        "frozen_executor_sha256": "e" * 64,
    }


def _synthetic_frozen() -> dict[str, bytes]:
    return {
        EXECUTOR.MARKER_NAME: (BASE / EXECUTOR.MARKER_NAME).read_bytes(),
        EXECUTOR.CONFIG_NAME: (BASE / EXECUTOR.CONFIG_NAME).read_bytes(),
        EXECUTOR.REQUIREMENTS_NAME: (BASE / EXECUTOR.REQUIREMENTS_NAME).read_bytes(),
    }


def test_execute_cleans_private_roots_before_positive_terminal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "attempt"
    cli_root = tmp_path / ".cli"
    private = tmp_path / ".private"
    paths = {
        "output": output,
        "cli": cli_root,
        "private": private,
        "cli_source": tmp_path / "source.exe",
        "python": tmp_path / "python.exe",
        "policy": tmp_path / "requirements.toml",
    }
    monkeypatch.setenv("C1_CAPABILITY_EXECUTOR_SHA256", "e" * 64)
    monkeypatch.setattr(EXECUTOR, "_git", lambda *args, **kwargs: "1" * 40)
    monkeypatch.setattr(EXECUTOR, "_manifest", lambda *args: _synthetic_manifest())
    monkeypatch.setattr(EXECUTOR, "_verified_frozen_blobs", lambda *args: _synthetic_frozen())
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_validate_external_bindings", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_paths", lambda *args: paths)
    monkeypatch.setattr(EXECUTOR, "_validate_runtime", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_raw_copy_exact", lambda source, target, size, digest: target.write_bytes(b"cli"))
    monkeypatch.setattr(EXECUTOR, "_preflight_cli", lambda *args: None)

    calls = 0
    def launcher(argv, cwd, env, timeout):
        nonlocal calls
        calls += 1
        assert "PATH" not in env
        if calls == 1:
            return _result(1, stderr=b"bare python unavailable")
        Path(argv[-1]).write_bytes(EXECUTOR.MARKER_BYTES)
        return _result(0)

    def publish(path: Path, payload: bytes):
        assert not cli_root.exists()
        assert not private.exists()
        value = json.loads(payload)
        assert value["status"] == "ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE"
        return value

    monkeypatch.setattr(EXECUTOR, "_publish_terminal", publish)
    result = EXECUTOR.execute(
        repo_root=tmp_path,
        owner_authorized_freeze_commit="1" * 40,
        launcher=launcher,
    )
    assert result["cleanup"] == "COMPLETE"
    assert calls == 2


def test_cleanup_failure_overrides_launchable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "attempt"
    cli_root = tmp_path / ".cli"
    private = tmp_path / ".private"
    paths = {"output": output, "cli": cli_root, "private": private, "cli_source": tmp_path / "source.exe", "python": tmp_path / "python.exe", "policy": tmp_path / "policy"}
    monkeypatch.setenv("C1_CAPABILITY_EXECUTOR_SHA256", "e" * 64)
    monkeypatch.setattr(EXECUTOR, "_git", lambda *args, **kwargs: "1" * 40)
    monkeypatch.setattr(EXECUTOR, "_manifest", lambda *args: _synthetic_manifest())
    monkeypatch.setattr(EXECUTOR, "_verified_frozen_blobs", lambda *args: _synthetic_frozen())
    monkeypatch.setattr(EXECUTOR, "_validate_source_bindings", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_validate_external_bindings", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_paths", lambda *args: paths)
    monkeypatch.setattr(EXECUTOR, "_validate_runtime", lambda *args: None)
    monkeypatch.setattr(EXECUTOR, "_raw_copy_exact", lambda source, target, size, digest: target.write_bytes(b"cli"))
    monkeypatch.setattr(EXECUTOR, "_preflight_cli", lambda *args: None)
    calls = 0
    def launcher(argv, cwd, env, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(1)
        Path(argv[-1]).write_bytes(EXECUTOR.MARKER_BYTES)
        return _result(0)
    real_remove = EXECUTOR._remove_tree
    def fail_private(path: Path):
        if path == private:
            raise OSError("forced cleanup failure")
        real_remove(path)
    monkeypatch.setattr(EXECUTOR, "_remove_tree", fail_private)
    monkeypatch.setattr(EXECUTOR, "_publish_terminal", lambda path, payload: json.loads(payload))
    result = EXECUTOR.execute(repo_root=tmp_path, owner_authorized_freeze_commit="1" * 40, launcher=launcher)
    assert result["status"] == "CAPABILITY_PROBE_CLEANUP_FAILED"
    assert result["cleanup"] == "FAILED"


def test_publication_is_create_once_and_readback_exact(tmp_path: Path) -> None:
    output = tmp_path / "attempt"
    payload = b'{"status":"TEST"}\n'
    assert EXECUTOR._publish_terminal(output, payload) == {"status": "TEST"}
    assert (output / "terminal.json").read_bytes() == payload
    with pytest.raises(EXECUTOR.ProbeError, match="already exists"):
        EXECUTOR._publish_terminal(output, payload)


def test_executor_direct_file_main_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(BASE / "capability_probe_executor.py")])
    with pytest.raises(EXECUTOR.ProbeError, match="streamed"):
        EXECUTOR.main()


def test_bootstrap_direct_file_execution_is_rejected_before_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(BOOTSTRAP, "_git", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("git called")))
    monkeypatch.setattr(sys, "argv", [str(BASE / "capability_probe_bootstrap.py")])
    with pytest.raises(BOOTSTRAP.BootstrapError, match="streamed"):
        BOOTSTRAP.execute(repo_root=tmp_path, owner_authorized_freeze_commit="1" * 40)


def _fixture_git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


def test_streamed_bootstrap_ignores_dirty_manifest_bootstrap_and_executor(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _fixture_git(repo, "init", "-q")
    _fixture_git(repo, "config", "user.email", "probe@example.invalid")
    _fixture_git(repo, "config", "user.name", "Probe Fixture")
    freeze = repo.joinpath(*BOOTSTRAP.FREEZE_REPO_DIR.split("/"))
    freeze.mkdir(parents=True)
    bootstrap = (BASE / "capability_probe_bootstrap.py").read_bytes()
    trusted_executor = (
        "import os\nfrom pathlib import Path\n"
        "Path(os.environ['C1_TRUSTED_MARKER']).write_text('trusted', encoding='utf-8')\n"
    ).encode()
    bootstrap_path = freeze / "capability_probe_bootstrap.py"
    executor_path = freeze / "capability_probe_executor.py"
    bootstrap_path.write_bytes(bootstrap)
    executor_path.write_bytes(trusted_executor)
    bootstrap_oid = _fixture_git(repo, "hash-object", "--no-filters", str(bootstrap_path)).decode().strip()
    executor_oid = _fixture_git(repo, "hash-object", "--no-filters", str(executor_path)).decode().strip()
    python = Path(sys.executable).resolve()
    data = {
        "schema": BOOTSTRAP.SCHEMA,
        "runtime": {
            "python_executable_bytes": python.stat().st_size,
            "python_executable_sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
        },
        "derived_paths": {"python_executable": str(python)},
        "frozen_executor_sha256": hashlib.sha256(trusted_executor).hexdigest(),
        "frozen_files": [
            {"path": bootstrap_path.name, "git_blob_oid": bootstrap_oid, "bytes": len(bootstrap), "sha256": hashlib.sha256(bootstrap).hexdigest()},
            {"path": executor_path.name, "git_blob_oid": executor_oid, "bytes": len(trusted_executor), "sha256": hashlib.sha256(trusted_executor).hexdigest()},
        ],
    }
    manifest_path = freeze / "capability-probe-manifest.json"
    manifest_path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    _fixture_git(repo, "add", ".")
    _fixture_git(repo, "commit", "-q", "-m", "fixture")
    head = _fixture_git(repo, "rev-parse", "HEAD").decode().strip()
    dirty_marker = tmp_path / "dirty"
    trusted_marker = tmp_path / "trusted"
    bootstrap_path.write_text(f"from pathlib import Path\nPath({str(dirty_marker)!r}).write_text('dirty')\n", encoding="utf-8")
    executor_path.write_text(f"from pathlib import Path\nPath({str(dirty_marker)!r}).write_text('dirty')\n", encoding="utf-8")
    manifest_path.write_text('{"redirect":"dirty"}\n', encoding="utf-8")
    committed_bootstrap = _fixture_git(
        repo, "show", f"{head}:{BOOTSTRAP.FREEZE_REPO_DIR}/capability_probe_bootstrap.py"
    )
    environment = dict(os.environ)
    environment["C1_TRUSTED_MARKER"] = str(trusted_marker)
    completed = subprocess.run(
        [str(python), "-I", "-", "--repo-root", str(repo), "--owner-authorized-freeze-commit", head],
        input=committed_bootstrap,
        env=environment,
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert trusted_marker.read_text(encoding="utf-8") == "trusted"
    assert not dirty_marker.exists()


def test_parser_has_no_auth_path_digest_or_command_override() -> None:
    assert {action.dest for action in EXECUTOR._parser()._actions} == {"help", "repo_root", "owner_authorized_freeze_commit"}
    assert {action.dest for action in BOOTSTRAP._parser()._actions} == {"help", "repo_root", "owner_authorized_freeze_commit"}


def test_no_hosted_retry_download_or_persistent_policy_surface() -> None:
    source = (BASE / "capability_probe_executor.py").read_text(encoding="utf-8")
    for forbidden in ("auth.json", "urlopen", "requests.", "urllib", "Set-ExecutionPolicy", "model_observed_id", "sandbox windows"):
        assert forbidden not in source
    assert source.count(" = launcher(") == 2
    assert "str(exc)" not in source
    assert "exception_message" not in source


def test_attempt_roots_remain_absent() -> None:
    data = manifest()
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    paths = EXECUTOR._paths(repo, data)
    assert not paths["output"].exists()
    assert not paths["cli"].exists()
    assert not paths["private"].exists()
    assert not repo.joinpath(*data["derived_paths"]["qualification_03_output_root"].split("/")).exists()


def test_binding_and_preflight_order_precedes_controls() -> None:
    source = (BASE / "capability_probe_executor.py").read_text(encoding="utf-8")
    body = source[source.index("def execute(") :]
    ordered = [
        "_manifest(repo, commit)",
        "_verified_frozen_blobs(repo, commit, manifest)",
        "_validate_source_bindings(repo, manifest)",
        "_validate_external_bindings(manifest)",
        "_validate_runtime(paths, manifest)",
        "_assert_roots_absent(paths)",
        "cli_root.mkdir(parents=True)",
        "_preflight_cli(cli, workspace, env)",
        'launcher(_command(cli, workspace, "python", negative_path)',
        "positive = launcher(",
    ]
    positions = [body.index(token) for token in ordered]
    assert positions == sorted(positions)


def test_all_authority_flags_are_false() -> None:
    authority = manifest()["execution_authority"]
    assert authority and all(value is False for value in authority.values())


def test_live_policy_binding_is_unchanged() -> None:
    data = manifest()
    runtime = data["runtime"]
    assert runtime["requirements_bytes"] == 58
    assert runtime["requirements_sha256"] == "9aa1f17cc4a36a3ac502862eb42d84044799eaf1b4de7c8cb1e31a25b10c3440"
