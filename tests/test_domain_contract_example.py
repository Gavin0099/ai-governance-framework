import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.domain_contract_loader import load_domain_contract
from runtime_hooks.core.pre_task_check import run_pre_task_check
from runtime_hooks.core.post_task_check import run_post_task_check
from runtime_hooks.core.session_start import build_session_start_context, format_human_result


EXAMPLE_CONTRACT = Path("examples/usb-hub-contract/contract.yaml")
EXAMPLE_FIXTURES = Path("examples/usb-hub-contract/fixtures")


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
        task_level="L2",
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
    assert result["domain_validator_results"][0]["metadata"]["interrupt_functions"] == ["USB_ISR"]
    assert any("domain-validator:interrupt_safety_validator:" in warning for warning in result["warnings"])


def test_usb_hub_example_post_task_skips_warning_without_interrupt_context():
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
            "changed_functions": ["CFU_Handler", "BufferCopy"],
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
    assert result["domain_validator_results"][0]["warnings"] == []
    assert result["domain_validator_results"][0]["metadata"]["interrupt_functions"] == []


def test_usb_hub_example_post_task_can_infer_interrupt_context_from_diff_text():
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
            "diff_text": """
void USB_ISR(void) {
    printf("oops");
}

static void CFU_Handler(void) {
    return;
}
""",
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
    assert "printf" in result["domain_validator_results"][0]["warnings"][0]
    assert result["domain_validator_results"][0]["metadata"]["interrupt_functions"] == ["USB_ISR"]


def test_usb_hub_example_post_task_cli_can_consume_checks_file_fixture():
    command = [
        sys.executable,
        "runtime_hooks/core/post_task_check.py",
        "--file",
        str((EXAMPLE_FIXTURES / "post_task_response.txt").resolve()),
        "--risk",
        "medium",
        "--oversight",
        "review-required",
        "--checks-file",
        str((EXAMPLE_FIXTURES / "interrupt_regression.checks.json").resolve()),
        "--contract",
        str(EXAMPLE_CONTRACT.resolve()),
        "--format",
        "json",
    ]

    completed = subprocess.run(
        command,
        cwd=Path(".").resolve(),
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["domain_validator_results"][0]["name"] == "interrupt_safety_validator"
    assert "printf" in result["domain_validator_results"][0]["warnings"][0]
    assert result["domain_validator_results"][0]["metadata"]["interrupt_functions"] == ["USB_ISR"]
    assert any("domain-validator:interrupt_safety_validator:" in warning for warning in result["warnings"])


def test_usb_hub_example_post_task_cli_can_consume_diff_file_checks(tmp_path):
    diff_file = tmp_path / "interrupt_regression.patch"
    diff_file.write_text(
        """
diff --git a/src/usb_hub.c b/src/usb_hub.c
index 1111111..2222222 100644
--- a/src/usb_hub.c
+++ b/src/usb_hub.c
@@ -40,6 +40,11 @@ static void CFU_Handler(void) {
     return;
 }
+
+void USB_ISR(void) {
+    printf("oops");
+}
""".strip(),
        encoding="utf-8",
    )
    checks_file = tmp_path / "interrupt_regression_diff_file.checks.json"
    checks_file.write_text(
        json.dumps(
            {
                "diff_file": str(diff_file.resolve()),
                "changed_files": [str((EXAMPLE_FIXTURES / "src" / "usb_hub.c").resolve())],
                "test_names": [
                    "firmware_tests::test_cfu_failure_path_reports_error",
                    "firmware_tests::test_interrupt_guard_cleanup_release",
                ],
                "warnings": [],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    command = [
        sys.executable,
        "runtime_hooks/core/post_task_check.py",
        "--file",
        str((EXAMPLE_FIXTURES / "post_task_response.txt").resolve()),
        "--risk",
        "medium",
        "--oversight",
        "review-required",
        "--checks-file",
        str(checks_file.resolve()),
        "--contract",
        str(EXAMPLE_CONTRACT.resolve()),
        "--format",
        "json",
    ]

    completed = subprocess.run(
        command,
        cwd=Path(".").resolve(),
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert "printf" in result["domain_validator_results"][0]["warnings"][0]
    assert result["domain_validator_results"][0]["metadata"]["interrupt_functions"] == ["USB_ISR"]
