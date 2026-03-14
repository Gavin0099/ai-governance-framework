import sys
from pathlib import Path
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.domain_validator_loader import (
    build_domain_validation_payload,
    preflight_domain_validators,
    run_domain_validators,
)


@pytest.fixture
def local_validator_contract_root():
    path = Path("tests") / "_tmp_domain_validator"
    if path.exists():
        shutil.rmtree(path)
    (path / "validators").mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_preflight_domain_validators_loads_domain_validator(local_validator_contract_root):
    (local_validator_contract_root / "validators" / "sample_validator.py").write_text(
        "from governance_tools.validator_interface import DomainValidator, ValidatorResult\n"
        "class SampleValidator(DomainValidator):\n"
        "    @property\n"
        "    def rule_ids(self):\n"
        "        return ['firmware-rule']\n"
        "    def validate(self, payload):\n"
        "        return ValidatorResult(ok=True, rule_ids=self.rule_ids)\n",
        encoding="utf-8",
    )
    contract_file = local_validator_contract_root / "contract.yaml"
    contract_file.write_text(
        "name: validator-test\n"
        "validators:\n"
        "  - validators/sample_validator.py\n",
        encoding="utf-8",
    )

    result = preflight_domain_validators(contract_file)

    assert result is not None
    assert result["ok"] is True
    assert result["validators"][0]["name"] == "sample_validator"
    assert result["validators"][0]["rule_ids"] == ["firmware-rule"]


def test_run_domain_validators_routes_only_matching_rules(local_validator_contract_root):
    (local_validator_contract_root / "validators" / "sample_validator.py").write_text(
        "from governance_tools.validator_interface import DomainValidator, ValidatorResult\n"
        "class SampleValidator(DomainValidator):\n"
        "    @property\n"
        "    def rule_ids(self):\n"
        "        return ['firmware-rule']\n"
        "    def validate(self, payload):\n"
        "        return ValidatorResult(ok=False, rule_ids=self.rule_ids, warnings=['advisory hit'])\n",
        encoding="utf-8",
    )
    contract_file = local_validator_contract_root / "contract.yaml"
    contract_file.write_text(
        "name: validator-test\n"
        "validators:\n"
        "  - validators/sample_validator.py\n",
        encoding="utf-8",
    )

    payload = build_domain_validation_payload(
        response_text="response",
        checks={"isr_code": "printf('bad');"},
        fields={"RULES": "common,firmware-rule"},
        resolved_rules=["common", "firmware-rule"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )
    result = run_domain_validators(
        contract_file=contract_file,
        payload=payload,
        active_rule_ids=["common", "firmware-rule"],
    )

    assert len(result) == 1
    assert result[0]["name"] == "sample_validator"
    assert result[0]["warnings"] == ["advisory hit"]


def test_build_domain_validation_payload_extracts_firmware_focused_fields():
    payload = build_domain_validation_payload(
        response_text="response",
        checks={
            "isr_code": "void USB_ISR() { printf('bad'); }",
            "changed_functions": ["USB_ISR", "CFU_Handler"],
            "changed_files": ["src/usb/isr.c", "src/usb/cfu.c"],
        },
        fields={"RULES": "common,hub-firmware"},
        resolved_rules=["common", "hub-firmware"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )

    assert payload["isr_code"] == "void USB_ISR() { printf('bad'); }"
    assert payload["changed_functions"] == ["USB_ISR", "CFU_Handler"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert payload["changed_files"] == ["src/usb/isr.c", "src/usb/cfu.c"]


def test_build_domain_validation_payload_can_extract_functions_from_diff_text():
    payload = build_domain_validation_payload(
        response_text="response",
        checks={
            "diff_text": """
void USB_ISR(void) {
    printf("bad");
}

static void CFU_Handler(void) {
    return;
}
""",
            "changed_files": ["src/usb/isr.c"],
        },
        fields={"RULES": "common,hub-firmware"},
        resolved_rules=["common", "hub-firmware"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )

    assert payload["changed_functions"] == ["USB_ISR", "CFU_Handler"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert "printf" in payload["isr_code"]


def test_build_domain_validation_payload_can_extract_functions_from_unified_diff():
    payload = build_domain_validation_payload(
        response_text="response",
        checks={
            "diff_text": """
@@ -1,3 +1,8 @@
+void USB_ISR(void) {
+    printf("bad");
+}
+
 static void CFU_Handler(void) {
     return;
 }
""",
        },
        fields={"RULES": "common,hub-firmware"},
        resolved_rules=["common", "hub-firmware"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )

    assert payload["changed_functions"] == ["USB_ISR", "CFU_Handler"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert "printf" in payload["isr_code"]


def test_build_domain_validation_payload_can_extract_from_changed_file_contents(tmp_path):
    source_file = tmp_path / "usb_isr.c"
    source_file.write_text(
        """
void USB_ISR(void) {
    printf("bad");
}
""".strip(),
        encoding="utf-8",
    )

    payload = build_domain_validation_payload(
        response_text="response",
        checks={
            "changed_files": [str(source_file)],
        },
        fields={"RULES": "common,hub-firmware"},
        resolved_rules=["common", "hub-firmware"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )

    assert payload["changed_functions"] == ["USB_ISR"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert "printf" in payload["isr_code"]
