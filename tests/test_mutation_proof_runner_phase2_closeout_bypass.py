from pathlib import Path

from governance_tools.mutation_proof_runner_phase2 import (
    MutationProofRunnerPhase2,
    SCENARIOS,
    _test_closeout_bypass,
)


EXPECTED_VIOLATION = "phase_d_completed_without_reviewer_closeout_artifact"


def _closeout_bypass_scenario():
    matches = [scenario for scenario in SCENARIOS if scenario.id == "closeout_bypass"]
    assert len(matches) == 1
    return matches[0]


def test_closeout_bypass_scenario_targets_state_reconciliation_contract():
    scenario = _closeout_bypass_scenario()

    assert scenario.mutation.target_file == "governance_tools/state_reconciliation_validator.py"
    assert scenario.expected_violation == EXPECTED_VIOLATION
    assert scenario.violation_field == "violations"
    assert scenario.test_fn is _test_closeout_bypass
    assert "state_reconciliation_validator" in scenario.description


def test_closeout_bypass_mutation_anchor_matches_current_validator_source():
    scenario = _closeout_bypass_scenario()
    validator_source = Path("governance_tools/state_reconciliation_validator.py").read_text(
        encoding="utf-8"
    )

    assert scenario.mutation.old_str in validator_source
    assert validator_source.count(scenario.mutation.old_str) == 1
    assert EXPECTED_VIOLATION in scenario.mutation.old_str


def test_closeout_bypass_fixture_triggers_exact_unmutated_violation(tmp_path):
    raw_result = _test_closeout_bypass(Path.cwd(), tmp_path)

    assert raw_result["ok"] is False
    assert raw_result["exit_code"] == 1
    assert raw_result["violations"] == [EXPECTED_VIOLATION]


def test_closeout_bypass_survival_check_requires_exact_violation_absence():
    runner = MutationProofRunnerPhase2(Path.cwd())

    assert (
        runner._check_mutation_survived(
            {"violations": [EXPECTED_VIOLATION]},
            EXPECTED_VIOLATION,
            "violations",
        )
        is False
    )
    assert (
        runner._check_mutation_survived(
            {"violations": []},
            EXPECTED_VIOLATION,
            "violations",
        )
        is True
    )
