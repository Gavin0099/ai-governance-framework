import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.refactor_evidence_validator import validate_refactor_evidence


def test_refactor_evidence_validator_passes_with_expected_signals():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_behavior_lock",
                "tests/test_service.py::test_public_api_contract_stable",
                "tests/test_service.py::test_rollback_cleanup_on_failure",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "raises TimeoutError",
                    "status": "unchanged",
                    "reviewer_note": "",
                }
            ],
            "failure_test_validation": {
                "coverage": {
                    "rollback_cleanup": {"count": 1, "matches": ["test_rollback_cleanup_on_failure"]}
                }
            },
        }
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["signals_detected"]["error_path_inventory_evidence"] is True
    assert result["signals_detected"]["error_behavior_diff_evidence"] is True


def test_refactor_evidence_validator_blocks_missing_regression_and_interface_signals():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_happy_path",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": False,
                }
            ],
        }
    )

    assert result["ok"] is False
    assert any("regression-oriented" in error for error in result["errors"])
    assert any("interface stability" in error for error in result["errors"])
    assert result["signals_detected"]["cleanup_evidence"] is True


def test_refactor_evidence_validator_warns_when_cleanup_evidence_missing():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": False,
                }
            ],
        }
    )

    assert result["ok"] is True
    assert any("cleanup / rollback evidence" in warning for warning in result["warnings"])


def test_error_path_inventory_missing_hard_stop():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
            ]
        }
    )

    assert result["ok"] is False
    assert any("error_path_inventory missing" in error for error in result["errors"])


def test_error_path_inventory_missing_fields():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "affected_by_refactor": True,
                }
            ],
        }
    )

    assert result["ok"] is False
    assert any("missing fields" in error for error in result["errors"])


def test_error_behavior_diff_missing_for_affected_case():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
        }
    )

    assert result["ok"] is False
    assert any("error_behavior_diff missing entries" in error for error in result["errors"])


def test_error_behavior_diff_changed_without_reviewer_note():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                }
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "returns fallback result",
                    "status": "changed",
                    "reviewer_note": "",
                }
            ],
        }
    )

    assert result["ok"] is False
    assert any("reviewer_note is empty" in error for error in result["errors"])


def test_error_path_full_compliant():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_regression_characterization",
                "tests/test_service.py::test_interface_contract_stable",
                "tests/test_service.py::test_cleanup_release",
            ],
            "error_path_inventory": [
                {
                    "error_id": "ERR-001",
                    "trigger": "Database timeout",
                    "pre_refactor_behavior": "raises TimeoutError",
                    "affected_by_refactor": True,
                },
                {
                    "error_id": "ERR-002",
                    "trigger": "Permission denied",
                    "pre_refactor_behavior": "returns 403",
                    "affected_by_refactor": False,
                },
            ],
            "error_behavior_diff": [
                {
                    "error_id": "ERR-001",
                    "pre_behavior": "raises TimeoutError",
                    "post_behavior": "raises TimeoutError",
                    "status": "unchanged",
                    "reviewer_note": "",
                }
            ],
        }
    )

    assert result["ok"] is True
    assert result["errors"] == []
