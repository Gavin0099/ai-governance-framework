from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "new_experiment_cohort_amendment",
    BASE / "new_experiment_cohort_amendment.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load(name: str) -> dict:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def repo_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=BASE,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Path(completed.stdout.strip())


def git_blob(oid: str) -> bytes:
    return MODULE.read_git_blob(repo_root(), oid)


def test_original_preregistration_is_byte_exact_and_field_exact() -> None:
    projection = load("preserved-preregistration-projection.json")
    payload = git_blob(MODULE.ORIGINAL_MANIFEST_OID)
    MODULE.validate_preserved_preregistration(payload, projection)


@pytest.mark.parametrize(
    "field",
    ["owner_authority", "decision_rules", "attempt06_quarantine", "claim_ceiling"],
)
def test_preserved_preregistration_drift_fails_closed(field: str) -> None:
    projection = load("preserved-preregistration-projection.json")
    projection[field] = {"tampered": True}
    with pytest.raises(MODULE.CohortAmendmentError, match=field):
        MODULE.validate_preserved_preregistration(
            git_blob(MODULE.ORIGINAL_MANIFEST_OID), projection
        )


def test_owner_decision_packet_binding_is_literal() -> None:
    manifest = load("amendment-manifest.json")
    packet = manifest["owner_authority"]["decision_packet"]
    assert packet["bytes"] == MODULE.OWNER_PACKET_BYTES == 17526
    assert packet["sha256"] == MODULE.OWNER_PACKET_SHA256
    assert packet["sha256"] == "572b0c91862abfc1006d6aff9d21f06729b6617058785a9942f8647bc78a97e9"


def test_inventory_binds_exact_prior_file_set_without_mapping_content() -> None:
    inventory = load("prior-evidence-inventory.json")
    MODULE.validate_inventory(inventory)
    assert inventory["bounded_file_count"] == 6
    mapping = next(
        item for item in inventory["files"]
        if item["content_class"] == "private_control_surface"
    )
    assert set(mapping) == {
        "path", "bytes", "sha256", "content_class",
        "content_inspected_for_treatment_assignment", "retention",
    }
    assert mapping["content_inspected_for_treatment_assignment"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("producer_dispatches", 1),
        ("outcomes_sealed", 1),
        ("scorer_submissions", 1),
        ("outcome_bearing_units_observed", 1),
        ("mapping_released", True),
    ],
)
def test_any_observed_result_forbids_reset(field: str, value: object) -> None:
    inventory = load("prior-evidence-inventory.json")
    inventory["mechanical_summary"][field] = value
    with pytest.raises(MODULE.CohortAmendmentError, match="forbidden"):
        MODULE.validate_inventory(inventory)


def test_window_expiry_alone_does_not_authorize_reset() -> None:
    policy = load("new-experiment-cohort-policy.json")
    MODULE.validate_policy(policy)
    assert policy["prior_attempt_disposition"]["window_expiry_alone_authorizes_reset"] is False


def test_second_reset_is_not_automatic() -> None:
    policy = load("new-experiment-cohort-policy.json")
    MODULE.validate_policy(policy)
    abuse = policy["anti_reset_abuse"]
    assert abuse["automatic_second_reset"] is False
    assert abuse["second_reset_requires_new_owner_decision"] is True
    assert abuse["second_reset_requires_observed_failure_analysis"] is True


def test_randomization_counting_is_rejected() -> None:
    policy = load("new-experiment-cohort-policy.json")
    MODULE.validate_policy(policy)
    assert policy["rejected_rule"]["token"] == "RANDOMIZATION_COUNTING"
    assert policy["infrastructure_attempt_is_not_statistical_unit"] is True


def test_new_cohort_record_creates_no_execution_surface() -> None:
    record = load("new-cohort-record.json")
    MODULE.validate_cohort_record(record)
    assert set(record["prior_execution_set"]["prior_pair_ids"]) == {
        "C1-skill-primary-pair-01", "C1-skill-primary-pair-02"
    }
    assert all(value is False for value in record["created_surfaces"].values())


def test_pair_budget_state_requires_exact_decision_commit() -> None:
    inventory = load("prior-evidence-inventory.json")
    with pytest.raises(MODULE.CohortAmendmentError, match="exact full SHA"):
        MODULE.build_pair_budget_state("short", inventory)
    state = MODULE.build_pair_budget_state("a" * 40, inventory)
    assert state == {
        "governing_rule": "NEW_EXPERIMENT_COHORT",
        "governing_rule_decision_commit": "a" * 40,
        "cohort_id": "C1-skill-primary-cohort-02",
        "infrastructure_attempts_consumed": 2,
        "randomizations_committed": 1,
        "producer_dispatches": 0,
        "outcomes_sealed": 0,
        "statistical_units_counted": 0,
        "remaining_authorized_units": 3,
    }


def test_terminal_preserves_all_execution_authority_as_false() -> None:
    terminal = load("amendment-terminal.json")
    MODULE.validate_terminal(terminal)
    tampered = copy.deepcopy(terminal)
    tampered["randomization_authorized"] = True
    with pytest.raises(MODULE.CohortAmendmentError, match="widens"):
        MODULE.validate_terminal(tampered)


def synthetic_evidence(tmp_path: Path) -> tuple[Path, dict]:
    documents = {
        "c1-skill-primary-pair-01/repeat-01/terminal.json": {
            "status": "RANDOMIZATION_BINDING_MISMATCH",
            "freeze_commit": "c" * 40,
            "randomization_created": False,
            "event_count": 0,
            "chain_state": "empty",
        },
        "c1-skill-primary-pair-02/repeat-01/batch-admission.json": {
            "admission_at_utc": "2026-08-27T02:29:55.939417Z",
            "window_expires_at_utc": "2026-08-27T14:29:55.939417Z",
        },
        "c1-skill-primary-pair-02/repeat-01/terminal.json": {
            "status": "RANDOMIZATION_COMMITTED",
            "freeze_commit": "d" * 40,
            "randomization_created": True,
            "event_count": 1,
            "chain_state": "randomization_committed",
        },
        "c1-skill-primary-pair-02/repeat-01/evidence/randomization-record.json": {
            "pair_id": "C1-skill-primary-pair-02"
        },
        "c1-skill-primary-pair-02/repeat-01/evidence/chain/0001-randomization-committed.json": {
            "event": "randomization_committed", "sequence": 1
        },
    }
    files = []
    for relative, document in documents.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(document, sort_keys=True) + "\n").encode()
        path.write_bytes(payload)
        entry = {
            "path": relative,
            "bytes": len(payload),
            "sha256": MODULE.sha256(payload),
            "content_class": "public_fixture",
        }
        entry.update(document)
        files.append(entry)
    mapping_path = tmp_path / "c1-skill-primary-pair-02/repeat-01/control/mapping-reveal.json"
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_payload = b"private fixture bytes"
    mapping_path.write_bytes(mapping_payload)
    files.append({
        "path": mapping_path.relative_to(tmp_path).as_posix(),
        "bytes": len(mapping_payload),
        "sha256": MODULE.sha256(mapping_payload),
        "content_class": "private_control_surface",
        "content_inspected_for_treatment_assignment": False,
        "retention": "bytes_and_sha256_only",
    })
    inventory = {
        "schema": MODULE.INVENTORY_SCHEMA,
        "bounded_file_count": 6,
        "files": files,
        "mechanical_summary": {
            "infrastructure_attempts_consumed": 2,
            "randomizations_committed": 1,
            "producer_dispatches": 0,
            "outcomes_sealed": 0,
            "scorer_submissions": 0,
            "outcome_bearing_units_observed": 0,
            "mapping_released": False,
            "statistical_units_counted": 0,
        },
    }
    return tmp_path, inventory


def test_synthetic_exact_evidence_scan_passes(tmp_path: Path) -> None:
    root, inventory = synthetic_evidence(tmp_path)
    MODULE.scan_prior_evidence_root(root, inventory)


def test_extra_outcome_file_fails_closed(tmp_path: Path) -> None:
    root, inventory = synthetic_evidence(tmp_path)
    extra = root / "c1-skill-primary-pair-02/repeat-01/evidence/outcome.json"
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MODULE.CohortAmendmentError, match="inventory drift"):
        MODULE.scan_prior_evidence_root(root, inventory)


def test_unbound_pair_directory_fails_closed(tmp_path: Path) -> None:
    root, inventory = synthetic_evidence(tmp_path)
    extra = root / "c1-skill-primary-pair-03/repeat-01/terminal.json"
    extra.parent.mkdir(parents=True)
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(MODULE.CohortAmendmentError, match="pair directory inventory drift"):
        MODULE.scan_prior_evidence_root(root, inventory)


def test_prior_evidence_digest_drift_fails_closed(tmp_path: Path) -> None:
    root, inventory = synthetic_evidence(tmp_path)
    target = root / inventory["files"][0]["path"]
    target.write_bytes(target.read_bytes() + b"drift")
    with pytest.raises(MODULE.CohortAmendmentError, match="binding drift"):
        MODULE.scan_prior_evidence_root(root, inventory)


def test_inventory_path_traversal_fails_closed() -> None:
    inventory = load("prior-evidence-inventory.json")
    inventory["files"][0]["path"] = "../escaped-terminal.json"
    with pytest.raises(MODULE.CohortAmendmentError, match="invalid or duplicate"):
        MODULE.validate_inventory(inventory)


def test_manifest_binds_every_file_except_itself() -> None:
    manifest = load("amendment-manifest.json")
    frozen = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {path.name for path in BASE.iterdir() if path.is_file()}
    assert set(frozen) == actual - {"amendment-manifest.json"}
    for relative, entry in frozen.items():
        payload = (BASE / relative).read_bytes()
        assert len(payload) == entry["bytes"]
        assert MODULE.sha256(payload) == entry["sha256"]


def test_full_freeze_document_validation() -> None:
    state = MODULE.validate_freeze_documents(BASE, git_blob)
    assert state["governing_rule"] == "NEW_EXPERIMENT_COHORT"
    assert state["statistical_units_counted"] == 0
