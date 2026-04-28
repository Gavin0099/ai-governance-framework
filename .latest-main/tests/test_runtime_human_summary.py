import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.core.human_summary import build_summary_line, format_contract_summary_label


def test_format_contract_summary_label_includes_risk_tier_when_known():
    assert format_contract_summary_label("kernel-driver", "high") == "kernel-driver/high"


def test_format_contract_summary_label_omits_unknown_risk_tier():
    assert format_contract_summary_label("custom-contract", "unknown") == "custom-contract"


def test_build_summary_line_joins_non_empty_parts():
    assert build_summary_line("ok=True", None, "rules=common") == "summary=ok=True | rules=common"
