from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Protocol


MANIFEST_SCHEMA = "c1-machine-policy-setup-observer-authorization-correction-freeze.v4"
PRECHECK_SCHEMA = "c1-machine-policy-independent-rollback-precheck.v2"
OBSERVATION_SCHEMA = "c1-machine-policy-observation.v2"
EVIDENCE_SCHEMA = "c1-windows-sandbox-machine-policy-setup-evidence.v3"
RECEIPT_SCHEMA = "c1-windows-sandbox-machine-policy-receipt.v1"
ATTEMPT_ID = "C1-machine-policy-setup-04"
EXPECTED_REQUIREMENTS_BYTES = 58
EXPECTED_REQUIREMENTS_SHA256 = (
    "9aa1f17cc4a36a3ac502862eb42d84044799eaf1b4de7c8cb1e31a25b10c3440"
)
EXPECTED_CONFIG_SHA256 = (
    "ed33eb56dae642e0a6695c9c1e4455210ffd6319ee7f119da6ee3e92bb9fd587"
)
EXPECTED_POWERSHELL_SHA256 = (
    "7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5"
)
EXPECTED_POWERSHELL_PATH = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)
EXPECTED_OBSERVER_BYTES = 6338
EXPECTED_OBSERVER_SHA256 = (
    "3215cb143933f2728e34b0ab29f4d14edfaa5dfa0a9a263705fd1fa0d85c2b0d"
)
EXPECTED_SID_SHA256 = (
    "f0499f65a3828dfd191d0f3179ee47528dd723df2c1753e0f4131f83cd5017ce"
)
EXPECTED_RULE_SUMMARY_SHA256 = (
    "177a1d63754db207bdf5b86c924434b899c618e2d07acc4f84e9a661797ec302"
)
EXPECTED_SECURITY_DESCRIPTOR_SHA256 = (
    "9b3806eb0682cd3451b2226b6980de0aa0f2d70d5de9a863be65e12e8aa73d2d"
)
TERMINAL_PRECEDENCE = (
    "MACHINE_POLICY_LEAKAGE_REVIEW_REQUIRED",
    "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS",
    "MACHINE_POLICY_ROLLBACK_FAILED",
    "MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED",
    "MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE",
    "MACHINE_POLICY_DRIFT_REVIEW_REQUIRED",
    "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE",
    "MACHINE_POLICY_AUTHORITY_MISMATCH",
    "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE",
    "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
    "MACHINE_POLICY_PRECONDITION_FAILED",
    "MACHINE_POLICY_PUBLICATION_FAILED",
    "MACHINE_POLICY_SETUP_APPLIED",
)
FORBIDDEN_FIELDS = {
    "raw_sid",
    "account_name",
    "firewall_rule_name",
    "firewall_inventory",
    "security_descriptor",
    "raw_requirements_payload",
    "credential",
    "token",
    "cookie",
    "authorization",
    "prompt",
    "response",
    "event_stream",
    "unrelated_local_path",
}


class SetupError(RuntimeError):
    def __init__(
        self,
        status: str,
        diagnostic: str,
        *,
        identity: ExecutionIdentity | None = None,
        observer_stage: str | None = None,
        observer_error_class: str | None = None,
    ):
        super().__init__(diagnostic)
        self.status = status
        self.diagnostic = diagnostic
        self.identity = identity
        self.observer_stage = observer_stage
        self.observer_error_class = observer_error_class


@dataclass(frozen=True)
class ExecutionIdentity:
    sid_sha256: str
    account_class: str
    administrator_role_enabled: bool


@dataclass(frozen=True)
class MachineState:
    account_present: bool
    account_enabled: bool
    password_required: bool
    sid_sha256: str
    domain_profile_enabled: bool
    private_profile_enabled: bool
    public_profile_enabled: bool
    relevant_outbound_rule_count: int
    outbound_block_rule_count: int
    outbound_allow_rule_count: int
    rule_summary_bytes: int
    rule_summary_sha256: str
    account_block_relation_verified: bool
    security_descriptor_sha256: str
    target_exists: bool
    legacy_target_exists: bool
    user_target_exists: bool


@dataclass(frozen=True)
class MachineObservation:
    identity: ExecutionIdentity
    state: MachineState


class Adapter(Protocol):
    target_path: Path

    def path_is_safe(self) -> bool: ...
    def observe_identity(self) -> ExecutionIdentity: ...
    def observe(self) -> MachineObservation: ...
    def publish(self, payload: bytes) -> tuple[str, ...]: ...
    def read_target(self) -> bytes: ...
    def target_is_regular_file(self) -> bool: ...
    def rollback(self, created_directories: tuple[str, ...]) -> str: ...
    def rollback_channel_available(self) -> bool: ...


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve_git_head(repo: Path, *, runner=subprocess.run) -> str:
    """Resolve HEAD from the bounded repository root, never the deep freeze path."""
    try:
        completed = runner(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError(
            "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE",
            "bounded Git identity check could not launch",
        ) from exc
    head = completed.stdout.strip()
    if completed.returncode != 0 or completed.stderr or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SetupError(
            "MACHINE_POLICY_EXECUTOR_IDENTITY_UNAVAILABLE",
            "bounded Git identity check failed",
        )
    return head


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "repository root unavailable")


def _git(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def validate_frozen_bindings(base: Path, manifest: Mapping[str, object]) -> None:
    entries = manifest.get("frozen_files")
    if not isinstance(entries, list):
        raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "frozen inventory missing")
    expected = {str(entry["path"]) for entry in entries if isinstance(entry, dict)}
    actual = {
        path.name for path in base.iterdir()
        if path.is_file() and path.name != "setup-manifest.json"
    }
    if expected != actual:
        raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "frozen inventory mismatch")
    for entry in entries:
        if not isinstance(entry, dict):
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "frozen binding malformed")
        payload = (base / str(entry["path"])).read_bytes()
        if len(payload) != entry.get("bytes") or sha256(payload) != entry.get("sha256"):
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "frozen binding mismatch")


def validate_source_bindings(repo: Path, manifest: Mapping[str, object]) -> None:
    entries = manifest.get("source_bindings")
    if not isinstance(entries, list):
        raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "source bindings missing")
    for entry in entries:
        if not isinstance(entry, dict):
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "source binding malformed")
        path = str(entry["path"])
        oid = str(_git(repo, "rev-parse", f'{entry["commit"]}:{path}'))
        if oid != entry.get("git_blob_oid"):
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "source blob mismatch")
        payload = _git(repo, "cat-file", "blob", oid, binary=True)
        assert isinstance(payload, bytes)
        if len(payload) != entry.get("bytes") or sha256(payload) != entry.get("sha256"):
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "source content mismatch")


def _load_object(payload: bytes, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", f"invalid {label}") from exc
    if not isinstance(value, dict):
        raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", f"invalid {label}")
    return value


def _walk_forbidden(value: object) -> None:
    if isinstance(value, dict):
        overlap = FORBIDDEN_FIELDS.intersection(value)
        if overlap:
            raise SetupError(
                "MACHINE_POLICY_LEAKAGE_REVIEW_REQUIRED",
                "retained evidence contains a forbidden field",
            )
        for child in value.values():
            _walk_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _walk_forbidden(child)


def validate_precheck(
    payload: bytes, *, freeze_commit: str, rollback_script_sha256: str
) -> Mapping[str, object]:
    value = _load_object(payload, "rollback precheck")
    required = {
        "schema",
        "setup_freeze_commit",
        "rollback_script_sha256",
        "powershell_executable_sha256",
        "owner_sid_sha256",
        "owner_account_class",
        "owner_shell_independent_from_codex",
        "administrator_role_enabled",
        "target_absent",
        "rollback_script_outside_policy_and_scratch_roots",
        "shell_held_open_until_terminal",
        "observed_at_utc",
        "status",
        "diagnostic",
    }
    if set(value) != required:
        raise SetupError("MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE", "precheck field set mismatch")
    expected = {
        "schema": PRECHECK_SCHEMA,
        "setup_freeze_commit": freeze_commit,
        "rollback_script_sha256": rollback_script_sha256,
        "powershell_executable_sha256": EXPECTED_POWERSHELL_SHA256,
        "owner_account_class": "owner_administrator",
        "owner_shell_independent_from_codex": True,
        "administrator_role_enabled": True,
        "target_absent": True,
        "rollback_script_outside_policy_and_scratch_roots": True,
        "shell_held_open_until_terminal": True,
        "status": "INDEPENDENT_ELEVATED_ROLLBACK_CHANNEL_READY",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SetupError(
                "MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE",
                "independent rollback channel is unavailable",
            )
    owner_sid_sha256 = value.get("owner_sid_sha256")
    if (
        not isinstance(owner_sid_sha256, str)
        or len(owner_sid_sha256) != 64
        or any(character not in "0123456789abcdef" for character in owner_sid_sha256)
    ):
        raise SetupError(
            "MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE",
            "owner identity binding is invalid",
        )
    if not isinstance(value.get("observed_at_utc"), str):
        raise SetupError("MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE", "precheck timestamp missing")
    if not isinstance(value.get("diagnostic"), str) or len(str(value["diagnostic"])) > 160:
        raise SetupError("MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE", "precheck diagnostic invalid")
    _walk_forbidden(value)
    return value


def validate_state(state: MachineState, *, require_target_absent: bool) -> None:
    expected = (
        state.account_present,
        state.account_enabled,
        state.password_required,
        state.sid_sha256 == EXPECTED_SID_SHA256,
        state.domain_profile_enabled,
        state.private_profile_enabled,
        state.public_profile_enabled,
        state.relevant_outbound_rule_count == 2,
        state.outbound_block_rule_count == 1,
        state.outbound_allow_rule_count == 1,
        state.rule_summary_bytes == 367,
        state.rule_summary_sha256 == EXPECTED_RULE_SUMMARY_SHA256,
        state.account_block_relation_verified,
        state.security_descriptor_sha256 == EXPECTED_SECURITY_DESCRIPTOR_SHA256,
        not state.legacy_target_exists,
        not state.user_target_exists,
    )
    if not all(expected):
        raise SetupError("MACHINE_POLICY_DRIFT_REVIEW_REQUIRED", "bounded machine state drifted")
    if require_target_absent and state.target_exists:
        raise SetupError("MACHINE_POLICY_DRIFT_REVIEW_REQUIRED", "managed requirements target already exists")


def bounded_identity(identity: ExecutionIdentity) -> Mapping[str, object]:
    return {
        "sid_sha256": identity.sid_sha256,
        "account_class": identity.account_class,
        "administrator_role_enabled": identity.administrator_role_enabled,
    }


def validate_execution_identity(
    identity: ExecutionIdentity, *, precheck: Mapping[str, object]
) -> None:
    expected_sid = precheck.get("owner_sid_sha256")
    if (
        identity.account_class != "owner_candidate"
        or identity.administrator_role_enabled is not True
        or identity.sid_sha256 != expected_sid
    ):
        raise SetupError(
            "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE",
            "setup identity is not the elevated rollback owner",
            identity=identity,
            observer_stage="identity",
            observer_error_class="INSUFFICIENT_PRIVILEGE",
        )


def bounded_state(state: MachineState) -> Mapping[str, object]:
    return {
        "account_present": state.account_present,
        "account_enabled": state.account_enabled,
        "password_required": state.password_required,
        "sid_sha256": state.sid_sha256,
        "firewall_profiles_enabled": {
            "domain": state.domain_profile_enabled,
            "private": state.private_profile_enabled,
            "public": state.public_profile_enabled,
        },
        "relevant_outbound_rule_count": state.relevant_outbound_rule_count,
        "outbound_block_rule_count": state.outbound_block_rule_count,
        "outbound_allow_rule_count": state.outbound_allow_rule_count,
        "rule_summary_bytes": state.rule_summary_bytes,
        "rule_summary_sha256": state.rule_summary_sha256,
        "account_block_relation_verified": state.account_block_relation_verified,
        "security_descriptor_sha256": state.security_descriptor_sha256,
        "target_exists": state.target_exists,
        "legacy_target_exists": state.legacy_target_exists,
        "user_target_exists": state.user_target_exists,
    }


def downstream_receipt() -> Mapping[str, object]:
    return {
        "schema": RECEIPT_SCHEMA,
        "sandbox_implementation": "elevated",
        "managed_requirement_enforced": True,
        "fallback_observed": False,
        "config_sha256": EXPECTED_CONFIG_SHA256,
        "requirements_sha256": EXPECTED_REQUIREMENTS_SHA256,
        "machine_state_change_owner_authorized": True,
        "rollback_path_reviewed": True,
    }


def select_terminal(statuses: list[str]) -> str:
    known = [status for status in TERMINAL_PRECEDENCE if status in statuses]
    if not known:
        raise ValueError("no known terminal")
    return known[0]


def _terminal(
    *,
    status: str,
    freeze_commit: str,
    plan_sha256: str,
    diagnostic: str,
    identity: ExecutionIdentity | None = None,
    observer_stage: str | None = None,
    observer_error_class: str | None = None,
    executing_commit_verified: bool = True,
) -> Mapping[str, object]:
    value = {
        "schema": "c1-machine-policy-setup-terminal.v4",
        "status": status,
        "setup_attempt_id": ATTEMPT_ID,
        "freeze_commit": freeze_commit,
        "setup_plan_sha256": plan_sha256,
        "executing_commit_verified": executing_commit_verified,
        "machine_mutation_attempted": status in {
            "MACHINE_POLICY_PUBLICATION_FAILED",
            "MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED",
            "MACHINE_POLICY_ROLLBACK_FAILED",
            "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS",
            "MACHINE_POLICY_SETUP_APPLIED",
        },
        "sandbox_qualification_executed": False,
        "hosted_request_executed": False,
        "randomization_created": False,
        "execution_identity": bounded_identity(identity) if identity else None,
        "observer_failure": (
            {
                "stage": observer_stage,
                "error_class": observer_error_class,
            }
            if observer_stage and observer_error_class
            else None
        ),
        "diagnostic": diagnostic[:240],
    }
    _walk_forbidden(value)
    return value


def execute_setup(
    *,
    freeze_commit: str,
    executing_commit: str,
    owner_authorized_setup_commit: str,
    frozen_plan_sha256: str,
    owner_authorized_setup_plan_sha256: str,
    requirements_payload: bytes,
    rollback_script_payload: bytes,
    precheck_payload: bytes,
    adapter: Adapter,
    now: datetime | None = None,
) -> tuple[Mapping[str, object], Mapping[str, object] | None, Mapping[str, object] | None]:
    mutation_attempted = False
    created_directories: tuple[str, ...] = ()
    pre_state: MachineState | None = None
    identity: ExecutionIdentity | None = None
    try:
        if freeze_commit != executing_commit or owner_authorized_setup_commit != executing_commit:
            raise SetupError("MACHINE_POLICY_AUTHORITY_MISMATCH", "owner authority differs from executing freeze")
        if owner_authorized_setup_plan_sha256 != frozen_plan_sha256:
            raise SetupError("MACHINE_POLICY_AUTHORITY_MISMATCH", "setup plan authority mismatch")
        if len(requirements_payload) != EXPECTED_REQUIREMENTS_BYTES or sha256(requirements_payload) != EXPECTED_REQUIREMENTS_SHA256:
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "requirements payload binding mismatch")
        if not adapter.path_is_safe():
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "target path is unsafe")
        precheck = validate_precheck(
            precheck_payload,
            freeze_commit=freeze_commit,
            rollback_script_sha256=sha256(rollback_script_payload),
        )
        if not adapter.rollback_channel_available():
            raise SetupError("MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE", "independent rollback shell closed")
        identity = adapter.observe_identity()
        validate_execution_identity(identity, precheck=precheck)
        pre_observation = adapter.observe()
        validate_execution_identity(pre_observation.identity, precheck=precheck)
        if pre_observation.identity != identity:
            raise SetupError(
                "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE",
                "setup identity changed between bounded observations",
                identity=pre_observation.identity,
                observer_stage="identity",
                observer_error_class="IDENTITY_DRIFT",
            )
        pre_state = pre_observation.state
        validate_state(pre_state, require_target_absent=True)
        mutation_attempted = True
        try:
            created_directories = adapter.publish(requirements_payload)
        except SetupError:
            raise
        except OSError as exc:
            raise SetupError(
                "MACHINE_POLICY_PUBLICATION_FAILED", "atomic publication failed"
            ) from exc
        try:
            if not adapter.target_is_regular_file():
                raise SetupError("MACHINE_POLICY_PUBLICATION_FAILED", "published target is not a regular file")
            installed = adapter.read_target()
            if len(installed) != EXPECTED_REQUIREMENTS_BYTES or sha256(installed) != EXPECTED_REQUIREMENTS_SHA256:
                raise SetupError("MACHINE_POLICY_PUBLICATION_FAILED", "post-publication content mismatch")
            post_observation = adapter.observe()
            validate_execution_identity(post_observation.identity, precheck=precheck)
            if post_observation.identity != identity:
                raise SetupError(
                    "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE",
                    "setup identity changed after publication",
                    identity=post_observation.identity,
                    observer_stage="identity",
                    observer_error_class="IDENTITY_DRIFT",
                )
            post_state = post_observation.state
            validate_state(post_state, require_target_absent=False)
            if not post_state.target_exists:
                raise SetupError("MACHINE_POLICY_PUBLICATION_FAILED", "target absent after publication")
            if not adapter.rollback_channel_available():
                raise SetupError("MACHINE_POLICY_ROLLBACK_CHANNEL_UNAVAILABLE", "rollback shell closed before terminal")
        except SetupError:
            raise
        except BaseException as exc:
            raise SetupError(
                "MACHINE_POLICY_PUBLICATION_FAILED", "post-publication verification failed"
            ) from exc
        status = "MACHINE_POLICY_SETUP_APPLIED"
        diagnostic = "exact managed requirement installed; qualification not executed"
        observed = (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
        evidence = {
            "schema": EVIDENCE_SCHEMA,
            "setup_attempt_id": ATTEMPT_ID,
            "freeze_commit": freeze_commit,
            "setup_executor_commit": executing_commit,
            "owner_authorized_setup_commit": owner_authorized_setup_commit,
            "setup_plan_sha256": frozen_plan_sha256,
            "observed_at_utc": observed,
            "execution_identity": bounded_identity(identity),
            "pre_state": bounded_state(pre_state),
            "mutation": {
                "target_kind": "windows_system_managed_requirements",
                "expected_bytes": EXPECTED_REQUIREMENTS_BYTES,
                "expected_sha256": EXPECTED_REQUIREMENTS_SHA256,
                "atomic_publication": True,
                "created_directory_count": len(created_directories),
            },
            "post_state": bounded_state(post_state),
            "rollback": {
                "required": True,
                "reviewed": True,
                "attempted": False,
                "completed": False,
                "diagnostic": "independent owner shell held open; rollback not needed",
            },
            "terminal_status": status,
            "diagnostic": diagnostic,
        }
        _walk_forbidden(evidence)
        return _terminal(
            status=status,
            freeze_commit=freeze_commit,
            plan_sha256=frozen_plan_sha256,
            diagnostic=diagnostic,
            identity=identity,
        ), evidence, downstream_receipt()
    except SetupError as exc:
        status = exc.status
        if mutation_attempted:
            try:
                rollback = adapter.rollback(created_directories)
            except BaseException:
                rollback = "FAILED"
            if rollback == "REVIEW_REQUIRED":
                status = select_terminal([status, "MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED"])
            elif rollback == "AMBIGUOUS":
                status = select_terminal([status, "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS"])
            elif rollback != "COMPLETE":
                status = select_terminal([status, "MACHINE_POLICY_ROLLBACK_FAILED"])
        return _terminal(
            status=status,
            freeze_commit=freeze_commit,
            plan_sha256=frozen_plan_sha256,
            diagnostic=exc.diagnostic,
            identity=exc.identity or identity,
            observer_stage=exc.observer_stage,
            observer_error_class=exc.observer_error_class,
        ), None, None


class WindowsAdapter:
    def __init__(
        self,
        *,
        base: Path,
        precheck: Mapping[str, object],
        rollback_request_path: Path,
        rollback_receipt_path: Path,
        rollback_heartbeat_path: Path,
    ):
        program_data = os.environ.get("ProgramData")
        if not program_data:
            raise SetupError("MACHINE_POLICY_PRECONDITION_FAILED", "ProgramData is unavailable")
        self.base = base
        self.policy_root = Path(program_data) / "OpenAI" / "Codex"
        self.target_path = self.policy_root / "requirements.toml"
        self.precheck = precheck
        self.rollback_request_path = rollback_request_path
        self.rollback_receipt_path = rollback_receipt_path
        self.rollback_heartbeat_path = rollback_heartbeat_path
        self._created: tuple[str, ...] = ()

    def path_is_safe(self) -> bool:
        if any(part == ".." for part in self.target_path.parts):
            return False
        for path in (self.policy_root, self.policy_root.parent):
            if path.exists():
                info = os.lstat(path)
                attributes = getattr(info, "st_file_attributes", 0)
                if path.is_symlink() or attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    return False
        return self.target_path.parent == self.policy_root

    def _run_observer(self, mode: str) -> Mapping[str, object]:
        script = self.base / "machine_policy_observer.ps1"
        try:
            observer_payload = script.read_bytes()
            powershell_payload = EXPECTED_POWERSHELL_PATH.read_bytes()
        except OSError as exc:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer launch binding is unavailable",
                observer_stage="authorization",
                observer_error_class="LAUNCH_BINDING_UNAVAILABLE",
            ) from exc
        if (
            len(observer_payload) != EXPECTED_OBSERVER_BYTES
            or sha256(observer_payload) != EXPECTED_OBSERVER_SHA256
        ):
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer bytes differ from the freeze",
                observer_stage="authorization",
                observer_error_class="OBSERVER_DIGEST_MISMATCH",
            )
        if sha256(powershell_payload) != EXPECTED_POWERSHELL_SHA256:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded PowerShell executable differs from the freeze",
                observer_stage="authorization",
                observer_error_class="POWERSHELL_DIGEST_MISMATCH",
            )
        try:
            completed = subprocess.run(
                [
                    str(EXPECTED_POWERSHELL_PATH),
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                    "-Mode",
                    mode,
                ],
                check=False,
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer process did not complete",
                observer_stage="launch",
                observer_error_class=type(exc).__name__.upper(),
            ) from exc
        if completed.returncode != 0 or bool(completed.stderr):
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer child was denied by AuthorizationManager",
                observer_stage="authorization",
                observer_error_class="AUTHORIZATION_MANAGER_DENIED",
            )
        try:
            value = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer envelope is unavailable",
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            ) from exc
        if not isinstance(value, dict) or set(value) != {
            "schema", "mode", "status", "stage", "error_class",
            "identity", "machine_state",
        }:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer envelope field set mismatch",
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            )
        if value.get("schema") != OBSERVATION_SCHEMA or value.get("mode") != mode.lower():
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer envelope binding mismatch",
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            )
        identity_value = value.get("identity")
        identity: ExecutionIdentity | None = None
        if identity_value is not None:
            if not isinstance(identity_value, dict) or set(identity_value) != {
                "sid_sha256", "account_class", "administrator_role_enabled",
            }:
                raise SetupError(
                    "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                    "bounded observer identity field set mismatch",
                    observer_stage="identity",
                    observer_error_class="INVALID_ENVELOPE",
                )
            try:
                identity = ExecutionIdentity(**identity_value)
            except TypeError as exc:
                raise SetupError(
                    "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                    "bounded observer identity is invalid",
                    observer_stage="identity",
                    observer_error_class="INVALID_ENVELOPE",
                ) from exc
        stage = value.get("stage")
        error_class = value.get("error_class")
        if not isinstance(stage, str) or not isinstance(error_class, str):
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer classification is invalid",
                identity=identity,
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            )
        if value.get("status") == "OBSERVATION_FAILED":
            status = (
                "MACHINE_POLICY_INSUFFICIENT_PRIVILEGE"
                if error_class == "INSUFFICIENT_PRIVILEGE"
                else "MACHINE_POLICY_PRECONDITION_FAILED"
            )
            raise SetupError(
                status,
                f"bounded observer failed at {stage} ({error_class})",
                identity=identity,
                observer_stage=stage,
                observer_error_class=error_class,
            )
        if (
            value.get("status") != "OBSERVATION_PASSED"
        ):
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer process contract failed",
                identity=identity,
                observer_stage=stage,
                observer_error_class="PROCESS_CONTRACT_FAILED",
            )
        if identity is None:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer omitted execution identity",
                observer_stage="identity",
                observer_error_class="INVALID_ENVELOPE",
            )
        return value

    def observe_identity(self) -> ExecutionIdentity:
        value = self._run_observer("Identity")
        if value.get("machine_state") is not None:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "identity probe exposed a machine-state payload",
                observer_stage="identity",
                observer_error_class="INVALID_ENVELOPE",
            )
        identity = value["identity"]
        assert isinstance(identity, dict)
        return ExecutionIdentity(**identity)

    def observe(self) -> MachineObservation:
        value = self._run_observer("Full")
        identity_value = value["identity"]
        state_value = value.get("machine_state")
        if not isinstance(identity_value, dict) or not isinstance(state_value, dict):
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "full observer omitted bounded state",
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            )
        try:
            return MachineObservation(
                identity=ExecutionIdentity(**identity_value),
                state=MachineState(**state_value),
            )
        except TypeError as exc:
            raise SetupError(
                "MACHINE_POLICY_OBSERVER_LAUNCH_FAILED",
                "bounded observer state field mismatch",
                observer_stage="envelope",
                observer_error_class="INVALID_ENVELOPE",
            ) from exc

    def publish(self, payload: bytes) -> tuple[str, ...]:
        created: list[str] = []
        for path in (self.policy_root.parent, self.policy_root):
            if not path.exists():
                path.mkdir(exist_ok=False)
                created.append(path.name)
        staging = self.policy_root / f".requirements.{uuid.uuid4().hex}.staging"
        try:
            with staging.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if self.target_path.exists():
                raise SetupError("MACHINE_POLICY_DRIFT_REVIEW_REQUIRED", "target appeared before publication")
            os.link(staging, self.target_path)
            staging.unlink()
        finally:
            if staging.exists():
                staging.unlink()
        self._created = tuple(created)
        return self._created

    def read_target(self) -> bytes:
        return self.target_path.read_bytes()

    def target_is_regular_file(self) -> bool:
        return self.target_path.is_file() and not self.target_path.is_symlink()

    def rollback(self, created_directories: tuple[str, ...]) -> str:
        if self.rollback_request_path.exists() or self.rollback_receipt_path.exists():
            return "REVIEW_REQUIRED"
        request = canonical_json(
            {
                "schema": "c1-machine-policy-rollback-request.v1",
                "created_directories": list(created_directories),
                "requirements_sha256": EXPECTED_REQUIREMENTS_SHA256,
            }
        )
        self.rollback_request_path.write_bytes(request)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and not self.rollback_receipt_path.exists():
            time.sleep(0.1)
        if not self.rollback_receipt_path.exists():
            return "AMBIGUOUS"
        receipt = _load_object(self.rollback_receipt_path.read_bytes(), "rollback receipt")
        status = receipt.get("status")
        if status == "MACHINE_POLICY_ROLLBACK_COMPLETE":
            return "COMPLETE"
        if status == "MACHINE_POLICY_ROLLBACK_STATE_AMBIGUOUS":
            return "AMBIGUOUS"
        if status == "MACHINE_POLICY_ROLLBACK_REVIEW_REQUIRED":
            return "REVIEW_REQUIRED"
        return "FAILED"

    def rollback_channel_available(self) -> bool:
        try:
            age = time.time() - self.rollback_heartbeat_path.stat().st_mtime
        except OSError:
            return False
        return self.precheck.get("shell_held_open_until_terminal") is True and age <= 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-authorized-freeze-commit", required=True)
    parser.add_argument("--owner-authorized-setup-plan-sha256", required=True)
    parser.add_argument("--rollback-precheck", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    base = Path(__file__).resolve().parent
    repo = _repo_root(base)
    manifest = _load_object((base / "setup-manifest.json").read_bytes(), "manifest")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        return 2
    validate_frozen_bindings(base, manifest)
    validate_source_bindings(repo, manifest)
    publication = manifest.get("publication")
    if not isinstance(publication, dict):
        return 2
    output_root = (repo / str(publication["output_root"])).resolve()
    coordination = (repo / str(publication["coordination_root"])).resolve()
    if output_root.exists() or not coordination.is_dir() or coordination.is_symlink():
        return 2
    try:
        head = resolve_git_head(repo)
    except SetupError as exc:
        terminal = _terminal(
            status=exc.status,
            freeze_commit="0" * 40,
            plan_sha256=str(manifest["setup_plan_sha256"]),
            diagnostic=exc.diagnostic,
            executing_commit_verified=False,
        )
        output_root.mkdir(parents=True, exist_ok=False)
        (output_root / "terminal.json").write_bytes(canonical_json(terminal))
        return 2
    precheck_payload = args.rollback_precheck.read_bytes()
    precheck = _load_object(precheck_payload, "rollback precheck")
    adapter = WindowsAdapter(
        base=base,
        precheck=precheck,
        rollback_request_path=coordination / "rollback-request.json",
        rollback_receipt_path=coordination / "rollback-receipt.json",
        rollback_heartbeat_path=coordination / "rollback-heartbeat.txt",
    )
    terminal, evidence, receipt = execute_setup(
        freeze_commit=head,
        executing_commit=head,
        owner_authorized_setup_commit=args.owner_authorized_freeze_commit,
        frozen_plan_sha256=str(manifest["setup_plan_sha256"]),
        owner_authorized_setup_plan_sha256=args.owner_authorized_setup_plan_sha256,
        requirements_payload=(base / "requirements.toml").read_bytes(),
        rollback_script_payload=(base / "independent_owner_rollback.ps1").read_bytes(),
        precheck_payload=precheck_payload,
        adapter=adapter,
    )
    output_root.mkdir(parents=True, exist_ok=False)
    (output_root / "terminal.json").write_bytes(canonical_json(terminal))
    if evidence is not None and receipt is not None:
        (output_root / "setup-evidence.json").write_bytes(canonical_json(evidence))
        (output_root / "machine-policy-receipt.json").write_bytes(canonical_json(receipt))
    return 0 if terminal["status"] == "MACHINE_POLICY_SETUP_APPLIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
