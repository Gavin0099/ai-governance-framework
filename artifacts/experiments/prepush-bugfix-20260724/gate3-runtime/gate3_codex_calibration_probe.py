from __future__ import annotations

import ctypes
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import gate3_codex_calibration as calibration
import gate3_codex_live_canary as live


AUTHORIZATION = calibration.AUTHORIZATION
PRIVATE_SCHEMA = "gate3-codex-calibration-private-decision.v2"
PUBLIC_SCHEMA = "gate3-codex-calibration-probe-receipt.v4"
FAILURE_SCHEMA = "gate3-codex-calibration-probe-failure-receipt.v3"
RUN_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
IMPLEMENTATION_FIELDS = frozenset(
    {
        "calibration_cli_sha256",
        "calibration_collector_sha256",
        "calibration_probe_sha256",
        "calibration_runner_sha256",
        "credential_common_sha256",
        "evidence_chain_sha256",
        "live_canary_sha256",
        "route_plan_sha256",
        "session_launcher_sha256",
        "wrapper_contract_sha256",
    }
)
RESIDUE_CLASSES = frozenset(
    {"private_runtime", "runner_private_runtime", "success_output"}
)
FAILURE_STAGES = frozenset(
    {
        "authorization",
        "private_setup",
        "runner",
        "runner_receipt",
        "collector",
        "frozen_input",
        "private_publication",
        "public_projection",
        "success_publication",
    }
)


class ProbeError(RuntimeError):
    """A fixed-message calibration orchestration failure."""

    def __init__(
        self,
        message: str,
        *,
        residue_classes: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        if not set(residue_classes).issubset(RESIDUE_CLASSES):
            raise ValueError("calibration residue class is invalid")
        self.residue_classes = residue_classes


class PublicationError(ProbeError):
    def __init__(self, *, linked_by_this_call: bool) -> None:
        super().__init__("calibration create-once publication failed")
        self.linked_by_this_call = linked_by_this_call


@dataclass(frozen=True)
class RunnerResult:
    rollout_bytes: bytes
    exit_code: int


@dataclass(frozen=True)
class ProbeResult:
    private_artifact: Path
    public_receipt: Path


AclSetter = Callable[[Path, bool], None]
Runner = Callable[[], RunnerResult]
Publisher = Callable[[Path, bytes], bool]


def _failure_path(success_path: Path) -> Path:
    return success_path.with_name(f"{success_path.name}.failure.json")


def _assert_output_preflight(success_path: Path) -> Path:
    failure_path = _failure_path(success_path)
    if success_path.exists() or failure_path.exists():
        raise ProbeError("calibration output collision")
    if not success_path.parent.is_dir():
        raise ProbeError("calibration output parent is unavailable")
    return failure_path


def _assert_private_parent(parent: Path) -> Path:
    resolved = parent.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        common = Path(os.path.commonpath([resolved, temp_root]))
    except ValueError as error:
        raise ProbeError("calibration private parent is outside user Temp") from error
    if common != temp_root or not resolved.is_dir():
        raise ProbeError("calibration private parent is outside user Temp")
    return resolved


def _windows_current_user_only_acl(path: Path, container: bool) -> None:
    if os.name != "nt":
        raise ProbeError("calibration private ACL backend is unavailable")
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    token = ctypes.c_void_p()
    token_query = 0x0008
    token_user = 1
    dacl_information = 0x00000004
    protected_dacl_information = 0x80000000
    security_descriptor_revision = 1

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
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = ctypes.c_int
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
    advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = ctypes.c_int
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    sid_text = ctypes.c_wchar_p()
    descriptor = ctypes.c_void_p()
    rendered = ctypes.c_wchar_p()
    try:
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(), token_query, ctypes.byref(token)
        ):
            raise OSError(ctypes.get_last_error())
        required = ctypes.c_uint32()
        advapi32.GetTokenInformation(
            token, token_user, None, 0, ctypes.byref(required)
        )
        token_buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token,
            token_user,
            token_buffer,
            required.value,
            ctypes.byref(required),
        ):
            raise OSError(ctypes.get_last_error())
        sid_pointer = ctypes.cast(token_buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not advapi32.ConvertSidToStringSidW(
            sid_pointer, ctypes.byref(sid_text)
        ):
            raise OSError(ctypes.get_last_error())
        inheritance = "OICI" if container else ""
        expected_ace = f"(A;{inheritance};FA;;;{sid_text.value})"
        sddl = f"D:P{expected_ace}"
        descriptor_size = ctypes.c_uint32()
        if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            security_descriptor_revision,
            ctypes.byref(descriptor),
            ctypes.byref(descriptor_size),
        ):
            raise OSError(ctypes.get_last_error())
        if not advapi32.SetFileSecurityW(
            str(path),
            dacl_information | protected_dacl_information,
            descriptor,
        ):
            raise OSError(ctypes.get_last_error())
        observed_size = ctypes.c_uint32()
        advapi32.GetFileSecurityW(
            str(path),
            dacl_information,
            None,
            0,
            ctypes.byref(observed_size),
        )
        observed = ctypes.create_string_buffer(observed_size.value)
        if not advapi32.GetFileSecurityW(
            str(path),
            dacl_information,
            observed,
            observed_size.value,
            ctypes.byref(observed_size),
        ):
            raise OSError(ctypes.get_last_error())
        rendered_size = ctypes.c_uint32()
        if not advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            observed,
            security_descriptor_revision,
            dacl_information,
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
            raise ProbeError("calibration private ACL verification failed")
    except (OSError, ValueError):
        raise ProbeError("calibration private ACL verification failed")
    finally:
        if token.value:
            kernel32.CloseHandle(token)
        if sid_text:
            kernel32.LocalFree(sid_text)
        if descriptor.value:
            kernel32.LocalFree(descriptor)
        if rendered:
            kernel32.LocalFree(rendered)


def _allocate_private_root(parent: Path) -> Path:
    resolved = _assert_private_parent(parent)
    return Path(tempfile.mkdtemp(prefix="gate3-calibration-", dir=resolved))


def _publish_create_once_owned(path: Path, payload: bytes) -> bool:
    if path.exists():
        raise PublicationError(linked_by_this_call=False)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    linked = False
    publication_error: BaseException | None = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            linked = True
        except FileExistsError as error:
            publication_error = error
    except BaseException as error:
        publication_error = error
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
    except OSError as error:
        if publication_error is None:
            publication_error = error
    if publication_error is not None:
        raise PublicationError(linked_by_this_call=linked) from publication_error
    return True


def _private_payload(
    observation: calibration.CalibrationObservation, *, run_id: str
) -> bytes:
    evidence = calibration.private_evidence(observation)
    value = {
        "authorization": AUTHORIZATION,
        **evidence,
        "run_id": run_id,
        "schema": PRIVATE_SCHEMA,
    }
    return live._json_bytes(value)


def _atomic_private_publish(
    root: Path,
    payload: bytes,
    acl_setter: AclSetter,
) -> Path:
    destination = root / "decision.json"
    temporary = root / "decision.json.tmp"
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        acl_setter(temporary, False)
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise ProbeError("calibration private artifact collision") from error
        acl_setter(destination, False)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def _validate_runner_result(value: object) -> RunnerResult:
    if not isinstance(value, RunnerResult):
        raise ProbeError("calibration runner receipt is invalid")
    if (
        not isinstance(value.rollout_bytes, bytes)
        or not isinstance(value.exit_code, int)
        or isinstance(value.exit_code, bool)
    ):
        raise ProbeError("calibration runner receipt is invalid")
    if value.exit_code != 0:
        raise ProbeError("calibration runner failed")
    return value


def _validate_implementation_identity(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != IMPLEMENTATION_FIELDS:
        raise ProbeError("calibration implementation identity is invalid")
    if any(
        not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None
        for digest in value.values()
    ):
        raise ProbeError("calibration implementation identity is invalid")
    return {key: value[key] for key in sorted(value)}


def _success_receipt(
    observation: calibration.CalibrationObservation,
    *,
    run_id: str,
    implementation_identity: dict[str, str],
) -> bytes:
    value = {
        "admission_performed": False,
        "authorization": AUTHORIZATION,
        "calibration": calibration.public_receipt(observation),
        "cleanup": {
            "private_decision_artifact_retained": True,
            "private_temporary_residue": False,
            "status": "PASS",
        },
        "execution": {
            "runner_invocations": 1,
            "runner_retries_by_orchestrator": 0,
            "runner_status": "PASS",
        },
        "implementation": implementation_identity,
        "non_counted": True,
        "private_artifact_disclosure": {
            "digest_published": False,
            "path_published": False,
        },
        "run_id": run_id,
        "schema": PUBLIC_SCHEMA,
        "scoreable": False,
        "success_packet_capable": False,
    }
    payload = live._json_bytes(value)
    if live._privacy_violations(payload):
        raise ProbeError("calibration public receipt contains private material")
    return payload


def _failure_receipt(
    *,
    run_id: str,
    failure_stage: str,
    runner_invocations: int,
    cleanup_status: str,
    residue_classes: list[str],
    implementation_identity: dict[str, str],
) -> bytes:
    if failure_stage not in FAILURE_STAGES:
        raise ProbeError("calibration failure stage is invalid")
    if not set(residue_classes).issubset(RESIDUE_CLASSES):
        raise ProbeError("calibration residue class is invalid")
    value = {
        "admission_performed": False,
        "authorization": AUTHORIZATION,
        "cleanup": {
            "residue_classes": sorted(residue_classes),
            "status": cleanup_status,
        },
        "execution": {
            "runner_invocations": runner_invocations,
            "runner_retries_by_orchestrator": 0,
        },
        "failure_stage": failure_stage,
        "implementation": implementation_identity,
        "non_counted": True,
        "private_artifact_disclosure": {
            "credential_content_retained": False,
            "credential_digest_retained": False,
            "credential_source_path_retained": False,
            "private_artifact_digest_published": False,
            "private_artifact_path_published": False,
            "raw_rollout_retained": False,
        },
        "run_id": run_id,
        "schema": FAILURE_SCHEMA,
        "scoreable": False,
        "success_packet_capable": False,
    }
    payload = live._json_bytes(value)
    if live._privacy_violations(payload):
        raise ProbeError("calibration failure receipt contains private material")
    return payload


def _remove_private_root(root: Path | None) -> None:
    if root is not None and root.exists():
        shutil.rmtree(root)


def _cleanup_private_root(root: Path | None) -> list[str]:
    if root is None:
        return []
    for _attempt in range(2):
        try:
            _remove_private_root(root)
        except OSError:
            continue
        if not root.exists():
            return []
    return ["private_runtime"] if root.exists() else []


def orchestrate(
    success_path: Path,
    *,
    run_id: str,
    authorization: str,
    expected_workspace: str,
    expected_prompt: bytes,
    signed_identity: dict[str, str],
    implementation_identity: dict[str, str],
    private_parent: Path,
    runner: Runner,
    _acl_setter: AclSetter = _windows_current_user_only_acl,
    _publisher: Publisher = _publish_create_once_owned,
) -> ProbeResult:
    """Run one injected calibration invocation; never perform admission."""

    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ProbeError("calibration run id is invalid")
    success_path = success_path.resolve()
    failure_path = _assert_output_preflight(success_path)
    private_parent = _assert_private_parent(private_parent)
    implementation_identity = _validate_implementation_identity(
        implementation_identity
    )
    try:
        if Path(os.path.commonpath([success_path, private_parent])) == private_parent:
            raise ProbeError("calibration public output overlaps private Temp")
    except ValueError:
        pass
    failure_stage = "authorization"
    runner_invocations = 0
    private_root: Path | None = None
    private_artifact: Path | None = None
    public_payload: bytes | None = None
    success_owned = False
    succeeded = False
    try:
        if authorization != AUTHORIZATION:
            raise ProbeError("calibration authorization is invalid")
        failure_stage = "frozen_input"
        if (
            not isinstance(expected_workspace, str)
            or not expected_workspace.strip()
            or not isinstance(expected_prompt, bytes)
            or not expected_prompt
        ):
            raise ProbeError("calibration frozen input is invalid")
        calibration._validate_signed_identity(signed_identity)
        failure_stage = "private_setup"
        private_root = _allocate_private_root(private_parent)
        _acl_setter(private_root, True)
        failure_stage = "runner"
        runner_invocations = 1
        result = runner()
        failure_stage = "runner_receipt"
        result = _validate_runner_result(result)
        failure_stage = "collector"
        observation = calibration.collect(
            result.rollout_bytes,
            expected_workspace=expected_workspace,
            expected_prompt=expected_prompt,
            signed_identity=signed_identity,
        )
        if observation.source_status != "ok":
            raise ProbeError("calibration rollout source is invalid")
        failure_stage = "private_publication"
        private_artifact = _atomic_private_publish(
            private_root,
            _private_payload(observation, run_id=run_id),
            _acl_setter,
        )
        failure_stage = "public_projection"
        public_payload = _success_receipt(
            observation,
            run_id=run_id,
            implementation_identity=implementation_identity,
        )
        if set(private_root.iterdir()) != {private_artifact}:
            raise ProbeError("calibration private temporary cleanup failed")
        failure_stage = "success_publication"
        try:
            success_owned = _publisher(success_path, public_payload) is True
        except PublicationError as error:
            success_owned = error.linked_by_this_call
            raise
        if not success_owned:
            raise ProbeError("calibration publication ownership is invalid")
        succeeded = True
        return ProbeResult(
            private_artifact=private_artifact,
            public_receipt=success_path,
        )
    except Exception as error:
        if isinstance(error, ProbeError):
            reported = error
        else:
            reported = ProbeError("calibration orchestration failed")
        residue_classes = _cleanup_private_root(private_root)
        if isinstance(reported, ProbeError):
            residue_classes.extend(reported.residue_classes)
        if success_owned and success_path.exists():
            try:
                success_path.unlink()
            except OSError:
                pass
        if success_path.exists():
            residue_classes.append("success_output")
        failure_payload = _failure_receipt(
            run_id=run_id,
            failure_stage=failure_stage,
            runner_invocations=runner_invocations,
            cleanup_status="FAIL" if residue_classes else "PASS",
            residue_classes=residue_classes,
            implementation_identity=implementation_identity,
        )
        if _publisher(failure_path, failure_payload) is not True:
            raise ProbeError("calibration failure publication ownership is invalid")
        raise reported
    finally:
        if not succeeded and private_root is not None and private_root.exists():
            _cleanup_private_root(private_root)
