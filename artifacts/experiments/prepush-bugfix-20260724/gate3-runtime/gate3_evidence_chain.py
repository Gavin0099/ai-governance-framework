#!/usr/bin/env python3
"""Gate 3 experiment-local metrics and scorer-ordering evidence chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "gate3-protocol-contract.v1"
METRICS_SCHEMA = "gate3-run-metrics.v1"
SCORE_SCHEMA = "gate3-blind-score.v1"
MAPPING_SCHEMA = "gate3-mapping-release.v1"
EVENT_SCHEMA = "gate3-ordering-event.v1"
MANIFEST_SCHEMA = "gate3-preregistration-amendment-candidate-set.v1"
ANON_ID = re.compile(r"^OUT-[0-9a-f]{12}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EVENT_SEQUENCE = (
    "outcome_sealed",
    "outcome_sealed",
    "blind_set_closed",
    "primary_scorer_submitted",
    "second_scorer_submitted",
    "mapping_released",
)
CANDIDATE_FILES = (
    ".gitattributes",
    "docs/governance/gate3-preregistration-amendment-v1-candidate-20260729.md",
    (
        "artifacts/experiments/prepush-bugfix-20260724/candidate/"
        "gate3-protocol-contract-v1.json"
    ),
    (
        "artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/"
        "gate3_evidence_chain.py"
    ),
    (
        "artifacts/experiments/prepush-bugfix-20260724/gate3-runtime/"
        "test_gate3_evidence_chain.py"
    ),
)
CANDIDATE_MANIFEST = (
    "artifacts/experiments/prepush-bugfix-20260724/candidate/"
    "gate3-preregistration-amendment-v1-candidate-manifest.json"
)
COMMON_PAIR_FIELDS = (
    "task_id",
    "pair_id",
    "repeat_index",
    "baseline_commit",
    "randomization_record_sha256",
    "task_packet_sha256",
    "model_build",
    "permissions_sha256",
    "budget_sha256",
    "harness_contract_sha256",
    "scorer_rubric_sha256",
)
CONTRACT_PAIR_CONTROLS = COMMON_PAIR_FIELDS[3:]


class EvidenceError(ValueError):
    """A fail-closed contract or retained-evidence error."""


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _source_relative_to_evidence_root(path: Path, chain_dir: Path) -> str:
    evidence_root = chain_dir.resolve().parent
    try:
        relative = path.resolve().relative_to(evidence_root)
    except ValueError as exc:
        raise EvidenceError(
            f"source artifact must stay under evidence root {evidence_root}: {path}"
        ) from exc
    return relative.as_posix()


def _source_from_event(relative: object, chain_dir: Path) -> Path:
    if not isinstance(relative, str) or not relative:
        raise EvidenceError("event source path is invalid")
    candidate = chain_dir.resolve().parent.joinpath(*relative.split("/"))
    try:
        candidate.resolve().relative_to(chain_dir.resolve().parent)
    except ValueError as exc:
        raise EvidenceError("event source path escapes evidence root") from exc
    return candidate


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON root is not an object: {path}")
    return value


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _publish_create_once(path: Path, payload: bytes) -> None:
    """Atomically publish complete bytes without permitting replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise EvidenceError(f"create-once target already exists: {path}")
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise EvidenceError(
                f"create-once target already exists: {path}"
            ) from exc
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"{field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise EvidenceError(f"{field} must include a timezone")
    return parsed


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EvidenceError(f"{field} must be a non-negative integer")
    return value


def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = _load_json(path)
    if value.get("schema") != CONTRACT_SCHEMA:
        raise EvidenceError("contract schema is not gate3-protocol-contract.v1")
    if (
        value.get("authorization")
        != "pending_independent_review_and_owner_signature"
    ):
        raise EvidenceError("contract is not an unsigned candidate")
    chain = value.get("evidence_chain")
    if not isinstance(chain, dict):
        raise EvidenceError("contract evidence_chain is absent")
    if tuple(chain.get("event_order", [])) != EVENT_SEQUENCE:
        raise EvidenceError("contract event order differs from runtime")
    primary = value.get("primary_study")
    if not isinstance(primary, dict) or tuple(
        primary.get("pair_controls", [])
    ) != CONTRACT_PAIR_CONTROLS:
        raise EvidenceError("contract pair controls differ from runtime")
    return value, _sha256_bytes(raw)


def validate_metrics(
    value: dict[str, Any],
    contract: dict[str, Any],
    *,
    packet_sha256: str | None = None,
) -> dict[str, Any]:
    if value.get("schema") != METRICS_SCHEMA:
        raise EvidenceError("metrics schema is invalid")
    for field in ("task_id", "pair_id", "run_id", "model_build"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise EvidenceError(f"metrics {field} must be non-empty")
    if not ANON_ID.fullmatch(str(value.get("anon_id", ""))):
        raise EvidenceError("metrics anon_id is invalid")
    if not HEX40.fullmatch(str(value.get("baseline_commit", ""))):
        raise EvidenceError("metrics baseline_commit is invalid")
    for field in (
        "task_packet_sha256",
        "permissions_sha256",
        "budget_sha256",
        "harness_contract_sha256",
        "scorer_rubric_sha256",
        "randomization_record_sha256",
    ):
        if not isinstance(value.get(field), str) or not HEX64.fullmatch(
            value[field]
        ):
            raise EvidenceError(f"metrics {field} is invalid")
    repeat_index = _non_negative_int(value.get("repeat_index"), "repeat_index")
    if repeat_index not in (1, 2, 3):
        raise EvidenceError("repeat_index must be 1, 2 or 3")

    status = value.get("status")
    allowed = contract["run_metrics"]["terminal_statuses"]
    if status not in allowed:
        raise EvidenceError(f"metrics status is not allowed: {status}")
    completed = value.get("completed_under_cap")
    eligible = value.get("conditional_quality_eligible")
    if not isinstance(completed, bool) or not isinstance(eligible, bool):
        raise EvidenceError("completion and quality eligibility must be booleans")
    expected_completed = status == "completed"
    if completed is not expected_completed or eligible is not expected_completed:
        raise EvidenceError(
            "status, completed_under_cap and conditional_quality_eligible disagree"
        )

    timestamps = value.get("timestamps")
    if not isinstance(timestamps, dict):
        raise EvidenceError("timestamps must be an object")
    started = _parse_timestamp(timestamps.get("started_at"), "started_at")
    finished = _parse_timestamp(timestamps.get("finished_at"), "finished_at")
    if finished < started:
        raise EvidenceError("finished_at precedes started_at")
    first_edit_raw = timestamps.get("first_edit_at")
    if first_edit_raw is not None:
        first_edit = _parse_timestamp(first_edit_raw, "first_edit_at")
        if first_edit < started or first_edit > finished:
            raise EvidenceError("first_edit_at is outside the run interval")

    costs = value.get("costs")
    if not isinstance(costs, dict):
        raise EvidenceError("costs must be an object")
    for field in contract["run_metrics"]["cost_fields"]:
        _non_negative_int(costs.get(field), f"costs.{field}")
    tokens = costs.get("tokens")
    if not isinstance(tokens, dict) or not isinstance(
        tokens.get("available"), bool
    ):
        raise EvidenceError("costs.tokens availability is invalid")
    token_counts = ("input", "output", "cache_read", "cache_write")
    if tokens["available"]:
        for field in token_counts:
            _non_negative_int(tokens.get(field), f"costs.tokens.{field}")
        if "reason" in tokens:
            raise EvidenceError("available token metrics may not carry a reason")
    else:
        if not isinstance(tokens.get("reason"), str) or not tokens["reason"].strip():
            raise EvidenceError("unavailable token metrics require a reason")
        if any(field in tokens for field in token_counts):
            raise EvidenceError("unavailable token metrics may not carry counts")

    observations = value.get("method_observations")
    if not isinstance(observations, dict):
        raise EvidenceError("method_observations must be an object")
    required_observations = set(
        contract["run_metrics"]["method_observation_fields"]
    )
    if set(observations) != required_observations:
        raise EvidenceError("method_observations field set is not exact")
    for name, observation in observations.items():
        if not isinstance(observation, dict):
            raise EvidenceError(f"method observation {name} is not an object")
        observed = observation.get("observed")
        evidence = observation.get("evidence_sha256")
        if not isinstance(observed, bool) or not isinstance(evidence, list):
            raise EvidenceError(f"method observation {name} is malformed")
        if any(not isinstance(item, str) or not HEX64.fullmatch(item) for item in evidence):
            raise EvidenceError(f"method observation {name} digest is invalid")
        if observed and not evidence:
            raise EvidenceError(
                f"observed method behavior {name} lacks digest evidence"
            )

    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        raise EvidenceError("artifacts must be an object")
    for field in ("event_log_sha256", "output_packet_sha256"):
        if not isinstance(artifacts.get(field), str) or not HEX64.fullmatch(
            artifacts[field]
        ):
            raise EvidenceError(f"artifacts.{field} is invalid")
    if packet_sha256 is not None and artifacts["output_packet_sha256"] != packet_sha256:
        raise EvidenceError("metrics output_packet_sha256 does not match packet")
    return value


def _conditional_score_fields(contract: dict[str, Any]) -> tuple[str, ...]:
    return tuple(contract["scorer_submission"]["conditional_quality_fields"])


def validate_submission(
    value: dict[str, Any],
    contract: dict[str, Any],
    role: str,
    outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if value.get("schema") != SCORE_SCHEMA:
        raise EvidenceError("scorer submission schema is invalid")
    if value.get("scorer_role") != role:
        raise EvidenceError("scorer role does not match command role")
    outputs = value.get("outputs")
    if not isinstance(outputs, list):
        raise EvidenceError("scorer outputs must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    fields = _conditional_score_fields(contract)
    for item in outputs:
        if not isinstance(item, dict):
            raise EvidenceError("scorer output is not an object")
        anon_id = item.get("anon_id")
        if not isinstance(anon_id, str) or anon_id in indexed:
            raise EvidenceError("scorer output anon_id is invalid or duplicated")
        completed = item.get("completed_under_cap")
        if not isinstance(completed, bool):
            raise EvidenceError("scorer completed_under_cap must be boolean")
        if anon_id not in outcomes:
            raise EvidenceError(f"unexpected scorer anon_id: {anon_id}")
        if completed is not outcomes[anon_id]["completed_under_cap"]:
            raise EvidenceError(f"scorer completion disagrees for {anon_id}")
        conditional = {field: item.get(field) for field in fields}
        if not completed:
            if any(value is not None for value in conditional.values()):
                raise EvidenceError(
                    f"non-completed output {anon_id} has scored quality"
                )
        else:
            if any(value is None for value in conditional.values()):
                raise EvidenceError(
                    f"completed output {anon_id} lacks conditional quality"
                )
            for field in (
                "oracle_acceptance",
                "regression_baseline_fail",
                "regression_passes_after_fix",
                "original_defect_caught",
                "no_new_scoped_regression",
            ):
                if not isinstance(conditional[field], bool):
                    raise EvidenceError(f"{anon_id} {field} must be boolean")
            sensitivity = conditional["sensitivity_score"]
            if not isinstance(sensitivity, dict):
                raise EvidenceError(f"{anon_id} sensitivity_score is invalid")
            caught = _non_negative_int(
                sensitivity.get("caught"), f"{anon_id}.sensitivity.caught"
            )
            total = _non_negative_int(
                sensitivity.get("total"), f"{anon_id}.sensitivity.total"
            )
            if total < 1 or caught > total:
                raise EvidenceError(f"{anon_id} sensitivity counts are invalid")
            for field in (
                "critical_residuals",
                "major_residuals",
                "claim_mismatch_count",
            ):
                _non_negative_int(conditional[field], f"{anon_id}.{field}")
            if conditional["scope_hygiene"] not in (
                "clean",
                "minor_issue",
                "major_issue",
            ):
                raise EvidenceError(f"{anon_id} scope_hygiene is invalid")
        indexed[anon_id] = item
    if set(indexed) != set(outcomes):
        raise EvidenceError("scorer anonymous population is incomplete")
    return value


def _event_files(chain_dir: Path) -> list[Path]:
    if not chain_dir.exists():
        return []
    unexpected = [
        path.name
        for path in chain_dir.iterdir()
        if not path.is_file()
        or path.is_symlink()
        or not re.fullmatch(r"\d{4}-[a-z0-9-]+\.json", path.name)
    ]
    if unexpected:
        raise EvidenceError(f"unexpected chain entries: {sorted(unexpected)}")
    return sorted(chain_dir.iterdir())


def verify_chain(
    chain_dir: Path,
    contract_path: Path,
    *,
    require_state: str | None = None,
) -> dict[str, Any]:
    contract, contract_sha = load_contract(contract_path)
    files = _event_files(chain_dir)
    if len(files) > len(EVENT_SEQUENCE):
        raise EvidenceError("chain has too many events")
    events: list[dict[str, Any]] = []
    previous_raw: bytes | None = None
    outcomes: dict[str, dict[str, Any]] = {}
    scorer_event_digests: dict[str, str] = {}
    closed_ids: list[str] | None = None
    study_kind: str | None = None
    pair_controls: dict[str, Any] | None = None
    for index, path in enumerate(files, start=1):
        raw = path.read_bytes()
        event = _load_json(path)
        if raw != _json_bytes(event):
            raise EvidenceError(f"event is not canonical JSON: {path.name}")
        expected_event = EVENT_SEQUENCE[index - 1]
        expected_name = (
            f"{index:04d}-{expected_event.replace('_', '-')}.json"
        )
        if path.name != expected_name:
            raise EvidenceError(f"chain sequence filename mismatch: {path.name}")
        if event.get("schema") != EVENT_SCHEMA:
            raise EvidenceError(f"event schema mismatch: {path.name}")
        if event.get("sequence") != index or event.get("event") != expected_event:
            raise EvidenceError(f"event sequence content mismatch: {path.name}")
        if event.get("contract_sha256") != contract_sha:
            raise EvidenceError(f"contract digest mismatch: {path.name}")
        expected_previous = (
            None if previous_raw is None else _sha256_bytes(previous_raw)
        )
        if event.get("previous_event_sha256") != expected_previous:
            raise EvidenceError(f"previous event digest mismatch: {path.name}")
        _parse_timestamp(event.get("recorded_at"), f"{path.name}.recorded_at")

        if expected_event == "outcome_sealed":
            anon_id = event.get("anon_id")
            if not isinstance(anon_id, str) or not ANON_ID.fullmatch(anon_id):
                raise EvidenceError(f"invalid sealed anon_id: {path.name}")
            if anon_id in outcomes:
                raise EvidenceError("duplicate sealed anonymous outcome")
            packet_path = _source_from_event(
                event.get("packet_path"), chain_dir
            )
            metrics_path = _source_from_event(
                event.get("metrics_path"), chain_dir
            )
            if not packet_path.is_file() or not metrics_path.is_file():
                raise EvidenceError("sealed source artifact is absent")
            if _sha256_file(packet_path) != event.get("packet_sha256"):
                raise EvidenceError("sealed packet digest mismatch")
            if _sha256_file(metrics_path) != event.get("metrics_sha256"):
                raise EvidenceError("sealed metrics digest mismatch")
            metrics = validate_metrics(
                _load_json(metrics_path),
                contract,
                packet_sha256=str(event["packet_sha256"]),
            )
            if metrics["anon_id"] != anon_id:
                raise EvidenceError("sealed metrics anon_id mismatch")
            outcomes[anon_id] = {
                "completed_under_cap": metrics["completed_under_cap"],
                "controls": {
                    field: metrics[field] for field in COMMON_PAIR_FIELDS
                },
                "packet_sha256": event["packet_sha256"],
                "metrics_sha256": event["metrics_sha256"],
                "run_id": metrics["run_id"],
            }
        elif expected_event == "blind_set_closed":
            closed_ids = event.get("anonymous_ids")
            study_kind = event.get("study_kind")
            mappings = contract["evidence_chain"]["mapping_treatments"]
            if study_kind not in mappings:
                raise EvidenceError("blind-set study_kind is invalid")
            if (
                not isinstance(closed_ids, list)
                or closed_ids != sorted(outcomes)
                or len(closed_ids)
                != contract["evidence_chain"]["anonymous_outcomes_per_comparison"]
            ):
                raise EvidenceError("closed anonymous set is invalid")
            expected_sources = {
                anon_id: {
                    "packet_sha256": outcomes[anon_id]["packet_sha256"],
                    "metrics_sha256": outcomes[anon_id]["metrics_sha256"],
                }
                for anon_id in closed_ids
            }
            if event.get("sealed_sources") != expected_sources:
                raise EvidenceError("blind-set source summary is invalid")
            control_values = {
                json.dumps(
                    outcome["controls"],
                    sort_keys=True,
                    ensure_ascii=False,
                )
                for outcome in outcomes.values()
            }
            if len(control_values) != 1:
                raise EvidenceError("sealed outcomes do not share pair controls")
            if len({outcome["run_id"] for outcome in outcomes.values()}) != len(
                outcomes
            ):
                raise EvidenceError("sealed outcomes reuse one run_id")
            pair_controls = next(iter(outcomes.values()))["controls"]
            if event.get("pair_controls") != pair_controls:
                raise EvidenceError("blind-set pair controls are invalid")
        elif expected_event in (
            "primary_scorer_submitted",
            "second_scorer_submitted",
        ):
            if closed_ids is None:
                raise EvidenceError("scorer submission precedes blind-set closure")
            role = "primary" if expected_event.startswith("primary") else "second"
            submission_path = _source_from_event(
                event.get("submission_path"), chain_dir
            )
            if not submission_path.is_file():
                raise EvidenceError("scorer submission source is absent")
            if _sha256_file(submission_path) != event.get("submission_sha256"):
                raise EvidenceError("scorer submission digest mismatch")
            validate_submission(
                _load_json(submission_path), contract, role, outcomes
            )
            scorer_event_digests[role] = _sha256_bytes(raw)
        elif expected_event == "mapping_released":
            if closed_ids is None or study_kind is None:
                raise EvidenceError("mapping release precedes blind-set closure")
            mapping_path = _source_from_event(
                event.get("mapping_path"), chain_dir
            )
            if not mapping_path.is_file():
                raise EvidenceError("mapping source is absent")
            if _sha256_file(mapping_path) != event.get("mapping_sha256"):
                raise EvidenceError("mapping digest mismatch")
            mapping_doc = _load_json(mapping_path)
            if mapping_doc.get("schema") != MAPPING_SCHEMA:
                raise EvidenceError("mapping schema is invalid")
            if mapping_doc.get("study_kind") != study_kind:
                raise EvidenceError("mapping study_kind mismatch")
            if event.get("study_kind") != study_kind:
                raise EvidenceError("mapping event study_kind mismatch")
            mapping = mapping_doc.get("mapping")
            expected_treatments = set(
                contract["evidence_chain"]["mapping_treatments"][study_kind]
            )
            if (
                not isinstance(mapping, dict)
                or set(mapping) != set(closed_ids)
                or set(mapping.values()) != expected_treatments
            ):
                raise EvidenceError("mapping population or treatment set is invalid")
            if event.get("scorer_event_sha256") != scorer_event_digests:
                raise EvidenceError("mapping release scorer-event digests mismatch")
        events.append(event)
        previous_raw = raw

    state = "empty" if not events else events[-1]["event"]
    if require_state is not None and state != require_state:
        raise EvidenceError(
            f"required chain state {require_state} not reached; current={state}"
        )
    return {
        "contract_sha256": contract_sha,
        "event_count": len(events),
        "head_sha256": (
            None if previous_raw is None else _sha256_bytes(previous_raw)
        ),
        "state": state,
        "status": "PASS",
    }


def _append_event(
    chain_dir: Path,
    contract_path: Path,
    event_name: str,
    fields: dict[str, Any],
) -> Path:
    report = verify_chain(chain_dir, contract_path)
    sequence = report["event_count"] + 1
    if sequence > len(EVENT_SEQUENCE) or EVENT_SEQUENCE[sequence - 1] != event_name:
        raise EvidenceError(
            f"event {event_name} is not allowed after state {report['state']}"
        )
    _, contract_sha = load_contract(contract_path)
    event = {
        "contract_sha256": contract_sha,
        "event": event_name,
        "previous_event_sha256": report["head_sha256"],
        "recorded_at": _utc_now(),
        "schema": EVENT_SCHEMA,
        "sequence": sequence,
        **fields,
    }
    path = chain_dir / (
        f"{sequence:04d}-{event_name.replace('_', '-')}.json"
    )
    _publish_create_once(path, _json_bytes(event))
    verify_chain(chain_dir, contract_path)
    return path


def seal_outcome(
    chain_dir: Path,
    contract_path: Path,
    packet_path: Path,
    metrics_path: Path,
) -> Path:
    contract, _ = load_contract(contract_path)
    if not packet_path.is_file() or not metrics_path.is_file():
        raise EvidenceError("packet and metrics files must exist")
    packet_sha = _sha256_file(packet_path)
    metrics = validate_metrics(
        _load_json(metrics_path), contract, packet_sha256=packet_sha
    )
    return _append_event(
        chain_dir,
        contract_path,
        "outcome_sealed",
        {
            "anon_id": metrics["anon_id"],
            "metrics_path": _source_relative_to_evidence_root(
                metrics_path, chain_dir
            ),
            "metrics_sha256": _sha256_file(metrics_path),
            "packet_path": _source_relative_to_evidence_root(
                packet_path, chain_dir
            ),
            "packet_sha256": packet_sha,
        },
    )


def close_blind_set(
    chain_dir: Path,
    contract_path: Path,
    study_kind: str,
) -> Path:
    contract, _ = load_contract(contract_path)
    report = verify_chain(chain_dir, contract_path)
    if report["event_count"] != 2:
        raise EvidenceError("blind set requires exactly two sealed outcomes")
    files = _event_files(chain_dir)
    events = [_load_json(path) for path in files]
    anon_ids = sorted(event["anon_id"] for event in events)
    sources = {
        event["anon_id"]: {
            "metrics_sha256": event["metrics_sha256"],
            "packet_sha256": event["packet_sha256"],
        }
        for event in events
    }
    metrics = [
        _load_json(_source_from_event(event["metrics_path"], chain_dir))
        for event in events
    ]
    controls = [
        {field: item[field] for field in COMMON_PAIR_FIELDS}
        for item in metrics
    ]
    if controls[0] != controls[1]:
        raise EvidenceError("sealed outcomes do not share pair controls")
    if metrics[0]["run_id"] == metrics[1]["run_id"]:
        raise EvidenceError("sealed outcomes reuse one run_id")
    if study_kind not in contract["evidence_chain"]["mapping_treatments"]:
        raise EvidenceError("study_kind is not registered")
    return _append_event(
        chain_dir,
        contract_path,
        "blind_set_closed",
        {
            "anonymous_ids": anon_ids,
            "pair_controls": controls[0],
            "sealed_sources": sources,
            "study_kind": study_kind,
        },
    )


def submit_scorer(
    chain_dir: Path,
    contract_path: Path,
    role: str,
    submission_path: Path,
) -> Path:
    contract, _ = load_contract(contract_path)
    if role not in contract["scorer_submission"]["roles"]:
        raise EvidenceError("scorer role is not registered")
    expected_event = f"{role}_scorer_submitted"
    if not submission_path.is_file():
        raise EvidenceError("scorer submission file is absent")
    verify_chain(chain_dir, contract_path)
    events = [_load_json(path) for path in _event_files(chain_dir)]
    outcomes = {
        event["anon_id"]: {
            "completed_under_cap": _load_json(
                _source_from_event(event["metrics_path"], chain_dir)
            )["completed_under_cap"]
        }
        for event in events
        if event["event"] == "outcome_sealed"
    }
    validate_submission(
        _load_json(submission_path), contract, role, outcomes
    )
    return _append_event(
        chain_dir,
        contract_path,
        expected_event,
        {
            "scorer_role": role,
            "submission_path": _source_relative_to_evidence_root(
                submission_path, chain_dir
            ),
            "submission_sha256": _sha256_file(submission_path),
        },
    )


def release_mapping(
    chain_dir: Path,
    contract_path: Path,
    mapping_path: Path,
) -> Path:
    contract, _ = load_contract(contract_path)
    verify_chain(
        chain_dir, contract_path, require_state="second_scorer_submitted"
    )
    if not mapping_path.is_file():
        raise EvidenceError("mapping file is absent")
    mapping_doc = _load_json(mapping_path)
    events = [_load_json(path) for path in _event_files(chain_dir)]
    close_event = next(
        event for event in events if event["event"] == "blind_set_closed"
    )
    if mapping_doc.get("schema") != MAPPING_SCHEMA:
        raise EvidenceError("mapping schema is invalid")
    if mapping_doc.get("study_kind") != close_event["study_kind"]:
        raise EvidenceError("mapping study_kind differs from blind set")
    mapping = mapping_doc.get("mapping")
    treatments = set(
        contract["evidence_chain"]["mapping_treatments"][
            close_event["study_kind"]
        ]
    )
    if (
        not isinstance(mapping, dict)
        or set(mapping) != set(close_event["anonymous_ids"])
        or set(mapping.values()) != treatments
    ):
        raise EvidenceError("mapping population or treatment set is invalid")
    scorer_event_digests = {
        event["scorer_role"]: _sha256_file(path)
        for path, event in zip(_event_files(chain_dir), events)
        if event["event"].endswith("_scorer_submitted")
    }
    return _append_event(
        chain_dir,
        contract_path,
        "mapping_released",
        {
            "mapping_path": _source_relative_to_evidence_root(
                mapping_path, chain_dir
            ),
            "mapping_sha256": _sha256_file(mapping_path),
            "scorer_event_sha256": scorer_event_digests,
            "study_kind": close_event["study_kind"],
        },
    )


def build_candidate_manifest(
    repo_root: Path,
    output_path: Path,
    source_base_commit: str,
) -> dict[str, Any]:
    if not HEX40.fullmatch(source_base_commit):
        raise EvidenceError("source_base_commit must be a full 40-hex commit")
    files = []
    for relative in CANDIDATE_FILES:
        path = repo_root.joinpath(*relative.split("/"))
        if not path.is_file():
            raise EvidenceError(f"candidate file is absent: {relative}")
        raw = path.read_bytes()
        files.append(
            {
                "bytes": len(raw),
                "path": relative,
                "sha256": _sha256_bytes(raw),
            }
        )
    value = {
        "authorization": "pending_independent_review_and_owner_signature",
        "files": files,
        "not_claimed": [
            "independent approval",
            "owner signature",
            "canonical promotion",
            "safe structured write harness",
            "natural bug admission",
            "Gate 3 start",
            "cryptographic writer authentication",
            "Skill effectiveness",
        ],
        "purpose": (
            "Exact candidate bytes for independent review and later owner "
            "signature; PASS does not authorize Gate 3."
        ),
        "schema": MANIFEST_SCHEMA,
        "source_base_commit": source_base_commit,
    }
    _atomic_write(output_path, _json_bytes(value))
    return value


def verify_candidate(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise EvidenceError("candidate manifest schema is invalid")
    if (
        manifest.get("authorization")
        != "pending_independent_review_and_owner_signature"
    ):
        raise EvidenceError("candidate manifest authorization is invalid")
    if not HEX40.fullmatch(str(manifest.get("source_base_commit", ""))):
        raise EvidenceError("candidate source_base_commit is invalid")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise EvidenceError("candidate manifest files are absent")
    if [entry.get("path") for entry in entries] != list(CANDIDATE_FILES):
        raise EvidenceError("candidate manifest file set or order is invalid")
    checks: list[dict[str, Any]] = []
    for entry in entries:
        path = repo_root.joinpath(*entry["path"].split("/"))
        exists = path.is_file()
        raw = path.read_bytes() if exists else b""
        passed = (
            exists
            and entry.get("bytes") == len(raw)
            and entry.get("sha256") == _sha256_bytes(raw)
        )
        checks.append({"check": entry["path"], "passed": passed})
        if not passed:
            raise EvidenceError(f"candidate file mismatch: {entry['path']}")
    contract_path = repo_root / CANDIDATE_FILES[2]
    load_contract(contract_path)
    attribute_lines = set(
        (repo_root / ".gitattributes").read_text(encoding="utf-8").splitlines()
    )
    exact_paths = (*CANDIDATE_FILES[1:], CANDIDATE_MANIFEST)
    missing_attributes = [
        relative
        for relative in exact_paths
        if f"/{relative} -text" not in attribute_lines
    ]
    if missing_attributes:
        raise EvidenceError(
            f"candidate byte-preservation attributes missing: {missing_attributes}"
        )
    return {
        "checks": [
            *checks,
            {
                "check": "byte_preservation_attributes_complete",
                "passed": True,
            },
        ],
        "manifest_sha256": _sha256_file(manifest_path),
        "status": "PASS",
    }


def _write_report(path: str | None, value: object) -> None:
    if path:
        _atomic_write(Path(path), _json_bytes(value))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    metrics = sub.add_parser("validate-metrics")
    metrics.add_argument("--contract", required=True)
    metrics.add_argument("--metrics", required=True)
    metrics.add_argument("--packet")
    metrics.add_argument("--json-out")

    seal = sub.add_parser("seal-outcome")
    seal.add_argument("--chain-dir", required=True)
    seal.add_argument("--contract", required=True)
    seal.add_argument("--packet", required=True)
    seal.add_argument("--metrics", required=True)

    close = sub.add_parser("close-blind-set")
    close.add_argument("--chain-dir", required=True)
    close.add_argument("--contract", required=True)
    close.add_argument(
        "--study-kind",
        required=True,
        choices=(
            "skill_primary",
            "governance_diagnostic",
            "validator_diagnostic",
        ),
    )

    submit = sub.add_parser("submit-scorer")
    submit.add_argument("--chain-dir", required=True)
    submit.add_argument("--contract", required=True)
    submit.add_argument("--role", required=True, choices=("primary", "second"))
    submit.add_argument("--submission", required=True)

    release = sub.add_parser("release-mapping")
    release.add_argument("--chain-dir", required=True)
    release.add_argument("--contract", required=True)
    release.add_argument("--mapping", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--chain-dir", required=True)
    verify.add_argument("--contract", required=True)
    verify.add_argument(
        "--require-state",
        choices=(
            "empty",
            "outcome_sealed",
            "blind_set_closed",
            "primary_scorer_submitted",
            "second_scorer_submitted",
            "mapping_released",
        ),
    )
    verify.add_argument("--json-out")

    build = sub.add_parser("build-candidate-manifest")
    build.add_argument("--repo-root", required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--source-base-commit", required=True)

    candidate = sub.add_parser("verify-candidate")
    candidate.add_argument("--repo-root", required=True)
    candidate.add_argument("--manifest", required=True)
    candidate.add_argument("--json-out")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-metrics":
            contract, contract_sha = load_contract(Path(args.contract))
            packet_sha = (
                _sha256_file(Path(args.packet)) if args.packet else None
            )
            validate_metrics(
                _load_json(Path(args.metrics)),
                contract,
                packet_sha256=packet_sha,
            )
            result = {"contract_sha256": contract_sha, "status": "PASS"}
            _write_report(args.json_out, result)
            print(json.dumps(result, sort_keys=True))
        elif args.command == "seal-outcome":
            print(
                seal_outcome(
                    Path(args.chain_dir),
                    Path(args.contract),
                    Path(args.packet),
                    Path(args.metrics),
                )
            )
        elif args.command == "close-blind-set":
            print(
                close_blind_set(
                    Path(args.chain_dir),
                    Path(args.contract),
                    args.study_kind,
                )
            )
        elif args.command == "submit-scorer":
            print(
                submit_scorer(
                    Path(args.chain_dir),
                    Path(args.contract),
                    args.role,
                    Path(args.submission),
                )
            )
        elif args.command == "release-mapping":
            print(
                release_mapping(
                    Path(args.chain_dir),
                    Path(args.contract),
                    Path(args.mapping),
                )
            )
        elif args.command == "verify":
            result = verify_chain(
                Path(args.chain_dir),
                Path(args.contract),
                require_state=args.require_state,
            )
            _write_report(args.json_out, result)
            print(json.dumps(result, sort_keys=True))
        elif args.command == "build-candidate-manifest":
            result = build_candidate_manifest(
                Path(args.repo_root),
                Path(args.out),
                args.source_base_commit,
            )
            print(json.dumps(result, sort_keys=True))
        elif args.command == "verify-candidate":
            result = verify_candidate(
                Path(args.repo_root), Path(args.manifest)
            )
            _write_report(args.json_out, result)
            print(json.dumps(result, sort_keys=True))
        else:  # pragma: no cover - argparse guarantees the command.
            raise AssertionError(args.command)
    except (EvidenceError, OSError) as exc:
        result = {"error": str(exc), "status": "FAIL"}
        json_out = getattr(args, "json_out", None)
        _write_report(json_out, result)
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
