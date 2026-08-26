from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MANIFEST_PATH = HERE / "amendment-manifest.json"
POLICY_PATH = HERE / "d5-countability-policy.json"
TERMINAL_PATH = HERE / "d5-admission-terminal.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


D5 = load_module("d5_countability_amendment", HERE / "d5_countability_amendment.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(tmp_path: Path, manifest: dict | None = None) -> dict:
    return D5.evaluate_amended_admission(
        repo_root=ROOT,
        manifest=manifest or load_json(MANIFEST_PATH),
        randomization_path=tmp_path / "randomization.json",
    )


def exact_evidence(**overrides):
    values = {
        "event_names": D5.EVENT_ORDER,
        "event_7_proof_verified": True,
        "event_8_mapping_commitment_verified": True,
        "local_chain_verified": True,
        "final_head_receipt_present": False,
    }
    values.update(overrides)
    return values


def test_frozen_files_bind_every_file_except_manifest() -> None:
    manifest = load_json(MANIFEST_PATH)
    declared = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {
        path.name
        for path in HERE.iterdir()
        if path.is_file() and path.name != MANIFEST_PATH.name
    }
    assert set(declared) == actual
    for name, entry in declared.items():
        raw = (HERE / name).read_bytes()
        assert len(raw) == entry["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_owner_decision_packet_binding_is_exact() -> None:
    packet = load_json(MANIFEST_PATH)["owner_authority"]["decision_packet"]
    assert packet == {
        "bytes": 14040,
        "file": "c1-d5-final-head-countability-owner-decision-packet-2026-08-26.md",
        "lines": 326,
        "location": "repo_external_review_surface",
        "review_verdict": "APPROVED",
        "sha256": "d4fe3ba43ec9b2d1b74c3a14feb36dfad05ea945353e45b87dd979c89796cb6b",
    }


def test_original_freezes_remain_exactly_bound() -> None:
    manifest = load_json(MANIFEST_PATH)
    expected = {entry["path"]: entry["sha256"] for entry in manifest["bindings"]}
    for relative, digest in expected.items():
        raw = (ROOT / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
    assert manifest["preserved_decisions"] == {
        "attempt_06_quarantine": "UNCHANGED_BY_EXACT_PREREGISTRATION_BINDING",
        "client_side_identity_amendment": "UNCHANGED_BY_EXACT_AMENDMENT_BINDING",
        "d1_d7_thresholds": "UNCHANGED_BY_EXACT_PREREGISTRATION_BINDING",
        "frozen_d5_uniform_post_hoc_validator": "UNCHANGED",
    }


def test_policy_preserves_event_7_and_requires_local_event_8() -> None:
    policy = load_json(POLICY_PATH)
    D5.validate_policy(policy)
    assert len(policy["event_order"]) == 8
    assert policy["event_order"][6] == "external_chain_head_pinned"
    assert policy["event_order"][7] == "mapping_released"
    assert policy["event_7"]["proof_bearing"] is True
    assert policy["event_8"]["local_chain_required"] is True
    assert policy["event_8"]["mapping_commitment_required"] is True
    assert policy["final_head_receipt"]["event_9_defined"] is False


def test_missing_final_head_receipt_alone_is_not_a_failure() -> None:
    result = D5.assess_countability(**exact_evidence(final_head_receipt_present=False))
    assert result.countable is True
    assert result.reasons == ()
    assert result.final_head_receipt_required is False


def test_optional_final_head_receipt_does_not_change_countability() -> None:
    without_receipt = D5.assess_countability(**exact_evidence())
    with_receipt = D5.assess_countability(
        **exact_evidence(final_head_receipt_present=True)
    )
    assert without_receipt == with_receipt


def test_missing_event_7_fails_closed() -> None:
    events = tuple(event for event in D5.EVENT_ORDER if event != "external_chain_head_pinned")
    result = D5.assess_countability(**exact_evidence(event_names=events))
    assert result.countable is False
    assert result.reasons == ("EVENT_SEQUENCE_INVALID",)


def test_invalid_event_7_proof_cannot_be_rescued_by_final_head_receipt() -> None:
    result = D5.assess_countability(
        **exact_evidence(
            event_7_proof_verified=False,
            final_head_receipt_present=True,
        )
    )
    assert result.countable is False
    assert result.reasons == ("EVENT_7_EXTERNAL_PIN_INVALID",)


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (
            lambda values: values.update(
                event_names=tuple(
                    event for event in D5.EVENT_ORDER if event != "mapping_released"
                )
            ),
            "EVENT_SEQUENCE_INVALID",
        ),
        (
            lambda values: values.update(event_8_mapping_commitment_verified=False),
            "EVENT_8_MAPPING_COMMITMENT_INVALID",
        ),
        (
            lambda values: values.update(local_chain_verified=False),
            "LOCAL_FINAL_CHAIN_INVALID",
        ),
    ],
)
def test_missing_or_altered_event_8_fails_closed(mutation, expected_reason: str) -> None:
    values = exact_evidence()
    mutation(values)
    result = D5.assess_countability(**values)
    assert result.countable is False
    assert expected_reason in result.reasons


def test_extra_event_9_fails_closed() -> None:
    result = D5.assess_countability(
        **exact_evidence(event_names=(*D5.EVENT_ORDER, "final_head_pinned"))
    )
    assert result.countable is False
    assert result.reasons == ("EVENT_SEQUENCE_INVALID",)


def test_amended_admission_passes_without_creating_randomization(tmp_path: Path) -> None:
    result = evaluate(tmp_path)
    assert result == load_json(TERMINAL_PATH)
    assert result["status"] == D5.PASSED
    assert result["randomization_created"] is False
    assert all(result["checks"].values())
    assert not (tmp_path / "randomization.json").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["countability_decision"].__setitem__(
            "resolved_token", "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION"
        ),
        lambda value: value["owner_authority"]["decision_packet"].__setitem__(
            "sha256", "0" * 64
        ),
        lambda value: value["execution_authority"].__setitem__(
            "randomization_authorized", True
        ),
    ],
)
def test_decision_or_authority_drift_stops(tmp_path: Path, mutation) -> None:
    manifest = copy.deepcopy(load_json(MANIFEST_PATH))
    mutation(manifest)
    result = evaluate(tmp_path, manifest)
    assert result["status"] == D5.STOPPED
    assert "D5_AMENDMENT_INVALID" in result["reasons"]


def test_binding_drift_stops(tmp_path: Path) -> None:
    manifest = copy.deepcopy(load_json(MANIFEST_PATH))
    manifest["bindings"][0]["sha256"] = "0" * 64
    result = evaluate(tmp_path, manifest)
    assert result["status"] == D5.STOPPED
    assert any(reason.startswith("BINDING_MISMATCH:") for reason in result["reasons"])


def test_existing_randomization_stops_without_modification(tmp_path: Path) -> None:
    randomization = tmp_path / "randomization.json"
    randomization.write_bytes(b"{}\n")
    result = D5.evaluate_amended_admission(
        repo_root=ROOT,
        manifest=load_json(MANIFEST_PATH),
        randomization_path=randomization,
    )
    assert result["status"] == D5.STOPPED
    assert result["reasons"] == ["RANDOMIZATION_ALREADY_EXISTS"]
    assert randomization.read_bytes() == b"{}\n"


def test_cli_precondition_failure_writes_one_stop_terminal(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]\n", encoding="utf-8")
    out = tmp_path / "terminal.json"
    exit_code = D5.main(
        [
            "--repo-root",
            str(ROOT),
            "--manifest",
            str(invalid),
            "--randomization-path",
            str(tmp_path / "never-created.json"),
            "--out",
            str(out),
        ]
    )
    terminal = load_json(out)
    assert exit_code == 3
    assert terminal["status"] == D5.STOPPED
    assert terminal["randomization_created"] is False
    assert terminal["reasons"] == ["ADMISSION_PRECONDITION_FAILED:D5CountabilityError"]
    assert len(list(tmp_path.glob("terminal.json"))) == 1
