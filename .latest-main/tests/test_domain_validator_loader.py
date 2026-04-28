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

    assert payload["schema_version"] == "1.0"
    assert payload["payload_type"] == "domain-validator-payload"
    assert payload["isr_code"] == "void USB_ISR() { printf('bad'); }"
    assert payload["changed_functions"] == ["USB_ISR", "CFU_Handler"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert payload["changed_files"] == ["src/usb/isr.c", "src/usb/cfu.c"]
    assert payload["evidence_envelope"]["schema_version"] == "1.0"
    assert payload["evidence_envelope"]["source_keys"] == ["changed_files", "changed_functions", "isr_code"]
    assert payload["compatibility"]["additive_fields_allowed"] is True


def test_build_domain_validation_payload_includes_contract_snapshot_and_provenance(tmp_path):
    contract_file = tmp_path / "contract.yaml"
    contract_file.write_text(
        "name: temp-domain\n"
        "domain: firmware\n"
        "plugin_version: \"1.2.3\"\n"
        "framework_interface_version: \"1\"\n",
        encoding="utf-8",
    )

    payload = build_domain_validation_payload(
        response_text="response",
        checks={"changed_files": ["src/ui/layout.tsx"]},
        fields={"RULES": "common,temp-domain", "RISK": "low", "OVERSIGHT": "auto", "MEMORY_MODE": "candidate"},
        resolved_rules=["common", "temp-domain"],
        domain_contract={
            "name": "temp-domain",
            "documents": [],
            "ai_behavior_override": [],
            "raw": {
                "domain": "firmware",
                "plugin_version": "1.2.3",
                "framework_interface_version": "1",
            },
        },
        contract_file=contract_file,
    )

    assert payload["contract_snapshot"]["name"] == "temp-domain"
    assert payload["contract_snapshot"]["domain"] == "firmware"
    assert payload["contract_snapshot"]["plugin_version"] == "1.2.3"
    assert payload["contract_snapshot"]["framework_interface_version"] == "1"
    assert payload["evidence_envelope"]["provenance"]["contract_name"] == "temp-domain"
    assert payload["evidence_envelope"]["provenance"]["contract_domain"] == "firmware"
    assert payload["evidence_envelope"]["provenance"]["plugin_version"] == "1.2.3"
    assert payload["evidence_envelope"]["provenance"]["contract_path"] == str(contract_file.resolve())


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


def test_build_domain_validation_payload_can_extract_functions_from_diff_file(tmp_path):
    diff_file = tmp_path / "usb_hub.patch"
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
+    printf("bad");
+}
""".strip(),
        encoding="utf-8",
    )

    payload = build_domain_validation_payload(
        response_text="response",
        checks={"diff_file": str(diff_file)},
        fields={"RULES": "common,hub-firmware"},
        resolved_rules=["common", "hub-firmware"],
        domain_contract={"documents": [], "ai_behavior_override": []},
    )

    assert payload["changed_functions"] == ["USB_ISR"]
    assert payload["interrupt_functions"] == ["USB_ISR"]
    assert "printf" in payload["isr_code"]
