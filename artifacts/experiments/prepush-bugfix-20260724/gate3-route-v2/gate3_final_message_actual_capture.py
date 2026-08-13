"""Offline-only Gate 3 actual-capture adapter core.

The module consumes private synthetic/reviewed NDJSON bytes and emits only
content-free public attestations.  It does not launch Codex, read credentials,
or prove that adapter-reported markers correspond to an executable's stdout.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


MAX_LINE_BYTES = 1 << 20
MAX_TOTAL_BYTES = 32 << 20
SHA256_NONE = "NONE"
PUBLIC_CLAIM = "PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED"

AUTHORIZATION_PATH = "capture-authorization.json"
PROCESS_RESULT_PATH = "process-result.json"
PROJECTION_PATH = "lifecycle-projection.json"
CAPTURE_RESULT_PATH = "capture-result.json"

AUTHORIZATION_SCHEMA = "gate3-route-v2.capture-authorization.v1"
PROCESS_RESULT_SCHEMA = "gate3-route-v2.content-free-process-result.v1"
PROJECTION_SCHEMA = "gate3-route-v2.actual-lifecycle-projection.v1"
CAPTURE_RESULT_SCHEMA = "gate3-route-v2.capture-result.v1"


class CaptureError(ValueError):
    """Closed adapter failure that never renders private input."""

    def __init__(self, code: str, line_ordinal: int | None = None) -> None:
        self.code = code
        self.line_ordinal = line_ordinal
        suffix = "" if line_ordinal is None else f":line={line_ordinal}"
        super().__init__(f"{code}{suffix}")


class SyntheticCrash(RuntimeError):
    """Deterministic crash point for offline retained-state tests."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _contract_bytes(name: str, value: object) -> bytes:
    return canonical_bytes({"name": name, "value": value})


def _raw_envelope_contract_bytes(
    max_line_bytes: int, max_total_bytes: int
) -> bytes:
    return _contract_bytes(
        "gate3-route-v2.raw-envelope-contract.v1",
        {
            "events": [
                "thread.started",
                "turn.started",
                "item.started",
                "item.updated",
                "item.completed",
                "turn.completed",
                "turn.failed",
                "error",
            ],
            "item_discriminants": ["agent_message", "other"],
            "max_line_bytes": max_line_bytes,
            "max_total_bytes": max_total_bytes,
            "unknown_event": "FAIL_CLOSED",
        },
    )


RAW_ENVELOPE_CONTRACT_BYTES = _raw_envelope_contract_bytes(1 << 20, 32 << 20)

PROJECTOR_CONTRACT_BYTES = _contract_bytes(
    "gate3-route-v2.lifecycle-projector-contract.v1",
    {
        "item_markers": ["agent_message", "none", "other"],
        "markers": [
            "thread_started",
            "turn_started",
            "item_started",
            "item_updated",
            "item_completed",
            "turn_completed",
            "turn_failed",
            "stream_error",
        ],
        "ordinal": "zero-based-contiguous",
        "raw_retention": "NONE",
    },
)

ADAPTER_CONTRACT_BYTES = _contract_bytes(
    "gate3-route-v2.actual-capture-adapter-contract.v1",
    {
        "capture_ordinal": 1,
        "claim": PUBLIC_CLAIM,
        "replacement": False,
        "retry": False,
    },
)


def _schema(name: str, required: Sequence[str]) -> bytes:
    return canonical_bytes(
        {
            "additional_properties": False,
            "name": name,
            "required": sorted(required),
            "schema": "gate3-route-v2.closed-public-schema.v1",
        }
    )


PUBLIC_SCHEMA_BYTES = {
    "authorization": _schema(
        AUTHORIZATION_SCHEMA,
        (
            "action_sha256",
            "adapter_contract_sha256",
            "adapter_source_sha256",
            "arm",
            "capture_ordinal",
            "command_contract_sha256",
            "executable_sha256",
            "lifecycle_projector_sha256",
            "public_schema_sha256",
            "raw_envelope_contract_sha256",
            "replacement",
            "retry",
            "schema",
        ),
    ),
    "process_result": _schema(
        PROCESS_RESULT_SCHEMA,
        (
            "exit_code",
            "process_disposition",
            "schema",
            "stdout_eof",
            "stdout_read_failed",
            "stdout_reader_complete",
        ),
    ),
    "projection": _schema(
        PROJECTION_SCHEMA,
        (
            "action_sha256",
            "adapter_contract_sha256",
            "command_contract_sha256",
            "entries",
            "projector_sha256",
            "raw_retention",
            "schema",
        ),
    ),
    "capture_result": _schema(
        CAPTURE_RESULT_SCHEMA,
        (
            "authorization_sha256",
            "failure_code",
            "process_result_sha256",
            "projection_sha256",
            "schema",
            "status",
        ),
    ),
}


def public_schema_sha256() -> dict[str, str]:
    return {name: sha256(payload) for name, payload in PUBLIC_SCHEMA_BYTES.items()}


def module_source_sha256() -> str:
    """Hash the exact reviewed module bytes without retaining them publicly."""

    return sha256(Path(__file__).read_bytes())


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class CaptureBindings:
    executable_sha256: str
    command_contract_sha256: str
    adapter_source_sha256: str
    action_sha256: str
    arm: str
    adapter_contract_sha256: str = field(
        default_factory=lambda: sha256(ADAPTER_CONTRACT_BYTES)
    )
    raw_envelope_contract_sha256: str = field(
        default_factory=lambda: sha256(RAW_ENVELOPE_CONTRACT_BYTES)
    )
    lifecycle_projector_sha256: str = field(
        default_factory=lambda: sha256(PROJECTOR_CONTRACT_BYTES)
    )
    public_schema_sha256: Mapping[str, str] = field(
        default_factory=public_schema_sha256
    )

    def validate(self) -> None:
        for value in (
            self.executable_sha256,
            self.command_contract_sha256,
            self.adapter_source_sha256,
            self.action_sha256,
            self.adapter_contract_sha256,
            self.raw_envelope_contract_sha256,
            self.lifecycle_projector_sha256,
        ):
            if not _is_sha256(value):
                raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        if self.arm not in {"A", "B"}:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        try:
            expected_raw_contract = _raw_envelope_contract_bytes(1 << 20, 32 << 20)
            if MAX_LINE_BYTES != 1 << 20 or MAX_TOTAL_BYTES != 32 << 20:
                raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
            if RAW_ENVELOPE_CONTRACT_BYTES != expected_raw_contract:
                raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
            current_values = {
                "adapter_source_sha256": module_source_sha256(),
                "adapter_contract_sha256": sha256(ADAPTER_CONTRACT_BYTES),
                "raw_envelope_contract_sha256": sha256(expected_raw_contract),
                "lifecycle_projector_sha256": sha256(PROJECTOR_CONTRACT_BYTES),
            }
            current_schemas = public_schema_sha256()
        except Exception:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH") from None
        if self.adapter_source_sha256 != current_values["adapter_source_sha256"]:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        if self.adapter_contract_sha256 != current_values["adapter_contract_sha256"]:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        if self.raw_envelope_contract_sha256 != current_values["raw_envelope_contract_sha256"]:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        if self.lifecycle_projector_sha256 != current_values["lifecycle_projector_sha256"]:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
        if dict(self.public_schema_sha256) != current_schemas:
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")

    def authorization(self) -> dict[str, object]:
        self.validate()
        return {
            "action_sha256": self.action_sha256,
            "adapter_contract_sha256": self.adapter_contract_sha256,
            "adapter_source_sha256": self.adapter_source_sha256,
            "arm": self.arm,
            "capture_ordinal": 1,
            "command_contract_sha256": self.command_contract_sha256,
            "executable_sha256": self.executable_sha256,
            "lifecycle_projector_sha256": self.lifecycle_projector_sha256,
            "public_schema_sha256": dict(self.public_schema_sha256),
            "raw_envelope_contract_sha256": self.raw_envelope_contract_sha256,
            "replacement": False,
            "retry": False,
            "schema": AUTHORIZATION_SCHEMA,
        }


def synthetic_bindings(*, arm: str = "A") -> CaptureBindings:
    return CaptureBindings(
        executable_sha256=sha256(b"reviewed-synthetic-executable-v1\n"),
        command_contract_sha256=sha256(b"reviewed-synthetic-command-v1\n"),
        adapter_source_sha256=module_source_sha256(),
        action_sha256=sha256(f"reviewed-synthetic-action-{arm}-v1\n".encode("ascii")),
        arm=arm,
    )


@dataclass(frozen=True)
class Discriminant:
    marker: str
    item_marker: str


EVENT_MARKERS = {
    "thread.started": "thread_started",
    "turn.started": "turn_started",
    "item.started": "item_started",
    "item.updated": "item_updated",
    "item.completed": "item_completed",
    "turn.completed": "turn_completed",
    "turn.failed": "turn_failed",
    "error": "stream_error",
}
ITEM_EVENTS = {"item.started", "item.updated", "item.completed"}
TERMINAL_MARKERS = {"turn_completed", "turn_failed", "stream_error"}
ITEM_MARKERS = {"agent_message", "none", "other"}


class _DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise _DuplicateKey
        value[key] = child
    return value


def _reject_nonfinite(_: str) -> object:
    raise ValueError


def _validated_runtime_limits() -> tuple[int, int]:
    expected = _raw_envelope_contract_bytes(1 << 20, 32 << 20)
    if MAX_LINE_BYTES != 1 << 20 or MAX_TOTAL_BYTES != 32 << 20:
        raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
    if RAW_ENVELOPE_CONTRACT_BYTES != expected:
        raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
    return 1 << 20, 32 << 20


def parse_private_ndjson(raw: bytes) -> tuple[Discriminant, ...]:
    """Extract admitted discriminants without returning private JSON objects."""

    max_line_bytes, max_total_bytes = _validated_runtime_limits()
    if type(raw) is not bytes or not raw:
        raise CaptureError("FRAMING_INVALID")
    if len(raw) > max_total_bytes:
        raise CaptureError("SIZE_LIMIT_EXCEEDED")
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise CaptureError("FRAMING_INVALID")

    lines = raw[:-1].split(b"\n")
    if not lines or any(not line for line in lines):
        raise CaptureError("FRAMING_INVALID")

    output: list[Discriminant] = []
    for ordinal, line in enumerate(lines):
        if len(line) > max_line_bytes:
            raise CaptureError("SIZE_LIMIT_EXCEEDED", ordinal)
        try:
            text = line.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise CaptureError("UTF8_INVALID", ordinal) from None
        try:
            value = json.loads(
                text,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_nonfinite,
            )
        except Exception:
            raise CaptureError("JSON_INVALID", ordinal) from None
        if not isinstance(value, dict):
            raise CaptureError("JSON_INVALID", ordinal)

        event_type = value.get("type")
        if not isinstance(event_type, str) or event_type not in EVENT_MARKERS:
            raise CaptureError("UNKNOWN_EVENT_TYPE", ordinal)

        item_marker = "none"
        if event_type in ITEM_EVENTS:
            item = value.get("item")
            if not isinstance(item, dict):
                raise CaptureError("ITEM_DISCRIMINANT_INVALID", ordinal)
            item_type = item.get("type")
            if not isinstance(item_type, str) or not item_type:
                raise CaptureError("ITEM_DISCRIMINANT_INVALID", ordinal)
            item_marker = "agent_message" if item_type == "agent_message" else "other"
        output.append(Discriminant(EVENT_MARKERS[event_type], item_marker))
    return tuple(output)


def project_lifecycle(
    discriminants: Sequence[Discriminant], bindings: CaptureBindings
) -> dict[str, object]:
    bindings.validate()
    markers = [entry.marker for entry in discriminants]
    if len(markers) < 3:
        raise CaptureError("LIFECYCLE_INCOMPLETE")
    if markers[0:2] != ["thread_started", "turn_started"]:
        raise CaptureError("LIFECYCLE_INCOMPLETE")
    if markers[-1] not in TERMINAL_MARKERS:
        raise CaptureError("LIFECYCLE_INCOMPLETE")
    if any(marker in {"thread_started", "turn_started"} for marker in markers[2:]):
        raise CaptureError("LIFECYCLE_INCOMPLETE")
    if any(marker in TERMINAL_MARKERS for marker in markers[:-1]):
        raise CaptureError("LIFECYCLE_INCOMPLETE")
    if any(
        marker not in {"item_started", "item_updated", "item_completed"}
        for marker in markers[2:-1]
    ):
        raise CaptureError("LIFECYCLE_INCOMPLETE")

    entries = [
        {
            "item_marker": entry.item_marker,
            "marker": entry.marker,
            "ordinal": ordinal,
        }
        for ordinal, entry in enumerate(discriminants)
    ]
    projection = {
        "action_sha256": bindings.action_sha256,
        "adapter_contract_sha256": bindings.adapter_contract_sha256,
        "command_contract_sha256": bindings.command_contract_sha256,
        "entries": entries,
        "projector_sha256": bindings.lifecycle_projector_sha256,
        "raw_retention": "NONE",
        "schema": PROJECTION_SCHEMA,
    }
    validate_projection(projection, bindings)
    return projection


def agent_message_axis(
    projection: Mapping[str, object], bindings: CaptureBindings
) -> str:
    validate_projection(projection, bindings)
    entries = projection.get("entries")
    assert isinstance(entries, list)
    completed_agent = any(
        isinstance(entry, dict)
        and entry.get("marker") == "item_completed"
        and entry.get("item_marker") == "agent_message"
        for entry in entries
    )
    if completed_agent:
        return "PRESENT"
    if any(
        isinstance(entry, dict) and entry.get("item_marker") == "other"
        for entry in entries
    ):
        return "INDETERMINATE"
    if any(
        isinstance(entry, dict) and entry.get("item_marker") == "agent_message"
        for entry in entries
    ):
        return "INDETERMINATE"
    return "ABSENT"


def build_process_result(
    *,
    exit_code: int | None = 0,
    process_disposition: str = "EXITED",
    stdout_eof: bool = True,
    stdout_reader_complete: bool = True,
    stdout_read_failed: bool = False,
) -> dict[str, object]:
    value = {
        "exit_code": exit_code,
        "process_disposition": process_disposition,
        "schema": PROCESS_RESULT_SCHEMA,
        "stdout_eof": stdout_eof,
        "stdout_read_failed": stdout_read_failed,
        "stdout_reader_complete": stdout_reader_complete,
    }
    validate_process_result(value)
    return value


PROCESS_DISPOSITIONS = {"EXITED", "TIMED_OUT", "TERMINATED", "START_FAILED"}


def _require_exact_fields(value: Mapping[str, object], fields: set[str]) -> None:
    if set(value) != fields:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")


def validate_process_result(value: Mapping[str, object]) -> None:
    _require_exact_fields(
        value,
        {
            "exit_code",
            "process_disposition",
            "schema",
            "stdout_eof",
            "stdout_read_failed",
            "stdout_reader_complete",
        },
    )
    if value.get("schema") != PROCESS_RESULT_SCHEMA:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    disposition = value.get("process_disposition")
    if disposition not in PROCESS_DISPOSITIONS:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    exit_code = value.get("exit_code")
    if disposition == "EXITED":
        if type(exit_code) is not int:
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
    elif exit_code is not None:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    for key in ("stdout_eof", "stdout_read_failed", "stdout_reader_complete"):
        if type(value.get(key)) is not bool:
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if value["stdout_read_failed"] and (
        value["stdout_eof"] or value["stdout_reader_complete"]
    ):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")


def validate_projection(value: Mapping[str, object], bindings: CaptureBindings) -> None:
    _require_exact_fields(
        value,
        {
            "action_sha256",
            "adapter_contract_sha256",
            "command_contract_sha256",
            "entries",
            "projector_sha256",
            "raw_retention",
            "schema",
        },
    )
    expected = {
        "action_sha256": bindings.action_sha256,
        "adapter_contract_sha256": bindings.adapter_contract_sha256,
        "command_contract_sha256": bindings.command_contract_sha256,
        "projector_sha256": bindings.lifecycle_projector_sha256,
        "raw_retention": "NONE",
        "schema": PROJECTION_SCHEMA,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    entries = value.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    discriminants: list[Discriminant] = []
    for ordinal, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
        _require_exact_fields(entry, {"item_marker", "marker", "ordinal"})
        if type(entry.get("ordinal")) is not int or entry["ordinal"] != ordinal:
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
        marker = entry.get("marker")
        item_marker = entry.get("item_marker")
        if marker not in set(EVENT_MARKERS.values()) or item_marker not in ITEM_MARKERS:
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
        if (marker.startswith("item_") and item_marker == "none") or (
            not marker.startswith("item_") and item_marker != "none"
        ):
            raise CaptureError("PRIVACY_VALIDATION_FAILED")
        discriminants.append(Discriminant(str(marker), str(item_marker)))
    markers = [entry.marker for entry in discriminants]
    if markers[0:2] != ["thread_started", "turn_started"]:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if markers[-1] not in TERMINAL_MARKERS:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if any(marker in TERMINAL_MARKERS for marker in markers[:-1]):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if any(marker in {"thread_started", "turn_started"} for marker in markers[2:]):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if any(
        marker not in {"item_started", "item_updated", "item_completed"}
        for marker in markers[2:-1]
    ):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")


RESULT_ROWS = {
    ("COMPLETE", "NONE"): True,
    ("INCOMPLETE", "LIFECYCLE_INCOMPLETE"): False,
    ("INVALID", "FRAMING_INVALID"): False,
    ("INVALID", "UTF8_INVALID"): False,
    ("INVALID", "JSON_INVALID"): False,
    ("INVALID", "UNKNOWN_EVENT_TYPE"): False,
    ("INVALID", "ITEM_DISCRIMINANT_INVALID"): False,
    ("INVALID", "SIZE_LIMIT_EXCEEDED"): False,
    ("UNAVAILABLE", "STDOUT_READ_FAILED"): False,
    ("UNAVAILABLE", "CAPTURE_CONTRACT_MISMATCH"): False,
    ("UNAVAILABLE", "PRIVACY_VALIDATION_FAILED"): False,
    ("UNAVAILABLE", "PUBLICATION_FAILED"): False,
}


def validate_capture_result(value: Mapping[str, object]) -> None:
    _require_exact_fields(
        value,
        {
            "authorization_sha256",
            "failure_code",
            "process_result_sha256",
            "projection_sha256",
            "schema",
            "status",
        },
    )
    if value.get("schema") != CAPTURE_RESULT_SCHEMA:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if not _is_sha256(value.get("authorization_sha256")) or not _is_sha256(
        value.get("process_result_sha256")
    ):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    row = (value.get("status"), value.get("failure_code"))
    if row not in RESULT_ROWS:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    projection_required = RESULT_ROWS[row]
    projection_sha = value.get("projection_sha256")
    if projection_required != _is_sha256(projection_sha):
        raise CaptureError("PRIVACY_VALIDATION_FAILED")
    if not projection_required and projection_sha != SHA256_NONE:
        raise CaptureError("PRIVACY_VALIDATION_FAILED")


@dataclass
class CreateOnceStore:
    files: dict[str, bytes] = field(default_factory=dict)
    crash_plan: tuple[str, str] | None = None

    def arm_crash(self, path: str, phase: str) -> None:
        if phase not in {"before", "after"}:
            raise CaptureError("CRASH_PHASE_INVALID")
        self.crash_plan = (path, phase)

    def publish(self, path: str, payload: bytes) -> str:
        if type(payload) is not bytes:
            raise CaptureError("PUBLICATION_FAILED")
        crash = None
        if self.crash_plan is not None and self.crash_plan[0] == path:
            crash = self.crash_plan[1]
            self.crash_plan = None
        if crash == "before":
            raise SyntheticCrash("BEFORE_DURABILITY")
        existing = self.files.get(path)
        if existing is not None and existing != payload:
            raise CaptureError("CREATE_ONCE_COLLISION")
        self.files.setdefault(path, payload)
        if self.files[path] != payload:
            raise CaptureError("DURABLE_REOPEN_MISMATCH")
        digest = sha256(payload)
        if crash == "after":
            raise SyntheticCrash("AFTER_DURABILITY")
        return digest

    def read(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError:
            raise CaptureError("ARTIFACT_MISSING") from None

    def clone(self) -> "CreateOnceStore":
        return CreateOnceStore(copy.deepcopy(self.files))


def _parse_canonical(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
        if not isinstance(value, dict) or canonical_bytes(value) != payload:
            raise CaptureError("PUBLIC_ARTIFACT_INVALID")
    except CaptureError:
        raise
    except Exception:
        raise CaptureError("PUBLIC_ARTIFACT_INVALID") from None
    return value


def verify_authorization_for_launch(
    store: CreateOnceStore, expected_bindings: CaptureBindings
) -> str:
    expected = canonical_bytes(expected_bindings.authorization())
    try:
        retained = store.read(AUTHORIZATION_PATH)
    except CaptureError:
        raise CaptureError("CAPTURE_CONTRACT_MISMATCH") from None
    if retained != expected:
        raise CaptureError("CAPTURE_CONTRACT_MISMATCH")
    return sha256(retained)


def _capture_row(code: str) -> tuple[str, str]:
    if code == "LIFECYCLE_INCOMPLETE":
        return "INCOMPLETE", code
    if code in {
        "FRAMING_INVALID",
        "UTF8_INVALID",
        "JSON_INVALID",
        "UNKNOWN_EVENT_TYPE",
        "ITEM_DISCRIMINANT_INVALID",
        "SIZE_LIMIT_EXCEEDED",
    }:
        return "INVALID", code
    if code in {
        "STDOUT_READ_FAILED",
        "CAPTURE_CONTRACT_MISMATCH",
        "PRIVACY_VALIDATION_FAILED",
        "PUBLICATION_FAILED",
    }:
        return "UNAVAILABLE", code
    raise CaptureError("PUBLICATION_FAILED")


@dataclass
class CapturePublisher:
    store: CreateOnceStore
    _may_capture: bool = False

    def authorize(self, bindings: CaptureBindings) -> str:
        if AUTHORIZATION_PATH in self.store.files:
            raise CaptureError("CAPTURE_ALREADY_AUTHORIZED")
        payload = canonical_bytes(bindings.authorization())
        digest = self.store.publish(AUTHORIZATION_PATH, payload)
        if self.store.read(AUTHORIZATION_PATH) != payload:
            raise CaptureError("DURABLE_REOPEN_MISMATCH")
        self._may_capture = True
        return digest

    def capture(
        self,
        raw: bytes,
        process_result: Mapping[str, object],
        bindings: CaptureBindings,
    ) -> dict[str, object]:
        if not self._may_capture:
            raise CaptureError("CAPTURE_RESULT_UNKNOWN")
        self._may_capture = False
        authorization_sha = verify_authorization_for_launch(self.store, bindings)
        validate_process_result(process_result)
        process_payload = canonical_bytes(dict(process_result))
        if PROCESS_RESULT_PATH in self.store.files:
            raise CaptureError("CREATE_ONCE_COLLISION")
        process_sha = self.store.publish(PROCESS_RESULT_PATH, process_payload)
        if self.store.read(PROCESS_RESULT_PATH) != process_payload:
            raise CaptureError("DURABLE_REOPEN_MISMATCH")

        projection_sha = SHA256_NONE
        try:
            if process_result["stdout_read_failed"]:
                raise CaptureError("STDOUT_READ_FAILED")
            if not process_result["stdout_eof"] or not process_result["stdout_reader_complete"]:
                raise CaptureError("LIFECYCLE_INCOMPLETE")
            bindings.validate()
            discriminants = parse_private_ndjson(raw)
            projection = project_lifecycle(discriminants, bindings)
            projection_payload = canonical_bytes(projection)
            if PROJECTION_PATH in self.store.files:
                raise CaptureError("CREATE_ONCE_COLLISION")
            projection_sha = self.store.publish(PROJECTION_PATH, projection_payload)
            if self.store.read(PROJECTION_PATH) != projection_payload:
                raise CaptureError("DURABLE_REOPEN_MISMATCH")
            status, failure_code = "COMPLETE", "NONE"
        except SyntheticCrash:
            raise
        except CaptureError as exc:
            if exc.code in {"CREATE_ONCE_COLLISION", "DURABLE_REOPEN_MISMATCH"}:
                status, failure_code = "UNAVAILABLE", "PUBLICATION_FAILED"
                projection_sha = SHA256_NONE
            else:
                status, failure_code = _capture_row(exc.code)

        result = {
            "authorization_sha256": authorization_sha,
            "failure_code": failure_code,
            "process_result_sha256": process_sha,
            "projection_sha256": projection_sha,
            "schema": CAPTURE_RESULT_SCHEMA,
            "status": status,
        }
        validate_capture_result(result)
        result_payload = canonical_bytes(result)
        if CAPTURE_RESULT_PATH in self.store.files:
            raise CaptureError("CREATE_ONCE_COLLISION")
        self.store.publish(CAPTURE_RESULT_PATH, result_payload)
        if self.store.read(CAPTURE_RESULT_PATH) != result_payload:
            raise CaptureError("DURABLE_REOPEN_MISMATCH")
        return result


@dataclass(frozen=True)
class Verification:
    verified: bool
    code: str
    claim: str | None = None


def reconstruct_state(store: CreateOnceStore) -> str:
    if AUTHORIZATION_PATH not in store.files:
        return "NOT_AUTHORIZED"
    if CAPTURE_RESULT_PATH not in store.files:
        return "CAPTURE_RESULT_UNKNOWN"
    return "RESULT_RETAINED"


def verify_public(
    store: CreateOnceStore, expected_bindings: CaptureBindings
) -> Verification:
    try:
        authorization_sha = verify_authorization_for_launch(store, expected_bindings)
        if CAPTURE_RESULT_PATH not in store.files:
            return Verification(False, "CAPTURE_RESULT_UNKNOWN")
        authorization = _parse_canonical(store.read(AUTHORIZATION_PATH))
        if authorization != expected_bindings.authorization():
            raise CaptureError("CAPTURE_CONTRACT_MISMATCH")

        process_payload = store.read(PROCESS_RESULT_PATH)
        process_result = _parse_canonical(process_payload)
        validate_process_result(process_result)

        result = _parse_canonical(store.read(CAPTURE_RESULT_PATH))
        validate_capture_result(result)
        if result["authorization_sha256"] != authorization_sha:
            raise CaptureError("PUBLIC_LINK_MISMATCH")
        if result["process_result_sha256"] != sha256(process_payload):
            raise CaptureError("PUBLIC_LINK_MISMATCH")

        projection_required = result["status"] == "COMPLETE"
        expected_paths = {
            AUTHORIZATION_PATH,
            PROCESS_RESULT_PATH,
            CAPTURE_RESULT_PATH,
        }
        if projection_required:
            projection_payload = store.read(PROJECTION_PATH)
            projection = _parse_canonical(projection_payload)
            validate_projection(projection, expected_bindings)
            if result["projection_sha256"] != sha256(projection_payload):
                raise CaptureError("PUBLIC_LINK_MISMATCH")
            expected_paths.add(PROJECTION_PATH)
        elif result["projection_sha256"] != SHA256_NONE:
            raise CaptureError("PUBLIC_LINK_MISMATCH")
        if set(store.files) != expected_paths:
            raise CaptureError("PUBLIC_ARTIFACT_TREE_NOT_CLOSED")
        return Verification(True, "VERIFIED", PUBLIC_CLAIM)
    except CaptureError as exc:
        return Verification(False, exc.code)
    except Exception:
        return Verification(False, "PUBLIC_ARTIFACT_INVALID")


__all__ = [
    "ADAPTER_CONTRACT_BYTES",
    "AUTHORIZATION_PATH",
    "CAPTURE_RESULT_PATH",
    "CaptureBindings",
    "CaptureError",
    "CapturePublisher",
    "CreateOnceStore",
    "Discriminant",
    "MAX_LINE_BYTES",
    "MAX_TOTAL_BYTES",
    "PROCESS_RESULT_PATH",
    "PROJECTION_PATH",
    "PUBLIC_CLAIM",
    "PUBLIC_SCHEMA_BYTES",
    "RAW_ENVELOPE_CONTRACT_BYTES",
    "SyntheticCrash",
    "Verification",
    "agent_message_axis",
    "build_process_result",
    "canonical_bytes",
    "module_source_sha256",
    "parse_private_ndjson",
    "project_lifecycle",
    "public_schema_sha256",
    "reconstruct_state",
    "sha256",
    "synthetic_bindings",
    "verify_authorization_for_launch",
    "verify_public",
]
