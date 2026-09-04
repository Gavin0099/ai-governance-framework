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
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import socket
import stat
from typing import Callable, Mapping, Protocol
import uuid

from governance_tools import solo_r2_controller_state as controller_state
from governance_tools.solo_r2_attempt_execution import (
    PairLedgerLock,
    PreAttemptExecutionCoordinator,
    PreAttemptValidation,
)
from governance_tools.solo_r2_attempt_materialization import (
    FrozenGitMaterializer,
    HostLocalEndpointDisposition,
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
    ExecutionPolicy,
    NativeCodexExecBackend,
    NativeExecutionPreparation,
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
HOST_LOCAL_OBSERVATION_UNAVAILABLE = "HOST_LOCAL_OBSERVATION_UNAVAILABLE / STOP"
READY_BEFORE_ATTEMPT = "R2_READY_BEFORE_ATTEMPT_HANDLE_CREATION"
QUALIFICATION_STATUS = "R2_NON_EXPOSURE_OK"
BOUNDARY_SCHEMA = "solo-r2-pre-exposure-boundary/v3"
_LOWER_HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_CHALLENGE = re.compile(r"[0-9a-f]{32}\Z")
_PROBE_SCRIPT_RELPATH = "qualification-boundary-probe.ps1"
_PROBE_CONFIG_RELPATH = "qualification-boundary-config.json"
_CREDENTIAL_SENTINEL_NAME = "qualification-credential-sentinel.txt"
_PROBE_TIMEOUT_MILLISECONDS = 5_000


_BOUNDARY_PROBE_SCRIPT = b"""param(
    [Parameter(Mandatory=$true)][string]$ConfigPath
)
$ErrorActionPreference = 'Stop'
$config = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($ConfigPath, [Text.Encoding]::UTF8))

function Invoke-TcpProbe([string]$HostName, [int]$Port, [string]$Payload) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        try {
            $pending = $client.BeginConnect($HostName, $Port, $null, $null)
            $completed = $pending.AsyncWaitHandle.WaitOne([int]$config.timeout_milliseconds)
            $pending.AsyncWaitHandle.Close()
            if (-not $completed) {
                return 'TIMEOUT'
            }
            try {
                $client.EndConnect($pending)
            } catch [Net.Sockets.SocketException] {
                return 'CONNECTION_FAILED'
            }
            if ($Payload.Length -gt 0) {
                $bytes = [Text.Encoding]::ASCII.GetBytes($Payload)
                $stream = $client.GetStream()
                $stream.Write($bytes, 0, $bytes.Length)
                $stream.Flush()
            }
            return 'CONNECTED'
        } catch [Net.Sockets.SocketException] {
            return 'CONNECTION_FAILED'
        } catch {
            return 'ERROR'
        }
    } finally {
        $client.Dispose()
    }
}

try {
    $challenge = [IO.File]::ReadAllText([string]$config.challenge_path, [Text.Encoding]::ASCII)
    $challengeRead = 'READ'
} catch {
    $challenge = 'UNAVAILABLE'
    $challengeRead = 'ERROR'
}

try {
    $whoamiRaw = [string](& ([string]$config.whoami_path) /user /fo csv /nh 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'whoami failed' }
    $whoamiRow = $whoamiRaw | ConvertFrom-Csv -Header User,Sid
    $principalSid = [string]$whoamiRow.Sid
    $principalObservation = 'OBSERVED'
} catch {
    $principalSid = 'UNAVAILABLE'
    $principalObservation = 'ERROR'
}

try {
    [void][IO.File]::ReadAllBytes([string]$config.credential_sentinel_path)
    $credentialRead = 'VISIBLE'
} catch {
    if ($_.Exception.HResult -eq -2147024891 -or $_.Exception -is [UnauthorizedAccessException] -or $_.Exception -is [Security.SecurityException]) {
        $credentialRead = 'DENIED'
    } else {
        $credentialRead = 'ERROR'
    }
}

$offHostConnect = Invoke-TcpProbe ([string]$config.off_host_host) ([int]$config.off_host_port) ''
$hostLocalConnect = Invoke-TcpProbe ([string]$config.host_local_host) ([int]$config.host_local_port) $challenge

[ordered]@{
    challenge = $challenge
    challenge_read = $challengeRead
    credential_read = $credentialRead
    host_local_connect = $hostLocalConnect
    off_host_connect = $offHostConnect
    principal_observation = $principalObservation
    principal_sid = $principalSid
    status = 'R2_NON_EXPOSURE_OK'
} | ConvertTo-Json -Compress
"""


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
class OffHostControlEndpoint:
    """Owner-supplied literal IP endpoint used only as a positive control."""

    host: str
    port: int

    def validate(self) -> None:
        if not isinstance(self.host, str):
            _fail(PAIR_INVALID)
        try:
            address = ipaddress.ip_address(self.host)
        except (TypeError, ValueError):
            _fail(PAIR_INVALID)
        if (
            type(self.port) is not int
            or not 1 <= self.port <= 65_535
            or address.is_loopback
            or address.is_unspecified
            or address.is_multicast
        ):
            _fail(PAIR_INVALID)

    @property
    def display(self) -> str:
        self.validate()
        return (
            f"[{self.host}]:{self.port}"
            if ":" in self.host
            else f"{self.host}:{self.port}"
        )


@dataclass(frozen=True)
class BoundaryProbeIdentity:
    script_relative_path: str
    script_byte_length: int
    script_sha256: str
    powershell_path: str
    powershell_byte_length: int
    powershell_sha256: str

    def validate(self) -> None:
        if not isinstance(self.script_relative_path, str):
            _fail(PAIR_INVALID)
        pure = PurePosixPath(self.script_relative_path)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != _PROBE_SCRIPT_RELPATH
            or type(self.script_byte_length) is not int
            or self.script_byte_length != len(_BOUNDARY_PROBE_SCRIPT)
            or self.script_sha256 != _sha256(_BOUNDARY_PROBE_SCRIPT)
            or not isinstance(self.powershell_path, str)
            or os.path.normcase(self.powershell_path)
            != os.path.normcase(str(WINDOWS_POWERSHELL_PATH))
            or type(self.powershell_byte_length) is not int
            or self.powershell_byte_length != WINDOWS_POWERSHELL_BYTE_LENGTH
            or self.powershell_sha256 != WINDOWS_POWERSHELL_SHA256
        ):
            _fail(PAIR_INVALID)


@dataclass(frozen=True)
class PreExposureBoundaryEvidence:
    """Digest-bound result of the already-adopted pre-ID boundary checks."""

    evidence_sha256: str
    credential_sentinel_visible: bool
    network_tcp_egress_denied: bool
    host_local: HostLocalIsolation
    off_host_control_endpoint: OffHostControlEndpoint
    qualification_probe: BoundaryProbeIdentity

    def validate(self) -> None:
        self.host_local.validate()
        self.off_host_control_endpoint.validate()
        self.qualification_probe.validate()
        if (
            _LOWER_HEX_64.fullmatch(self.evidence_sha256) is None
            or self.credential_sentinel_visible is not False
            or self.network_tcp_egress_denied is not True
        ):
            _fail(PAIR_INVALID)

    @classmethod
    def create_once(
        cls,
        path: Path | str,
        *,
        credential_sentinel_visible: bool,
        network_tcp_egress_denied: bool,
        host_local: HostLocalIsolation,
        off_host_control_endpoint: OffHostControlEndpoint,
        qualification_probe: BoundaryProbeIdentity,
    ) -> "PreExposureBoundaryEvidence":
        target = Path(path)
        host_local.validate()
        off_host_control_endpoint.validate()
        qualification_probe.validate()
        if (
            not target.is_absolute()
            or credential_sentinel_visible is not False
            or network_tcp_egress_denied is not True
        ):
            _fail(PAIR_INVALID)
        _closed_directory(target.parent)
        if os.path.lexists(target):
            _fail(PAIR_INVALID)
        payload = json.dumps(
            {
                "schema": BOUNDARY_SCHEMA,
                "credential_sentinel_visible": credential_sentinel_visible,
                "network_tcp_egress_denied": network_tcp_egress_denied,
                "host_local_endpoint_reachable": (
                    host_local.host_local_endpoint_reachable.value
                ),
                "observed_host_listener_count": host_local.observed_host_listener_count,
                "runtime_endpoint_inputs": list(host_local.runtime_endpoint_inputs),
                "off_host_control_endpoint": {
                    "host": off_host_control_endpoint.host,
                    "port": off_host_control_endpoint.port,
                },
                "qualification_probe": {
                    "script_relative_path": qualification_probe.script_relative_path,
                    "script_byte_length": qualification_probe.script_byte_length,
                    "script_sha256": qualification_probe.script_sha256,
                    "powershell_path": qualification_probe.powershell_path,
                    "powershell_byte_length": qualification_probe.powershell_byte_length,
                    "powershell_sha256": qualification_probe.powershell_sha256,
                },
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii") + b"\n"
        try:
            with target.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            _fail()
        return cls.load(target, expected_sha256=_sha256(payload))

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
            "off_host_control_endpoint",
            "qualification_probe",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected
            or value["schema"] != BOUNDARY_SCHEMA
        ):
            _fail(PAIR_INVALID)
        runtime_inputs = value["runtime_endpoint_inputs"]
        endpoint = value["off_host_control_endpoint"]
        probe = value["qualification_probe"]
        if (
            not isinstance(runtime_inputs, list)
            or any(not isinstance(item, str) for item in runtime_inputs)
            or not isinstance(endpoint, dict)
            or set(endpoint) != {"host", "port"}
            or not isinstance(probe, dict)
            or set(probe)
            != {
                "script_relative_path",
                "script_byte_length",
                "script_sha256",
                "powershell_path",
                "powershell_byte_length",
                "powershell_sha256",
            }
        ):
            _fail(PAIR_INVALID)
        try:
            host_local_disposition = HostLocalEndpointDisposition(
                value["host_local_endpoint_reachable"]
            )
        except (TypeError, ValueError):
            _fail(PAIR_INVALID)
        result = cls(
            evidence_sha256=expected_sha256,
            credential_sentinel_visible=value["credential_sentinel_visible"],
            network_tcp_egress_denied=value["network_tcp_egress_denied"],
            host_local=HostLocalIsolation(
                host_local_disposition,
                value["observed_host_listener_count"],
                tuple(runtime_inputs),
            ),
            off_host_control_endpoint=OffHostControlEndpoint(
                endpoint["host"], endpoint["port"]
            ),
            qualification_probe=BoundaryProbeIdentity(
                probe["script_relative_path"],
                probe["script_byte_length"],
                probe["script_sha256"],
                probe["powershell_path"],
                probe["powershell_byte_length"],
                probe["powershell_sha256"],
            ),
        )
        result.validate()
        return result


@dataclass(frozen=True)
class HostLocalTcpObservation:
    """Raw facts from one qualification-owned same-host TCP probe.

    ``NO_CONNECTION`` is a completed observation after the child command has
    returned a structured ``CONNECTION_FAILED`` result.  It is deliberately
    distinct from ``TIMEOUT``: a timeout can never establish ``BLOCKED``.
    """

    expected_nonce: str
    child_connect: str
    listener_outcome: str
    listener_payload: str | None
    launcher_pre_reachable: bool
    launcher_post_reachable: bool
    same_child_required_probes_passed: bool

    def classify(self) -> HostLocalEndpointDisposition:
        if (
            not isinstance(self.expected_nonce, str)
            or _CHALLENGE.fullmatch(self.expected_nonce) is None
            or not isinstance(self.child_connect, str)
            or not isinstance(self.listener_outcome, str)
            or (
                self.listener_payload is not None
                and not isinstance(self.listener_payload, str)
            )
            or self.launcher_pre_reachable is not True
            or self.launcher_post_reachable is not True
            or self.same_child_required_probes_passed is not True
        ):
            return HostLocalEndpointDisposition.UNRESOLVED
        if (
            self.listener_outcome == "PAYLOAD_RECEIVED"
            and self.listener_payload == self.expected_nonce
            and self.child_connect == "CONNECTED"
        ):
            return HostLocalEndpointDisposition.REACHABLE
        if (
            self.listener_outcome == "NO_CONNECTION"
            and self.listener_payload is None
            and self.child_connect == "CONNECTION_FAILED"
        ):
            return HostLocalEndpointDisposition.BLOCKED
        return HostLocalEndpointDisposition.UNRESOLVED


@dataclass(frozen=True)
class PreExposureBoundaryObservation:
    credential_read: str
    launcher_egress_pre_reachable: bool
    child_egress_connect: str
    launcher_egress_post_reachable: bool
    host_local_tcp: HostLocalTcpObservation
    observed_host_listener_count: int | None
    runtime_endpoint_inputs: tuple[str, ...]
    off_host_control_endpoint: OffHostControlEndpoint
    qualification_probe: BoundaryProbeIdentity


class BoundaryObservationSource(Protocol):
    def __call__(
        self,
        *,
        result: NativeExecutionResult,
        generation: SandboxGenerationFingerprint,
    ) -> PreExposureBoundaryObservation: ...


class PreExposureBoundaryEvidenceProducer:
    """Compose typed child/launcher observations into create-once evidence."""

    def __init__(
        self,
        *,
        evidence_path: Path | str,
        observation_source: BoundaryObservationSource | None = None,
    ) -> None:
        self.evidence_path = Path(evidence_path)
        self.observation_source = observation_source
        self._used = False
        if not self.evidence_path.is_absolute() or (
            observation_source is not None and not callable(observation_source)
        ):
            _fail(PAIR_INVALID)

    def produce(
        self,
        *,
        result: NativeExecutionResult,
        generation: SandboxGenerationFingerprint,
        observation: PreExposureBoundaryObservation | None = None,
    ) -> PreExposureBoundaryEvidence:
        if self._used:
            _fail(PAIR_INVALID)
        self._used = True
        if observation is None:
            if self.observation_source is None:
                _fail(PAIR_INVALID)
            try:
                observation = self.observation_source(
                    result=result, generation=generation
                )
            except RuntimeWindowError:
                raise
            except Exception:
                _fail()
        elif self.observation_source is not None:
            _fail(PAIR_INVALID)
        if not isinstance(observation, PreExposureBoundaryObservation):
            _fail(PAIR_INVALID)
        if (
            observation.credential_read != "DENIED"
            or observation.launcher_egress_pre_reachable is not True
            or observation.child_egress_connect != "BLOCKED"
            or observation.launcher_egress_post_reachable is not True
            or not isinstance(observation.runtime_endpoint_inputs, tuple)
            or observation.runtime_endpoint_inputs
        ):
            _fail(PAIR_INVALID)
        if not isinstance(observation.host_local_tcp, HostLocalTcpObservation):
            _fail(HOST_LOCAL_OBSERVATION_UNAVAILABLE)
        host_local_disposition = observation.host_local_tcp.classify()
        if host_local_disposition is HostLocalEndpointDisposition.UNRESOLVED:
            _fail(HOST_LOCAL_OBSERVATION_UNAVAILABLE)
        if (
            type(observation.observed_host_listener_count) is not int
            or observation.observed_host_listener_count != 0
        ):
            _fail(PAIR_INVALID)
        return PreExposureBoundaryEvidence.create_once(
            self.evidence_path,
            credential_sentinel_visible=False,
            network_tcp_egress_denied=True,
            host_local=HostLocalIsolation(
                host_local_disposition,
                observation.observed_host_listener_count,
                observation.runtime_endpoint_inputs,
            ),
            off_host_control_endpoint=observation.off_host_control_endpoint,
            qualification_probe=observation.qualification_probe,
        )


class HostLocalObservationUnavailable:
    """Compatibility stop until same-host TCP behavior is resolved."""

    def __call__(
        self,
        *,
        result: NativeExecutionResult,
        generation: SandboxGenerationFingerprint,
    ) -> PreExposureBoundaryObservation:
        del result, generation
        _fail(HOST_LOCAL_OBSERVATION_UNAVAILABLE)


class LocalBoundaryListener(Protocol):
    host: str
    port: int

    def launcher_round_trip(self, payload: str, *, timeout_seconds: float) -> bool: ...

    def observe_child(self) -> tuple[str, str | None]: ...

    def close_and_count(self) -> int: ...


class BoundaryMachineTransport(Protocol):
    def open_local_listener(self) -> LocalBoundaryListener: ...

    def can_connect(
        self, endpoint: OffHostControlEndpoint, *, timeout_seconds: float
    ) -> bool: ...


class _SocketBoundaryListener:
    """Run-owned loopback listener; backlog observation avoids helper threads."""

    def __init__(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            server.bind(("127.0.0.1", 0))
            server.listen(3)
        except OSError:
            server.close()
            _fail()
        self._server = server
        self.host = "127.0.0.1"
        self.port = int(server.getsockname()[1])
        self._closed = False

    @staticmethod
    def _payload(
        connection: socket.socket, *, timeout_seconds: float
    ) -> tuple[str, str | None]:
        connection.settimeout(timeout_seconds)
        chunks: list[bytes] = []
        size = 0
        try:
            while True:
                block = connection.recv(65 - size)
                if not block:
                    break
                chunks.append(block)
                size += len(block)
                if size >= 65:
                    break
        except TimeoutError:
            return "TIMEOUT", None
        except OSError:
            return "ERROR", None
        payload = b"".join(chunks)
        try:
            text = payload.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            return "ERROR", None
        return "PAYLOAD_RECEIVED", text

    def _accept(self, *, timeout_seconds: float) -> tuple[str, str | None]:
        try:
            self._server.settimeout(timeout_seconds)
            connection, _ = self._server.accept()
        except TimeoutError:
            return "TIMEOUT", None
        except OSError:
            return "ERROR", None
        with connection:
            return self._payload(connection, timeout_seconds=timeout_seconds)

    def launcher_round_trip(self, payload: str, *, timeout_seconds: float) -> bool:
        if self._closed or _CHALLENGE.fullmatch(payload) is None:
            return False
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=timeout_seconds
            ) as client:
                client.sendall(payload.encode("ascii"))
                client.shutdown(socket.SHUT_WR)
        except OSError:
            return False
        outcome, received = self._accept(timeout_seconds=timeout_seconds)
        return outcome == "PAYLOAD_RECEIVED" and received == payload

    def observe_child(self) -> tuple[str, str | None]:
        """Observe the backlog after the terminated child command returns.

        No pending connection is a completed ``NO_CONNECTION`` observation;
        a timeout while reading an accepted connection remains ``TIMEOUT``.
        """
        if self._closed:
            return "ERROR", None
        try:
            self._server.setblocking(False)
            connection, _ = self._server.accept()
        except BlockingIOError:
            return "NO_CONNECTION", None
        except OSError:
            return "ERROR", None
        with connection:
            return self._payload(
                connection, timeout_seconds=_PROBE_TIMEOUT_MILLISECONDS / 1_000
            )

    def close_and_count(self) -> int:
        if self._closed:
            _fail()
        try:
            self._server.close()
        except OSError:
            _fail()
        self._closed = True
        if self._server.fileno() != -1:
            _fail()
        return 0


class WindowsSocketBoundaryTransport:
    """Concrete bounded socket transport used by the production producer."""

    def open_local_listener(self) -> LocalBoundaryListener:
        if os.name != "nt":
            _fail()
        return _SocketBoundaryListener()

    def can_connect(
        self, endpoint: OffHostControlEndpoint, *, timeout_seconds: float
    ) -> bool:
        endpoint.validate()
        if os.name != "nt" or timeout_seconds <= 0:
            _fail()
        try:
            with socket.create_connection(
                (endpoint.host, endpoint.port), timeout=timeout_seconds
            ):
                return True
        except OSError:
            return False


class BoundaryProbeExecute(Protocol):
    def __call__(
        self, *, prompt: bytes, output_schema: Mapping[str, object]
    ) -> NativeExecutionResult: ...


class MachineBackedBoundaryProbe:
    """Run one fixed child probe and compose its launcher-side observations."""

    def __init__(
        self,
        *,
        off_host_control_endpoint: OffHostControlEndpoint,
        credential_sentinel_path: Path | str,
        transport: BoundaryMachineTransport | None = None,
    ) -> None:
        off_host_control_endpoint.validate()
        sentinel = Path(credential_sentinel_path)
        if not sentinel.is_absolute() or sentinel.name != _CREDENTIAL_SENTINEL_NAME:
            _fail(PAIR_INVALID)
        self.off_host_control_endpoint = off_host_control_endpoint
        self.credential_sentinel_path = sentinel
        self.transport = (
            WindowsSocketBoundaryTransport() if transport is None else transport
        )

    @staticmethod
    def _capture_regular(path: Path) -> tuple[int, str]:
        try:
            value = os.lstat(path)
            resolved = path.resolve(strict=True)
            payload = path.read_bytes()
        except OSError:
            _fail()
        if (
            os.path.normcase(str(path)) != os.path.normcase(str(resolved))
            or not stat.S_ISREG(value.st_mode)
            or stat.S_ISLNK(value.st_mode)
            or bool(getattr(value, "st_file_attributes", 0) & 0x400)
        ):
            _fail(PAIR_INVALID)
        if path.name == _CREDENTIAL_SENTINEL_NAME:
            try:
                text = payload.decode("ascii", errors="strict")
            except UnicodeDecodeError:
                _fail(PAIR_INVALID)
            if _CHALLENGE.fullmatch(text) is None:
                _fail(PAIR_INVALID)
        return len(payload), _sha256(payload)

    @staticmethod
    def _schema() -> dict[str, object]:
        statuses = {
            "challenge_read": ("READ", "ERROR"),
            "credential_read": ("DENIED", "VISIBLE", "ERROR"),
            "host_local_connect": (
                "CONNECTED",
                "CONNECTION_FAILED",
                "TIMEOUT",
                "ERROR",
            ),
            "off_host_connect": (
                "CONNECTED",
                "CONNECTION_FAILED",
                "TIMEOUT",
                "ERROR",
            ),
            "principal_observation": ("OBSERVED", "ERROR"),
        }
        properties: dict[str, object] = {
            "challenge": {"type": "string"},
            "principal_sid": {"type": "string"},
            "status": {"type": "string", "const": QUALIFICATION_STATUS},
        }
        properties.update(
            {
                key: {"type": "string", "enum": list(values)}
                for key, values in statuses.items()
            }
        )
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(properties),
            "additionalProperties": False,
        }

    @staticmethod
    def _quote_powershell(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _read_command_result(
        result: NativeExecutionResult,
        *,
        configured_catalog: ToolCatalog,
        expected_command: str,
    ) -> dict[str, object]:
        metrics = validate_execution_result(result, configured_catalog)
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
        output = item.get("aggregated_output")
        if (
            item.get("status") != "completed"
            or item.get("exit_code") != 0
            or item.get("command") != expected_command
            or not isinstance(output, str)
        ):
            _fail(PAIR_INVALID)
        try:
            observed = json.loads(output)
        except json.JSONDecodeError:
            _fail(PAIR_INVALID)
        expected_keys = set(MachineBackedBoundaryProbe._schema()["required"])
        if (
            not isinstance(observed, dict)
            or set(observed) != expected_keys
            or final != observed
            or output.strip()
            != json.dumps(
                observed,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        ):
            _fail(PAIR_INVALID)
        return observed

    def run(
        self,
        *,
        workspace: Path,
        challenge: str,
        challenge_path: Path,
        whoami: PinnedExecutable,
        generation: SandboxGenerationFingerprint,
        configured_catalog: ToolCatalog,
        execute: BoundaryProbeExecute,
    ) -> tuple[NativeExecutionResult, PreExposureBoundaryObservation]:
        if (
            _CHALLENGE.fullmatch(challenge) is None
            or challenge_path != workspace / "qualification-challenge.txt"
            or set(workspace.iterdir()) != {challenge_path}
        ):
            _fail(PAIR_INVALID)
        try:
            self.credential_sentinel_path.relative_to(workspace)
        except ValueError:
            pass
        else:
            _fail(PAIR_INVALID)
        sentinel_identity = self._capture_regular(self.credential_sentinel_path)
        try:
            powershell = PinnedExecutable.capture(WINDOWS_POWERSHELL_PATH)
        except Exception:
            _fail()
        if (
            powershell.byte_length != WINDOWS_POWERSHELL_BYTE_LENGTH
            or powershell.sha256 != WINDOWS_POWERSHELL_SHA256
        ):
            _fail(PAIR_INVALID)
        whoami.verify()
        probe_identity = BoundaryProbeIdentity(
            _PROBE_SCRIPT_RELPATH,
            len(_BOUNDARY_PROBE_SCRIPT),
            _sha256(_BOUNDARY_PROBE_SCRIPT),
            str(powershell.path),
            powershell.byte_length,
            powershell.sha256,
        )
        probe_identity.validate()
        listener = self.transport.open_local_listener()
        local_pre = False
        local_post = False
        egress_pre = False
        egress_post = False
        listener_outcome = "UNOBSERVED"
        listener_payload: str | None = None
        listener_count: int | None = None
        script_path = workspace / _PROBE_SCRIPT_RELPATH
        config_path = workspace / _PROBE_CONFIG_RELPATH
        script_written = False
        config_written = False
        cleanup_failed = False
        result: NativeExecutionResult | None = None
        try:
            local_pre = listener.launcher_round_trip(
                secrets.token_hex(16),
                timeout_seconds=_PROBE_TIMEOUT_MILLISECONDS / 1_000,
            )
            egress_pre = self.transport.can_connect(
                self.off_host_control_endpoint,
                timeout_seconds=_PROBE_TIMEOUT_MILLISECONDS / 1_000,
            )
            if local_pre is not True or egress_pre is not True:
                _fail(HOST_LOCAL_OBSERVATION_UNAVAILABLE)
            config_payload = json.dumps(
                {
                    "challenge_path": str(challenge_path),
                    "credential_sentinel_path": str(self.credential_sentinel_path),
                    "host_local_host": listener.host,
                    "host_local_port": listener.port,
                    "off_host_host": self.off_host_control_endpoint.host,
                    "off_host_port": self.off_host_control_endpoint.port,
                    "timeout_milliseconds": _PROBE_TIMEOUT_MILLISECONDS,
                    "whoami_path": str(whoami.path),
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
            try:
                with script_path.open("xb") as stream:
                    stream.write(_BOUNDARY_PROBE_SCRIPT)
                    stream.flush()
                    os.fsync(stream.fileno())
                script_written = True
                with config_path.open("xb") as stream:
                    stream.write(config_payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                config_written = True
            except OSError:
                _fail()
            command = " ".join(
                (
                    "&",
                    self._quote_powershell(str(powershell.path)),
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    self._quote_powershell(str(script_path)),
                    "-ConfigPath",
                    self._quote_powershell(str(config_path)),
                )
            )
            prompt = (
                "This is a runtime qualification probe, not a repository task.\n"
                "Use the shell tool exactly once and execute exactly this command:\n"
                f"{command}\n"
                "Return only the exact JSON object printed by the command. Do not run "
                "any other command or inspect any other file.\n"
            ).encode("utf-8")
            result = execute(prompt=prompt, output_schema=self._schema())
            listener_outcome, listener_payload = listener.observe_child()
            local_post = listener.launcher_round_trip(
                secrets.token_hex(16),
                timeout_seconds=_PROBE_TIMEOUT_MILLISECONDS / 1_000,
            )
            egress_post = self.transport.can_connect(
                self.off_host_control_endpoint,
                timeout_seconds=_PROBE_TIMEOUT_MILLISECONDS / 1_000,
            )
            try:
                script_unchanged = script_path.read_bytes() == _BOUNDARY_PROBE_SCRIPT
                config_unchanged = config_path.read_bytes() == config_payload
            except OSError:
                _fail()
            if not script_unchanged or not config_unchanged:
                _fail(PAIR_INVALID)
            observed = self._read_command_result(
                result,
                configured_catalog=configured_catalog,
                expected_command=command,
            )
        finally:
            try:
                listener_count = listener.close_and_count()
            except Exception:
                cleanup_failed = True
            for path, written in (
                (config_path, config_written),
                (script_path, script_written),
            ):
                if written:
                    try:
                        path.unlink()
                    except OSError:
                        cleanup_failed = True
            if cleanup_failed:
                _fail()
        if result is None or listener_count != 0:
            _fail()
        if (
            self._capture_regular(self.credential_sentinel_path) != sentinel_identity
            or powershell.verify() != powershell.path
            or whoami.verify() != whoami.path
        ):
            _fail(PAIR_INVALID)
        required_probe_pass = (
            observed["status"] == QUALIFICATION_STATUS
            and observed["challenge_read"] == "READ"
            and observed["challenge"] == challenge
            and observed["principal_observation"] == "OBSERVED"
            and isinstance(observed["principal_sid"], str)
            and observed["principal_sid"].lower() == generation.offline_sid.lower()
            and observed["credential_read"] == "DENIED"
            and observed["off_host_connect"] == "CONNECTION_FAILED"
        )
        child_egress = (
            "BLOCKED"
            if observed["off_host_connect"] == "CONNECTION_FAILED"
            else str(observed["off_host_connect"])
        )
        observation = PreExposureBoundaryObservation(
            str(observed["credential_read"]),
            egress_pre,
            child_egress,
            egress_post,
            HostLocalTcpObservation(
                challenge,
                str(observed["host_local_connect"]),
                listener_outcome,
                listener_payload,
                local_pre,
                local_post,
                required_probe_pass,
            ),
            listener_count,
            (),
            self.off_host_control_endpoint,
            probe_identity,
        )
        return result, observation


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
class RuntimeFreezeCandidate:
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
    runtime_quiescent: bool


@dataclass(frozen=True)
class RuntimeFreeze(RuntimeFreezeCandidate):
    boundary_evidence_sha256: str


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
        boundary_evidence: PreExposureBoundaryEvidence | None = None,
        assert_runtime_quiescent: Callable[[], None],
    ) -> None:
        self.backend = backend
        self.repository_probe = repository_probe
        self.qualification_helper = qualification_helper
        self.generation_probe = generation_probe
        self.pair_lock = pair_lock
        self.boundary_evidence = boundary_evidence
        self.assert_runtime_quiescent = assert_runtime_quiescent

    def capture_candidate(self) -> RuntimeFreezeCandidate:
        self.assert_runtime_quiescent()
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
        result = RuntimeFreezeCandidate(
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
            True,
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

    def finalize(
        self,
        candidate: RuntimeFreezeCandidate,
        boundary_evidence: PreExposureBoundaryEvidence,
    ) -> RuntimeFreeze:
        boundary_evidence.validate()
        if (
            self.boundary_evidence is not None
            and self.boundary_evidence != boundary_evidence
        ):
            _fail(PAIR_INVALID)
        if self.capture_candidate() != candidate:
            _fail(SAME_MACHINE_WINDOW_REJECTED)
        self.boundary_evidence = boundary_evidence
        return RuntimeFreeze(
            **candidate.__dict__,
            boundary_evidence_sha256=boundary_evidence.evidence_sha256,
        )

    def capture(self) -> RuntimeFreeze:
        if self.boundary_evidence is None:
            _fail(PAIR_INVALID)
        return self.finalize(self.capture_candidate(), self.boundary_evidence)

    def assert_unchanged(self, expected: RuntimeFreeze) -> None:
        if (
            self.boundary_evidence is None
            or self.boundary_evidence.evidence_sha256
            != expected.boundary_evidence_sha256
            or self.capture_candidate()
            != RuntimeFreezeCandidate(
                **{
                    key: value
                    for key, value in expected.__dict__.items()
                    if key != "boundary_evidence_sha256"
                }
            )
        ):
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


@dataclass(frozen=True)
class ProvisioningExecutionPreparation:
    """Non-counted native input with no pre-existing boundary assertion."""

    runtime_identity: RuntimeIdentity
    execution_policy: ExecutionPolicy
    configured_tool_inventory: tuple[Mapping[str, object], ...]
    catalog_sha256: str
    sandbox_principal: str
    sandbox_account_generation: str
    task_exposure_state: str = "NONE"


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
        boundary_producer: PreExposureBoundaryEvidenceProducer,
        boundary_probe: MachineBackedBoundaryProbe,
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
        self.boundary_producer = boundary_producer
        self.boundary_probe = boundary_probe
        self.boundary_evidence: PreExposureBoundaryEvidence | None = None
        self.generation_probe = generation_probe
        self._freeze: SandboxGenerationFingerprint | None = None
        self._provisioned = False
        self._canary_used = False
        self._prepared_ordinals: list[int] = []
        runtime_identity.validate()
        whoami.verify()
        if (
            not isinstance(boundary_producer, PreExposureBoundaryEvidenceProducer)
            or boundary_producer.observation_source is not None
            or not isinstance(boundary_probe, MachineBackedBoundaryProbe)
            or not callable(generation_probe)
            or len(
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

    def _pre_boundary_preparation(
        self, generation: SandboxGenerationFingerprint
    ) -> ProvisioningExecutionPreparation:
        """Build only the seven fields consumed by native dispatch."""

        catalog = self.native_backend.configured_catalog
        return ProvisioningExecutionPreparation(
            self.runtime_identity,
            REQUIRED_EXECUTION_POLICY,
            catalog.public_inventory(),
            catalog.catalog_sha256,
            generation.offline_sid,
            generation.value,
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
        if not context or any(output.iterdir()) or any(workspace.iterdir()):
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
                prepared_arm=self._pre_boundary_preparation(generation),
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
        if any(self.qualification_output.iterdir()) or any(
            self.qualification_workspace.iterdir()
        ):
            _fail(PAIR_INVALID)
        challenge = secrets.token_hex(16)
        if _CHALLENGE.fullmatch(challenge) is None:
            _fail()
        challenge_path = self.qualification_workspace / "qualification-challenge.txt"
        challenge_payload = challenge.encode("ascii")
        try:
            with challenge_path.open("xb") as stream:
                stream.write(challenge_payload)
                stream.flush()
                os.fsync(stream.fileno())

            def execute(
                *, prompt: bytes, output_schema: Mapping[str, object]
            ) -> NativeExecutionResult:
                return self.native_backend.execute(
                    prepared_arm=self._pre_boundary_preparation(self._freeze),
                    workspace_root=self.qualification_workspace,
                    codex_home=self.codex_home,
                    output_root=self.qualification_output,
                    prompt=prompt,
                    output_schema=output_schema,
                )

            result, observation = self.boundary_probe.run(
                workspace=self.qualification_workspace,
                challenge=challenge,
                challenge_path=challenge_path,
                whoami=self.whoami,
                generation=self._freeze,
                configured_catalog=self.native_backend.configured_catalog,
                execute=execute,
            )
            if challenge_path.read_bytes() != challenge_payload:
                _fail(PAIR_INVALID)
            boundary_evidence = self.boundary_producer.produce(
                result=result,
                generation=self._freeze,
                observation=observation,
            )
        except OSError:
            _fail()
        finally:
            challenge_path.unlink(missing_ok=True)
        boundary_evidence.validate()
        self.boundary_evidence = boundary_evidence
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
            or self.boundary_evidence is None
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

    def require_boundary_evidence(self) -> PreExposureBoundaryEvidence:
        if self.boundary_evidence is None or not self._canary_used:
            _fail(PAIR_INVALID)
        self.boundary_evidence.validate()
        return self.boundary_evidence

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
            candidate = self.freeze_probe.capture_candidate()
            if provisioning.generation_after != candidate.generation:
                _fail(SAME_MACHINE_WINDOW_REJECTED)
            self.backend.bind_freeze(candidate.generation)
            qualification = self.adapter.qualify_canary()
            freeze = self.freeze_probe.finalize(
                candidate,
                self.backend.require_boundary_evidence(),
            )
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
