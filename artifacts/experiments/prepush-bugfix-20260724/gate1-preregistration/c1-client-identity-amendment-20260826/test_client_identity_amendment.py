from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load("external_preflight_adapter")
IDENTITY = _load("client_identity_receipt")
HEX = "a" * 64


def _fields(phase: str, captured: datetime) -> dict[str, object]:
    return {
        "phase": phase,
        "comparison_id": "C1-P01",
        "anonymous_outcome_id": "OUT-001",
        "captured_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "batch_admission_sha256": HEX,
        "model_requested_id": "gpt-5.6-sol",
        "model_request_source": "frozen_cli_argv",
        "model_request_argument_sha256": IDENTITY.model_request_argument_sha256(),
        "identity_evidence_level": "CLIENT_SIDE_INVOCATION_ONLY",
        "server_executed_model_observed": False,
        "provider_attestation_available": False,
        "cli_version": "codex-cli 0.148.0-alpha.9",
        "cli_version_stdout_bytes": 26,
        "cli_version_stdout_sha256": IDENTITY.EXPECTED_CLI_VERSION_STDOUT_SHA256,
        "cli_executable_bytes": 295_151_920,
        "cli_executable_sha256": PREFLIGHT.EXPECTED_EXECUTABLE_SHA256,
        "runner_git_blob_oid": PREFLIGHT.EXPECTED_RUNNER_BLOB_OID,
        "runner_bytes": PREFLIGHT.EXPECTED_RUNNER_BYTES,
        "runner_sha256": PREFLIGHT.EXPECTED_RUNNER_SHA256,
        "preflight_adapter_sha256": IDENTITY.EXPECTED_PREFLIGHT_ADAPTER_SHA256,
        "python_executable_sha256": IDENTITY.EXPECTED_PYTHON_SHA256,
        "command_contract_sha256": IDENTITY.EXPECTED_COMMAND_CONTRACT_SHA256,
        "previous_event_sha256": HEX,
    }


def test_manifest_binds_every_non_manifest_file_exactly() -> None:
    manifest = json.loads((HERE / "amendment-manifest.json").read_text("utf-8"))
    declared = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {
        path.name
        for path in HERE.iterdir()
        if path.is_file() and path.name != "amendment-manifest.json"
    }
    assert set(declared) == actual
    for name, entry in declared.items():
        raw = (HERE / name).read_bytes()
        assert len(raw) == entry["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_selected_runner_and_command_contract_are_exact() -> None:
    route, codex = PREFLIGHT._load_runner_modules()
    runner = Path(codex.__file__).resolve()
    assert runner.stat().st_size == 44_296
    assert route._sha256_file(runner) == PREFLIGHT.EXPECTED_RUNNER_SHA256
    projection = PREFLIGHT.command_contract_projection()
    assert projection["command_contract_sha256"] == IDENTITY.EXPECTED_COMMAND_CONTRACT_SHA256
    assert projection["python_executable_sha256"] == IDENTITY.EXPECTED_PYTHON_SHA256


def test_manifest_exact_build_matches_the_shipped_calculators() -> None:
    manifest = json.loads((HERE / "amendment-manifest.json").read_text("utf-8"))
    build = manifest["exact_build"]
    client = manifest["client_identity"]
    assert client["model_request_argument_sha256"] == IDENTITY.model_request_argument_sha256()
    assert build["cli"]["executable_sha256"] == IDENTITY.EXPECTED_CLI_SHA256
    assert build["runner"]["sha256"] == IDENTITY.EXPECTED_RUNNER_SHA256
    assert build["python"]["executable_sha256"] == IDENTITY.EXPECTED_PYTHON_SHA256
    assert build["external_preflight_adapter"]["sha256"] == IDENTITY.EXPECTED_PREFLIGHT_ADAPTER_SHA256
    assert build["command_contract"]["command_contract_sha256"] == IDENTITY.EXPECTED_COMMAND_CONTRACT_SHA256


def test_receipt_uses_client_side_identity_only() -> None:
    now = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    receipt = IDENTITY.build_receipt(_fields("PRE_DISPATCH", now))
    assert receipt["identity_evidence_level"] == "CLIENT_SIDE_INVOCATION_ONLY"
    assert receipt["server_executed_model_observed"] is False
    assert receipt["provider_attestation_available"] is False
    assert not IDENTITY.FORBIDDEN_PROVIDER_OBSERVATION_FIELDS.intersection(receipt)


@pytest.mark.parametrize("field", sorted(IDENTITY.FORBIDDEN_PROVIDER_OBSERVATION_FIELDS))
def test_provider_observation_illusion_fields_fail_closed(field: str) -> None:
    now = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    receipt = IDENTITY.build_receipt(_fields("PRE_DISPATCH", now))
    receipt[field] = "fabricated"
    with pytest.raises(IDENTITY.ClientIdentityError, match="provider-observation"):
        IDENTITY.validate_receipt(receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_requested_id", "other-model"),
        ("model_request_source", "config_default"),
        ("identity_evidence_level", "PROVIDER_ATTESTED"),
        ("server_executed_model_observed", True),
        ("provider_attestation_available", True),
        ("cli_executable_sha256", "b" * 64),
        ("runner_sha256", "b" * 64),
        ("command_contract_sha256", "b" * 64),
    ],
)
def test_client_identity_drift_fails_closed(field: str, value: object) -> None:
    now = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    receipt = IDENTITY.build_receipt(_fields("PRE_DISPATCH", now))
    receipt[field] = value
    with pytest.raises(IDENTITY.ClientIdentityError):
        IDENTITY.validate_receipt(receipt)


def test_receipt_pair_accepts_exact_timing_and_projection() -> None:
    admission = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    dispatch = admission + timedelta(minutes=4)
    seal = dispatch + timedelta(minutes=20)
    pre = IDENTITY.build_receipt(_fields("PRE_DISPATCH", dispatch - timedelta(minutes=2)))
    post = IDENTITY.build_receipt(_fields("POST_SEAL", seal + timedelta(minutes=2)))
    IDENTITY.validate_receipt_pair(
        pre,
        post,
        batch_projection_sha256=pre["client_runtime_projection_sha256"],
        admission_at_utc=admission,
        dispatch_at_utc=dispatch,
        outcome_sealed_at_utc=seal,
    )


@pytest.mark.parametrize("failure", ["stale_pre", "late_post", "expired", "drift"])
def test_receipt_pair_timing_and_projection_fail_closed(failure: str) -> None:
    admission = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    dispatch = admission + timedelta(minutes=10)
    seal = dispatch + timedelta(minutes=20)
    pre_time = dispatch - timedelta(minutes=1)
    post_time = seal + timedelta(minutes=1)
    if failure == "stale_pre":
        pre_time = dispatch - timedelta(minutes=6)
    elif failure == "late_post":
        post_time = seal + timedelta(minutes=6)
    elif failure == "expired":
        dispatch = admission + timedelta(hours=12, seconds=1)
        seal = dispatch + timedelta(minutes=1)
        pre_time = dispatch - timedelta(minutes=1)
        post_time = seal + timedelta(minutes=1)
    pre = IDENTITY.build_receipt(_fields("PRE_DISPATCH", pre_time))
    post = IDENTITY.build_receipt(_fields("POST_SEAL", post_time))
    projection = pre["client_runtime_projection_sha256"]
    if failure == "drift":
        projection = "b" * 64
    with pytest.raises(IDENTITY.ClientIdentityError):
        IDENTITY.validate_receipt_pair(
            pre,
            post,
            batch_projection_sha256=projection,
            admission_at_utc=admission,
            dispatch_at_utc=dispatch,
            outcome_sealed_at_utc=seal,
        )


def test_paired_execution_gap_is_bounded() -> None:
    first = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    IDENTITY.validate_paired_execution_gap(
        first_outcome_sealed_at_utc=first,
        second_dispatch_at_utc=first + timedelta(minutes=15),
    )
    with pytest.raises(IDENTITY.ClientIdentityError, match="gap"):
        IDENTITY.validate_paired_execution_gap(
            first_outcome_sealed_at_utc=first,
            second_dispatch_at_utc=first + timedelta(minutes=15, seconds=1),
        )


def test_claim_template_forces_limitations() -> None:
    template = json.loads((HERE / "conclusion-claim-template.json").read_text("utf-8"))
    IDENTITY.validate_claim_template(template)
    assert IDENTITY.REQUIRED_LIMITATION in template["required_statements"]
    assert IDENTITY.REQUIRED_APPLICABILITY in template["required_statements"]
    assert IDENTITY.REQUIRED_NON_GENERALIZATION in template["required_statements"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("server_executed_model_observed", True),
        lambda value: value.__setitem__("identity_evidence_level", "PROVIDER_ATTESTED"),
        lambda value: value.__setitem__("required_statements", []),
        lambda value: value.__setitem__("prohibited_generalizations", []),
    ],
)
def test_claim_template_weakening_fails_closed(mutation) -> None:
    template = json.loads((HERE / "conclusion-claim-template.json").read_text("utf-8"))
    mutation(template)
    with pytest.raises(IDENTITY.ClientIdentityError):
        IDENTITY.validate_claim_template(template)


def test_d1_d7_quarantine_and_d5_are_unchanged() -> None:
    manifest = json.loads((HERE / "amendment-manifest.json").read_text("utf-8"))
    original = json.loads(
        (HERE.parent / "c1-20260825" / "preregistration-manifest.json").read_text("utf-8")
    )
    preserved = manifest["preserved_decisions"]
    assert preserved["decision_rules"] == {
        "initial_pairs_per_task": 2,
        "maximum_pairs_per_task": 3,
        "fourth_pair_allowed": False,
        "minimum_natural_bug_tasks": 3,
        "minimum_consumer_repositories": 2,
        "b_task_wins_minimum": 2,
        "minimum_valid_cost_pairs": 2,
        "median_b_over_a_wall_clock_ratio_maximum": 1.2,
        "median_b_over_a_tool_call_ratio_maximum": 1.2,
    }
    assert preserved["promotion_comparison"] == "B_vs_A_only"
    assert preserved["diagnostic_comparisons"] == ["B_vs_C", "C_vs_D"]
    for key, value in preserved["decision_rules"].items():
        assert original["decision_rules"][key] == value
    assert preserved["qualifying_success_fields"] == original["decision_rules"]["qualifying_success_fields"]
    assert preserved["third_pair_trigger"] == original["decision_rules"]["third_pair_trigger"]
    assert preserved["program_terminals"] == original["decision_rules"]["program_terminals"]
    assert preserved["promotion_comparison"] == original["treatments"]["promotion_comparison"]
    assert preserved["diagnostic_comparisons"] == original["treatments"]["diagnostic_comparisons"]
    assert preserved["attempt06_quarantine"] == original["attempt06_quarantine"]
    assert preserved["d5_countability"] == "UNRESOLVED_SEPARATE_COUNTABILITY_DECISION"
