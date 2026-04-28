import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.failure_test_validator import (
    classify_test_names,
    validate_failure_test_coverage,
)


FIXTURE_ROOT = Path("tests/_tmp_failure_test_validator")


def _reset_fixture(name: str) -> Path:
    path = FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_classify_test_names_detects_required_categories():
    matched = classify_test_names(
        [
            "test_invalid_input_returns_error",
            "test_boundary_max_size",
            "test_dependency_failure_timeout",
            "test_rollback_cleans_up_temp_file",
        ]
    )

    assert matched["invalid_input"]
    assert matched["boundary"]
    assert matched["failure_path"]
    assert matched["rollback_cleanup"]


def test_validate_failure_test_coverage_passes_with_required_signals():
    result = validate_failure_test_coverage(
        [
            "test_invalid_payload_rejected",
            "test_boundary_min_value",
            "test_network_failure_returns_retryable_error",
            "test_cleanup_after_rollback",
        ],
        require_rollback=True,
    )

    assert result["ok"] is True
    assert result["errors"] == []


def test_validate_failure_test_coverage_reports_missing_categories():
    result = validate_failure_test_coverage(
        [
            "test_happy_path",
            "test_successful_save",
        ],
        require_rollback=True,
    )

    assert result["ok"] is False
    assert any("invalid_input" in error for error in result["errors"])
    assert any("boundary" in error for error in result["errors"])
    assert any("failure_path" in error for error in result["errors"])
    assert any("rollback_cleanup" in error for error in result["errors"])
    assert any("Rollback / cleanup coverage" in warning for warning in result["warnings"])


def test_failure_test_validator_cli_shape():
    fixture = _reset_fixture("cli_shape")
    payload = fixture / "test_names.json"
    payload.write_text(
        json.dumps(
            {
                "tests": [
                    "test_invalid_request",
                    "test_boundary_limit",
                    "test_dependency_failure",
                ]
            }
        ),
        encoding="utf-8",
    )

    result = validate_failure_test_coverage(
        json.loads(payload.read_text(encoding="utf-8"))["tests"],
        require_rollback=False,
    )

    assert result["ok"] is True
