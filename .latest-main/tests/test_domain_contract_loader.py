import sys
from pathlib import Path
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.contract_resolver import resolve_contract
from governance_tools.domain_contract_loader import load_domain_contract


@pytest.fixture
def local_contract_root():
    path = Path("tests") / "_tmp_domain_contract"
    if path.exists():
        shutil.rmtree(path)
    (path / "docs").mkdir(parents=True)
    (path / "rules" / "firmware").mkdir(parents=True)
    (path / "validators").mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_load_domain_contract_resolves_relative_paths_and_contents(local_contract_root):
    (local_contract_root / "docs" / "start_session.md").write_text("# Firmware session\nUse board facts.\n", encoding="utf-8")
    (local_contract_root / "rules" / "firmware" / "safety.md").write_text("# Firmware safety\nNo unsafe rollback.\n", encoding="utf-8")
    (local_contract_root / "validators" / "firmware_validator.py").write_text("def validate():\n    return True\n", encoding="utf-8")
    contract_file = local_contract_root / "contract.yaml"
    contract_file.write_text(
        "name: usb-hub-firmware\n"
        "documents:\n"
        "  - docs/start_session.md\n"
        "rule_roots:\n"
        "  - rules\n"
        "validators:\n"
        "  - validators/firmware_validator.py\n",
        encoding="utf-8",
    )

    loaded = load_domain_contract(contract_file)

    assert loaded is not None
    assert loaded["name"] == "usb-hub-firmware"
    assert loaded["documents"][0]["exists"] is True
    assert "Use board facts." in loaded["documents"][0]["content"]
    assert loaded["rule_roots"][0].replace("\\", "/").endswith("/tests/_tmp_domain_contract/rules")
    assert loaded["validators"][0]["name"] == "firmware_validator"
    assert loaded["validators"][0]["exists"] is True


def test_resolve_contract_discovers_contract_from_project_root(local_contract_root):
    contract_file = local_contract_root / "contract.yaml"
    contract_file.write_text("name: usb-hub-firmware\n", encoding="utf-8")
    nested_root = local_contract_root / "nested" / "deeper"
    nested_root.mkdir(parents=True)

    resolution = resolve_contract(project_root=nested_root)

    assert resolution.path == contract_file.resolve()
    assert resolution.source == "discovery"


def test_resolve_contract_prefers_explicit_path(local_contract_root):
    contract_file = local_contract_root / "contract.yaml"
    contract_file.write_text("name: usb-hub-firmware\n", encoding="utf-8")

    resolution = resolve_contract(contract_file, project_root=local_contract_root / "nested")

    assert resolution.path == contract_file.resolve()
    assert resolution.source == "explicit"


def test_empty_validators_inline_list_is_valid(tmp_path):
    """validators: [] (inline) must not produce a phantom path entry."""
    c = tmp_path / "contract.yaml"
    c.write_text(
        'name: test\nplugin_version: "1.0"\nframework_interface_version: "1"\n'
        'framework_compatible: ">=1.0.0,<2.0.0"\ndomain: test\n'
        "documents: []\nai_behavior_override: []\nvalidators: []\n",
        encoding="utf-8",
    )
    result = load_domain_contract(c)
    assert result["validators"] == [], (
        "validators: [] must load as empty list, not a phantom '[]' path entry"
    )


def test_empty_validators_multiline_list_is_valid(tmp_path):
    """validators: with no items (block style) must also produce empty list."""
    c = tmp_path / "contract.yaml"
    c.write_text(
        'name: test\nplugin_version: "1.0"\nframework_interface_version: "1"\n'
        'framework_compatible: ">=1.0.0,<2.0.0"\ndomain: test\n'
        "documents:\nai_behavior_override:\nvalidators:\n",
        encoding="utf-8",
    )
    result = load_domain_contract(c)
    assert result["validators"] == []
