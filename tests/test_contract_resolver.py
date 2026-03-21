import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.contract_resolver import resolve_contract


@pytest.fixture
def resolver_root():
    path = Path("tests") / "_tmp_contract_resolver"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    # .git stops _search_upward_for_contract from escaping into the framework root
    (path / ".git").mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_explicit_path_takes_priority(resolver_root):
    contract_file = resolver_root / "contract.yaml"
    contract_file.write_text("name: explicit-contract\n", encoding="utf-8")

    resolution = resolve_contract(explicit_path=contract_file, project_root=resolver_root / "nested")

    assert resolution.path == contract_file.resolve()
    assert resolution.source == "explicit"
    assert resolution.error is None


def test_env_var_used_when_no_explicit(resolver_root, monkeypatch):
    contract_file = resolver_root / "contract.yaml"
    contract_file.write_text("name: env-contract\n", encoding="utf-8")
    monkeypatch.setenv("AI_GOVERNANCE_CONTRACT", str(contract_file))

    resolution = resolve_contract(project_root=resolver_root / "nested")

    assert resolution.path == contract_file.resolve()
    assert resolution.source == "env"


def test_discovery_finds_contract_yaml_in_project_root(resolver_root):
    contract_file = resolver_root / "contract.yaml"
    contract_file.write_text("name: discovered-contract\n", encoding="utf-8")
    nested = resolver_root / "src" / "driver"
    nested.mkdir(parents=True)

    resolution = resolve_contract(project_root=nested)

    assert resolution.path == contract_file.resolve()
    assert resolution.source == "discovery"


def test_discovery_stops_at_git_boundary(resolver_root):
    workspace = resolver_root / "workspace"
    workspace.mkdir()
    (workspace / ".git").mkdir()
    (resolver_root / "contract.yaml").write_text("name: outer-contract\n", encoding="utf-8")
    nested = workspace / "src" / "driver"
    nested.mkdir(parents=True)

    resolution = resolve_contract(project_root=nested)

    assert resolution.path is None
    assert resolution.source == "not_found"


def test_multiple_contracts_found_returns_warning(resolver_root):
    left = resolver_root / "usb" / "contract.yaml"
    right = resolver_root / "driver" / "contract.yaml"
    left.parent.mkdir(parents=True)
    right.parent.mkdir(parents=True)
    left.write_text("name: usb\n", encoding="utf-8")
    right.write_text("name: driver\n", encoding="utf-8")
    evidence_file = right.parent / "fixtures" / "checks.json"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text("{}", encoding="utf-8")

    resolution = resolve_contract(project_root=left.parent, extra_paths=[evidence_file])

    assert resolution.path is None
    assert resolution.source == "not_found"
    assert any("Multiple contract.yaml candidates were discovered" in warning for warning in resolution.warnings)


def test_not_found_returns_soft_skip(resolver_root, monkeypatch):
    monkeypatch.delenv("AI_GOVERNANCE_CONTRACT", raising=False)

    resolution = resolve_contract(project_root=resolver_root)

    assert resolution.path is None
    assert resolution.source == "not_found"
    assert resolution.error is None


def test_missing_explicit_path_returns_error(resolver_root):
    resolution = resolve_contract(explicit_path=resolver_root / "missing-contract.yaml")

    assert resolution.path is None
    assert resolution.source == "explicit"
    assert "does not exist" in (resolution.error or "")
