from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "c1_gate1_preregistration", ROOT / "gate1_preregistration.py"
)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


PairOutcome = module.PairOutcome
PreregistrationError = module.PreregistrationError
ProgramTerminal = module.ProgramTerminal


def test_manifest_binds_every_non_manifest_file_exactly() -> None:
    manifest = json.loads((ROOT / "preregistration-manifest.json").read_text("utf-8"))
    declared = {entry["path"]: entry for entry in manifest["frozen_files"]}
    actual = {
        path.name
        for path in ROOT.iterdir()
        if path.is_file() and path.name != "preregistration-manifest.json"
    }
    assert set(declared) == actual
    for name, entry in declared.items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == entry["bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_manifest_projects_treatment_order_rubric_and_quarantine() -> None:
    manifest = json.loads((ROOT / "preregistration-manifest.json").read_text("utf-8"))
    randomization = json.loads(
        (ROOT / "randomization-evidence-policy.json").read_text("utf-8")
    )
    rubric = json.loads((ROOT / "scorer-rubric.json").read_text("utf-8"))
    module.validate_treatment_lattice(manifest["treatments"]["arms"])
    module.validate_event_order(randomization["event_order"])
    module.validate_attempt06_quarantine(manifest["attempt06_quarantine"])
    assert tuple(rubric["qualifying_success_requires"]) == module.QUALIFYING_FIELDS
    assert manifest["decision_rules"]["program_terminals"] == [
        terminal.value for terminal in ProgramTerminal
    ]


def qualifying(**overrides: bool) -> dict[str, bool]:
    value = {field: True for field in module.QUALIFYING_FIELDS}
    value.update(overrides)
    return value


def test_qualifying_success_requires_every_frozen_boolean() -> None:
    assert module.qualifying_success(qualifying()) is True
    assert module.qualifying_success(qualifying(original_defect_caught=False)) is False


def test_qualifying_success_missing_or_non_boolean_fails_closed() -> None:
    missing = qualifying()
    missing.pop("oracle_acceptance")
    with pytest.raises(PreregistrationError, match="missing qualifying fields"):
        module.qualifying_success(missing)
    invalid = qualifying()
    invalid["oracle_acceptance"] = 1  # type: ignore[assignment]
    with pytest.raises(PreregistrationError, match="must be booleans"):
        module.qualifying_success(invalid)


def test_third_pair_trigger_is_tie_or_any_non_completion() -> None:
    b_wins = [
        PairOutcome(False, True, True, True),
        PairOutcome(False, True, True, True),
    ]
    tied = [
        PairOutcome(False, True, True, True),
        PairOutcome(True, False, True, True),
    ]
    incomplete = [
        PairOutcome(False, True, True, True),
        PairOutcome(False, True, False, True),
    ]
    assert module.third_pair_required(b_wins) is False
    assert module.third_pair_required(tied) is True
    assert module.third_pair_required(incomplete) is True


def test_task_decision_refuses_missing_or_untriggered_third_pair() -> None:
    tied = [
        PairOutcome(False, True, True, True),
        PairOutcome(True, False, True, True),
    ]
    with pytest.raises(PreregistrationError, match="third pair is required"):
        module.decide_task(tied)
    decided = module.decide_task(tied + [PairOutcome(False, True, True, True)])
    assert decided.winner == "B"
    assert decided.pairs_used == 3

    b_wins = [
        PairOutcome(False, True, True, True),
        PairOutcome(False, True, True, True),
    ]
    with pytest.raises(PreregistrationError, match="third pair is forbidden"):
        module.decide_task(b_wins + [PairOutcome(True, False, True, True)])


def test_cost_median_uses_paired_ratios_and_even_arithmetic_median() -> None:
    assert module.paired_ratios([10, 20], [12, 20]) == (1.2, 1.0)
    assert module.median_paired_ratio([10, 20], [12, 20]) == pytest.approx(1.1)


@pytest.mark.parametrize(
    ("a_values", "b_values"),
    [([], []), ([0], [1]), ([1], [0]), ([True], [1]), ([1, 2], [1])],
)
def test_cost_invalid_or_unpaired_values_fail_closed(a_values, b_values) -> None:
    with pytest.raises(PreregistrationError):
        module.median_paired_ratio(a_values, b_values)


def test_event_order_accepts_only_the_frozen_sequence() -> None:
    module.validate_event_order(module.EVENT_ORDER)
    swapped = list(module.EVENT_ORDER)
    swapped[-2], swapped[-1] = swapped[-1], swapped[-2]
    with pytest.raises(PreregistrationError, match="event order"):
        module.validate_event_order(swapped)

    missing_external_pin = tuple(
        event for event in module.EVENT_ORDER if event != "external_chain_head_pinned"
    )
    with pytest.raises(PreregistrationError, match="event order"):
        module.validate_event_order(missing_external_pin)


def test_mapping_commitment_has_independent_frozen_vector() -> None:
    mapping = {"OUT-1": "A", "OUT-2": "B"}
    nonce = "0123456789abcdef" * 4
    assert module.mapping_commitment(mapping, nonce) == (
        "7052e01163f006a9500fc50b323a861f49601a8948d451f312f47860c9531adb"
    )
    with pytest.raises(PreregistrationError, match="64 hex"):
        module.mapping_commitment(mapping, "00")


def test_feedback_visibility_is_d_only_and_exactly_once() -> None:
    for arm in ("A", "B", "C"):
        module.validate_feedback_visibility(arm, 0)
        with pytest.raises(PreregistrationError, match="must not receive"):
            module.validate_feedback_visibility(arm, 1)
    module.validate_feedback_visibility("D", 1)
    with pytest.raises(PreregistrationError, match="exactly one"):
        module.validate_feedback_visibility("D", 2)


def test_retained_feedback_allows_aggregates_and_rejects_detail_recursively() -> None:
    module.validate_retained_feedback(
        {
            "mutant_count": 3,
            "status_counts": {"Killed": 2, "Survived": 1},
            "cleanup_confirmed": True,
            "raw_output_retained": False,
            "bulk_path_listing_retained": False,
        }
    )
    with pytest.raises(PreregistrationError, match="forbidden fields"):
        module.validate_retained_feedback(
            {
                "operator_counts": {"mutants": [{"location": "not-retainable"}]},
                "cleanup_confirmed": True,
                "raw_output_retained": False,
                "bulk_path_listing_retained": False,
            }
        )


def test_retained_feedback_fails_closed_on_cleanup_or_unknown_field() -> None:
    base = {
        "mutant_count": 3,
        "cleanup_confirmed": True,
        "raw_output_retained": False,
        "bulk_path_listing_retained": False,
    }
    with pytest.raises(PreregistrationError, match="cleanup must be confirmed"):
        module.validate_retained_feedback({**base, "cleanup_confirmed": False})
    with pytest.raises(PreregistrationError, match="unapproved fields"):
        module.validate_retained_feedback({**base, "consumer_path": "private"})


def test_attempt06_quarantine_requires_every_forbidden_use() -> None:
    manifest = json.loads((ROOT / "preregistration-manifest.json").read_text("utf-8"))
    module.validate_attempt06_quarantine(manifest["attempt06_quarantine"])
    mutated = dict(manifest["attempt06_quarantine"])
    mutated["forbidden_uses"] = ["producer_input"]
    with pytest.raises(PreregistrationError, match="quarantine is incomplete"):
        module.validate_attempt06_quarantine(mutated)


def test_program_terminals_are_positive_negative_insufficient_invalid() -> None:
    common = dict(
        complete_sample=True,
        diversity_met=True,
        core_cost_pairs=2,
        b_task_wins=2,
        b_completion_not_lower=True,
        b_unique_critical_failures=0,
        product_success_difference_wins=1,
        wall_clock_ratio_median=1.2,
        tool_call_ratio_median=1.2,
    )
    assert module.decide_program_terminal(valid=False, **common) is ProgramTerminal.INVALID
    assert module.decide_program_terminal(valid=True, **common) is ProgramTerminal.POSITIVE
    assert (
        module.decide_program_terminal(valid=True, **{**common, "b_task_wins": 1})
        is ProgramTerminal.NEGATIVE
    )
    assert (
        module.decide_program_terminal(valid=True, **{**common, "core_cost_pairs": 1})
        is ProgramTerminal.INSUFFICIENT
    )


def test_treatment_lattice_preserves_only_the_declared_additions() -> None:
    common = {"common_task", "baseline", "permissions", "budget", "harness", "model"}
    valid = {
        "A": common,
        "B": common | {"skill"},
        "C": common | {"skill", "governance"},
        "D": common | {"skill", "governance", "validator_feedback"},
    }
    module.validate_treatment_lattice(valid)
    contaminated = {arm: set(inputs) for arm, inputs in valid.items()}
    contaminated["A"].add("skill")
    with pytest.raises(PreregistrationError, match="treatment lattice"):
        module.validate_treatment_lattice(contaminated)
