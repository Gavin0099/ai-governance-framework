from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import sandboxed_runner as runner


def build_preflight(
    *,
    cli_version_stdout: bytes,
    cli_executable: Path,
    python_executable: Path,
    runner_path: Path,
    config_path: Path,
    requirements_path: Path,
) -> bytes:
    try:
        version = cli_version_stdout.decode("utf-8").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise runner.SandboxedRunnerError("CLI version output is not UTF-8") from exc
    if version != runner.EXPECTED_CLI_VERSION:
        raise runner.SandboxedRunnerError("CLI version differs from freeze")
    config_bytes = config_path.read_bytes()
    requirements_bytes = requirements_path.read_bytes()
    runner.validate_policy_bytes(config_bytes, requirements_bytes)
    document = {
        "schema": runner.PREFLIGHT_SCHEMA,
        "cli_version": version,
        "cli_executable_sha256": runner.sha256_file(cli_executable),
        "python_executable_sha256": runner.sha256_file(python_executable),
        "runner_sha256": runner.sha256_file(runner_path),
        "config_sha256": runner.sha256_bytes(config_bytes),
        "requirements_sha256": runner.sha256_bytes(requirements_bytes),
        "command_contract_sha256": runner.command_contract_sha256(
            python_executable_sha256=runner.sha256_file(python_executable)
        ),
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "windows_sandbox": "elevated",
        "network_access": False,
        "allowed_sandbox_implementations": ["elevated"],
        "server_executed_model_observed": False,
        "identity_evidence_level": "CLIENT_SIDE_INVOCATION_ONLY",
    }
    runner.validate_preflight(
        document,
        runner_sha256=document["runner_sha256"],
        config_sha256=document["config_sha256"],
        requirements_sha256=document["requirements_sha256"],
    )
    return runner.canonical_json(document)


def parse_and_validate(
    payload: bytes,
    *,
    runner_sha256: str,
    config_sha256: str,
    requirements_sha256: str,
) -> Mapping[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise runner.SandboxedRunnerError("preflight is not canonical JSON") from exc
    if not isinstance(value, dict) or runner.canonical_json(value) != payload:
        raise runner.SandboxedRunnerError("preflight is not canonical JSON")
    runner.validate_preflight(
        value,
        runner_sha256=runner_sha256,
        config_sha256=config_sha256,
        requirements_sha256=requirements_sha256,
    )
    return value

