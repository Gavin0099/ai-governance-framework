import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.domain_governance_metadata import domain_priority_rank, domain_risk_tier, normalize_domain_name


def test_normalize_domain_name_lowercases_and_trims():
    assert normalize_domain_name("  Kernel-Driver ") == "kernel-driver"


def test_domain_priority_rank_prefers_high_risk_domains():
    assert domain_priority_rank("kernel-driver") < domain_priority_rank("firmware")


def test_domain_priority_rank_returns_default_for_unknown_domain():
    assert domain_priority_rank("mobile-app") == 50
    assert domain_priority_rank(None) == 99


def test_domain_risk_tier_returns_expected_labels():
    assert domain_risk_tier("kernel-driver") == "high"
    assert domain_risk_tier("firmware") == "medium"
    assert domain_risk_tier("usb-hub-firmware-contract") == "medium"
    assert domain_risk_tier("mobile-app") == "unknown"
