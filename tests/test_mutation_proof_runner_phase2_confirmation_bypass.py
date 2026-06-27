from pathlib import Path

from governance_tools.mutation_proof_runner_phase2 import (
    MutationProofRunnerPhase2,
    SCENARIOS,
    _test_confirmation_bypass,
)


EXPECTED_VIOLATION = "resolved_confirmed_requires_reviewer_confirmation"


def _confirmation_bypass_scenario():
    matches = [scenario for scenario in SCENARIOS if scenario.id == "confirmation_bypass"]
    assert len(matches) == 1
    return matches[0]


def test_confirmation_bypass_scenario_targets_lifecycle_transition_contract():
    scenario = _confirmation_bypass_scenario()

    assert scenario.mutation.target_file == "governance_tools/lifecycle_transition_writer.py"
    assert scenario.expected_violation == EXPECTED_VIOLATION
    assert scenario.violation_field == "errors"
    assert scenario.test_fn is _test_confirmation_bypass
    assert "lifecycle_transition_writer" in scenario.description


def test_confirmation_bypass_mutation_anchor_matches_current_source():
    scenario = _confirmation_bypass_scenario()
    source = Path("governance_tools/lifecycle_transition_writer.py").read_text(
        encoding="utf-8"
    )

    assert scenario.mutation.old_str in source
    assert source.count(scenario.mutation.old_str) == 1
    assert EXPECTED_VIOLATION in scenario.mutation.old_str


def test_confirmation_bypass_secondary_detection_sits_outside_mutation_anchor():
    scenario = _confirmation_bypass_scenario()
    source = Path("governance_tools/lifecycle_transition_writer.py").read_text(
        encoding="utf-8"
    )
    secondary_call = "_append_reviewer_confirmation_required_once(errors)"
    mutated_source = source.replace(
        scenario.mutation.old_str,
        scenario.mutation.new_str,
        1,
    )

    assert secondary_call in source
    assert secondary_call not in scenario.mutation.old_str
    assert scenario.mutation.old_str not in mutated_source
    assert secondary_call in mutated_source


def test_confirmation_bypass_fixture_triggers_exact_unmutated_error(tmp_path):
    raw_result = _test_confirmation_bypass(Path.cwd(), tmp_path)

    assert raw_result["ok"] is False
    assert raw_result["exit_code"] == 0
    assert raw_result["errors"] == [EXPECTED_VIOLATION]


def test_confirmation_bypass_survival_check_requires_exact_error_absence():
    runner = MutationProofRunnerPhase2(Path.cwd())

    assert (
        runner._check_mutation_survived(
            {"errors": [EXPECTED_VIOLATION]},
            EXPECTED_VIOLATION,
            "errors",
        )
        is False
    )
    assert (
        runner._check_mutation_survived(
            {"errors": []},
            EXPECTED_VIOLATION,
            "errors",
        )
        is True
    )
