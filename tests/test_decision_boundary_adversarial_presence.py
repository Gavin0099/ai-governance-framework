from pathlib import Path

from governance_tools.domain_contract_loader import load_domain_contract
from runtime_hooks.core.pre_task_check import run_pre_task_check


ADVERSARIAL_EXAMPLE_CONTRACT = Path(
    "examples/decision-boundary/adversarial-formal-presence/contract.yaml"
)


def test_adversarial_formal_presence_contract_loads():
    loaded = load_domain_contract(ADVERSARIAL_EXAMPLE_CONTRACT)

    assert loaded is not None
    assert loaded["name"] == "decision-boundary-adversarial-formal-presence"
    assert loaded["raw"]["preconditions_missing_spec"] == ["protocol_implementation"]
    assert loaded["raw"]["preconditions_missing_sample"] == ["pdf_parser"]


def test_adversarial_formal_presence_still_passes_current_gate():
    spec_result = run_pre_task_check(
        project_root=Path(".").resolve(),
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement protocol handling for firmware packets using draft-spec.md",
        contract_file=ADVERSARIAL_EXAMPLE_CONTRACT,
        task_level="L1",
    )
    sample_result = run_pre_task_check(
        project_root=Path(".").resolve(),
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Implement a PDF parser using sample file happy-path-only.pdf",
        contract_file=ADVERSARIAL_EXAMPLE_CONTRACT,
        task_level="L1",
    )

    spec_check = next(
        check for check in spec_result["decision_boundary"]["preconditions_checked"]
        if check["type"] == "missing_spec"
    )
    sample_check = next(
        check for check in sample_result["decision_boundary"]["preconditions_checked"]
        if check["type"] == "missing_sample"
    )

    assert spec_result["ok"] is True
    assert spec_result["decision_boundary"]["boundary_effect"] == "pass"
    assert spec_check["present"] is True
    assert spec_check["action"] == "pass"

    assert sample_result["ok"] is True
    assert sample_result["decision_boundary"]["boundary_effect"] == "pass"
    assert sample_check["present"] is True
    assert sample_check["action"] == "pass"
