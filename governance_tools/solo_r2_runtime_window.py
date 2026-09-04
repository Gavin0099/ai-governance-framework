"""Exclusive same-machine runtime window through the Solo R2 Attempt boundary.

This module deliberately stops before lifecycle admission.  It provisions the
machine-global Codex sandbox accounts, freezes the resulting runtime identity,
qualifies one information-dependent tool call, consumes the existing
materialization and pre-ID parity gates, and returns only a readiness object.
It cannot mint an Attempt handle or expose task bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Callable, Mapping
import uuid

from governance_tools import solo_r2_controller_state as controller_state
from governance_tools.solo_r2_attempt_execution import (
    PairLedgerLock,
    PreAttemptExecutionCoordinator,
    PreAttemptValidation,
)
from governance_tools.solo_r2_attempt_materialization import (
    FrozenGitMaterializer,
    HostLocalIsolation,
    PairMaterializationEvidence,
    PinnedExecutable,
    RepositoryBinding,
    _run_git,
    verify_repository_binding,
)
from governance_tools.solo_r2_codex_runner import (
    REQUIRED_EXECUTION_POLICY,
    WINDOWS_POWERSHELL_BYTE_LENGTH,
    WINDOWS_POWERSHELL_PATH,
    WINDOWS_POWERSHELL_SHA256,
    ArmPreparationObservation,
    CanaryObservation,
    CanaryQualification,
    CodexRunnerAdapter,
    NativeCodexExecBackend,
    NativeExecutionResult,
    PreparedArm,
    RuntimeIdentity,
    SandboxGenerationFingerprint,
    ToolCatalog,
    _run_contained_once,
    capture_sandbox_generation,
    resolve_codex_payload,
    validate_execution_result,
)


PRE_ATTEMPT_INFRA_FAILURE = "PRE_ATTEMPT_INFRA_FAILURE / STOP"
PAIR_INVALID = "PAIR_INVALID / STOP"
SAME_MACHINE_WINDOW_REJECTED = "SAME_MACHINE_WINDOW_REJECTED / STOP"
READY_BEFORE_ATTEMPT = "R2_READY_BEFORE_ATTEMPT_HANDLE_CREATION"
QUALIFICATION_STATUS = "R2_NON_EXPOSURE_OK"
BOUNDARY_SCHEMA = "solo-r2-pre-exposure-boundary/v1"
_LOWER_HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_CHALLENGE = re.compile(r"[0-9a-f]{32}\Z")


class RuntimeWindowError(RuntimeError):
    def __init__(self, code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
    raise RuntimeWindowError(code) from None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _closed_directory(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        _fail()
    try:
        value = os.lstat(path)
        resolved = path.resolve(strict=True)
    except OSError:
        _fail()
    if (
        os.path.normcase(str(path)) != os.path.normcase(str(resolved))
        or not stat.S_ISDIR(value.st_mode)
        or stat.S_ISLNK(value.st_mode)
        or bool(getattr(value, "st_file_attributes", 0) & 0x400)
    ):
        _fail()
    return resolved


@dataclass(frozen=True)
class PreExposureBoundaryEvidence:
    """Digest-bound result of the already-adopted pre-ID boundary checks."""

    evidence_sha256: str
    credential_sentinel_visible: bool
    network_tcp_egress_denied: bool
    host_local: HostLocalIsolation

    def validate(self) -> None:
        self.host_local.validate()
        if (
            _LOWER_HEX_64.fullmatch(self.evidence_sha256) is None
            or self.credential_sentinel_visible is not False
            or self.network_tcp_egress_denied is not True
        ):
            _fail(PAIR_INVALID)

    @classmethod
    def load(cls, path: Path | str, *, expected_sha256: str) -> "PreExposureBoundaryEvidence":
        source = Path(path)
        try:
            value_stat = os.lstat(source)
            resolved = source.resolve(strict=True)
            payload = source.read_bytes()
        except OSError:
            _fail()
        if (
            not source.is_absolute()
            or os.path.normcase(str(resolved)) != os.path.normcase(str(source))
            or not stat.S_ISREG(value_stat.st_mode)
            or stat.S_ISLNK(value_stat.st_mode)
            or bool(getattr(value_stat, "st_file_attributes", 0) & 0x400)
            or _sha256(payload) != expected_sha256
        ):
            _fail(PAIR_INVALID)
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail(PAIR_INVALID)
        expected = {
            "schema",
            "credential_sentinel_visible",
            "network_tcp_egress_denied",
            "host_local_endpoint_reachable",
            "observed_host_listener_count",
            "runtime_endpoint_inputs",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected
            or value["schema"] != BOUNDARY_SCHEMA
        ):
            _fail(PAIR_INVALID)
        runtime_inputs = value["runtime_endpoint_inputs"]
        if not isinstance(runtime_inputs, list) or any(
            not isinstance(item, str) for item in runtime_inputs
        ):
            _fail(PAIR_INVALID)
        result = cls(
            evidence_sha256=expected_sha256,
            credential_sentinel_visible=value["credential_sentinel_visible"],
            network_tcp_egress_denied=value["network_tcp_egress_denied"],
            host_local=HostLocalIsolation(
                value["host_local_endpoint_reachable"],
                value["observed_host_listener_count"],
                tuple(runtime_inputs),
            ),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class RepositoryFileIdentity:
    relative_path: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class RepositoryRuntimeIdentity:
    head_commit: str
    runner: RepositoryFileIdentity
    materialization: RepositoryFileIdentity


class GitRepositoryFreezeProbe:
    """Bind HEAD and exact committed Python blobs through one pinned Git."""

    def __init__(
        self,
        *,
        git: PinnedExecutable,
        repository: RepositoryBinding,
        temp_root: Path,
        runner_relative_path: str = "governance_tools/solo_r2_codex_runner.py",
        materialization_relative_path: str = "governance_tools/solo_r2_attempt_materialization.py",
    ) -> None:
        self.git = git
        self.repository = repository
        self.temp_root = _closed_directory(temp_root)
        self._paths = (runner_relative_path, materialization_relative_path)

    def _blob(self, head: str, relative: str) -> RepositoryFileIdentity:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            _fail(PAIR_INVALID)
        payload = _run_git(
            self.git,
            self.repository,
            ("show", f"{head}:{pure.as_posix()}"),
            temp_root=self.temp_root,
        )
        working_path = self.repository.root.joinpath(*pure.parts)
        try:
            working = working_path.read_bytes()
            value = os.lstat(working_path)
        except OSError:
            _fail()
        if (
            working != payload
            or not stat.S_ISREG(value.st_mode)
            or stat.S_ISLNK(value.st_mode)
            or bool(getattr(value, "st_file_attributes", 0) & 0x400)
        ):
            _fail(PAIR_INVALID)
        return RepositoryFileIdentity(pure.as_posix(), len(payload), _sha256(payload))

    def capture(self) -> RepositoryRuntimeIdentity:
        verify_repository_binding(self.git, self.repository, temp_root=self.temp_root)
        raw_head = _run_git(
            self.git,
            self.repository,
            ("rev-parse", "--verify", "HEAD"),
            temp_root=self.temp_root,
        )
        try:
            head = raw_head.decode("ascii", errors="strict").strip()
        except UnicodeDecodeError:
            _fail()
        if _LOWER_HEX_40.fullmatch(head) is None:
            _fail(PAIR_INVALID)
        result = RepositoryRuntimeIdentity(
            head,
            self._blob(head, self._paths[0]),
            self._blob(head, self._paths[1]),
        )
        self.git.verify()
        return result


@dataclass(frozen=True)
class RuntimeFreeze:
    payload_path: Path
    payload_byte_length: int
    payload_sha256: str
    qualification_helper_path: Path
    qualification_helper_byte_length: int
    qualification_helper_sha256: str
    repository: RepositoryRuntimeIdentity
    generation: SandboxGenerationFingerprint
    ledger_sha256: str
    evaluation_id: str
    pair_id: str
    slot: str
    command_policy: tuple[str, ...]
    command_policy_sha256: str
    boundary_evidence_sha256: str
    runtime_quiescent: bool = True


class RuntimeFreezeProbe:
    """Capture and re-check every mutable identity in the exclusive window."""

    def __init__(
        self,
        *,
        backend: NativeCodexExecBackend,
        repository_probe: GitRepositoryFreezeProbe,
        qualification_helper: PinnedExecutable,
        generation_probe: Callable[[], SandboxGenerationFingerprint],
        pair_lock: PairLedgerLock,
        boundary_evidence: PreExposureBoundaryEvidence,
        assert_runtime_quiescent: Callable[[], None],
    ) -> None:
        self.backend = backend
        self.repository_probe = repository_probe
        self.qualification_helper = qualification_helper
        self.generation_probe = generation_probe
        self.pair_lock = pair_lock
        self.boundary_evidence = boundary_evidence
        self.assert_runtime_quiescent = assert_runtime_quiescent

    def capture(self) -> RuntimeFreeze:
        self.assert_runtime_quiescent()
        self.boundary_evidence.validate()
        self.pair_lock.assert_unchanged()
        payload = resolve_codex_payload()
        payload.verify()
        qualification_helper = self.qualification_helper
        qualification_helper.verify()
        if payload != self.backend.executable:
            _fail(PAIR_INVALID)
        generation_before = self.generation_probe()
        generation_before.validate()
        repository = self.repository_probe.capture()
        try:
            ledger_payload = self.pair_lock.ledger_path.read_bytes()
        except OSError:
            _fail()
        command_policy = self.backend.command_policy_projection()
        policy_payload = json.dumps(
            command_policy, ensure_ascii=True, separators=(",", ":")
        ).encode("ascii")
        binding = self.pair_lock.binding
        result = RuntimeFreeze(
            payload.path,
            payload.byte_length,
            payload.sha256,
            qualification_helper.path,
            qualification_helper.byte_length,
            qualification_helper.sha256,
            repository,
            generation_before,
            _sha256(ledger_payload),
            binding.evaluation_id,
            binding.pair_id,
            binding.slot,
            command_policy,
            _sha256(policy_payload),
            self.boundary_evidence.evidence_sha256,
        )
        self.pair_lock.assert_unchanged()
        payload.verify()
        qualification_helper.verify()
        generation_after = self.generation_probe()
        generation_after.validate()
        if generation_after != generation_before:
            _fail(SAME_MACHINE_WINDOW_REJECTED)
        self.assert_runtime_quiescent()
        return result

    def assert_unchanged(self, expected: RuntimeFreeze) -> None:
        if self.capture() != expected:
            _fail(SAME_MACHINE_WINDOW_REJECTED)


_CODEX_PROCESS_QUERY = (
    "$ErrorActionPreference='Stop';"
    "$matches=@(Get-CimInstance -ClassName Win32_Process -ErrorAction Stop |"
    "Where-Object {$_.Name -match '(?i)^(ChatGPT|Codex|codex-code-mode-host)(\\.exe)?$'} |"
    "ForEach-Object {[ordered]@{name=$_.Name;process_id=[int]$_.ProcessId}});"
    "ConvertTo-Json -Compress -InputObject $matches"
)


class WindowsCodexRuntimeQuiescence:
    """Fail when any visible Desktop/Codex-family runtime is present."""

    def __init__(self, *, temp_root: Path) -> None:
        self.temp_root = _closed_directory(temp_root)

    def __call__(self) -> None:
        if os.name != "nt":
            _fail()
        try:
            powershell = PinnedExecutable.capture(WINDOWS_POWERSHELL_PATH)
        except Exception:
            _fail()
        if (
            powershell.byte_length != WINDOWS_POWERSHELL_BYTE_LENGTH
            or powershell.sha256 != WINDOWS_POWERSHELL_SHA256
        ):
            _fail(PAIR_INVALID)
        result = _run_contained_once(
            (
                str(powershell.path),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                _CODEX_PROCESS_QUERY,
            ),
            input_bytes=b"",
            cwd=self.temp_root,
            env={
                key: os.environ[key]
                for key in ("COMSPEC", "SYSTEMROOT", "WINDIR")
                if key in os.environ and os.environ[key]
            }
            | {"TEMP": str(self.temp_root), "TMP": str(self.temp_root), "NO_COLOR": "1"},
            timeout_seconds=30,
        )
        powershell.verify()
        if (
            result.returncode != 0
            or result.timed_out
            or result.tree_terminated is not True
            or result.stderr != b""
            or not result.stdout
            or len(result.stdout) > 65_536
        ):
            _fail()
        try:
            processes = json.loads(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail()
        if not isinstance(processes, list):
            _fail(PAIR_INVALID)
        for process in processes:
            if (
                not isinstance(process, dict)
                or set(process) != {"name", "process_id"}
                or not isinstance(process["name"], str)
                or type(process["process_id"]) is not int
                or process["process_id"] <= 0
            ):
                _fail(PAIR_INVALID)
        if processes:
            _fail(SAME_MACHINE_WINDOW_REJECTED)


@dataclass(frozen=True, repr=False, init=False)
class SealedArmOrder:
    order: tuple[str, str]

    @classmethod
    def _from_controller_state(
        cls, state: object, *, pair_lock: PairLedgerLock
    ) -> "SealedArmOrder":
        try:
            validated = controller_state.validate_controller_state(state)
        except controller_state.ControllerStateError:
            _fail(PAIR_INVALID)
        binding = pair_lock.binding
        if (
            validated["state_phase"] != controller_state.ORDER_FROZEN
            or validated["evaluation_id"] != binding.evaluation_id
            or validated["pair_id"] != binding.pair_id
            or validated["slot"] != binding.slot
            or validated["attempt_bindings"] != []
        ):
            _fail(PAIR_INVALID)
        order = tuple(validated["realized_order"])
        if len(order) != 2 or set(order) != {"CONTROL", "TREATMENT"}:
            _fail(PAIR_INVALID)
        result = object.__new__(cls)
        object.__setattr__(result, "order", order)
        return result

    @classmethod
    def from_sealed_package(
        cls,
        package_path: Path | str,
        *,
        key_path: Path | str,
        custody_boundary: controller_state.CustodyBoundary,
        expected_digest: str,
        pair_lock: PairLedgerLock,
    ) -> "SealedArmOrder":
        try:
            package = Path(package_path).read_bytes()
            state = controller_state.open_controller_package(
                package,
                key_path=key_path,
                custody_boundary=custody_boundary,
                expected_digest=expected_digest,
                expected_evaluation_id=pair_lock.binding.evaluation_id,
                expected_pair_id=pair_lock.binding.pair_id,
                expected_slot=pair_lock.binding.slot,
            )
        except (OSError, controller_state.ControllerStateError):
            _fail(PAIR_INVALID)
        return cls._from_controller_state(state, pair_lock=pair_lock)

    def ordinals(self) -> tuple[int, int]:
        return tuple(  # type: ignore[return-value]
            1 if arm == "CONTROL" else 2 for arm in self.order
        )


@dataclass(frozen=True)
class ProvisioningObservation:
    generation_before: SandboxGenerationFingerprint
    generation_after: SandboxGenerationFingerprint
    native_result: NativeExecutionResult
    generation_changed: bool
    task_exposure_state: str = "NONE"
    attempt_handle: None = None


class NativePreExposureObservationBackend:
    """Concrete production implementation of the pre-exposure backend."""

    def __init__(
        self,
        *,
        native_backend: NativeCodexExecBackend,
        codex_home: Path,
        provisioning_workspace: Path,
        provisioning_output: Path,
        qualification_workspace: Path,
        qualification_output: Path,
        whoami: PinnedExecutable,
        runtime_identity: RuntimeIdentity,
        boundary_evidence: PreExposureBoundaryEvidence,
        generation_probe: Callable[[], SandboxGenerationFingerprint],
    ) -> None:
        self.native_backend = native_backend
        self.codex_home = _closed_directory(codex_home)
        self.provisioning_workspace = _closed_directory(provisioning_workspace)
        self.provisioning_output = _closed_directory(provisioning_output)
        self.qualification_workspace = _closed_directory(qualification_workspace)
        self.qualification_output = _closed_directory(qualification_output)
        self.whoami = whoami
        self.runtime_identity = runtime_identity
        self.boundary_evidence = boundary_evidence
        self.generation_probe = generation_probe
        self._freeze: SandboxGenerationFingerprint | None = None
        self._provisioned = False
        self._canary_used = False
        self._prepared_ordinals: list[int] = []
        runtime_identity.validate()
        boundary_evidence.validate()
        whoami.verify()
        if (
            len(
                {
                    self.codex_home,
                    self.provisioning_workspace,
                    self.provisioning_output,
                    self.qualification_workspace,
                    self.qualification_output,
                }
            )
            != 5
            or any(
                any(directory.iterdir())
                for directory in (
                    self.provisioning_workspace,
                    self.provisioning_output,
                    self.qualification_workspace,
                    self.qualification_output,
                )
            )
            or native_backend.executable != resolve_codex_payload()
        ):
            _fail(PAIR_INVALID)

    def _generation(self) -> SandboxGenerationFingerprint:
        try:
            value = self.generation_probe()
            value.validate()
            return value
        except Exception:
            _fail()

    def _prepared(self, generation: SandboxGenerationFingerprint, context: str) -> PreparedArm:
        catalog = self.native_backend.configured_catalog
        return PreparedArm(
            1,
            context,
            context,
            self.runtime_identity,
            REQUIRED_EXECUTION_POLICY,
            catalog.public_inventory(),
            catalog.catalog_sha256,
            generation.offline_sid,
            generation.value,
            self.boundary_evidence.host_local,
        )

    @staticmethod
    def _schema() -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "const": QUALIFICATION_STATUS},
                "challenge": {"type": "string"},
                "principal_sid": {"type": "string"},
            },
            "required": ["status", "challenge", "principal_sid"],
            "additionalProperties": False,
        }

    def _execute_probe(
        self,
        *,
        generation: SandboxGenerationFingerprint,
        workspace: Path,
        output: Path,
        context: str,
    ) -> tuple[str, NativeExecutionResult]:
        if any(output.iterdir()) or any(workspace.iterdir()):
            _fail(PAIR_INVALID)
        challenge = secrets.token_hex(16)
        if _CHALLENGE.fullmatch(challenge) is None:
            _fail()
        challenge_path = workspace / "qualification-challenge.txt"
        challenge_payload = challenge.encode("ascii")
        try:
            with challenge_path.open("xb") as stream:
                stream.write(challenge_payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            _fail()
        prompt = (
            "This is a runtime qualification probe, not a repository task.\n"
            "Use the shell tool exactly once. Read .\\qualification-challenge.txt and "
            f"run '{self.whoami.path}' /user in that same command.\n"
            "Do not read any other workspace file, write files, inspect directories, "
            "access the network, or use repository, evaluation, oracle, historical-fix, "
            "or task material.\n"
            "Return only JSON with status R2_NON_EXPOSURE_OK, challenge equal to the "
            "file content, and principal_sid equal to the SID reported by whoami.\n"
        ).encode("utf-8")
        try:
            result = self.native_backend.execute(
                prepared_arm=self._prepared(generation, context),
                workspace_root=workspace,
                codex_home=self.codex_home,
                output_root=output,
                prompt=prompt,
                output_schema=self._schema(),
            )
            if challenge_path.read_bytes() != challenge_payload:
                _fail(PAIR_INVALID)
            return challenge, result
        finally:
            challenge_path.unlink(missing_ok=True)

    def _validate_probe(
        self,
        *,
        challenge: str,
        result: NativeExecutionResult,
        generation: SandboxGenerationFingerprint,
    ) -> None:
        metrics = validate_execution_result(result, self.native_backend.configured_catalog)
        if (
            result.disposition != "SUCCESS"
            or metrics.tool_call_count != 1
            or metrics.observed_tool_inventory != ("command_execution",)
        ):
            _fail(PAIR_INVALID)
        try:
            trace = result.trace_path.read_bytes()
            final = json.loads(result.final_message_path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            _fail(PAIR_INVALID)
        completed: list[Mapping[str, object]] = []
        for raw in trace.splitlines():
            try:
                event = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                _fail(PAIR_INVALID)
            if not isinstance(event, dict):
                _fail(PAIR_INVALID)
            item = event.get("item")
            if (
                event.get("type") == "item.completed"
                and isinstance(item, dict)
                and item.get("type") == "command_execution"
            ):
                completed.append(item)
        if len(completed) != 1 or not isinstance(final, dict):
            _fail(PAIR_INVALID)
        item = completed[0]
        command = item.get("command")
        output = item.get("aggregated_output")
        if (
            item.get("status") != "completed"
            or item.get("exit_code") != 0
            or not isinstance(command, str)
            or not isinstance(output, str)
            or str(self.whoami.path).lower() not in command.lower()
            or "/user" not in command.lower()
            or "qualification-challenge.txt" not in command.lower()
            or challenge not in output
            or generation.offline_sid.lower() not in output.lower()
            or "codexsandboxoffline" not in output.lower()
            or final
            != {
                "status": QUALIFICATION_STATUS,
                "challenge": challenge,
                "principal_sid": generation.offline_sid,
            }
        ):
            _fail(PAIR_INVALID)

    def provision_sandbox(self) -> ProvisioningObservation:
        if self._provisioned or self._freeze is not None:
            _fail()
        before = self._generation()
        challenge, result = self._execute_probe(
            generation=before,
            workspace=self.provisioning_workspace,
            output=self.provisioning_output,
            context="r2-non-counted-sandbox-provisioning",
        )
        after = self._generation()
        changed = after != before
        if not changed:
            self._validate_probe(challenge=challenge, result=result, generation=after)
        elif result.tree_terminated is not True:
            _fail(SAME_MACHINE_WINDOW_REJECTED)
        self._provisioned = True
        return ProvisioningObservation(before, after, result, changed)

    def bind_freeze(self, generation: SandboxGenerationFingerprint) -> None:
        if not self._provisioned or self._freeze is not None:
            _fail()
        generation.validate()
        if self._generation() != generation:
            _fail(SAME_MACHINE_WINDOW_REJECTED)
        self._freeze = generation

    def run_canary(
        self,
        *,
        executable: PinnedExecutable,
        expected_catalog: ToolCatalog,
        launcher_environment: Mapping[str, str],
        model_tool_environment: Mapping[str, str],
    ) -> CanaryObservation:
        if self._freeze is None or self._canary_used:
            _fail()
        if (
            executable != self.native_backend.executable
            or expected_catalog != self.native_backend.configured_catalog
            or launcher_environment.get("CODEX_HOME") != str(self.codex_home)
            or "PATH" in launcher_environment
            or "CODEX_HOME" in model_tool_environment
        ):
            _fail(PAIR_INVALID)
        challenge, result = self._execute_probe(
            generation=self._freeze,
            workspace=self.qualification_workspace,
            output=self.qualification_output,
            context="r2-information-dependency-qualification",
        )
        self._validate_probe(challenge=challenge, result=result, generation=self._freeze)
        self._canary_used = True
        catalog = self.native_backend.configured_catalog
        return CanaryObservation(
            "r2-information-dependency-qualification",
            self.qualification_workspace.name,
            self.runtime_identity,
            REQUIRED_EXECUTION_POLICY,
            catalog.public_inventory(),
            catalog.catalog_sha256,
            self.boundary_evidence.credential_sentinel_visible,
            self.boundary_evidence.network_tcp_egress_denied,
            self.boundary_evidence.host_local,
            self._freeze.offline_sid,
            self._freeze.value,
        )

    def prepare_arm(
        self,
        *,
        arm_ordinal: int,
        executable: PinnedExecutable,
        expected_catalog: ToolCatalog,
        launcher_environment: Mapping[str, str],
        model_tool_environment: Mapping[str, str],
    ) -> ArmPreparationObservation:
        if (
            self._freeze is None
            or not self._canary_used
            or arm_ordinal not in {1, 2}
            or arm_ordinal in self._prepared_ordinals
            or executable != self.native_backend.executable
            or expected_catalog != self.native_backend.configured_catalog
            or launcher_environment.get("CODEX_HOME") != str(self.codex_home)
            or "PATH" in launcher_environment
            or "CODEX_HOME" in model_tool_environment
            or self._generation() != self._freeze
        ):
            _fail(PAIR_INVALID)
        self.native_backend.executable.verify()
        self.boundary_evidence.validate()
        self._prepared_ordinals.append(arm_ordinal)
        catalog = self.native_backend.configured_catalog
        token = uuid.uuid4().hex
        return ArmPreparationObservation(
            arm_ordinal,
            f"r2-pre-id-context-{arm_ordinal}-{token}",
            f"r2-pre-id-no-workspace-{arm_ordinal}-{token}",
            self.runtime_identity,
            REQUIRED_EXECUTION_POLICY,
            catalog.public_inventory(),
            catalog.catalog_sha256,
            "NONE",
            self._freeze.offline_sid,
            self._freeze.value,
            self.boundary_evidence.credential_sentinel_visible,
            self.boundary_evidence.host_local,
        )

    @property
    def prepared_ordinals(self) -> tuple[int, ...]:
        return tuple(self._prepared_ordinals)


@dataclass(frozen=True, repr=False)
class PreAttemptRuntimeReadiness:
    disposition: str
    freeze: RuntimeFreeze
    provisioning: ProvisioningObservation
    qualification: CanaryQualification
    materialization: PairMaterializationEvidence
    validation: PreAttemptValidation
    prepared_control: PreparedArm
    prepared_treatment: PreparedArm
    next_arm: str
    next_arm_ordinal: int
    task_exposure_state: str = "NONE"
    attempt_handle: None = None
    target_pair_attempt_events: int = 0


class PreAttemptFrozenRuntimeWindow:
    """One-shot controller that stops immediately before Attempt admission."""

    def __init__(
        self,
        *,
        backend: NativePreExposureObservationBackend,
        adapter: CodexRunnerAdapter,
        freeze_probe: RuntimeFreezeProbe,
        materializer: FrozenGitMaterializer,
        pair_lock: PairLedgerLock,
        sealed_order: SealedArmOrder,
    ) -> None:
        if (
            adapter.backend is not backend
            or freeze_probe.pair_lock is not pair_lock
            or freeze_probe.qualification_helper != backend.whoami
        ):
            _fail(PAIR_INVALID)
        self.backend = backend
        self.adapter = adapter
        self.freeze_probe = freeze_probe
        self.materializer = materializer
        self.pair_lock = pair_lock
        self.sealed_order = sealed_order
        self._used = False

    def run(self) -> PreAttemptRuntimeReadiness:
        if self._used:
            _fail()
        self._used = True
        with self.pair_lock:
            self.freeze_probe.assert_runtime_quiescent()
            provisioning = self.backend.provision_sandbox()
            freeze = self.freeze_probe.capture()
            if provisioning.generation_after != freeze.generation:
                _fail(SAME_MACHINE_WINDOW_REJECTED)
            self.backend.bind_freeze(freeze.generation)
            qualification = self.adapter.qualify_canary()
            self.freeze_probe.assert_unchanged(freeze)

            materialization = self.materializer.qualify_pair(self.pair_lock.binding.pair_id)
            if self.materializer.leaves.active is not None:
                _fail(PAIR_INVALID)
            self.freeze_probe.assert_unchanged(freeze)

            prepared: dict[int, PreparedArm] = {}
            for ordinal in self.sealed_order.ordinals():
                prepared[ordinal] = self.adapter.prepare_formal_arm(ordinal)
                if self.materializer.leaves.active is not None:
                    _fail(PAIR_INVALID)
                self.freeze_probe.assert_unchanged(freeze)
            if self.backend.prepared_ordinals != self.sealed_order.ordinals():
                _fail(PAIR_INVALID)

            validation = PreAttemptExecutionCoordinator(self.pair_lock).validate(
                materialization=materialization,
                canary=qualification,
                control=prepared[1],
                treatment=prepared[2],
            )
            self.freeze_probe.assert_unchanged(freeze)
            if validation.attempt_handle is not None or validation.task_exposure_state != "NONE":
                _fail(PAIR_INVALID)
            return PreAttemptRuntimeReadiness(
                READY_BEFORE_ATTEMPT,
                freeze,
                provisioning,
                qualification,
                materialization,
                validation,
                prepared[1],
                prepared[2],
                self.sealed_order.order[0],
                self.sealed_order.ordinals()[0],
            )
