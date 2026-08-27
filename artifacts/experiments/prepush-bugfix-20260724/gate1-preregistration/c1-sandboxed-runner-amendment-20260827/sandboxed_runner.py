from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


SCHEMA = "c1-sandboxed-codex-runner.v1"
COMMAND_CONTRACT_SCHEMA = "c1-sandboxed-codex-command.v1"
PREFLIGHT_SCHEMA = "c1-sandboxed-codex-preflight.v1"
EXPECTED_CLI_VERSION = "codex-cli 0.148.0-alpha.9"
EXPECTED_CLI_SHA256 = (
    "f29f609375f3731d8db507a95124862a84e306982e30ba4300ddce5638bc6946"
)
EXPECTED_PYTHON_SHA256 = (
    "97c3228a59dcc05a771ab4eeec8126ce3f36ebb53616b479adc9f2c8050a9e84"
)
EXPECTED_MODEL = "gpt-5.6-sol"
REQUIRED_FLAGS = (
    "--ask-for-approval",
    "--ephemeral",
    "--ignore-user-config",
    "--json",
    "--model",
    "--output-last-message",
    "--output-schema",
    "--sandbox",
)
FORBIDDEN_ARGUMENTS = frozenset(
    {
        "--dangerously-bypass-approvals-and-sandbox",
        "--yolo",
        "danger-full-access",
        "sandbox_workspace_write.network_access=true",
        "windows.sandbox=unelevated",
    }
)
COMMAND_TEMPLATE = (
    "<exact-codex-executable>",
    "exec",
    "--ignore-user-config",
    "--json",
    "--ephemeral",
    "--output-last-message",
    "<private-final-message>",
    "--output-schema",
    "<private-output-schema>",
    "--sandbox",
    "workspace-write",
    "--ask-for-approval",
    "never",
    "-c",
    'windows.sandbox="elevated"',
    "-c",
    "sandbox_workspace_write.network_access=false",
    "--model",
    "<owner-selected-model>",
    "-",
)


class SandboxedRunnerError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def command_argv_projection() -> bytes:
    return canonical_json({"argv": list(COMMAND_TEMPLATE), "schema": SCHEMA})


def command_contract_sha256(*, python_executable_sha256: str) -> str:
    if python_executable_sha256 != EXPECTED_PYTHON_SHA256:
        raise SandboxedRunnerError("python executable identity mismatch")
    return sha256_bytes(
        canonical_json(
            {
                "argv": list(COMMAND_TEMPLATE),
                "python_executable_sha256": python_executable_sha256,
                "schema": COMMAND_CONTRACT_SCHEMA,
            }
        )
    )


def validate_policy_bytes(config_bytes: bytes, requirements_bytes: bytes) -> None:
    try:
        config = tomllib.loads(config_bytes.decode("utf-8"))
        requirements = tomllib.loads(requirements_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SandboxedRunnerError("sandbox policy is not canonical TOML") from exc
    if config.get("approval_policy") != "never":
        raise SandboxedRunnerError("approval policy must be never")
    if config.get("sandbox_mode") != "workspace-write":
        raise SandboxedRunnerError("sandbox mode must be workspace-write")
    workspace = config.get("sandbox_workspace_write")
    windows = config.get("windows")
    managed_windows = requirements.get("windows")
    if not isinstance(workspace, dict) or workspace.get("network_access") is not False:
        raise SandboxedRunnerError("task network must be disabled")
    if not isinstance(windows, dict) or windows.get("sandbox") != "elevated":
        raise SandboxedRunnerError("elevated Windows sandbox is required")
    if not isinstance(managed_windows, dict) or managed_windows.get(
        "allowed_sandbox_implementations"
    ) != ["elevated"]:
        raise SandboxedRunnerError("managed policy must prohibit sandbox fallback")


def build_command(
    executable: Path,
    *,
    schema_path: Path,
    final_path: Path,
    model_id: str = EXPECTED_MODEL,
) -> list[str]:
    if model_id != EXPECTED_MODEL:
        raise SandboxedRunnerError("model request differs from the frozen identity")
    command = [
        str(executable),
        "exec",
        "--ignore-user-config",
        "--json",
        "--ephemeral",
        "--output-last-message",
        str(final_path),
        "--output-schema",
        str(schema_path),
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "-c",
        'windows.sandbox="elevated"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "--model",
        model_id,
        "-",
    ]
    if any(argument in FORBIDDEN_ARGUMENTS for argument in command):
        raise SandboxedRunnerError("command contains a forbidden full-access argument")
    return command


def validate_preflight(
    document: Mapping[str, object],
    *,
    runner_sha256: str,
    config_sha256: str,
    requirements_sha256: str,
) -> None:
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "cli_version": EXPECTED_CLI_VERSION,
        "cli_executable_sha256": EXPECTED_CLI_SHA256,
        "python_executable_sha256": EXPECTED_PYTHON_SHA256,
        "runner_sha256": runner_sha256,
        "config_sha256": config_sha256,
        "requirements_sha256": requirements_sha256,
        "command_contract_sha256": command_contract_sha256(
            python_executable_sha256=EXPECTED_PYTHON_SHA256
        ),
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "windows_sandbox": "elevated",
        "network_access": False,
        "allowed_sandbox_implementations": ["elevated"],
        "server_executed_model_observed": False,
        "identity_evidence_level": "CLIENT_SIDE_INVOCATION_ONLY",
    }
    if dict(document) != expected:
        raise SandboxedRunnerError("sandboxed runner preflight differs from freeze")


@dataclass(frozen=True)
class LaunchResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False


Launcher = Callable[[Sequence[str], bytes, Path, Mapping[str, str], int], LaunchResult]
PathPolicy = Callable[[Path, bool], None]


@dataclass
class SandboxedCodexRunner:
    executable: Path
    python_executable: Path
    private_root: Path
    auth_payload: bytes
    config_bytes: bytes
    requirements_bytes: bytes
    preflight: Mapping[str, object]
    runner_sha256: str
    prompt: bytes
    output_schema: Mapping[str, object]
    workspace_files: Mapping[str, bytes]
    launcher: Launcher
    protect_path: PathPolicy
    verify_path: PathPolicy
    timeout_seconds: int = 300

    def validate(self) -> None:
        if not self.auth_payload:
            raise SandboxedRunnerError("credential seed payload is invalid")
        if not 1 <= self.timeout_seconds <= 1800:
            raise SandboxedRunnerError("timeout exceeds the frozen producer budget")
        if sha256_file(self.executable) != EXPECTED_CLI_SHA256:
            raise SandboxedRunnerError("CLI executable identity mismatch")
        if sha256_file(self.python_executable) != EXPECTED_PYTHON_SHA256:
            raise SandboxedRunnerError("Python executable identity mismatch")
        validate_policy_bytes(self.config_bytes, self.requirements_bytes)
        validate_preflight(
            self.preflight,
            runner_sha256=self.runner_sha256,
            config_sha256=sha256_bytes(self.config_bytes),
            requirements_sha256=sha256_bytes(self.requirements_bytes),
        )

    def prepare(self) -> tuple[Path, Path, Path]:
        self.validate()
        workspace = self.private_root / "workspace"
        codex_home = self.private_root / "codex-home"
        if self.private_root.exists():
            raise SandboxedRunnerError("private runner root already exists")
        workspace.mkdir(parents=True)
        codex_home.mkdir()
        self.protect_path(workspace, True)
        self.protect_path(codex_home, True)
        for relative_name, payload in self.workspace_files.items():
            relative = Path(relative_name)
            if relative.is_absolute() or ".." in relative.parts:
                raise SandboxedRunnerError("workspace artifact path escapes scratch")
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            self.protect_path(target, False)
        (codex_home / "auth.json").write_bytes(self.auth_payload)
        (codex_home / "config.toml").write_bytes(self.config_bytes)
        (codex_home / "requirements.toml").write_bytes(self.requirements_bytes)
        for name in ("auth.json", "config.toml", "requirements.toml"):
            self.protect_path(codex_home / name, False)
        self.verify_path(codex_home, True)
        self.verify_path(codex_home / "auth.json", False)
        schema_path = self.private_root / "output-schema.json"
        final_path = self.private_root / "final-message.json"
        schema_path.write_bytes(canonical_json(dict(self.output_schema)))
        self.protect_path(schema_path, False)
        return workspace, schema_path, final_path

    def run(self) -> LaunchResult:
        workspace, schema_path, final_path = self.prepare()
        command = build_command(
            self.executable, schema_path=schema_path, final_path=final_path
        )
        environment = {
            key: os.environ[key]
            for key in (
                "COMSPEC",
                "PATHEXT",
                "SYSTEMDRIVE",
                "SYSTEMROOT",
                "TEMP",
                "TMP",
                "WINDIR",
            )
            if key in os.environ
        }
        environment.update(
            {
                "CODEX_HOME": str(self.private_root / "codex-home"),
                "NO_COLOR": "1",
            }
        )
        return self.launcher(
            command, self.prompt, workspace, environment, self.timeout_seconds
        )
