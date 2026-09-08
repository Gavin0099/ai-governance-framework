from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping


POLICY_SCHEMA = "gate1-new-experiment-cohort-policy.v1"
INVENTORY_SCHEMA = "c1-prior-infrastructure-evidence-inventory.v1"
PROJECTION_SCHEMA = "c1-preserved-preregistration-projection.v1"
COHORT_SCHEMA = "c1-new-experiment-cohort-record.v1"
TERMINAL_SCHEMA = "c1-new-experiment-cohort-amendment-terminal.v1"
GOVERNING_RULE = "NEW_EXPERIMENT_COHORT"
COHORT_ID = "C1-skill-primary-cohort-02"
ORIGINAL_MANIFEST_BYTES = 9190
ORIGINAL_MANIFEST_SHA256 = "8515cea0b62a8df1bb806782913ca4543f6699f53743ded3edd5fab42b3d67b7"
ORIGINAL_MANIFEST_OID = "911382a0205aae9abc3081442ac173a1eada11da"
OWNER_PACKET_BYTES = 17526
OWNER_PACKET_SHA256 = "572b0c91862abfc1006d6aff9d21f06729b6617058785a9942f8647bc78a97e9"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CohortAmendmentError(RuntimeError):
    pass


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def strict_json(payload: bytes) -> dict[str, Any]:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CohortAmendmentError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CohortAmendmentError("invalid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CohortAmendmentError("top-level JSON value must be an object")
    return value


def validate_owner_packet(payload: bytes) -> None:
    if len(payload) != OWNER_PACKET_BYTES or sha256(payload) != OWNER_PACKET_SHA256:
        raise CohortAmendmentError("owner-decision packet binding mismatch")


def read_git_blob(repo_root: Path, oid: str) -> bytes:
    if not HEX40.fullmatch(oid):
        raise CohortAmendmentError("invalid Git blob OID")
    completed = subprocess.run(
        ["git", "cat-file", "blob", oid],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0 or completed.stderr:
        raise CohortAmendmentError("unable to read bound Git blob")
    return completed.stdout


def validate_preserved_preregistration(
    manifest_payload: bytes,
    projection: Mapping[str, Any],
) -> None:
    if len(manifest_payload) != ORIGINAL_MANIFEST_BYTES:
        raise CohortAmendmentError("original manifest byte count drift")
    if sha256(manifest_payload) != ORIGINAL_MANIFEST_SHA256:
        raise CohortAmendmentError("original manifest digest drift")
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise CohortAmendmentError("projection schema mismatch")
    original = strict_json(manifest_payload)
    for field in ("owner_authority", "decision_rules", "attempt06_quarantine", "claim_ceiling"):
        if projection.get(field) != original.get(field):
            raise CohortAmendmentError(f"preserved preregistration field drift: {field}")
    assertions = projection.get("preservation_assertions")
    if not isinstance(assertions, dict) or assertions.get("decision_rules_reopened") is not False:
        raise CohortAmendmentError("decision rules were reopened")


def validate_inventory(inventory: Mapping[str, Any]) -> None:
    if inventory.get("schema") != INVENTORY_SCHEMA:
        raise CohortAmendmentError("inventory schema mismatch")
    files = inventory.get("files")
    if not isinstance(files, list) or len(files) != 6 or inventory.get("bounded_file_count") != 6:
        raise CohortAmendmentError("prior evidence inventory must bind exactly six files")
    paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise CohortAmendmentError("invalid inventory entry")
        path = entry.get("path")
        digest = entry.get("sha256")
        size = entry.get("bytes")
        if not isinstance(path, str) or path in paths or path.startswith("/") or ".." in Path(path).parts:
            raise CohortAmendmentError("invalid or duplicate inventory path")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise CohortAmendmentError("invalid inventory digest")
        if not isinstance(size, int) or size < 1:
            raise CohortAmendmentError("invalid inventory byte count")
        paths.add(path)
    mapping = next((item for item in files if item.get("content_class") == "private_control_surface"), None)
    if mapping is None:
        raise CohortAmendmentError("private mapping binding missing")
    if mapping.get("content_inspected_for_treatment_assignment") is not False:
        raise CohortAmendmentError("private mapping inspection is forbidden")
    if mapping.get("retention") != "bytes_and_sha256_only":
        raise CohortAmendmentError("private mapping retention widened")
    summary = inventory.get("mechanical_summary")
    validate_reset_eligibility(summary)
    if summary.get("infrastructure_attempts_consumed") != 2:
        raise CohortAmendmentError("prior infrastructure attempt count drift")
    if summary.get("randomizations_committed") != 1:
        raise CohortAmendmentError("prior randomization count drift")
    if summary.get("statistical_units_counted") != 0:
        raise CohortAmendmentError("prior statistical unit count drift")


def validate_reset_eligibility(summary: Any) -> None:
    if not isinstance(summary, Mapping):
        raise CohortAmendmentError("missing reset eligibility summary")
    zero_fields = (
        "producer_dispatches",
        "outcomes_sealed",
        "scorer_submissions",
        "outcome_bearing_units_observed",
    )
    for field in zero_fields:
        if summary.get(field) != 0:
            raise CohortAmendmentError(f"cohort reset forbidden after observation: {field}")
    if summary.get("mapping_released") is not False:
        raise CohortAmendmentError("cohort reset forbidden after mapping release")


def scan_prior_evidence_root(evidence_root: Path, inventory: Mapping[str, Any]) -> None:
    validate_inventory(inventory)
    expected = {entry["path"]: entry for entry in inventory["files"]}
    expected_pair_dirs = {Path(relative).parts[0] for relative in expected}
    actual: dict[str, Path] = {}
    if not evidence_root.is_dir() or evidence_root.is_symlink():
        raise CohortAmendmentError("evidence root missing or unsafe")
    observed_pair_dirs = {
        path.name
        for path in evidence_root.iterdir()
        if path.is_dir() and path.name.startswith("c1-skill-primary-pair-")
    }
    if observed_pair_dirs != expected_pair_dirs:
        raise CohortAmendmentError("prior pair directory inventory drift")
    for pair_dir_name in sorted(expected_pair_dirs):
        pair_dir = evidence_root / pair_dir_name
        if pair_dir.is_symlink() or not pair_dir.is_dir():
            raise CohortAmendmentError("prior pair directory missing or unsafe")
        for path in pair_dir.rglob("*"):
            if path.is_symlink():
                raise CohortAmendmentError("symlink forbidden in evidence root")
            if path.is_file():
                relative = path.relative_to(evidence_root).as_posix()
                actual[relative] = path
    if set(actual) != set(expected):
        raise CohortAmendmentError("prior evidence file inventory drift")
    for relative, path in actual.items():
        payload = path.read_bytes()
        bound = expected[relative]
        if len(payload) != bound["bytes"] or sha256(payload) != bound["sha256"]:
            raise CohortAmendmentError(f"prior evidence binding drift: {relative}")
        if bound.get("content_class") == "private_control_surface":
            continue
        document = strict_json(payload)
        for field in (
            "status",
            "freeze_commit",
            "randomization_created",
            "event_count",
            "chain_state",
            "pair_id",
            "event",
            "sequence",
            "admission_at_utc",
            "window_expires_at_utc",
        ):
            if field in bound and document.get(field) != bound[field]:
                raise CohortAmendmentError(f"prior evidence semantic drift: {relative}:{field}")


def validate_policy(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != POLICY_SCHEMA or policy.get("governing_rule") != GOVERNING_RULE:
        raise CohortAmendmentError("cohort policy identity mismatch")
    eligibility = policy.get("eligibility")
    validate_reset_eligibility(eligibility)
    abuse = policy.get("anti_reset_abuse")
    if not isinstance(abuse, Mapping):
        raise CohortAmendmentError("anti-reset policy missing")
    required = {
        "unfavorable_observed_result_may_be_relabelled_infrastructure_invalid": False,
        "reset_after_any_outcome_bearing_unit": "FORBIDDEN",
        "automatic_second_reset": False,
        "second_reset_requires_new_owner_decision": True,
        "second_reset_requires_observed_failure_analysis": True,
        "decision_rules_may_be_reopened": False,
    }
    if any(abuse.get(key) != value for key, value in required.items()):
        raise CohortAmendmentError("anti-reset policy weakened")
    if policy.get("rejected_rule", {}).get("token") != "RANDOMIZATION_COUNTING":
        raise CohortAmendmentError("rejected randomization-counting rule missing")


def validate_cohort_record(record: Mapping[str, Any]) -> None:
    if record.get("schema") != COHORT_SCHEMA or record.get("cohort_id") != COHORT_ID:
        raise CohortAmendmentError("cohort record identity mismatch")
    if record.get("status") != "FROZEN_NOT_RANDOMIZED":
        raise CohortAmendmentError("cohort record claims execution")
    surfaces = record.get("created_surfaces")
    if not isinstance(surfaces, Mapping) or any(value is not False for value in surfaces.values()):
        raise CohortAmendmentError("cohort record creates an unauthorized surface")
    resolution = record.get("decision_commit_resolution")
    if not isinstance(resolution, Mapping):
        raise CohortAmendmentError("decision commit resolution missing")
    if resolution.get("source") != "EXACT_EXECUTING_FREEZE_COMMIT_AT_ADMISSION":
        raise CohortAmendmentError("decision commit source is not exact executing commit")
    if resolution.get("resolved_in_this_freeze") is not False:
        raise CohortAmendmentError("self-referential decision commit claim")


def build_pair_budget_state(
    executing_freeze_commit: str,
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    if not HEX40.fullmatch(executing_freeze_commit):
        raise CohortAmendmentError("decision commit must be an exact full SHA")
    validate_inventory(inventory)
    summary = inventory["mechanical_summary"]
    return {
        "governing_rule": GOVERNING_RULE,
        "governing_rule_decision_commit": executing_freeze_commit,
        "cohort_id": COHORT_ID,
        "infrastructure_attempts_consumed": summary["infrastructure_attempts_consumed"],
        "randomizations_committed": summary["randomizations_committed"],
        "producer_dispatches": summary["producer_dispatches"],
        "outcomes_sealed": summary["outcomes_sealed"],
        "statistical_units_counted": summary["statistical_units_counted"],
        "remaining_authorized_units": 3,
    }


def validate_terminal(terminal: Mapping[str, Any]) -> None:
    if terminal.get("schema") != TERMINAL_SCHEMA:
        raise CohortAmendmentError("terminal schema mismatch")
    if terminal.get("status") != "NEW_EXPERIMENT_COHORT_AMENDMENT_FROZEN_NOT_RANDOMIZED":
        raise CohortAmendmentError("terminal status mismatch")
    authority_fields = (
        "machine_policy_setup_authorized",
        "randomization_authorized",
        "producer_authorized",
        "scorer_authorized",
        "arms_authorized",
        "mapping_release_authorized",
        "rekor_post_authorized",
    )
    if any(terminal.get(field) is not False for field in authority_fields):
        raise CohortAmendmentError("terminal widens execution authority")


def validate_freeze_documents(base: Path, git_blob_reader: Callable[[str], bytes]) -> dict[str, Any]:
    policy = strict_json((base / "new-experiment-cohort-policy.json").read_bytes())
    inventory = strict_json((base / "prior-evidence-inventory.json").read_bytes())
    projection = strict_json((base / "preserved-preregistration-projection.json").read_bytes())
    cohort = strict_json((base / "new-cohort-record.json").read_bytes())
    terminal = strict_json((base / "amendment-terminal.json").read_bytes())
    validate_policy(policy)
    validate_inventory(inventory)
    validate_cohort_record(cohort)
    validate_terminal(terminal)
    manifest_payload = git_blob_reader(ORIGINAL_MANIFEST_OID)
    validate_preserved_preregistration(manifest_payload, projection)
    return build_pair_budget_state("0" * 40, inventory)
