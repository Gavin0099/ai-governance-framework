from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Mapping, Sequence


SCHEMA = "c1-nonhosted-sandbox-capability-probe-freeze.v1"
ATTEMPT_ID = "C1-nonhosted-sandbox-capability-probe-01"
FREEZE_REPO_DIR = (
    "artifacts/experiments/prepush-bugfix-20260724/gate1-preregistration/"
    "c1-nonhosted-sandbox-capability-probe-implementation-freeze-20260828"
)
MANIFEST_REPO_PATH = f"{FREEZE_REPO_DIR}/capability-probe-manifest.json"
EXECUTOR_NAME = "capability_probe_executor.py"
MARKER_NAME = "marker_probe.py"
CONFIG_NAME = "sandbox-config.toml"
REQUIREMENTS_NAME = "sandbox-requirements.toml"
MARKER_BYTES = b"C1_ABSOLUTE_PYTHON_TASK_PLANE_MARKER_V1\n"
HEX40 = set("0123456789abcdef")
INHERITED_ENV_KEYS = (
    "COMSPEC",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class LaunchResult:
    returncode: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes


Launcher = Callable[[Sequence[str], Path, Mapping[str, str], float], LaunchResult]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo}",
            "-C",
            str(repo),
            *args,
        ],
        check=True,
        capture_output=True,
    )
    if completed.stderr:
        raise ProbeError("git binding command produced stderr")
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def _commit_blob(repo: Path, commit: str, path: str) -> tuple[str, bytes]:
    oid = str(_git(repo, "rev-parse", f"{commit}:{path}"))
    payload = _git(repo, "cat-file", "blob", oid, binary=True)
    assert isinstance(payload, bytes)
    return oid, payload


def _json_object(payload: bytes, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"invalid JSON binding: {label}") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"JSON binding is not an object: {label}")
    return value


def _safe_repo_path(raw: str, label: str) -> PurePosixPath:
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        not posix.parts
        or posix.is_absolute()
        or windows.drive
        or windows.root
        or "." in posix.parts
        or ".." in posix.parts
        or "." in windows.parts
        or ".." in windows.parts
    ):
        raise ProbeError(f"unsafe repo path: {label}")
    return posix


def _contained(root: Path, raw: str, label: str) -> Path:
    anchor = root.resolve()
    candidate = anchor.joinpath(*_safe_repo_path(raw, label).parts).resolve()
    try:
        candidate.relative_to(anchor)
    except ValueError as exc:
        raise ProbeError(f"bound path escapes repo: {label}") from exc
    return candidate


def _manifest(repo: Path, commit: str) -> Mapping[str, object]:
    _, payload = _commit_blob(repo, commit, MANIFEST_REPO_PATH)
    value = _json_object(payload, "manifest")
    if value.get("schema") != SCHEMA:
        raise ProbeError("manifest schema mismatch")
    return value


def _verified_frozen_blobs(
    repo: Path, commit: str, manifest: Mapping[str, object]
) -> Mapping[str, bytes]:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise ProbeError("frozen inventory unavailable")
    tree = str(_git(repo, "ls-tree", "--name-only", f"{commit}:{FREEZE_REPO_DIR}"))
    actual = {line for line in tree.splitlines() if line}
    expected = {"capability-probe-manifest.json"}
    blobs: dict[str, bytes] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            raise ProbeError("invalid frozen inventory entry")
        rel = str(raw["path"])
        _safe_repo_path(rel, f"frozen:{rel}")
        expected.add(rel)
        oid, payload = _commit_blob(repo, commit, f"{FREEZE_REPO_DIR}/{rel}")
        if (
            oid != raw.get("git_blob_oid")
            or len(payload) != raw.get("bytes")
            or _sha256(payload) != raw.get("sha256")
        ):
            raise ProbeError(f"frozen file binding mismatch: {rel}")
        blobs[rel] = payload
    if actual != expected:
        raise ProbeError("frozen directory inventory drift")
    return blobs


def _validate_source_bindings(
    repo: Path, manifest: Mapping[str, object]
) -> None:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise ProbeError("source bindings unavailable")
    for raw in entries:
        if not isinstance(raw, dict):
            raise ProbeError("invalid source binding")
        commit = str(raw["commit"])
        path = str(raw["path"])
        _safe_repo_path(path, f"source:{path}")
        oid, payload = _commit_blob(repo, commit, path)
        if (
            oid != raw.get("git_blob_oid")
            or len(payload) != raw.get("bytes")
            or _sha256(payload) != raw.get("sha256")
        ):
            raise ProbeError(f"source binding mismatch: {path}")


def _validate_external_bindings(manifest: Mapping[str, object]) -> None:
    entries = manifest.get("external_bindings")
    if not isinstance(entries, list):
        raise ProbeError("external bindings unavailable")
    for raw in entries:
        if not isinstance(raw, dict):
            raise ProbeError("invalid external binding")
        path = Path(str(raw["path"]))
        if not path.is_absolute() or not path.is_file():
            raise ProbeError(f"external binding unavailable: {raw.get('label')}")
        if path.stat().st_size != raw.get("bytes") or _sha256_file(path) != raw.get(
            "sha256"
        ):
            raise ProbeError(f"external binding mismatch: {raw.get('label')}")


def _paths(repo: Path, manifest: Mapping[str, object]) -> Mapping[str, Path]:
    raw = manifest.get("derived_paths")
    if not isinstance(raw, dict):
        raise ProbeError("derived paths unavailable")
    return {
        "output": _contained(repo, str(raw["output_root"]), "output_root"),
        "cli": _contained(repo, str(raw["cli_staging_root"]), "cli_staging_root"),
        "private": _contained(repo, str(raw["private_root"]), "private_root"),
        "cli_source": Path(str(raw["installed_cli_source"])),
        "python": Path(str(raw["python_executable"])),
        "policy": Path(str(raw["live_machine_policy"])),
    }


def _validate_runtime(paths: Mapping[str, Path], manifest: Mapping[str, object]) -> None:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise ProbeError("runtime binding unavailable")
    checks = (
        ("cli_source", "cli_executable_bytes", "cli_executable_sha256"),
        ("python", "python_executable_bytes", "python_executable_sha256"),
        ("policy", "requirements_bytes", "requirements_sha256"),
    )
    for path_key, bytes_key, digest_key in checks:
        path = paths[path_key]
        if not path.is_file():
            raise ProbeError(f"runtime file unavailable: {path_key}")
        if path.stat().st_size != runtime.get(bytes_key) or _sha256_file(path) != runtime.get(
            digest_key
        ):
            raise ProbeError(f"runtime binding mismatch: {path_key}")


def _assert_roots_absent(paths: Mapping[str, Path]) -> None:
    output = paths["output"]
    for path in (output, paths["cli"], paths["private"]):
        if path.exists():
            raise ProbeError(f"create-once root already exists: {path.name}")


def _claim_attempt(output: Path) -> None:
    if not output.parent.is_dir():
        raise ProbeError("frozen evidence root unavailable")
    try:
        output.mkdir()
    except FileExistsError as exc:
        raise ProbeError("attempt output already claimed") from exc


def _raw_copy_exact(source: Path, target: Path, size: int, digest: str) -> None:
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=8 * 1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if target.stat().st_size != size or _sha256_file(target) != digest:
        raise ProbeError("staged CLI binding mismatch")


def _minimal_environment(private_root: Path) -> Mapping[str, str]:
    environment = {
        key: os.environ[key] for key in INHERITED_ENV_KEYS if key in os.environ
    }
    environment["CODEX_HOME"] = str(private_root / "codex-home")
    environment["NO_COLOR"] = "1"
    if "PATH" in environment:
        raise ProbeError("PATH entered the frozen environment")
    return environment


def _command(cli: Path, workspace: Path, executable: str, marker: Path) -> list[str]:
    argv = [
        str(cli),
        "sandbox",
        "-C",
        str(workspace),
        "-c",
        'sandbox_mode="workspace-write"',
        "-c",
        'approval_policy="never"',
        "-c",
        'windows.sandbox="elevated"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "--",
        executable,
        str(workspace / MARKER_NAME),
        "--output",
        str(marker),
    ]
    if "windows" in argv[1:3]:
        raise ProbeError("forbidden helper subcommand")
    return argv


def _default_launcher(
    argv: Sequence[str], cwd: Path, env: Mapping[str, str], timeout: float
) -> LaunchResult:
    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            input=b"",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return LaunchResult(completed.returncode, False, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return LaunchResult(None, True, exc.stdout or b"", exc.stderr or b"")


def _preflight_cli(cli: Path, cwd: Path, env: Mapping[str, str]) -> None:
    completed = subprocess.run(
        [str(cli), "--version"],
        cwd=cwd,
        env=dict(env),
        input=b"",
        capture_output=True,
        timeout=10.0,
        check=False,
    )
    if (
        completed.returncode != 0
        or completed.stderr
        or _sha256(completed.stdout)
        != "867f4045c33a719c57ed0fc3751a5d9de8dbdb78494a64f43a73ca5c76ef71c5"
    ):
        raise ProbeError("CLI version preflight failed")


def _result_evidence(result: LaunchResult) -> Mapping[str, object]:
    return {
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stdout_sha256": _sha256(result.stdout),
        "stderr_sha256": _sha256(result.stderr),
    }


def _classify(
    negative: LaunchResult,
    positive: LaunchResult | None,
    negative_marker: bytes | None,
    positive_marker: bytes | None,
) -> str:
    return _classify_with_stage(
        negative, positive, negative_marker, positive_marker
    )[0]


def _classify_with_stage(
    negative: LaunchResult,
    positive: LaunchResult | None,
    negative_marker: bytes | None,
    positive_marker: bytes | None,
) -> tuple[str, str]:
    if negative.timed_out or negative.returncode is None:
        return "CAPABILITY_PROBE_SURFACE_UNAVAILABLE", "bare_control_result"
    if negative.returncode == 0 or negative_marker is not None:
        return "CAPABILITY_PROBE_AMBIGUOUS", "bare_control_result"
    if positive is None or positive.timed_out or positive.returncode is None:
        return "CAPABILITY_PROBE_SURFACE_UNAVAILABLE", "absolute_control_result"
    if (
        positive.returncode == 0
        and positive.stdout == b""
        and positive.stderr == b""
        and positive_marker == MARKER_BYTES
    ):
        return "ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE", "none"
    if positive.returncode != 0 and positive_marker is None:
        return "CAPABILITY_PROBE_AMBIGUOUS", "absolute_control_result"
    return "CAPABILITY_PROBE_AMBIGUOUS", "marker_validation"


def _terminal(
    *, status: str, commit: str, negative: LaunchResult | None,
    positive: LaunchResult | None, cleanup: str, diagnostic: str,
    failure_stage: str, exception_class: str
) -> bytes:
    value = {
        "schema": "c1-nonhosted-sandbox-capability-probe-terminal.v1",
        "attempt_id": ATTEMPT_ID,
        "status": status,
        "freeze_commit": commit,
        "hosted_request_attempted": False,
        "auth_payload_read": False,
        "capability_probe_executed": negative is not None,
        "negative_control": _result_evidence(negative) if negative else None,
        "positive_control": _result_evidence(positive) if positive else None,
        "cleanup": cleanup,
        "diagnostic": diagnostic,
        "failure_stage": failure_stage,
        "exception_class": exception_class,
        "qualification_03_created": False,
        "randomization_created": False,
    }
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _publish_terminal(output: Path, payload: bytes) -> Mapping[str, object]:
    if not output.is_dir():
        raise ProbeError("attempt output claim unavailable")
    staging = output / ".terminal-staging"
    terminal = output / "terminal.json"
    if terminal.exists() or staging.exists() or any(output.iterdir()):
        raise ProbeError("terminal output already exists")
    try:
        with staging.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if staging.read_bytes() != payload:
            raise ProbeError("terminal readback mismatch")
        os.replace(staging, terminal)
        return _json_object(terminal.read_bytes(), "terminal")
    except BaseException:
        if staging.exists():
            staging.unlink()
        raise


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def execute(
    *, repo_root: Path, owner_authorized_freeze_commit: str,
    launcher: Launcher = _default_launcher
) -> Mapping[str, object]:
    repo = repo_root.resolve()
    commit = owner_authorized_freeze_commit.lower()
    if len(commit) != 40 or any(char not in HEX40 for char in commit):
        raise ProbeError("owner commit is not a full SHA")
    if str(_git(repo, "rev-parse", "HEAD")) != commit:
        raise ProbeError("owner authority does not match repository HEAD")
    manifest = _manifest(repo, commit)
    frozen = _verified_frozen_blobs(repo, commit, manifest)
    _validate_source_bindings(repo, manifest)
    _validate_external_bindings(manifest)
    paths = _paths(repo, manifest)
    _validate_runtime(paths, manifest)
    _assert_roots_absent(paths)
    expected_executor = str(manifest["frozen_executor_sha256"])
    if os.environ.get("C1_CAPABILITY_EXECUTOR_SHA256") != expected_executor:
        raise ProbeError("bootstrap executor authority unavailable")
    runtime = manifest["runtime"]
    assert isinstance(runtime, dict)
    cli_root = paths["cli"]
    private = paths["private"]
    output = paths["output"]
    _claim_attempt(output)
    negative: LaunchResult | None = None
    positive: LaunchResult | None = None
    status = "CAPABILITY_PROBE_SURFACE_UNAVAILABLE"
    diagnostic = "sandbox helper was unavailable"
    stage = "materialization"
    failure_stage = "none"
    exception_class = "NONE"
    cleanup_failed = False
    try:
        cli_root.mkdir(parents=True)
        private.mkdir(parents=True)
        workspace = private / "workspace"
        codex_home = private / "codex-home"
        workspace.mkdir()
        codex_home.mkdir()
        cli = cli_root / "codex.exe"
        _raw_copy_exact(
            paths["cli_source"], cli,
            int(runtime["cli_executable_bytes"]), str(runtime["cli_executable_sha256"])
        )
        (codex_home / "config.toml").write_bytes(frozen[CONFIG_NAME])
        (codex_home / "requirements.toml").write_bytes(frozen[REQUIREMENTS_NAME])
        (workspace / MARKER_NAME).write_bytes(frozen[MARKER_NAME])
        env = _minimal_environment(private)
        stage = "cli_preflight"
        _preflight_cli(cli, workspace, env)
        negative_path = workspace / "negative.marker"
        positive_path = workspace / "positive.marker"
        stage = "bare_control_launch"
        negative = launcher(_command(cli, workspace, "python", negative_path), workspace, env, 30.0)
        stage = "bare_control_result"
        negative_marker = negative_path.read_bytes() if negative_path.is_file() else None
        if not negative.timed_out and negative.returncode not in (None, 0) and negative_marker is None:
            stage = "absolute_control_launch"
            positive = launcher(
                _command(cli, workspace, str(paths["python"]), positive_path),
                workspace, env, 30.0,
            )
            stage = "absolute_control_result"
        stage = "marker_read"
        positive_marker = positive_path.read_bytes() if positive_path.is_file() else None
        stage = "marker_validation"
        status, failure_stage = _classify_with_stage(
            negative, positive, negative_marker, positive_marker
        )
        diagnostic = {
            "ABSOLUTE_PYTHON_TASK_PLANE_LAUNCHABLE": "absolute Python produced the exact marker",
            "CAPABILITY_PROBE_SURFACE_UNAVAILABLE": "sandbox helper did not complete",
            "CAPABILITY_PROBE_AMBIGUOUS": "control evidence was not uniquely interpretable",
        }[status]
    except (OSError, subprocess.SubprocessError, ProbeError) as exc:
        failure_stage = stage
        exception_class = type(exc).__name__ if type(exc).__name__ in {
            "OSError", "PermissionError", "ProbeError", "TimeoutExpired"
        } else "OTHER"
        status = (
            "CAPABILITY_PROBE_SURFACE_UNAVAILABLE"
            if stage in {"cli_preflight", "bare_control_launch", "absolute_control_launch"}
            else "CAPABILITY_PROBE_AMBIGUOUS"
        )
        diagnostic = "bounded probe stage failed"
    finally:
        for root in (private, cli_root):
            try:
                _remove_tree(root)
            except OSError:
                cleanup_failed = True
    if cleanup_failed or private.exists() or cli_root.exists():
        status = "CAPABILITY_PROBE_CLEANUP_FAILED"
        diagnostic = "private or CLI cleanup failed"
        cleanup = "FAILED"
        failure_stage = "cleanup"
    else:
        cleanup = "COMPLETE"
    payload = _terminal(
        status=status, commit=commit, negative=negative, positive=positive,
        cleanup=cleanup, diagnostic=diagnostic, failure_stage=failure_stage,
        exception_class=exception_class,
    )
    return _publish_terminal(output, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    return parser


def main() -> int:
    if sys.argv[0] != "-" or globals().get("__file__") != "<stdin>":
        raise ProbeError("executor must be streamed by the authorized bootstrap")
    args = _parser().parse_args()
    terminal = execute(
        repo_root=Path(args.repo_root),
        owner_authorized_freeze_commit=args.owner_authorized_freeze_commit,
    )
    print(json.dumps(terminal, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
