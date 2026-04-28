import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.failure_completeness_validator import validate_failure_completeness


def test_failure_completeness_validator_passes_with_richer_metadata():
    result = validate_failure_completeness(
        {
            "test_names": [
                "tests/test_service.py::test_exception_path_returns_domain_error",
                "tests/test_service.py::test_rollback_cleanup_on_failure",
            ],
            "exception_assertions": ["raises DomainError"],
            "rollback_verified": True,
            "failure_test_validation": {
                "coverage": {
                    "failure_path": {"count": 1, "matches": ["test_exception_path_returns_domain_error"]},
                    "rollback_cleanup": {"count": 1, "matches": ["test_rollback_cleanup_on_failure"]},
                }
            },
        },
        require_cleanup=True,
    )

    assert result["ok"] is True
    assert result["errors"] == []


def test_failure_completeness_validator_errors_when_failure_signal_missing():
    result = validate_failure_completeness(
        {
            "test_names": ["tests/test_service.py::test_happy_path"],
        }
    )

    assert result["ok"] is False
    assert any("failure-path signal" in error for error in result["errors"])


def test_failure_completeness_validator_requires_cleanup_for_refactor_like_checks():
    result = validate_failure_completeness(
        {
            "test_names": ["tests/test_service.py::test_exception_path_returns_error"],
            "exception_verified": True,
            "failure_test_validation": {
                "coverage": {
                    "failure_path": {"count": 1, "matches": ["test_exception_path_returns_error"]},
                    "rollback_cleanup": {"count": 0, "matches": []},
                }
            },
        },
        require_cleanup=True,
    )

    assert result["ok"] is False
    assert any("rollback/cleanup verification" in error for error in result["errors"])
