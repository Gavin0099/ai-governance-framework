#!/usr/bin/env python3
"""Gate 3 experiment-local metrics and scorer-ordering evidence chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "gate3-protocol-contract.v1"
METRICS_SCHEMA = "gate3-run-metrics.v1"
SCORE_SCHEMA = "gate3-blind-score.v1"
MAPPING_SCHEMA = "gate3-mapping-release.v1"
RANDOMIZATION_SCHEMA = "gate3-randomization-record.v1"
MAPPING_COMMITMENT_SCHEMA = "gate3-mapping-reveal-commitment.v1"
ADMISSION_SCHEMA = "gate3-outcome-admission.v1"
OUTCOME_PACKET_SCHEMA = "gate3-outcome-packet.v1"
TASK_DECISION_SCHEMA = "gate3-task-decision.v1"
RECEIPT_SCHEMA = "gate3-test-evidence-receipt.v1"
HARNESS_CONTRACT_SCHEMA = "gate3-common-harness-contract.v1"
EVENT_SCHEMA = "gate3-ordering-event.v1"
MANIFEST_SCHEMA = "gate3-preregistration-amendment-candidate-set.v1"
ANON_ID = re.compile(r"^OUT-[0-9a-f]{12}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EVENT_SEQUENCE = (
    "randomization_committed",
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
        "gate3-harness-contract-v1.json"
    ),
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
HARNESS_CONTRACT_NAME = "gate3-harness-contract-v1.json"
ADMISSION_INPUT_DIGEST_FIELDS = (
    "baseline_instruction_sha256",
    "task_packet_sha256",
    "treatment_packet_sha256",
    "governance_instruction_sha256",
    "validator_bundle_sha256",
    "validator_config_sha256",
    "permissions_sha256",
    "budget_sha256",
    "harness_contract_sha256",
    "scorer_rubric_sha256",
    "randomization_record_sha256",
)
TREATMENT_INPUT_DIGEST_FIELDS = (
    "treatment_packet_sha256",
    "governance_instruction_sha256",
    "validator_bundle_sha256",
    "validator_config_sha256",
)
_GIT_PROOF_CACHE: set[tuple[str, str, str, str, tuple[str, ...]]] = set()


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


def _positive_int(value: object, field: str) -> int:
    parsed = _non_negative_int(value, field)
    if parsed == 0:
        raise EvidenceError(f"{field} must be greater than zero")
    return parsed


def _git(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _validate_source_base_commit(repo_root: Path, source_base_commit: str) -> None:
    if not HEX40.fullmatch(source_base_commit):
        raise EvidenceError("source_base_commit must be a full 40-hex commit")
    _git(repo_root, "cat-file", "-e", f"{source_base_commit}^{{commit}}")
    head = _git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    if not HEX40.fullmatch(head):
        raise EvidenceError("repository HEAD is not a full commit")
    _git(repo_root, "merge-base", "--is-ancestor", source_base_commit, head)


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
    harness = value.get("harness_prerequisite")
    if not isinstance(harness, dict) or (
        harness.get("candidate_contract_path") != HARNESS_CONTRACT_NAME
        or harness.get("owner_signature_requires_candidate_contract") is not True
    ):
        raise EvidenceError("candidate harness contract is not signature-bound")
    harness_path = path.parent / HARNESS_CONTRACT_NAME
    harness_raw = harness_path.read_bytes()
    harness_value = _load_json(harness_path)
    if (
        harness_value.get("schema") != HARNESS_CONTRACT_SCHEMA
        or harness_value.get("authorization")
        != "candidate_only_not_gate3_start_authority"
    ):
        raise EvidenceError("candidate harness contract is invalid")
    admission = harness_value.get("admission")
    if (
        not isinstance(admission, dict)
        or admission.get("schema") != ADMISSION_SCHEMA
        or tuple(admission.get("input_digest_fields", []))
        != ADMISSION_INPUT_DIGEST_FIELDS
        or tuple(admission.get("retained_input_artifact_fields", []))
        != ADMISSION_INPUT_DIGEST_FIELDS
        or tuple(admission.get("retained_input_artifact_entry_fields", []))
        != ("path", "sha256")
    ):
        raise EvidenceError("candidate harness admission contract differs from runtime")
    receipt = harness_value.get("test_receipt")
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("index_policy") != "sorted_unique_paths"
    ):
        raise EvidenceError("candidate harness receipt contract differs from runtime")
    packet_policy = harness_value.get("scorer_packet")
    payload_policy = (
        packet_policy.get("scorer_payload")
        if isinstance(packet_policy, dict)
        else None
    )
    if (
        not isinstance(packet_policy, dict)
        or packet_policy.get("field_policy")
        != "exact_set_no_additional_top_level_fields"
        or not isinstance(packet_policy.get("forbidden_identity_substrings"), list)
        or not packet_policy["forbidden_identity_substrings"]
        or not isinstance(payload_policy, dict)
        or payload_policy.get("field_policy") != "exact_set_no_additional_fields"
        or payload_policy.get("value_policy")
        != "scalar_values_only_no_nested_objects_or_arrays"
        or not isinstance(payload_policy.get("allowed_fields"), list)
        or not payload_policy["allowed_fields"]
    ):
        raise EvidenceError("candidate harness packet contract differs from runtime")
    value["_harness_contract_sha256"] = _sha256_bytes(harness_raw)
    value["_scorer_packet_policy"] = packet_policy
    return value, _sha256_bytes(raw)


def _scorer_visible_strings(value: Any, *, keys: bool = True):
    """Yield every key and string value anywhere inside a scorer packet."""
    if isinstance(value, dict):
        for key, item in value.items():
            if keys and isinstance(key, str):
                yield key
            yield from _scorer_visible_strings(item, keys=keys)
    elif isinstance(value, list):
        for item in value:
            yield from _scorer_visible_strings(item, keys=keys)
    elif isinstance(value, str):
        yield value


def _validate_scorer_packet_shape(
    packet: dict[str, Any], policy: dict[str, Any]
) -> None:
    """Refuse a packet that carries more than the scorer is meant to see.

    Requiring the necessary fields to be present says nothing about what else
    rides along. Withholding the mapping is not blindness if the packet names
    the arm, so the field set is exact and every key and string value in the
    whole document is checked against the forbidden vocabulary.
    """
    if set(packet) != set(policy["required_fields"]):
        raise EvidenceError("outcome packet carries fields outside the exact set")
    payload_policy = policy["scorer_payload"]
    payload = packet["scorer_payload"]
    if set(payload) != set(payload_policy["allowed_fields"]):
        raise EvidenceError(
            "outcome packet scorer_payload differs from the allowed field set"
        )
    for item in payload.values():
        if isinstance(item, (dict, list)):
            raise EvidenceError("outcome packet scorer_payload value is not scalar")
    forbidden = tuple(policy["forbidden_identity_substrings"])
    exempt = set(payload_policy.get("identity_scan_exempt_fields", ()))
    scanned = {
        key: value for key, value in packet.items() if key != "scorer_payload"
    }
    scanned["scorer_payload"] = {
        key: value for key, value in payload.items() if key not in exempt
    }
    # Keys are never exempt, only the values of declared producer-output
    # fields. A fix may legitimately contain any word; a field name may not.
    for text in _scorer_visible_strings(scanned):
        lowered = text.lower()
        if any(marker in lowered for marker in forbidden):
            raise EvidenceError("outcome packet reveals treatment identity")
    for key in payload:
        lowered = key.lower()
        if any(marker in lowered for marker in forbidden):
            raise EvidenceError("outcome packet reveals treatment identity")


def _mapping_commitment(
    mapping: dict[str, str], study_kind: str, nonce_hex: str
) -> str:
    payload = {
        "mapping": mapping,
        "nonce_hex": nonce_hex,
        "schema": MAPPING_COMMITMENT_SCHEMA,
        "study_kind": study_kind,
    }
    return _sha256_bytes(_json_bytes(payload))


def validate_randomization_record(
    value: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    if value.get("schema") != RANDOMIZATION_SCHEMA:
        raise EvidenceError("randomization record schema is invalid")
    study_kind = value.get("study_kind")
    treatment_sets = contract["evidence_chain"]["mapping_treatments"]
    if study_kind not in treatment_sets:
        raise EvidenceError("randomization study_kind is invalid")
    for field in ("task_id", "pair_id"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise EvidenceError(f"randomization {field} must be non-empty")
    repeat_index = _non_negative_int(
        value.get("repeat_index"), "randomization repeat_index"
    )
    if repeat_index not in (1, 2, 3):
        raise EvidenceError("randomization repeat_index must be 1, 2 or 3")
    anon_ids = value.get("anonymous_ids")
    expected_count = contract["evidence_chain"]["anonymous_outcomes_per_comparison"]
    if (
        not isinstance(anon_ids, list)
        or len(anon_ids) != expected_count
        or anon_ids != sorted(anon_ids)
        or len(set(anon_ids)) != expected_count
        or any(not isinstance(item, str) or not ANON_ID.fullmatch(item) for item in anon_ids)
    ):
        raise EvidenceError("randomization anonymous_ids are invalid")
    if not HEX64.fullmatch(str(value.get("mapping_commitment_sha256", ""))):
        raise EvidenceError("randomization mapping commitment is invalid")
    treatment_inputs = value.get("treatment_inputs")
    expected_treatments = set(treatment_sets[study_kind])
    if not isinstance(treatment_inputs, dict) or set(treatment_inputs) != expected_treatments:
        raise EvidenceError("randomization treatment input population is invalid")
    for treatment, inputs in treatment_inputs.items():
        if not isinstance(inputs, dict) or set(inputs) != set(
            TREATMENT_INPUT_DIGEST_FIELDS
        ):
            raise EvidenceError(
                f"randomization treatment inputs are invalid for {treatment}"
            )
        for field in TREATMENT_INPUT_DIGEST_FIELDS:
            if not HEX64.fullmatch(str(inputs.get(field, ""))):
                raise EvidenceError(
                    f"randomization {treatment}.{field} digest is invalid"
                )
    return value


def validate_mapping_reveal(
    mapping_doc: dict[str, Any],
    contract: dict[str, Any],
    randomization_record: dict[str, Any],
    randomization_record_sha256: str,
) -> dict[str, str]:
    if mapping_doc.get("schema") != MAPPING_SCHEMA:
        raise EvidenceError("mapping schema is invalid")
    study_kind = randomization_record["study_kind"]
    if mapping_doc.get("study_kind") != study_kind:
        raise EvidenceError("mapping study_kind mismatch")
    mapping = mapping_doc.get("mapping")
    nonce_hex = mapping_doc.get("nonce_hex")
    expected_ids = set(randomization_record["anonymous_ids"])
    expected_treatments = set(
        contract["evidence_chain"]["mapping_treatments"][study_kind]
    )
    if (
        not isinstance(mapping, dict)
        or set(mapping) != expected_ids
        or set(mapping.values()) != expected_treatments
        or not isinstance(nonce_hex, str)
        or len(nonce_hex)
        != contract["evidence_chain"]["mapping_commitment"][
            "nonce_hex_characters"
        ]
        or not HEX64.fullmatch(nonce_hex)
    ):
        raise EvidenceError("mapping population, treatment set or nonce is invalid")
    if (
        mapping_doc.get("randomization_record_sha256")
        != randomization_record_sha256
        or _mapping_commitment(mapping, study_kind, nonce_hex)
        != randomization_record["mapping_commitment_sha256"]
    ):
        raise EvidenceError("mapping does not match preregistered commitment")
    return mapping


def _blind_input_set_sha256(outcomes: dict[str, dict[str, Any]]) -> str:
    inputs = [
        {
            "anon_id": anon_id,
            "packet_sha256": outcomes[anon_id]["packet_sha256"],
        }
        for anon_id in sorted(outcomes)
    ]
    return _sha256_bytes(_json_bytes(inputs))


def _verify_git_proof(
    bundle_path: Path,
    baseline_commit: str,
    output_commit: str,
    final_diff_path: Path,
    tracked_changed_files: list[str],
) -> None:
    cache_key = (
        _sha256_file(bundle_path),
        baseline_commit,
        output_commit,
        _sha256_file(final_diff_path),
        tuple(tracked_changed_files),
    )
    if cache_key in _GIT_PROOF_CACHE:
        return
    with tempfile.TemporaryDirectory() as temporary:
        clone = Path(temporary) / "repo"
        completed = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                str(bundle_path),
                str(clone),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise EvidenceError(f"git bundle clone failed: {detail}")
        _git(clone, "cat-file", "-e", f"{baseline_commit}^{{commit}}")
        _git(clone, "cat-file", "-e", f"{output_commit}^{{commit}}")
        _git(clone, "merge-base", "--is-ancestor", baseline_commit, output_commit)
        expected_diff = _git(
            clone,
            "diff",
            "--binary",
            "--full-index",
            baseline_commit,
            output_commit,
            "--",
        )
        if final_diff_path.read_bytes() != expected_diff:
            raise EvidenceError("retained final diff does not match bundled commits")
        expected_paths = [
            item.decode("utf-8")
            for item in _git(
                clone,
                "diff",
                "--name-only",
                "-z",
                baseline_commit,
                output_commit,
                "--",
            ).split(b"\0")
            if item
        ]
        if tracked_changed_files != expected_paths:
            raise EvidenceError("tracked changed files do not match bundled commits")
    _GIT_PROOF_CACHE.add(cache_key)


def _verify_live_capture(
    repo_root: Path,
    baseline_commit: str,
    output_commit: str,
    final_diff_path: Path,
) -> None:
    _git(repo_root, "cat-file", "-e", f"{baseline_commit}^{{commit}}")
    _git(repo_root, "cat-file", "-e", f"{output_commit}^{{commit}}")
    _git(repo_root, "merge-base", "--is-ancestor", baseline_commit, output_commit)
    head = _git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    if head != output_commit:
        raise EvidenceError("live capture HEAD does not match output_commit")
    if _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise EvidenceError("live capture worktree is not clean")
    live_diff = _git(
        repo_root,
        "diff",
        "--binary",
        "--full-index",
        baseline_commit,
        output_commit,
        "--",
    )
    if live_diff != final_diff_path.read_bytes():
        raise EvidenceError("live capture diff does not match retained final diff")


def validate_admission(
    admission_path: Path,
    packet_path: Path,
    metrics: dict[str, Any],
    contract: dict[str, Any],
    chain_dir: Path,
    *,
    live_repo_root: Path | None = None,
) -> dict[str, Any]:
    admission_raw = admission_path.read_bytes()
    admission = _load_json(admission_path)
    if admission_raw != _json_bytes(admission):
        raise EvidenceError("outcome admission is not canonical JSON")
    if admission.get("schema") != ADMISSION_SCHEMA:
        raise EvidenceError("outcome admission schema is invalid")
    if admission.get("anon_id") != metrics["anon_id"]:
        raise EvidenceError("admission anon_id does not match metrics")
    baseline_commit = str(admission.get("baseline_commit", ""))
    output_commit = str(admission.get("output_commit", ""))
    if (
        baseline_commit != metrics["baseline_commit"]
        or not HEX40.fullmatch(baseline_commit)
        or not HEX40.fullmatch(output_commit)
        or baseline_commit == output_commit
    ):
        raise EvidenceError("admission commit identity is invalid")
    if admission.get("worktree_clean_at_capture") is not True:
        raise EvidenceError("admission does not attest a clean capture")
    if admission.get("model_build") != metrics["model_build"]:
        raise EvidenceError("admission model_build does not match metrics")
    treatment = admission.get("treatment")
    all_treatments = {
        item
        for values in contract["evidence_chain"]["mapping_treatments"].values()
        for item in values
    }
    if treatment not in all_treatments:
        raise EvidenceError("admission treatment is invalid")

    input_digests = admission.get("input_digests")
    if not isinstance(input_digests, dict) or set(input_digests) != set(
        ADMISSION_INPUT_DIGEST_FIELDS
    ):
        raise EvidenceError("admission input digest field set is invalid")
    for field in ADMISSION_INPUT_DIGEST_FIELDS:
        if not HEX64.fullmatch(str(input_digests.get(field, ""))):
            raise EvidenceError(f"admission {field} digest is invalid")
    metric_bindings = {
        "task_packet_sha256": metrics["task_packet_sha256"],
        "permissions_sha256": metrics["permissions_sha256"],
        "budget_sha256": metrics["budget_sha256"],
        "harness_contract_sha256": metrics["harness_contract_sha256"],
        "scorer_rubric_sha256": metrics["scorer_rubric_sha256"],
        "randomization_record_sha256": metrics["randomization_record_sha256"],
    }
    if any(input_digests[field] != expected for field, expected in metric_bindings.items()):
        raise EvidenceError("admission input digest does not match metrics")
    if (
        input_digests["harness_contract_sha256"]
        != contract["_harness_contract_sha256"]
    ):
        raise EvidenceError("admission does not bind the candidate harness contract")
    input_artifacts = admission.get("input_artifacts")
    if not isinstance(input_artifacts, dict) or set(input_artifacts) != set(
        ADMISSION_INPUT_DIGEST_FIELDS
    ):
        raise EvidenceError("admission retained input artifact field set is invalid")
    retained_paths: list[str] = []
    for field in ADMISSION_INPUT_DIGEST_FIELDS:
        entry = input_artifacts[field]
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise EvidenceError(f"admission retained input artifact is invalid: {field}")
        source_path = _source_from_event(entry.get("path"), chain_dir)
        if (
            not source_path.is_file()
            or entry.get("sha256") != input_digests[field]
            or entry["sha256"] != _sha256_file(source_path)
        ):
            raise EvidenceError(
                f"admission retained input artifact does not match digest: {field}"
            )
        retained_paths.append(entry["path"])
    if len(set(retained_paths)) != len(retained_paths):
        raise EvidenceError("admission retained input artifact paths must be unique")

    packet_raw = packet_path.read_bytes()
    packet = _load_json(packet_path)
    if packet_raw != _json_bytes(packet):
        raise EvidenceError("outcome packet is not canonical JSON")
    if (
        packet.get("schema") != OUTCOME_PACKET_SCHEMA
        or packet.get("anon_id") != admission["anon_id"]
        or packet.get("baseline_commit") != baseline_commit
        or packet.get("output_commit") != output_commit
        or packet.get("harness_contract_sha256")
        != input_digests["harness_contract_sha256"]
        or not isinstance(packet.get("scorer_payload"), dict)
    ):
        raise EvidenceError("outcome packet identity or schema is invalid")
    _validate_scorer_packet_shape(packet, contract["_scorer_packet_policy"])
    packet_sha = _sha256_bytes(packet_raw)
    if (
        admission.get("output_packet_sha256") != packet_sha
        or metrics["artifacts"]["output_packet_sha256"] != packet_sha
    ):
        raise EvidenceError("admission output packet digest is invalid")

    event_log = admission.get("event_log")
    if not isinstance(event_log, dict):
        raise EvidenceError("admission event_log is absent")
    event_log_path = _source_from_event(event_log.get("path"), chain_dir)
    if (
        not event_log_path.is_file()
        or event_log.get("sha256") != _sha256_file(event_log_path)
        or event_log["sha256"] != metrics["artifacts"]["event_log_sha256"]
    ):
        raise EvidenceError("retained event log identity is invalid")

    final_diff = admission.get("final_diff")
    if not isinstance(final_diff, dict):
        raise EvidenceError("admission final_diff is absent")
    final_diff_path = _source_from_event(final_diff.get("path"), chain_dir)
    if not final_diff_path.is_file():
        raise EvidenceError("retained final diff is absent")
    final_diff_sha = _sha256_file(final_diff_path)
    tracked_changed_files = final_diff.get("tracked_changed_files")
    if (
        final_diff.get("sha256") != final_diff_sha
        or packet.get("final_diff_sha256") != final_diff_sha
        or not isinstance(tracked_changed_files, list)
        or not tracked_changed_files
        or tracked_changed_files != sorted(set(tracked_changed_files))
        or any(not isinstance(item, str) or not item for item in tracked_changed_files)
    ):
        raise EvidenceError("admission final diff identity is invalid")

    receipts = admission.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        raise EvidenceError("admission requires test receipts")
    receipt_paths = [
        entry.get("path") if isinstance(entry, dict) else None
        for entry in receipts
    ]
    if (
        any(not isinstance(path, str) or not path for path in receipt_paths)
        or receipt_paths != sorted(set(receipt_paths))
    ):
        raise EvidenceError("admission receipt paths must be sorted and unique")
    receipt_index: list[dict[str, str]] = []
    for entry in receipts:
        if not isinstance(entry, dict):
            raise EvidenceError("admission receipt entry is invalid")
        receipt_path = _source_from_event(entry.get("path"), chain_dir)
        if not receipt_path.is_file():
            raise EvidenceError("retained test receipt is absent")
        receipt_raw = receipt_path.read_bytes()
        receipt = _load_json(receipt_path)
        if receipt_raw != _json_bytes(receipt):
            raise EvidenceError("test receipt is not canonical JSON")
        receipt_sha = _sha256_bytes(receipt_raw)
        output_path = _source_from_event(receipt.get("output_path"), chain_dir)
        if (
            entry.get("sha256") != receipt_sha
            or receipt.get("schema") != RECEIPT_SCHEMA
            or receipt.get("linked_commit") != output_commit
            or receipt.get("exit_code") != 0
            or not isinstance(receipt.get("command"), str)
            or not receipt["command"].strip()
            or not output_path.is_file()
            or receipt.get("output_sha256") != _sha256_file(output_path)
        ):
            raise EvidenceError("test receipt does not bind the output commit")
        receipt_index.append({"path": entry["path"], "sha256": receipt_sha})
    receipt_set_sha = _sha256_bytes(_json_bytes(receipt_index))
    if (
        admission.get("receipt_set_sha256") != receipt_set_sha
        or packet.get("receipt_set_sha256") != receipt_set_sha
    ):
        raise EvidenceError("receipt set digest is invalid")

    bundle = admission.get("git_bundle")
    if not isinstance(bundle, dict):
        raise EvidenceError("admission git_bundle is absent")
    bundle_path = _source_from_event(bundle.get("path"), chain_dir)
    if (
        not bundle_path.is_file()
        or bundle.get("sha256") != _sha256_file(bundle_path)
    ):
        raise EvidenceError("retained git bundle identity is invalid")
    _verify_git_proof(
        bundle_path,
        baseline_commit,
        output_commit,
        final_diff_path,
        tracked_changed_files,
    )
    if live_repo_root is not None:
        _verify_live_capture(
            live_repo_root, baseline_commit, output_commit, final_diff_path
        )
    return admission


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
    if value["harness_contract_sha256"] != contract["_harness_contract_sha256"]:
        raise EvidenceError("metrics do not bind the candidate harness contract")
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
    core_available = costs.get("core_available")
    if not isinstance(core_available, bool):
        raise EvidenceError("costs.core_available must be boolean")
    core_fields = tuple(contract["run_metrics"]["core_cost_fields"])
    if core_available:
        for field in core_fields:
            _positive_int(costs.get(field), f"costs.{field}")
        if "core_unavailable_reason" in costs:
            raise EvidenceError("available core costs may not carry a reason")
    else:
        if any(costs.get(field) is not None for field in core_fields):
            raise EvidenceError("unavailable core costs must be null")
        if (
            not isinstance(costs.get("core_unavailable_reason"), str)
            or not costs["core_unavailable_reason"].strip()
        ):
            raise EvidenceError("unavailable core costs require a reason")
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


def evaluate_cost_gate(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    gate = contract["decision_rule"]["cost_gate"]
    wall_ratios: list[float] = []
    tool_ratios: list[float] = []
    for arm_a, arm_b in pairs:
        costs_a = arm_a.get("costs")
        costs_b = arm_b.get("costs")
        if not isinstance(costs_a, dict) or not isinstance(costs_b, dict):
            raise EvidenceError("cost gate pair lacks cost objects")
        if costs_a.get("core_available") is not True or costs_b.get(
            "core_available"
        ) is not True:
            continue
        wall_a = _positive_int(costs_a.get("wall_clock_ms"), "A wall_clock_ms")
        wall_b = _positive_int(costs_b.get("wall_clock_ms"), "B wall_clock_ms")
        tools_a = _positive_int(costs_a.get("tool_calls"), "A tool_calls")
        tools_b = _positive_int(costs_b.get("tool_calls"), "B tool_calls")
        wall_ratios.append(wall_b / wall_a)
        tool_ratios.append(tools_b / tools_a)
    minimum = _positive_int(gate.get("minimum_valid_pairs"), "minimum_valid_pairs")
    if len(wall_ratios) < minimum:
        return {
            "status": gate["telemetry_unavailable_disposition"],
            "valid_pairs": len(wall_ratios),
        }
    wall_median = statistics.median(wall_ratios)
    tool_median = statistics.median(tool_ratios)
    passed = (
        wall_median <= gate["median_paired_wall_clock_ratio_max"]
        and tool_median <= gate["median_paired_tool_call_ratio_max"]
    )
    return {
        "median_paired_tool_call_ratio": tool_median,
        "median_paired_wall_clock_ratio": wall_median,
        "status": "PASS" if passed else "NEGATIVE",
        "valid_pairs": len(wall_ratios),
    }


def _conditional_score_fields(contract: dict[str, Any]) -> tuple[str, ...]:
    return tuple(contract["scorer_submission"]["conditional_quality_fields"])


def validate_submission(
    value: dict[str, Any],
    contract: dict[str, Any],
    role: str,
    outcomes: dict[str, dict[str, Any]],
    *,
    blind_input_set_sha256: str,
    scorer_rubric_sha256: str,
) -> dict[str, Any]:
    if value.get("schema") != SCORE_SCHEMA:
        raise EvidenceError("scorer submission schema is invalid")
    if value.get("scorer_role") != role:
        raise EvidenceError("scorer role does not match command role")
    for field in ("scorer_identity", "scorer_context_id", "model_build"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise EvidenceError(f"scorer {field} must be non-empty")
    if (
        value.get("scorer_rubric_sha256") != scorer_rubric_sha256
        or value.get("blind_input_set_sha256") != blind_input_set_sha256
        or value.get("independence_declaration") is not True
    ):
        raise EvidenceError("scorer identity, rubric or blind-input binding is invalid")
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
    scorer_metadata: dict[str, dict[str, str]] = {}
    closed_ids: list[str] | None = None
    study_kind: str | None = None
    pair_controls: dict[str, Any] | None = None
    randomization_record: dict[str, Any] | None = None
    randomization_record_sha256: str | None = None
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

        if expected_event == "randomization_committed":
            randomization_path = _source_from_event(
                event.get("randomization_record_path"), chain_dir
            )
            if not randomization_path.is_file():
                raise EvidenceError("randomization record source is absent")
            randomization_raw = randomization_path.read_bytes()
            randomization_record = validate_randomization_record(
                _load_json(randomization_path), contract
            )
            if randomization_raw != _json_bytes(randomization_record):
                raise EvidenceError("randomization record is not canonical JSON")
            randomization_record_sha256 = _sha256_bytes(randomization_raw)
            if (
                event.get("randomization_record_sha256")
                != randomization_record_sha256
                or event.get("mapping_commitment_sha256")
                != randomization_record["mapping_commitment_sha256"]
            ):
                raise EvidenceError("randomization commitment event is invalid")
        elif expected_event == "outcome_sealed":
            if randomization_record is None or randomization_record_sha256 is None:
                raise EvidenceError("outcome precedes randomization commitment")
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
            metrics_raw = metrics_path.read_bytes()
            metrics = validate_metrics(
                _load_json(metrics_path),
                contract,
                packet_sha256=str(event["packet_sha256"]),
            )
            if metrics_raw != _json_bytes(metrics):
                raise EvidenceError("sealed metrics are not canonical JSON")
            if metrics["anon_id"] != anon_id:
                raise EvidenceError("sealed metrics anon_id mismatch")
            if (
                anon_id not in randomization_record["anonymous_ids"]
                or metrics["randomization_record_sha256"]
                != randomization_record_sha256
                or metrics["task_id"] != randomization_record["task_id"]
                or metrics["pair_id"] != randomization_record["pair_id"]
                or metrics["repeat_index"] != randomization_record["repeat_index"]
            ):
                raise EvidenceError("sealed metrics do not match randomization record")
            admission_path = _source_from_event(
                event.get("admission_path"), chain_dir
            )
            if (
                not admission_path.is_file()
                or _sha256_file(admission_path) != event.get("admission_sha256")
            ):
                raise EvidenceError("sealed admission source identity is invalid")
            admission = validate_admission(
                admission_path,
                packet_path,
                metrics,
                contract,
                chain_dir,
            )
            outcomes[anon_id] = {
                "admission": admission,
                "completed_under_cap": metrics["completed_under_cap"],
                "controls": {
                    field: metrics[field] for field in COMMON_PAIR_FIELDS
                },
                "packet_sha256": event["packet_sha256"],
                "metrics_sha256": event["metrics_sha256"],
                "run_id": metrics["run_id"],
            }
        elif expected_event == "blind_set_closed":
            if randomization_record is None or randomization_record_sha256 is None:
                raise EvidenceError("blind-set closure lacks randomization commitment")
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
                or closed_ids != randomization_record["anonymous_ids"]
                or study_kind != randomization_record["study_kind"]
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
            if (
                event.get("randomization_record_sha256")
                != randomization_record_sha256
                or event.get("blind_input_set_sha256")
                != _blind_input_set_sha256(outcomes)
            ):
                raise EvidenceError("blind-set commitment binding is invalid")
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
            submission = validate_submission(
                _load_json(submission_path),
                contract,
                role,
                outcomes,
                blind_input_set_sha256=_blind_input_set_sha256(outcomes),
                scorer_rubric_sha256=str(pair_controls["scorer_rubric_sha256"]),
            )
            metadata = {
                field: submission[field]
                for field in (
                    "scorer_identity",
                    "scorer_context_id",
                    "model_build",
                    "scorer_rubric_sha256",
                    "blind_input_set_sha256",
                )
            }
            if event.get("scorer_metadata") != metadata:
                raise EvidenceError("scorer event metadata does not match submission")
            if role == "second" and (
                metadata["scorer_context_id"]
                == scorer_metadata["primary"]["scorer_context_id"]
            ):
                raise EvidenceError("primary and second scorer contexts are not independent")
            scorer_metadata[role] = metadata
            scorer_event_digests[role] = _sha256_bytes(raw)
        elif expected_event == "mapping_released":
            if (
                closed_ids is None
                or study_kind is None
                or randomization_record is None
                or randomization_record_sha256 is None
            ):
                raise EvidenceError("mapping release precedes blind-set closure")
            mapping_path = _source_from_event(
                event.get("mapping_path"), chain_dir
            )
            if not mapping_path.is_file():
                raise EvidenceError("mapping source is absent")
            if _sha256_file(mapping_path) != event.get("mapping_sha256"):
                raise EvidenceError("mapping digest mismatch")
            mapping_doc = _load_json(mapping_path)
            if event.get("study_kind") != study_kind:
                raise EvidenceError("mapping event study_kind mismatch")
            mapping = validate_mapping_reveal(
                mapping_doc,
                contract,
                randomization_record,
                randomization_record_sha256,
            )
            for anon_id, treatment in mapping.items():
                admission = outcomes[anon_id]["admission"]
                if admission["treatment"] != treatment:
                    raise EvidenceError("released mapping does not match admitted treatment")
                expected_inputs = randomization_record["treatment_inputs"][treatment]
                if any(
                    admission["input_digests"][field] != expected_inputs[field]
                    for field in TREATMENT_INPUT_DIGEST_FIELDS
                ):
                    raise EvidenceError(
                        "admitted treatment inputs do not match randomization record"
                    )
            if event.get("scorer_event_sha256") != scorer_event_digests:
                raise EvidenceError("mapping release scorer-event digests mismatch")
            if (
                event.get("randomization_record_sha256")
                != randomization_record_sha256
            ):
                raise EvidenceError("mapping event randomization digest mismatch")
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


def commit_randomization(
    chain_dir: Path,
    contract_path: Path,
    randomization_record_path: Path,
) -> Path:
    contract, _ = load_contract(contract_path)
    if not randomization_record_path.is_file():
        raise EvidenceError("randomization record file is absent")
    raw = randomization_record_path.read_bytes()
    record = validate_randomization_record(
        _load_json(randomization_record_path), contract
    )
    if raw != _json_bytes(record):
        raise EvidenceError("randomization record is not canonical JSON")
    return _append_event(
        chain_dir,
        contract_path,
        "randomization_committed",
        {
            "mapping_commitment_sha256": record["mapping_commitment_sha256"],
            "randomization_record_path": _source_relative_to_evidence_root(
                randomization_record_path, chain_dir
            ),
            "randomization_record_sha256": _sha256_bytes(raw),
        },
    )


def seal_outcome(
    chain_dir: Path,
    contract_path: Path,
    packet_path: Path,
    metrics_path: Path,
    admission_path: Path,
    repo_root: Path,
) -> Path:
    contract, _ = load_contract(contract_path)
    if (
        not packet_path.is_file()
        or not metrics_path.is_file()
        or not admission_path.is_file()
    ):
        raise EvidenceError("packet, metrics and admission files must exist")
    packet_sha = _sha256_file(packet_path)
    metrics = validate_metrics(
        _load_json(metrics_path), contract, packet_sha256=packet_sha
    )
    validate_admission(
        admission_path,
        packet_path,
        metrics,
        contract,
        chain_dir,
        live_repo_root=repo_root,
    )
    return _append_event(
        chain_dir,
        contract_path,
        "outcome_sealed",
        {
            "admission_path": _source_relative_to_evidence_root(
                admission_path, chain_dir
            ),
            "admission_sha256": _sha256_file(admission_path),
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


def resolve_qualifying_success(
    primary: dict[str, Any],
    second: dict[str, Any],
    verifier: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Decide one run's qualifying success from two scorers, conservatively.

    Two scorers with no stated disagreement rule is not two scorers; it is one
    scorer plus an unresolved argument, and whoever reads the result later gets
    to pick. Under conservative intersection a run qualifies only if both
    scorers pass every scorer-judged field. Disagreement makes it not a
    qualifying success and leaves it in the denominator, so a conflict cannot
    quietly shrink the sample or be resolved toward the larger effect.

    Objective fields are not voted on. Test outcomes, commits and receipts come
    from the verifier, which observed them.
    """
    policy = contract["decision_rule"]["scorer_disagreement_policy"]
    conflicts: list[str] = []
    judged: dict[str, bool] = {}
    for field in policy["scorer_judged_fields"]:
        first, other = primary.get(field), second.get(field)
        if first != other:
            conflicts.append(field)
            judged[field] = False
            continue
        judged[field] = first is True
    determined = {
        field: verifier.get(field) is True
        for field in policy["verifier_determined_fields"]
    }
    return {
        "conflicting_fields": sorted(conflicts),
        "qualifying_success": all(judged.values()) and all(determined.values()),
        "scorer_judged": judged,
        "scorers_conflicted": bool(conflicts),
        "verifier_determined": determined,
    }


def _pair_qualifying_counts(
    pairs: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[dict[str, int], list[dict[str, Any]], bool]:
    """Resolve every run in every pair, conservatively."""
    counts = {"A": 0, "B": 0}
    detail: list[dict[str, Any]] = []
    any_non_completed = False
    for pair in pairs:
        entry: dict[str, Any] = {
            "pair_id": pair["pair_id"],
            "repeat_index": pair["repeat_index"],
            "runs": {},
        }
        for arm in ("A", "B"):
            run = pair["runs"][arm]
            resolved = resolve_qualifying_success(
                run["primary"], run["second"], run["verifier"], contract
            )
            if resolved["qualifying_success"]:
                counts[arm] += 1
            if run["verifier"].get("completed_under_cap") is not True:
                any_non_completed = True
            entry["runs"][arm] = resolved
        detail.append(entry)
    return counts, detail, any_non_completed


def build_task_decision(
    task_id: str,
    study_kind: str,
    pairs: list[dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Decide a task from exactly two or three verified pairs.

    The disagreement boundary was written into the contract as flags, and flags
    are not enforcement: nothing refused a fourth pair, an adjudicator or a
    replacement, because no code path decided a task at all. This is that path.

    A tie after two pairs, or any non-completed run, requires the third pair,
    which is the frozen adaptive sample. After three pairs the task is decided
    however the counts fall. Nothing authorizes a fourth.
    """
    policy = contract["decision_rule"]["scorer_disagreement_policy"]
    maximum = policy["maximum_pairs_per_task"]
    roles = list(contract["scorer_submission"]["roles"])
    if study_kind not in contract["evidence_chain"]["mapping_treatments"]:
        raise EvidenceError("task decision study_kind is not registered")
    if not isinstance(pairs, list) or len(pairs) < 2:
        raise EvidenceError("task decision requires at least two pairs")
    if len(pairs) > maximum:
        raise EvidenceError("task decision exceeds the frozen maximum pairs")
    seen_ids: set[str] = set()
    seen_indexes: set[int] = set()
    for pair in pairs:
        pair_id = pair.get("pair_id")
        repeat_index = pair.get("repeat_index")
        if not isinstance(pair_id, str) or not pair_id.strip():
            raise EvidenceError("task decision pair_id must be non-empty")
        if pair_id in seen_ids:
            raise EvidenceError("task decision repeats a pair_id")
        seen_ids.add(pair_id)
        if repeat_index not in range(1, maximum + 1):
            raise EvidenceError("task decision repeat_index is out of range")
        if repeat_index in seen_indexes:
            raise EvidenceError("task decision repeats a repeat_index")
        seen_indexes.add(repeat_index)
        if pair.get("replacement_for") is not None:
            raise EvidenceError(
                "task decision admits no replacement pair"
            )
        runs = pair.get("runs")
        if not isinstance(runs, dict) or set(runs) != {"A", "B"}:
            raise EvidenceError("task decision pair must carry exactly two arms")
        for run in runs.values():
            if not isinstance(run, dict) or set(run) != {
                "primary",
                "second",
                "verifier",
            }:
                raise EvidenceError(
                    "task decision run must carry exactly the two roles and the "
                    "verifier"
                )
    if seen_indexes != set(range(1, len(pairs) + 1)):
        raise EvidenceError("task decision repeat_index sequence has a gap")
    counts, detail, any_non_completed = _pair_qualifying_counts(pairs, contract)
    conflicted = [
        {
            "arm": arm,
            "fields": entry["runs"][arm]["conflicting_fields"],
            "pair_id": entry["pair_id"],
        }
        for entry in detail
        for arm in ("A", "B")
        if entry["runs"][arm]["scorers_conflicted"]
    ]
    tied = counts["A"] == counts["B"]
    if len(pairs) < maximum and (tied or any_non_completed):
        status = "third_pair_required"
        winner = None
    else:
        status = "decided"
        winner = None if tied else max(counts, key=counts.__getitem__)
    return {
        "conflict_record": conflicted,
        "pair_count": len(pairs),
        "pairs": detail,
        "qualifying_success_counts": counts,
        "schema": TASK_DECISION_SCHEMA,
        "scorer_roles": roles,
        "status": status,
        "study_kind": study_kind,
        "task_id": task_id,
        "winner": winner,
    }


def verify_task_decision(
    receipt: dict[str, Any],
    pairs: list[dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Recompute the decision and refuse any receipt that differs."""
    if receipt.get("schema") != TASK_DECISION_SCHEMA:
        raise EvidenceError("task decision schema is invalid")
    rebuilt = build_task_decision(
        str(receipt.get("task_id", "")),
        str(receipt.get("study_kind", "")),
        pairs,
        contract,
    )
    if receipt != rebuilt:
        raise EvidenceError("task decision differs from the recomputed decision")
    return rebuilt


def _assert_single_varying_factor(
    admissions: list[dict[str, Any]],
    study_kind: str,
    contract: dict[str, Any],
) -> None:
    """Refuse a pair whose arms differ in more than the studied factor.

    Checking that each arm matches its own preregistered digests says nothing
    about how the arms differ from each other. If governance and validator
    inputs vary alongside the skill packet, the arm difference cannot be read
    as the skill effect, and the whole comparison silently measures a mixture.
    """
    controls = contract["comparison_controls"]
    varying = controls["varying_input_digests"].get(study_kind)
    if not isinstance(varying, list) or not varying:
        raise EvidenceError("study_kind has no declared varying factor")
    varying_set = set(varying)
    digests = []
    for admission in admissions:
        entry = admission.get("input_digests")
        if not isinstance(entry, dict):
            raise EvidenceError("sealed outcome admission has no input digests")
        digests.append(entry)
    for field in ADMISSION_INPUT_DIGEST_FIELDS:
        if field in varying_set:
            continue
        first, second = digests[0].get(field), digests[1].get(field)
        if first != second:
            raise EvidenceError(
                "sealed outcomes differ in an input outside the studied factor"
            )
    if all(
        digests[0].get(field) == digests[1].get(field) for field in varying_set
    ):
        raise EvidenceError("sealed outcomes do not differ in the studied factor")


def close_blind_set(
    chain_dir: Path,
    contract_path: Path,
    study_kind: str,
) -> Path:
    contract, _ = load_contract(contract_path)
    report = verify_chain(chain_dir, contract_path)
    if report["event_count"] != 3:
        raise EvidenceError("blind set requires exactly two sealed outcomes")
    files = _event_files(chain_dir)
    events = [
        _load_json(path)
        for path in files
        if _load_json(path)["event"] == "outcome_sealed"
    ]
    randomization_event = _load_json(files[0])
    randomization_record = _load_json(
        _source_from_event(
            randomization_event["randomization_record_path"], chain_dir
        )
    )
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
    admissions = [
        _load_json(_source_from_event(event["admission_path"], chain_dir))
        for event in events
    ]
    _assert_single_varying_factor(admissions, study_kind, contract)
    if (
        study_kind != randomization_record["study_kind"]
        or anon_ids != randomization_record["anonymous_ids"]
    ):
        raise EvidenceError("blind set differs from randomization record")
    outcome_summary = {
        event["anon_id"]: {"packet_sha256": event["packet_sha256"]}
        for event in events
    }
    return _append_event(
        chain_dir,
        contract_path,
        "blind_set_closed",
        {
            "anonymous_ids": anon_ids,
            "blind_input_set_sha256": _blind_input_set_sha256(outcome_summary),
            "pair_controls": controls[0],
            "randomization_record_sha256": randomization_event[
                "randomization_record_sha256"
            ],
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
    report = verify_chain(chain_dir, contract_path)
    next_sequence = report["event_count"] + 1
    if (
        next_sequence > len(EVENT_SEQUENCE)
        or EVENT_SEQUENCE[next_sequence - 1] != expected_event
    ):
        raise EvidenceError(
            f"event {expected_event} is not allowed after state {report['state']}"
        )
    events = [_load_json(path) for path in _event_files(chain_dir)]
    outcomes = {
        event["anon_id"]: {
            "completed_under_cap": _load_json(
                _source_from_event(event["metrics_path"], chain_dir)
            )["completed_under_cap"],
            "packet_sha256": event["packet_sha256"],
        }
        for event in events
        if event["event"] == "outcome_sealed"
    }
    close_event = next(
        event for event in events if event["event"] == "blind_set_closed"
    )
    submission = validate_submission(
        _load_json(submission_path),
        contract,
        role,
        outcomes,
        blind_input_set_sha256=close_event["blind_input_set_sha256"],
        scorer_rubric_sha256=close_event["pair_controls"][
            "scorer_rubric_sha256"
        ],
    )
    if role == "second":
        primary_event = next(
            event for event in events if event["event"] == "primary_scorer_submitted"
        )
        if (
            submission["scorer_context_id"]
            == primary_event["scorer_metadata"]["scorer_context_id"]
        ):
            raise EvidenceError("primary and second scorer contexts are not independent")
    metadata = {
        field: submission[field]
        for field in (
            "scorer_identity",
            "scorer_context_id",
            "model_build",
            "scorer_rubric_sha256",
            "blind_input_set_sha256",
        )
    }
    return _append_event(
        chain_dir,
        contract_path,
        expected_event,
        {
            "scorer_metadata": metadata,
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
    randomization_event = events[0]
    randomization_record_path = _source_from_event(
        randomization_event["randomization_record_path"], chain_dir
    )
    randomization_record = validate_randomization_record(
        _load_json(randomization_record_path), contract
    )
    randomization_sha = randomization_event["randomization_record_sha256"]
    close_event = next(
        event for event in events if event["event"] == "blind_set_closed"
    )
    if mapping_doc.get("study_kind") != close_event["study_kind"]:
        raise EvidenceError("mapping study_kind differs from blind set")
    mapping = validate_mapping_reveal(
        mapping_doc,
        contract,
        randomization_record,
        randomization_sha,
    )
    for event in events:
        if event["event"] != "outcome_sealed":
            continue
        admission = _load_json(
            _source_from_event(event["admission_path"], chain_dir)
        )
        treatment = mapping[event["anon_id"]]
        if admission["treatment"] != treatment:
            raise EvidenceError("released mapping does not match admitted treatment")
        if any(
            admission["input_digests"][field]
            != randomization_record["treatment_inputs"][treatment][field]
            for field in TREATMENT_INPUT_DIGEST_FIELDS
        ):
            raise EvidenceError(
                "admitted treatment inputs do not match randomization record"
            )
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
            "randomization_record_sha256": randomization_sha,
            "scorer_event_sha256": scorer_event_digests,
            "study_kind": close_event["study_kind"],
        },
    )


def build_candidate_manifest(
    repo_root: Path,
    output_path: Path,
    source_base_commit: str,
) -> dict[str, Any]:
    _validate_source_base_commit(repo_root, source_base_commit)
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
    _validate_source_base_commit(
        repo_root, str(manifest.get("source_base_commit", ""))
    )
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
    contract_path = repo_root / CANDIDATE_FILES[3]
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

    randomization = sub.add_parser("commit-randomization")
    randomization.add_argument("--chain-dir", required=True)
    randomization.add_argument("--contract", required=True)
    randomization.add_argument("--record", required=True)

    seal = sub.add_parser("seal-outcome")
    seal.add_argument("--chain-dir", required=True)
    seal.add_argument("--contract", required=True)
    seal.add_argument("--packet", required=True)
    seal.add_argument("--metrics", required=True)
    seal.add_argument("--admission", required=True)
    seal.add_argument("--repo-root", required=True)

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
            "randomization_committed",
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
        elif args.command == "commit-randomization":
            print(
                commit_randomization(
                    Path(args.chain_dir),
                    Path(args.contract),
                    Path(args.record),
                )
            )
        elif args.command == "seal-outcome":
            print(
                seal_outcome(
                    Path(args.chain_dir),
                    Path(args.contract),
                    Path(args.packet),
                    Path(args.metrics),
                    Path(args.admission),
                    Path(args.repo_root),
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
