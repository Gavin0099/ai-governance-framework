from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


EXPECTED_CLI_VERSION = "codex-cli 0.148.0-alpha.9"
EXPECTED_EXECUTABLE_SHA256 = (
    "f29f609375f3731d8db507a95124862a84e306982e30ba4300ddce5638bc6946"
)
EXPECTED_RUNNER_BLOB_OID = "d74dc12984ec8b4d997b6ed4cb39e02a49891bf0"
EXPECTED_RUNNER_BYTES = 44_296
EXPECTED_RUNNER_SHA256 = (
    "55403b05196c44e73c71b041c18888ad66629843c23ab9d5c3f6430690e737be"
)


class AmendmentPreflightError(RuntimeError):
    """A current-build preflight cannot satisfy the frozen amendment."""


def _route_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "gate3-route-v2"


def _load_runner_modules() -> tuple[Any, Any]:
    route_dir = str(_route_directory())
    if route_dir not in sys.path:
        sys.path.insert(0, route_dir)
    import gate3_route_v2 as route
    import gate3_route_v2_codex as codex

    runner_path = Path(codex.__file__).resolve()
    if runner_path.stat().st_size != EXPECTED_RUNNER_BYTES:
        raise AmendmentPreflightError("selected runner byte count differs")
    if route._sha256_file(runner_path) != EXPECTED_RUNNER_SHA256:
        raise AmendmentPreflightError("selected runner digest differs")
    return route, codex


def command_contract_projection() -> dict[str, object]:
    route, codex = _load_runner_modules()
    interpreter = Path(sys.executable).resolve()
    return {
        "command_argv_projection_sha256": route._sha256_bytes(
            route._json_bytes(list(codex.AB_COMMAND_TEMPLATE))
        ),
        "command_contract_sha256": codex._ab_command_contract_sha256(),
        "python_executable_bytes": interpreter.stat().st_size,
        "python_executable_sha256": route._sha256_file(interpreter),
        "windows_guard_source_sha256": route._sha256_bytes(
            codex.WINDOWS_GUARD.encode("utf-8")
        ),
    }


def _probe_output(route: Any, result: Any) -> dict[str, object]:
    for payload in (result.stdout, result.stderr):
        if len(payload) > 262_144:
            raise AmendmentPreflightError("preflight output is too large")
        try:
            payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise AmendmentPreflightError("preflight output is not UTF-8") from exc
    return {
        "returncode": result.returncode,
        "stderr_len": len(result.stderr),
        "stderr_sha256": route._sha256_bytes(result.stderr),
        "stdout_len": len(result.stdout),
        "stdout_sha256": route._sha256_bytes(result.stdout),
    }


def measure_amended_preflight(
    *,
    run_id: str,
    executable: Path,
    preflight_root: Path,
    probe: Callable[[Sequence[str], Path, Mapping[str, str]], Any] | None = None,
) -> tuple[bytes, Path]:
    """Measure the amended CLI without changing the selected runner bytes."""

    route, codex = _load_runner_modules()
    source = executable.resolve()
    if not source.is_file() or route._sha256_file(source) != EXPECTED_EXECUTABLE_SHA256:
        raise AmendmentPreflightError("Codex executable differs from amendment")
    native_probe = probe or codex._native_probe
    owned_root = False
    try:
        preflight_root.mkdir(parents=True)
        owned_root = True
        route._current_user_only(preflight_root, True)
        snapshot = preflight_root / "codex.exe"
        shutil.copyfile(source, snapshot)
        route._current_user_only(snapshot, False)
        if route._sha256_file(snapshot) != EXPECTED_EXECUTABLE_SHA256:
            raise AmendmentPreflightError("executable snapshot differs")

        home = preflight_root / "codex-home"
        home.mkdir()
        route._current_user_only(home, True)
        env = codex._closed_environment(home)
        environment_projection = codex._environment_projection_sha256(env)
        version = native_probe((str(snapshot), "--version"), preflight_root, env)
        root_help = native_probe((str(snapshot), "--help"), preflight_root, env)
        exec_help = native_probe((str(snapshot), "exec", "--help"), preflight_root, env)
        results = (version, root_help, exec_help)
        if any(item.timed_out or item.returncode != 0 for item in results):
            raise AmendmentPreflightError("Codex zero-session preflight failed")

        observed_version = version.stdout.decode("utf-8", errors="strict").strip()
        root_help_text = (root_help.stdout + root_help.stderr).decode("utf-8", errors="strict")
        exec_help_text = (exec_help.stdout + exec_help.stderr).decode("utf-8", errors="strict")
        if observed_version != EXPECTED_CLI_VERSION:
            raise AmendmentPreflightError("Codex version differs from amendment")
        if not root_help_text.strip():
            raise AmendmentPreflightError("Codex root help is empty")
        if any(flag not in exec_help_text for flag in codex.AB_REQUIRED_FLAGS):
            raise AmendmentPreflightError("Codex help lacks an amended required flag")
        codex._validate_closed_zero_session_residue(home)
        codex._remove_tree_bounded(home)

        identity = route._validate_execution_identity(
            {
                "cli_version": observed_version,
                "command_contract_sha256": codex._ab_command_contract_sha256(),
                "executable_sha256": EXPECTED_EXECUTABLE_SHA256,
                "kind": "codex_exec",
                "runner_sha256": EXPECTED_RUNNER_SHA256,
            }
        )
        payload = route._json_bytes(
            {
                "authorization": route.LIVE_AUTHORIZATION,
                "checks": {
                    "cleanup": "PASS",
                    "exec_help": "PASS",
                    "root_help": "PASS",
                    "version": "PASS",
                },
                "compatibility": {
                    "required_flag_presence": {
                        flag: flag in exec_help_text
                        for flag in sorted(codex.AB_REQUIRED_FLAGS)
                    },
                    "root_help_nonempty": True,
                    "version_match": True,
                },
                "environment_policy_sha256": codex._environment_policy_sha256(),
                "environment_projection_sha256": environment_projection,
                "execution_identity": identity,
                "probe_outputs": {
                    "exec_help": _probe_output(route, exec_help),
                    "root_help": _probe_output(route, root_help),
                    "version": _probe_output(route, version),
                },
                "required_flags": sorted(codex.AB_REQUIRED_FLAGS),
                "run_id": route._validate_run_id(run_id),
                "schema": route.PREFLIGHT_SCHEMA,
            }
        )
        route._validate_public_payload(payload)
        return payload, snapshot
    except BaseException:
        if owned_root and os.path.lexists(preflight_root):
            codex._remove_tree_bounded(preflight_root)
        raise


def prove_runner_accepts_preflight(
    *, measured_preflight: bytes, executable_snapshot: Path, private_root: Path
) -> dict[str, str]:
    route, codex = _load_runner_modules()
    value = json.loads(measured_preflight)
    runner = codex.CodexExecRunner(
        run_id=value["run_id"],
        executable_snapshot=executable_snapshot,
        private_root=private_root,
        auth_payload=b"{}\n",
        measured_preflight=measured_preflight,
        model_id="gpt-5.6-sol",
    )
    identity = runner.execution_identity()
    if identity["runner_sha256"] != EXPECTED_RUNNER_SHA256:
        raise AmendmentPreflightError("runner accepted the wrong identity")
    return identity
