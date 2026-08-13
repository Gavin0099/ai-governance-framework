"""Pure synthetic classifier for the Gate 3 final-message diagnostic design.

This module intentionally performs no filesystem, process, network, credential,
preflight, publication, or live-session work.  Its authority is limited to the
fixed synthetic contract and fixture identities defined below.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from types import CodeType, FunctionType
from typing import Mapping


PUBLIC_INPUT_SCHEMA = "gate3-route-v2.final-message-diagnostic-input.v1"
CLASSIFICATION_SCHEMA = (
    "gate3-route-v2.final-message-diagnostic-classification.v1"
)
SYNTHETIC_PROVENANCE = "fixed_synthetic_fixture"


class ProcessAxis(str, Enum):
    ZERO = "ZERO"
    PROCESS_EXECUTION_FAILURE = "PROCESS_EXECUTION_FAILURE"
    INDETERMINATE = "INDETERMINATE"


class TurnEventAxis(str, Enum):
    TURN_COMPLETED_WITH_AGENT_MESSAGE = "TURN_COMPLETED_WITH_AGENT_MESSAGE"
    TURN_COMPLETED_WITHOUT_AGENT_MESSAGE = "TURN_COMPLETED_WITHOUT_AGENT_MESSAGE"
    TURN_FAILED = "TURN_FAILED"
    INDETERMINATE = "INDETERMINATE"


class FinalOutputAxis(str, Enum):
    ABSENT_AT_POST_TERMINATION_OBSERVATION = (
        "ABSENT_AT_POST_TERMINATION_OBSERVATION"
    )
    NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE = (
        "NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE"
    )
    CREATED_THEN_REMOVED = "CREATED_THEN_REMOVED"
    CAPTURED_VALID = "CAPTURED_VALID"
    CAPTURED_INVALID = "CAPTURED_INVALID"
    READ_FAILED = "READ_FAILED"
    PATH_INVALID = "PATH_INVALID"
    INDETERMINATE = "INDETERMINATE"


class TaskExecutionAxis(str, Enum):
    MATCHED_EXPECTED = "MATCHED_EXPECTED"
    UNCHANGED_BASELINE = "UNCHANGED_BASELINE"
    OTHER_MISMATCH = "OTHER_MISMATCH"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    INDETERMINATE = "INDETERMINATE"


class DiagnosticClass(str, Enum):
    PROCESS_EXECUTION_FAILURE = "PROCESS_EXECUTION_FAILURE"
    CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED = (
        "CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED"
    )
    TURN_COMPLETED_WITHOUT_AGENT_MESSAGE = "TURN_COMPLETED_WITHOUT_AGENT_MESSAGE"
    ADAPTER_CAPTURE_FAILURE = "ADAPTER_CAPTURE_FAILURE"
    FINAL_SCHEMA_FAILURE = "FINAL_SCHEMA_FAILURE"
    TASK_EXECUTION_FAILURE = "TASK_EXECUTION_FAILURE"
    MULTIPLE_FAILURES = "MULTIPLE_FAILURES"
    INDETERMINATE = "INDETERMINATE"
    DIAGNOSTIC_PATH_COMPLETE = "DIAGNOSTIC_PATH_COMPLETE"


@dataclass(frozen=True)
class AxisSnapshot:
    process: ProcessAxis
    turn_event: TurnEventAxis
    final_output: FinalOutputAxis
    task_execution: TaskExecutionAxis


@dataclass(frozen=True)
class Classification:
    axes: AxisSnapshot
    diagnostic_classes: tuple[DiagnosticClass, ...]
    overall: DiagnosticClass
    reasons: tuple[str, ...]

    def as_public_value(self) -> dict[str, object]:
        return {
            "axes": {
                "final_output": self.axes.final_output.value,
                "process": self.axes.process.value,
                "task_execution": self.axes.task_execution.value,
                "turn_event": self.axes.turn_event.value,
            },
            "diagnostic_classes": [value.value for value in self.diagnostic_classes],
            "overall": self.overall.value,
            "reasons": list(self.reasons),
            "schema": CLASSIFICATION_SCHEMA,
        }


_EVENT_CONTRACT_VALUE: dict[str, object] = {
    "allowed_item_markers": ["agent_message"],
    "allowed_markers": [
        "item_completed",
        "item_started",
        "turn_completed",
        "turn_failed",
        "turn_started",
    ],
    "completed_turn_process_rule": (
        "completed terminal is compatible with zero, nonzero, or externally "
        "terminated process only when timed_out is false"
    ),
    "schema": "gate3-route-v2.synthetic-event-contract.v1",
    "terminal_markers": ["turn_completed", "turn_failed"],
}
_EVENT_SCHEMA_VALUE: dict[str, object] = {
    "closed_entry_fields": ["item_marker", "marker", "ordinal"],
    "item_marker_allowed_only_for": ["item_completed", "item_started"],
    "ordinal_rule": "zero_based_contiguous",
    "schema": "gate3-route-v2.synthetic-event-projection-schema.v1",
    "terminal_rule": "exactly_one_terminal_and_terminal_is_last",
    "turn_start_rule": "exactly_one_turn_started_and_start_is_first",
}


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


SYNTHETIC_EVENT_CONTRACT_BYTES = _json_bytes(_EVENT_CONTRACT_VALUE)
SYNTHETIC_EVENT_SCHEMA_BYTES = _json_bytes(_EVENT_SCHEMA_VALUE)
SYNTHETIC_EVENT_CONTRACT_SHA256 = _sha256(SYNTHETIC_EVENT_CONTRACT_BYTES)
SYNTHETIC_EVENT_SCHEMA_SHA256 = _sha256(SYNTHETIC_EVENT_SCHEMA_BYTES)

_RAW_TYPE_TO_MARKER = {
    "item.completed": "item_completed",
    "item.started": "item_started",
    "turn.completed": "turn_completed",
    "turn.failed": "turn_failed",
    "turn.started": "turn_started",
}


def parse_validate_synthetic_raw(raw: bytes) -> tuple[dict[str, object], ...]:
    """Parse the fixed synthetic NDJSON subset into closed validated events."""

    if not isinstance(raw, bytes) or not raw:
        raise ValueError("synthetic raw event stream must be non-empty bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("synthetic raw event stream is not UTF-8") from exc
    if not text.endswith("\n") or any(not line for line in text.splitlines()):
        raise ValueError("synthetic raw event framing is invalid")
    validated: list[dict[str, object]] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise ValueError("synthetic raw event is not JSON") from exc
        if not isinstance(event, dict):
            raise ValueError("synthetic raw event is not an object")
        raw_type = event.get("type")
        if not isinstance(raw_type, str) or raw_type not in _RAW_TYPE_TO_MARKER:
            raise ValueError("synthetic raw event type is not allowed")
        if raw_type.startswith("item."):
            if set(event) != {"item", "type"}:
                raise ValueError("synthetic item event fields are not closed")
            item = event.get("item")
            if not isinstance(item, dict) or set(item) != {"type"}:
                raise ValueError("synthetic item fields are not closed")
            item_type = item.get("type")
            if item_type != "agent_message":
                raise ValueError("synthetic item type is not allowed")
            validated.append({"item_type": item_type, "type": raw_type})
        else:
            if set(event) != {"type"}:
                raise ValueError("synthetic turn event fields are not closed")
            validated.append({"type": raw_type})
    return tuple(validated)


def project_validated_events(
    events: tuple[dict[str, object], ...]
) -> list[dict[str, object]]:
    """Project validated synthetic events into the closed public markers."""

    projection: list[dict[str, object]] = []
    for ordinal, event in enumerate(events):
        raw_type = event["type"]
        if not isinstance(raw_type, str) or raw_type not in _RAW_TYPE_TO_MARKER:
            raise ValueError("validated synthetic event type is invalid")
        entry: dict[str, object] = {
            "marker": _RAW_TYPE_TO_MARKER[raw_type],
            "ordinal": ordinal,
        }
        if "item_type" in event:
            if event["item_type"] != "agent_message":
                raise ValueError("validated synthetic item type is invalid")
            entry["item_marker"] = "agent_message"
        projection.append(entry)
    return projection


def _code_constant_value(value: object) -> object:
    if isinstance(value, CodeType):
        return _code_value(value)
    if isinstance(value, tuple):
        return [_code_constant_value(item) for item in value]
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError("implementation contains an unsupported code constant")


def _code_value(code: CodeType) -> dict[str, object]:
    return {
        "argcount": code.co_argcount,
        "cellvars": list(code.co_cellvars),
        "code_hex": code.co_code.hex(),
        "consts": [_code_constant_value(value) for value in code.co_consts],
        "exceptiontable_hex": code.co_exceptiontable.hex(),
        "flags": code.co_flags,
        "freevars": list(code.co_freevars),
        "kwonlyargcount": code.co_kwonlyargcount,
        "names": list(code.co_names),
        "nlocals": code.co_nlocals,
        "posonlyargcount": code.co_posonlyargcount,
        "stacksize": code.co_stacksize,
        "varnames": list(code.co_varnames),
    }


def implementation_sha256(function: object) -> str:
    """Hash executable bytecode semantics without reading source files."""

    if not isinstance(function, FunctionType):
        raise TypeError("implementation identity requires a Python function")
    bound_data: dict[str, object] = {}
    if function in {parse_validate_synthetic_raw, project_validated_events}:
        bound_data["raw_type_to_marker"] = dict(sorted(_RAW_TYPE_TO_MARKER.items()))
    return _sha256(
        _json_bytes(
            {
                "bound_data": bound_data,
                "bytecode": _code_value(function.__code__),
            }
        )
    )


_CONTENT_FIXTURES: dict[str, tuple[str, bytes]] = {
    "synthetic_final_v1": ("final_message", b'{"status":"synthetic-ok"}\n'),
    "synthetic_final_invalid_v1": ("final_message", b'{"unexpected":true}\n'),
    "synthetic_stderr_empty_v1": ("stderr", b""),
    "synthetic_stderr_nonempty_v1": ("stderr", b"synthetic stderr\n"),
    "synthetic_stdout_empty_v1": ("stdout", b""),
    "synthetic_stdout_completed_without_agent_v1": (
        "stdout",
        b'{"type":"turn.started"}\n'
        b'{"type":"turn.completed"}\n',
    ),
    "synthetic_stdout_turn_failed_v1": (
        "stdout",
        b'{"type":"turn.started"}\n'
        b'{"type":"turn.failed"}\n',
    ),
    "synthetic_stdout_v1": (
        "stdout",
        b'{"type":"turn.started"}\n'
        b'{"item":{"type":"agent_message"},"type":"item.completed"}\n'
        b'{"type":"turn.completed"}\n',
    ),
}

_TOP_LEVEL_FIELDS = {
    "content_identities",
    "event_contract",
    "event_contract_sha256",
    "event_parser_validator_sha256",
    "event_projection",
    "event_projector_sha256",
    "event_schema",
    "event_schema_sha256",
    "final_output",
    "process",
    "schema",
    "task_execution",
}
_PROCESS_FIELDS = {
    "exit_classification",
    "launch_status",
    "stderr_capture",
    "stdout_capture",
    "timed_out",
    "tree_cleanup",
}
_CONTENT_FIELDS = {
    "artifact",
    "bytes",
    "fixture_id",
    "provenance",
    "sha256",
}
_MARKERS = set(_EVENT_CONTRACT_VALUE["allowed_markers"])
_ITEM_MARKERS = set(_EVENT_CONTRACT_VALUE["allowed_item_markers"])
_TERMINALS = set(_EVENT_CONTRACT_VALUE["terminal_markers"])


def _content_identity(fixture_id: str) -> dict[str, object]:
    artifact, payload = _CONTENT_FIXTURES[fixture_id]
    return {
        "artifact": artifact,
        "bytes": len(payload),
        "fixture_id": fixture_id,
        "provenance": SYNTHETIC_PROVENANCE,
        "sha256": _sha256(payload),
    }


def synthetic_fixture_bytes(fixture_id: str) -> bytes:
    """Return exact bytes for one fixed, synthetic-only content fixture."""

    try:
        return _CONTENT_FIXTURES[fixture_id][1]
    except KeyError as exc:
        raise ValueError("synthetic fixture identity is not approved") from exc


def build_synthetic_input(
    *,
    event_scenario: str = "completed_with_agent",
    final_output: object = FinalOutputAxis.CAPTURED_VALID.value,
) -> dict[str, object]:
    """Return one canonical, internally consistent synthetic public input."""

    try:
        final_axis = FinalOutputAxis(final_output)
    except (TypeError, ValueError) as exc:
        raise ValueError("synthetic final-output class is invalid") from exc
    stdout_fixture = {
        "completed_with_agent": "synthetic_stdout_v1",
        "completed_without_agent": (
            "synthetic_stdout_completed_without_agent_v1"
        ),
        "turn_failed": "synthetic_stdout_turn_failed_v1",
    }.get(event_scenario)
    if stdout_fixture is None:
        raise ValueError("synthetic event scenario is invalid")
    content_identities = [
        _content_identity(stdout_fixture),
        _content_identity("synthetic_stderr_empty_v1"),
    ]
    if final_axis == FinalOutputAxis.CAPTURED_VALID:
        content_identities.append(_content_identity("synthetic_final_v1"))
    elif final_axis == FinalOutputAxis.CAPTURED_INVALID:
        content_identities.append(_content_identity("synthetic_final_invalid_v1"))
    raw_stdout = synthetic_fixture_bytes(stdout_fixture)
    event_projection = project_validated_events(
        parse_validate_synthetic_raw(raw_stdout)
    )

    return {
        "content_identities": content_identities,
        "event_contract": json.loads(SYNTHETIC_EVENT_CONTRACT_BYTES),
        "event_contract_sha256": SYNTHETIC_EVENT_CONTRACT_SHA256,
        "event_parser_validator_sha256": implementation_sha256(
            parse_validate_synthetic_raw
        ),
        "event_projection": event_projection,
        "event_projector_sha256": implementation_sha256(
            project_validated_events
        ),
        "event_schema": json.loads(SYNTHETIC_EVENT_SCHEMA_BYTES),
        "event_schema_sha256": SYNTHETIC_EVENT_SCHEMA_SHA256,
        "final_output": final_axis.value,
        "process": {
            "exit_classification": "zero",
            "launch_status": "started",
            "stderr_capture": "empty",
            "stdout_capture": "nonempty",
            "timed_out": False,
            "tree_cleanup": "PASS",
        },
        "schema": PUBLIC_INPUT_SCHEMA,
        "task_execution": TaskExecutionAxis.MATCHED_EXPECTED.value,
    }


def _indeterminate(reason: str) -> Classification:
    return Classification(
        axes=AxisSnapshot(
            process=ProcessAxis.INDETERMINATE,
            turn_event=TurnEventAxis.INDETERMINATE,
            final_output=FinalOutputAxis.INDETERMINATE,
            task_execution=TaskExecutionAxis.INDETERMINATE,
        ),
        diagnostic_classes=(),
        overall=DiagnosticClass.INDETERMINATE,
        reasons=(reason,),
    )


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _validate_bound_value(
    value: object,
    claimed_digest: object,
    expected_value: Mapping[str, object],
    expected_digest: str,
    prefix: str,
    reasons: list[str],
) -> None:
    if not isinstance(value, dict):
        _append_reason(reasons, f"{prefix}_invalid")
        return
    try:
        actual_digest = _sha256(_json_bytes(value))
    except (TypeError, ValueError):
        _append_reason(reasons, f"{prefix}_invalid")
        return
    if claimed_digest != actual_digest:
        _append_reason(reasons, f"{prefix}_digest_mismatch")
        return
    if actual_digest != expected_digest or value != expected_value:
        _append_reason(reasons, f"{prefix}_not_authoritative")


def _validate_content_identities(
    value: object, reasons: list[str]
) -> dict[str, tuple[str, bytes]]:
    by_artifact: dict[str, tuple[str, bytes]] = {}
    if not isinstance(value, list):
        _append_reason(reasons, "content_identity_inventory_invalid")
        return by_artifact
    seen_fixtures: set[str] = set()
    for record in value:
        if not isinstance(record, dict) or set(record) != _CONTENT_FIELDS:
            _append_reason(reasons, "content_identity_fields_invalid")
            continue
        fixture_id = record.get("fixture_id")
        if not isinstance(fixture_id, str) or fixture_id not in _CONTENT_FIXTURES:
            _append_reason(reasons, "content_identity_fixture_invalid")
            continue
        if fixture_id in seen_fixtures:
            _append_reason(reasons, "content_identity_inventory_invalid")
            continue
        seen_fixtures.add(fixture_id)
        artifact, payload = _CONTENT_FIXTURES[fixture_id]
        record_valid = True
        if record.get("provenance") != SYNTHETIC_PROVENANCE:
            _append_reason(reasons, "content_identity_provenance_invalid")
            record_valid = False
        if record.get("artifact") != artifact:
            _append_reason(reasons, "content_identity_artifact_invalid")
            record_valid = False
        byte_count = record.get("bytes")
        if isinstance(byte_count, bool) or byte_count != len(payload):
            _append_reason(reasons, "content_identity_bytes_mismatch")
            record_valid = False
        if record.get("sha256") != _sha256(payload):
            _append_reason(reasons, "content_identity_digest_mismatch")
            record_valid = False
        if artifact in by_artifact:
            _append_reason(reasons, "content_identity_inventory_invalid")
            record_valid = False
        if record_valid:
            by_artifact[artifact] = (fixture_id, payload)
    return by_artifact


def _validate_content_consistency(
    content: Mapping[str, tuple[str, bytes]],
    process: Mapping[str, object] | None,
    final_axis: FinalOutputAxis,
    reasons: list[str],
) -> None:
    if process is not None:
        for artifact, capture_field in (
            ("stdout", "stdout_capture"),
            ("stderr", "stderr_capture"),
        ):
            capture = process.get(capture_field)
            record = content.get(artifact)
            payload = None if record is None else record[1]
            consistent = (
                (capture == "absent" and payload is None)
                or (capture == "empty" and payload == b"")
                or (
                    capture == "nonempty"
                    and isinstance(payload, bytes)
                    and len(payload) > 0
                )
                or (capture == "capture_failed" and payload is None)
            )
            if not consistent:
                _append_reason(
                    reasons, f"{artifact}_content_capture_contradiction"
                )

    final_record = content.get("final_message")
    expected_fixture = {
        FinalOutputAxis.CAPTURED_VALID: "synthetic_final_v1",
        FinalOutputAxis.CAPTURED_INVALID: "synthetic_final_invalid_v1",
    }.get(final_axis)
    if expected_fixture is None:
        if final_record is not None:
            _append_reason(reasons, "final_content_observation_contradiction")
    elif final_record is None or final_record[0] != expected_fixture:
        _append_reason(reasons, "final_content_observation_contradiction")


def _validate_process(
    value: object, reasons: list[str]
) -> tuple[ProcessAxis, dict[str, object] | None]:
    initial_reason_count = len(reasons)
    if not isinstance(value, dict) or set(value) != _PROCESS_FIELDS:
        _append_reason(reasons, "process_fields_invalid")
        return ProcessAxis.INDETERMINATE, None
    launch = value.get("launch_status")
    exit_classification = value.get("exit_classification")
    stdout_capture = value.get("stdout_capture")
    stderr_capture = value.get("stderr_capture")
    timed_out = value.get("timed_out")
    cleanup = value.get("tree_cleanup")
    if launch not in {"not_attempted", "started", "failed"}:
        _append_reason(reasons, "process_launch_status_invalid")
    if exit_classification not in {
        "zero",
        "nonzero",
        "signal_or_termination",
        "unavailable",
    }:
        _append_reason(reasons, "process_exit_classification_invalid")
    if stdout_capture not in {"absent", "empty", "nonempty", "capture_failed"}:
        _append_reason(reasons, "stdout_capture_invalid")
    if stderr_capture not in {"absent", "empty", "nonempty", "capture_failed"}:
        _append_reason(reasons, "stderr_capture_invalid")
    if not isinstance(timed_out, bool):
        _append_reason(reasons, "process_timeout_invalid")
    if cleanup not in {"PASS", "FAIL", "NOT_ATTEMPTED"}:
        _append_reason(reasons, "process_tree_cleanup_invalid")
    if len(reasons) != initial_reason_count:
        return ProcessAxis.INDETERMINATE, value
    if cleanup != "PASS":
        _append_reason(reasons, "process_tree_cleanup_incomplete")
    if stdout_capture == "capture_failed" or stderr_capture == "capture_failed":
        _append_reason(reasons, "stream_capture_failed")
    if launch == "not_attempted" or exit_classification == "unavailable":
        _append_reason(reasons, "process_observation_incomplete")
        return ProcessAxis.INDETERMINATE, value
    if launch == "failed" or timed_out or exit_classification in {
        "nonzero",
        "signal_or_termination",
    }:
        return ProcessAxis.PROCESS_EXECUTION_FAILURE, value
    return ProcessAxis.ZERO, value


def _validate_projection(
    value: object, reasons: list[str]
) -> TurnEventAxis:
    if not isinstance(value, list):
        _append_reason(reasons, "event_projection_not_array")
        return TurnEventAxis.INDETERMINATE
    markers: list[str] = []
    agent_message_count = 0
    for expected_ordinal, entry in enumerate(value):
        if not isinstance(entry, dict):
            _append_reason(reasons, "event_projection_entry_invalid")
            return TurnEventAxis.INDETERMINATE
        if set(entry) - {"ordinal", "marker", "item_marker"}:
            _append_reason(reasons, "event_projection_entry_fields_invalid")
            return TurnEventAxis.INDETERMINATE
        ordinal = entry.get("ordinal")
        if isinstance(ordinal, bool) or ordinal != expected_ordinal:
            _append_reason(reasons, "event_projection_ordinal_gap")
            return TurnEventAxis.INDETERMINATE
        marker = entry.get("marker")
        if not isinstance(marker, str) or marker not in _MARKERS:
            _append_reason(reasons, "event_projection_unknown_marker")
            return TurnEventAxis.INDETERMINATE
        markers.append(marker)
        item_marker = entry.get("item_marker")
        if marker in {"item_started", "item_completed"}:
            if item_marker is not None and item_marker not in _ITEM_MARKERS:
                _append_reason(reasons, "event_projection_unknown_item_marker")
                return TurnEventAxis.INDETERMINATE
            if marker == "item_completed" and item_marker == "agent_message":
                agent_message_count += 1
        elif "item_marker" in entry:
            _append_reason(reasons, "event_projection_item_marker_misplaced")
            return TurnEventAxis.INDETERMINATE
    if markers.count("turn_started") != 1:
        _append_reason(reasons, "event_projection_start_count_invalid")
        return TurnEventAxis.INDETERMINATE
    terminal_count = sum(marker in _TERMINALS for marker in markers)
    if terminal_count != 1:
        _append_reason(reasons, "event_projection_terminal_count_invalid")
        return TurnEventAxis.INDETERMINATE
    if not markers or markers[0] != "turn_started":
        _append_reason(reasons, "event_projection_start_order_invalid")
        return TurnEventAxis.INDETERMINATE
    if markers[-1] not in _TERMINALS:
        _append_reason(reasons, "event_projection_terminal_order_invalid")
        return TurnEventAxis.INDETERMINATE
    if markers[-1] == "turn_failed":
        return TurnEventAxis.TURN_FAILED
    if agent_message_count:
        return TurnEventAxis.TURN_COMPLETED_WITH_AGENT_MESSAGE
    return TurnEventAxis.TURN_COMPLETED_WITHOUT_AGENT_MESSAGE


def _enum_or_indeterminate(
    enum_type: type[Enum], value: object, reason: str, reasons: list[str]
) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        _append_reason(reasons, reason)
        return enum_type("INDETERMINATE")


def _classify(value: Mapping[str, object]) -> Classification:
    reasons: list[str] = []
    if "event_contract" not in value:
        return _indeterminate("event_contract_missing")
    if set(value) != _TOP_LEVEL_FIELDS:
        return _indeterminate("closed_input_fields_invalid")
    if value.get("schema") != PUBLIC_INPUT_SCHEMA:
        return _indeterminate("input_schema_invalid")

    _validate_bound_value(
        value.get("event_contract"),
        value.get("event_contract_sha256"),
        _EVENT_CONTRACT_VALUE,
        SYNTHETIC_EVENT_CONTRACT_SHA256,
        "event_contract",
        reasons,
    )
    _validate_bound_value(
        value.get("event_schema"),
        value.get("event_schema_sha256"),
        _EVENT_SCHEMA_VALUE,
        SYNTHETIC_EVENT_SCHEMA_SHA256,
        "event_schema",
        reasons,
    )
    if value.get("event_parser_validator_sha256") != implementation_sha256(
        parse_validate_synthetic_raw
    ):
        _append_reason(reasons, "event_parser_validator_identity_mismatch")
    if value.get("event_projector_sha256") != implementation_sha256(
        project_validated_events
    ):
        _append_reason(reasons, "event_projector_identity_mismatch")
    content = _validate_content_identities(
        value.get("content_identities"), reasons
    )

    process_axis, process = _validate_process(value.get("process"), reasons)
    final_axis = _enum_or_indeterminate(
        FinalOutputAxis,
        value.get("final_output"),
        "final_output_class_invalid",
        reasons,
    )
    task_axis = _enum_or_indeterminate(
        TaskExecutionAxis,
        value.get("task_execution"),
        "task_execution_class_invalid",
        reasons,
    )
    assert isinstance(final_axis, FinalOutputAxis)
    assert isinstance(task_axis, TaskExecutionAxis)

    _validate_content_consistency(content, process, final_axis, reasons)
    turn_axis = _validate_projection(value.get("event_projection"), reasons)
    event_authority_invalid = any(
        reason.startswith(
            (
                "event_contract_",
                "event_schema_",
                "event_parser_validator_",
                "event_projector_",
            )
        )
        for reason in reasons
    )
    projection_invalid = any(
        reason.startswith("event_projection_") for reason in reasons
    )
    if not event_authority_invalid and not projection_invalid:
        stdout_record = content.get("stdout")
        if stdout_record is None or not stdout_record[1]:
            _append_reason(reasons, "event_raw_unavailable")
        else:
            try:
                derived_projection = project_validated_events(
                    parse_validate_synthetic_raw(stdout_record[1])
                )
            except (TypeError, ValueError, KeyError):
                _append_reason(reasons, "event_raw_validation_failed")
            else:
                if derived_projection != value.get("event_projection"):
                    _append_reason(
                        reasons, "event_projection_derivation_mismatch"
                    )
    if any(reason.startswith("event_") for reason in reasons) or (
        "stdout_content_capture_contradiction" in reasons
    ):
        turn_axis = TurnEventAxis.INDETERMINATE

    if process is not None and process.get("timed_out") is True and turn_axis in {
        TurnEventAxis.TURN_COMPLETED_WITH_AGENT_MESSAGE,
        TurnEventAxis.TURN_COMPLETED_WITHOUT_AGENT_MESSAGE,
    }:
        _append_reason(reasons, "completed_turn_process_contradiction")
    if (
        process is not None
        and process.get("launch_status") in {"failed", "not_attempted"}
        and turn_axis != TurnEventAxis.INDETERMINATE
    ):
        _append_reason(reasons, "launch_terminal_contradiction")
    if task_axis in {
        TaskExecutionAxis.CAPTURE_FAILED,
        TaskExecutionAxis.INDETERMINATE,
    }:
        _append_reason(reasons, "task_observation_incomplete")
    if final_axis in {FinalOutputAxis.PATH_INVALID, FinalOutputAxis.INDETERMINATE}:
        _append_reason(reasons, "final_output_observation_inadmissible")
    if turn_axis == TurnEventAxis.INDETERMINATE:
        _append_reason(reasons, "turn_event_observation_inadmissible")
    if turn_axis == TurnEventAxis.TURN_COMPLETED_WITHOUT_AGENT_MESSAGE and final_axis in {
        FinalOutputAxis.CAPTURED_VALID,
        FinalOutputAxis.CAPTURED_INVALID,
        FinalOutputAxis.READ_FAILED,
    }:
        _append_reason(reasons, "final_present_without_agent_message")

    derived: list[DiagnosticClass] = []
    if process_axis == ProcessAxis.PROCESS_EXECUTION_FAILURE:
        derived.append(DiagnosticClass.PROCESS_EXECUTION_FAILURE)
    if (
        turn_axis == TurnEventAxis.TURN_COMPLETED_WITH_AGENT_MESSAGE
        and final_axis
        == FinalOutputAxis.NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE
    ):
        derived.append(
            DiagnosticClass.CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED
        )
    if turn_axis == TurnEventAxis.TURN_COMPLETED_WITHOUT_AGENT_MESSAGE:
        derived.append(DiagnosticClass.TURN_COMPLETED_WITHOUT_AGENT_MESSAGE)
    if final_axis == FinalOutputAxis.READ_FAILED:
        derived.append(DiagnosticClass.ADAPTER_CAPTURE_FAILURE)
    if final_axis == FinalOutputAxis.CAPTURED_INVALID:
        derived.append(DiagnosticClass.FINAL_SCHEMA_FAILURE)
    if task_axis in {
        TaskExecutionAxis.UNCHANGED_BASELINE,
        TaskExecutionAxis.OTHER_MISMATCH,
    }:
        derived.append(DiagnosticClass.TASK_EXECUTION_FAILURE)

    axes = AxisSnapshot(
        process=process_axis,
        turn_event=turn_axis,
        final_output=final_axis,
        task_execution=task_axis,
    )
    if reasons:
        return Classification(
            axes=axes,
            diagnostic_classes=tuple(derived),
            overall=DiagnosticClass.INDETERMINATE,
            reasons=tuple(reasons),
        )
    if len(derived) > 1:
        return Classification(
            axes=axes,
            diagnostic_classes=tuple(derived),
            overall=DiagnosticClass.MULTIPLE_FAILURES,
            reasons=(),
        )
    if len(derived) == 1:
        return Classification(
            axes=axes,
            diagnostic_classes=tuple(derived),
            overall=derived[0],
            reasons=(),
        )
    if (
        process_axis == ProcessAxis.ZERO
        and turn_axis == TurnEventAxis.TURN_COMPLETED_WITH_AGENT_MESSAGE
        and final_axis == FinalOutputAxis.CAPTURED_VALID
        and task_axis == TaskExecutionAxis.MATCHED_EXPECTED
    ):
        return Classification(
            axes=axes,
            diagnostic_classes=(DiagnosticClass.DIAGNOSTIC_PATH_COMPLETE,),
            overall=DiagnosticClass.DIAGNOSTIC_PATH_COMPLETE,
            reasons=(),
        )
    return Classification(
        axes=axes,
        diagnostic_classes=(),
        overall=DiagnosticClass.INDETERMINATE,
        reasons=("insufficient_admissible_evidence",),
    )


def classify_public_input(value: object) -> dict[str, object]:
    """Classify closed synthetic public observations and always fail closed."""

    if not isinstance(value, dict):
        return _indeterminate("input_not_object").as_public_value()
    try:
        return _classify(value).as_public_value()
    except Exception:
        return _indeterminate("classifier_input_invalid").as_public_value()


def canonical_classification_bytes(value: object) -> bytes:
    """Deterministically rebuild the public classification bytes."""

    return _json_bytes(classify_public_input(value))
