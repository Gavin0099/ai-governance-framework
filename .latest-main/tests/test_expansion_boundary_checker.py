import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.expansion_boundary_checker import run_checks


FRAMEWORK_ROOT = Path(__file__).parent.parent


def test_expansion_boundary_checker_accepts_current_pre_task_decision_boundary_surface():
    violations = run_checks(FRAMEWORK_ROOT)

    unexpected = [
        violation
        for violation in violations
        if violation.kind == "new_return_key"
        and Path(violation.file).name == "pre_task_check.py"
    ]

    assert unexpected == []
