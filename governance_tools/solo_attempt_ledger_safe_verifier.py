#!/usr/bin/env python3
"""Whitelist-only pre-Attempt verifier for the Solo controller ledger."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Final


VERIFIER_SCHEMA: Final = "solo_attempt_ledger_safe_verifier.v1"
LEDGER_SCHEMA: Final = "solo_attempt_ledger.v1"
PAIR_ID_PATTERN: Final = re.compile(
    r"^solo-pair0-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
LABEL_PATTERN: Final = re.compile(r"^[0-9a-f]{32}$")

OUTPUT_KEYS: Final = (
    "verifier_schema",
    "status",
    "code",
    "schema_version",
    "event_type",
    "event_seq",
    "pair_id",
    "slot",
    "ledger_event_count",
    "pair_count",
    "attempt_count",
    "execution_event_count",
    "arm_execution_count",
    "task_exposure_count",
    "attempt_id_present",
    "controller_mapping_structure_present",
)

_EXECUTION_EVENT_TYPES: Final = {
    "TASK_EXPOSED",
    "EXECUTION_TERMINAL",
    "SCORING_RECORDED",
    "UNBLINDED",
}


def _result(*, status: str, code: str, **updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "verifier_schema": VERIFIER_SCHEMA,
        "status": status,
        "code": code,
        "schema_version": "UNAVAILABLE",
        "event_type": "UNAVAILABLE",
        "event_seq": 0,
        "pair_id": "UNAVAILABLE",
        "slot": "UNAVAILABLE",
        "ledger_event_count": 0,
        "pair_count": 0,
        "attempt_count": 0,
        "execution_event_count": 0,
        "arm_execution_count": 0,
        "task_exposure_count": 0,
        "attempt_id_present": False,
        "controller_mapping_structure_present": False,
    }
    result.update(updates)
    return result


def _read_events(path: Path) -> tuple[list[dict[str, Any]] | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "FILE_READ_ERROR"

    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        return None, "LEDGER_ENCODING_ERROR"

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, "LEDGER_ENCODING_ERROR"

    lines = text[:-1].split("\n")
    if not lines or any(not line for line in lines):
        return None, "LEDGER_LINE_FORMAT_ERROR"

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            return None, "LEDGER_JSON_ERROR"
        if not isinstance(event, dict):
            return None, "LEDGER_EVENT_TYPE_ERROR"
        events.append(event)
    return events, None


def _mapping_structure_is_valid(event: dict[str, Any]) -> bool:
    pair_record = event.get("pair_record")
    if not isinstance(pair_record, dict):
        return False
    if pair_record.get("label_mapping_scope") != "CONTROLLER_ONLY":
        return False
    if pair_record.get("execution_context_mapping_access") != "DENIED":
        return False
    if pair_record.get("scoring_context_mapping_access") != "DENIED":
        return False

    arms = pair_record.get("planned_arms")
    if not isinstance(arms, list) or len(arms) != 2:
        return False

    arm_names: set[str] = set()
    labels: set[str] = set()
    treatment_states: set[str] = set()
    for arm_record in arms:
        if not isinstance(arm_record, dict):
            return False
        arm_name = arm_record.get("arm")
        label = arm_record.get("anonymous_scoring_label")
        treatment_state = arm_record.get("treatment_state")
        if not isinstance(arm_name, str) or not isinstance(label, str):
            return False
        if not isinstance(treatment_state, str):
            return False
        if LABEL_PATTERN.fullmatch(label) is None:
            return False
        if arm_record.get("canonical_attempt_id") is not None:
            return False
        arm_names.add(arm_name)
        labels.add(label)
        treatment_states.add(treatment_state)

    return (
        arm_names == {"CONTROL", "TREATMENT"}
        and len(labels) == 2
        and treatment_states == {"ABSENT", "PACKET_FROZEN"}
    )


def verify_pre_attempt_ledger(path: Path) -> dict[str, object]:
    """Verify the Pair 0 pre-Attempt state without returning nested values."""

    events, read_error = _read_events(path)
    if read_error is not None:
        return _result(status="FAIL", code=read_error)
    assert events is not None

    event_count = len(events)
    pair_count = sum(event.get("event_type") == "PAIR_CREATED" for event in events)
    execution_event_count = sum(
        event.get("event_type") in _EXECUTION_EVENT_TYPES for event in events
    )
    task_exposure_count = sum(
        event.get("event_type") == "TASK_EXPOSED" for event in events
    )
    attempt_count = sum(event.get("attempt_id") is not None for event in events)

    safe_counts = {
        "ledger_event_count": event_count,
        "pair_count": pair_count,
        "attempt_count": attempt_count,
        "execution_event_count": execution_event_count,
        "task_exposure_count": task_exposure_count,
        "attempt_id_present": attempt_count > 0,
    }
    if event_count != 1:
        return _result(status="FAIL", code="LEDGER_EVENT_COUNT_ERROR", **safe_counts)

    event = events[0]
    if event.get("schema_version") != LEDGER_SCHEMA:
        return _result(status="FAIL", code="LEDGER_SCHEMA_ERROR", **safe_counts)
    if event.get("event_type") != "PAIR_CREATED":
        return _result(status="FAIL", code="FIRST_EVENT_ERROR", **safe_counts)
    if type(event.get("event_seq")) is not int or event["event_seq"] != 1:
        return _result(status="FAIL", code="EVENT_SEQUENCE_ERROR", **safe_counts)

    pair_id = event.get("pair_id")
    if not isinstance(pair_id, str) or PAIR_ID_PATTERN.fullmatch(pair_id) is None:
        return _result(status="FAIL", code="PAIR_ID_ERROR", **safe_counts)
    if event.get("slot") != "Pair 0":
        return _result(status="FAIL", code="PAIR_SLOT_ERROR", **safe_counts)
    if pair_count != 1 or attempt_count != 0 or execution_event_count != 0:
        return _result(status="FAIL", code="PRE_ATTEMPT_COUNT_ERROR", **safe_counts)

    mapping_valid = _mapping_structure_is_valid(event)
    if not mapping_valid:
        return _result(status="FAIL", code="MAPPING_STRUCTURE_ERROR", **safe_counts)

    execution = event.get("execution")
    admission = event.get("admission")
    execution_contract = event.get("execution_contract")
    if not all(isinstance(value, dict) for value in (execution, admission, execution_contract)):
        return _result(status="FAIL", code="PRE_ATTEMPT_STATE_ERROR", **safe_counts)
    assert isinstance(execution, dict)
    assert isinstance(admission, dict)
    assert isinstance(execution_contract, dict)

    arm_execution_count = execution.get("arm_executions")
    if type(arm_execution_count) is not int or arm_execution_count != 0:
        return _result(status="FAIL", code="ARM_EXECUTION_COUNT_ERROR", **safe_counts)
    if admission.get("task_exposure") != "NOT_EXPOSED":
        return _result(status="FAIL", code="TASK_EXPOSURE_STATE_ERROR", **safe_counts)
    if admission.get("execution_authorization") != "ABSENT":
        return _result(status="FAIL", code="AUTHORIZATION_STATE_ERROR", **safe_counts)
    if admission.get("attempt_id_creation") != "BLOCKED":
        return _result(status="FAIL", code="ATTEMPT_GATE_STATE_ERROR", **safe_counts)
    if execution_contract.get("execution_authorization") != "NOT_AUTHORIZED":
        return _result(status="FAIL", code="AUTHORIZATION_STATE_ERROR", **safe_counts)
    if execution_contract.get("attempt_id_creation") != "DENIED":
        return _result(status="FAIL", code="ATTEMPT_GATE_STATE_ERROR", **safe_counts)

    return _result(
        status="PASS",
        code="OK",
        schema_version=LEDGER_SCHEMA,
        event_type="PAIR_CREATED",
        event_seq=1,
        pair_id=pair_id,
        slot="Pair 0",
        arm_execution_count=0,
        controller_mapping_structure_present=True,
        **safe_counts,
    )


def render_result(result: dict[str, object]) -> str:
    """Render only the fixed flat scalar output contract."""

    if tuple(result.keys()) != OUTPUT_KEYS:
        raise ValueError("SAFE_OUTPUT_KEY_MISMATCH")
    if any(isinstance(value, (dict, list, tuple, set)) for value in result.values()):
        raise ValueError("SAFE_OUTPUT_NESTING_REJECTED")
    return json.dumps(result, ensure_ascii=True, sort_keys=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "--ledger":
        result = _result(status="FAIL", code="ARGUMENT_ERROR")
    else:
        try:
            result = verify_pre_attempt_ledger(Path(args[1]))
        except Exception:  # pragma: no cover - last-resort redaction boundary
            result = _result(status="FAIL", code="UNEXPECTED_ERROR")

    try:
        output = render_result(result)
    except Exception:  # pragma: no cover - fixed fail-closed fallback
        output = render_result(_result(status="FAIL", code="OUTPUT_CONTRACT_ERROR"))
        print(output)
        return 2
    print(output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
