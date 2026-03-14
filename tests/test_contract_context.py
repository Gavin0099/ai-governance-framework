import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.contract_context import contract_label, extract_contract_context, normalize_session_start_payload


def test_normalize_session_start_payload_handles_envelope_shape():
    normalized = normalize_session_start_payload(
        {
            "event_type": "session_start",
            "result": {"task_text": "demo"},
        }
    )

    assert normalized == {"task_text": "demo"}


def test_extract_contract_context_reads_resolution_and_domain_fields():
    context = extract_contract_context(
        {
            "resolved_contract_file": "D:/USB-Hub-Firmware-Architecture-Contract/contract.yaml",
            "contract_resolution": {"source": "discovery"},
            "domain_contract": {
                "name": "usb-hub-firmware-contract",
                "raw": {
                    "domain": "firmware",
                    "plugin_version": "1.0.0",
                },
            },
        }
    )

    assert context["source"] == "discovery"
    assert context["path"] == "D:/USB-Hub-Firmware-Architecture-Contract/contract.yaml"
    assert context["name"] == "usb-hub-firmware-contract"
    assert context["domain"] == "firmware"
    assert context["plugin_version"] == "1.0.0"
    assert context["risk_tier"] == "medium"


def test_contract_label_prefers_domain_over_name():
    assert contract_label({"domain": "kernel-driver", "name": "kernel-driver-contract"}) == "kernel-driver"
    assert contract_label({"domain": None, "name": "custom-contract"}) == "custom-contract"
