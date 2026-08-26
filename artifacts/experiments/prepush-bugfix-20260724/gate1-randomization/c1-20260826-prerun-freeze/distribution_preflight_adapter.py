"""Zero-session preflight for the exact npm Codex distribution."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any


EXPECTED_VERSION = "codex-cli 0.148.0-alpha.9"
EXPECTED_EXECUTABLE_BYTES = 295_151_920
EXPECTED_EXECUTABLE_SHA256 = "88aa986d1405d41dcc9c2f777d7b028de07edc33b6468a8dd8db6a0cc62c315f"
EXPECTED_RUNNER_BYTES = 44_296
EXPECTED_RUNNER_SHA256 = "55403b05196c44e73c71b041c18888ad66629843c23ab9d5c3f6430690e737be"


class PreflightError(RuntimeError):
    pass


def _load_runner(repo_root: Path) -> tuple[Any, Any]:
    route_dir = repo_root / "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2"
    if str(route_dir) not in sys.path:
        sys.path.insert(0, str(route_dir))
    import gate3_route_v2 as route
    import gate3_route_v2_codex as codex

    runner = Path(codex.__file__).resolve()
    if runner.stat().st_size != EXPECTED_RUNNER_BYTES or route._sha256_file(runner) != EXPECTED_RUNNER_SHA256:
        raise PreflightError("runner binding differs")
    return route, codex


def command_contract_projection(repo_root: Path) -> dict[str, object]:
    route, codex = _load_runner(repo_root)
    interpreter = Path(sys.executable).resolve()
    return {
        "command_argv_projection_sha256": route._sha256_bytes(route._json_bytes(list(codex.AB_COMMAND_TEMPLATE))),
        "command_contract_sha256": codex._ab_command_contract_sha256(),
        "python_executable_bytes": interpreter.stat().st_size,
        "python_executable_sha256": route._sha256_file(interpreter),
        "windows_guard_source_sha256": route._sha256_bytes(codex.WINDOWS_GUARD.encode("utf-8")),
    }


def measure_preflight(repo_root: Path, executable: Path, root: Path) -> tuple[bytes, Path]:
    route, codex = _load_runner(repo_root)
    executable = executable.resolve()
    if executable.stat().st_size != EXPECTED_EXECUTABLE_BYTES or route._sha256_file(executable) != EXPECTED_EXECUTABLE_SHA256:
        raise PreflightError("npm native executable binding differs")
    root.mkdir()
    snapshot = root / "codex.exe"
    shutil.copyfile(executable, snapshot)
    home = root / "codex-home"
    home.mkdir()
    environment = codex._closed_environment(home)
    environment_projection = codex._environment_projection_sha256(environment)
    results = {
        "version": codex._native_probe((str(snapshot), "--version"), root, environment),
        "root_help": codex._native_probe((str(snapshot), "--help"), root, environment),
        "exec_help": codex._native_probe((str(snapshot), "exec", "--help"), root, environment),
    }
    if any(item.timed_out or item.returncode != 0 for item in results.values()):
        raise PreflightError("zero-session preflight failed")
    version = results["version"].stdout.decode("utf-8", errors="strict").strip()
    root_help = (results["root_help"].stdout + results["root_help"].stderr).decode("utf-8", errors="strict")
    exec_help = (results["exec_help"].stdout + results["exec_help"].stderr).decode("utf-8", errors="strict")
    if version != EXPECTED_VERSION or not root_help.strip() or any(flag not in exec_help for flag in codex.AB_REQUIRED_FLAGS):
        raise PreflightError("zero-session compatibility differs")
    codex._validate_closed_zero_session_residue(home)
    codex._remove_tree_bounded(home)
    projection = command_contract_projection(repo_root)
    identity = route._validate_execution_identity({
        "cli_version": version,
        "command_contract_sha256": projection["command_contract_sha256"],
        "executable_sha256": EXPECTED_EXECUTABLE_SHA256,
        "kind": "codex_exec",
        "runner_sha256": EXPECTED_RUNNER_SHA256,
    })
    payload = route._json_bytes({
        "authorization": route.LIVE_AUTHORIZATION,
        "checks": {"cleanup": "PASS", "exec_help": "PASS", "root_help": "PASS", "version": "PASS"},
        "compatibility": {
            "required_flag_presence": {flag: flag in exec_help for flag in sorted(codex.AB_REQUIRED_FLAGS)},
            "root_help_nonempty": True,
            "version_match": True,
        },
        "environment_policy_sha256": codex._environment_policy_sha256(),
        "environment_projection_sha256": environment_projection,
        "execution_identity": identity,
        "probe_outputs": {
            name: {
                "returncode": result.returncode,
                "stderr_len": len(result.stderr),
                "stderr_sha256": route._sha256_bytes(result.stderr),
                "stdout_len": len(result.stdout),
                "stdout_sha256": route._sha256_bytes(result.stdout),
            }
            for name, result in results.items()
        },
        "required_flags": sorted(codex.AB_REQUIRED_FLAGS),
        "run_id": "c1-pair02-distribution-preflight",
        "schema": route.PREFLIGHT_SCHEMA,
    })
    route._validate_public_payload(payload)
    return payload, snapshot


def prove_runner_accepts(repo_root: Path, preflight: bytes, snapshot: Path, private_root: Path) -> dict[str, str]:
    _, codex = _load_runner(repo_root)
    value = json.loads(preflight)
    runner = codex.CodexExecRunner(
        run_id=value["run_id"], executable_snapshot=snapshot, private_root=private_root,
        auth_payload=b"{}\n", measured_preflight=preflight, model_id="gpt-5.6-sol",
    )
    return runner.execution_identity()
