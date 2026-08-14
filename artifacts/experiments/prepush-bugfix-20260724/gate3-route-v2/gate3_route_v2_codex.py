from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import gate3_route_v2 as route


PINNED_CLI_VERSION = "codex-cli 0.146.0"
COMMAND_CONTRACT_SCHEMA = "gate3-route-v2.codex-command.v2"
PREFLIGHT_CONTRACT_SCHEMA = "gate3-route-v2.codex-preflight.v2"
REQUIRED_FLAGS = (
    "--ephemeral",
    "--json",
    "--output-last-message",
    "--output-schema",
    "--dangerously-bypass-approvals-and-sandbox",
)
AB_REQUIRED_FLAGS = tuple(sorted((*REQUIRED_FLAGS, "--model")))
ENVIRONMENT_SOURCE_KEYS = (
    "COMSPEC",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)
PROMPT = (
    b"This is a synthetic, non-scoring route check. Read task.md, replace the "
    b"contents of result.txt with exactly CALIBRATION_OK followed by one newline, "
    b"then return only the JSON object required by the output schema.\n"
)
OUTPUT_SCHEMA: dict[str, Any] = {
    "additionalProperties": False,
    "properties": {"status": {"enum": ["ok"], "type": "string"}},
    "required": ["status"],
    "type": "object",
}
BASELINE_WORKSPACE = {
    "task.md": b"Produce the exact synthetic result requested by the prompt.\n",
    "result.txt": b"PENDING\n",
}
EXPECTED_WORKSPACE = {
    "task.md": BASELINE_WORKSPACE["task.md"],
    "result.txt": b"CALIBRATION_OK\n",
}
COMMAND_TEMPLATE = (
    "<pinned-python-job-guard-on-windows>",
    "<measured-executable-snapshot>",
    "exec",
    "--json",
    "--ephemeral",
    "--output-last-message",
    "<private-final-message>",
    "--output-schema",
    "<private-output-schema>",
    "--dangerously-bypass-approvals-and-sandbox",
    "-",
)
AB_COMMAND_TEMPLATE = COMMAND_TEMPLATE[:-1] + (
    "--model",
    "<owner-selected-model>",
    "-",
)
WINDOWS_GUARD = (
    "import os,pathlib,sys,time\n"
    "p=pathlib.Path(sys.argv[1])\n"
    "while not p.exists():\n"
    "    time.sleep(.005)\n"
    "os.execv(sys.argv[2],sys.argv[2:])\n"
)


def _implementation_sha256() -> str:
    return route._sha256_file(Path(__file__))


def _command_contract_sha256() -> str:
    return route._sha256_bytes(
        route._json_bytes(
            {
                "argv": list(COMMAND_TEMPLATE),
                "schema": COMMAND_CONTRACT_SCHEMA,
                "windows_guard": {
                    "interpreter_sha256": route._sha256_file(Path(sys.executable)),
                    "isolated_flags": ["-I", "-S"],
                    "source_sha256": route._sha256_bytes(WINDOWS_GUARD.encode("utf-8")),
                },
            }
        )
    )


def _ab_command_contract_sha256() -> str:
    return route._sha256_bytes(
        route._json_bytes(
            {
                "argv": list(AB_COMMAND_TEMPLATE),
                "schema": "gate3-route-v2.codex-ab-command.v1",
                "windows_guard": {
                    "interpreter_sha256": route._sha256_file(Path(sys.executable)),
                    "isolated_flags": ["-I", "-S"],
                    "source_sha256": route._sha256_bytes(
                        WINDOWS_GUARD.encode("utf-8")
                    ),
                },
            }
        )
    )


def _environment_policy_sha256() -> str:
    return route._sha256_bytes(
        route._json_bytes(
            {
                "fixed": {"NO_COLOR": "1"},
                "internal": ["CODEX_HOME"],
                "source_allowlist": list(ENVIRONMENT_SOURCE_KEYS),
                "schema": "gate3-route-v2.environment-policy.v1",
            }
        )
    )


def _closed_environment(codex_home: Path) -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in ENVIRONMENT_SOURCE_KEYS
        if key in os.environ and os.environ[key]
    }
    env["CODEX_HOME"] = str(codex_home)
    env["NO_COLOR"] = "1"
    return env


def _environment_projection_sha256(env: Mapping[str, str]) -> str:
    projection: dict[str, str] = {
        "CODEX_HOME": "isolated_private_home",
        "NO_COLOR": "1",
    }
    if os.name == "nt":
        required = {"COMSPEC", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
        if not required <= set(env):
            raise route.RouteV2Error("closed environment lacks a required OS value")
        system_root = Path(env["SYSTEMROOT"]).resolve()
        if Path(env["WINDIR"]).resolve() != system_root:
            raise route.RouteV2Error("Windows system roots differ")
        expected_comspec = (system_root / "System32" / "cmd.exe").resolve()
        if Path(env["COMSPEC"]).resolve() != expected_comspec:
            raise route.RouteV2Error("Windows command processor is untrusted")
        if Path(env["TEMP"]).resolve() != Path(env["TMP"]).resolve():
            raise route.RouteV2Error("Windows temporary roots differ")
        projection.update(
            {
                "COMSPEC": "system32_cmd",
                "SYSTEMROOT": "windows_system_root",
                "TEMP": "operator_temp_root",
                "TMP": "operator_temp_root",
                "WINDIR": "windows_system_root",
            }
        )
    for key in ("PATHEXT", "SYSTEMDRIVE"):
        if key in env:
            projection[key] = "present"
    return route._sha256_bytes(
        route._json_bytes(
            {"projection": projection, "schema": "gate3-route-v2.environment-projection.v1"}
        )
    )


def _safe_artifact_path(root: Path, artifact_id: str) -> Path:
    if route.ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
        raise route.RouteV2Error("workspace artifact identity is invalid")
    path = (root / artifact_id).resolve()
    if path.parent != root.resolve():
        raise route.RouteV2Error("workspace artifact escapes the synthetic root")
    return path


def _fixed_paths(run_id: str) -> dict[str, Path]:
    run_id = route._validate_run_id(run_id)
    root = route.TRUSTED_ROUTE_ROOT.resolve()
    return {
        "external": root / "external",
        "final_pin": root / "pins" / run_id / "final.sha256",
        "locator": root / "locators",
        "output": root / "public" / run_id,
        "private": root / "private" / f"gate3-v2-{run_id}",
        "terminal_pin": root / "pins" / run_id / "terminal.sha256",
        "trusted": root,
    }


def _validate_fixed_paths(run_id: str) -> dict[str, Path]:
    paths = {name: value.resolve() for name, value in _fixed_paths(run_id).items()}
    root = paths["trusted"]
    for name, path in paths.items():
        if name != "trusted" and root not in path.parents:
            raise route.RouteV2Error("fixed route path escapes the trusted root")
    if len({str(path).casefold() for path in paths.values()}) != len(paths):
        raise route.RouteV2Error("fixed route paths overlap")
    collision_targets = (
        paths["output"],
        paths["private"],
        paths["locator"] / run_id,
        paths["external"] / f"{run_id}.terminal.json",
        paths["final_pin"],
        paths["terminal_pin"],
    )
    if any(path.exists() for path in collision_targets):
        raise route.RouteV2Error("fixed route output collision")
    return paths


def _probe_publication_parents(paths: Mapping[str, Path]) -> None:
    parents = {
        paths["output"].parent,
        paths["locator"],
        paths["external"],
        paths["final_pin"].parent,
    }
    for parent in parents:
        parent.mkdir(parents=True, exist_ok=True)
        route._current_user_only(parent, True)
        route._verify_current_user_only(parent, True)
        probe = parent / ".gate3-v2-create-once-probe"
        try:
            route._publish_create_once(probe, b"probe\n")
            if probe.read_bytes() != b"probe\n":
                raise route.RouteV2Error("fixed publication probe differs")
        finally:
            probe.unlink(missing_ok=True)


@dataclass(frozen=True)
class _ContainedResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    tree_terminated: bool


def _run_contained(
    command: Sequence[str],
    *,
    input_bytes: bytes,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> _ContainedResult:
    """Run one command and leave no descendant alive after return."""
    creationflags = 0
    start_new_session = os.name != "nt"
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    actual_command = list(command)
    gate: Path | None = None
    if os.name == "nt":
        gate = cwd / f".gate3-job-{uuid.uuid4().hex}"
        if gate.exists():
            raise route.RouteV2Error("process gate collision")
        actual_command = [
            sys.executable, "-I", "-S", "-c", WINDOWS_GUARD,
            str(gate), *actual_command,
        ]
    process = subprocess.Popen(
        actual_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=dict(env),
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    job = None
    if os.name == "nt":
        try:
            job = _assign_kill_on_close_job(process)
            assert gate is not None
            gate.write_bytes(b"go")
        except BaseException:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if job is not None:
                _close_job(job)
            if gate is not None:
                gate.unlink(missing_ok=True)
            raise
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=input_bytes, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            _terminate_job(job)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    finally:
        if os.name == "nt":
            _terminate_job(job)
            tree_terminated = _job_is_empty(job)
            _close_job(job)
            if gate is not None:
                gate.unlink(missing_ok=True)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            tree_terminated = True
    if not tree_terminated:
        raise route.RouteV2Error("process tree cleanup is incomplete")
    return _ContainedResult(
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        tree_terminated=tree_terminated,
    )


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


def _assign_kill_on_close_job(process: subprocess.Popen[bytes]) -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    )
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise route.RouteV2Error("Windows Job Object creation failed")
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        job, 9, ctypes.byref(info), ctypes.sizeof(info)
    ):
        kernel32.CloseHandle(job)
        raise route.RouteV2Error("Windows Job Object policy failed")
    if not kernel32.AssignProcessToJobObject(job, int(process._handle)):
        kernel32.CloseHandle(job)
        process.kill()
        process.wait()
        raise route.RouteV2Error("Windows Job Object assignment failed")
    return int(job)


def _close_job(job: int | None) -> None:
    if job is None:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle(job)


def _terminate_job(job: int | None) -> None:
    if job is not None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject(job, 1)


def _job_is_empty(job: int | None) -> bool:
    if job is None:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    info = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
    for _ in range(50):
        if not kernel32.QueryInformationJobObject(
            job, 1, ctypes.byref(info), ctypes.sizeof(info), None
        ):
            return False
        if info.ActiveProcesses == 0:
            return True
        time.sleep(0.01)
    return False


Probe = Callable[[Sequence[str], Path, Mapping[str, str]], _ContainedResult]


_ZERO_SESSION_HELPER_FILES = frozenset(
    {".lock", "applypatch.bat", "apply_patch.bat"}
)
_CLEANUP_ATTEMPTS = 20
_CLEANUP_DELAY_SECONDS = 0.05


def _is_reparse_stat(value: os.stat_result) -> bool:
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _closed_directory_entries(path: Path, expected: set[str], label: str) -> None:
    try:
        root_value = os.lstat(path)
    except OSError as exc:
        raise route.RouteV2Error(f"{label} is unreadable") from exc
    if not stat.S_ISDIR(root_value.st_mode) or _is_reparse_stat(root_value):
        raise route.RouteV2Error("zero-session preflight created private residue")
    try:
        with os.scandir(path) as scanned:
            entries = {entry.name: entry for entry in scanned}
    except OSError as exc:
        raise route.RouteV2Error(f"{label} is unreadable") from exc
    if set(entries) != expected:
        raise route.RouteV2Error("zero-session preflight created private residue")
    for entry in entries.values():
        try:
            value = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise route.RouteV2Error(f"{label} is unreadable") from exc
        if _is_reparse_stat(value):
            raise route.RouteV2Error("zero-session preflight created private residue")


def _validate_closed_zero_session_residue(home: Path) -> None:
    """Accept only the pinned CLI's observed closed helper topology."""
    try:
        home_value = os.lstat(home)
    except OSError as exc:
        raise route.RouteV2Error("zero-session helper root is unreadable") from exc
    if not stat.S_ISDIR(home_value.st_mode) or _is_reparse_stat(home_value):
        raise route.RouteV2Error("zero-session preflight created private residue")
    try:
        with os.scandir(home) as entries:
            empty = next(entries, None) is None
    except OSError as exc:
        raise route.RouteV2Error("zero-session helper root is unreadable") from exc
    if empty:
        return
    _closed_directory_entries(home, {"tmp"}, "zero-session helper root")
    tmp = home / "tmp"
    if not tmp.is_dir():
        raise route.RouteV2Error("zero-session preflight created private residue")
    _closed_directory_entries(tmp, {"arg0"}, "zero-session helper tmp")
    arg0 = tmp / "arg0"
    if not arg0.is_dir():
        raise route.RouteV2Error("zero-session preflight created private residue")
    try:
        with os.scandir(arg0) as entries:
            helpers = list(entries)
    except OSError as exc:
        raise route.RouteV2Error("zero-session helper arg0 is unreadable") from exc
    if len(helpers) != 1:
        raise route.RouteV2Error("zero-session preflight created private residue")
    helper = helpers[0]
    suffix = helper.name.removeprefix("codex-arg0")
    try:
        helper_stat = helper.stat(follow_symlinks=False)
    except OSError as exc:
        raise route.RouteV2Error("zero-session helper is unreadable") from exc
    if (
        not helper.name.startswith("codex-arg0")
        or not suffix
        or not suffix.isascii()
        or not suffix.isalnum()
        or not stat.S_ISDIR(helper_stat.st_mode)
        or _is_reparse_stat(helper_stat)
    ):
        raise route.RouteV2Error("zero-session preflight created private residue")
    helper_path = Path(helper.path)
    _closed_directory_entries(
        helper_path, set(_ZERO_SESSION_HELPER_FILES), "zero-session helper"
    )
    for name in _ZERO_SESSION_HELPER_FILES:
        path = helper_path / name
        value = os.lstat(path)
        if (
            not stat.S_ISREG(value.st_mode)
            or value.st_nlink != 1
            or (name == ".lock" and value.st_size != 0)
            or (name != ".lock" and not 0 < value.st_size <= 65_536)
        ):
            raise route.RouteV2Error("zero-session preflight created private residue")


def _remove_tree_once(path: Path) -> None:
    value = os.lstat(path)
    if _is_reparse_stat(value):
        if stat.S_ISDIR(value.st_mode):
            os.rmdir(path)
        else:
            os.unlink(path)
        return
    if not stat.S_ISDIR(value.st_mode):
        if value.st_nlink > 1:
            os.unlink(path)
            return
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)
        return
    with os.scandir(path) as entries:
        children = [Path(entry.path) for entry in entries]
    for child in children:
        _remove_tree_once(child)
    os.chmod(path, stat.S_IWRITE)
    os.rmdir(path)


def _remove_tree_bounded(path: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(_CLEANUP_ATTEMPTS):
        if not os.path.lexists(path):
            return
        try:
            _remove_tree_once(path)
            return
        except OSError as exc:
            last_error = exc
            if attempt + 1 < _CLEANUP_ATTEMPTS:
                time.sleep(_CLEANUP_DELAY_SECONDS)
    raise route.RouteV2Error("zero-session preflight cleanup failed") from last_error


def _native_probe(command: Sequence[str], cwd: Path, env: Mapping[str, str]) -> _ContainedResult:
    return _run_contained(
        command, input_bytes=b"", cwd=cwd, env=env, timeout_seconds=30
    )


def _probe_output(result: _ContainedResult) -> dict[str, object]:
    for payload in (result.stdout, result.stderr):
        if len(payload) > 262_144:
            raise route.PublicPrivacyError("preflight probe output is too large")
        try:
            payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise route.PublicPrivacyError("preflight probe output is not UTF-8") from exc
    return {
        "returncode": result.returncode,
        "stderr_len": len(result.stderr),
        "stderr_sha256": route._sha256_bytes(result.stderr),
        "stdout_len": len(result.stdout),
        "stdout_sha256": route._sha256_bytes(result.stdout),
    }


def _measure_preflight(
    *,
    run_id: str,
    executable: Path,
    expected_executable_sha256: str,
    preflight_root: Path,
    probe: Probe = _native_probe,
    _required_flags: Sequence[str] = REQUIRED_FLAGS,
    _command_contract_digest: str | None = None,
) -> tuple[bytes, Path]:
    if route.SHA256_RE.fullmatch(expected_executable_sha256) is None:
        raise route.RouteV2Error("expected executable identity is invalid")
    source = executable.resolve()
    if not source.is_file() or route._sha256_file(source) != expected_executable_sha256:
        raise route.RouteV2Error("Codex executable differs from the pinned identity")
    owned_root = False
    try:
        preflight_root.mkdir(parents=True)
        owned_root = True
        route._current_user_only(preflight_root, True)
        snapshot = preflight_root / "codex.exe"
        shutil.copyfile(source, snapshot)
        route._current_user_only(snapshot, False)
        if route._sha256_file(snapshot) != expected_executable_sha256:
            raise route.RouteV2Error("executable snapshot differs from source")
        home = preflight_root / "codex-home"
        home.mkdir()
        route._current_user_only(home, True)
        env = _closed_environment(home)
        environment_projection = _environment_projection_sha256(env)
        version = probe((str(snapshot), "--version"), preflight_root, env)
        root_help = probe((str(snapshot), "--help"), preflight_root, env)
        exec_help = probe((str(snapshot), "exec", "--help"), preflight_root, env)
        if any(result.timed_out or result.returncode != 0 for result in (version, root_help, exec_help)):
            raise route.RouteV2Error("Codex zero-session preflight failed")
        observed_version = version.stdout.decode("utf-8", errors="strict").strip()
        root_help_text = (root_help.stdout + root_help.stderr).decode(
            "utf-8", errors="strict"
        )
        exec_help_text = (exec_help.stdout + exec_help.stderr).decode(
            "utf-8", errors="strict"
        )
        if observed_version != PINNED_CLI_VERSION:
            raise route.RouteV2Error("Codex version differs from the frozen version")
        if not root_help_text.strip():
            raise route.RouteV2Error("Codex root help is empty")
        if any(flag not in exec_help_text for flag in _required_flags):
            raise route.RouteV2Error("Codex help lacks a required flag")
        _validate_closed_zero_session_residue(home)
        _remove_tree_bounded(home)
        identity = route._validate_execution_identity(
            {
                "cli_version": observed_version,
                "command_contract_sha256": (
                    _command_contract_digest or _command_contract_sha256()
                ),
                "executable_sha256": expected_executable_sha256,
                "kind": "codex_exec",
                "runner_sha256": _implementation_sha256(),
            }
        )
        payload = route._json_bytes(
            {
                "authorization": route.LIVE_AUTHORIZATION,
                "checks": {
                    "cleanup": "PASS", "exec_help": "PASS",
                    "root_help": "PASS", "version": "PASS",
                },
                "compatibility": {
                    "required_flag_presence": {
                        flag: flag in exec_help_text for flag in sorted(_required_flags)
                    },
                    "root_help_nonempty": bool(root_help_text.strip()),
                    "version_match": observed_version == PINNED_CLI_VERSION,
                },
                "environment_policy_sha256": _environment_policy_sha256(),
                "environment_projection_sha256": environment_projection,
                "execution_identity": identity,
                "probe_outputs": {
                    "exec_help": _probe_output(exec_help),
                    "root_help": _probe_output(root_help),
                    "version": _probe_output(version),
                },
                "required_flags": sorted(_required_flags),
                "run_id": route._validate_run_id(run_id),
                "schema": route.PREFLIGHT_SCHEMA,
            }
        )
        route._validate_public_payload(payload)
        return payload, snapshot
    except BaseException as original_error:
        if owned_root and os.path.lexists(preflight_root):
            try:
                _remove_tree_bounded(preflight_root)
            except BaseException as cleanup_error:
                raise BaseExceptionGroup(
                    "zero-session preflight and cleanup both failed",
                    [original_error, cleanup_error],
                ) from original_error
        raise


def _measure_ab_preflight(**kwargs: Any) -> tuple[bytes, Path]:
    return _measure_preflight(
        **kwargs,
        _required_flags=AB_REQUIRED_FLAGS,
        _command_contract_digest=_ab_command_contract_sha256(),
    )


@dataclass(frozen=True)
class CodexExecRunner:
    run_id: str
    executable_snapshot: Path
    private_root: Path
    auth_payload: bytes
    measured_preflight: bytes
    model_id: str | None = None
    prompt: bytes = PROMPT
    output_schema: Mapping[str, Any] = field(default_factory=lambda: OUTPUT_SCHEMA)
    baseline_workspace: Mapping[str, bytes] = field(default_factory=lambda: BASELINE_WORKSPACE)
    observed_artifact_ids: Sequence[str] = tuple(EXPECTED_WORKSPACE)
    timeout_seconds: int = 300
    _prepared: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.auth_payload, bytes) or not self.auth_payload:
            raise route.RouteV2Error("credential seed payload is invalid")
        if type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 3600:
            raise route.RouteV2Error("runner timeout is invalid")
        if self.model_id is not None:
            route._validate_public_token(self.model_id, "model identity")
        route._validate_schema_definition(dict(self.output_schema))
        route._validate_artifacts(self.baseline_workspace)
        _, identity = route._validate_preflight(
            self.measured_preflight, route._validate_run_id(self.run_id),
            route.LIVE_AUTHORIZATION,
        )
        preflight_value = json.loads(self.measured_preflight)
        expected_flags = (
            sorted(AB_REQUIRED_FLAGS)
            if self.model_id is not None
            else sorted(REQUIRED_FLAGS)
        )
        expected_command_digest = (
            _ab_command_contract_sha256()
            if self.model_id is not None
            else _command_contract_sha256()
        )
        if (
            preflight_value.get("required_flags") != expected_flags
            or identity["command_contract_sha256"] != expected_command_digest
        ):
            raise route.RouteV2Error("runner model and preflight profile differ")
        if identity["executable_sha256"] != route._sha256_file(self.executable_snapshot):
            raise route.RouteV2Error("runner executable differs from measured preflight")

    def execution_identity(self) -> dict[str, str]:
        value = json.loads(self.measured_preflight)["execution_identity"]
        return route._validate_execution_identity(value)

    def preflight_bytes(self) -> bytes:
        return self.measured_preflight

    def trusted_capability(self) -> route.TrustedLiveRunner:
        return route._trusted_live_runner(
            execution_identity=self.execution_identity(),
            preflight=self.preflight_bytes(),
            invoke=self.__call__,
        )

    def command(self, schema_path: Path, final_path: Path) -> list[str]:
        command = [
            str(self.executable_snapshot), "exec", "--json", "--ephemeral",
            "--output-last-message", str(final_path), "--output-schema",
            str(schema_path), "--dangerously-bypass-approvals-and-sandbox",
        ]
        if self.model_id is not None:
            command.extend(("--model", self.model_id))
        command.append("-")
        return command

    def prepare_private(self, staged_workspace: Mapping[str, bytes]) -> None:
        if self._prepared:
            raise route.RouteV2Error("runner private workspace is already prepared")
        private_root = self.private_root.resolve()
        workspace = private_root / "workspace"
        codex_home = private_root / "codex-home"
        if workspace.exists() or codex_home.exists():
            raise route.RouteV2Error("runner private output collision")
        workspace.mkdir()
        codex_home.mkdir()
        route._current_user_only(workspace, True)
        route._current_user_only(codex_home, True)
        for artifact_id, payload in route._validate_artifacts(staged_workspace).items():
            path = _safe_artifact_path(workspace, artifact_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            route._current_user_only(path, False)
        auth_path = codex_home / "auth.json"
        auth_path.write_bytes(self.auth_payload)
        route._current_user_only(auth_path, False)
        route._verify_current_user_only(codex_home, True)
        route._verify_current_user_only(auth_path, False)
        if {path.name for path in codex_home.iterdir()} != {"auth.json"}:
            raise route.RouteV2Error("isolated Codex home inventory is invalid")
        object.__setattr__(self, "_prepared", True)

    def __call__(self) -> route.SyntheticResult:
        private_root = self.private_root.resolve()
        workspace = private_root / "workspace"
        codex_home = private_root / "codex-home"
        if not self._prepared:
            self.prepare_private(self.baseline_workspace)
        elif not workspace.is_dir() or not codex_home.is_dir():
            raise route.RouteV2Error("prepared runner private workspace is missing")
        schema_path = private_root / "output-schema.json"
        final_path = private_root / "final-message.json"
        schema_path.write_bytes(route._json_bytes(dict(self.output_schema)))
        route._current_user_only(schema_path, False)
        completed = _run_contained(
            self.command(schema_path, final_path), input_bytes=self.prompt,
            cwd=workspace, env=_closed_environment(codex_home),
            timeout_seconds=self.timeout_seconds,
        )
        if completed.timed_out:
            return route.SyntheticResult(
                exit_code=-1, stdout=completed.stdout, final_message=None,
                workspace=None, exit_classification="signal_or_termination",
                final_capture="absent", workspace_capture="capture_failed",
            )
        try:
            final_message = final_path.read_bytes() if final_path.is_file() else None
            final_capture = "captured" if final_message is not None else "absent"
        except OSError:
            final_message, final_capture = None, "read_failed"
        try:
            observed = {
                artifact_id: _safe_artifact_path(workspace, artifact_id).read_bytes()
                for artifact_id in self.observed_artifact_ids
            }
            workspace_capture = "captured"
        except OSError:
            observed, workspace_capture = None, "capture_failed"
        return route.SyntheticResult(
            exit_code=completed.returncode, stdout=completed.stdout,
            final_message=final_message, workspace=observed,
            exit_classification=("zero" if completed.returncode == 0 else "nonzero"),
            final_capture=final_capture, workspace_capture=workspace_capture,
        )


_TRUSTED_CODEX_INVOKE = CodexExecRunner.__call__


class CodexABArmRunner:
    """One live Codex arm bound to a signed pair manifest and staged bytes."""

    def __init__(
        self,
        *,
        run_id: str,
        contract_manifest_sha256: str,
        executable_snapshot: Path,
        auth_payload: bytes,
        measured_preflight: bytes,
        model_id: str,
        staged_files: Mapping[str, bytes],
        expected_artifact_ids: Sequence[str],
        prompt: bytes,
        output_schema: Mapping[str, Any],
    ) -> None:
        route._validate_run_id(run_id)
        if route.SHA256_RE.fullmatch(contract_manifest_sha256) is None:
            raise route.RouteV2Error("contract manifest identity is invalid")
        self.run_id = run_id
        self._contract = contract_manifest_sha256
        self._executable = executable_snapshot
        self._auth = auth_payload
        self._preflight = measured_preflight
        self._model = route._validate_public_token(model_id, "model identity")
        self._files = route._validate_artifacts(staged_files)
        self._expected_ids = tuple(expected_artifact_ids)
        self._prompt = prompt
        self._schema = dict(output_schema)
        self._runner: CodexExecRunner | None = None
        self.calls = 0
        preflight_value, identity = route._validate_preflight(
            measured_preflight, run_id, route.LIVE_AUTHORIZATION
        )
        if (
            preflight_value["required_flags"] != sorted(AB_REQUIRED_FLAGS)
            or identity["command_contract_sha256"] != _ab_command_contract_sha256()
        ):
            raise route.RouteV2Error("live A/B preflight profile is invalid")

    def credential_matches(self, expected: bytes) -> bool:
        return isinstance(expected, bytes) and self._auth == expected

    def admission_matches(self, arm: Mapping[str, object], model_id: str) -> bool:
        treatment = arm.get("treatment_projection")
        if not isinstance(treatment, Mapping):
            return False
        packet = self._files.get("skill.packet")
        manifest = self._files.get("treatment-manifest.json")
        packet_digest = treatment.get("treatment_packet_sha256")
        packet_match = (
            treatment.get("state") == "absent"
            and packet_digest == "absent"
            and packet is None
        ) or (
            treatment.get("state") == "present"
            and isinstance(packet, bytes)
            and packet_digest == route._sha256_bytes(packet)
        )
        try:
            manifest_value = json.loads(manifest.decode("utf-8")) if manifest else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        manifest_match = (
            isinstance(manifest, bytes)
            and manifest == route._json_bytes(manifest_value)
            and treatment.get("treatment_manifest_sha256")
            == route._sha256_bytes(manifest)
            and manifest_value
            == {
                "packet_artifact_id": (
                    "absent" if treatment.get("state") == "absent" else "skill.packet"
                ),
                "packet_sha256": packet_digest,
                "state": treatment.get("state"),
            }
        )
        projection = {
            "artifacts": route._artifact_projection(self._files)
        }
        return (
            self._model == model_id
            and route._sha256_bytes(route._json_bytes(projection))
            == arm.get("staged_input_manifest_sha256")
            and packet_match
            and manifest_match
        )

    def execution_identity(self) -> dict[str, str]:
        value = json.loads(self._preflight)["execution_identity"]
        return route._validate_execution_identity(value)

    def preflight_bytes(self) -> bytes:
        return self._preflight

    def capability(self) -> route.TrustedLiveABArmRunner:
        return route._trusted_live_ab_arm_runner(
            execution_identity=self.execution_identity(),
            preflight=self._preflight,
            prepare=self._prepare,
            invoke=self._invoke,
        )

    def _prepare(self, private_root: Path, action_payload: bytes) -> bytes:
        if self._runner is not None or self.calls:
            raise route.RouteV2Error("live A/B runner preparation is not create-once")
        action = json.loads(action_payload)
        projection = {"artifacts": route._artifact_projection(self._files)}
        staged_digest = route._sha256_bytes(route._json_bytes(projection))
        if staged_digest != action.get("staged_input_manifest_sha256"):
            raise route.RouteV2Error("staged input manifest differs")
        if action.get("model_id") != self._model:
            raise route.RouteV2Error("model selector differs")
        treatment = action.get("treatment_projection")
        if not isinstance(treatment, Mapping) or not self.admission_matches(
            {
                "staged_input_manifest_sha256": staged_digest,
                "treatment_projection": treatment,
            },
            self._model,
        ):
            raise route.RouteV2Error("live A/B staged admission differs")
        runner = CodexExecRunner(
            run_id=self.run_id,
            executable_snapshot=self._executable,
            private_root=private_root,
            auth_payload=self._auth,
            measured_preflight=self._preflight,
            model_id=self._model,
            prompt=self._prompt,
            output_schema=self._schema,
            baseline_workspace=self._files,
            observed_artifact_ids=self._expected_ids,
        )
        runner.prepare_private(self._files)
        self._runner = runner
        return route._json_bytes(
            {
                "action_sha256": route._sha256_bytes(action_payload),
                "arm_id": action["arm_id"],
                "contract_manifest_sha256": self._contract,
                "credential_acl": "PASS",
                "model_id": self._model,
                "model_selector_match": "PASS",
                "only_auth_inventory": "PASS",
                "pair_action_sha256": action["pair_action_sha256"],
                "pair_id": action["pair_id"],
                "run_id": action["run_id"],
                "schema": route.INPUT_ATTESTATION_SCHEMA,
                "staged_acl": "PASS",
                "staged_content_match": "PASS",
                "staged_input_manifest_sha256": staged_digest,
                "staged_inventory_match": "PASS",
                "treatment_packet_sha256": treatment["treatment_packet_sha256"],
                "treatment_state": treatment["state"],
                "validator_sha256": _implementation_sha256(),
            }
        )

    def _invoke(self) -> route.SyntheticResult:
        if self._runner is None or self.calls:
            raise route.RouteV2Error("live A/B runner invocation order is invalid")
        self.calls += 1
        return self._runner()


_TRUSTED_LIVE_AB_PREPARE = CodexABArmRunner._prepare
_TRUSTED_LIVE_AB_INVOKE = CodexABArmRunner._invoke
route._register_live_ab_provenance(
    canonical_type=CodexABArmRunner,
    prepare_function=_TRUSTED_LIVE_AB_PREPARE,
    invoke_function=_TRUSTED_LIVE_AB_INVOKE,
    module_path=Path(__file__),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one authorized Gate 3 v2 session.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--codex-exe", type=Path, required=True)
    parser.add_argument("--expected-executable-sha256", required=True)
    parser.add_argument("--auth-file", type=Path, required=True)
    return parser


def _publish_pin(path: Path, artifact: Path) -> str:
    digest = route._sha256_file(artifact)
    route._publish_create_once(path, (digest + "\n").encode("ascii"))
    return digest


def main(argv: Sequence[str] | None = None, *, _probe: Probe = _native_probe) -> int:
    args = _parser().parse_args(argv)
    if args.authorization != route.LIVE_AUTHORIZATION:
        raise route.RouteV2Error("live vertical-slice authorization is invalid")
    paths = _validate_fixed_paths(args.run_id)
    _probe_publication_parents(paths)
    preflight_root = paths["private"].parent / f".{args.run_id}-preflight"
    if preflight_root.exists():
        raise route.RouteV2Error("preflight output collision")
    preflight, snapshot = _measure_preflight(
        run_id=args.run_id, executable=args.codex_exe,
        expected_executable_sha256=args.expected_executable_sha256,
        preflight_root=preflight_root, probe=_probe,
    )
    try:
        auth_file = args.auth_file.resolve()
        route._verify_current_user_only(auth_file, False)
        auth_payload = auth_file.read_bytes()
        runner = CodexExecRunner(
            run_id=args.run_id, executable_snapshot=snapshot,
            private_root=paths["private"],
            auth_payload=auth_payload, measured_preflight=preflight,
        )
        try:
            result = route.orchestrate(
                paths["output"], locator_root=paths["locator"],
                external_root=paths["external"], run_id=args.run_id,
                authorization=args.authorization, prompt=PROMPT,
                output_schema=OUTPUT_SCHEMA, expected_workspace=EXPECTED_WORKSPACE,
                runner=runner.trusted_capability(),
            )
        except route.RouteV2Error:
            terminal = paths["external"] / f"{args.run_id}.terminal.json"
            if terminal.is_file():
                terminal_digest = _publish_pin(paths["terminal_pin"], terminal)
                route.verify_external_terminal(
                    paths["external"], output_root=paths["output"],
                    locator_root=paths["locator"], run_id=args.run_id,
                    expected_terminal_sha256=terminal_digest,
                    expected_authorization=route.LIVE_AUTHORIZATION,
                )
                print(json.dumps({"decision": "NO_ADMISSIBLE", "verified": True}))
                return 2
            raise
        assert result.final_receipt is not None
        final_digest = _publish_pin(paths["final_pin"], result.final_receipt)
        identity = runner.execution_identity()
        action_digest = route._sha256_bytes(
            route.action_bytes(
                run_id=args.run_id, prompt=PROMPT, output_schema=OUTPUT_SCHEMA,
                expected_workspace=EXPECTED_WORKSPACE,
                authorization=route.LIVE_AUTHORIZATION,
                execution_identity=identity,
                preflight_sha256=route._sha256_bytes(preflight),
            )
        )
        verified = route.verify(
            paths["output"], locator_root=paths["locator"],
            external_root=paths["external"], run_id=args.run_id,
            expected_action_sha256=action_digest,
            expected_final_sha256=final_digest,
        )
        print(json.dumps({"decision": verified["decision"], "verified": True}))
        return 0 if verified["decision"] == "SUCCESS" else 2
    finally:
        if preflight_root.exists():
            shutil.rmtree(preflight_root)


def _entrypoint() -> int:
    """Use this measured module instance without a replaceable re-import."""
    return main()


if __name__ == "__main__":
    sys.exit(_entrypoint())
