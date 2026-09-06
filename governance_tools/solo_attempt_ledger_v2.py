"""Closed-schema public lifecycle ledger for Solo Evaluation Revision 2.

This module represents public lifecycle data only.  It does not create
controller state, scoring bundles, keys, nonces, or the canonical evaluation
ledger.  Callers must provide the target path explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
from uuid import UUID

from governance_tools import solo_r2_disposable_profile as disposable


LEDGER_SCHEMA = "solo_attempt_ledger.v2"
PUBLIC_LEDGER_PATH = Path(
    "artifacts/evidence/solo-evaluation-20260831/attempt-ledger.v2.ndjson"
)
REPLACEMENT_PUBLIC_LEDGER_PATH = Path(
    "artifacts/evidence/solo-evaluation-r2-replacement-20260905/"
    "attempt-ledger.v2.ndjson"
)
V1_LEDGER_SHA256 = (
    "596e798868adae1f9b0fd7d33d6eef6505d947415b95b748381951f3e32e04ab"
)
ADOPTED_PROTOCOL_SHA256 = (
    "1b93c13a287090015aa01e42ad423d8c9fa60bf7565baf3f0bf4abe1141bcdff"
)
ADOPTED_CONTRACT_SHA256 = (
    "3503313ccc9ff563d4a464309348af23bd3ae37d3cffb96d7d009173b345f3ea"
)
ADOPTED_SCHEMA_SHA256 = (
    "d64d9f881a07947b363ef12d2c53e8628dcd4b4dabbf89ba3cbd42f4131d01bb"
)
ADOPTED_SCHEMA_ID = f"{LEDGER_SCHEMA}@sha256:{ADOPTED_SCHEMA_SHA256}"
LEGACY_PAIR_ID = "solo-pair0-719cb39e-acda-4e1a-95c9-4cb1b8a4c040"

SLOTS = ("R2-SHAKEDOWN", "A1", "A2", "A3", "A4", "A5", "A6")
ATTEMPT_CEILING_TOTAL = 14
ATTEMPT_CEILING_BREAKDOWN = {slot: 2 for slot in SLOTS}

EVENT_TYPES = frozenset(
    {
        "V2_GENESIS",
        "PAIR_CREATED",
        "PRE_ATTEMPT_INFRA_FAILURE",
        "ATTEMPT_ADMITTED",
        "ADMITTED_NOT_EXPOSED",
        "TASK_EXPOSED",
        "EXECUTION_TERMINAL",
        "CONTROLLER_STATE_SEALED",
        "SCORING_RECORDED",
        "PREMATURE_UNBLINDING",
        "UNBLINDING_RECORDED",
    }
)

LEDGER_PARSE_FAILURE = "LEDGER_PARSE_FAILURE / STOP"
LEDGER_SCHEMA_FAILURE = "LEDGER_SCHEMA_FAILURE / STOP"
LEDGER_TRANSITION_FAILURE = "LEDGER_TRANSITION_FAILURE / STOP"
LEDGER_APPEND_FAILURE = "LEDGER_APPEND_FAILURE / STOP"
GENESIS_PUBLICATION_ABSENT = "ABSENT"
GENESIS_PUBLICATION_VALID = "VALID"
GENESIS_PUBLICATION_INVALID = "INVALID"

_COMMON_KEYS = frozenset(
    {
        "schema_version",
        "event_seq",
        "event_type",
        "event_id",
        "timestamp_utc",
        "pair_id",
        "slot",
    }
)
_GENESIS_KEYS = frozenset(
    {
        "schema_version",
        "event_seq",
        "event_type",
        "event_id",
        "timestamp_utc",
        "evaluation_id",
        "predecessor_digest",
        "adopted_protocol_sha256",
        "adopted_contract_sha256",
        "adopted_schema_id",
        "legacy_pair_id",
        "legacy_pair_state_at_v1",
        "legacy_pair_attempts_used",
        "legacy_pair_disposition",
        "attempt_ceiling_total",
        "attempt_ceiling_breakdown",
    }
)
_EVENT_EXTRA_KEYS = {
    "PAIR_CREATED": frozenset({"category", "repository", "frozen_identities"}),
    "PRE_ATTEMPT_INFRA_FAILURE": frozenset(
        {"category", "repository", "admission_result"}
    ),
    "ATTEMPT_ADMITTED": frozenset(
        {"attempt_handle", "attempt_state", "admission_result"}
    ),
    "ADMITTED_NOT_EXPOSED": frozenset(
        {"attempt_handle", "attempt_state", "admission_result"}
    ),
    "TASK_EXPOSED": frozenset(
        {"attempt_handle", "attempt_state", "admission_result"}
    ),
    "EXECUTION_TERMINAL": frozenset(
        {"attempt_handle", "attempt_state", "correctness_result", "cost_metrics"}
    ),
    "CONTROLLER_STATE_SEALED": frozenset(
        {"sealed_package_digest", "score_count"}
    ),
    "SCORING_RECORDED": frozenset({"sealed_package_digest", "score_count"}),
    "PREMATURE_UNBLINDING": frozenset({"sealed_package_digest", "score_count"}),
    "UNBLINDING_RECORDED": frozenset({"sealed_package_digest", "score_count"}),
}
_FROZEN_IDENTITY_KEYS = frozenset(
    {
        "protocol_sha256",
        "contract_sha256",
        "schema_id",
        "qualification_record_sha256",
        "historical_base_commit",
        "historical_fix_commit",
        "oracle_blob_sha256",
    }
)
_ADMISSION_KEYS = frozenset({"status", "preflight_ids", "task_exposure_state"})
_CORRECTNESS_KEYS = frozenset(
    {
        "oracle_status",
        "required_case_count",
        "passed_case_count",
        "regression_status",
        "scope_status",
    }
)
_COST_KEYS = frozenset(
    {"elapsed_ms", "tokens_total", "tool_calls", "review_rounds"}
)
_REQUIRED_COST_KEYS = frozenset({"elapsed_ms", "tool_calls"})
_LOWER_HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_RFC3339_UTC = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z"
)
_FORBIDDEN_PUBLIC_TOKENS = frozenset({"CONTROL", "TREATMENT"})


class LedgerError(RuntimeError):
    """Fail-closed ledger error carrying only a frozen public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GenesisPublicationError(LedgerError):
    """Uncertain first-publication failure with one read-only classification."""

    def __init__(self, publication_state: str) -> None:
        if publication_state not in {
            GENESIS_PUBLICATION_ABSENT,
            GENESIS_PUBLICATION_VALID,
            GENESIS_PUBLICATION_INVALID,
        }:
            publication_state = GENESIS_PUBLICATION_INVALID
        self.publication_state = publication_state
        super().__init__(LEDGER_APPEND_FAILURE)


@dataclass(frozen=True)
class LedgerSummary:
    schema_version: str
    ledger_event_count: int
    pair_count: int
    admitted_attempt_count: int
    initiated_attempt_count: int
    terminal_execution_count: int
    scoring_record_count: int
    unblinding_record_count: int
    attempt_ceiling_total: int
    next_event_seq: int
    public_schema_closed: bool = True


def _fail(code: str = LEDGER_SCHEMA_FAILURE) -> None:
    raise LedgerError(code)


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and not any(
        ord(character) < 32 for character in value
    )


def _is_lower_hex(value: object, pattern: re.Pattern[str]) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_uuid4(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _is_rfc3339_utc(value: object) -> bool:
    if not isinstance(value, str) or _RFC3339_UTC.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _require_exact_keys(value: object, expected: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(expected):
        _fail()
    if not all(isinstance(key, str) for key in value):
        _fail()
    return value


def _reject_forbidden_public_tokens(value: object) -> None:
    if isinstance(value, str):
        if value in _FORBIDDEN_PUBLIC_TOKENS:
            _fail()
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_forbidden_public_tokens(key)
            _reject_forbidden_public_tokens(child)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _reject_forbidden_public_tokens(child)


def _validate_common(event: Mapping[str, Any], expected_seq: int, schema: str = LEDGER_SCHEMA) -> None:
    if event.get("schema_version") != schema:
        _fail()
    if type(event.get("event_seq")) is not int or event["event_seq"] != expected_seq:
        _fail(LEDGER_TRANSITION_FAILURE)
    if event.get("event_type") not in EVENT_TYPES:
        _fail()
    if not _is_uuid4(event.get("event_id")):
        _fail()
    if not _is_rfc3339_utc(event.get("timestamp_utc")):
        _fail()


def _validate_genesis(event: Mapping[str, Any], schema: str = LEDGER_SCHEMA) -> None:
    _require_exact_keys(event, _GENESIS_KEYS)
    _validate_common(event, 1, schema)
    if event["event_type"] != "V2_GENESIS":
        _fail(LEDGER_TRANSITION_FAILURE)
    if not _is_uuid4(event.get("evaluation_id")):
        _fail()
    expected_strings = {
        "predecessor_digest": V1_LEDGER_SHA256,
        "adopted_protocol_sha256": ADOPTED_PROTOCOL_SHA256,
        "adopted_contract_sha256": ADOPTED_CONTRACT_SHA256,
        "adopted_schema_id": disposable.SCHEMA_ID if schema == disposable.SCHEMA else ADOPTED_SCHEMA_ID,
        "legacy_pair_id": LEGACY_PAIR_ID,
        "legacy_pair_state_at_v1": "PAIR_CREATED",
        "legacy_pair_disposition": "PRE_ATTEMPT_TERMINATION",
    }
    if any(event.get(key) != value for key, value in expected_strings.items()):
        _fail()
    if (
        type(event.get("legacy_pair_attempts_used")) is not int
        or event["legacy_pair_attempts_used"] != 0
        or type(event.get("attempt_ceiling_total")) is not int
        or event["attempt_ceiling_total"] != ATTEMPT_CEILING_TOTAL
    ):
        _fail()
    breakdown = _require_exact_keys(
        event.get("attempt_ceiling_breakdown"),
        frozenset(ATTEMPT_CEILING_BREAKDOWN),
    )
    if any(
        type(breakdown[slot]) is not int
        or breakdown[slot] != ATTEMPT_CEILING_BREAKDOWN[slot]
        for slot in SLOTS
    ):
        _fail()


def _validate_frozen_identities(value: object, schema: str = LEDGER_SCHEMA) -> Mapping[str, Any]:
    if schema == disposable.SCHEMA:
        expected = {
            "protocol_sha256": ADOPTED_PROTOCOL_SHA256,
            "contract_sha256": ADOPTED_CONTRACT_SHA256,
            "schema_id": disposable.SCHEMA_ID,
            "input_authority_sha256": disposable.INPUT_SHA256,
        }
        identities = _require_exact_keys(value, frozenset(expected))
        if dict(identities) != expected:
            _fail()
        return identities
    identities = _require_exact_keys(value, _FROZEN_IDENTITY_KEYS)
    if identities["protocol_sha256"] != ADOPTED_PROTOCOL_SHA256:
        _fail()
    if identities["contract_sha256"] != ADOPTED_CONTRACT_SHA256:
        _fail()
    if identities["schema_id"] != ADOPTED_SCHEMA_ID:
        _fail()
    for key in ("qualification_record_sha256", "oracle_blob_sha256"):
        if not _is_lower_hex(identities[key], _LOWER_HEX_64):
            _fail()
    for key in ("historical_base_commit", "historical_fix_commit"):
        if not _is_lower_hex(identities[key], _LOWER_HEX_40):
            _fail()
    return identities


def _validate_admission(value: object) -> Mapping[str, Any]:
    admission = _require_exact_keys(value, _ADMISSION_KEYS)
    if admission["status"] not in {"ADMITTED", "REFUSED", "FAIL_CLOSED"}:
        _fail()
    preflight_ids = admission["preflight_ids"]
    if not isinstance(preflight_ids, list) or not all(
        _is_nonempty_string(item) for item in preflight_ids
    ):
        _fail()
    if admission["task_exposure_state"] not in {"NONE", "EXPOSED"}:
        _fail()
    return admission


def _validate_correctness(value: object) -> None:
    correctness = _require_exact_keys(value, _CORRECTNESS_KEYS)
    if correctness["oracle_status"] not in {"PASS", "FAIL", "NOT_RUN"}:
        _fail()
    if correctness["regression_status"] not in {
        "NONE",
        "PRESENT",
        "NOT_EVALUATED",
    }:
        _fail()
    if correctness["scope_status"] not in {
        "WITHIN_SCOPE",
        "VIOLATION",
        "NOT_EVALUATED",
    }:
        _fail()
    required = correctness["required_case_count"]
    passed = correctness["passed_case_count"]
    if not _is_non_negative_int(required) or not _is_non_negative_int(passed):
        _fail()
    if passed > required:
        _fail()


def _validate_cost_metrics(value: object) -> None:
    if not isinstance(value, Mapping):
        _fail()
    keys = set(value)
    if not _REQUIRED_COST_KEYS.issubset(keys) or not keys.issubset(_COST_KEYS):
        _fail()
    if not all(_is_non_negative_int(metric) for metric in value.values()):
        _fail()


def _validate_event_shape(event: object, expected_seq: int, schema: str = LEDGER_SCHEMA) -> Mapping[str, Any]:
    if not isinstance(event, Mapping):
        _fail()
    event_type = event.get("event_type")
    if not isinstance(event_type, str) or event_type not in _EVENT_EXTRA_KEYS:
        _fail()
    _require_exact_keys(event, _COMMON_KEYS | _EVENT_EXTRA_KEYS[event_type])
    _validate_common(event, expected_seq, schema)
    pair_id = event["pair_id"]
    if event_type == "PRE_ATTEMPT_INFRA_FAILURE":
        if pair_id is not None and not _is_nonempty_string(pair_id):
            _fail()
    elif not _is_nonempty_string(pair_id):
        _fail()
    if event["slot"] not in SLOTS:
        _fail()
    if schema == disposable.SCHEMA and event["slot"] != "R2-SHAKEDOWN":
        _fail()

    if event_type == "PAIR_CREATED":
        if not _is_nonempty_string(event["category"]) or not _is_nonempty_string(
            event["repository"]
        ):
            _fail()
        _validate_frozen_identities(event["frozen_identities"], schema)
    elif event_type == "PRE_ATTEMPT_INFRA_FAILURE":
        if not _is_nonempty_string(event["category"]) or not _is_nonempty_string(
            event["repository"]
        ):
            _fail()
        admission = _validate_admission(event["admission_result"])
        if admission["status"] == "ADMITTED" or admission["task_exposure_state"] != "NONE":
            _fail()
    elif event_type in {
        "ATTEMPT_ADMITTED",
        "ADMITTED_NOT_EXPOSED",
        "TASK_EXPOSED",
    }:
        if not _is_lower_hex(event["attempt_handle"], _LOWER_HEX_64):
            _fail()
        admission = _validate_admission(event["admission_result"])
        expected_states = {
            "ATTEMPT_ADMITTED": ("ADMITTED", "NONE"),
            "ADMITTED_NOT_EXPOSED": ("ADMITTED_NOT_EXPOSED", "NONE"),
            "TASK_EXPOSED": ("TASK_EXPOSED", "EXPOSED"),
        }
        expected_state, exposure = expected_states[event_type]
        if event["attempt_state"] != expected_state:
            _fail()
        if admission["status"] != "ADMITTED" or admission["task_exposure_state"] != exposure:
            _fail()
    elif event_type == "EXECUTION_TERMINAL":
        if not _is_lower_hex(event["attempt_handle"], _LOWER_HEX_64):
            _fail()
        if event["attempt_state"] != "TERMINAL":
            _fail()
        _validate_correctness(event["correctness_result"])
        _validate_cost_metrics(event["cost_metrics"])
    else:
        if not _is_lower_hex(event["sealed_package_digest"], _LOWER_HEX_64):
            _fail()
        if not _is_non_negative_int(event["score_count"]):
            _fail()
        expected_counts: dict[str, set[int]] = {
            "CONTROLLER_STATE_SEALED": {0},
            "SCORING_RECORDED": {2},
            "PREMATURE_UNBLINDING": {0, 1},
            "UNBLINDING_RECORDED": {2},
        }
        if event["score_count"] not in expected_counts[event_type]:
            _fail()

    _reject_forbidden_public_tokens(event)
    return event


def validate_ledger_events(events: Sequence[Mapping[str, Any]]) -> LedgerSummary:
    """Validate a complete v2 event history and return public scalar counts."""

    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        _fail()
    if not events:
        _fail()

    genesis = events[0]
    if not isinstance(genesis, Mapping):
        _fail()
    schema = genesis.get("schema_version")
    if schema not in (LEDGER_SCHEMA, disposable.SCHEMA):
        _fail()
    _validate_genesis(genesis, schema)
    evaluation_id = genesis["evaluation_id"]
    event_ids = {genesis["event_id"]}
    pairs: dict[str, dict[str, Any]] = {}
    slot_pairs: dict[str, str] = {}
    attempts: dict[str, dict[str, Any]] = {}
    slot_initiated = {slot: 0 for slot in SLOTS}
    initiated_total = 0
    admitted_total = 0
    terminal_total = 0
    scoring_total = 0
    unblinding_total = 0
    globally_stopped = False

    for expected_seq, raw_event in enumerate(events[1:], start=2):
        event = _validate_event_shape(raw_event, expected_seq, schema)
        event_id = event["event_id"]
        if event_id in event_ids:
            _fail(LEDGER_TRANSITION_FAILURE)
        event_ids.add(event_id)
        if globally_stopped:
            _fail(LEDGER_TRANSITION_FAILURE)

        event_type = event["event_type"]
        pair_id = event["pair_id"]
        slot = event["slot"]

        if event_type == "PAIR_CREATED":
            assert isinstance(pair_id, str)
            if pair_id == LEGACY_PAIR_ID or pair_id in pairs or slot in slot_pairs:
                _fail(LEDGER_TRANSITION_FAILURE)
            if slot != "R2-SHAKEDOWN":
                shakedown_id = slot_pairs.get("R2-SHAKEDOWN")
                if shakedown_id is None or pairs[shakedown_id]["phase"] != "UNBLINDED":
                    _fail(LEDGER_TRANSITION_FAILURE)
            pairs[pair_id] = {
                "slot": slot,
                "category": event["category"],
                "repository": event["repository"],
                "phase": "CREATED",
                "handles": [],
                "digest": None,
            }
            slot_pairs[slot] = pair_id
            continue

        if event_type == "PRE_ATTEMPT_INFRA_FAILURE":
            if slot != "R2-SHAKEDOWN":
                shakedown_id = slot_pairs.get("R2-SHAKEDOWN")
                if shakedown_id is None or pairs[shakedown_id]["phase"] != "UNBLINDED":
                    _fail(LEDGER_TRANSITION_FAILURE)
            if pair_id is None:
                if slot in slot_pairs:
                    _fail(LEDGER_TRANSITION_FAILURE)
            else:
                pair = pairs.get(pair_id)
                if (
                    pair is None
                    or pair["slot"] != slot
                    or pair["category"] != event["category"]
                    or pair["repository"] != event["repository"]
                    or pair["phase"] != "CREATED"
                    or pair["handles"]
                ):
                    _fail(LEDGER_TRANSITION_FAILURE)
                pair["phase"] = "STOPPED"
            globally_stopped = True
            continue

        assert isinstance(pair_id, str)
        pair = pairs.get(pair_id)
        if pair is None or pair["slot"] != slot or pair["phase"] == "STOPPED":
            _fail(LEDGER_TRANSITION_FAILURE)

        if event_type == "ATTEMPT_ADMITTED":
            handle = event["attempt_handle"]
            if handle in attempts or len(pair["handles"]) >= 2:
                _fail(LEDGER_TRANSITION_FAILURE)
            if pair["phase"] not in {"CREATED", "ATTEMPTS"}:
                _fail(LEDGER_TRANSITION_FAILURE)
            attempts[handle] = {
                "pair_id": pair_id,
                "slot": slot,
                "state": "ADMITTED",
                "admission": event["admission_result"],
            }
            pair["handles"].append(handle)
            pair["phase"] = "ATTEMPTS"
            admitted_total += 1
            continue

        if event_type in {"ADMITTED_NOT_EXPOSED", "TASK_EXPOSED", "EXECUTION_TERMINAL"}:
            handle = event["attempt_handle"]
            attempt = attempts.get(handle)
            if attempt is None or attempt["pair_id"] != pair_id or attempt["slot"] != slot:
                _fail(LEDGER_TRANSITION_FAILURE)

            if event_type == "ADMITTED_NOT_EXPOSED":
                if attempt["state"] != "ADMITTED":
                    _fail(LEDGER_TRANSITION_FAILURE)
                if event["admission_result"]["preflight_ids"] != attempt["admission"]["preflight_ids"]:
                    _fail(LEDGER_TRANSITION_FAILURE)
                attempt["state"] = "ADMITTED_NOT_EXPOSED"
                pair["phase"] = "STOPPED"
                globally_stopped = True
            elif event_type == "TASK_EXPOSED":
                if attempt["state"] != "ADMITTED":
                    _fail(LEDGER_TRANSITION_FAILURE)
                admitted = attempt["admission"]
                exposed = event["admission_result"]
                if (
                    admitted["status"] != exposed["status"]
                    or admitted["preflight_ids"] != exposed["preflight_ids"]
                ):
                    _fail(LEDGER_TRANSITION_FAILURE)
                if slot_initiated[slot] >= ATTEMPT_CEILING_BREAKDOWN[slot]:
                    _fail(LEDGER_TRANSITION_FAILURE)
                if initiated_total >= ATTEMPT_CEILING_TOTAL:
                    _fail(LEDGER_TRANSITION_FAILURE)
                attempt["state"] = "TASK_EXPOSED"
                slot_initiated[slot] += 1
                initiated_total += 1
            else:
                if attempt["state"] != "TASK_EXPOSED":
                    _fail(LEDGER_TRANSITION_FAILURE)
                attempt["state"] = "TERMINAL"
                terminal_total += 1
            continue

        if event_type == "CONTROLLER_STATE_SEALED":
            if pair["phase"] != "ATTEMPTS" or len(pair["handles"]) != 2:
                _fail(LEDGER_TRANSITION_FAILURE)
            if any(attempts[handle]["state"] != "TERMINAL" for handle in pair["handles"]):
                _fail(LEDGER_TRANSITION_FAILURE)
            pair["phase"] = "SEALED"
            pair["digest"] = event["sealed_package_digest"]
        elif event_type == "SCORING_RECORDED":
            if pair["phase"] != "SEALED" or event["sealed_package_digest"] != pair["digest"]:
                _fail(LEDGER_TRANSITION_FAILURE)
            pair["phase"] = "SCORED"
            scoring_total += 1
        elif event_type == "PREMATURE_UNBLINDING":
            if pair["phase"] != "SEALED" or event["sealed_package_digest"] != pair["digest"]:
                _fail(LEDGER_TRANSITION_FAILURE)
            pair["phase"] = "STOPPED"
            globally_stopped = True
        elif event_type == "UNBLINDING_RECORDED":
            if pair["phase"] != "SCORED" or event["sealed_package_digest"] != pair["digest"]:
                _fail(LEDGER_TRANSITION_FAILURE)
            pair["phase"] = "UNBLINDED"
            unblinding_total += 1
        else:
            _fail(LEDGER_TRANSITION_FAILURE)

    return LedgerSummary(
        schema_version=schema,
        ledger_event_count=len(events),
        pair_count=len(pairs),
        admitted_attempt_count=admitted_total,
        initiated_attempt_count=initiated_total,
        terminal_execution_count=terminal_total,
        scoring_record_count=scoring_total,
        unblinding_record_count=unblinding_total,
        attempt_ceiling_total=ATTEMPT_CEILING_TOTAL,
        next_event_seq=len(events) + 1,
    )


def _pairs_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(LEDGER_PARSE_FAILURE)
        result[key] = value
    return result


def read_ledger(path: Path | str, *, allow_missing: bool = False) -> list[dict[str, Any]]:
    """Read strict UTF-8/LF NDJSON without exposing parse details."""

    ledger_path = Path(path)
    try:
        if not ledger_path.exists():
            if allow_missing:
                return []
            _fail(LEDGER_PARSE_FAILURE)
        data = ledger_path.read_bytes()
    except LedgerError:
        raise
    except OSError as exc:
        raise LedgerError(LEDGER_PARSE_FAILURE) from exc

    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data or not data.endswith(b"\n"):
        _fail(LEDGER_PARSE_FAILURE)
    try:
        text = data.decode("utf-8", errors="strict")
        events = [
            json.loads(line, object_pairs_hook=_pairs_without_duplicate_keys)
            for line in text[:-1].split("\n")
        ]
    except LedgerError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LedgerError(LEDGER_PARSE_FAILURE) from exc
    if not all(isinstance(event, dict) for event in events):
        _fail(LEDGER_PARSE_FAILURE)
    return events


def encode_event(event: Mapping[str, Any]) -> bytes:
    """Encode one event deterministically as an LF-terminated UTF-8 line."""

    try:
        encoded = json.dumps(
            dict(event), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as exc:
        raise LedgerError(LEDGER_SCHEMA_FAILURE) from exc
    if b"\r" in encoded or encoded.startswith(b"\xef\xbb\xbf"):
        _fail()
    return encoded


def _path_entry_exists(path: Path) -> bool:
    try:
        return os.path.lexists(path)
    except (OSError, TypeError, ValueError):
        _fail(LEDGER_APPEND_FAILURE)


def _snapshot_genesis_event(
    event: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, LedgerSummary]:
    """Freeze, validate, and re-encode one genesis without caller aliases."""

    try:
        initial_bytes = encode_event(event)
        snapshot = json.loads(
            initial_bytes,
            object_pairs_hook=_pairs_without_duplicate_keys,
        )
    except LedgerError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        _fail(LEDGER_SCHEMA_FAILURE)
    if type(snapshot) is not dict:
        _fail(LEDGER_SCHEMA_FAILURE)
    summary = validate_ledger_events([snapshot])
    canonical_bytes = encode_event(snapshot)
    if canonical_bytes != initial_bytes:
        _fail(LEDGER_SCHEMA_FAILURE)
    return snapshot, canonical_bytes, summary


def classify_genesis_publication(
    path: Path | str, event: Mapping[str, Any]
) -> str:
    """Classify a first-publication target without changing filesystem state."""

    ledger_path = Path(path)
    expected_event, expected_bytes, _summary = _snapshot_genesis_event(event)
    try:
        if not _path_entry_exists(ledger_path):
            return GENESIS_PUBLICATION_ABSENT
    except LedgerError:
        return GENESIS_PUBLICATION_INVALID
    try:
        if ledger_path.read_bytes() != expected_bytes:
            return GENESIS_PUBLICATION_INVALID
        events = read_ledger(ledger_path)
        summary = validate_ledger_events(events)
    except (LedgerError, OSError):
        return GENESIS_PUBLICATION_INVALID
    if (
        events != [expected_event]
        or summary.ledger_event_count != 1
        or summary.pair_count != 0
        or summary.admitted_attempt_count != 0
        or summary.initiated_attempt_count != 0
        or summary.next_event_seq != 2
    ):
        return GENESIS_PUBLICATION_INVALID
    return GENESIS_PUBLICATION_VALID


def create_genesis_ledger(
    path: Path | str, event: Mapping[str, Any]
) -> LedgerSummary:
    """Publish one complete genesis through a same-directory atomic replace."""

    ledger_path = Path(path)
    candidate, encoded, summary = _snapshot_genesis_event(event)
    # Disposable publication also needs the one-allocation binding record.
    # Only its dedicated creation operation can publish that pair of artifacts.
    if summary.schema_version == disposable.SCHEMA:
        _fail(LEDGER_APPEND_FAILURE)
    temporary = ledger_path.with_name(f".{ledger_path.name}.tmp")
    if (
        not ledger_path.parent.is_dir()
        or _path_entry_exists(ledger_path)
        or _path_entry_exists(temporary)
    ):
        _fail(LEDGER_APPEND_FAILURE)

    replace_started = False
    try:
        with temporary.open("xb+", buffering=0) as stream:
            written = stream.write(encoded)
            if written != len(encoded):
                raise OSError("short write")
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read() != encoded:
                raise OSError("read-back mismatch")
        if _path_entry_exists(ledger_path):
            raise OSError("target appeared before publication")
        replace_started = True
        os.replace(temporary, ledger_path)
    except LedgerError:
        if not replace_started:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    except OSError:
        if replace_started:
            raise GenesisPublicationError(
                classify_genesis_publication(ledger_path, candidate)
            ) from None
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        if _path_entry_exists(ledger_path):
            raise GenesisPublicationError(
                classify_genesis_publication(ledger_path, candidate)
            ) from None
        _fail(LEDGER_APPEND_FAILURE)

    publication_state = classify_genesis_publication(ledger_path, candidate)
    if publication_state != GENESIS_PUBLICATION_VALID:
        raise GenesisPublicationError(publication_state)
    return summary


def append_event(path: Path | str, event: Mapping[str, Any]) -> LedgerSummary:
    """Validate full history, durably append one event, then report success."""

    ledger_path = Path(path)
    existing = read_ledger(ledger_path, allow_missing=True)
    candidate = [*existing, dict(event)]
    summary = validate_ledger_events(candidate)
    if summary.schema_version == disposable.SCHEMA:
        from governance_tools.solo_r2_pair_creation import _has_reparse_or_symlink_component
        expected = disposable.ROOT / disposable.LEDGER_PATH
        if (ledger_path != expected or ledger_path.resolve(strict=True) != expected
                or _has_reparse_or_symlink_component(ledger_path)
                or ledger_path.stat().st_nlink != 1):
            _fail(LEDGER_APPEND_FAILURE)
    encoded = encode_event(event)
    try:
        if not ledger_path.parent.is_dir():
            raise OSError("parent unavailable")
        with ledger_path.open("ab", buffering=0) as stream:
            written = stream.write(encoded)
            if written != len(encoded):
                raise OSError("short write")
            os.fsync(stream.fileno())
    except OSError as exc:
        raise LedgerError(LEDGER_APPEND_FAILURE) from exc
    return summary


def validate_ledger_file(path: Path | str) -> LedgerSummary:
    """Validate an existing v2 ledger file."""

    return validate_ledger_events(read_ledger(path))
