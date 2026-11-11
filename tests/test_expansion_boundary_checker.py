import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.expansion_boundary_checker import (
    ExpansionBoundaryResult,
    Violation,
    _CORE_POST_TASK_KEYS,
    _CORE_SESSION_START_KEYS,
    _TRANSITIONAL_POST_TASK_KEYS,
    _TRANSITIONAL_SESSION_START_KEYS,
    _check_new_return_keys,
    run_checks,
)


FRAMEWORK_ROOT = Path(__file__).parent.parent
VISIBILITY_OUTPUT_KEYS = {
    "by_consumer",
    "by_field",
    "by_type",
    "contract_version",
    "high_frequency_misuse_triggers_enforcement",
    "notice",
    "total_violations",
    "visibility_only",
}


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


def test_session_envelope_is_core_lifecycle_metadata():
    assert "session_envelope" in _CORE_SESSION_START_KEYS
    assert "session_envelope" not in _TRANSITIONAL_SESSION_START_KEYS

    result = run_checks(FRAMEWORK_ROOT)
    assert [v for v in result.violations if v.kind == "transitional_key_stale"] == []
    unexpected = [
        violation
        for violation in result.violations
        if violation.kind == "new_return_key"
        and Path(violation.file).name == "session_start.py"
    ]
    assert unexpected == []


def test_session_start_still_rejects_an_unadmitted_return_key():
    source = (
        "def run():\n"
        "    return {'ok': True, 'session_envelope': {}, 'unadmitted_new_key': 1}\n"
    )

    violations = _check_new_return_keys(Path("session_start.py"), source)

    assert [v.kind for v in violations] == ["new_return_key"]
    assert "unadmitted_new_key" in violations[0].detail
    assert "session_envelope" not in violations[0].detail


def test_stable_visibility_output_keys_are_core_not_transitional():
    assert VISIBILITY_OUTPUT_KEYS <= _CORE_POST_TASK_KEYS
    assert VISIBILITY_OUTPUT_KEYS.isdisjoint(_TRANSITIONAL_POST_TASK_KEYS)


def test_expansion_boundary_checker_run_checks_contract_shape():
    result = run_checks(FRAMEWORK_ROOT)

    assert isinstance(result, ExpansionBoundaryResult)
    assert isinstance(result.ok, bool)
    assert isinstance(result.violations, list)
    assert isinstance(result.warnings, list)
    assert isinstance(result.checked_files, list)
    assert all(isinstance(v, Violation) for v in result.violations)
