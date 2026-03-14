import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.domain_contract_loader import load_domain_contract
from runtime_hooks.core.pre_task_check import run_pre_task_check
from runtime_hooks.core.post_task_check import run_post_task_check
from runtime_hooks.core.session_start import build_session_start_context, format_human_result


EXAMPLE_CONTRACT = Path("examples/usb-hub-contract/contract.yaml")


def test_usb_hub_example_contract_loads():
    loaded = load_domain_contract(EXAMPLE_CONTRACT)

    assert loaded is not None
    assert loaded["name"] == "usb-hub-firmware-contract"
    assert len(loaded["documents"]) == 2
    assert len(loaded["ai_behavior_override"]) == 1
    assert loaded["validators"][0]["name"] == "interrupt_safety_validator"


def test_usb_hub_example_session_start_includes_domain_previews():
    result = build_session_start_context(
        project_root=Path(".").resolve(),
        plan_path=Path("PLAN.md"),
        rules="common,hub-firmware",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Validate USB hub firmware response flow",
        contract_file=EXAMPLE_CONTRACT,
    )

    output = format_human_result(result)
    assert "domain_contract=usb-hub-firmware-contract" in output
    assert "domain_documents=USB_HUB_FW_CHECKLIST.md,USB_HUB_ARCHITECTURE.md" in output
    assert "domain_behavior_overrides=AGENTS.md" in output
    assert "behavior_preview[AGENTS.md]=# USB-Hub Firmware Agent Rules" in output
    assert "document_preview[USB_HUB_FW_CHECKLIST.md]=# USB Hub Firmware Checklist" in output
    assert "validator_preflight_ok=True" in output


def test_usb_hub_example_pre_task_check_loads_external_rule_pack():
    result = run_pre_task_check(
        project_root=Path(".").resolve(),
        rules="common,hub-firmware",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text="Validate USB hub firmware response flow",
        contract_file=EXAMPLE_CONTRACT,
    )

    names = [pack["name"] for pack in result["active_rules"]["active_rules"]]
    content = "\n".join(
        file["content"]
        for pack in result["active_rules"]["active_rules"]
        if pack["name"] == "hub-firmware"
        for file in pack["files"]
    )

    assert result["ok"] is True
    assert names == ["common", "hub-firmware"]
    assert "HUB-001 - cfu-response-must-follow-request" in content
    assert "HUB-004 - dptr-guard" in content


def test_usb_hub_example_post_task_runs_domain_validator_advisory():
    response_text = (
        "[Governance Contract]\n"
        "LANG = C++\n"
        "LEVEL = L2\n"
        "SCOPE = feature\n"
        "PLAN = PLAN.md\n"
        "LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT\n"
        "CONTEXT = repo -> runtime-governance; NOT: platform rewrite\n"
        "PRESSURE = SAFE (20/200)\n"
        "RULES = common,hub-firmware\n"
        "RISK = medium\n"
        "OVERSIGHT = review-required\n"
        "MEMORY_MODE = candidate\n"
    )

    result = run_post_task_check(
        response_text,
        risk="medium",
        oversight="review-required",
        checks={
            "isr_code": "void USB_ISR() { printf(\"oops\"); }",
            "changed_functions": ["USB_ISR", "CFU_Handler"],
            "test_names": [
                "firmware_tests::test_cfu_failure_path_reports_error",
                "firmware_tests::test_interrupt_guard_cleanup_release",
            ],
            "warnings": [],
            "errors": [],
        },
        contract_file=EXAMPLE_CONTRACT,
    )

    assert result["ok"] is True
    assert len(result["domain_validator_results"]) == 1
    assert result["domain_validator_results"][0]["name"] == "interrupt_safety_validator"
    assert "printf" in result["domain_validator_results"][0]["warnings"][0]
    assert result["domain_validator_results"][0]["metadata"]["changed_functions"] == ["USB_ISR", "CFU_Handler"]
    assert any("domain-validator:interrupt_safety_validator:" in warning for warning in result["warnings"])
