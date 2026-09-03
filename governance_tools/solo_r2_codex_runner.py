"""Concrete native Codex runner and pre-exposure gates for Solo R2.

The configured tool surface is frozen before task exposure.  Actual tool use
is derived only from the authoritative ``codex exec --json`` stream after the
run; the two arms are not required to use the same tools.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import uuid
from typing import Callable, Mapping, Protocol, Sequence, TypeVar

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from governance_tools.solo_r2_attempt_materialization import (
    HostLocalIsolation,
    PinnedExecutable,
)


PAIR_INVALID = "PAIR_INVALID / STOP"
PRE_ATTEMPT_INFRA_FAILURE = "PRE_ATTEMPT_INFRA_FAILURE / STOP"
AGENT_FAILURE = "AGENT_FAILURE"
SUCCESS = "SUCCESS"
TOOL_CALL_LIMIT_REACHED = "TOOL_CALL_LIMIT_REACHED"
APPROVAL_REQUIRED_DENIED = "APPROVAL_REQUIRED_DENIED"
MODEL_SELECTOR = "gpt-5.6-sol"
REASONING_EFFORT = "high"
IDENTITY_DISPOSITION = "DECLARED_NOT_VERIFIED"
TOOL_CALL_CAP_ENFORCEMENT = "MEASURED_POST_HOC"
HARD_PRE_DISPATCH_CAP = "NOT_CLAIMED"
MAX_TOOL_CALLS = 60
MAX_ELAPSED_SECONDS = 1_800
MAX_TRACE_BYTES = 64 * 1024 * 1024
MAX_TRACE_LINE_BYTES = 1024 * 1024
MAX_PROMPT_BYTES = 1024 * 1024
CODEX_PAYLOAD_BYTE_LENGTH = 293_056_816
CODEX_PAYLOAD_SHA256 = "0d916cde6e0f5231b24f4d861c7a6c591bbed67925d8a26e1335c18a15e31819"
WINDOWS_POWERSHELL_PATH = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)
WINDOWS_POWERSHELL_BYTE_LENGTH = 454_656
WINDOWS_POWERSHELL_SHA256 = "7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5"
LOCAL_ACCOUNTS_MODULE_PATH = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules"
    r"\Microsoft.PowerShell.LocalAccounts\1.0.0.0"
    r"\Microsoft.Powershell.LocalAccounts.dll"
)
LOCAL_ACCOUNTS_MODULE_BYTE_LENGTH = 94_208
LOCAL_ACCOUNTS_MODULE_SHA256 = "e3fd92382a1ffc15724b215dcc3729961d0af730c93362db317d98b43c54c9ce"
SANDBOX_GENERATION_SCHEMA = "solo-r2-sandbox-generation/v1"
SANDBOX_GENERATION_PREFIX = "sha256:"
MAX_SANDBOX_USERS_JSON_BYTES = 1024 * 1024
_PAYLOAD_DIRECTORY_NAME = re.compile(r"[0-9a-f]{16}")
_SID = re.compile(r"S-1-(?:\d+-)+\d+")
_PASSWORD_LAST_SET_UTC = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z"
)
_PASSIVE_ITEM_TYPES = frozenset({"agent_message", "reasoning"})
_TOP_LEVEL_EVENTS = frozenset(
    {
        "thread.started",
        "turn.started",
        "item.started",
        "item.updated",
        "item.completed",
        "turn.completed",
        "turn.failed",
        "error",
    }
)
_WINDOWS_JOB_GUARD = (
    "import os,pathlib,sys,time\n"
    "p=pathlib.Path(sys.argv[1])\n"
    "while not p.exists(): time.sleep(.005)\n"
    "os.execv(sys.argv[2],sys.argv[2:])\n"
)


class RunnerGateError(RuntimeError):
    def __init__(self, code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str = PRE_ATTEMPT_INFRA_FAILURE) -> None:
    raise RunnerGateError(code)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            _fail(PAIR_INVALID)
        value[key] = item
    return value


def _json_object(payload: bytes) -> dict[str, object]:
    if not payload or len(payload) > MAX_TRACE_LINE_BYTES:
        _fail(PAIR_INVALID)
    try:
        value = json.loads(payload, object_pairs_hook=_object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail(PAIR_INVALID)
    if not isinstance(value, dict):
        _fail(PAIR_INVALID)
    return value


def _closed_directory(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        _fail()
    try:
        resolved = path.resolve(strict=True)
        value = os.lstat(resolved)
    except OSError:
        _fail()
    if (
        os.path.normcase(str(resolved)) != os.path.normcase(str(path))
        or not stat.S_ISDIR(value.st_mode)
        or stat.S_ISLNK(value.st_mode)
        or bool(
            getattr(value, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
    ):
        _fail()
    return resolved


class _GUID(ctypes.Structure):
    _fields_ = (
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    )

    @classmethod
    def parse(cls, value: str) -> "_GUID":
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


def _windows_local_app_data_path() -> Path:
    """Resolve LocalAppData through the Windows known-folder API, not env."""

    if os.name != "nt":
        _fail()
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = (
        ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    folder = _GUID.parse("f1b32785-6fba-4fcf-9d55-7b8e7f157091")
    value = wintypes.LPWSTR()
    if shell32.SHGetKnownFolderPath(ctypes.byref(folder), 0, None, ctypes.byref(value)) != 0:
        _fail()
    try:
        if not value.value:
            _fail()
        return _closed_directory(Path(value.value))
    finally:
        ole32.CoTaskMemFree(value)


def resolve_codex_payload() -> PinnedExecutable:
    """Select the one governed Codex payload by known-folder root and bytes."""

    root = _closed_directory(
        _windows_local_app_data_path() / "OpenAI" / "Codex" / "bin"
    )
    matches: list[PinnedExecutable] = []
    try:
        children = tuple(sorted(root.iterdir(), key=lambda item: item.name))
    except OSError:
        _fail()
    for child in children:
        try:
            directory = _closed_directory(child)
        except RunnerGateError:
            raise
        if _PAYLOAD_DIRECTORY_NAME.fullmatch(directory.name) is None:
            continue
        candidate = directory / "codex.exe"
        if not candidate.exists():
            continue
        try:
            pinned = PinnedExecutable.capture(candidate)
        except Exception:
            _fail()
        if (
            pinned.byte_length == CODEX_PAYLOAD_BYTE_LENGTH
            and pinned.sha256 == CODEX_PAYLOAD_SHA256
        ):
            matches.append(pinned)
    if len(matches) != 1:
        _fail()
    return matches[0]


@dataclass(frozen=True)
class SandboxGenerationFingerprint:
    offline_sid: str
    online_sid: str
    offline_password_last_set_utc: str
    online_password_last_set_utc: str
    sandbox_users_json_byte_length: int
    sandbox_users_json_sha256: str
    value: str

    @classmethod
    def create(
        cls,
        *,
        offline_sid: str,
        online_sid: str,
        offline_password_last_set_utc: str,
        online_password_last_set_utc: str,
        sandbox_users_json_byte_length: int,
        sandbox_users_json_sha256: str,
    ) -> "SandboxGenerationFingerprint":
        material = {
            "offline_password_last_set_utc": offline_password_last_set_utc,
            "offline_sid": offline_sid,
            "online_password_last_set_utc": online_password_last_set_utc,
            "online_sid": online_sid,
            "sandbox_users_json_byte_length": sandbox_users_json_byte_length,
            "sandbox_users_json_sha256": sandbox_users_json_sha256,
            "schema": SANDBOX_GENERATION_SCHEMA,
        }
        result = cls(
            offline_sid,
            online_sid,
            offline_password_last_set_utc,
            online_password_last_set_utc,
            sandbox_users_json_byte_length,
            sandbox_users_json_sha256,
            SANDBOX_GENERATION_PREFIX + _sha256(_canonical_json(material)),
        )
        result.validate()
        return result

    def validate(self) -> None:
        if (
            not isinstance(self.offline_sid, str)
            or _SID.fullmatch(self.offline_sid) is None
            or not isinstance(self.online_sid, str)
            or _SID.fullmatch(self.online_sid) is None
            or self.offline_sid == self.online_sid
            or not isinstance(self.offline_password_last_set_utc, str)
            or _PASSWORD_LAST_SET_UTC.fullmatch(self.offline_password_last_set_utc) is None
            or not isinstance(self.online_password_last_set_utc, str)
            or _PASSWORD_LAST_SET_UTC.fullmatch(self.online_password_last_set_utc) is None
            or type(self.sandbox_users_json_byte_length) is not int
            or not 0 < self.sandbox_users_json_byte_length <= MAX_SANDBOX_USERS_JSON_BYTES
            or not isinstance(self.sandbox_users_json_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.sandbox_users_json_sha256) is None
        ):
            _fail()
        material = {
            "offline_password_last_set_utc": self.offline_password_last_set_utc,
            "offline_sid": self.offline_sid,
            "online_password_last_set_utc": self.online_password_last_set_utc,
            "online_sid": self.online_sid,
            "sandbox_users_json_byte_length": self.sandbox_users_json_byte_length,
            "sandbox_users_json_sha256": self.sandbox_users_json_sha256,
            "schema": SANDBOX_GENERATION_SCHEMA,
        }
        expected = SANDBOX_GENERATION_PREFIX + _sha256(_canonical_json(material))
        if self.value != expected:
            _fail()


SandboxGenerationProbe = Callable[[], SandboxGenerationFingerprint]


def _sandbox_users_json_identity(codex_home: Path) -> tuple[int, str]:
    root = _closed_directory(codex_home)
    matches: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = tuple(directory.iterdir())
        except OSError:
            _fail()
        for child in children:
            try:
                value = os.lstat(child)
            except OSError:
                _fail()
            if (
                stat.S_ISLNK(value.st_mode)
                or bool(
                    getattr(value, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                )
            ):
                _fail()
            if stat.S_ISDIR(value.st_mode):
                pending.append(child)
            elif stat.S_ISREG(value.st_mode) and child.name == "sandbox_users.json":
                matches.append(child)
            elif not stat.S_ISREG(value.st_mode):
                _fail()
    if len(matches) != 1:
        _fail()
    try:
        payload = matches[0].read_bytes()
    except OSError:
        _fail()
    if not payload or len(payload) > MAX_SANDBOX_USERS_JSON_BYTES:
        _fail()
    return len(payload), _sha256(payload)


_SANDBOX_ACCOUNT_QUERY = (
    "$ErrorActionPreference='Stop';"
    f"Import-Module -Name '{LOCAL_ACCOUNTS_MODULE_PATH}' -Force -ErrorAction Stop;"
    "$offline=Microsoft.PowerShell.LocalAccounts\\Get-LocalUser "
    "-Name 'CodexSandboxOffline' -ErrorAction Stop;"
    "$online=Microsoft.PowerShell.LocalAccounts\\Get-LocalUser "
    "-Name 'CodexSandboxOnline' -ErrorAction Stop;"
    "if($null -eq $offline.PasswordLastSet -or $null -eq $online.PasswordLastSet)"
    "{throw 'PASSWORD_LAST_SET_UNAVAILABLE'};"
    "[ordered]@{offline_sid=$offline.SID.Value;online_sid=$online.SID.Value;"
    "offline_password_last_set_utc=$offline.PasswordLastSet.ToUniversalTime().ToString('o');"
    "online_password_last_set_utc=$online.PasswordLastSet.ToUniversalTime().ToString('o')}"
    "|ConvertTo-Json -Compress"
)


def capture_sandbox_generation(
    *, codex_home: Path, temp_root: Path
) -> SandboxGenerationFingerprint:
    """Measure the generation-sensitive pre-ID state without reading secrets."""

    try:
        powershell = PinnedExecutable.capture(WINDOWS_POWERSHELL_PATH)
        module = PinnedExecutable.capture(LOCAL_ACCOUNTS_MODULE_PATH)
    except Exception:
        _fail()
    if (
        powershell.byte_length != WINDOWS_POWERSHELL_BYTE_LENGTH
        or powershell.sha256 != WINDOWS_POWERSHELL_SHA256
        or module.byte_length != LOCAL_ACCOUNTS_MODULE_BYTE_LENGTH
        or module.sha256 != LOCAL_ACCOUNTS_MODULE_SHA256
    ):
        _fail()
    powershell.verify()
    module.verify()
    result = _run_contained_once(
        (
            str(powershell.path), "-NoLogo", "-NoProfile", "-NonInteractive",
            "-Command", _SANDBOX_ACCOUNT_QUERY,
        ),
        input_bytes=b"",
        cwd=_closed_directory(codex_home),
        env=launcher_environment(codex_home, temp_root),
        timeout_seconds=30,
    )
    powershell.verify()
    module.verify()
    if (
        result.returncode != 0
        or result.timed_out
        or result.tree_terminated is not True
        or not result.stdout
        or len(result.stdout) > 8192
        or result.stderr != b""
    ):
        _fail()
    try:
        projection = _json_object(result.stdout)
    except RunnerGateError:
        _fail()
    expected_keys = {
        "offline_sid", "online_sid", "offline_password_last_set_utc",
        "online_password_last_set_utc",
    }
    if not isinstance(projection, dict) or set(projection) != expected_keys:
        _fail()
    marker_length, marker_sha256 = _sandbox_users_json_identity(codex_home)
    try:
        return SandboxGenerationFingerprint.create(
            offline_sid=projection["offline_sid"],
            online_sid=projection["online_sid"],
            offline_password_last_set_utc=projection["offline_password_last_set_utc"],
            online_password_last_set_utc=projection["online_password_last_set_utc"],
            sandbox_users_json_byte_length=marker_length,
            sandbox_users_json_sha256=marker_sha256,
        )
    except (KeyError, TypeError):
        _fail()


def validate_sandbox_binding(
    principal: str,
    generation: str,
    observed: SandboxGenerationFingerprint,
) -> None:
    observed.validate()
    validate_sandbox_binding_value(principal, generation)
    if principal != observed.offline_sid or generation != observed.value:
        _fail()


def validate_sandbox_binding_value(principal: str, generation: str) -> None:
    if (
        not isinstance(principal, str)
        or _SID.fullmatch(principal) is None
        or not isinstance(generation, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", generation) is None
    ):
        _fail()


@dataclass(frozen=True, order=True)
class ToolDescriptor:
    """One allowed top-level Codex JSONL ``item.type``."""

    name: str
    approval_required: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or not self.name.isascii()
            or any(ord(character) < 33 for character in self.name)
            or self.name in _PASSIVE_ITEM_TYPES
            or type(self.approval_required) is not bool
        ):
            _fail(PAIR_INVALID)


@dataclass(frozen=True)
class ToolCatalog:
    tools: tuple[ToolDescriptor, ...]
    catalog_sha256: str

    @classmethod
    def project(cls, tools: Sequence[ToolDescriptor]) -> "ToolCatalog":
        if isinstance(tools, (str, bytes, bytearray)):
            _fail(PAIR_INVALID)
        ordered = tuple(sorted(tools))
        if not ordered or len({tool.name for tool in ordered}) != len(ordered):
            _fail(PAIR_INVALID)
        projection = [
            {"approval_required": tool.approval_required, "name": tool.name}
            for tool in ordered
        ]
        return cls(ordered, _sha256(_canonical_json(projection)))

    @classmethod
    def observed(
        cls, inventory: Sequence[Mapping[str, object]], catalog_sha256: str
    ) -> "ToolCatalog":
        try:
            if any(set(item) != {"name", "approval_required"} for item in inventory):
                _fail(PAIR_INVALID)
            tools = tuple(
                ToolDescriptor(
                    name=item["name"],
                    approval_required=item["approval_required"],
                )
                for item in inventory
            )
        except (KeyError, TypeError):
            _fail(PAIR_INVALID)
        projected = cls.project(tools)
        if catalog_sha256 != projected.catalog_sha256:
            _fail(PAIR_INVALID)
        return projected

    def public_inventory(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {"name": tool.name, "approval_required": tool.approval_required}
            for tool in self.tools
        )

    def admits(self, observed: Sequence[str]) -> bool:
        return set(observed) <= {tool.name for tool in self.tools}


@dataclass(frozen=True)
class RuntimeIdentity:
    model_selector: str
    reasoning_effort: str
    runtime_model_build: str
    codex_client_identity: str
    host_identity: str
    identity_disposition: str

    def validate(self) -> None:
        if (
            self.model_selector != MODEL_SELECTOR
            or self.reasoning_effort != REASONING_EFFORT
            or self.identity_disposition != IDENTITY_DISPOSITION
        ):
            _fail(PAIR_INVALID)
        if any(
            not isinstance(value, str) or not value
            for value in (
                self.runtime_model_build,
                self.codex_client_identity,
                self.host_identity,
            )
        ):
            _fail()

    def equality_projection(self) -> tuple[str, str, str]:
        self.validate()
        return (
            self.runtime_model_build,
            self.codex_client_identity,
            self.host_identity,
        )


@dataclass(frozen=True)
class ExecutionPolicy:
    max_elapsed_seconds: int
    max_tool_calls: int
    retry_limit: int
    approval_mode: str
    network_mode: str
    cache_control: str
    fresh_context_required: bool
    tool_call_cap_enforcement: str
    hard_pre_dispatch_cap: str

    def validate(self) -> None:
        if self != REQUIRED_EXECUTION_POLICY:
            _fail(PAIR_INVALID)


REQUIRED_EXECUTION_POLICY = ExecutionPolicy(
    max_elapsed_seconds=MAX_ELAPSED_SECONDS,
    max_tool_calls=MAX_TOOL_CALLS,
    retry_limit=0,
    approval_mode="CODEX_NATIVE_NEVER",
    network_mode="CODEX_NATIVE_SANDBOX_OFFLINE",
    cache_control="UNAVAILABLE",
    fresh_context_required=True,
    tool_call_cap_enforcement=TOOL_CALL_CAP_ENFORCEMENT,
    hard_pre_dispatch_cap=HARD_PRE_DISPATCH_CAP,
)


@dataclass(frozen=True)
class CanaryObservation:
    context_id: str
    workspace_id: str
    runtime_identity: RuntimeIdentity
    execution_policy: ExecutionPolicy
    configured_tool_inventory: tuple[Mapping[str, object], ...]
    catalog_sha256: str
    credential_sentinel_visible: bool
    network_tcp_egress_denied: bool
    host_local: HostLocalIsolation
    sandbox_principal: str
    sandbox_account_generation: str


@dataclass(frozen=True)
class CanaryQualification:
    context_id: str
    workspace_id: str
    runtime_identity: RuntimeIdentity
    execution_policy: ExecutionPolicy
    catalog: ToolCatalog
    sandbox_principal: str
    sandbox_account_generation: str
    host_local: HostLocalIsolation


@dataclass(frozen=True)
class ArmPreparationObservation:
    arm_ordinal: int
    context_id: str
    workspace_id: str
    runtime_identity: RuntimeIdentity
    execution_policy: ExecutionPolicy
    configured_tool_inventory: tuple[Mapping[str, object], ...]
    catalog_sha256: str
    task_exposure_state: str
    sandbox_principal: str
    sandbox_account_generation: str
    credential_sentinel_visible: bool
    host_local: HostLocalIsolation


@dataclass(frozen=True)
class PreparedArm:
    arm_ordinal: int
    context_id: str
    workspace_id: str
    runtime_identity: RuntimeIdentity
    execution_policy: ExecutionPolicy
    configured_tool_inventory: tuple[Mapping[str, object], ...]
    catalog_sha256: str
    sandbox_principal: str
    sandbox_account_generation: str
    host_local: HostLocalIsolation
    task_exposure_state: str = "NONE"


class PreExposureObservationBackend(Protocol):
    """Pre-ID observation boundary; it makes no cap-enforcement claim."""

    def run_canary(
        self,
        *,
        executable: PinnedExecutable,
        expected_catalog: ToolCatalog,
        launcher_environment: Mapping[str, str],
        model_tool_environment: Mapping[str, str],
    ) -> CanaryObservation: ...

    def prepare_arm(
        self,
        *,
        arm_ordinal: int,
        executable: PinnedExecutable,
        expected_catalog: ToolCatalog,
        launcher_environment: Mapping[str, str],
        model_tool_environment: Mapping[str, str],
    ) -> ArmPreparationObservation: ...


def launcher_environment(codex_home: Path, temp_root: Path) -> dict[str, str]:
    """Closed environment for Codex; no discovery PATH is inherited."""

    if not codex_home.is_absolute() or not temp_root.is_absolute():
        _fail()
    env = {
        "CODEX_HOME": str(codex_home),
        "NO_COLOR": "1",
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
    }
    for key in ("COMSPEC", "SYSTEMROOT", "WINDIR"):
        if key in os.environ and os.environ[key]:
            env[key] = os.environ[key]
    return env


def model_tool_environment(temp_root: Path) -> dict[str, str]:
    """Expected model-tool environment measured by the sandbox canary."""

    if not temp_root.is_absolute():
        _fail()
    env = {"NO_COLOR": "1", "TEMP": str(temp_root), "TMP": str(temp_root)}
    for key in ("COMSPEC", "SYSTEMROOT", "WINDIR"):
        if key in os.environ and os.environ[key]:
            env[key] = os.environ[key]
    forbidden = {"CODEX_HOME", "HOME", "USERPROFILE", "PATH", "PATHEXT"}
    if forbidden & set(env):
        _fail()
    return env


_T = TypeVar("_T")


class ToolCallGate:
    """Reference specification only; production Codex does not install it."""

    enforcement_disposition = "SPECIFIED_NOT_INSTALLED"

    def __init__(self, catalog: ToolCatalog) -> None:
        self.catalog = catalog
        self.calls = 0

    def invoke(self, name: str, effect: Callable[[], _T]) -> _T:
        descriptor = next((tool for tool in self.catalog.tools if tool.name == name), None)
        if descriptor is None:
            _fail(PAIR_INVALID)
        if self.calls >= MAX_TOOL_CALLS:
            raise RunnerGateError(TOOL_CALL_LIMIT_REACHED)
        self.calls += 1
        if descriptor.approval_required:
            raise RunnerGateError(APPROVAL_REQUIRED_DENIED)
        return effect()


class CodexRunnerAdapter:
    """Qualify a canary, then prepare fresh unexposed formal arm contexts."""

    def __init__(
        self,
        *,
        executable: PinnedExecutable,
        backend: PreExposureObservationBackend,
        expected_catalog: ToolCatalog,
        codex_home: Path,
        temp_root: Path,
        sandbox_generation_probe: SandboxGenerationProbe | None = None,
    ) -> None:
        self.executable = executable
        self.backend = backend
        self.expected_catalog = expected_catalog
        self._launcher_env = launcher_environment(codex_home, temp_root)
        self._tool_env = model_tool_environment(temp_root)
        self._sandbox_generation_probe = sandbox_generation_probe or (
            lambda: capture_sandbox_generation(
                codex_home=codex_home, temp_root=temp_root
            )
        )
        self._canary: CanaryQualification | None = None
        self._prepared_ordinals: set[int] = set()

    def _generation(self) -> SandboxGenerationFingerprint:
        try:
            observed = self._sandbox_generation_probe()
            observed.validate()
        except Exception:
            _fail()
        return observed

    def qualify_canary(self) -> CanaryQualification:
        if self._canary is not None:
            _fail()
        self.executable.verify()
        generation_before = self._generation()
        observed = self.backend.run_canary(
            executable=self.executable,
            expected_catalog=self.expected_catalog,
            launcher_environment=dict(self._launcher_env),
            model_tool_environment=dict(self._tool_env),
        )
        generation_after = self._generation()
        if generation_after != generation_before:
            _fail()
        catalog = ToolCatalog.observed(
            observed.configured_tool_inventory, observed.catalog_sha256
        )
        observed.runtime_identity.validate()
        observed.execution_policy.validate()
        observed.host_local.validate()
        if (
            catalog != self.expected_catalog
            or observed.credential_sentinel_visible is not False
            or observed.network_tcp_egress_denied is not True
            or not observed.context_id
            or not observed.workspace_id
        ):
            _fail(PAIR_INVALID)
        validate_sandbox_binding(
            observed.sandbox_principal,
            observed.sandbox_account_generation,
            generation_before,
        )
        self._canary = CanaryQualification(
            observed.context_id,
            observed.workspace_id,
            observed.runtime_identity,
            observed.execution_policy,
            catalog,
            observed.sandbox_principal,
            observed.sandbox_account_generation,
            observed.host_local,
        )
        return self._canary

    def prepare_formal_arm(self, arm_ordinal: int) -> PreparedArm:
        if (
            self._canary is None
            or arm_ordinal not in {1, 2}
            or arm_ordinal in self._prepared_ordinals
        ):
            _fail()
        self.executable.verify()
        generation_before = self._generation()
        if generation_before.value != self._canary.sandbox_account_generation:
            _fail()
        observed = self.backend.prepare_arm(
            arm_ordinal=arm_ordinal,
            executable=self.executable,
            expected_catalog=self.expected_catalog,
            launcher_environment=dict(self._launcher_env),
            model_tool_environment=dict(self._tool_env),
        )
        generation_after = self._generation()
        if generation_after != generation_before:
            _fail()
        catalog = ToolCatalog.observed(
            observed.configured_tool_inventory, observed.catalog_sha256
        )
        observed.runtime_identity.validate()
        observed.execution_policy.validate()
        observed.host_local.validate()
        if (
            observed.arm_ordinal != arm_ordinal
            or catalog != self.expected_catalog
            or observed.task_exposure_state != "NONE"
            or observed.credential_sentinel_visible is not False
            or not observed.context_id
            or not observed.workspace_id
            or observed.context_id == self._canary.context_id
            or observed.workspace_id == self._canary.workspace_id
        ):
            _fail(PAIR_INVALID)
        validate_sandbox_binding(
            observed.sandbox_principal,
            observed.sandbox_account_generation,
            generation_before,
        )
        self._prepared_ordinals.add(arm_ordinal)
        return PreparedArm(
            arm_ordinal,
            observed.context_id,
            observed.workspace_id,
            observed.runtime_identity,
            observed.execution_policy,
            observed.configured_tool_inventory,
            observed.catalog_sha256,
            observed.sandbox_principal,
            observed.sandbox_account_generation,
            observed.host_local,
        )


@dataclass(frozen=True)
class TraceMetrics:
    trace_sha256: str
    byte_length: int
    tool_call_count: int
    observed_tool_inventory: tuple[str, ...]
    terminal_event: str


def derive_trace_metrics(trace: bytes) -> TraceMetrics:
    """Strictly derive tool use from one complete authoritative JSONL trace."""

    if (
        not isinstance(trace, bytes)
        or not trace
        or len(trace) > MAX_TRACE_BYTES
        or not trace.endswith(b"\n")
        or b"\r" in trace
    ):
        _fail(PAIR_INVALID)
    lines = trace.splitlines()
    if any(not line or len(line) > MAX_TRACE_LINE_BYTES for line in lines):
        _fail(PAIR_INVALID)
    events: list[dict[str, object]] = []
    for line in lines:
        try:
            value = json.loads(line, object_pairs_hook=_object_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail(PAIR_INVALID)
        if not isinstance(value, dict) or set(value).isdisjoint({"type"}):
            _fail(PAIR_INVALID)
        event_type = value.get("type")
        if event_type not in _TOP_LEVEL_EVENTS:
            _fail(PAIR_INVALID)
        events.append(value)
    types = [event["type"] for event in events]
    completed_terminals = [
        item for item in types if item in {"turn.completed", "turn.failed"}
    ]
    if (
        types[0] != "thread.started"
        or types.count("thread.started") != 1
        or types.count("turn.started") != 1
        or types[1] != "turn.started"
        or types[-1] not in {"turn.completed", "turn.failed", "error"}
        or len(completed_terminals) > 1
        or (completed_terminals and types[-1] != completed_terminals[0])
    ):
        _fail(PAIR_INVALID)

    started: set[str] = set()
    tool_types: list[str] = []
    for event in events:
        if event["type"] != "item.started":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            _fail(PAIR_INVALID)
        item_type = item.get("type")
        if not isinstance(item_type, str) or not item_type:
            _fail(PAIR_INVALID)
        if item_type in _PASSIVE_ITEM_TYPES:
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in started:
            _fail(PAIR_INVALID)
        started.add(item_id)
        tool_types.append(item_type)
    return TraceMetrics(
        trace_sha256=_sha256(trace),
        byte_length=len(trace),
        tool_call_count=len(tool_types),
        observed_tool_inventory=tuple(sorted(set(tool_types))),
        terminal_event=str(types[-1]),
    )


@dataclass(frozen=True, repr=False)
class ProcessResult:
    returncode: int
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)
    timed_out: bool
    tree_terminated: bool


@dataclass(frozen=True)
class LauncherProcessIdentity:
    principal: str
    principal_sid: str
    integrity: str
    elevated: bool

    def validate(self, expected_principal_sid: str) -> None:
        _principal_leaf(self.principal)
        if (
            not isinstance(expected_principal_sid, str)
            or _SID.fullmatch(expected_principal_sid) is None
            or not isinstance(self.principal_sid, str)
            or _SID.fullmatch(self.principal_sid) is None
            or self.principal_sid != expected_principal_sid
            or self.integrity != "MEDIUM"
            or self.elevated is not False
        ):
            _fail(PAIR_INVALID)


def _principal_leaf(value: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(PAIR_INVALID)
    return value.replace("/", "\\").rsplit("\\", 1)[-1]


@dataclass(frozen=True, repr=False)
class NativeExecutionResult:
    trace_path: Path
    schema_path: Path
    final_message_path: Path
    schema_sha256: str
    schema_byte_length: int
    trace_sha256: str
    trace_byte_length: int
    tool_call_count: int
    observed_tool_inventory: tuple[str, ...]
    terminal_event: str
    disposition: str
    returncode: int
    timed_out: bool
    tree_terminated: bool
    stderr_sha256: str
    stderr_byte_length: int
    final_message_sha256: str
    final_message_byte_length: int


class NativeCodexExecBackend:
    """Launch exactly one pinned native Codex process and retain its JSONL trace."""

    def __init__(
        self,
        *,
        executable: PinnedExecutable,
        configured_catalog: ToolCatalog,
        expected_launcher_sid: str,
        sandbox_generation_capture: Callable[..., SandboxGenerationFingerprint] | None = None,
    ) -> None:
        if (
            not isinstance(expected_launcher_sid, str)
            or _SID.fullmatch(expected_launcher_sid) is None
        ):
            _fail(PAIR_INVALID)
        self.executable = executable
        self.configured_catalog = configured_catalog
        self.expected_launcher_sid = expected_launcher_sid
        self._sandbox_generation_capture = (
            sandbox_generation_capture or capture_sandbox_generation
        )

    def _command(self, schema_path: Path, final_path: Path) -> tuple[str, ...]:
        executable = self.executable.verify()
        return (
            str(executable),
            "-c",
            f"model_reasoning_effort={REASONING_EFFORT}",
            "-c",
            'approval_policy="never"',
            "-c",
            'windows.sandbox="elevated"',
            "-c",
            "sandbox_workspace_write.network_access=false",
            "-c",
            'cli_auth_credentials_store="keyring"',
            "exec",
            "--ignore-user-config",
            "--strict-config",
            "--sandbox",
            "workspace-write",
            "--json",
            "--ephemeral",
            "--output-last-message",
            str(final_path),
            "--output-schema",
            str(schema_path),
            "--model",
            MODEL_SELECTOR,
            "-",
        )

    def execute(
        self,
        *,
        prepared_arm: PreparedArm,
        workspace_root: Path,
        codex_home: Path,
        output_root: Path,
        prompt: bytes,
        output_schema: Mapping[str, object],
    ) -> NativeExecutionResult:
        """Expose one task exactly once; callers own admission before this call."""

        if (
            prepared_arm.task_exposure_state != "NONE"
            or not isinstance(prompt, bytes)
            or not prompt
            or len(prompt) > MAX_PROMPT_BYTES
            or not isinstance(output_schema, Mapping)
        ):
            _fail(PAIR_INVALID)
        prepared_arm.runtime_identity.validate()
        prepared_arm.execution_policy.validate()
        catalog = ToolCatalog.observed(
            prepared_arm.configured_tool_inventory, prepared_arm.catalog_sha256
        )
        if catalog != self.configured_catalog:
            _fail(PAIR_INVALID)
        workspace = _closed_directory(workspace_root)
        home = _closed_directory(codex_home)
        output = _closed_directory(output_root)
        if any(output.iterdir()) or len({workspace, home, output}) != 3:
            _fail(PAIR_INVALID)
        identity = _windows_process_identity()
        identity.validate(self.expected_launcher_sid)
        try:
            generation = self._sandbox_generation_capture(
                codex_home=home, temp_root=output
            )
            generation.validate()
        except Exception:
            _fail()
        if any(output.iterdir()):
            _fail()
        validate_sandbox_binding(
            prepared_arm.sandbox_principal,
            prepared_arm.sandbox_account_generation,
            generation,
        )

        schema_path = output / "output-schema.json"
        final_path = output / "final-message.json"
        trace_path = output / "codex-trace.jsonl"
        try:
            schema_object = dict(output_schema)
            Draft202012Validator.check_schema(schema_object)
            schema_payload = _canonical_json(schema_object) + b"\n"
        except (SchemaError, TypeError, ValueError):
            _fail(PAIR_INVALID)
        try:
            with schema_path.open("xb") as stream:
                stream.write(schema_payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            _fail()
        command = self._command(schema_path, final_path)
        environment = launcher_environment(home, output)
        # This is the only production dispatch.  Retry is intentionally absent.
        result = _run_contained_once(
            command,
            input_bytes=prompt,
            cwd=workspace,
            env=environment,
            timeout_seconds=MAX_ELAPSED_SECONDS,
        )
        self.executable.verify()
        if (
            not isinstance(result, ProcessResult)
            or result.tree_terminated is not True
            or len(result.stdout) > MAX_TRACE_BYTES
            or len(result.stderr) > MAX_TRACE_BYTES
        ):
            _fail(PAIR_INVALID)
        try:
            with trace_path.open("xb") as stream:
                stream.write(result.stdout)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            _fail()
        metrics = derive_trace_metrics(result.stdout)
        if not catalog.admits(metrics.observed_tool_inventory):
            _fail(PAIR_INVALID)
        try:
            final_payload = final_path.read_bytes()
        except OSError:
            final_payload = b""
        final_message_valid = False
        if final_payload:
            try:
                final_object = _json_object(final_payload)
                Draft202012Validator(schema_object).validate(final_object)
                final_message_valid = True
            except (RunnerGateError, SchemaError, ValidationError):
                final_message_valid = False
        disposition = (
            SUCCESS
            if (
                metrics.tool_call_count <= MAX_TOOL_CALLS
                and not result.timed_out
                and result.returncode == 0
                and metrics.terminal_event == "turn.completed"
                and final_message_valid
            )
            else AGENT_FAILURE
        )
        return NativeExecutionResult(
            trace_path=trace_path,
            schema_path=schema_path,
            final_message_path=final_path,
            schema_sha256=_sha256(schema_payload),
            schema_byte_length=len(schema_payload),
            trace_sha256=metrics.trace_sha256,
            trace_byte_length=metrics.byte_length,
            tool_call_count=metrics.tool_call_count,
            observed_tool_inventory=metrics.observed_tool_inventory,
            terminal_event=metrics.terminal_event,
            disposition=disposition,
            returncode=result.returncode,
            timed_out=result.timed_out,
            tree_terminated=result.tree_terminated,
            stderr_sha256=_sha256(result.stderr),
            stderr_byte_length=len(result.stderr),
            final_message_sha256=_sha256(final_payload),
            final_message_byte_length=len(final_payload),
        )


def validate_execution_result(
    result: NativeExecutionResult, configured_catalog: ToolCatalog
) -> TraceMetrics:
    """Recompute every claimed post-hoc metric from the retained trace."""

    try:
        trace = result.trace_path.read_bytes()
        schema_payload = result.schema_path.read_bytes()
        final_payload = result.final_message_path.read_bytes()
    except OSError:
        _fail(PAIR_INVALID)
    metrics = derive_trace_metrics(trace)
    schema = _json_object(schema_payload)
    final_message_valid = False
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(_json_object(final_payload))
        final_message_valid = True
    except (RunnerGateError, SchemaError, ValidationError):
        final_message_valid = False
    expected_disposition = (
        SUCCESS
        if (
            metrics.tool_call_count <= MAX_TOOL_CALLS
            and not result.timed_out
            and result.returncode == 0
            and metrics.terminal_event == "turn.completed"
            and final_message_valid
        )
        else AGENT_FAILURE
    )
    if (
        not configured_catalog.admits(metrics.observed_tool_inventory)
        or metrics.trace_sha256 != result.trace_sha256
        or metrics.byte_length != result.trace_byte_length
        or metrics.tool_call_count != result.tool_call_count
        or metrics.observed_tool_inventory != result.observed_tool_inventory
        or metrics.terminal_event != result.terminal_event
        or expected_disposition != result.disposition
        or result.tree_terminated is not True
        or _sha256(schema_payload) != result.schema_sha256
        or len(schema_payload) != result.schema_byte_length
        or _sha256(final_payload) != result.final_message_sha256
        or len(final_payload) != result.final_message_byte_length
    ):
        _fail(PAIR_INVALID)
    return metrics


def _run_contained_once(
    command: Sequence[str],
    *,
    input_bytes: bytes,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> ProcessResult:
    """Run one process tree with no shell and kill descendants on return."""

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    actual_command = list(command)
    gate: Path | None = None
    if os.name == "nt":
        temp_root = _closed_directory(Path(env["TEMP"]))
        gate = temp_root / f".solo-r2-job-{uuid.uuid4().hex}"
        if gate.exists():
            _fail()
        python = PinnedExecutable.capture(Path(sys.executable).resolve()).verify()
        actual_command = [
            str(python), "-I", "-S", "-c", _WINDOWS_JOB_GUARD,
            str(gate), *actual_command,
        ]
    process = subprocess.Popen(
        actual_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=dict(env),
        shell=False,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    job: int | None = None
    if os.name == "nt":
        try:
            job = _assign_kill_on_close_job(process)
            assert gate is not None
            with gate.open("xb") as stream:
                stream.write(b"go\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            process.kill()
            process.wait()
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
    return ProcessResult(process.returncode, stdout, stderr, timed_out, tree_terminated)


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
        _fail()
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = 0x00002000
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        kernel32.CloseHandle(job)
        _fail()
    if not kernel32.AssignProcessToJobObject(job, int(process._handle)):
        kernel32.CloseHandle(job)
        _fail()
    return int(job)


def _terminate_job(job: int | None) -> None:
    if job is not None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject(job, 1)


def _close_job(job: int | None) -> None:
    if job is not None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle(job)


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


def _windows_process_identity() -> LauncherProcessIdentity:
    """Read the current Windows token; environment user names are not trusted."""

    if os.name != "nt":
        _fail()
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
    )
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.ConvertSidToStringSidW.argtypes = (
        ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)
    )
    advapi32.GetSidSubAuthorityCount.argtypes = (ctypes.c_void_p,)
    advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi32.GetSidSubAuthority.argtypes = (ctypes.c_void_p, wintypes.DWORD)
    advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
    advapi32.LookupAccountSidW.argtypes = (
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    )
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        _fail()
    try:
        def token_info(kind: int) -> ctypes.Array[ctypes.c_char]:
            needed = wintypes.DWORD()
            advapi32.GetTokenInformation(token, kind, None, 0, ctypes.byref(needed))
            if not needed.value:
                _fail()
            buffer = ctypes.create_string_buffer(needed.value)
            if not advapi32.GetTokenInformation(
                token, kind, buffer, needed.value, ctypes.byref(needed)
            ):
                _fail()
            return buffer

        class _SID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class _TOKEN_USER(ctypes.Structure):
            _fields_ = [("User", _SID_AND_ATTRIBUTES)]

        class _TOKEN_ELEVATION(ctypes.Structure):
            _fields_ = [("TokenIsElevated", wintypes.DWORD)]

        class _TOKEN_MANDATORY_LABEL(ctypes.Structure):
            _fields_ = [("Label", _SID_AND_ATTRIBUTES)]

        user_buffer = token_info(1)
        user = ctypes.cast(user_buffer, ctypes.POINTER(_TOKEN_USER)).contents
        elevation = ctypes.cast(
            token_info(20), ctypes.POINTER(_TOKEN_ELEVATION)
        ).contents.TokenIsElevated
        integrity_buffer = token_info(25)
        integrity_sid = ctypes.cast(
            integrity_buffer, ctypes.POINTER(_TOKEN_MANDATORY_LABEL)
        ).contents.Label.Sid
        count = advapi32.GetSidSubAuthorityCount(integrity_sid)
        if not count:
            _fail()
        subauthority_count = count.contents.value
        if subauthority_count == 0:
            _fail()
        rid_pointer = advapi32.GetSidSubAuthority(
            integrity_sid, subauthority_count - 1
        )
        if not rid_pointer:
            _fail()
        rid = rid_pointer.contents.value
        integrity = (
            "LOW" if rid < 0x2000 else
            "MEDIUM" if rid < 0x3000 else
            "HIGH" if rid < 0x4000 else "SYSTEM"
        )
        string_sid = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(user.User.Sid, ctypes.byref(string_sid)):
            _fail()
        try:
            principal_sid = string_sid.value
        finally:
            kernel32.LocalFree(string_sid)
        name_size = wintypes.DWORD()
        domain_size = wintypes.DWORD()
        sid_type = wintypes.DWORD()
        advapi32.LookupAccountSidW(
            None, user.User.Sid, None, ctypes.byref(name_size), None,
            ctypes.byref(domain_size), ctypes.byref(sid_type),
        )
        name = ctypes.create_unicode_buffer(name_size.value)
        domain = ctypes.create_unicode_buffer(domain_size.value)
        if not advapi32.LookupAccountSidW(
            None, user.User.Sid, name, ctypes.byref(name_size), domain,
            ctypes.byref(domain_size), ctypes.byref(sid_type),
        ):
            _fail()
        principal = f"{domain.value}\\{name.value}" if domain.value else name.value
        return LauncherProcessIdentity(principal, principal_sid, integrity, not not elevation)
    finally:
        kernel32.CloseHandle(token)
