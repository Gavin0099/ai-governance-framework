import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.expansion_boundary_checker import (
    ExpansionBoundaryResult,
    Violation,
    _TRANSITIONAL_SESSION_START_KEYS,
    run_checks,
)


FRAMEWORK_ROOT = Path(__file__).parent.parent


def test_expansion_boundary_checker_accepts_current_pre_task_decision_boundary_surface():
    result = run_checks(FRAMEWORK_ROOT)
    violations = result.violations

    unexpected = [
        violation
        for violation in violations
        if violation.kind == "new_return_key"
        and Path(violation.file).name == "pre_task_check.py"
    ]

    assert unexpected == []


def test_session_envelope_is_admitted_as_transitional_lifecycle_metadata():
    admission = _TRANSITIONAL_SESSION_START_KEYS["session_envelope"]

    assert admission == {
        "status": "transitional",
        "expected": "core",
        "admitted_date": "2026-07-29",
        "source_commit": "a0683a5c",
    }

    result = run_checks(FRAMEWORK_ROOT)
    unexpected = [
        violation
        for violation in result.violations
        if violation.kind == "new_return_key"
        and Path(violation.file).name == "session_start.py"
    ]
    assert unexpected == []


def test_expansion_boundary_checker_run_checks_contract_shape():
    result = run_checks(FRAMEWORK_ROOT)

    assert isinstance(result, ExpansionBoundaryResult)
    assert isinstance(result.ok, bool)
    assert isinstance(result.violations, list)
    assert isinstance(result.warnings, list)
    assert isinstance(result.checked_files, list)
    assert all(isinstance(v, Violation) for v in result.violations)
