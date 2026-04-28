import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.driver_evidence_validator import validate_driver_evidence


def test_driver_evidence_validator_passes_with_sdv_and_ioctl_evidence():
    result = validate_driver_evidence(
        {
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_cleanup_unwind_on_partial_init_failure",
                "driver_tests::test_irql_passive_level_contract",
            ],
            "diagnostics": [
                "Static Driver Verifier: no defects found for current ruleset",
                "SAL analysis: pageable code not reachable from dispatch_level path",
            ],
            "summary": {"failed": 0},
        }
    )

    assert result["ok"] is True
    assert result["errors"] == []


def test_driver_evidence_validator_requires_static_analysis_and_irql_evidence():
    result = validate_driver_evidence(
        {
            "test_names": ["driver_tests::test_ioctl_invalid_input_rejected"],
            "summary": {"failed": 0},
        }
    )

    assert result["ok"] is False
    assert any("static analysis result" in error for error in result["errors"])
    assert any("IRQL / pageable-context verification" in error for error in result["errors"])


def test_driver_evidence_validator_reports_failing_results():
    result = validate_driver_evidence(
        {
            "test_names": [
                "driver_tests::test_ioctl_invalid_input_rejected",
                "driver_tests::test_irql_dispatch_level_guard",
            ],
            "diagnostics": ["SDV report generated"],
            "summary": {"failed": 1},
        }
    )

    assert result["ok"] is False
    assert any("failing test or analysis results" in error for error in result["errors"])
