from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gate3_codex_calibration as calibration
import gate3_codex_live_canary as live
import test_gate3_codex_live_canary as fixtures


def _records(raw: bytes) -> list[dict[str, object]]:
    return [json.loads(line) for line in raw.splitlines()]


def _raw(records: list[dict[str, object]]) -> bytes:
    return b"".join(fixtures._line(record) for record in records)


def _collect(raw: bytes | None = None) -> calibration.CalibrationObservation:
    return calibration.collect(
        fixtures._rollout() if raw is None else raw,
        expected_workspace=fixtures.WORKSPACE,
        expected_prompt=b"frozen prompt",
        signed_identity={
            "cli_version": live.DEFAULT_CLI_VERSION,
            "comp_hash": live.DEFAULT_COMP_HASH,
            "effort": live.DEFAULT_REASONING,
            "model": live.DEFAULT_MODEL,
        },
    )


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (b"", "empty"),
        (b"{}", "not_newline_terminated"),
        (b"not-json\n", "invalid_json"),
        (b"[]\n", "non_object_record"),
    ],
)
def test_source_failures_are_fixed_vocabulary(raw: bytes, status: str) -> None:
    observation = _collect(raw)
    assert observation.source_status == status
    assert observation.wrapper_census == ()
    assert set(calibration.SOURCE_STATUSES) >= {status}


def test_collector_observes_context_and_wrappers_without_admission() -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"]["originator"] = "Observed Surface"
    records[0]["payload"]["source"] = "observed-source"
    records[1]["payload"]["approval_policy"] = "different"
    records.append(
        json.loads(
            fixtures._line(
                {
                    "payload": {
                        "call_id": "call-extra",
                        "input": fixtures._bad_wrapper("git status"),
                        "name": "exec",
                        "type": "custom_tool_call",
                    },
                    "timestamp": "2026-07-29T08:00:04Z",
                    "type": "response_item",
                }
            )
        )
    )
    observation = _collect(_raw(records))
    assert observation.private_ruling_values == {
        "originator": {"status": "single", "values": ("Observed Surface",)},
        "source": {"status": "single", "values": ("observed-source",)},
    }
    assert observation.public_context["enums"]["approval_policy"] == {
        "status": "unsafe"
    }
    assert len(observation.wrapper_census) == 2
    assert observation.wrapper_census[1]["field_name_census"] == {
        "known_field_counts": {"command": 1, "timeout_ms": 1, "workdir": 1},
        "total_field_count": 3,
        "unknown_field_count": 0,
    }
    assert not isinstance(observation, dict)


@pytest.mark.parametrize("record_type", ["session_meta", "turn_context"])
@pytest.mark.parametrize("count", [0, 2])
def test_context_cardinality_is_observed_not_admitted(
    record_type: str, count: int
) -> None:
    records = _records(fixtures._rollout())
    selected = [record for record in records if record["type"] == record_type]
    records = [record for record in records if record["type"] != record_type]
    records.extend(selected * count)
    observation = _collect(_raw(records))
    expected = "absent" if count == 0 else "multiple"
    assert observation.envelope_statuses[record_type] == expected
    assert observation.source_status == "ok"


def test_malformed_context_payload_does_not_hide_wrappers() -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"] = "not-an-object"
    observation = _collect(_raw(records))
    assert observation.envelope_statuses["session_meta"] == "malformed"
    assert len(observation.wrapper_census) == 1


def test_non_string_tool_input_is_censused_without_payload() -> None:
    records = _records(fixtures._rollout())
    records[-1]["payload"]["input"] = {
        "command": "Get-Content C:/Users/private/secret.txt"
    }
    observation = _collect(_raw(records))
    assert observation.wrapper_census[0]["input_status"] == "non_string"
    assert "Get-Content" not in json.dumps(observation.wrapper_census)


def test_public_projection_never_contains_open_ruling_values_or_paths() -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"]["originator"] = "Private Surface Label"
    records[0]["payload"]["source"] = "private-source"
    records[0]["payload"]["unknown_private_field"] = "private-value"
    observation = _collect(_raw(records))
    receipt = calibration.public_receipt(observation)
    encoded = live._json_bytes(receipt)
    assert b"Private Surface Label" not in encoded
    assert b"private-source" not in encoded
    assert b"unknown_private_field" not in encoded
    assert b"private-value" not in encoded
    assert fixtures.WORKSPACE.encode() not in encoded
    assert live._privacy_violations(encoded) == []
    assert receipt["unknown_context_field_count"] == 1
    assert receipt["unknown_context_class_counts"] == {
        field_class: int(field_class == "session_meta")
        for field_class in calibration.UNKNOWN_CONTEXT_CLASSES
    }
    private = calibration.private_evidence(observation)
    assert private["unknown_context_field_census"] == [
        {"class": "session_meta", "count": 1, "name": "unknown_private_field"}
    ]


@pytest.mark.parametrize(
    "private_value",
    [
        "C:/Users/private/secret.txt",
        "Bearer synthetic-private-token",
        "sk-synthetic-private-material",
    ],
)
def test_private_ruling_value_rejects_private_material(private_value: str) -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"]["originator"] = private_value
    observation = _collect(_raw(records))
    assert observation.private_ruling_values["originator"] == {
        "status": "unsafe",
        "values": (),
    }
    projection = observation.public_context["open_rulings"]["originator"]
    assert "private_value_retained" not in projection


def test_public_projection_rejects_arbitrary_string_injection() -> None:
    observation = _collect()
    observation.public_context["injected"] = "C:/Users/private/secret.txt"
    with pytest.raises(live.CanaryError, match="schema is not closed"):
        calibration.public_receipt(observation)


def test_public_projection_rejects_safe_but_unknown_wrapper_value() -> None:
    observation = _collect()
    observation.wrapper_census[0]["tool_family"] = "private_but_safe"
    with pytest.raises(live.CanaryError, match="wrapper census value"):
        calibration.public_receipt(observation)


def test_instruction_digest_separates_count_from_content() -> None:
    records = _records(fixtures._rollout())
    duplicate = next(
        record
        for record in records
        if record.get("payload", {}).get("role") == "developer"
    )
    records.append(duplicate)
    observation = _collect(_raw(records))
    assert observation.record_counts["developer_instruction"] == 2
    assert len(observation.instruction_record_sha256["developer"]) == 2
    assert len(set(observation.instruction_record_sha256["developer"])) == 1
    assert observation.instruction_content_anchor["developer"] == {
        "sha256": observation.instruction_record_sha256["developer"][0],
        "status": "single",
    }
    assert calibration.private_evidence(observation)[
        "ordered_developer_instruction_sha256"
    ] == observation.instruction_record_sha256["developer"]


def test_world_state_mutations_are_censused_without_acceptance() -> None:
    records = _records(fixtures._rollout())
    world = next(record for record in records if record["type"] == "world_state")
    world["payload"]["full"] = False
    observation = _collect(_raw(records))
    assert observation.world_state_status == "malformed"
    assert observation.world_state_census["full_true_count"] == 0


def test_publish_is_canonical_create_once_and_non_scoreable() -> None:
    observation = _collect()
    with tempfile.TemporaryDirectory(dir=HERE) as temporary:
        target = Path(temporary) / "calibration-receipt.json"
        calibration.publish(target, observation)
        receipt = json.loads(target.read_bytes())
        assert target.read_bytes() == live._json_bytes(receipt)
        assert receipt["schema"] == calibration.PUBLIC_RECEIPT_SCHEMA
        assert receipt["authorization"] == calibration.AUTHORIZATION
        assert receipt["admission_performed"] is False
        assert receipt["scoreable"] is False
        assert receipt["success_packet_capable"] is False
        assert "accepted" not in receipt
        assert "private_ruling_values" not in receipt
        with pytest.raises(Exception, match="create-once target already exists"):
            calibration.publish(target, observation)


def test_public_receipt_requires_calibration_observation_type() -> None:
    with pytest.raises(TypeError, match="calibration observation type"):
        calibration.public_receipt({})  # type: ignore[arg-type]


def test_identity_mismatch_does_not_publish_observed_value() -> None:
    observation = _collect(fixtures._rollout(model="PrivateProjectModel"))
    receipt = calibration.public_receipt(observation)
    encoded = live._json_bytes(receipt)
    assert receipt["public_context"]["identities"]["model"] == {
        "status": "mismatch"
    }
    assert b"PrivateProjectModel" not in encoded
    assert receipt["signed_identity"]["model"] == live.DEFAULT_MODEL


def test_unknown_context_count_requires_non_bool_nonnegative_integer() -> None:
    observation = _collect()
    for invalid in (False, True, -1, "Private Surface Label"):
        mutated = replace(observation, unknown_context_field_count=invalid)
        with pytest.raises(live.CanaryError, match="unknown context count"):
            calibration.private_evidence(mutated)
        with pytest.raises(live.CanaryError, match="unknown context count"):
            calibration.public_receipt(mutated)


@pytest.mark.parametrize(
    ("census", "message"),
    [
        ([], "census type"),
        (({"class": "unknown", "count": 1, "name": "field"},), "census value"),
        (({"class": "session_meta", "count": 1, "name": ""},), "census value"),
        (({"class": "session_meta", "count": True, "name": "field"},), "census value"),
        (({"class": "session_meta", "count": 0, "name": "field"},), "census value"),
        (
            (
                {"class": "session_meta", "count": 1, "name": "field"},
                {"class": "session_meta", "count": 1, "name": "field"},
            ),
            "repeats a field",
        ),
        (
            (
                {"class": "turn_context", "count": 1, "name": "z"},
                {"class": "session_meta", "count": 1, "name": "a"},
            ),
            "census order",
        ),
    ],
)
def test_unknown_context_census_mutations_fail_closed(
    census: object, message: str
) -> None:
    observation = _collect()
    mutated = replace(
        observation,
        unknown_context_field_census=census,  # type: ignore[arg-type]
        unknown_context_field_count=2,
    )
    with pytest.raises(live.CanaryError, match=message):
        calibration.private_evidence(mutated)
    with pytest.raises(live.CanaryError, match=message):
        calibration.public_receipt(mutated)


def test_unknown_context_census_total_must_match_public_count() -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"]["private_name"] = "private-value"  # type: ignore[index]
    observation = _collect(_raw(records))
    mutated = replace(observation, unknown_context_field_count=2)
    with pytest.raises(live.CanaryError, match="census total differs"):
        calibration.private_evidence(mutated)
    with pytest.raises(live.CanaryError, match="census total differs"):
        calibration.public_receipt(mutated)


def test_open_ruling_missing_null_and_multiple_are_distinct() -> None:
    records = _records(fixtures._rollout())
    del records[0]["payload"]["originator"]
    missing = _collect(_raw(records))
    assert missing.private_ruling_values["originator"]["status"] == "missing"
    assert missing.public_context["open_rulings"]["originator"]["presence_count"] == 0

    records[0]["payload"]["originator"] = None
    explicit_null = _collect(_raw(records))
    assert explicit_null.private_ruling_values["originator"]["status"] == "unsafe"
    assert explicit_null.public_context["open_rulings"]["originator"] == {
        "presence_count": 1,
        "json_types": ["null"],
        "length_buckets": ["not_string"],
    }

    second = json.loads(json.dumps(records[0]))
    records[0]["payload"]["originator"] = "SurfaceAlpha"
    second["payload"]["originator"] = "SurfaceBravo"
    records.insert(1, second)
    multiple = _collect(_raw(records))
    assert multiple.private_ruling_values["originator"] == {
        "status": "multiple",
        "values": ("SurfaceAlpha", "SurfaceBravo"),
    }


def test_nested_unknown_context_names_are_aggregate_only() -> None:
    records = _records(fixtures._rollout())
    settings = records[1]["payload"]["collaboration_mode"]["settings"]
    settings["private_nested_name"] = "not-published"
    records[1]["payload"]["permission_profile"]["private_permission"] = True
    observation = _collect(_raw(records))
    receipt = calibration.public_receipt(observation)
    encoded = live._json_bytes(receipt)
    assert receipt["unknown_context_field_count"] == 2
    assert b"private_nested_name" not in encoded
    assert b"private_permission" not in encoded
    assert b"not-published" not in encoded
    assert receipt["unknown_context_class_counts"] == {
        field_class: int(
            field_class in {"collaboration_settings", "permission_profile"}
        )
        for field_class in calibration.UNKNOWN_CONTEXT_CLASSES
    }
    assert calibration.private_evidence(observation)[
        "unknown_context_field_census"
    ] == [
        {
            "class": "collaboration_settings",
            "count": 1,
            "name": "private_nested_name",
        },
        {
            "class": "permission_profile",
            "count": 1,
            "name": "private_permission",
        },
    ]


def test_machine_unknown_elements_and_attributes_are_aggregate_only() -> None:
    records = _records(fixtures._rollout())
    machine = next(
        record
        for record in records
        if record.get("type") == "response_item"
        and "<environment_context>"
        in record.get("payload", {}).get("content", [{}])[0].get("text", "")
    )
    text = machine["payload"]["content"][0]["text"]
    machine["payload"]["content"][0]["text"] = text.replace(
        "</environment_context>",
        '<private_machine_field private_attr="x">secret</private_machine_field>'
        "</environment_context>",
    )
    observation = _collect(_raw(records))
    receipt = calibration.public_receipt(observation)
    encoded = live._json_bytes(receipt)
    assert receipt["unknown_context_field_count"] == 2
    assert b"private_machine_field" not in encoded
    assert b"private_attr" not in encoded
    assert b"secret" not in encoded
    assert receipt["unknown_context_class_counts"] == {
        field_class: int(
            field_class in {"machine_attribute", "machine_element"}
        )
        for field_class in calibration.UNKNOWN_CONTEXT_CLASSES
    }
    assert calibration.private_evidence(observation)[
        "unknown_context_field_census"
    ] == [
        {
            "class": "machine_attribute",
            "count": 1,
            "name": "private_machine_field@private_attr",
        },
        {
            "class": "machine_element",
            "count": 1,
            "name": "private_machine_field",
        },
    ]


def test_known_nested_and_machine_context_have_fixed_projections() -> None:
    receipt = calibration.public_receipt(_collect())
    context = receipt["public_context"]
    assert context["enums"]["permission_profile_type"] == {
        "status": "single_safe",
        "value": "disabled",
    }
    assert context["enums"]["sandbox_policy_type"] == {
        "status": "single_safe",
        "value": "danger-full-access",
    }
    assert context["enums"]["machine_shell"] == {
        "status": "single_safe",
        "value": "powershell",
    }
    assert context["enums"]["machine_file_system_type"] == {
        "status": "single_safe",
        "value": "unrestricted",
    }
    assert context["collaboration"]["model"] == {"status": "match"}
    assert context["dates"]["turn_current_date"]["value"] == fixtures.CURRENT_DATE


def test_impossible_dates_are_never_published_as_safe() -> None:
    records = _records(fixtures._rollout())
    records[1]["payload"]["current_date"] = "9999-99-99"
    machine = next(
        record
        for record in records
        if record.get("type") == "response_item"
        and "<environment_context>"
        in record.get("payload", {}).get("content", [{}])[0].get("text", "")
    )
    text = machine["payload"]["content"][0]["text"]
    machine["payload"]["content"][0]["text"] = text.replace(
        fixtures.CURRENT_DATE, "9999-99-99"
    )
    observation = _collect(_raw(records))
    assert observation.public_context["dates"] == {
        "machine_current_date": {"status": "unsafe"},
        "turn_current_date": {"status": "unsafe"},
    }

    observation.public_context["dates"]["turn_current_date"] = {
        "status": "single_safe",
        "value": "9999-99-99",
    }
    with pytest.raises(live.CanaryError, match="turn_current_date value is invalid"):
        calibration.public_receipt(observation)


def test_identifier_relations_are_fail_closed() -> None:
    observation = _collect()
    observation.public_context["identifiers"]["session_id"]["unique_count"] = 999
    with pytest.raises(live.CanaryError, match="unique count is inconsistent"):
        calibration.public_receipt(observation)

    observation = _collect()
    observation.public_context["identifiers"]["session_id"].update(
        {"presence_count": 0, "unique_count": 0}
    )
    with pytest.raises(live.CanaryError, match="presence shape is inconsistent"):
        calibration.public_receipt(observation)

    observation = _collect()
    observation.public_context["identifiers"]["session_id"] = {
        "presence_count": 1,
        "json_types": ["number", "string"],
        "length_buckets": ["1_16", "not_string"],
        "unique_count": 1,
    }
    with pytest.raises(live.CanaryError, match="presence count is inconsistent"):
        calibration.public_receipt(observation)

    observation = _collect()
    observation.public_context["identifiers"]["session_id"] = {
        "presence_count": 3,
        "json_types": ["number", "string"],
        "length_buckets": ["17_64", "1_16", "not_string"],
        "unique_count": 1,
    }
    with pytest.raises(live.CanaryError, match="unique bounds are inconsistent"):
        calibration.public_receipt(observation)


def test_open_ruling_relations_are_fail_closed() -> None:
    observation = _collect()
    observation.public_context["open_rulings"]["originator"] = {
        "presence_count": 0,
        "json_types": ["string"],
        "length_buckets": ["1_16"],
    }
    with pytest.raises(live.CanaryError, match="presence shape is inconsistent"):
        calibration.public_receipt(observation)

    observation = _collect()
    observation.public_context["open_rulings"]["originator"] = {
        "presence_count": 1,
        "json_types": ["number", "string"],
        "length_buckets": ["1_16", "not_string"],
    }
    with pytest.raises(live.CanaryError, match="presence count is inconsistent"):
        calibration.public_receipt(observation)


def test_session_identity_and_event_prompt_have_fixed_statuses() -> None:
    records = _records(fixtures._rollout())
    records[0]["payload"]["session_id"] = "different"
    records[6]["payload"]["message"] = "different prompt"
    observation = _collect(_raw(records))
    assert observation.envelope_statuses["session_identity"] == "malformed"
    assert observation.prompt_statuses["event_user_message"] == "mismatch"
    assert observation.record_counts["unmatched_event_prompt"] == 1


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (b"", "empty"),
        (b"{}", "not_newline_terminated"),
        (b"not-json\n", "invalid_json"),
        (b"[]\n", "non_object_record"),
    ],
)
def test_malformed_source_can_publish_closed_negative_receipt(
    raw: bytes, status: str
) -> None:
    observation = _collect(raw)
    receipt = calibration.public_receipt(observation)
    assert receipt["source_status"] == status
    assert set(receipt["record_counts"]) == set(calibration.RECORD_COUNT_FIELDS)
    assert set(receipt["envelope_statuses"]) == set(calibration.ENVELOPE_FIELDS)
    with tempfile.TemporaryDirectory(dir=HERE) as temporary:
        target = Path(temporary) / f"{status}.json"
        calibration.publish(target, observation)
        assert json.loads(target.read_bytes())["source_status"] == status


def test_wrapper_totals_and_ordinals_are_verified() -> None:
    observation = _collect()
    observation.wrapper_census[0]["field_name_census"]["total_field_count"] = 999
    with pytest.raises(live.CanaryError, match="wrapper census value"):
        calibration.public_receipt(observation)

    observation = _collect()
    observation.wrapper_census[0]["tool_call_ordinal"] = 2
    with pytest.raises(live.CanaryError, match="wrapper census value"):
        calibration.public_receipt(observation)


def test_instruction_anchor_is_recomputed_from_record_digests() -> None:
    observation = _collect()
    observation.instruction_content_anchor["developer"]["sha256"] = "0" * 64
    with pytest.raises(live.CanaryError, match="anchor differs"):
        calibration.public_receipt(observation)
