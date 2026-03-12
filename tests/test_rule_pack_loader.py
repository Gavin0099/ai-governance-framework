import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.rule_pack_loader import (
    available_rule_packs,
    describe_rule_selection,
    parse_rule_list,
)


def test_parse_rule_list_deduplicates_and_strips():
    assert parse_rule_list("common, python,common") == ["common", "python"]


def test_available_rule_packs_contains_seed_packs():
    packs = available_rule_packs()
    assert "common" in packs
    assert "python" in packs


def test_describe_rule_selection_resolves_files():
    description = describe_rule_selection(["common", "python"])
    assert description["valid"] is True
    assert [item["name"] for item in description["resolved"]] == ["common", "python"]


def test_describe_rule_selection_reports_missing():
    description = describe_rule_selection(["common", "missing-pack"])
    assert description["valid"] is False
    assert description["missing"] == ["missing-pack"]
