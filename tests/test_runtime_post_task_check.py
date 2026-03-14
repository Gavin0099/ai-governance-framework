import sys
from pathlib import Path
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.post_task_check import format_human_result, run_post_task_check


def _contract(**overrides) -> str:
    fields = {
        "LANG": "C++",
        "LEVEL": "L2",
        "SCOPE": "feature",
        "PLAN": "PLAN.md",
        "LOADED": "SYSTEM_PROMPT, HUMAN-OVERSIGHT",
        "CONTEXT": "repo -> runtime-governance; NOT: platform rewrite",
        "PRESSURE": "SAFE (20/200)",
        "RULES": "common,python",
        "RISK": "medium",
        "OVERSIGHT": "review-required",
        "MEMORY_MODE": "candidate",
    }
    fields.update(overrides)
    body = "\n".join(f"{k} = {v}" for k, v in fields.items())
    return f"[Governance Contract]\n{body}\n"


@pytest.fixture
def local_memory_root():
    path = Path("tests") / "_tmp_post_task_memory"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_post_task_check_passes_for_compliant_output():
    result = run_post_task_check(_contract(), risk="medium", oversight="review-required")
    assert result["ok"] is True


def test_post_task_check_fails_without_contract():
    result = run_post_task_check("no contract here", risk="medium", oversight="review-required")
    assert result["ok"] is False
    assert any("Missing governance contract" in error for error in result["errors"])


def test_post_task_check_fails_high_risk_auto_oversight():
    result = run_post_task_check(_contract(OVERSIGHT="auto"), risk="high", oversight="auto")
    assert result["ok"] is False
    assert any("High-risk" in error for error in result["errors"])


def test_post_task_check_can_create_candidate_snapshot(local_memory_root):
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        memory_root=local_memory_root,
        snapshot_task="Runtime governance",
        snapshot_summary="Snapshot from post-task check",
        create_snapshot=True,
    )
    assert result["ok"] is True
    assert result["snapshot"] is not None
    assert Path(result["snapshot"]["snapshot_path"]).exists()


def test_post_task_check_blocks_durable_memory_without_oversight():
    result = run_post_task_check(
        _contract(MEMORY_MODE="durable", OVERSIGHT="auto"),
        risk="medium",
        oversight="auto",
    )
    assert result["ok"] is False
    assert any("Durable memory" in error for error in result["errors"])


def test_post_task_check_merges_runtime_check_errors():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "warnings": ["Rollback / cleanup coverage was not detected."],
            "errors": ["Missing required failure-test coverage: failure_path"],
        },
    )
    assert result["ok"] is False
    assert any("runtime-check: Missing required failure-test coverage: failure_path" in error for error in result["errors"])
    assert any("runtime-check: Rollback / cleanup coverage was not detected." in warning for warning in result["warnings"])


def test_post_task_check_applies_refactor_evidence_requirements():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_happy_path",
                "tests/test_service.py::test_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["refactor_evidence"] is not None
    assert any("refactor-evidence: Missing refactor evidence: regression-oriented test signal" in error for error in result["errors"])
    assert any("refactor-evidence: Missing refactor evidence: interface stability signal" in error for error in result["errors"])


def test_post_task_check_applies_failure_completeness_checks():
    result = run_post_task_check(
        _contract(),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": ["tests/test_service.py::test_happy_path"],
            "warnings": [],
            "errors": [],
        },
    )
    assert result["ok"] is False
    assert result["failure_completeness"] is not None
    assert any("failure-completeness: Missing failure completeness evidence: failure-path signal" in error for error in result["errors"])


def test_post_task_check_can_use_public_api_diff_for_refactor_interface_stability():
    root = Path("tests") / "_tmp_public_api_runtime"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        before_file = root / "before.cs"
        after_file = root / "after.cs"
        before_file.write_text(
            "public class Service\n{\n    public int Run(int value) => value;\n}\n",
            encoding="utf-8",
        )
        after_file.write_text(
            "public class Service\n{\n    public int Run(int value) => value;\n    public int Ping() => 0;\n}\n",
            encoding="utf-8",
        )

        result = run_post_task_check(
            _contract(RULES="common,refactor"),
            risk="medium",
            oversight="review-required",
            checks={
                "test_names": [
                    "tests/test_service.py::test_regression_contract",
                    "tests/test_service.py::test_cleanup_release",
                ],
                "warnings": [],
                "errors": [],
            },
            api_before_files=[before_file],
            api_after_files=[after_file],
        )

        assert result["public_api_diff"] is not None
        assert result["public_api_diff"]["ok"] is True
        assert result["refactor_evidence"]["signals_detected"]["interface_stability_evidence"] is True
        assert all("interface stability signal" not in error for error in result["errors"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_task_check_blocks_removed_public_api_for_refactor():
    root = Path("tests") / "_tmp_public_api_runtime_removed"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        before_file = root / "before.cs"
        after_file = root / "after.cs"
        before_file.write_text("public class Service { public int Run(int value) => value; }", encoding="utf-8")
        after_file.write_text("public class Service { internal int Run(int value) => value; }", encoding="utf-8")

        result = run_post_task_check(
            _contract(RULES="common,refactor"),
            risk="medium",
            oversight="review-required",
            checks={
                "test_names": [
                    "tests/test_service.py::test_regression_contract",
                    "tests/test_service.py::test_cleanup_release",
                ],
                "warnings": [],
                "errors": [],
            },
            api_before_files=[before_file],
            api_after_files=[after_file],
        )

        assert result["ok"] is False
        assert any("public-api-diff: Public API surface removed or changed." in error for error in result["errors"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_post_task_check_applies_kernel_driver_evidence_requirements():
    result = run_post_task_check(
        _contract(RULES="common,cpp,kernel-driver", RISK="high", OVERSIGHT="human-approval"),
        risk="high",
        oversight="human-approval",
        checks={
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_cleanup_unwind_on_partial_init_failure",
            ],
            "diagnostics": ["WDK compile output only"],
            "summary": {"failed": 0},
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is False
    assert result["driver_evidence"] is not None
    assert any("driver-evidence: Missing kernel-driver evidence: static analysis result" in error for error in result["errors"])
    assert any("driver-evidence: Missing kernel-driver evidence: IRQL / pageable-context verification" in error for error in result["errors"])


def test_post_task_check_passes_kernel_driver_evidence_with_sdv_signal():
    result = run_post_task_check(
        _contract(RULES="common,cpp,kernel-driver", RISK="high", OVERSIGHT="human-approval"),
        risk="high",
        oversight="human-approval",
        checks={
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_cleanup_unwind_on_partial_init_failure",
                "driver_tests::test_irql_passive_level_contract",
            ],
            "diagnostics": [
                "Static Driver Verifier: ruleset passed",
                "SAL analysis confirms pageable path is passive_level only",
            ],
            "summary": {"failed": 0},
            "warnings": [],
            "errors": [],
        },
    )

    assert result["ok"] is True
    assert result["driver_evidence"] is not None
    assert result["driver_evidence"]["ok"] is True


def test_post_task_check_human_output_includes_evidence_summary():
    result = run_post_task_check(
        _contract(RULES="common,refactor"),
        risk="medium",
        oversight="review-required",
        checks={
            "test_names": [
                "tests/test_service.py::test_regression_contract",
                "tests/test_service.py::test_cleanup_release",
            ],
            "public_api_diff": {
                "ok": True,
                "removed": [],
                "added": ["public int Ping() => 0;"],
                "warnings": ["Public API surface added or changed."],
                "errors": [],
            },
            "warnings": [],
            "errors": [],
        },
    )

    output = format_human_result(result)
    assert "[post_task_check]" in output
    assert "summary=ok=False | compliant=True | memory_mode=candidate" in output
    assert "public_api_added=1" in output
    assert "public_api_ok=True" in output
    assert "failure_completeness_ok=" in output
    assert "refactor_evidence_ok=" in output


def test_post_task_check_can_validate_external_rule_pack_from_contract(tmp_path):
    contract_root = tmp_path / "usb_hub_contract"
    (contract_root / "rules" / "firmware").mkdir(parents=True)
    (contract_root / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    contract_file = contract_root / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,firmware"),
        risk="medium",
        oversight="review-required",
        contract_file=contract_file,
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["rule_packs"]["valid"] is True


def test_post_task_check_can_auto_discover_domain_contract_from_project_root(tmp_path):
    (tmp_path / "rules" / "firmware").mkdir(parents=True)
    (tmp_path / "rules" / "firmware" / "safety.md").write_text("# Firmware rule\nValidate rollback.\n", encoding="utf-8")
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "rule_roots:\n"
        "  - rules\n",
        encoding="utf-8",
    )

    result = run_post_task_check(
        _contract(RULES="common,firmware"),
        risk="medium",
        oversight="review-required",
        project_root=tmp_path,
    )

    assert result["ok"] is True
    assert result["domain_contract"]["name"] == "usb-hub-firmware"
    assert result["contract_resolution"]["source"] == "discovery"
    assert result["resolved_contract_file"] == str(contract_file.resolve())
    output = format_human_result(result)
    assert "contract=firmware/medium" in output or "contract=usb-hub-firmware/medium" in output
