import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.rule_pack_loader import (
    available_rule_packs,
    describe_rule_selection,
    load_rule_content,
    parse_rule_list,
    rule_pack_category,
)


def test_parse_rule_list_deduplicates_and_strips():
    assert parse_rule_list("common, python,common") == ["common", "python"]


def test_available_rule_packs_contains_seed_packs():
    packs = available_rule_packs()
    assert "common" in packs
    assert "python" in packs
    assert "cpp" in packs
    assert "refactor" in packs
    assert "csharp" in packs
    assert "avalonia" in packs
    assert "swift" in packs
    assert "kernel-driver" in packs


def test_describe_rule_selection_resolves_files():
    description = describe_rule_selection(["common", "python"])
    assert description["valid"] is True
    assert [item["name"] for item in description["resolved"]] == ["common", "python"]
    assert [item["category"] for item in description["resolved"]] == ["scope", "language"]


def test_describe_rule_selection_reports_missing():
    description = describe_rule_selection(["common", "missing-pack"])
    assert description["valid"] is False
    assert description["missing"] == ["missing-pack"]


def test_load_rule_content_returns_file_metadata_and_content():
    loaded = load_rule_content(["common"])
    assert loaded["valid"] is True
    assert loaded["active_rules"][0]["name"] == "common"
    assert loaded["active_rules"][0]["category"] == "scope"
    first_file = loaded["active_rules"][0]["files"][0]
    assert first_file["path"].replace("\\", "/").endswith("governance/rules/common/core.md")
    assert first_file["title"]
    assert first_file["content"]


def test_load_rule_content_can_load_cpp_build_boundary_pack():
    loaded = load_rule_content(["cpp"])
    assert loaded["valid"] is True
    first_file = loaded["active_rules"][0]["files"][0]
    assert "AdditionalIncludeDirectories" in first_file["content"]
    assert "cross-project private header" in first_file["content"]


def test_load_rule_content_can_load_refactor_pack():
    loaded = load_rule_content(["refactor"])
    assert loaded["valid"] is True
    assert loaded["active_rules"][0]["name"] == "refactor"
    contents = "\n".join(file["content"] for file in loaded["active_rules"][0]["files"]).lower()
    assert "可觀測行為保持不變" in contents
    assert "新的 boundary crossing" in contents
    assert "regression evidence" in contents
    assert "partial side effect" in contents
    assert "cleanup、rollback、dispose、release、或 revert" in contents


def test_load_rule_content_can_load_csharp_avalonia_swift_packs():
    loaded = load_rule_content(["csharp", "avalonia", "swift"])
    assert loaded["valid"] is True
    names = [pack["name"] for pack in loaded["active_rules"]]
    assert names == ["csharp", "avalonia", "swift"]
    categories = [pack["category"] for pack in loaded["active_rules"]]
    assert categories == ["language", "framework", "language"]
    contents = "\n".join(
        file["content"]
        for pack in loaded["active_rules"]
        for file in pack["files"]
    )
    assert "async void" in contents
    assert "Dispatcher.UIThread" in contents
    assert "structured concurrency" in contents


def test_load_rule_content_can_load_kernel_driver_pack():
    loaded = load_rule_content(["kernel-driver"])
    assert loaded["valid"] is True
    assert loaded["active_rules"][0]["name"] == "kernel-driver"
    assert loaded["active_rules"][0]["category"] == "platform"
    contents = "\n".join(file["content"] for file in loaded["active_rules"][0]["files"]).lower()
    assert "passive_level" in contents
    assert "dma" in contents
    assert "surprise-remove" in contents


def test_rule_pack_category_defaults_to_custom_for_unknown_packs():
    assert rule_pack_category("common") == "scope"
    assert rule_pack_category("avalonia") == "framework"
    assert rule_pack_category("kernel-driver") == "platform"
    assert rule_pack_category("my-team-pack") == "custom"


def test_rule_loader_supports_external_rule_roots():
    external_root = Path("tests") / "_tmp_rule_pack_loader" / "rules"
    if external_root.parent.exists():
        shutil.rmtree(external_root.parent)
    firmware_pack = external_root / "firmware"
    firmware_pack.mkdir(parents=True)
    try:
        (firmware_pack / "safety.md").write_text("# Firmware safety\nUse bounded DMA.\n", encoding="utf-8")

        loaded = load_rule_content(["common", "firmware"], [external_root, Path("governance/rules")])

        assert loaded["valid"] is True
        assert [pack["name"] for pack in loaded["active_rules"]] == ["common", "firmware"]
        assert loaded["active_rules"][1]["category"] == "custom"
        assert "bounded DMA" in loaded["active_rules"][1]["files"][0]["content"]
    finally:
        shutil.rmtree(external_root.parent, ignore_errors=True)
