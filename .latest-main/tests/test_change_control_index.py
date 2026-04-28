import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_control_index import build_change_control_index


def test_change_control_index_lists_generated_artifacts(tmp_path):
    (tmp_path / "claude_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Refactor boundary | proposal_risk=medium | promoted=False\n",
        encoding="utf-8",
    )
    (tmp_path / "claude_session_start.txt").write_text("handoff", encoding="utf-8")
    (tmp_path / "claude_session_start.json").write_text(
        """
{
  "event_type": "session_start",
  "result": {
    "contract_resolution": {
      "source": "discovery",
      "path": "D:/USB-Hub-Firmware-Architecture-Contract/contract.yaml"
    },
    "domain_contract": {
      "name": "usb-hub-firmware-contract",
      "raw": {
        "domain": "firmware",
        "plugin_version": "1.0.0"
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    output = build_change_control_index(tmp_path)

    assert "[change_control_index]" in output
    assert "summary=change_control_summaries=1 | session_start_notes=1 | session_start_envelopes=1" in output
    assert "[review_order]" in output
    assert "[priority_change_control_summaries]" in output
    assert "claude_change_control_summary.txt | summary=task=Refactor boundary | proposal_risk=medium | promoted=False | contract_source=discovery | contract_name=usb-hub-firmware-contract | contract_domain=firmware | plugin_version=1.0.0 | contract_risk_tier=medium" in output
    assert "claude_session_start.txt" in output
    assert "claude_session_start.json" in output


def test_change_control_index_prioritizes_higher_risk_summaries(tmp_path):
    (tmp_path / "low_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Minor cleanup | proposal_risk=low | promoted=True\n",
        encoding="utf-8",
    )
    (tmp_path / "high_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Driver boundary change | proposal_risk=high | runtime_decision=blocked | promoted=False\n",
        encoding="utf-8",
    )

    output = build_change_control_index(tmp_path)

    priority_section = output.split("[priority_change_control_summaries]\n", 1)[1].split("\n[change_control_summaries]", 1)[0]
    assert priority_section.index("high_change_control_summary.txt") < priority_section.index("low_change_control_summary.txt")


def test_change_control_index_prioritizes_high_risk_domain_when_summary_risk_is_equal(tmp_path):
    (tmp_path / "firmware_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Firmware review | proposal_risk=medium | promoted=False | contract=firmware\n",
        encoding="utf-8",
    )
    (tmp_path / "firmware_session_start.json").write_text(
        """
{
  "event_type": "session_start",
  "result": {
    "domain_contract": {
      "name": "usb-hub-firmware-contract",
      "raw": {
        "domain": "firmware",
        "plugin_version": "1.0.0"
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "kernel_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Driver review | proposal_risk=medium | promoted=False | contract=kernel-driver\n",
        encoding="utf-8",
    )
    (tmp_path / "kernel_session_start.json").write_text(
        """
{
  "event_type": "session_start",
  "result": {
    "domain_contract": {
      "name": "kernel-driver-contract",
      "raw": {
        "domain": "kernel-driver",
        "plugin_version": "1.0.0"
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    output = build_change_control_index(tmp_path)

    priority_section = output.split("[priority_change_control_summaries]\n", 1)[1].split("\n[change_control_summaries]", 1)[0]
    assert priority_section.index("kernel_change_control_summary.txt") < priority_section.index("firmware_change_control_summary.txt")
