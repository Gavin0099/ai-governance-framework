"""Command line entry point for the single-session calibration probe.

The probe orchestrator takes an injected runner and never starts a session
itself, which is what makes it testable without credentials. This module is the
one place that supplies a real runner, so everything that touches credentials
stays in one reviewable seam.

What this does not do, deliberately:

* It does not admit anything, score anything, or build a packet.
* It does not run a pair. It calls the calibration runner, which refuses any
  authorization other than the calibration one and invokes exactly one session.
* It does not authorize itself. ``--authorization`` must carry the calibration
  authorization string, and both this module and the runner check it.

Usage:
    python gate3_codex_calibration_cli.py \\
        --authorization non_counted_codex_calibration_probe_only \\
        --run-id <id> --out <receipt path> --prompt <file> \\
        --model ... --cli-version ... --comp-hash ... --effort ...
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
SNAPSHOT_MANIFEST_ENV = "GATE3_CALIBRATION_SNAPSHOT_MANIFEST"
SNAPSHOT_LOCK_HANDLES_ENV = "GATE3_CALIBRATION_SNAPSHOT_LOCK_HANDLES"
SNAPSHOT_SCHEMA = "gate3-codex-calibration-runtime-snapshot.v1"
_SNAPSHOT_VERIFIED = False
SNAPSHOT_FILES = (
    "gate3_codex_calibration_cli.py",
    "gate3_codex_calibration.py",
    "gate3_codex_calibration_probe.py",
    "gate3_codex_live_canary.py",
    "gate3_evidence_chain.py",
    "gate3_wrapper_semantic_contract.py",
    "gate3_codex_calibration_runner.ps1",
    "gate3_codex_credential_common.ps1",
    "gate3_codex_session_launcher.ps1",
)

# The outer process is only a snapshot bootstrap.  The actual calibration
# imports and executes these modules from the locked snapshot.  Imported use in
# tests remains direct so no test can accidentally start a child process.
_DIRECT_RUNTIME = __name__ != "__main__" or SNAPSHOT_MANIFEST_ENV in os.environ
if _DIRECT_RUNTIME:
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import gate3_codex_calibration as calibration  # noqa: E402
    import gate3_codex_calibration_probe as probe  # noqa: E402
    import gate3_codex_live_canary as live  # noqa: E402

CALIBRATION_RUNNER = HERE / "gate3_codex_calibration_runner.ps1"
ROUTE_PLAN_SCHEMA = "gate3-codex-calibration-route-plan.v2"
RUNNER_RECEIPT_SCHEMA = "gate3-codex-calibration-runner-receipt.v2"


def _snapshot_acl(path: Path) -> None:
    """Apply and verify a protected current-user-only directory ACL."""
    script = r"""
$ErrorActionPreference = 'Stop'
$path = $env:GATE3_SNAPSHOT_ACL_PATH
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object Security.AccessControl.FileSystemAccessRule(
    $identity,
    [Security.AccessControl.FileSystemRights]::FullControl,
    [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Allow
)
$acl.AddAccessRule($rule)
[IO.Directory]::SetAccessControl($path, $acl)
$observed = [IO.Directory]::GetAccessControl($path)
$rules = @($observed.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))
if (-not $observed.AreAccessRulesProtected -or $rules.Count -ne 1 -or
    $rules[0].IdentityReference -ne $identity -or
    $rules[0].AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
    (($rules[0].FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne
        [Security.AccessControl.FileSystemRights]::FullControl)) {
    throw 'snapshot ACL verification failed'
}
"""
    environment = os.environ.copy()
    environment["GATE3_SNAPSHOT_ACL_PATH"] = str(path)
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError("calibration runtime snapshot ACL failed")


def _lock_snapshot_file(path: Path, *, inheritable: bool = False) -> int:
    """Hold a Windows handle that permits reads but denies write/delete."""
    if os.name != "nt":
        raise RuntimeError("calibration runtime snapshot locking is unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    handle = kernel32.CreateFileW(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ only: deny write and delete
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle in (None, invalid):
        raise OSError(ctypes.get_last_error(), "snapshot file lock failed")
    if inheritable:
        kernel32.SetHandleInformation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        if not kernel32.SetHandleInformation(handle, 1, 1):
            kernel32.CloseHandle(handle)
            raise OSError(ctypes.get_last_error(), "snapshot lock inheritance failed")
    return int(handle)


def _close_snapshot_handles(handles: list[int]) -> None:
    if not handles:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    for handle in reversed(handles):
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def _snapshot_payload(root: Path) -> bytes:
    import hashlib

    files = {}
    for name in SNAPSHOT_FILES:
        files[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    return (
        json.dumps(
            {"files": files, "schema": SNAPSHOT_SCHEMA},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _verify_runtime_snapshot() -> None:
    global _SNAPSHOT_VERIFIED
    manifest_text = os.environ.get(SNAPSHOT_MANIFEST_ENV)
    handles_text = os.environ.get(SNAPSHOT_LOCK_HANDLES_ENV)
    if not manifest_text or not handles_text or not handles_text.isascii():
        raise RuntimeError("calibration runtime snapshot is required")
    try:
        inherited_handles = json.loads(handles_text)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("calibration runtime snapshot lock is invalid") from error
    expected_names = {*SNAPSHOT_FILES, "snapshot-manifest.json"}
    if (
        not isinstance(inherited_handles, dict)
        or set(inherited_handles) != expected_names
        or any(type(value) is not int or value <= 0 for value in inherited_handles.values())
    ):
        raise RuntimeError("calibration runtime snapshot lock is invalid")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.argtypes = [ctypes.c_void_p]
    kernel32.GetFileType.restype = ctypes.c_uint32
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_uint32
    manifest = Path(manifest_text).resolve()
    if manifest.parent != HERE or manifest.name != "snapshot-manifest.json":
        raise RuntimeError("calibration runtime snapshot boundary is invalid")
    observed = json.loads(manifest.read_text(encoding="utf-8"))
    expected = json.loads(_snapshot_payload(HERE))
    if observed != expected:
        raise RuntimeError("calibration runtime snapshot identity is invalid")
    # Every executable and the manifest must carry its own inherited lock.
    # Bind each numeric handle to the exact path it protects; an arbitrary
    # valid handle plus a deny-only ACL is not evidence of immutability.
    for name in sorted(expected_names):
        path = manifest if name == manifest.name else HERE / name
        inherited_handle = inherited_handles[name]
        if kernel32.GetFileType(ctypes.c_void_p(inherited_handle)) == 0:
            raise RuntimeError("calibration runtime snapshot lock is invalid")
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetFinalPathNameByHandleW(
            ctypes.c_void_p(inherited_handle), buffer, len(buffer), 0
        )
        if length == 0 or length >= len(buffer):
            raise RuntimeError("calibration runtime snapshot lock is invalid")
        handle_path = buffer.value
        if handle_path.startswith("\\\\?\\UNC\\"):
            handle_path = "\\\\" + handle_path[8:]
        elif handle_path.startswith("\\\\?\\"):
            handle_path = handle_path[4:]
        if Path(handle_path).resolve() != path.resolve():
            raise RuntimeError("calibration runtime snapshot lock path differs")
        write_handle = kernel32.CreateFileW(
            str(path),
            0x40000000,  # GENERIC_WRITE
            0x00000001,
            None,
            3,
            0x00000080,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if write_handle not in (None, invalid):
            kernel32.CloseHandle(write_handle)
            raise RuntimeError("calibration runtime snapshot is not locked")
        if ctypes.get_last_error() != 32:  # ERROR_SHARING_VIOLATION
            raise RuntimeError("calibration runtime snapshot lock is not proven")
    _SNAPSHOT_VERIFIED = True


def _run_from_runtime_snapshot(
    argv: list[str],
    *,
    _source_root: Path = HERE,
    _acl_setter: Callable[[Path], None] = _snapshot_acl,
    _after_locked: Callable[[Path], None] | None = None,
    _executor: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> int:
    """Execute the calibration from one ACL-protected, read-locked snapshot."""
    snapshot = Path(tempfile.mkdtemp(prefix="gate3-calibration-runtime-")).resolve()
    handles: list[int] = []
    try:
        _acl_setter(snapshot)
        for name in SNAPSHOT_FILES:
            shutil.copyfile(_source_root / name, snapshot / name)
        manifest = snapshot / "snapshot-manifest.json"
        manifest.write_bytes(_snapshot_payload(snapshot))
        inherited_handles: dict[str, int] = {}
        for name in SNAPSHOT_FILES:
            handle = _lock_snapshot_file(snapshot / name, inheritable=True)
            inherited_handles[name] = handle
            handles.append(handle)
        manifest_handle = _lock_snapshot_file(manifest, inheritable=True)
        inherited_handles[manifest.name] = manifest_handle
        handles.append(manifest_handle)
        if _after_locked is not None:
            _after_locked(snapshot)
        environment = os.environ.copy()
        environment[SNAPSHOT_MANIFEST_ENV] = str(manifest)
        environment[SNAPSHOT_LOCK_HANDLES_ENV] = json.dumps(
            inherited_handles, sort_keys=True, separators=(",", ":")
        )
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = _executor(
            [sys.executable, str(snapshot / Path(__file__).name), *argv],
            env=environment,
            check=False,
            close_fds=False,
        )
        return int(completed.returncode)
    finally:
        _close_snapshot_handles(handles)
        shutil.rmtree(snapshot)


def _route_plan_bytes() -> bytes:
    return live._json_bytes(
        {
            "authorization": calibration.AUTHORIZATION,
            "frozen_route": {
                "calibration_runner_implementation_sha256": (
                    live._sha256_file(CALIBRATION_RUNNER)
                ),
                "credential_common_implementation_sha256": (
                    live._sha256_file(live.DEFAULT_CREDENTIAL_COMMON)
                ),
                "launcher_implementation_sha256": live._sha256_file(
                    live.DEFAULT_SESSION_LAUNCHER
                ),
            },
            "schema": ROUTE_PLAN_SCHEMA,
        }
    )


def _route_plan(path: Path) -> str:
    """Pin every executable the runner will load, including the shared file."""
    payload = _route_plan_bytes()
    path.write_bytes(payload)
    return live._sha256_bytes(payload)


def _implementation_identity() -> dict[str, str]:
    return {
        "calibration_cli_sha256": live._sha256_file(Path(__file__)),
        "calibration_collector_sha256": live._sha256_file(
            Path(calibration.__file__)
        ),
        "calibration_probe_sha256": live._sha256_file(Path(probe.__file__)),
        "calibration_runner_sha256": live._sha256_file(CALIBRATION_RUNNER),
        "credential_common_sha256": live._sha256_file(
            live.DEFAULT_CREDENTIAL_COMMON
        ),
        "evidence_chain_sha256": live._sha256_file(Path(live.chain.__file__)),
        "live_canary_sha256": live._sha256_file(Path(live.__file__)),
        "route_plan_sha256": live._sha256_bytes(_route_plan_bytes()),
        "session_launcher_sha256": live._sha256_file(
            live.DEFAULT_SESSION_LAUNCHER
        ),
        "wrapper_contract_sha256": live._sha256_file(
            Path(live.contract.__file__)
        ),
    }


def _remove_private_root(root: Path) -> None:
    for _attempt in range(2):
        try:
            shutil.rmtree(root)
        except OSError:
            pass
        if not root.exists():
            return
    raise probe.ProbeError(
        "calibration runner private cleanup failed",
        residue_classes=("runner_private_runtime",),
    )


def _live_runner(
    prompt_path: Path,
    codex_command: str,
    implementation_identity: dict[str, str],
    *,
    _acl_setter: probe.AclSetter | None = None,
    _cleanup: Callable[[Path], None] = _remove_private_root,
) -> probe.Runner:
    """Build a runner that invokes exactly one real calibration session.

    The private tree lives under the user Temp root the runner confines to,
    and is removed whether or not the session succeeded. The rollout is read
    out before removal; nothing else survives the call.
    """

    if _acl_setter is None:
        _acl_setter = probe._windows_current_user_only_acl

    def run() -> probe.RunnerResult:
        private_root = Path(
            tempfile.mkdtemp(prefix="gate3-calibration-private-")
        ).resolve()
        try:
            # Apply and verify the ACL before writing prompt, output, receipt,
            # route-plan or CODEX_HOME bytes anywhere below this root.
            _acl_setter(private_root, True)
            workspace = private_root / "workspace"
            workspace.mkdir()
            live._git(workspace, "init", "-q")
            codex_home = private_root / "codex-home"
            codex_home.mkdir()
            private = private_root / "private"
            private.mkdir()
            prompt = private_root / "prompt.txt"
            prompt.write_bytes(prompt_path.read_bytes())
            plan = private_root / "route-plan.json"
            route_plan_sha256 = _route_plan(plan)
            if route_plan_sha256 != implementation_identity["route_plan_sha256"]:
                raise probe.ProbeError("calibration route plan identity drifted")
            receipt = private / "calibration-runner-receipt.json"
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(CALIBRATION_RUNNER),
                    "-Authorization",
                    calibration.AUTHORIZATION,
                    "-CodexCommand",
                    codex_command,
                    "-RoutePlanPath",
                    str(plan),
                    "-Workspace",
                    str(workspace),
                    "-PromptPath",
                    str(prompt),
                    "-CodexHome",
                    str(codex_home),
                    "-StdoutPath",
                    str(private / "session.stdout"),
                    "-StderrPath",
                    str(private / "session.stderr"),
                    "-ExitCodePath",
                    str(private / "session.exit"),
                    "-PrivateReceiptPath",
                    str(receipt),
                ],
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise probe.ProbeError("calibration runner failed closed")
            observed = json.loads(receipt.read_text(encoding="utf-8"))
            if (
                observed.get("schema") != RUNNER_RECEIPT_SCHEMA
                or observed.get("session_invocations") != 1
                or observed.get("replacement_sessions") != 0
                or observed.get("authorization") != calibration.AUTHORIZATION
                or observed.get("auth_files_removed") is not True
                or observed.get("secret_material_retained") is not False
                or observed.get("route_plan_sha256") != route_plan_sha256
                or observed.get("implementation")
                != {
                    "calibration_runner_sha256": implementation_identity[
                        "calibration_runner_sha256"
                    ],
                    "credential_common_sha256": implementation_identity[
                        "credential_common_sha256"
                    ],
                    "launcher_sha256": implementation_identity[
                        "session_launcher_sha256"
                    ],
                }
            ):
                raise probe.ProbeError("calibration runner receipt is invalid")
            rollout = live._single_rollout(codex_home)
            return probe.RunnerResult(rollout.read_bytes(), 0)
        finally:
            _cleanup(private_root)

    return run


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--workspace-token", default=live.GENERIC_CONTEXT_TOKEN)
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--model", default=live.DEFAULT_MODEL)
    parser.add_argument("--cli-version", default=live.DEFAULT_CLI_VERSION)
    parser.add_argument("--comp-hash", default=live.DEFAULT_COMP_HASH)
    parser.add_argument("--effort", default=live.DEFAULT_REASONING)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    result: dict[str, object]
    try:
        if args.authorization != calibration.AUTHORIZATION:
            raise probe.ProbeError("calibration authorization is invalid")
        implementation_identity = _implementation_identity()
        published = probe.orchestrate(
            args.out,
            run_id=args.run_id,
            authorization=args.authorization,
            expected_workspace=args.workspace_token,
            expected_prompt=args.prompt.read_bytes(),
            signed_identity={
                "cli_version": args.cli_version,
                "comp_hash": args.comp_hash,
                "effort": args.effort,
                "model": args.model,
            },
            implementation_identity=implementation_identity,
            private_parent=Path(tempfile.gettempdir()),
            runner=_live_runner(
                args.prompt,
                args.codex_command,
                implementation_identity,
            ),
        )
        result = {
            "public_receipt": str(published.public_receipt),
            "status": "PASS",
        }
    except (probe.ProbeError, live.CanaryError, OSError, ValueError) as exc:
        result = {"error": str(exc), "status": "FAIL"}
        if args.json_out is not None:
            args.json_out.write_text(
                json.dumps(result, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(str(exc), file=sys.stderr)
        return 2
    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(result, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    if not _SNAPSHOT_VERIFIED:
        raise RuntimeError("calibration runtime snapshot is required")
    return _main(argv)


if __name__ == "__main__":
    if SNAPSHOT_MANIFEST_ENV in os.environ:
        _verify_runtime_snapshot()
        raise SystemExit(main())
    raise SystemExit(_run_from_runtime_snapshot(sys.argv[1:]))
