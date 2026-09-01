from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import UUID

import pytest

from governance_tools import solo_attempt_ledger_v2 as ledger


def _uuid(number: int) -> str:
    return str(UUID(int=number, version=4))


def _handle(number: int) -> str:
    return hashlib.sha256(f"handle-{number}".encode()).hexdigest()


def _digest(number: int) -> str:
    return hashlib.sha256(f"sealed-{number}".encode()).hexdigest()


def _genesis() -> dict[str, object]:
    return {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": 1,
        "event_type": "V2_GENESIS",
        "event_id": _uuid(1),
        "timestamp_utc": "2026-08-31T00:00:00Z",
        "evaluation_id": _uuid(9000),
        "predecessor_digest": ledger.V1_LEDGER_SHA256,
        "adopted_protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
        "adopted_contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
        "adopted_schema_id": ledger.ADOPTED_SCHEMA_ID,
        "legacy_pair_id": ledger.LEGACY_PAIR_ID,
        "legacy_pair_state_at_v1": "PAIR_CREATED",
        "legacy_pair_attempts_used": 0,
        "legacy_pair_disposition": "PRE_ATTEMPT_TERMINATION",
        "attempt_ceiling_total": 14,
        "attempt_ceiling_breakdown": dict(ledger.ATTEMPT_CEILING_BREAKDOWN),
    }


def _common(
    events: list[dict[str, object]], event_type: str, pair_id: str | None, slot: str
) -> dict[str, object]:
    sequence = len(events) + 1
    return {
        "schema_version": ledger.LEDGER_SCHEMA,
        "event_seq": sequence,
        "event_type": event_type,
        "event_id": _uuid(sequence),
        "timestamp_utc": f"2026-08-31T00:00:{sequence % 60:02d}Z",
        "pair_id": pair_id,
        "slot": slot,
    }


def _frozen_identities() -> dict[str, str]:
    return {
        "protocol_sha256": ledger.ADOPTED_PROTOCOL_SHA256,
        "contract_sha256": ledger.ADOPTED_CONTRACT_SHA256,
        "schema_id": ledger.ADOPTED_SCHEMA_ID,
        "qualification_record_sha256": "a" * 64,
        "historical_base_commit": "b" * 40,
        "historical_fix_commit": "c" * 40,
        "oracle_blob_sha256": "d" * 64,
    }


def _admission(exposed: bool = False) -> dict[str, object]:
    return {
        "status": "ADMITTED",
        "preflight_ids": ["preflight-v2"],
        "task_exposure_state": "EXPOSED" if exposed else "NONE",
    }


def _correctness() -> dict[str, object]:
    return {
        "oracle_status": "PASS",
        "required_case_count": 7,
        "passed_case_count": 7,
        "regression_status": "NONE",
        "scope_status": "WITHIN_SCOPE",
    }


def _pair_created(
    events: list[dict[str, object]], slot: str, pair_id: str
) -> dict[str, object]:
    return {
        **_common(events, "PAIR_CREATED", pair_id, slot),
        "category": "bugfix",
        "repository": "synthetic-consumer",
        "frozen_identities": _frozen_identities(),
    }


def _pre_attempt_failure(
    events: list[dict[str, object]],
    pair_id: str | None,
    slot: str,
    *,
    category: str = "bugfix",
    repository: str = "synthetic-consumer",
) -> dict[str, object]:
    return {
        **_common(events, "PRE_ATTEMPT_INFRA_FAILURE", pair_id, slot),
        "category": category,
        "repository": repository,
        "admission_result": {
            "status": "FAIL_CLOSED",
            "preflight_ids": ["preflight-v2"],
            "task_exposure_state": "NONE",
        },
    }


def _append_complete_pair(
    events: list[dict[str, object]], slot: str, pair_id: str, seed: int
) -> None:
    events.append(_pair_created(events, slot, pair_id))
    for arm_offset in range(2):
        handle = _handle(seed + arm_offset)
        events.append(
            {
                **_common(events, "ATTEMPT_ADMITTED", pair_id, slot),
                "attempt_handle": handle,
                "attempt_state": "ADMITTED",
                "admission_result": _admission(),
            }
        )
        events.append(
            {
                **_common(events, "TASK_EXPOSED", pair_id, slot),
                "attempt_handle": handle,
                "attempt_state": "TASK_EXPOSED",
                "admission_result": _admission(exposed=True),
            }
        )
        events.append(
            {
                **_common(events, "EXECUTION_TERMINAL", pair_id, slot),
                "attempt_handle": handle,
                "attempt_state": "TERMINAL",
                "correctness_result": _correctness(),
                "cost_metrics": {"elapsed_ms": 10, "tool_calls": 2},
            }
        )
    sealed_digest = _digest(seed)
    events.append(
        {
            **_common(events, "CONTROLLER_STATE_SEALED", pair_id, slot),
            "sealed_package_digest": sealed_digest,
            "score_count": 0,
        }
    )
    events.append(
        {
            **_common(events, "SCORING_RECORDED", pair_id, slot),
            "sealed_package_digest": sealed_digest,
            "score_count": 2,
        }
    )
    events.append(
        {
            **_common(events, "UNBLINDING_RECORDED", pair_id, slot),
            "sealed_package_digest": sealed_digest,
            "score_count": 2,
        }
    )


def _complete_shakedown() -> list[dict[str, object]]:
    events = [_genesis()]
    _append_complete_pair(events, "R2-SHAKEDOWN", "pair-r2-shakedown", 100)
    return events


def _assert_code(events: list[dict[str, object]], expected: str) -> None:
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.validate_ledger_events(events)
    assert caught.value.code == expected
    assert str(caught.value) == expected


def test_complete_shakedown_history_has_public_scalar_summary() -> None:
    summary = ledger.validate_ledger_events(_complete_shakedown())

    assert summary == ledger.LedgerSummary(
        schema_version=ledger.LEDGER_SCHEMA,
        ledger_event_count=11,
        pair_count=1,
        admitted_attempt_count=2,
        initiated_attempt_count=2,
        terminal_execution_count=2,
        scoring_record_count=1,
        unblinding_record_count=1,
        attempt_ceiling_total=14,
        next_event_seq=12,
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda event: event.update({"arm": "CONTROL"}),
        lambda event: event["frozen_identities"].update({"extra": "secret"}),
        lambda event: event["frozen_identities"].update(
            {"historical_fix_commit": "not-a-commit"}
        ),
    ],
)
def test_closed_schema_rejects_unknown_or_invalid_public_fields(mutator) -> None:
    events = _complete_shakedown()
    mutator(events[1])
    _assert_code(events, ledger.LEDGER_SCHEMA_FAILURE)


def test_attempt_event_cannot_carry_sealed_digest_join_key() -> None:
    events = _complete_shakedown()
    events[2]["sealed_package_digest"] = "e" * 64
    _assert_code(events, ledger.LEDGER_SCHEMA_FAILURE)


def test_composites_reject_nested_values_and_boolean_counts() -> None:
    events = _complete_shakedown()
    events[2]["admission_result"]["preflight_ids"] = [{"nested": "forbidden"}]
    _assert_code(events, ledger.LEDGER_SCHEMA_FAILURE)

    events = _complete_shakedown()
    events[4]["correctness_result"]["required_case_count"] = True
    _assert_code(events, ledger.LEDGER_SCHEMA_FAILURE)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda event: event.update({"legacy_pair_attempts_used": False}),
        lambda event: event.update({"attempt_ceiling_total": 14.0}),
        lambda event: event["attempt_ceiling_breakdown"].update(
            {"R2-SHAKEDOWN": 2.0}
        ),
    ],
)
def test_genesis_requires_exact_integer_types(mutator) -> None:
    genesis = _genesis()
    mutator(genesis)

    _assert_code([genesis], ledger.LEDGER_SCHEMA_FAILURE)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-W36-1T00:00:00Z",
        "2026-08-31T00:00Z",
        "2026-08-31T00:00:00+0000",
        "2026-08-31T00:00:00+00:00",
        "2026-08-31 00:00:00Z",
    ],
)
def test_genesis_rejects_non_frozen_timestamp_profiles(timestamp: str) -> None:
    genesis = _genesis()
    genesis["timestamp_utc"] = timestamp

    _assert_code([genesis], ledger.LEDGER_SCHEMA_FAILURE)


def test_genesis_accepts_canonical_frozen_timestamp() -> None:
    summary = ledger.validate_ledger_events([_genesis()])

    assert summary.ledger_event_count == 1


def test_fixed_error_does_not_echo_secret_like_input() -> None:
    sentinel = "SECRET-CONTROLLER-MAPPING-SENTINEL"
    events = _complete_shakedown()
    events[1]["controller_state"] = sentinel

    with pytest.raises(ledger.LedgerError) as caught:
        ledger.validate_ledger_events(events)

    assert sentinel not in str(caught.value)
    assert str(caught.value) == ledger.LEDGER_SCHEMA_FAILURE


def test_sequence_duplicate_id_and_transition_gaps_fail_closed() -> None:
    events = _complete_shakedown()
    events[3]["event_seq"] = 99
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)

    events = _complete_shakedown()
    events[3]["event_id"] = events[2]["event_id"]
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)

    events = _complete_shakedown()
    del events[3]
    for sequence, event in enumerate(events, start=1):
        event["event_seq"] = sequence
        event["event_id"] = _uuid(sequence)
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_analytic_pair_requires_completed_shakedown() -> None:
    events = [_genesis(), _pair_created([_genesis()], "R2-SHAKEDOWN", "pair-r2")]
    events.append(_pair_created(events, "A1", "pair-a1"))
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_r2_pair_cannot_reuse_legacy_pair_identity() -> None:
    events = [_genesis()]
    events.append(_pair_created(events, "R2-SHAKEDOWN", ledger.LEGACY_PAIR_ID))
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_pre_pair_failure_is_terminal_and_analytic_slot_waits_for_shakedown() -> None:
    events = [_genesis()]
    events.append(_pre_attempt_failure(events, None, "R2-SHAKEDOWN"))
    summary = ledger.validate_ledger_events(events)
    assert summary.pair_count == 0
    assert summary.admitted_attempt_count == 0
    assert summary.initiated_attempt_count == 0

    events = [_genesis()]
    failure = _pre_attempt_failure(events, None, "A1")
    failure["admission_result"]["status"] = "REFUSED"
    events.append(failure)
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_pre_attempt_failure_rejects_null_pair_after_pair_creation() -> None:
    events = [_genesis()]
    events.append(_pair_created(events, "R2-SHAKEDOWN", "pair-r2"))
    events.append(_pre_attempt_failure(events, None, "R2-SHAKEDOWN"))

    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "different-category"),
        ("repository", "different-repository"),
    ],
)
def test_pre_attempt_failure_rejects_mismatched_pair_binding(
    field: str, value: str
) -> None:
    events = [_genesis()]
    pair_id = "pair-r2"
    events.append(_pair_created(events, "R2-SHAKEDOWN", pair_id))
    failure = _pre_attempt_failure(events, pair_id, "R2-SHAKEDOWN")
    failure[field] = value
    events.append(failure)

    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_pre_attempt_failure_accepts_exact_existing_pair_binding() -> None:
    events = [_genesis()]
    pair_id = "pair-r2"
    events.append(_pair_created(events, "R2-SHAKEDOWN", pair_id))
    events.append(_pre_attempt_failure(events, pair_id, "R2-SHAKEDOWN"))

    summary = ledger.validate_ledger_events(events)

    assert summary.pair_count == 1
    assert summary.admitted_attempt_count == 0
    assert summary.initiated_attempt_count == 0


def test_admitted_not_exposed_reserves_handle_without_consumption_and_stops() -> None:
    events = [_genesis()]
    pair_id = "pair-r2-shakedown"
    handle = _handle(501)
    events.append(_pair_created(events, "R2-SHAKEDOWN", pair_id))
    events.append(
        {
            **_common(events, "ATTEMPT_ADMITTED", pair_id, "R2-SHAKEDOWN"),
            "attempt_handle": handle,
            "attempt_state": "ADMITTED",
            "admission_result": _admission(),
        }
    )
    events.append(
        {
            **_common(events, "ADMITTED_NOT_EXPOSED", pair_id, "R2-SHAKEDOWN"),
            "attempt_handle": handle,
            "attempt_state": "ADMITTED_NOT_EXPOSED",
            "admission_result": _admission(),
        }
    )

    summary = ledger.validate_ledger_events(events)
    assert summary.admitted_attempt_count == 1
    assert summary.initiated_attempt_count == 0

    events.append(_pair_created(events, "A1", "pair-a1"))
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_premature_unblinding_is_terminal_and_requires_matching_digest() -> None:
    events = _complete_shakedown()[:-2]
    pair_id = "pair-r2-shakedown"
    digest = events[-1]["sealed_package_digest"]
    events.append(
        {
            **_common(events, "PREMATURE_UNBLINDING", pair_id, "R2-SHAKEDOWN"),
            "sealed_package_digest": digest,
            "score_count": 0,
        }
    )
    ledger.validate_ledger_events(events)

    events.append(_pair_created(events, "A1", "pair-a1"))
    _assert_code(events, ledger.LEDGER_TRANSITION_FAILURE)


def test_all_slots_reach_exact_fourteen_attempt_ceiling() -> None:
    events = [_genesis()]
    for index, slot in enumerate(ledger.SLOTS):
        _append_complete_pair(events, slot, f"pair-{slot.lower()}", 1000 + index * 10)

    summary = ledger.validate_ledger_events(events)
    assert summary.pair_count == 7
    assert summary.admitted_attempt_count == 14
    assert summary.initiated_attempt_count == 14
    assert summary.attempt_ceiling_total == 14


def test_append_writes_strict_utf8_lf_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    events = _complete_shakedown()

    for event in events:
        summary = ledger.append_event(path, event)

    data = path.read_bytes()
    assert data.endswith(b"\n")
    assert b"\r" not in data
    assert not data.startswith(b"\xef\xbb\xbf")
    assert summary == ledger.validate_ledger_file(path)
    assert ledger.read_ledger(path) == events


def test_create_genesis_ledger_atomically_publishes_exactly_one_event(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    genesis = _genesis()

    summary = ledger.create_genesis_ledger(path, genesis)

    assert path.read_bytes() == ledger.encode_event(genesis)
    assert ledger.read_ledger(path) == [genesis]
    assert summary == ledger.validate_ledger_file(path)
    assert summary.ledger_event_count == 1
    assert summary.pair_count == 0
    assert summary.initiated_attempt_count == 0
    assert summary.next_event_seq == 2
    assert not path.with_name(f".{path.name}.tmp").exists()
    assert (
        ledger.classify_genesis_publication(path, genesis)
        == ledger.GENESIS_PUBLICATION_VALID
    )


def test_create_genesis_publishes_the_validated_snapshot_not_mutated_caller_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    genesis = _genesis()
    expected = deepcopy(genesis)
    real_fsync = ledger.os.fsync

    def mutate_caller_after_write(file_descriptor: int) -> None:
        real_fsync(file_descriptor)
        genesis["attempt_ceiling_breakdown"]["A1"] = 999

    monkeypatch.setattr(ledger.os, "fsync", mutate_caller_after_write)
    summary = ledger.create_genesis_ledger(path, genesis)

    assert genesis != expected
    assert ledger.read_ledger(path) == [expected]
    assert summary == ledger.validate_ledger_file(path)
    assert (
        ledger.classify_genesis_publication(path, expected)
        == ledger.GENESIS_PUBLICATION_VALID
    )


def test_create_genesis_rejects_existing_target_or_temporary_without_overwrite(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    path.write_bytes(b"existing-target\n")
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.create_genesis_ledger(path, _genesis())
    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert path.read_bytes() == b"existing-target\n"

    path.unlink()
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(b"existing-temporary")
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.create_genesis_ledger(path, _genesis())
    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert not path.exists()
    assert temporary.read_bytes() == b"existing-temporary"


def test_create_genesis_fsync_failure_keeps_canonical_absent_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"

    def fail_fsync(_file_descriptor: int) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(ledger.os, "fsync", fail_fsync)
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.create_genesis_ledger(path, _genesis())

    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert not path.exists()
    assert not path.with_name(f".{path.name}.tmp").exists()


def test_create_genesis_pre_replace_inspection_failure_cleans_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    real_exists = ledger._path_entry_exists
    calls = 0

    def fail_third_inspection(candidate: Path) -> bool:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise ledger.LedgerError(ledger.LEDGER_APPEND_FAILURE)
        return real_exists(candidate)

    monkeypatch.setattr(ledger, "_path_entry_exists", fail_third_inspection)
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.create_genesis_ledger(path, _genesis())

    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert not path.exists()
    assert not path.with_name(f".{path.name}.tmp").exists()


@pytest.mark.parametrize(
    ("replace_outcome", "expected_state", "target_exists", "target_valid"),
    [
        ("absent", ledger.GENESIS_PUBLICATION_ABSENT, False, False),
        ("valid", ledger.GENESIS_PUBLICATION_VALID, True, True),
        ("invalid", ledger.GENESIS_PUBLICATION_INVALID, True, False),
    ],
)
def test_create_genesis_uncertain_replace_classifies_once_without_retry_or_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replace_outcome: str,
    expected_state: str,
    target_exists: bool,
    target_valid: bool,
) -> None:
    path = tmp_path / f"{replace_outcome}.v2.ndjson"
    genesis = _genesis()
    real_replace = ledger.os.replace
    calls = 0

    def uncertain_replace(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if replace_outcome == "valid":
            real_replace(source, target)
        elif replace_outcome == "invalid":
            target.write_bytes(b"partial-or-invalid")
        raise OSError("synthetic uncertain replace")

    monkeypatch.setattr(ledger.os, "replace", uncertain_replace)
    with pytest.raises(ledger.GenesisPublicationError) as caught:
        ledger.create_genesis_ledger(path, genesis)

    assert calls == 1
    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert caught.value.publication_state == expected_state
    assert path.exists() is target_exists
    if target_exists:
        assert (
            ledger.classify_genesis_publication(path, genesis)
            == (ledger.GENESIS_PUBLICATION_VALID if target_valid else ledger.GENESIS_PUBLICATION_INVALID)
        )
    assert path.with_name(f".{path.name}.tmp").exists() is (replace_outcome != "valid")


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_unicode_line_separators_round_trip_inside_json_strings(
    tmp_path: Path, separator: str
) -> None:
    path = tmp_path / f"unicode-{ord(separator):04x}.ndjson"
    events = [_genesis()]
    pair = _pair_created(events, "R2-SHAKEDOWN", "pair-r2")
    pair["category"] = f"bugfix{separator}category"
    events.append(pair)

    for event in events:
        ledger.append_event(path, event)

    assert separator.encode("utf-8") in path.read_bytes()
    assert ledger.read_ledger(path) == events
    assert ledger.validate_ledger_file(path).pair_count == 1


def test_append_rejects_candidate_before_write(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"
    ledger.append_event(path, _genesis())
    original = path.read_bytes()
    invalid = _pair_created([_genesis()], "R2-SHAKEDOWN", "pair-r2")
    invalid["arm"] = "TREATMENT"

    with pytest.raises(ledger.LedgerError) as caught:
        ledger.append_event(path, invalid)

    assert caught.value.code == ledger.LEDGER_SCHEMA_FAILURE
    assert path.read_bytes() == original


def test_fsync_failure_never_returns_success(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "synthetic-ledger.v2.ndjson"

    def fail_fsync(_file_descriptor: int) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(ledger.os, "fsync", fail_fsync)
    with pytest.raises(ledger.LedgerError) as caught:
        ledger.append_event(path, _genesis())

    assert caught.value.code == ledger.LEDGER_APPEND_FAILURE
    assert "synthetic" not in str(caught.value)


@pytest.mark.parametrize(
    "payload",
    [
        b"\xef\xbb\xbf{}\n",
        b"{}\r\n",
        b"{}",
        b'{"schema_version":"one","schema_version":"two"}\n',
    ],
)
def test_reader_rejects_bom_crlf_missing_lf_and_duplicate_keys(
    tmp_path: Path, payload: bytes
) -> None:
    path = tmp_path / "invalid.ndjson"
    path.write_bytes(payload)

    with pytest.raises(ledger.LedgerError) as caught:
        ledger.read_ledger(path)

    assert caught.value.code == ledger.LEDGER_PARSE_FAILURE


def test_encoder_is_deterministic_and_does_not_add_bom_or_cr() -> None:
    event = _genesis()
    first = ledger.encode_event(event)
    second = ledger.encode_event(deepcopy(event))

    assert first == second
    assert first.endswith(b"\n")
    assert b"\r" not in first
    assert not first.startswith(b"\xef\xbb\xbf")
    assert json.loads(first) == event
