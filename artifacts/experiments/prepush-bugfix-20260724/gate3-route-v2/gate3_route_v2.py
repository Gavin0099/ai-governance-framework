from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


AUTHORIZATION = "gate3_route_v2_synthetic_non_scoring_only"
LIVE_AUTHORIZATION = "gate3_route_v2_single_session_non_scoring_only"
AUTHORIZATIONS = frozenset({AUTHORIZATION, LIVE_AUTHORIZATION})
PREFLIGHT_SCHEMA = "gate3-route-v2.preflight.v2"
ACTION_SCHEMA = "gate3-route-v2.action.v3"
AB_ACTION_SCHEMA = "gate3-route-v2.action.v4"
ATTESTATION_SCHEMA = "gate3-route-v2.content-attestation.v1"
PACKET_SCHEMA = "gate3-route-v2.packet.v1"
AB_PACKET_SCHEMA = "gate3-route-v2.packet.v2"
INPUT_ATTESTATION_SCHEMA = "gate3-route-v2.input-attestation.v1"
SEAL_SCHEMA = "gate3-route-v2.observation-seal.v1"
FINAL_SCHEMA = "gate3-route-v2.final-receipt.v1"
EXTERNAL_SCHEMA = "gate3-route-v2.external-terminal.v2"
LOCATOR_SCHEMA = "gate3-route-v2.recovery-locator.v2"
RUN_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{7,79}", re.ASCII)
ARTIFACT_ID_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,79}", re.ASCII)
SHA256_RE = re.compile(r"[0-9a-f]{64}", re.ASCII)
TRUSTED_ROUTE_ROOT = Path(tempfile.gettempdir()) / "gate3-route-v2-runtime"
TERMINAL_STAGES = frozenset(
    {
        "final_publication_exhausted",
        "final_publication_failure",
        "action_publication_failure",
        "preflight_publication_failure",
        "locator_prelaunch_failure",
        "orphan_without_seal",
        "preseal_attestation_failure",
        "preseal_packet_failure",
        "preseal_private_acl_failure",
        "preseal_runner_failure",
        "preseal_seal_failure",
    }
)
LOCATOR_ABSENT_TERMINALS = frozenset(
    {
        "action_publication_failure",
        "preflight_publication_failure",
        "locator_prelaunch_failure",
    }
)


class RouteV2Error(RuntimeError):
    """Fail-closed synthetic route error."""


class PublicationError(RouteV2Error):
    """Create-once publication failed."""


class PublicPrivacyError(RouteV2Error):
    """A proposed public artifact crossed the closed privacy boundary."""


class SyntheticCrash(BaseException):
    """Test-only process interruption that intentionally bypasses closeout."""


@dataclass(frozen=True)
class SyntheticResult:
    exit_code: int
    stdout: bytes | None
    final_message: bytes | None
    workspace: Mapping[str, bytes] | None
    exit_classification: str | None = None
    stdout_capture: str | None = None
    final_capture: str | None = None
    workspace_capture: str | None = None


@dataclass(frozen=True)
class FaultPlan:
    publication_failures: frozenset[str] = field(default_factory=frozenset)
    privacy_failures: frozenset[str] = field(default_factory=frozenset)
    crash_after: str | None = None
    cleanup_failures: int = 0
    locator_removal_failures: int = 0


@dataclass(frozen=True)
class RouteResult:
    output_root: Path
    locator: Path
    final_receipt: Path | None
    external_terminal: Path | None
    decision: str


_LIVE_RUNNER_TOKEN = object()


class TrustedLiveRunner:
    """Non-subclassable capability assembled only after a measured preflight."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TrustedLiveRunner cannot be subclassed")

    def __init__(
        self,
        *,
        _token: object,
        execution_identity: Mapping[str, str],
        preflight: bytes,
        invoke: Callable[[], SyntheticResult],
    ) -> None:
        if _token is not _LIVE_RUNNER_TOKEN:
            raise RouteV2Error("trusted live runner capability is invalid")
        self._execution_identity = _validate_execution_identity(execution_identity)
        self._preflight = preflight
        self._invoke = invoke

    def execution_identity(self) -> Mapping[str, str]:
        return dict(self._execution_identity)

    def preflight_bytes(self) -> bytes:
        return self._preflight

    def __call__(self) -> SyntheticResult:
        return self._invoke()


def _trusted_live_runner(
    *,
    execution_identity: Mapping[str, str],
    preflight: bytes,
    invoke: Callable[[], SyntheticResult],
) -> TrustedLiveRunner:
    owner = getattr(invoke, "__self__", None)
    owner_type = type(owner)
    module = sys.modules.get("gate3_route_v2_codex")
    canonical_type = getattr(module, "CodexExecRunner", None)
    canonical_invoke = getattr(module, "_TRUSTED_CODEX_INVOKE", None)
    if (
        owner is None
        or owner_type is not canonical_type
        or getattr(invoke, "__func__", None) is not canonical_invoke
    ):
        raise RouteV2Error("trusted live runner provenance is invalid")
    module_path = Path(str(getattr(module, "__file__", "")))
    identity = _validate_execution_identity(execution_identity)
    if (
        not module_path.is_file()
        or _sha256_file(module_path) != identity["runner_sha256"]
        or owner.execution_identity() != identity
        or owner.preflight_bytes() != preflight
    ):
        raise RouteV2Error("trusted live runner provenance is invalid")
    return TrustedLiveRunner(
        _token=_LIVE_RUNNER_TOKEN,
        execution_identity=identity,
        preflight=preflight,
        invoke=invoke,
    )


_AB_RUNNER_TOKEN = object()


class TrustedABArmRunner:
    """Synthetic A/B capability that stages and attests before one invocation."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TrustedABArmRunner cannot be subclassed")

    def __init__(
        self,
        *,
        _token: object,
        execution_identity: Mapping[str, str],
        prepare: Callable[[Path, bytes], bytes],
        invoke: Callable[[], SyntheticResult],
    ) -> None:
        if _token is not _AB_RUNNER_TOKEN:
            raise RouteV2Error("trusted A/B runner capability is invalid")
        self._execution_identity = _validate_execution_identity(execution_identity)
        self._prepare = prepare
        self._invoke = invoke

    def prepare(self, private_root: Path, action_payload: bytes) -> bytes:
        return self._prepare(private_root, action_payload)

    def execution_identity(self) -> Mapping[str, str]:
        return dict(self._execution_identity)

    def __call__(self) -> SyntheticResult:
        return self._invoke()


def _trusted_ab_arm_runner(
    *,
    execution_identity: Mapping[str, str],
    prepare: Callable[[Path, bytes], bytes],
    invoke: Callable[[], SyntheticResult],
) -> TrustedABArmRunner:
    prepare_owner = getattr(prepare, "__self__", None)
    invoke_owner = getattr(invoke, "__self__", None)
    module = sys.modules.get("gate3_route_v2_ab")
    canonical_type = getattr(module, "SyntheticABArmRunner", None)
    identity = _validate_execution_identity(execution_identity)
    module_path = Path(str(getattr(module, "__file__", "")))
    if (
        prepare_owner is None
        or prepare_owner is not invoke_owner
        or type(prepare_owner) is not canonical_type
        or getattr(prepare, "__func__", None)
        is not getattr(module, "_TRUSTED_AB_PREPARE", None)
        or getattr(invoke, "__func__", None)
        is not getattr(module, "_TRUSTED_AB_INVOKE", None)
        or not module_path.is_file()
        or _sha256_file(module_path) != identity["runner_sha256"]
        or prepare_owner.execution_identity() != identity
    ):
        raise RouteV2Error("trusted A/B runner provenance is invalid")
    return TrustedABArmRunner(
        _token=_AB_RUNNER_TOKEN,
        execution_identity=identity,
        prepare=prepare,
        invoke=invoke,
    )


Publisher = Callable[[Path, bytes], None]
AclProtector = Callable[[Path, bool], None]
Cleaner = Callable[[Path], bool]
LocatorRemover = Callable[[Path], None]
Runner = Callable[[], SyntheticResult]


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _implementation_sha256() -> str:
    return _sha256_file(Path(__file__))


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteV2Error(f"invalid JSON artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise RouteV2Error(f"JSON artifact is not an object: {path.name}")
    if path.read_bytes() != _json_bytes(value):
        raise RouteV2Error(f"JSON artifact is not canonical: {path.name}")
    return value


def _publish_create_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise PublicationError(f"create-once target exists: {path.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise PublicationError(f"create-once target exists: {path.name}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _validate_public_payload(payload: bytes) -> None:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicPrivacyError("public artifact is not canonical JSON") from exc
    if not isinstance(value, dict) or payload != _json_bytes(value):
        raise PublicPrivacyError("public artifact is not canonical JSON")

    forbidden = (
        re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\[?.\\]?\\|\\\\[^\\]+\\[^\\]+)"),
        re.compile(r"(?i)(?:/home/|/users/|\\users\\|appdata[\\/])"),
        re.compile(r"(?i)(?:sk-[a-z0-9_-]{8,}|bearer\s+[a-z0-9._-]{8,})"),
    )

    def walk(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or any(ord(char) < 0x20 for char in key):
                    raise PublicPrivacyError("public artifact key is invalid")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            if any(pattern.search(item) for pattern in forbidden):
                raise PublicPrivacyError("public artifact contains a private surface")

    walk(value)


def _current_user_only(path: Path, container: bool) -> None:
    if os.name != "nt":
        os.chmod(path, 0o700 if container else 0o600)
        observed = stat.S_IMODE(path.stat().st_mode)
        if observed & 0o077:
            raise RouteV2Error("current-user-only ACL verification failed")
        return

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    token = ctypes.c_void_p()
    sid_text = ctypes.c_wchar_p()
    descriptor = ctypes.c_void_p()
    rendered = ctypes.c_wchar_p()
    try:
        advapi32.OpenProcessToken.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        advapi32.OpenProcessToken.restype = ctypes.c_int
        advapi32.GetTokenInformation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.GetTokenInformation.restype = ctypes.c_int
        advapi32.ConvertSidToStringSidW.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        advapi32.ConvertSidToStringSidW.restype = ctypes.c_int
        advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = (
            ctypes.c_int
        )
        advapi32.SetFileSecurityW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        advapi32.SetFileSecurityW.restype = ctypes.c_int
        advapi32.GetFileSecurityW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.GetFileSecurityW.restype = ctypes.c_int
        advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_wchar_p),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = (
            ctypes.c_int
        )
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
        ):
            raise OSError(ctypes.get_last_error())
        required = ctypes.c_uint32()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        token_buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, token_buffer, required.value, ctypes.byref(required)
        ):
            raise OSError(ctypes.get_last_error())
        sid_pointer = ctypes.cast(token_buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(sid_text)):
            raise OSError(ctypes.get_last_error())
        inheritance = "OICI" if container else ""
        expected_ace = f"(A;{inheritance};FA;;;{sid_text.value})"
        sddl = f"D:P{expected_ace}"
        descriptor_size = ctypes.c_uint32()
        if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)
        ):
            raise OSError(ctypes.get_last_error())
        if not advapi32.SetFileSecurityW(
            str(path), 0x00000004 | 0x80000000, descriptor
        ):
            raise OSError(ctypes.get_last_error())
        observed_size = ctypes.c_uint32()
        advapi32.GetFileSecurityW(
            str(path), 0x00000004, None, 0, ctypes.byref(observed_size)
        )
        observed = ctypes.create_string_buffer(observed_size.value)
        if not advapi32.GetFileSecurityW(
            str(path),
            0x00000004,
            observed,
            observed_size.value,
            ctypes.byref(observed_size),
        ):
            raise OSError(ctypes.get_last_error())
        rendered_size = ctypes.c_uint32()
        if not advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            observed,
            1,
            0x00000004,
            ctypes.byref(rendered),
            ctypes.byref(rendered_size),
        ):
            raise OSError(ctypes.get_last_error())
        observed_sddl = rendered.value or ""
        if (
            not observed_sddl.startswith("D:P")
            or observed_sddl.count("(") != 1
            or expected_ace not in observed_sddl
        ):
            raise RouteV2Error("current-user-only ACL verification failed")
    except (OSError, ValueError) as exc:
        raise RouteV2Error("current-user-only ACL verification failed") from exc
    finally:
        if token.value:
            kernel32.CloseHandle(token)
        if sid_text:
            kernel32.LocalFree(sid_text)
        if descriptor.value:
            kernel32.LocalFree(descriptor)
        if rendered:
            kernel32.LocalFree(rendered)


def _verify_current_user_only(path: Path, container: bool) -> None:
    if os.name != "nt":
        observed = stat.S_IMODE(path.stat().st_mode)
        if observed & 0o077:
            raise RouteV2Error("current-user-only ACL verification failed")
        return

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    token = ctypes.c_void_p()
    sid_text = ctypes.c_wchar_p()
    rendered = ctypes.c_wchar_p()
    try:
        advapi32.OpenProcessToken.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        advapi32.OpenProcessToken.restype = ctypes.c_int
        advapi32.GetTokenInformation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.GetTokenInformation.restype = ctypes.c_int
        advapi32.ConvertSidToStringSidW.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        advapi32.ConvertSidToStringSidW.restype = ctypes.c_int
        advapi32.GetFileSecurityW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.GetFileSecurityW.restype = ctypes.c_int
        advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_wchar_p),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = (
            ctypes.c_int
        )
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
        ):
            raise OSError(ctypes.get_last_error())
        required = ctypes.c_uint32()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
        token_buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, token_buffer, required.value, ctypes.byref(required)
        ):
            raise OSError(ctypes.get_last_error())
        sid_pointer = ctypes.cast(token_buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(sid_text)):
            raise OSError(ctypes.get_last_error())
        inheritance = "OICI" if container else ""
        expected_ace = f"(A;{inheritance};FA;;;{sid_text.value})"
        observed_size = ctypes.c_uint32()
        advapi32.GetFileSecurityW(
            str(path), 0x00000004, None, 0, ctypes.byref(observed_size)
        )
        observed = ctypes.create_string_buffer(observed_size.value)
        if not advapi32.GetFileSecurityW(
            str(path),
            0x00000004,
            observed,
            observed_size.value,
            ctypes.byref(observed_size),
        ):
            raise OSError(ctypes.get_last_error())
        rendered_size = ctypes.c_uint32()
        if not advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            observed,
            1,
            0x00000004,
            ctypes.byref(rendered),
            ctypes.byref(rendered_size),
        ):
            raise OSError(ctypes.get_last_error())
        observed_sddl = rendered.value or ""
        if (
            not observed_sddl.startswith("D:P")
            or observed_sddl.count("(") != 1
            or expected_ace not in observed_sddl
        ):
            raise RouteV2Error("current-user-only ACL verification failed")
    except (OSError, ValueError) as exc:
        raise RouteV2Error("current-user-only ACL verification failed") from exc
    finally:
        if token.value:
            kernel32.CloseHandle(token)
        if sid_text:
            kernel32.LocalFree(sid_text)
        if rendered:
            kernel32.LocalFree(rendered)


def _validate_run_id(run_id: object) -> str:
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise RouteV2Error("run identity is invalid")
    return run_id


def _validate_authorization(value: object) -> str:
    if not isinstance(value, str) or value not in AUTHORIZATIONS:
        raise RouteV2Error("authorization is invalid")
    return value


def _default_execution_identity() -> dict[str, str]:
    implementation = _implementation_sha256()
    return {
        "cli_version": "synthetic",
        "command_contract_sha256": implementation,
        "executable_sha256": implementation,
        "kind": "synthetic",
        "runner_sha256": implementation,
    }


def _validate_execution_identity(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "cli_version",
        "command_contract_sha256",
        "executable_sha256",
        "kind",
        "runner_sha256",
    }:
        raise RouteV2Error("execution identity is invalid")
    normalized = dict(value)
    if normalized.get("kind") not in {"codex_exec", "synthetic"}:
        raise RouteV2Error("execution identity is invalid")
    cli_version = normalized.get("cli_version")
    if (
        not isinstance(cli_version, str)
        or not cli_version
        or cli_version != cli_version.strip()
        or len(cli_version) > 80
        or any(ord(char) < 0x20 or ord(char) > 0x7E for char in cli_version)
    ):
        raise RouteV2Error("execution identity is invalid")
    for key in (
        "command_contract_sha256",
        "executable_sha256",
        "runner_sha256",
    ):
        if not isinstance(normalized.get(key), str) or SHA256_RE.fullmatch(
            normalized[key]
        ) is None:
            raise RouteV2Error("execution identity is invalid")
    return normalized


def _validate_execution_binding(
    authorization: object, execution_identity: object
) -> tuple[str, dict[str, str]]:
    validated_authorization = _validate_authorization(authorization)
    identity = _validate_execution_identity(execution_identity)
    if (
        validated_authorization == AUTHORIZATION
        and identity["kind"] != "synthetic"
    ) or (
        validated_authorization == LIVE_AUTHORIZATION
        and identity["kind"] != "codex_exec"
    ):
        raise RouteV2Error("authorization and execution identity differ")
    return validated_authorization, identity


def _synthetic_preflight_bytes(
    run_id: str, execution_identity: Mapping[str, str] | None = None
) -> bytes:
    identity = _validate_execution_identity(
        execution_identity
        if execution_identity is not None
        else _default_execution_identity()
    )
    return _json_bytes(
        {
            "authorization": AUTHORIZATION,
            "checks": {
                "cleanup": "not_applicable",
                "exec_help": "not_applicable",
                "root_help": "not_applicable",
                "version": "not_applicable",
            },
            "compatibility": {
                "required_flag_presence": {},
                "root_help_nonempty": "not_applicable",
                "version_match": "not_applicable",
            },
            "environment_policy_sha256": _implementation_sha256(),
            "environment_projection_sha256": _implementation_sha256(),
            "execution_identity": identity,
            "probe_outputs": {},
            "required_flags": [],
            "run_id": _validate_run_id(run_id),
            "schema": PREFLIGHT_SCHEMA,
        }
    )


def _validate_preflight(
    payload: bytes, run_id: str, authorization: str
) -> tuple[dict[str, Any], dict[str, str]]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteV2Error("preflight receipt is invalid") from exc
    if not isinstance(value, dict) or payload != _json_bytes(value):
        raise RouteV2Error("preflight receipt is invalid")
    if set(value) != {
        "authorization",
            "checks",
            "compatibility",
            "environment_policy_sha256",
            "environment_projection_sha256",
            "execution_identity",
            "probe_outputs",
        "required_flags",
        "run_id",
        "schema",
    } or (
        value.get("schema") != PREFLIGHT_SCHEMA
        or value.get("run_id") != run_id
        or value.get("authorization") != authorization
        or SHA256_RE.fullmatch(str(value.get("environment_policy_sha256"))) is None
        or SHA256_RE.fullmatch(str(value.get("environment_projection_sha256"))) is None
    ):
        raise RouteV2Error("preflight receipt is invalid")
    identity = _validate_execution_binding(
        value.get("authorization"), value.get("execution_identity")
    )[1]
    checks = value.get("checks")
    compatibility = value.get("compatibility")
    flags = value.get("required_flags")
    probe_outputs = value.get("probe_outputs")
    if authorization == LIVE_AUTHORIZATION:
        if checks != {
            "cleanup": "PASS",
            "exec_help": "PASS",
            "root_help": "PASS",
            "version": "PASS",
        } or flags != sorted(
            [
                "--ephemeral",
                "--json",
                "--output-last-message",
                    "--output-schema",
                    "--dangerously-bypass-approvals-and-sandbox",
            ]
        ) or not isinstance(probe_outputs, Mapping) or set(probe_outputs) != {
            "exec_help", "root_help", "version"
        }:
            raise RouteV2Error("live preflight checks are incomplete")
        _validate_live_compatibility(compatibility, flags)
        validated_outputs = {
            name: _validate_probe_output(probe_outputs[name])
            for name in ("exec_help", "root_help", "version")
        }
        if validated_outputs["version"]["stdout_len"] == 0 or any(
            validated_outputs[name]["stdout_len"]
            + validated_outputs[name]["stderr_len"]
            == 0
            for name in ("root_help", "exec_help")
        ):
            raise RouteV2Error("live preflight probe output is empty")
    elif checks != {
        "cleanup": "not_applicable",
        "exec_help": "not_applicable",
        "root_help": "not_applicable",
        "version": "not_applicable",
    } or compatibility != {
        "required_flag_presence": {},
        "root_help_nonempty": "not_applicable",
        "version_match": "not_applicable",
    } or flags != [] or probe_outputs != {}:
        raise RouteV2Error("synthetic preflight checks are invalid")
    return value, identity


def _validate_live_compatibility(value: object, flags: list[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "required_flag_presence", "root_help_nonempty", "version_match"
    }:
        raise RouteV2Error("live preflight compatibility is invalid")
    presence = value.get("required_flag_presence")
    if (
        not isinstance(presence, Mapping)
        or set(presence) != set(flags)
        or any(type(presence[flag]) is not bool or presence[flag] is not True for flag in flags)
        or type(value.get("root_help_nonempty")) is not bool
        or value.get("root_help_nonempty") is not True
        or type(value.get("version_match")) is not bool
        or value.get("version_match") is not True
    ):
        raise RouteV2Error("live preflight compatibility is invalid")


def _validate_probe_output(value: object) -> dict[str, object]:
    # Raw probe bytes are private and deleted after the pinned builder emits this
    # attestation. Offline verification checks the closed shape and chain identity;
    # it does not reconstruct version/help semantics from these digests.
    if not isinstance(value, Mapping) or set(value) != {
        "returncode", "stderr_len", "stderr_sha256", "stdout_len", "stdout_sha256",
    } or type(value.get("returncode")) is not int or value.get("returncode") != 0:
        raise RouteV2Error("live preflight probe output is invalid")
    for stream in ("stdout", "stderr"):
        length = value.get(f"{stream}_len")
        digest = value.get(f"{stream}_sha256")
        if (
            type(length) is not int
            or not 0 <= length <= 262_144
            or not isinstance(digest, str)
            or SHA256_RE.fullmatch(digest) is None
        ):
            raise RouteV2Error("live preflight probe output is invalid")
    return dict(value)


def _validate_artifacts(value: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(value, Mapping):
        raise RouteV2Error("workspace artifact map is invalid")
    result: dict[str, bytes] = {}
    for key, payload in value.items():
        if not isinstance(key, str) or ARTIFACT_ID_RE.fullmatch(key) is None:
            raise RouteV2Error("workspace artifact identity is invalid")
        if not isinstance(payload, bytes):
            raise RouteV2Error("workspace artifact payload is invalid")
        result[key] = payload
    return dict(sorted(result.items()))


def _artifact_projection(value: Mapping[str, bytes]) -> list[dict[str, object]]:
    return [
        {"artifact_id": key, "bytes": len(payload), "sha256": _sha256_bytes(payload)}
        for key, payload in sorted(value.items())
    ]


def _validate_projection(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise RouteV2Error("workspace projection is invalid")
    normalized: list[dict[str, object]] = []
    for item in value:
        if (
            not isinstance(item, dict)
            or set(item) != {"artifact_id", "bytes", "sha256"}
            or not isinstance(item.get("artifact_id"), str)
            or ARTIFACT_ID_RE.fullmatch(item["artifact_id"]) is None
            or type(item.get("bytes")) is not int
            or item["bytes"] < 0
            or not isinstance(item.get("sha256"), str)
            or SHA256_RE.fullmatch(item["sha256"]) is None
        ):
            raise RouteV2Error("workspace projection is invalid")
        normalized.append(dict(item))
    if normalized != sorted(normalized, key=lambda item: str(item["artifact_id"])):
        raise RouteV2Error("workspace projection is not canonical")
    if len({item["artifact_id"] for item in normalized}) != len(normalized):
        raise RouteV2Error("workspace projection repeats an artifact")
    return normalized


def action_bytes(
    *,
    run_id: str,
    prompt: bytes,
    output_schema: dict[str, Any],
    expected_workspace: Mapping[str, bytes],
    authorization: str = AUTHORIZATION,
    execution_identity: Mapping[str, str] | None = None,
    preflight_sha256: str | None = None,
    ab_admission: Mapping[str, object] | None = None,
) -> bytes:
    run_id = _validate_run_id(run_id)
    if not isinstance(prompt, bytes):
        raise RouteV2Error("prompt bytes are invalid")
    schema = _validate_schema_definition(output_schema)
    expected = _validate_artifacts(expected_workspace)
    authorization, identity = _validate_execution_binding(
        authorization,
        execution_identity if execution_identity is not None else _default_execution_identity()
    )
    if preflight_sha256 is None:
        if authorization != AUTHORIZATION:
            raise RouteV2Error("live action requires a preflight identity")
        preflight_sha256 = _sha256_bytes(_synthetic_preflight_bytes(run_id))
    if SHA256_RE.fullmatch(preflight_sha256) is None:
        raise RouteV2Error("preflight identity is invalid")
    action: dict[str, object] = {
            "authorization": authorization,
            "execution_identity": identity,
            "expected_workspace": _artifact_projection(expected),
            "output_schema": schema,
            "preflight_sha256": preflight_sha256,
            "prompt_sha256": _sha256_bytes(prompt),
            "run_id": run_id,
            "schema": ACTION_SCHEMA,
        }
    if ab_admission is not None:
        if authorization != AUTHORIZATION:
            raise RouteV2Error("A/B admission requires synthetic authorization")
        admission = _validate_ab_admission(ab_admission)
        action.update(admission)
        action["schema"] = AB_ACTION_SCHEMA
    return _json_bytes(action)


def _validate_public_token(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 120
        or any(ord(char) < 0x20 or ord(char) > 0x7E for char in value)
    ):
        raise RouteV2Error(f"{label} is invalid")
    return value


def _validate_treatment_projection(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "state",
        "treatment_manifest_sha256",
        "treatment_packet_sha256",
    }:
        raise RouteV2Error("treatment projection is invalid")
    state = value.get("state")
    packet = value.get("treatment_packet_sha256")
    manifest = value.get("treatment_manifest_sha256")
    if not isinstance(manifest, str) or SHA256_RE.fullmatch(manifest) is None:
        raise RouteV2Error("treatment projection is invalid")
    if state == "absent" and packet == "absent":
        return {
            "state": "absent",
            "treatment_manifest_sha256": manifest,
            "treatment_packet_sha256": "absent",
        }
    if (
        state != "present"
        or not isinstance(packet, str)
        or SHA256_RE.fullmatch(packet) is None
    ):
        raise RouteV2Error("treatment projection is invalid")
    return {
        "state": "present",
        "treatment_manifest_sha256": manifest,
        "treatment_packet_sha256": packet,
    }


def _validate_ab_admission(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != {
        "arm_id",
        "model_id",
        "pair_action_sha256",
        "pair_id",
        "staged_input_manifest_sha256",
        "treatment_projection",
    }:
        raise RouteV2Error("A/B admission is invalid")
    arm_id = value.get("arm_id")
    if arm_id not in {"A", "B"}:
        raise RouteV2Error("A/B arm identity is invalid")
    pair_id = _validate_public_token(value.get("pair_id"), "pair identity")
    model_id = _validate_public_token(value.get("model_id"), "model identity")
    pair_action = value.get("pair_action_sha256")
    staged = value.get("staged_input_manifest_sha256")
    if (
        not isinstance(pair_action, str)
        or SHA256_RE.fullmatch(pair_action) is None
        or not isinstance(staged, str)
        or SHA256_RE.fullmatch(staged) is None
    ):
        raise RouteV2Error("A/B admission digest is invalid")
    treatment = _validate_treatment_projection(value.get("treatment_projection"))
    if (arm_id == "A") is not (treatment["state"] == "absent"):
        raise RouteV2Error("A/B treatment differs from arm identity")
    return {
        "arm_id": arm_id,
        "model_id": model_id,
        "pair_action_sha256": pair_action,
        "pair_id": pair_id,
        "staged_input_manifest_sha256": staged,
        "treatment_projection": treatment,
    }


def _validate_input_attestation(
    payload: bytes, action: Mapping[str, object]
) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteV2Error("input attestation is invalid") from exc
    expected_keys = {
        "action_sha256",
        "arm_id",
        "contract_manifest_sha256",
        "credential_acl",
        "model_id",
        "model_selector_match",
        "only_auth_inventory",
        "pair_action_sha256",
        "pair_id",
        "run_id",
        "schema",
        "staged_acl",
        "staged_content_match",
        "staged_input_manifest_sha256",
        "staged_inventory_match",
        "treatment_packet_sha256",
        "treatment_state",
        "validator_sha256",
    }
    treatment = action.get("treatment_projection")
    if (
        not isinstance(value, dict)
        or payload != _json_bytes(value)
        or set(value) != expected_keys
        or value.get("schema") != INPUT_ATTESTATION_SCHEMA
        or value.get("pair_id") != action.get("pair_id")
        or value.get("arm_id") != action.get("arm_id")
        or value.get("run_id") != action.get("run_id")
        or value.get("pair_action_sha256") != action.get("pair_action_sha256")
        or value.get("action_sha256") != _sha256_bytes(_json_bytes(dict(action)))
        or value.get("model_id") != action.get("model_id")
        or value.get("staged_input_manifest_sha256")
        != action.get("staged_input_manifest_sha256")
        or not isinstance(treatment, Mapping)
        or value.get("treatment_state") != treatment.get("state")
        or value.get("treatment_packet_sha256")
        != treatment.get("treatment_packet_sha256")
        or any(
            value.get(key) != "PASS"
            for key in (
                "credential_acl",
                "model_selector_match",
                "only_auth_inventory",
                "staged_acl",
                "staged_content_match",
                "staged_inventory_match",
            )
        )
        or not isinstance(value.get("contract_manifest_sha256"), str)
        or SHA256_RE.fullmatch(value["contract_manifest_sha256"]) is None
        or not isinstance(value.get("validator_sha256"), str)
        or SHA256_RE.fullmatch(value["validator_sha256"]) is None
    ):
        raise RouteV2Error("input attestation is invalid")
    return value


def _validate_schema_definition(schema: object) -> dict[str, Any]:
    if not isinstance(schema, dict):
        raise RouteV2Error("output schema is invalid")
    allowed = {"additionalProperties", "properties", "required", "type"}
    if set(schema) - allowed or schema.get("type") != "object":
        raise RouteV2Error("output schema is invalid")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise RouteV2Error("output schema is invalid")
    if schema.get("additionalProperties") is not False:
        raise RouteV2Error("output schema is invalid")
    if any(not isinstance(name, str) for name in required) or set(required) - set(
        properties
    ):
        raise RouteV2Error("output schema is invalid")
    for name, rule in properties.items():
        if not isinstance(name, str) or not isinstance(rule, dict):
            raise RouteV2Error("output schema is invalid")
        if set(rule) - {"enum", "type"} or rule.get("type") not in {
            "boolean",
            "integer",
            "number",
            "string",
        }:
            raise RouteV2Error("output schema is invalid")
        if "enum" in rule and not isinstance(rule["enum"], list):
            raise RouteV2Error("output schema is invalid")
    return schema


def _matches_schema(value: object, schema: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    properties = schema["properties"]
    if set(schema["required"]) - set(value):
        return False
    if set(value) - set(properties):
        return False
    type_map: dict[str, type | tuple[type, ...]] = {
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "string": str,
    }
    for name, item in value.items():
        expected = properties[name]["type"]
        if expected == "integer" and isinstance(item, bool):
            return False
        if expected == "number" and isinstance(item, bool):
            return False
        if not isinstance(item, type_map[expected]):
            return False
        if "enum" in properties[name] and item not in properties[name]["enum"]:
            return False
    return True


def _validate_result(value: object) -> SyntheticResult:
    if not isinstance(value, SyntheticResult):
        raise RouteV2Error("synthetic runner result is invalid")
    if type(value.exit_code) is not int:
        raise RouteV2Error("synthetic runner result is invalid")
    exit_classification = value.exit_classification or (
        "zero" if value.exit_code == 0 else "nonzero"
    )
    if exit_classification not in {"zero", "nonzero", "signal_or_termination"}:
        raise RouteV2Error("synthetic runner result is invalid")
    if (
        (exit_classification == "zero" and value.exit_code != 0)
        or (exit_classification == "nonzero" and value.exit_code == 0)
        or (exit_classification == "signal_or_termination" and value.exit_code >= 0)
    ):
        raise RouteV2Error("synthetic runner result is invalid")
    stdout_capture = value.stdout_capture or "captured"
    if stdout_capture not in {"captured", "capture_failed"} or (
        (stdout_capture == "captured" and not isinstance(value.stdout, bytes))
        or (stdout_capture == "capture_failed" and value.stdout is not None)
    ):
        raise RouteV2Error("synthetic runner result is invalid")
    final_capture = value.final_capture or (
        "absent" if value.final_message is None else "captured"
    )
    if final_capture not in {"captured", "absent", "read_failed"} or (
        (final_capture == "captured" and not isinstance(value.final_message, bytes))
        or (final_capture != "captured" and value.final_message is not None)
    ):
        raise RouteV2Error("synthetic runner result is invalid")
    workspace_capture = value.workspace_capture or "captured"
    if workspace_capture not in {"captured", "capture_failed"} or (
        (workspace_capture == "captured" and not isinstance(value.workspace, Mapping))
        or (workspace_capture == "capture_failed" and value.workspace is not None)
    ):
        raise RouteV2Error("synthetic runner result is invalid")
    return SyntheticResult(
        exit_code=value.exit_code,
        stdout=value.stdout,
        final_message=value.final_message,
        workspace=(
            _validate_artifacts(value.workspace)
            if workspace_capture == "captured"
            else None
        ),
        exit_classification=exit_classification,
        stdout_capture=stdout_capture,
        final_capture=final_capture,
        workspace_capture=workspace_capture,
    )


def _attestation(
    result: SyntheticResult | None, output_schema: dict[str, Any]
) -> tuple[dict[str, Any], bool, bool]:
    if result is None:
        return (
            {
                "exit_classification": "unavailable",
                "final_message": {"status": "absent"},
                "final_schema_validation": "not_attempted",
                "schema": ATTESTATION_SCHEMA,
                "schema_sha256": _sha256_bytes(_json_bytes(output_schema)),
                "stdout": {"status": "absent", "validation": "not_attempted"},
                "validator_sha256": _implementation_sha256(),
                "workspace_capture": "not_attempted",
            },
            False,
            False,
        )
    if result.stdout_capture == "capture_failed":
        stdout_identity: dict[str, object] = {
            "status": "capture_failed",
            "validation": "not_attempted",
        }
        stdout_valid = False
    else:
        assert result.stdout is not None
        lines = result.stdout.splitlines()
        stdout_values: list[object] = []
        stdout_valid = bool(lines)
        for line in lines:
            if not line.strip():
                continue
            try:
                stdout_values.append(json.loads(line))
            except (UnicodeDecodeError, json.JSONDecodeError):
                stdout_valid = False
        stdout_valid = stdout_valid and bool(stdout_values) and len(stdout_values) == len(
            [line for line in lines if line.strip()]
        )
        stdout_status = "empty" if not result.stdout else "nonempty"
        stdout_identity = {
            "bytes": len(result.stdout),
            "json_value_count": len(stdout_values),
            "sha256": _sha256_bytes(result.stdout),
            "status": stdout_status,
            "validation": "PASS" if stdout_valid else "FAIL",
        }
    final_status = "absent"
    final_valid = False
    final_identity: dict[str, object] = {"status": final_status}
    final_validation = "not_attempted"
    if result.final_capture == "read_failed":
        final_status = "read_failed"
        final_identity = {"status": final_status}
    elif result.final_message is not None:
        final_status = "empty" if not result.final_message else "nonempty"
        final_identity = {
            "bytes": len(result.final_message),
            "sha256": _sha256_bytes(result.final_message),
            "status": final_status,
        }
        try:
            final_value = json.loads(result.final_message.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            final_value = None
        final_valid = _matches_schema(final_value, output_schema)
        final_validation = "PASS" if final_valid else "FAIL"

    attestation = {
        "exit_classification": result.exit_classification,
        "final_message": final_identity,
        "final_schema_validation": final_validation,
        "schema": ATTESTATION_SCHEMA,
        "schema_sha256": _sha256_bytes(_json_bytes(output_schema)),
        "stdout": stdout_identity,
        "validator_sha256": _implementation_sha256(),
        "workspace_capture": (
            "PASS" if result.workspace_capture == "captured" else "FAIL"
        ),
    }
    return attestation, stdout_valid, final_valid


def _faulting_publisher(
    plan: FaultPlan, delegate: Publisher, *, public: bool
) -> Publisher:
    def publish(path: Path, payload: bytes) -> None:
        if path.name in plan.publication_failures:
            raise PublicationError(f"injected publication failure: {path.name}")
        if public:
            if path.name in plan.privacy_failures:
                raise PublicPrivacyError(
                    f"injected public privacy failure: {path.name}"
                )
            _validate_public_payload(payload)
        delegate(path, payload)

    return publish


def _faulting_cleaner(plan: FaultPlan) -> Cleaner:
    remaining = plan.cleanup_failures

    def clean(path: Path) -> bool:
        nonlocal remaining
        if remaining:
            remaining -= 1
            return False
        shutil.rmtree(path, ignore_errors=False) if path.exists() else None
        return not path.exists()

    return clean


def _attempt_cleanup(clean: Cleaner, path: Path) -> bool:
    try:
        reported = clean(path)
    except Exception:
        return False
    return reported is True and not path.exists()


def _faulting_remover(plan: FaultPlan) -> LocatorRemover:
    remaining = plan.locator_removal_failures

    def remove(path: Path) -> None:
        nonlocal remaining
        if remaining and (path.exists() or path.parent.exists()):
            remaining -= 1
            raise RouteV2Error("locator removal failed")
        if path.exists():
            path.unlink()
        if path.parent.exists():
            path.parent.rmdir()

    return remove


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _assert_distinct_roots(
    output_root: Path, private_root: Path, locator: Path, external_path: Path
) -> None:
    resolved = [
        output_root.resolve(),
        private_root.resolve(),
        locator.resolve(),
        external_path.resolve(),
    ]
    if len(set(resolved)) != 4:
        raise RouteV2Error("route roots overlap")
    if _is_within(output_root, private_root) or _is_within(private_root, output_root):
        raise RouteV2Error("public or recovery artifact is inside cleanup target")
    if _is_within(locator, private_root) or _is_within(external_path, private_root):
        raise RouteV2Error("public or recovery artifact is inside cleanup target")
    if _is_within(locator, output_root) or _is_within(external_path, output_root):
        raise RouteV2Error("recovery artifact is inside route output")


def _locator_value(
    run_id: str, private_root: Path, authorization: str = AUTHORIZATION
) -> dict[str, str]:
    return {
        "authorization": _validate_authorization(authorization),
        "cleanup_target": str(private_root.resolve()),
        "run_id": run_id,
        "schema": LOCATOR_SCHEMA,
    }


def _trusted_roots(
    run_id: str, override: Path | None = None
) -> tuple[Path, Path, Path, Path]:
    root = (TRUSTED_ROUTE_ROOT if override is None else override).resolve()
    return (
        root / "public" / run_id,
        root / "private" / f"gate3-v2-{run_id}",
        root / "locators" / run_id / "locator.json",
        root / "external" / f"{run_id}.terminal.json",
    )


def _validate_trusted_roots(
    *,
    output_root: Path,
    locator: Path,
    external_path: Path,
    run_id: str,
    override: Path | None,
) -> Path:
    expected_output, private_root, expected_locator, expected_external = _trusted_roots(
        run_id, override
    )
    if (
        output_root.resolve() != expected_output
        or locator.resolve() != expected_locator
        or external_path.resolve() != expected_external
    ):
        raise RouteV2Error("route path differs from trusted layout")
    return private_root


def _locator_path(locator_root: Path, run_id: str) -> Path:
    return locator_root.resolve() / run_id / "locator.json"


def _locator_residue(locator: Path) -> bool:
    return locator.exists() or locator.parent.exists()


def _validate_locator(
    path: Path,
    run_id: str,
    private_root: Path,
    acl_verify: AclProtector = _verify_current_user_only,
    authorization: str = AUTHORIZATION,
) -> None:
    acl_verify(path.parent, True)
    acl_verify(path, False)
    value = _load_object(path)
    if value != _locator_value(
        run_id, private_root, authorization
    ) or path.read_bytes() != _json_bytes(value):
        raise RouteV2Error("recovery locator identity is invalid")


def _external_terminal(
    *,
    run_id: str,
    stage: str,
    cleanup: str,
    locator_absent: bool,
    authorization: str = AUTHORIZATION,
) -> dict[str, object]:
    return {
        "admissible_route_result": False,
        "authorization": _validate_authorization(authorization),
        "cleanup": cleanup,
        "locator_absent": locator_absent,
        "run_id": run_id,
        "schema": EXTERNAL_SCHEMA,
        "terminal": stage,
    }


def _validate_external_value(
    value: dict[str, Any], run_id: str, authorization: str = AUTHORIZATION
) -> None:
    if (
        set(value)
        != {
            "admissible_route_result",
            "authorization",
            "cleanup",
            "locator_absent",
            "run_id",
            "schema",
            "terminal",
        }
        or value.get("schema") != EXTERNAL_SCHEMA
        or value.get("run_id") != run_id
        or value.get("authorization") != _validate_authorization(authorization)
        or value.get("admissible_route_result") is not False
        or value.get("cleanup") != "PASS"
        or type(value.get("locator_absent")) is not bool
        or value.get("terminal") not in TERMINAL_STAGES
        or value.get("locator_absent")
        is not (value.get("terminal") in LOCATOR_ABSENT_TERMINALS)
    ):
        raise RouteV2Error("external terminal is invalid")


def _publish_external_closeout(
    external_path: Path,
    *,
    output_root: Path,
    run_id: str,
    stage: str,
    cleanup_passed: bool,
    locator: Path,
    publish: Publisher,
    remove_locator: LocatorRemover,
    authorization: str = AUTHORIZATION,
) -> None:
    if not cleanup_passed:
        return
    if output_root.exists():
        shutil.rmtree(output_root, ignore_errors=False)
    if output_root.exists():
        raise RouteV2Error("partial route artifact residue remains")
    value = _external_terminal(
        run_id=run_id,
        stage=stage,
        cleanup="PASS",
        locator_absent=not _locator_residue(locator),
        authorization=authorization,
    )
    publish(external_path, _json_bytes(value))
    remove_locator(locator)
    if _locator_residue(locator):
        raise RouteV2Error("recovery locator residue remains")
    # The record intentionally says the locator existed at publication time.
    # Its absence is established independently by the reconciler/verifier.


def _load_recovery_chain(
    output_root: Path, run_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    attestation_path = output_root / "attestation.json"
    packet_path = output_root / "packet.json"
    seal_path = output_root / "seal.json"
    if not all(path.is_file() for path in (attestation_path, packet_path, seal_path)):
        raise RouteV2Error("recovery chain is incomplete")
    packet = _load_object(packet_path)
    seal = _load_object(seal_path)
    if (
        packet.get("schema") != PACKET_SCHEMA
        or packet.get("run_id") != run_id
        or type(packet.get("eligible_success")) is not bool
        or set(seal)
        != {
            "attestation_sha256",
            "cleanup",
            "decision",
            "observations",
            "packet_sha256",
            "run_id",
            "schema",
        }
        or seal.get("schema") != SEAL_SCHEMA
        or seal.get("run_id") != run_id
        or seal.get("cleanup") != "PENDING"
        or seal.get("decision") != "PENDING"
        or not isinstance(seal.get("observations"), dict)
        or seal.get("attestation_sha256") != _sha256_file(attestation_path)
        or seal.get("packet_sha256") != _sha256_file(packet_path)
    ):
        raise RouteV2Error("recovery chain identity is invalid")
    return packet, seal


def _validate_recovery_final(output_root: Path, run_id: str) -> str:
    packet, seal = _load_recovery_chain(output_root, run_id)
    final = _load_object(output_root / "final.json")
    expected_decision = (
        "SUCCESS"
        if packet["eligible_success"]
        and final.get("cleanup") == "PASS"
        and final.get("recovery") == "none"
        else "FAILURE"
    )
    if (
        set(final)
        != {
            "cleanup",
            "decision",
            "locator_required",
            "packet_sha256",
            "recovery",
            "run_id",
            "schema",
            "seal_sha256",
        }
        or final.get("schema") != FINAL_SCHEMA
        or final.get("run_id") != run_id
        or final.get("packet_sha256") != _sha256_bytes(_json_bytes(packet))
        or final.get("seal_sha256") != _sha256_bytes(_json_bytes(seal))
        or final.get("cleanup") not in {"PASS", "FAIL"}
        or final.get("recovery") not in {"none", "interrupted_after_seal"}
        or final.get("decision") != expected_decision
        or final.get("locator_required") is not (final.get("cleanup") == "FAIL")
    ):
        raise RouteV2Error("recovery final identity is invalid")
    return expected_decision


def orchestrate(
    output_root: Path,
    *,
    locator_root: Path,
    external_root: Path,
    run_id: str,
    authorization: str,
    prompt: bytes,
    output_schema: dict[str, Any],
    expected_workspace: Mapping[str, bytes],
    runner: Runner,
    ab_admission: Mapping[str, object] | None = None,
    fault_plan: FaultPlan | None = None,
    _publisher: Publisher = _publish_create_once,
    _acl: AclProtector = _current_user_only,
    _acl_verify: AclProtector = _verify_current_user_only,
    _trusted_route_root: Path | None = None,
) -> RouteResult:
    run_id = _validate_run_id(run_id)
    _validate_authorization(authorization)
    if not isinstance(prompt, bytes):
        raise RouteV2Error("prompt bytes are invalid")
    schema = _validate_schema_definition(output_schema)
    expected = _validate_artifacts(expected_workspace)
    if ab_admission is not None and type(runner) is not TrustedABArmRunner:
        raise RouteV2Error("A/B admission requires a trusted A/B runner")
    if ab_admission is not None and authorization != AUTHORIZATION:
        raise RouteV2Error("A/B admission requires synthetic authorization")
    if authorization == LIVE_AUTHORIZATION:
        if type(runner) is not TrustedLiveRunner:
            raise RouteV2Error("live authorization requires a trusted runner")
        preflight_payload = runner.preflight_bytes()
        _, execution_identity = _validate_preflight(
            preflight_payload, run_id, authorization
        )
        if execution_identity != _validate_execution_identity(
            runner.execution_identity()
        ):
            raise RouteV2Error("runner differs from measured preflight")
    else:
        synthetic_identity = (
            runner.execution_identity()
            if ab_admission is not None and type(runner) is TrustedABArmRunner
            else None
        )
        preflight_payload = _synthetic_preflight_bytes(run_id, synthetic_identity)
        _, execution_identity = _validate_preflight(
            preflight_payload, run_id, authorization
        )
    plan = fault_plan or FaultPlan()
    publish = _faulting_publisher(plan, _publisher, public=True)
    publish_private = _faulting_publisher(plan, _publisher, public=False)
    clean = _faulting_cleaner(plan)
    remove_locator = _faulting_remover(plan)

    output_root = output_root.resolve()
    locator = _locator_path(locator_root, run_id)
    external_path = (external_root.resolve() / f"{run_id}.terminal.json").resolve()
    private_root = _validate_trusted_roots(
        output_root=output_root,
        locator=locator,
        external_path=external_path,
        run_id=run_id,
        override=_trusted_route_root,
    )
    _assert_distinct_roots(output_root, private_root, locator, external_path)
    if (
        output_root.exists()
        or private_root.exists()
        or locator.parent.exists()
        or external_path.exists()
    ):
        raise RouteV2Error("route output collision")
    output_root.mkdir(parents=True)
    external_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        publish(output_root / "preflight.json", preflight_payload)
    except BaseException as exc:
        _publish_external_closeout(
            external_path,
            output_root=output_root,
            run_id=run_id,
            stage="preflight_publication_failure",
            cleanup_passed=True,
            locator=locator,
            publish=publish,
            remove_locator=lambda _: None,
            authorization=authorization,
        )
        raise RouteV2Error("preflight publication failed before invocation") from exc

    action_payload = action_bytes(
        run_id=run_id,
        prompt=prompt,
        output_schema=schema,
        expected_workspace=expected,
        authorization=authorization,
        execution_identity=execution_identity,
        preflight_sha256=_sha256_bytes(preflight_payload),
        ab_admission=ab_admission,
    )
    action = json.loads(action_payload)
    try:
        publish(output_root / "action.json", action_payload)
    except BaseException as exc:
        _publish_external_closeout(
            external_path,
            output_root=output_root,
            run_id=run_id,
            stage="action_publication_failure",
            cleanup_passed=True,
            locator=locator,
            publish=publish,
            remove_locator=lambda _: None,
            authorization=authorization,
        )
        raise RouteV2Error("action publication failed before invocation") from exc

    runner_calls = 0
    try:
        locator.parent.mkdir(parents=True)
        _acl(locator.parent, True)
        publish_private(
            locator, _json_bytes(_locator_value(run_id, private_root, authorization))
        )
        _acl(locator, False)
        _validate_locator(
            locator, run_id, private_root, _acl_verify, authorization
        )
    except BaseException:
        try:
            if _locator_residue(locator):
                remove_locator(locator)
        finally:
            if _locator_residue(locator):
                raise RouteV2Error("partial locator residue remains")
        _publish_external_closeout(
            external_path,
            output_root=output_root,
            run_id=run_id,
            stage="locator_prelaunch_failure",
            cleanup_passed=True,
            locator=locator,
            publish=publish,
            remove_locator=lambda _: None,
            authorization=authorization,
        )
        raise RouteV2Error("locator prelaunch validation failed")

    stage = "private_acl"
    seal_path = output_root / "seal.json"
    final_path = output_root / "final.json"
    try:
        private_root.mkdir(parents=True)
        _acl(private_root, True)
        input_attestation: dict[str, object] | None = None
        if ab_admission is not None:
            assert type(runner) is TrustedABArmRunner
            stage = "input_attestation"
            input_payload = runner.prepare(private_root, action_payload)
            input_attestation = _validate_input_attestation(input_payload, action)
            publish(output_root / "input-attestation.json", input_payload)
        stage = "runner"
        runner_calls += 1
        try:
            result = _validate_result(runner())
        except Exception:
            result = None
        if runner_calls != 1:
            raise RouteV2Error("synthetic runner invocation count is invalid")
        if plan.crash_after == "runner":
            raise SyntheticCrash("injected crash after runner")

        if result is not None:
            if result.stdout_capture == "captured":
                assert result.stdout is not None
                stdout_path = private_root / "stdout.ndjson"
                stdout_path.write_bytes(result.stdout)
                _acl(stdout_path, False)
            if result.final_capture == "captured":
                assert result.final_message is not None
                final_private = private_root / "final-message.json"
                final_private.write_bytes(result.final_message)
                _acl(final_private, False)

        stage = "attestation"
        attestation, stdout_valid, final_valid = _attestation(result, schema)
        publish(output_root / "attestation.json", _json_bytes(attestation))
        if plan.crash_after == "attestation":
            raise SyntheticCrash("injected crash after attestation")

        stage = "packet"
        workspace_captured = (
            result is not None and result.workspace_capture == "captured"
        )
        observed = (
            _artifact_projection(result.workspace)
            if workspace_captured and result is not None and result.workspace is not None
            else []
        )
        workspace_match = workspace_captured and observed == action["expected_workspace"]
        packet = {
            "action_sha256": _sha256_bytes(_json_bytes(action)),
            "attestation_sha256": _sha256_bytes(_json_bytes(attestation)),
            "checks": {
                "exit_zero": result is not None
                and result.exit_classification == "zero",
                "final_schema": final_valid,
                "stdout_ndjson": stdout_valid,
                "workspace_matches_expected": workspace_match,
            },
            "eligible_success": all(
                (
                    result is not None and result.exit_classification == "zero",
                    final_valid,
                    stdout_valid,
                    workspace_match,
                )
            ),
            "observed_workspace": observed,
            "run_id": run_id,
            "schema": AB_PACKET_SCHEMA if input_attestation is not None else PACKET_SCHEMA,
        }
        if input_attestation is not None:
            packet["input_attestation_sha256"] = _sha256_bytes(
                _json_bytes(input_attestation)
            )
        publish(output_root / "packet.json", _json_bytes(packet))

        stage = "seal"
        seal = {
            "attestation_sha256": packet["attestation_sha256"],
            "cleanup": "PENDING",
            "decision": "PENDING",
            "observations": {
                "exit_classification": attestation["exit_classification"],
                "final_message": attestation["final_message"]["status"],
                "final_schema": attestation["final_schema_validation"],
                "packet_assembly": "PASS",
                "process_launch": "attempted",
                "stdout_capture": attestation["stdout"]["status"],
                "stdout_ndjson": attestation["stdout"]["validation"],
                "workspace_capture": (
                    attestation["workspace_capture"]
                ),
                "workspace_validation": (
                    "PASS"
                    if workspace_match
                    else "FAIL"
                    if workspace_captured
                    else "not_attempted"
                ),
            },
            "packet_sha256": _sha256_bytes(_json_bytes(packet)),
            "run_id": run_id,
            "schema": SEAL_SCHEMA,
        }
        publish(seal_path, _json_bytes(seal))
        if plan.crash_after == "seal":
            raise SyntheticCrash("injected crash after seal")
    except SyntheticCrash:
        raise
    except BaseException as exc:
        cleanup_passed = _attempt_cleanup(clean, private_root)
        _publish_external_closeout(
            external_path,
            output_root=output_root,
            run_id=run_id,
            stage=f"preseal_{stage}_failure",
            cleanup_passed=cleanup_passed,
            locator=locator,
            publish=publish,
            remove_locator=remove_locator,
            authorization=authorization,
        )
        raise RouteV2Error(f"synthetic route failed before seal: {stage}") from exc

    cleanup_passed = _attempt_cleanup(clean, private_root)
    if plan.crash_after == "cleanup":
        raise SyntheticCrash("injected crash after cleanup")
    decision = "SUCCESS" if packet["eligible_success"] and cleanup_passed else "FAILURE"
    final = {
        "cleanup": "PASS" if cleanup_passed else "FAIL",
        "decision": decision,
        "locator_required": not cleanup_passed,
        "packet_sha256": seal["packet_sha256"],
        "recovery": "none",
        "run_id": run_id,
        "schema": FINAL_SCHEMA,
        "seal_sha256": _sha256_bytes(_json_bytes(seal)),
    }
    try:
        publish(final_path, _json_bytes(final))
    except BaseException as exc:
        _publish_external_closeout(
            external_path,
            output_root=output_root,
            run_id=run_id,
            stage="final_publication_failure",
            cleanup_passed=cleanup_passed,
            locator=locator,
            publish=publish,
            remove_locator=remove_locator,
            authorization=authorization,
        )
        raise RouteV2Error("final receipt publication failed") from exc

    if cleanup_passed:
        remove_locator(locator)
        if _locator_residue(locator):
            raise RouteV2Error("recovery locator residue remains")

    return RouteResult(
        output_root=output_root,
        locator=locator,
        final_receipt=final_path,
        external_terminal=None,
        decision=decision,
    )


def reconcile(
    output_root: Path,
    *,
    locator_root: Path,
    external_root: Path,
    run_id: str,
    authorization: str,
    fault_plan: FaultPlan | None = None,
    _publisher: Publisher = _publish_create_once,
    _acl_verify: AclProtector = _verify_current_user_only,
    _trusted_route_root: Path | None = None,
) -> RouteResult:
    run_id = _validate_run_id(run_id)
    _validate_authorization(authorization)
    plan = fault_plan or FaultPlan()
    publish = _faulting_publisher(plan, _publisher, public=True)
    clean = _faulting_cleaner(plan)
    remove_locator = _faulting_remover(plan)
    output_root = output_root.resolve()
    locator = _locator_path(locator_root, run_id)
    external_path = (external_root.resolve() / f"{run_id}.terminal.json").resolve()
    private_root = _validate_trusted_roots(
        output_root=output_root,
        locator=locator,
        external_path=external_path,
        run_id=run_id,
        override=_trusted_route_root,
    )
    _assert_distinct_roots(output_root, private_root, locator, external_path)
    if not locator.exists():
        raise RouteV2Error("recovery locator is absent")
    _validate_locator(locator, run_id, private_root, _acl_verify, authorization)
    cleanup_passed = _attempt_cleanup(clean, private_root)
    if not cleanup_passed:
        raise RouteV2Error("recovery cleanup failed")

    final_path = output_root / "final.json"
    seal_path = output_root / "seal.json"
    if external_path.exists():
        terminal = _load_object(external_path)
        _validate_external_value(terminal, run_id, authorization)
        remove_locator(locator)
        if _locator_residue(locator):
            raise RouteV2Error("recovery locator residue remains")
        return RouteResult(output_root, locator, None, external_path, "NO_ADMISSIBLE")

    if final_path.exists():
        decision = _validate_recovery_final(output_root, run_id)
        remove_locator(locator)
        if _locator_residue(locator):
            raise RouteV2Error("recovery locator residue remains")
        return RouteResult(output_root, locator, final_path, None, str(decision))

    if seal_path.exists():
        _, seal = _load_recovery_chain(output_root, run_id)
        final = {
            "cleanup": "PASS",
            "decision": "FAILURE",
            "locator_required": False,
            "packet_sha256": seal.get("packet_sha256"),
            "recovery": "interrupted_after_seal",
            "run_id": run_id,
            "schema": FINAL_SCHEMA,
            "seal_sha256": _sha256_file(seal_path),
        }
        try:
            publish(final_path, _json_bytes(final))
        except BaseException:
            _publish_external_closeout(
                external_path,
                output_root=output_root,
                run_id=run_id,
                stage="final_publication_exhausted",
                cleanup_passed=True,
                locator=locator,
                publish=publish,
                remove_locator=remove_locator,
                authorization=authorization,
            )
            return RouteResult(output_root, locator, None, external_path, "NO_ADMISSIBLE")
        remove_locator(locator)
        if _locator_residue(locator):
            raise RouteV2Error("recovery locator residue remains")
        return RouteResult(output_root, locator, final_path, None, "FAILURE")

    _publish_external_closeout(
        external_path,
        output_root=output_root,
        run_id=run_id,
        stage="orphan_without_seal",
        cleanup_passed=True,
        locator=locator,
        publish=publish,
        remove_locator=remove_locator,
        authorization=authorization,
    )
    return RouteResult(output_root, locator, None, external_path, "NO_ADMISSIBLE")


def verify(
    output_root: Path,
    *,
    locator_root: Path,
    external_root: Path,
    run_id: str,
    expected_action_sha256: str,
    expected_final_sha256: str,
    _trusted_route_root: Path | None = None,
) -> dict[str, Any]:
    run_id = _validate_run_id(run_id)
    if SHA256_RE.fullmatch(expected_action_sha256) is None:
        raise RouteV2Error("expected action identity is invalid")
    if SHA256_RE.fullmatch(expected_final_sha256) is None:
        raise RouteV2Error("expected final identity is invalid")
    output_root = output_root.resolve()
    locator = _locator_path(locator_root, run_id)
    external_path = external_root.resolve() / f"{run_id}.terminal.json"
    private_root = _validate_trusted_roots(
        output_root=output_root,
        locator=locator,
        external_path=external_path,
        run_id=run_id,
        override=_trusted_route_root,
    )
    if _locator_residue(locator):
        raise RouteV2Error("recovery locator still exists")
    if external_path.exists():
        raise RouteV2Error("same-run external terminal exists")
    if private_root.exists():
        raise RouteV2Error("private cleanup target still exists")
    expected_names = {
        "action.json",
        "attestation.json",
        "final.json",
        "packet.json",
        "preflight.json",
        "seal.json",
    }
    observed_entries = list(output_root.iterdir()) if output_root.is_dir() else []
    if any(
        entry.is_symlink()
        or not entry.is_file()
        or bool(
            getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
        for entry in observed_entries
    ):
        raise RouteV2Error("route artifact set contains an unsupported entry")
    observed_names = {entry.name for entry in observed_entries}
    if observed_names != expected_names and observed_names != expected_names | {
        "input-attestation.json"
    }:
        raise RouteV2Error("route artifact set is not closed")
    paths: dict[str, Path] = {
        name: output_root / f"{name}.json"
        for name in ("preflight", "action", "attestation", "packet", "seal", "final")
    }
    if any(not path.is_file() for path in paths.values()):
        raise RouteV2Error("route artifact set is incomplete")
    if _sha256_file(paths["final"]) != expected_final_sha256:
        raise RouteV2Error("final receipt differs from pinned identity")
    action = _load_object(paths["action"])
    is_ab = action.get("schema") == AB_ACTION_SCHEMA
    input_attestation: dict[str, object] | None = None
    if is_ab:
        paths["input-attestation"] = output_root / "input-attestation.json"
        if not paths["input-attestation"].is_file():
            raise RouteV2Error("route artifact set is incomplete")
        input_attestation = _load_object(paths["input-attestation"])
    if observed_names != (
        expected_names | {"input-attestation.json"} if is_ab else expected_names
    ):
        raise RouteV2Error("route artifact set differs from action schema")
    preflight = _load_object(paths["preflight"])
    attestation = _load_object(paths["attestation"])
    packet = _load_object(paths["packet"])
    seal = _load_object(paths["seal"])
    final = _load_object(paths["final"])
    if _sha256_file(paths["action"]) != expected_action_sha256:
        raise RouteV2Error("action differs from pinned identity")
    base_action_keys = {
        "authorization",
        "execution_identity",
        "expected_workspace",
        "output_schema",
        "preflight_sha256",
        "prompt_sha256",
        "run_id",
        "schema",
    }
    ab_action_keys = base_action_keys | {
        "arm_id",
        "model_id",
        "pair_action_sha256",
        "pair_id",
        "staged_input_manifest_sha256",
        "treatment_projection",
    }
    if set(action) != (ab_action_keys if is_ab else base_action_keys) or (
        action.get("schema") != (AB_ACTION_SCHEMA if is_ab else ACTION_SCHEMA)
        or action.get("run_id") != run_id
        or action.get("authorization") not in AUTHORIZATIONS
        or SHA256_RE.fullmatch(str(action.get("prompt_sha256"))) is None
        or action.get("preflight_sha256") != _sha256_file(paths["preflight"])
    ):
        raise RouteV2Error("action identity is invalid")
    _validate_execution_binding(
        action.get("authorization"), action.get("execution_identity")
    )
    if is_ab:
        _validate_ab_admission(
            {key: action[key] for key in ab_action_keys - base_action_keys}
        )
        assert input_attestation is not None
        _validate_input_attestation(paths["input-attestation"].read_bytes(), action)
    _, preflight_identity = _validate_preflight(
        paths["preflight"].read_bytes(), run_id, action["authorization"]
    )
    if preflight_identity != action["execution_identity"]:
        raise RouteV2Error("action differs from measured preflight")
    _validate_schema_definition(action.get("output_schema"))
    _validate_projection(action.get("expected_workspace"))
    if set(attestation) != {
        "exit_classification",
        "final_message",
        "final_schema_validation",
        "schema",
        "schema_sha256",
        "stdout",
        "validator_sha256",
        "workspace_capture",
    } or (
        attestation.get("schema") != ATTESTATION_SCHEMA
        or attestation.get("schema_sha256")
        != _sha256_bytes(_json_bytes(action["output_schema"]))
        or attestation.get("validator_sha256") != _implementation_sha256()
        or attestation.get("final_schema_validation")
        not in {"PASS", "FAIL", "not_attempted"}
        or attestation.get("exit_classification")
        not in {"zero", "nonzero", "signal_or_termination", "unavailable"}
        or attestation.get("workspace_capture") not in {"PASS", "FAIL", "not_attempted"}
    ):
        raise RouteV2Error("attestation identity is invalid")
    stdout_attestation = attestation.get("stdout")
    final_attestation = attestation.get("final_message")
    if (
        not isinstance(stdout_attestation, dict)
        or stdout_attestation.get("status")
        not in {"absent", "capture_failed", "empty", "nonempty"}
        or stdout_attestation.get("validation") not in {"PASS", "FAIL", "not_attempted"}
        or not isinstance(final_attestation, dict)
        or final_attestation.get("status")
        not in {"absent", "empty", "nonempty", "read_failed"}
    ):
        raise RouteV2Error("attestation structure is invalid")
    if stdout_attestation.get("status") in {"absent", "capture_failed"}:
        if set(stdout_attestation) != {"status", "validation"} or stdout_attestation.get(
            "validation"
        ) != "not_attempted":
            raise RouteV2Error("attestation structure is invalid")
    elif (
        set(stdout_attestation)
        != {"bytes", "json_value_count", "sha256", "status", "validation"}
        or type(stdout_attestation.get("bytes")) is not int
        or type(stdout_attestation.get("json_value_count")) is not int
        or stdout_attestation["bytes"] < 0
        or stdout_attestation["json_value_count"] < 0
        or SHA256_RE.fullmatch(str(stdout_attestation.get("sha256"))) is None
        or stdout_attestation.get("validation") == "not_attempted"
        or (stdout_attestation.get("status") == "empty")
        is not (stdout_attestation["bytes"] == 0)
    ):
        raise RouteV2Error("attestation structure is invalid")
    if final_attestation.get("status") in {"absent", "read_failed"}:
        if set(final_attestation) != {"status"} or attestation.get(
            "final_schema_validation"
        ) != "not_attempted":
            raise RouteV2Error("attestation structure is invalid")
    elif (
        set(final_attestation) != {"bytes", "sha256", "status"}
        or type(final_attestation.get("bytes")) is not int
        or final_attestation["bytes"] < 0
        or SHA256_RE.fullmatch(str(final_attestation.get("sha256"))) is None
        or attestation.get("final_schema_validation") == "not_attempted"
        or (final_attestation.get("status") == "empty")
        is not (final_attestation["bytes"] == 0)
    ):
        raise RouteV2Error("attestation structure is invalid")
    if attestation.get("exit_classification") == "unavailable":
        if (
            stdout_attestation.get("status") != "absent"
            or final_attestation.get("status") != "absent"
            or attestation.get("workspace_capture") != "not_attempted"
        ):
            raise RouteV2Error("attestation unavailable state is invalid")
    elif stdout_attestation.get("status") == "absent":
        raise RouteV2Error("attestation capture state is invalid")
    packet_keys = {
        "action_sha256",
        "attestation_sha256",
        "checks",
        "eligible_success",
        "observed_workspace",
        "run_id",
        "schema",
    }
    if is_ab:
        packet_keys.add("input_attestation_sha256")
    if (
        set(packet) != packet_keys
        or packet.get("schema") != (AB_PACKET_SCHEMA if is_ab else PACKET_SCHEMA)
        or packet.get("run_id") != run_id
        or (
            is_ab
            and packet.get("input_attestation_sha256")
            != _sha256_file(paths["input-attestation"])
        )
    ):
        raise RouteV2Error("packet identity is invalid")
    _validate_projection(packet.get("observed_workspace"))
    raw_checks = packet.get("checks")
    workspace_check = (
        raw_checks.get("workspace_matches_expected")
        if isinstance(raw_checks, dict)
        else None
    )
    expected_observations = {
        "exit_classification": attestation["exit_classification"],
        "final_message": final_attestation["status"],
        "final_schema": attestation["final_schema_validation"],
        "packet_assembly": "PASS",
        "process_launch": "attempted",
        "stdout_capture": stdout_attestation["status"],
        "stdout_ndjson": stdout_attestation["validation"],
        "workspace_capture": (
            attestation["workspace_capture"]
        ),
        "workspace_validation": (
            "not_attempted"
            if attestation.get("workspace_capture") != "PASS"
            else "PASS"
            if workspace_check is True
            else "FAIL"
        ),
    }
    if seal != {
        "attestation_sha256": _sha256_file(paths["attestation"]),
        "cleanup": "PENDING",
        "decision": "PENDING",
        "observations": expected_observations,
        "packet_sha256": _sha256_file(paths["packet"]),
        "run_id": run_id,
        "schema": SEAL_SCHEMA,
    }:
        raise RouteV2Error("observation seal linkage is invalid")
    if packet.get("action_sha256") != _sha256_file(paths["action"]):
        raise RouteV2Error("packet action linkage is invalid")
    if packet.get("attestation_sha256") != _sha256_file(paths["attestation"]):
        raise RouteV2Error("packet attestation linkage is invalid")
    expected_match = (
        attestation.get("workspace_capture") == "PASS"
        and packet.get("observed_workspace") == action.get("expected_workspace")
    )
    checks = packet.get("checks")
    if (
        not isinstance(checks, dict)
        or set(checks)
        != {"exit_zero", "final_schema", "stdout_ndjson", "workspace_matches_expected"}
        or any(type(item) is not bool for item in checks.values())
        or checks.get("workspace_matches_expected") is not expected_match
        or checks.get("exit_zero")
        is not (attestation.get("exit_classification") == "zero")
        or checks.get("stdout_ndjson")
        is not (stdout_attestation.get("validation") == "PASS")
        or checks.get("final_schema")
        is not (attestation.get("final_schema_validation") == "PASS")
    ):
        raise RouteV2Error("workspace decision is invalid")
    eligible = bool(checks) and all(checks.values())
    if packet.get("eligible_success") is not eligible:
        raise RouteV2Error("packet decision is invalid")
    expected_decision = (
        "SUCCESS"
        if eligible
        and final.get("cleanup") == "PASS"
        and final.get("recovery") == "none"
        else "FAILURE"
    )
    if (
        set(final)
        != {
            "cleanup",
            "decision",
            "locator_required",
            "packet_sha256",
            "recovery",
            "run_id",
            "schema",
            "seal_sha256",
        }
        or final.get("schema") != FINAL_SCHEMA
        or final.get("run_id") != run_id
        or final.get("packet_sha256") != _sha256_file(paths["packet"])
        or final.get("seal_sha256") != _sha256_file(paths["seal"])
        or final.get("decision") != expected_decision
        or final.get("cleanup") not in {"PASS", "FAIL"}
        or final.get("recovery") not in {"none", "interrupted_after_seal"}
        or final.get("locator_required") is not (final.get("cleanup") == "FAIL")
    ):
        raise RouteV2Error("final decision linkage is invalid")
    return {
        "claim": "synthetic_layer0_only",
        "decision": expected_decision,
        "raw_content_revalidated": False,
        "run_id": run_id,
        "status": "PASS",
    }


def verify_external_terminal(
    external_root: Path,
    *,
    output_root: Path,
    locator_root: Path,
    run_id: str,
    expected_terminal_sha256: str,
    expected_authorization: str = AUTHORIZATION,
    _trusted_route_root: Path | None = None,
) -> dict[str, Any]:
    run_id = _validate_run_id(run_id)
    expected_authorization = _validate_authorization(expected_authorization)
    if SHA256_RE.fullmatch(expected_terminal_sha256) is None:
        raise RouteV2Error("expected external terminal identity is invalid")
    locator = _locator_path(locator_root, run_id)
    terminal_path = external_root.resolve() / f"{run_id}.terminal.json"
    private_root = _validate_trusted_roots(
        output_root=output_root.resolve(),
        locator=locator,
        external_path=terminal_path,
        run_id=run_id,
        override=_trusted_route_root,
    )
    if (
        _locator_residue(locator)
        or private_root.exists()
        or output_root.resolve().exists()
        or not terminal_path.is_file()
    ):
        raise RouteV2Error("external terminal closeout is incomplete")
    if _sha256_file(terminal_path) != expected_terminal_sha256:
        raise RouteV2Error("external terminal differs from pinned identity")
    value = _load_object(terminal_path)
    _validate_external_value(value, run_id, expected_authorization)
    return {
        "admissible_route_result": False,
        "run_id": run_id,
        "status": "PASS",
    }
