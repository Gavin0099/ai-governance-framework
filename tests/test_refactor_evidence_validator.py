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
            "failure_test_validation": {
                "coverage": {
                    "rollback_cleanup": {"count": 1, "matches": ["test_rollback_cleanup_on_failure"]}
                }
            },
        }
    )

    assert result["ok"] is True
    assert result["errors"] == []


def test_refactor_evidence_validator_blocks_missing_regression_and_interface_signals():
    result = validate_refactor_evidence(
        {
            "test_names": [
                "tests/test_service.py::test_happy_path",
                "tests/test_service.py::test_cleanup_release",
            ]
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
            ]
        }
    )

    assert result["ok"] is True
    assert any("cleanup / rollback evidence" in warning for warning in result["warnings"])
