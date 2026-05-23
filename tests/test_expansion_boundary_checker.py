import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.expansion_boundary_checker import ExpansionBoundaryResult, Violation, run_checks


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


def test_expansion_boundary_checker_run_checks_contract_shape():
    result = run_checks(FRAMEWORK_ROOT)

    assert isinstance(result, ExpansionBoundaryResult)
    assert isinstance(result.ok, bool)
    assert isinstance(result.violations, list)
    assert isinstance(result.warnings, list)
    assert isinstance(result.checked_files, list)
    assert all(isinstance(v, Violation) for v in result.violations)
