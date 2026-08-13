from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_final_message_diagnostic as diagnostic


def _input(**kwargs: object) -> dict[str, object]:
    return diagnostic.build_synthetic_input(**kwargs)


def _classify(value: object) -> dict[str, object]:
    return diagnostic.classify_public_input(value)


def test_complete_synthetic_path_is_diagnostic_only_complete() -> None:
    result = _classify(_input())
    assert result == {
        "axes": {
            "final_output": "CAPTURED_VALID",
            "process": "ZERO",
            "task_execution": "MATCHED_EXPECTED",
            "turn_event": "TURN_COMPLETED_WITH_AGENT_MESSAGE",
        },
        "diagnostic_classes": ["DIAGNOSTIC_PATH_COMPLETE"],
        "overall": "DIAGNOSTIC_PATH_COMPLETE",
        "reasons": [],
        "schema": "gate3-route-v2.final-message-diagnostic-classification.v1",
    }


@pytest.mark.parametrize("exit_classification", ["nonzero", "signal_or_termination"])
def test_process_failure_does_not_erase_completed_turn(
    exit_classification: str,
) -> None:
    value = _input()
    value["process"]["exit_classification"] = exit_classification
    result = _classify(value)
    assert result["axes"]["process"] == "PROCESS_EXECUTION_FAILURE"
    assert result["axes"]["turn_event"] == "TURN_COMPLETED_WITH_AGENT_MESSAGE"
    assert result["overall"] == "PROCESS_EXECUTION_FAILURE"
    assert result["diagnostic_classes"] == ["PROCESS_EXECUTION_FAILURE"]


def test_completed_turn_without_agent_message_is_not_model_fault() -> None:
    value = _input(
        event_scenario="completed_without_agent",
        final_output="NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE",
    )
    result = _classify(value)
    assert result["axes"]["turn_event"] == "TURN_COMPLETED_WITHOUT_AGENT_MESSAGE"
    assert result["overall"] == "TURN_COMPLETED_WITHOUT_AGENT_MESSAGE"
    assert "MODEL" not in json.dumps(result, sort_keys=True)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda value: value.pop("event_contract"), "event_contract_missing"),
        (
            lambda value: value["event_contract"].update({"schema": "mutated"}),
            "event_contract_digest_mismatch",
        ),
        (
            lambda value: value.update({"event_contract_sha256": "0" * 64}),
            "event_contract_digest_mismatch",
        ),
        (
            lambda value: value["event_schema"].update({"schema": "mutated"}),
            "event_schema_digest_mismatch",
        ),
        (
            lambda value: value.update({"event_schema_sha256": "0" * 64}),
            "event_schema_digest_mismatch",
        ),
        (
            lambda value: value.pop("event_parser_validator_sha256"),
            "closed_input_fields_invalid",
        ),
        (
            lambda value: value.update({"event_parser_validator_sha256": "0" * 64}),
            "event_parser_validator_identity_mismatch",
        ),
        (
            lambda value: value.update({"event_projector_sha256": "0" * 64}),
            "event_projector_identity_mismatch",
        ),
    ],
)
def test_event_authority_mutations_fail_closed(
    mutation: object, reason: str
) -> None:
    value = _input()
    mutation(value)
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert reason in result["reasons"]
    assert result["axes"]["turn_event"] == "INDETERMINATE"


def test_event_authority_failure_does_not_erase_process_observation() -> None:
    value = _input()
    value["event_contract_sha256"] = "0" * 64
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert result["axes"]["process"] == "ZERO"
    assert result["axes"]["turn_event"] == "INDETERMINATE"


def test_raw_fixture_deterministically_derives_public_projection() -> None:
    value = _input()
    raw = diagnostic.synthetic_fixture_bytes("synthetic_stdout_v1")
    parsed = diagnostic.parse_validate_synthetic_raw(raw)
    assert diagnostic.project_validated_events(parsed) == value["event_projection"]


def test_structurally_valid_projection_not_derived_from_raw_fails_closed() -> None:
    value = _input()
    value["event_projection"] = [
        {"ordinal": 0, "marker": "turn_started"},
        {"ordinal": 1, "marker": "turn_completed"},
    ]
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert result["axes"]["turn_event"] == "INDETERMINATE"
    assert "event_projection_derivation_mismatch" in result["reasons"]


def test_parser_and_projector_identities_bind_executed_bytecode() -> None:
    value = _input()
    assert value["event_parser_validator_sha256"] == diagnostic.implementation_sha256(
        diagnostic.parse_validate_synthetic_raw
    )
    assert value["event_projector_sha256"] == diagnostic.implementation_sha256(
        diagnostic.project_validated_events
    )


def test_parser_identity_binds_raw_type_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _input()
    monkeypatch.setitem(
        diagnostic._RAW_TYPE_TO_MARKER, "item.completed", "turn_completed"
    )
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "event_parser_validator_identity_mismatch" in result["reasons"]
    assert "event_projector_identity_mismatch" in result["reasons"]


def test_parser_identity_binds_exception_dispatch_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function = diagnostic.parse_validate_synthetic_raw
    original_identity = diagnostic.implementation_sha256(function)
    assert function.__code__.co_exceptiontable
    monkeypatch.setattr(
        function,
        "__code__",
        function.__code__.replace(co_exceptiontable=b""),
    )
    assert diagnostic.implementation_sha256(function) != original_identity


def test_failed_turn_remains_an_axis_observation_not_model_fault() -> None:
    value = _input(
        event_scenario="turn_failed",
        final_output="ABSENT_AT_POST_TERMINATION_OBSERVATION",
    )
    result = _classify(value)
    assert result["axes"]["turn_event"] == "TURN_FAILED"
    assert result["overall"] == "INDETERMINATE"
    assert "MODEL" not in json.dumps(result, sort_keys=True)


@pytest.mark.parametrize(
    ("projection", "reason"),
    [
        ("not-an-array", "event_projection_not_array"),
        (
            [
                {"ordinal": 0, "marker": "turn_started"},
                {"ordinal": 1, "marker": "unknown"},
                {"ordinal": 2, "marker": "turn_completed"},
            ],
            "event_projection_unknown_marker",
        ),
        (
            [
                {"ordinal": 0, "marker": "turn_started"},
                {"ordinal": 2, "marker": "turn_completed"},
            ],
            "event_projection_ordinal_gap",
        ),
        (
            [
                {"ordinal": 0, "marker": "turn_started"},
                {"ordinal": 1, "marker": "turn_completed"},
                {"ordinal": 2, "marker": "turn_completed"},
            ],
            "event_projection_terminal_count_invalid",
        ),
        (
            [
                {"ordinal": 0, "marker": "turn_completed"},
                {"ordinal": 1, "marker": "turn_started"},
            ],
            "event_projection_start_order_invalid",
        ),
        (
            [
                {"ordinal": 0, "marker": "turn_started"},
                {"ordinal": 1, "marker": "turn_completed"},
                {"ordinal": 2, "marker": "turn_failed"},
            ],
            "event_projection_terminal_count_invalid",
        ),
    ],
)
def test_projection_mutations_fail_closed(
    projection: object, reason: str
) -> None:
    value = _input()
    value["event_projection"] = projection
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert reason in result["reasons"]


@pytest.mark.parametrize(
    ("final_class", "expected_overall"),
    [
        ("ABSENT_AT_POST_TERMINATION_OBSERVATION", "INDETERMINATE"),
        (
            "NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE",
            "CLI_FINAL_OUTPUT_MATERIALIZATION_NOT_OBSERVED",
        ),
        ("CREATED_THEN_REMOVED", "INDETERMINATE"),
        ("CAPTURED_VALID", "DIAGNOSTIC_PATH_COMPLETE"),
        ("CAPTURED_INVALID", "FINAL_SCHEMA_FAILURE"),
        ("READ_FAILED", "ADAPTER_CAPTURE_FAILURE"),
        ("PATH_INVALID", "INDETERMINATE"),
        ("INDETERMINATE", "INDETERMINATE"),
    ],
)
def test_every_final_output_class_has_closed_disposition(
    final_class: str, expected_overall: str
) -> None:
    value = _input(final_output=final_class)
    result = _classify(value)
    assert result["axes"]["final_output"] == final_class
    assert result["overall"] == expected_overall


@pytest.mark.parametrize(
    ("task_class", "expected_overall"),
    [
        ("MATCHED_EXPECTED", "DIAGNOSTIC_PATH_COMPLETE"),
        ("UNCHANGED_BASELINE", "TASK_EXECUTION_FAILURE"),
        ("OTHER_MISMATCH", "TASK_EXECUTION_FAILURE"),
        ("CAPTURE_FAILED", "INDETERMINATE"),
        ("INDETERMINATE", "INDETERMINATE"),
    ],
)
def test_every_task_class_has_closed_disposition(
    task_class: str, expected_overall: str
) -> None:
    value = _input()
    value["task_execution"] = task_class
    result = _classify(value)
    assert result["axes"]["task_execution"] == task_class
    assert result["overall"] == expected_overall
    if task_class in {"CAPTURE_FAILED", "INDETERMINATE"}:
        assert "TASK_EXECUTION_FAILURE" not in result["diagnostic_classes"]


def test_timeout_with_completed_terminal_is_contradictory() -> None:
    value = _input()
    value["process"]["timed_out"] = True
    value["process"]["exit_classification"] = "signal_or_termination"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "completed_turn_process_contradiction" in result["reasons"]


@pytest.mark.parametrize("launch_status", ["failed", "not_attempted"])
def test_unlaunched_process_with_terminal_fails_closed(launch_status: str) -> None:
    value = _input()
    value["process"]["launch_status"] = launch_status
    if launch_status == "not_attempted":
        value["process"]["exit_classification"] = "unavailable"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "launch_terminal_contradiction" in result["reasons"]


@pytest.mark.parametrize(
    ("field", "replacement", "reason"),
    [
        ("timed_out", "yes", "process_timeout_invalid"),
        ("exit_classification", "success", "process_exit_classification_invalid"),
        ("tree_cleanup", "UNKNOWN", "process_tree_cleanup_invalid"),
    ],
)
def test_invalid_process_values_fail_closed(
    field: str, replacement: object, reason: str
) -> None:
    value = _input()
    value["process"][field] = replacement
    result = _classify(value)
    assert result["axes"]["process"] == "INDETERMINATE"
    assert result["overall"] == "INDETERMINATE"
    assert reason in result["reasons"]


def test_compatible_orthogonal_failures_remain_visible() -> None:
    value = _input(final_output="CAPTURED_INVALID")
    value["task_execution"] = "UNCHANGED_BASELINE"
    result = _classify(value)
    assert result["overall"] == "MULTIPLE_FAILURES"
    assert result["diagnostic_classes"] == [
        "FINAL_SCHEMA_FAILURE",
        "TASK_EXECUTION_FAILURE",
    ]


def test_capture_failure_has_fail_closed_precedence_over_other_failures() -> None:
    value = _input()
    value["process"]["exit_classification"] = "nonzero"
    value["task_execution"] = "CAPTURE_FAILED"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert result["axes"]["process"] == "PROCESS_EXECUTION_FAILURE"
    assert "TASK_EXECUTION_FAILURE" not in result["diagnostic_classes"]


def test_fixed_synthetic_content_identities_are_accepted() -> None:
    result = _classify(_input())
    assert result["overall"] == "DIAGNOSTIC_PATH_COMPLETE"
    assert not any(reason.startswith("content_identity") for reason in result["reasons"])


def test_nonempty_stdout_identity_with_empty_capture_fails_closed() -> None:
    value = _input()
    value["process"]["stdout_capture"] = "empty"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "stdout_content_capture_contradiction" in result["reasons"]


def test_empty_stderr_identity_with_nonempty_capture_fails_closed() -> None:
    value = _input()
    value["process"]["stderr_capture"] = "nonempty"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "stderr_content_capture_contradiction" in result["reasons"]


def test_final_content_identity_with_no_creation_fails_closed() -> None:
    value = _input()
    value["final_output"] = "NO_CREATION_OBSERVED_DURING_COMPLETE_LIFECYCLE"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert "final_content_observation_contradiction" in result["reasons"]


@pytest.mark.parametrize(
    ("field", "replacement", "reason"),
    [
        ("provenance", "live_model_content", "content_identity_provenance_invalid"),
        ("sha256", "0" * 64, "content_identity_digest_mismatch"),
        ("fixture_id", "unapproved", "content_identity_fixture_invalid"),
    ],
)
def test_unapproved_content_digest_identity_fails_closed(
    field: str, replacement: str, reason: str
) -> None:
    value = _input()
    value["content_identities"][0][field] = replacement
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    assert reason in result["reasons"]


def test_unknown_public_field_fails_closed_without_echoing_value() -> None:
    value = _input()
    value["private_model_text"] = "must-not-appear"
    result = _classify(value)
    assert result["overall"] == "INDETERMINATE"
    encoded = diagnostic.canonical_classification_bytes(value)
    assert b"must-not-appear" not in encoded
    assert "closed_input_fields_invalid" in result["reasons"]


@pytest.mark.parametrize("invalid", [None, [], "bad", 7, {"schema": "bad"}])
def test_completely_invalid_input_never_raises_and_fails_closed(
    invalid: object,
) -> None:
    result = _classify(invalid)
    assert result["overall"] == "INDETERMINATE"
    assert result["axes"] == {
        "final_output": "INDETERMINATE",
        "process": "INDETERMINATE",
        "task_execution": "INDETERMINATE",
        "turn_event": "INDETERMINATE",
    }
    assert result["reasons"]


def test_canonical_reconstruction_is_deterministic() -> None:
    first = _input()
    second = copy.deepcopy(first)
    second = {key: second[key] for key in reversed(tuple(second))}
    assert diagnostic.canonical_classification_bytes(first) == (
        diagnostic.canonical_classification_bytes(second)
    )


def test_classifier_does_not_perform_io() -> None:
    assert not hasattr(diagnostic, "Path")
    assert not hasattr(diagnostic, "subprocess")
    assert not hasattr(diagnostic, "socket")


def test_no_admissible_terminal_dead_enum_is_removed() -> None:
    assert not hasattr(diagnostic.TurnEventAxis, "NO_ADMISSIBLE_TERMINAL")
