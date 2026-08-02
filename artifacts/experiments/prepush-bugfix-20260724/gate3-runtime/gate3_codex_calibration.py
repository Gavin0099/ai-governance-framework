from __future__ import annotations

import copy
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import gate3_codex_live_canary as live
import gate3_evidence_chain as chain


PUBLIC_RECEIPT_SCHEMA = "gate3-codex-calibration-public-receipt.v1"
PRIVATE_OBSERVATION_SCHEMA = "gate3-codex-calibration-observation.v1"
AUTHORIZATION = "non_counted_codex_calibration_probe_only"

SOURCE_STATUSES = frozenset(
    {"ok", "empty", "not_newline_terminated", "invalid_json", "non_object_record"}
)
ENVELOPE_STATUSES = frozenset({"absent", "single", "multiple", "malformed"})
VALUE_STATUSES = frozenset({"missing", "single_safe", "multiple", "unsafe"})
MATCH_STATUSES = frozenset({"missing", "match", "mismatch", "multiple", "unsafe"})
PROMPT_STATUSES = frozenset({"absent", "exact", "multiple", "mismatch", "malformed"})
PRIVATE_RULING_STATUSES = frozenset({"missing", "single", "multiple", "unsafe"})

SESSION_META_FIELDS = frozenset(
    {
        "base_instructions",
        "cli_version",
        "cwd",
        "history_mode",
        "id",
        "model_provider",
        "originator",
        "session_id",
        "source",
        "thread_source",
    }
)
TURN_CONTEXT_FIELDS = frozenset(
    {
        "approval_policy",
        "approvals_reviewer",
        "collaboration_mode",
        "comp_hash",
        "current_date",
        "cwd",
        "effort",
        "model",
        "multi_agent_version",
        "permission_profile",
        "personality",
        "realtime_active",
        "sandbox_policy",
        "summary",
        "timezone",
        "turn_id",
        "workspace_roots",
    }
)
COLLABORATION_FIELDS = frozenset({"mode", "settings"})
COLLABORATION_SETTING_FIELDS = frozenset(
    {"developer_instructions", "model", "reasoning_effort"}
)
TYPE_OBJECT_FIELDS = frozenset({"type"})
BASE_INSTRUCTION_FIELDS = frozenset({"text"})
OPEN_RULING_FIELDS = ("originator", "source")

PUBLIC_ENUM_ALLOWLISTS = {
    "approval_policy": frozenset({"never"}),
    "approvals_reviewer": frozenset({"user"}),
    "history_mode": frozenset({"legacy"}),
    "machine_file_system_type": frozenset({"unrestricted"}),
    "machine_permission_profile_type": frozenset({"disabled"}),
    "machine_shell": frozenset({"powershell"}),
    "machine_timezone": frozenset({live.DEFAULT_TIMEZONE}),
    "model_provider": frozenset({"openai"}),
    "multi_agent_version": frozenset({"v1"}),
    "permission_profile_type": frozenset({"disabled"}),
    "personality": frozenset({"pragmatic"}),
    "sandbox_policy_type": frozenset({"danger-full-access"}),
    "summary": frozenset({"auto"}),
    "thread_source": frozenset({"user"}),
    "timezone": frozenset({live.DEFAULT_TIMEZONE}),
}
SIGNED_IDENTITY_PATTERNS = {
    "cli_version": re.compile(r"[0-9]+(?:\.[0-9]+){2}"),
    "comp_hash": re.compile(r"[A-Za-z0-9._-]{1,64}"),
    "effort": re.compile(r"[a-z][a-z0-9_-]{0,31}"),
    "model": re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}"),
}
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
MACHINE_CONTEXT_TAGS = frozenset(
    {
        "current_date",
        "cwd",
        "environment_context",
        "file_system",
        "filesystem",
        "permission_profile",
        "root",
        "shell",
        "timezone",
        "workspace_roots",
    }
)
MACHINE_CONTEXT_ATTRIBUTES = {
    "file_system": frozenset({"type"}),
    "permission_profile": frozenset({"type"}),
}

RECORD_COUNT_FIELDS = frozenset(
    {
        "base_instruction",
        "developer_instruction",
        "event_user_message",
        "exact_event_prompt",
        "exact_response_prompt",
        "machine_context",
        "malformed_base_instruction",
        "malformed_developer_instruction",
        "malformed_machine_context",
        "non_string_event_prompt",
        "session_meta_object",
        "session_meta_raw",
        "turn_context_object",
        "turn_context_raw",
        "unmatched_event_prompt",
        "unmatched_response_user_message",
    }
)
ENVELOPE_FIELDS = frozenset(
    {
        "base_instruction",
        "developer_instruction",
        "machine_context",
        "session_identity",
        "session_meta",
        "turn_context",
    }
)
PROMPT_FIELDS = frozenset({"event_user_message", "response_user_message"})
PATH_CENSUS_FIELDS = frozenset(
    {
        "machine_cwd_match",
        "machine_root_entry_count",
        "machine_root_match",
        "session_meta_cwd_match",
        "turn_cwd_match",
        "turn_root_entry_count",
        "turn_root_match",
    }
)
WORLD_STATE_CENSUS_FIELDS = frozenset(
    {"full_true_count", "object_payload_count", "raw_count", "state_object_count"}
)
WRAPPER_ARGUMENT_SHAPES = frozenset(
    {"identifier", "object", "other", "string", "unparsed"}
)
WRAPPER_ENVELOPES = frozenset(
    {
        "bound_argument_then_direct_await_text",
        "const_await_then_text",
        "direct_await_text",
        "other",
    }
)


@dataclass(frozen=True)
class CalibrationObservation:
    """Private, non-admitting observation held in memory only."""

    source_status: str
    signed_identity: dict[str, str]
    record_counts: dict[str, int]
    envelope_statuses: dict[str, str]
    prompt_statuses: dict[str, str]
    public_context: dict[str, Any]
    private_ruling_values: dict[str, dict[str, Any]]
    instruction_record_sha256: dict[str, list[str]]
    instruction_content_anchor: dict[str, dict[str, Any]]
    path_census: dict[str, int]
    world_state_census: dict[str, int]
    world_state_status: str
    wrapper_census: tuple[dict[str, Any], ...]
    unknown_context_field_count: int


def _is_count(value: object) -> bool:
    return type(value) is int and value >= 0


def _records(raw: bytes) -> tuple[str, list[dict[str, Any]]]:
    if not raw:
        return "empty", []
    if not raw.endswith(b"\n"):
        return "not_newline_terminated", []
    records: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "invalid_json", []
        if not isinstance(value, dict):
            return "non_object_record", []
        records.append(value)
    return "ok", records


def _validate_signed_identity(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(SIGNED_IDENTITY_PATTERNS):
        raise live.CanaryError("calibration signed identity schema is invalid")
    result: dict[str, str] = {}
    for field, pattern in SIGNED_IDENTITY_PATTERNS.items():
        observed = value.get(field)
        if not isinstance(observed, str) or pattern.fullmatch(observed) is None:
            raise live.CanaryError("calibration signed identity value is invalid")
        result[field] = observed
    return result


def _typed_payloads(
    records: list[dict[str, Any]], record_type: str
) -> tuple[int, list[dict[str, Any]]]:
    selected = [record for record in records if record.get("type") == record_type]
    return len(selected), [
        record["payload"]
        for record in selected
        if isinstance(record.get("payload"), dict)
    ]


def _envelope_status(raw_count: int, object_count: int) -> str:
    if raw_count == 0:
        return "absent"
    if object_count != raw_count:
        return "malformed"
    return "single" if raw_count == 1 else "multiple"


def _safe_enum(values: list[object], allowed: frozenset[str]) -> dict[str, Any]:
    if not values:
        return {"status": "missing"}
    if any(not isinstance(value, str) for value in values):
        return {"status": "unsafe"}
    unique = sorted(set(values))
    if len(unique) != 1:
        return {"status": "multiple"}
    if unique[0] not in allowed:
        return {"status": "unsafe"}
    return {"status": "single_safe", "value": unique[0]}


def _safe_boolean(values: list[object]) -> dict[str, Any]:
    if not values:
        return {"status": "missing"}
    if any(type(value) is not bool for value in values):
        return {"status": "unsafe"}
    unique = set(values)
    if len(unique) != 1:
        return {"status": "multiple"}
    return {"status": "single_safe", "value": unique.pop()}


def _valid_date(value: object) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _safe_date(values: list[object]) -> dict[str, Any]:
    if not values:
        return {"status": "missing"}
    if any(not _valid_date(value) for value in values):
        return {"status": "unsafe"}
    unique = sorted(set(values))
    if len(unique) != 1:
        return {"status": "multiple"}
    return {"status": "single_safe", "value": unique[0]}


def _identity_match(values: list[object], expected: str) -> dict[str, str]:
    if not values:
        return {"status": "missing"}
    if any(not isinstance(value, str) for value in values):
        return {"status": "unsafe"}
    unique = set(values)
    if len(unique) != 1:
        return {"status": "multiple"}
    return {"status": "match" if unique == {expected} else "mismatch"}


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "other"


def _length_bucket(value: object) -> str:
    if not isinstance(value, str):
        return "not_string"
    length = len(value.encode("utf-8"))
    if length == 0:
        return "zero"
    if length <= 16:
        return "1_16"
    if length <= 64:
        return "17_64"
    return "65_plus"


def _private_ruling(values: list[object]) -> dict[str, Any]:
    if not values:
        return {"status": "missing", "values": ()}
    if any(not isinstance(value, str) or not value for value in values):
        return {"status": "unsafe", "values": ()}
    unique = tuple(sorted(set(values)))
    if any(
        len(value.encode("utf-8")) > 256
        or live._privacy_violations(live._json_bytes({"value": value}))
        for value in unique
    ):
        return {"status": "unsafe", "values": ()}
    return {"status": "single" if len(unique) == 1 else "multiple", "values": unique}


def _public_open_ruling(metas: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [meta[field] for meta in metas if field in meta]
    return {
        "presence_count": len(values),
        "json_types": sorted({_json_type(value) for value in values}),
        "length_buckets": sorted({_length_bucket(value) for value in values}),
    }


def _instruction_digest(value: object, expected_workspace: str) -> str | None:
    if isinstance(value, str):
        text = value
    elif isinstance(value, dict) and isinstance(value.get("text"), str):
        text = value["text"]
    else:
        return None
    normalized = live._normalised_context_view(text, expected_workspace=expected_workspace)
    if not isinstance(normalized, str):
        return None
    return live._sha256_bytes(normalized.encode("utf-8"))


def _content_anchor(digests: list[str]) -> dict[str, Any]:
    unique = sorted(set(digests))
    if not unique:
        return {"status": "missing"}
    if len(unique) != 1:
        return {"status": "multiple"}
    return {"sha256": unique[0], "status": "single"}


def _machine_unknown_count(text: str) -> int:
    matches = re.findall(
        r"<environment_context>.*?</environment_context>", text, flags=re.DOTALL
    )
    count = 0
    for matched in matches:
        try:
            root = ET.fromstring(matched)
        except ET.ParseError:
            continue
        for element in root.iter():
            if element.tag not in MACHINE_CONTEXT_TAGS:
                count += 1
            allowed = MACHINE_CONTEXT_ATTRIBUTES.get(element.tag, frozenset())
            count += len(set(element.attrib) - allowed)
    return count


def _unknown_context_count(
    metas: list[dict[str, Any]],
    turns: list[dict[str, Any]],
    user_texts: list[str],
) -> int:
    count = sum(len(set(meta) - SESSION_META_FIELDS) for meta in metas)
    count += sum(len(set(turn) - TURN_CONTEXT_FIELDS) for turn in turns)
    for meta in metas:
        base = meta.get("base_instructions")
        if isinstance(base, dict):
            count += len(set(base) - BASE_INSTRUCTION_FIELDS)
    for turn in turns:
        for field in ("permission_profile", "sandbox_policy"):
            value = turn.get(field)
            if isinstance(value, dict):
                count += len(set(value) - TYPE_OBJECT_FIELDS)
        collaboration = turn.get("collaboration_mode")
        if isinstance(collaboration, dict):
            count += len(set(collaboration) - COLLABORATION_FIELDS)
            settings = collaboration.get("settings")
            if isinstance(settings, dict):
                count += len(set(settings) - COLLABORATION_SETTING_FIELDS)
    count += sum(_machine_unknown_count(text) for text in user_texts)
    return count


def _path_counts(
    metas: list[dict[str, Any]],
    turns: list[dict[str, Any]],
    machines: list[dict[str, Any]],
    expected_workspace: str,
) -> dict[str, int]:
    result = {field: 0 for field in PATH_CENSUS_FIELDS}
    for meta in metas:
        result["session_meta_cwd_match"] += live._same_path(
            meta.get("cwd"), expected_workspace
        )
    for turn in turns:
        result["turn_cwd_match"] += live._same_path(turn.get("cwd"), expected_workspace)
        roots = turn.get("workspace_roots")
        if isinstance(roots, list):
            result["turn_root_entry_count"] += len(roots)
            result["turn_root_match"] += sum(
                live._same_path(root, expected_workspace) for root in roots
            )
    for machine in machines:
        result["machine_cwd_match"] += live._same_path(
            machine.get("cwd"), expected_workspace
        )
        roots = machine.get("workspace_roots")
        if isinstance(roots, list):
            result["machine_root_entry_count"] += len(roots)
            result["machine_root_match"] += sum(
                live._same_path(root, expected_workspace) for root in roots
            )
    return result


def _world_state_status(census: dict[str, int]) -> str:
    if census["raw_count"] == 0:
        return "absent"
    if (
        census["object_payload_count"] != census["raw_count"]
        or census["full_true_count"] != 1
        or census["state_object_count"] != census["object_payload_count"]
    ):
        return "malformed"
    return "single" if census["raw_count"] == 1 else "multiple"


def _wrapper_census(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    ordinal = 0
    for record in records:
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict) or payload.get("type") not in {
            "custom_tool_call",
            "function_call",
        }:
            continue
        ordinal += 1
        source = payload.get("input")
        if not isinstance(source, str):
            result.append(
                {
                    "argument_shape": "unparsed",
                    "envelope": "other",
                    "field_name_census": {
                        "known_field_counts": {},
                        "total_field_count": 0,
                        "unknown_field_count": 0,
                    },
                    "frozen_tool_call_token_count": 0,
                    "input_status": "non_string",
                    "rejection_class": "no_tool_call",
                    "tool_call_ordinal": ordinal,
                    "tool_call_token_count": 0,
                    "tool_family": "other",
                }
            )
        else:
            result.append(
                {
                    **live._tool_input_wrapper_diagnostic(source),
                    "input_status": "string",
                    "tool_call_ordinal": ordinal,
                }
            )
    return tuple(result)


def _session_identity_status(metas: list[dict[str, Any]]) -> str:
    if not metas:
        return "absent"
    values: list[str] = []
    for meta in metas:
        left = meta.get("id")
        right = meta.get("session_id")
        if not isinstance(left, str) or not left or not isinstance(right, str) or left != right:
            return "malformed"
        values.append(left)
    return "single" if len(set(values)) == 1 else "multiple"


def _identifier_projection(payloads: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [payload[field] for payload in payloads if field in payload]
    return {
        "presence_count": len(values),
        "json_types": sorted({_json_type(value) for value in values}),
        "length_buckets": sorted({_length_bucket(value) for value in values}),
        "unique_count": len({value for value in values if isinstance(value, str)}),
    }


def _object_type_projection(
    values: list[object], allowed: frozenset[str]
) -> dict[str, Any]:
    extracted = [
        value.get("type") if isinstance(value, dict) else None for value in values
    ]
    return _safe_enum(extracted, allowed)


def _collaboration_projection(
    turns: list[dict[str, Any]], signed_identity: dict[str, str]
) -> dict[str, Any]:
    values = [turn.get("collaboration_mode") for turn in turns]
    if not values:
        return {
            "developer_instructions": {"status": "missing"},
            "mode": {"status": "missing"},
            "model": {"status": "missing"},
            "reasoning_effort": {"status": "missing"},
            "status": "missing",
        }
    if any(not isinstance(value, dict) for value in values):
        status = "unsafe"
        modes: list[object] = []
        settings: list[dict[str, Any]] = []
    else:
        status = "single_safe" if len(values) == 1 else "multiple"
        modes = [value.get("mode") for value in values]
        settings = [
            value.get("settings")
            for value in values
            if isinstance(value.get("settings"), dict)
        ]
        if len(settings) != len(values):
            status = "unsafe"
    developer_values = [setting.get("developer_instructions") for setting in settings]
    if not developer_values:
        developer_status = "missing"
    elif all(value is None for value in developer_values):
        developer_status = "null"
    elif all(value is not None for value in developer_values):
        developer_status = "non_null"
    else:
        developer_status = "multiple"
    return {
        "developer_instructions": {"status": developer_status},
        "mode": _safe_enum(modes, frozenset({"default"})),
        "model": _identity_match(
            [setting.get("model") for setting in settings], signed_identity["model"]
        ),
        "reasoning_effort": _identity_match(
            [setting.get("reasoning_effort") for setting in settings],
            signed_identity["effort"],
        ),
        "status": status,
    }


def _empty_observation(
    source_status: str, signed_identity: dict[str, str]
) -> CalibrationObservation:
    missing_public = {
        "booleans": {"realtime_active": {"status": "missing"}},
        "collaboration": _collaboration_projection([], signed_identity),
        "dates": {
            "machine_current_date": {"status": "missing"},
            "turn_current_date": {"status": "missing"},
        },
        "enums": {
            field: {"status": "missing"} for field in PUBLIC_ENUM_ALLOWLISTS
        },
        "identifiers": {
            "session_id": {
                "presence_count": 0,
                "json_types": [],
                "length_buckets": [],
                "unique_count": 0,
            },
            "turn_id": {
                "presence_count": 0,
                "json_types": [],
                "length_buckets": [],
                "unique_count": 0,
            },
        },
        "identities": {
            field: {"status": "missing"} for field in SIGNED_IDENTITY_PATTERNS
        },
        "open_rulings": {
            field: {"presence_count": 0, "json_types": [], "length_buckets": []}
            for field in OPEN_RULING_FIELDS
        },
    }
    return CalibrationObservation(
        source_status=source_status,
        signed_identity=signed_identity,
        record_counts={field: 0 for field in RECORD_COUNT_FIELDS},
        envelope_statuses={field: "absent" for field in ENVELOPE_FIELDS},
        prompt_statuses={field: "absent" for field in PROMPT_FIELDS},
        public_context=missing_public,
        private_ruling_values={
            field: {"status": "missing", "values": ()}
            for field in OPEN_RULING_FIELDS
        },
        instruction_record_sha256={"base": [], "developer": []},
        instruction_content_anchor={
            "base": {"status": "missing"},
            "developer": {"status": "missing"},
        },
        path_census={field: 0 for field in PATH_CENSUS_FIELDS},
        world_state_census={field: 0 for field in WORLD_STATE_CENSUS_FIELDS},
        world_state_status="absent",
        wrapper_census=(),
        unknown_context_field_count=0,
    )


def collect(
    raw: bytes,
    *,
    expected_workspace: str,
    expected_prompt: bytes,
    signed_identity: dict[str, str],
) -> CalibrationObservation:
    """Collect one rollout without performing or returning admission.

    ``signed_identity`` is a caller-supplied synthetic trust boundary. This
    offline tranche validates its shape and compares observations to it; it
    does not claim signature or provenance verification.
    """

    expected = _validate_signed_identity(signed_identity)
    source_status, records = _records(raw)
    if source_status != "ok":
        return _empty_observation(source_status, expected)

    meta_raw_count, metas = _typed_payloads(records, "session_meta")
    turn_raw_count, turns = _typed_payloads(records, "turn_context")
    response_payloads = [
        record["payload"]
        for record in records
        if record.get("type") == "response_item"
        and isinstance(record.get("payload"), dict)
    ]
    developer_payloads = [
        payload
        for payload in response_payloads
        if payload.get("type") == "message" and payload.get("role") == "developer"
    ]
    user_texts = [
        text
        for payload in response_payloads
        for text in [live._message_text(payload)]
        if text is not None
    ]
    machines: list[dict[str, Any]] = []
    malformed_machine_count = 0
    for text in user_texts:
        try:
            machine = live._extract_machine_context(text)
        except live.CanaryError:
            malformed_machine_count += 1
            continue
        if machine is not None:
            machines.append(machine)

    exact_response = sum(text.encode("utf-8") == expected_prompt for text in user_texts)
    unmatched_response = len(user_texts) - exact_response - len(machines)
    event_values = [
        record.get("payload", {}).get("message")
        for record in records
        if record.get("type") == "event_msg"
        and isinstance(record.get("payload"), dict)
        and record["payload"].get("type") == "user_message"
    ]
    exact_event = sum(
        isinstance(value, str) and value.encode("utf-8") == expected_prompt
        for value in event_values
    )
    non_string_event = sum(not isinstance(value, str) for value in event_values)
    unmatched_event = len(event_values) - exact_event - non_string_event

    base_digests: list[str] = []
    malformed_base = 0
    for meta in metas:
        digest = _instruction_digest(meta.get("base_instructions"), expected_workspace)
        if digest is None:
            malformed_base += 1
        else:
            base_digests.append(digest)
    developer_digests: list[str] = []
    malformed_developer = 0
    for payload in developer_payloads:
        try:
            text = live._instruction_text(payload)
        except live.CanaryError:
            malformed_developer += 1
            continue
        digest = _instruction_digest(text, expected_workspace)
        if digest is None:
            malformed_developer += 1
        else:
            developer_digests.append(digest)

    machine_enum_values = {
        "machine_file_system_type": [
            machine.get("file_system_type") for machine in machines
        ],
        "machine_permission_profile_type": [
            machine.get("permission_profile_type") for machine in machines
        ],
        "machine_shell": [machine.get("shell") for machine in machines],
        "machine_timezone": [machine.get("timezone") for machine in machines],
    }
    turn_enum_values = {
        "approval_policy": [turn.get("approval_policy") for turn in turns],
        "approvals_reviewer": [turn.get("approvals_reviewer") for turn in turns],
        "history_mode": [meta.get("history_mode") for meta in metas],
        "model_provider": [meta.get("model_provider") for meta in metas],
        "multi_agent_version": [turn.get("multi_agent_version") for turn in turns],
        "permission_profile_type": [
            value.get("type") if isinstance(value, dict) else None
            for value in [turn.get("permission_profile") for turn in turns]
        ],
        "personality": [turn.get("personality") for turn in turns],
        "sandbox_policy_type": [
            value.get("type") if isinstance(value, dict) else None
            for value in [turn.get("sandbox_policy") for turn in turns]
        ],
        "summary": [turn.get("summary") for turn in turns],
        "thread_source": [meta.get("thread_source") for meta in metas],
        "timezone": [turn.get("timezone") for turn in turns],
    }
    public_context = {
        "booleans": {
            "realtime_active": _safe_boolean(
                [turn.get("realtime_active") for turn in turns]
            )
        },
        "collaboration": _collaboration_projection(turns, expected),
        "dates": {
            "machine_current_date": _safe_date(
                [machine.get("current_date") for machine in machines]
            ),
            "turn_current_date": _safe_date(
                [turn.get("current_date") for turn in turns]
            ),
        },
        "enums": {
            field: _safe_enum(
                (machine_enum_values | turn_enum_values)[field],
                PUBLIC_ENUM_ALLOWLISTS[field],
            )
            for field in PUBLIC_ENUM_ALLOWLISTS
        },
        "identifiers": {
            "session_id": _identifier_projection(metas, "session_id"),
            "turn_id": _identifier_projection(turns, "turn_id"),
        },
        "identities": {
            "cli_version": _identity_match(
                [meta.get("cli_version") for meta in metas], expected["cli_version"]
            ),
            "comp_hash": _identity_match(
                [turn.get("comp_hash") for turn in turns], expected["comp_hash"]
            ),
            "effort": _identity_match(
                [turn.get("effort") for turn in turns], expected["effort"]
            ),
            "model": _identity_match(
                [turn.get("model") for turn in turns], expected["model"]
            ),
        },
        "open_rulings": {
            field: _public_open_ruling(metas, field) for field in OPEN_RULING_FIELDS
        },
    }
    world_census = live._world_state_census(records)
    record_counts = {
        "base_instruction": len(base_digests),
        "developer_instruction": len(developer_payloads),
        "event_user_message": len(event_values),
        "exact_event_prompt": exact_event,
        "exact_response_prompt": exact_response,
        "machine_context": len(machines),
        "malformed_base_instruction": malformed_base,
        "malformed_developer_instruction": malformed_developer,
        "malformed_machine_context": malformed_machine_count,
        "non_string_event_prompt": non_string_event,
        "session_meta_object": len(metas),
        "session_meta_raw": meta_raw_count,
        "turn_context_object": len(turns),
        "turn_context_raw": turn_raw_count,
        "unmatched_event_prompt": unmatched_event,
        "unmatched_response_user_message": unmatched_response,
    }
    response_prompt_status = (
        "exact"
        if exact_response == 1 and unmatched_response == 0 and len(machines) == 1
        else "absent"
        if not user_texts
        else "multiple"
        if exact_response > 1
        else "mismatch"
    )
    event_prompt_status = (
        "exact"
        if exact_event == 1 and unmatched_event == 0 and non_string_event == 0
        else "absent"
        if not event_values
        else "malformed"
        if non_string_event
        else "multiple"
        if len(event_values) > 1
        else "mismatch"
    )
    return CalibrationObservation(
        source_status="ok",
        signed_identity=expected,
        record_counts=record_counts,
        envelope_statuses={
            "base_instruction": (
                "malformed"
                if malformed_base
                else _envelope_status(len(base_digests), len(base_digests))
            ),
            "developer_instruction": _envelope_status(
                len(developer_payloads), len(developer_payloads) - malformed_developer
            ),
            "machine_context": (
                "malformed"
                if malformed_machine_count
                else _envelope_status(len(machines), len(machines))
            ),
            "session_identity": _session_identity_status(metas),
            "session_meta": _envelope_status(meta_raw_count, len(metas)),
            "turn_context": _envelope_status(turn_raw_count, len(turns)),
        },
        prompt_statuses={
            "event_user_message": event_prompt_status,
            "response_user_message": response_prompt_status,
        },
        public_context=public_context,
        private_ruling_values={
            field: _private_ruling([meta[field] for meta in metas if field in meta])
            for field in OPEN_RULING_FIELDS
        },
        instruction_record_sha256={"base": base_digests, "developer": developer_digests},
        instruction_content_anchor={
            "base": _content_anchor(base_digests),
            "developer": _content_anchor(developer_digests),
        },
        path_census=_path_counts(metas, turns, machines, expected_workspace),
        world_state_census=world_census,
        world_state_status=_world_state_status(world_census),
        wrapper_census=_wrapper_census(records),
        unknown_context_field_count=_unknown_context_count(metas, turns, user_texts),
    )


def _require_exact_keys(
    value: object, expected: frozenset[str], *, label: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise live.CanaryError(f"calibration {label} schema is not closed")
    return value


def _validate_counts(
    value: object, expected: frozenset[str], *, label: str
) -> dict[str, int]:
    result = _require_exact_keys(value, expected, label=label)
    if any(not _is_count(item) for item in result.values()):
        raise live.CanaryError(f"calibration {label} count is invalid")
    return copy.deepcopy(result)


def _validate_simple_projection(
    value: object,
    *,
    label: str,
    allowed: frozenset[str] | None = None,
    boolean: bool = False,
    date: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("status") not in VALUE_STATUSES:
        raise live.CanaryError(f"calibration {label} projection is invalid")
    expected_keys = {"status", "value"} if value["status"] == "single_safe" else {"status"}
    if set(value) != expected_keys:
        raise live.CanaryError(f"calibration {label} projection is not closed")
    if value["status"] != "single_safe":
        return {"status": value["status"]}
    projected = value["value"]
    valid = (
        type(projected) is bool
        if boolean
        else isinstance(projected, str)
        and (allowed is None or projected in allowed)
        and (not date or _valid_date(projected))
    )
    if not valid:
        raise live.CanaryError(f"calibration {label} value is invalid")
    return copy.deepcopy(value)


def _validate_match(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"status"} or value.get("status") not in MATCH_STATUSES:
        raise live.CanaryError(f"calibration {label} match status is invalid")
    return {"status": value["status"]}


def _validate_presence_shape(item: dict[str, Any], *, label: str) -> None:
    if not _is_count(item["presence_count"]):
        raise live.CanaryError(f"calibration {label} count is invalid")
    if (
        not isinstance(item["json_types"], list)
        or any(value not in {"array", "boolean", "null", "number", "object", "other", "string"} for value in item["json_types"])
        or item["json_types"] != sorted(set(item["json_types"]))
        or not isinstance(item["length_buckets"], list)
        or any(value not in {"not_string", "zero", "1_16", "17_64", "65_plus"} for value in item["length_buckets"])
        or item["length_buckets"] != sorted(set(item["length_buckets"]))
    ):
        raise live.CanaryError(f"calibration {label} shape is invalid")
    presence = item["presence_count"]
    json_types = item["json_types"]
    length_buckets = item["length_buckets"]
    if (presence == 0) != (not json_types and not length_buckets):
        raise live.CanaryError(f"calibration {label} presence shape is inconsistent")
    string_buckets = set(length_buckets) - {"not_string"}
    if ("string" in json_types) != bool(string_buckets):
        raise live.CanaryError(f"calibration {label} string shape is inconsistent")
    non_string_types = set(json_types) - {"string"}
    if bool(non_string_types) != ("not_string" in length_buckets):
        raise live.CanaryError(f"calibration {label} non-string shape is inconsistent")
    minimum_presence = len(non_string_types) + len(string_buckets)
    if presence < minimum_presence:
        raise live.CanaryError(f"calibration {label} presence count is inconsistent")


def _validate_identifier(value: object, *, label: str) -> dict[str, Any]:
    item = _require_exact_keys(
        value,
        frozenset({"presence_count", "json_types", "length_buckets", "unique_count"}),
        label=label,
    )
    if not _is_count(item["unique_count"]):
        raise live.CanaryError(f"calibration {label} count is invalid")
    _validate_presence_shape(item, label=label)
    if item["unique_count"] > item["presence_count"]:
        raise live.CanaryError(f"calibration {label} unique count is inconsistent")
    if (item["unique_count"] > 0) != ("string" in item["json_types"]):
        raise live.CanaryError(f"calibration {label} unique shape is inconsistent")
    string_bucket_count = len(set(item["length_buckets"]) - {"not_string"})
    non_string_type_count = len(set(item["json_types"]) - {"string"})
    if (
        string_bucket_count > item["unique_count"]
        or item["unique_count"]
        > item["presence_count"] - non_string_type_count
    ):
        raise live.CanaryError(f"calibration {label} unique bounds are inconsistent")
    return copy.deepcopy(item)


def _validate_public_context(value: object) -> dict[str, Any]:
    context = _require_exact_keys(
        value,
        frozenset({"booleans", "collaboration", "dates", "enums", "identifiers", "identities", "open_rulings"}),
        label="public context",
    )
    booleans = _require_exact_keys(context["booleans"], frozenset({"realtime_active"}), label="booleans")
    dates = _require_exact_keys(context["dates"], frozenset({"machine_current_date", "turn_current_date"}), label="dates")
    enums = _require_exact_keys(context["enums"], frozenset(PUBLIC_ENUM_ALLOWLISTS), label="enums")
    identities = _require_exact_keys(context["identities"], frozenset(SIGNED_IDENTITY_PATTERNS), label="identities")
    identifiers = _require_exact_keys(context["identifiers"], frozenset({"session_id", "turn_id"}), label="identifiers")
    open_rulings = _require_exact_keys(context["open_rulings"], frozenset(OPEN_RULING_FIELDS), label="open rulings")
    collaboration = _require_exact_keys(
        context["collaboration"],
        frozenset({"developer_instructions", "mode", "model", "reasoning_effort", "status"}),
        label="collaboration",
    )
    if collaboration["status"] not in VALUE_STATUSES:
        raise live.CanaryError("calibration collaboration status is invalid")
    developer = collaboration["developer_instructions"]
    if not isinstance(developer, dict) or set(developer) != {"status"} or developer["status"] not in {"missing", "null", "non_null", "multiple"}:
        raise live.CanaryError("calibration collaboration developer status is invalid")
    projected_open: dict[str, Any] = {}
    for field in OPEN_RULING_FIELDS:
        item = _require_exact_keys(
            open_rulings[field],
            frozenset({"presence_count", "json_types", "length_buckets"}),
            label=f"open ruling {field}",
        )
        _validate_presence_shape(item, label=f"open ruling {field}")
        projected_open[field] = copy.deepcopy(item)
    return {
        "booleans": {"realtime_active": _validate_simple_projection(booleans["realtime_active"], label="realtime_active", boolean=True)},
        "collaboration": {
            "developer_instructions": copy.deepcopy(developer),
            "mode": _validate_simple_projection(collaboration["mode"], label="collaboration mode", allowed=frozenset({"default"})),
            "model": _validate_match(collaboration["model"], label="collaboration model"),
            "reasoning_effort": _validate_match(collaboration["reasoning_effort"], label="collaboration reasoning"),
            "status": collaboration["status"],
        },
        "dates": {field: _validate_simple_projection(dates[field], label=field, date=True) for field in dates},
        "enums": {field: _validate_simple_projection(enums[field], label=field, allowed=PUBLIC_ENUM_ALLOWLISTS[field]) for field in PUBLIC_ENUM_ALLOWLISTS},
        "identifiers": {field: _validate_identifier(identifiers[field], label=field) for field in identifiers},
        "identities": {field: _validate_match(identities[field], label=field) for field in identities},
        "open_rulings": projected_open,
    }


def _validate_instruction_records(value: object) -> dict[str, list[str]]:
    result = _require_exact_keys(value, frozenset({"base", "developer"}), label="instruction records")
    for digests in result.values():
        if not isinstance(digests, list) or any(not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in digests):
            raise live.CanaryError("calibration instruction record digest is invalid")
    return copy.deepcopy(result)


def _validate_instruction_anchors(
    anchors: object, records: dict[str, list[str]]
) -> dict[str, dict[str, Any]]:
    result = _require_exact_keys(anchors, frozenset({"base", "developer"}), label="instruction anchors")
    expected = {field: _content_anchor(records[field]) for field in records}
    if result != expected:
        raise live.CanaryError("calibration instruction anchor differs from record content")
    return copy.deepcopy(expected)


def _validate_wrapper_census(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, tuple):
        raise live.CanaryError("calibration wrapper census type is invalid")
    expected_keys = frozenset(
        {"argument_shape", "envelope", "field_name_census", "frozen_tool_call_token_count", "input_status", "rejection_class", "tool_call_ordinal", "tool_call_token_count", "tool_family"}
    )
    projected: list[dict[str, Any]] = []
    for expected_ordinal, wrapper in enumerate(value, 1):
        item = _require_exact_keys(wrapper, expected_keys, label="wrapper census")
        fields = _require_exact_keys(
            item["field_name_census"],
            frozenset({"known_field_counts", "total_field_count", "unknown_field_count"}),
            label="wrapper field census",
        )
        known = fields["known_field_counts"]
        valid = (
            isinstance(known, dict)
            and all(name in live.SAFE_TOOL_INPUT_FIELD_NAMES for name in known)
            and all(_is_count(count) and count > 0 for count in known.values())
            and _is_count(fields["total_field_count"])
            and _is_count(fields["unknown_field_count"])
            and fields["total_field_count"] == sum(known.values()) + fields["unknown_field_count"]
            and item["argument_shape"] in WRAPPER_ARGUMENT_SHAPES
            and item["envelope"] in WRAPPER_ENVELOPES
            and item["input_status"] in {"non_string", "string"}
            and item["rejection_class"] in live.WRAPPER_REJECTION_CLASSES
            and item["tool_family"] in {*live.FROZEN_TOOL_FAMILIES, "other"}
            and _is_count(item["frozen_tool_call_token_count"])
            and _is_count(item["tool_call_token_count"])
            and item["tool_call_ordinal"] == expected_ordinal
        )
        if not valid:
            raise live.CanaryError("calibration wrapper census value is invalid")
        projected.append(copy.deepcopy(item))
    return projected


def public_receipt(observation: CalibrationObservation) -> dict[str, Any]:
    """Build a closed privacy-safe projection with no admission semantics."""

    if not isinstance(observation, CalibrationObservation):
        raise TypeError("calibration observation type is required")
    signed_identity = _validate_signed_identity(observation.signed_identity)
    if observation.source_status not in SOURCE_STATUSES:
        raise live.CanaryError("calibration source status is invalid")
    if observation.world_state_status not in ENVELOPE_STATUSES:
        raise live.CanaryError("calibration world-state status is invalid")
    envelopes = _require_exact_keys(observation.envelope_statuses, ENVELOPE_FIELDS, label="envelope status")
    if any(status not in ENVELOPE_STATUSES for status in envelopes.values()):
        raise live.CanaryError("calibration envelope status is invalid")
    prompts = _require_exact_keys(observation.prompt_statuses, PROMPT_FIELDS, label="prompt status")
    if any(status not in PROMPT_STATUSES for status in prompts.values()):
        raise live.CanaryError("calibration prompt status is invalid")
    if not _is_count(observation.unknown_context_field_count):
        raise live.CanaryError("calibration unknown context count is invalid")
    instruction_records = _validate_instruction_records(observation.instruction_record_sha256)
    receipt = {
        "admission_performed": False,
        "authorization": AUTHORIZATION,
        "envelope_statuses": copy.deepcopy(envelopes),
        "instruction_content_anchor": _validate_instruction_anchors(observation.instruction_content_anchor, instruction_records),
        "instruction_record_sha256": instruction_records,
        "non_counted": True,
        "path_census": _validate_counts(observation.path_census, PATH_CENSUS_FIELDS, label="path census"),
        "prompt_statuses": copy.deepcopy(prompts),
        "public_context": _validate_public_context(observation.public_context),
        "record_counts": _validate_counts(observation.record_counts, RECORD_COUNT_FIELDS, label="record counts"),
        "schema": PUBLIC_RECEIPT_SCHEMA,
        "scoreable": False,
        "signed_identity": signed_identity,
        "source_status": observation.source_status,
        "success_packet_capable": False,
        "unknown_context_field_count": observation.unknown_context_field_count,
        "world_state_census": _validate_counts(observation.world_state_census, WORLD_STATE_CENSUS_FIELDS, label="world-state census"),
        "world_state_status": observation.world_state_status,
        "wrapper_census": _validate_wrapper_census(observation.wrapper_census),
    }
    payload = live._json_bytes(receipt)
    violations = live._privacy_violations(payload)
    if violations:
        raise live.CanaryError("calibration public receipt is not privacy-safe: " + "; ".join(violations))
    return receipt


def publish(path: Path, observation: CalibrationObservation) -> Path:
    """Create-once publish canonical public bytes; never writes private values."""

    payload = live._json_bytes(public_receipt(observation))
    chain._publish_create_once(path, payload)
    if path.read_bytes() != payload:
        raise live.CanaryError("calibration receipt bytes differ after publication")
    return path
