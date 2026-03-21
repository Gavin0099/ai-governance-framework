#!/usr/bin/env python3
"""
Unit tests for governance_tools/governance_drift_checker.py
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.governance_drift_checker import (
    BaselineDriftResult,
    BASELINE_YAML_RELPATH,
    BASELINE_SOURCE_RELPATH,
    _sha256_file,
    _current_baseline_version,
    _read_baseline_yaml,
    check_governance_drift,
    format_human,
    format_json,
)

FRAMEWORK_ROOT = Path(__file__).parent.parent


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write_agents_base(repo: Path, version: str = "1.0.0") -> Path:
    text = (
        "# AGENTS.base.md\n"
        "<!-- governance-baseline: protected -->\n"
        f"<!-- baseline_version: {version} -->\n\n"
        "## Level Alignment\n\nSome content.\n\n"
        "## Execution Pipeline\n\nContent.\n\n"
        "## Forbidden Behaviors\n\nContent.\n"
    )
    p = repo / "AGENTS.base.md"
    p.write_text(text, encoding="utf-8")
    return p


def _write_plan(repo: Path) -> Path:
    text = (
        "# PLAN.md\n"
        "<!-- governance-baseline: overridable -->\n\n"
        "> **最後更新**: 2026-03-21\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n- [ ] Phase A\n\n"
        "## Active Sprint\n\n- [ ] Task 1\n\n"
        "## Backlog\n\n- P1: none\n"
    )
    p = repo / "PLAN.md"
    p.write_text(text, encoding="utf-8")
    return p


def _write_contract(repo: Path, include_agents_base: bool = True) -> Path:
    docs_line = "  - AGENTS.base.md\n" if include_agents_base else ""
    text = (
        f"name: test-contract\n"
        f"plugin_version: \"1.0.0\"\n"
        f"framework_interface_version: \"1\"\n"
        f"framework_compatible: \">=1.0.0,<2.0.0\"\n"
        f"domain: test\n"
        f"documents:\n"
        f"{docs_line}"
        f"  - PLAN.md\n"
        f"ai_behavior_override:\n"
        f"  - AGENTS.base.md\n"
        f"validators:\n"
    )
    p = repo / "contract.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_baseline_yaml(
    repo: Path,
    agents_hash: str,
    plan_hash: str,
    contract_hash: str,
    baseline_version: str = "1.0.0",
    initialized_at: str = "2026-03-21T10:00:00Z",
    source_commit: str = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
) -> Path:
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: {baseline_version}\n"
        f"source_commit: {source_commit}\n"
        f"framework_root: {FRAMEWORK_ROOT}\n"
        f"initialized_at: {initialized_at}\n"
        f"initialized_by: scripts/init-governance.sh\n"
        f"sha256.AGENTS.base.md: {agents_hash}\n"
        f"sha256.PLAN.md: {plan_hash}\n"
        f"sha256.contract.yaml: {contract_hash}\n"
        f"overridable.AGENTS.base.md: protected\n"
        f"overridable.PLAN.md: overridable\n"
        f"overridable.contract.yaml: overridable\n"
        f"contract_required_fields:\n"
        f"  - name\n"
        f"  - framework_interface_version\n"
        f"  - framework_compatible\n"
        f"  - domain\n"
        f"plan_required_sections:\n"
        f"  - \"## Current Phase\"\n"
        f"  - \"## Active Sprint\"\n"
        f"  - \"## Backlog\"\n"
        f"plan_section_inventory:\n"
        f"  - \"## Current Phase\"\n"
        f"  - \"## Active Sprint\"\n"
        f"  - \"## Backlog\"\n"
    )
    gov_dir = repo / ".governance"
    gov_dir.mkdir(exist_ok=True)
    p = gov_dir / "baseline.yaml"
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def clean_repo(tmp_path):
    """A repo with all baseline files correctly set up."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    return tmp_path


# ── _sha256_file ──────────────────────────────────────────────────────────────

def test_sha256_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert _sha256_file(f) == expected


# ── _current_baseline_version ─────────────────────────────────────────────────

def test_current_baseline_version_from_framework():
    version = _current_baseline_version(FRAMEWORK_ROOT)
    assert version == "1.0.0"


def test_current_baseline_version_missing_file(tmp_path):
    assert _current_baseline_version(tmp_path) is None


# ── _read_baseline_yaml ───────────────────────────────────────────────────────

def test_read_baseline_yaml_missing(tmp_path):
    assert _read_baseline_yaml(tmp_path) is None


def test_read_baseline_yaml_present(tmp_path):
    gov = tmp_path / ".governance"
    gov.mkdir()
    (gov / "baseline.yaml").write_text("baseline_version: 1.0.0\n", encoding="utf-8")
    data = _read_baseline_yaml(tmp_path)
    assert data is not None
    assert data["baseline_version"] == "1.0.0"


# ── check_governance_drift — critical paths ───────────────────────────────────

def test_no_baseline_yaml_is_critical(tmp_path):
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT)
    assert result.severity == "critical"
    assert result.ok is False
    assert not result.checks.get("baseline_yaml_present", True)
    assert len(result.remediation_hints) > 0


def test_protected_file_missing_is_critical(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    agents.unlink()  # remove protected file

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.severity == "critical"
    assert result.checks.get("protected_files_present") is False


def test_protected_file_modified_is_critical(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    # Tamper with the protected file
    agents.write_text("tampered content", encoding="utf-8")

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT)
    assert result.severity == "critical"
    assert result.checks.get("protected_files_unmodified") is False


def test_contract_missing_required_field_is_critical(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    # Write contract without required 'domain' field
    bad_contract = tmp_path / "contract.yaml"
    bad_contract.write_text(
        "name: test\nframework_interface_version: \"1\"\nframework_compatible: \">=1.0.0\"\n",
        encoding="utf-8",
    )
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(bad_contract),
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.ok is False
    assert result.checks.get("contract_required_fields_present") is False


def test_contract_not_referencing_agents_base_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path, include_agents_base=False)
    # Override ai_behavior_override without AGENTS.base.md
    contract.write_text(
        "name: test\nplugin_version: \"1.0.0\"\nframework_interface_version: \"1\"\n"
        "framework_compatible: \">=1.0.0,<2.0.0\"\ndomain: test\ndocuments:\n  - PLAN.md\n"
        "ai_behavior_override:\n  - PLAN.md\nvalidators:\n",
        encoding="utf-8",
    )
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_agents_base_referenced") is False
    # Should be warning, not critical
    agent_finding = next(
        (f for f in result.findings if f["check"] == "contract_agents_base_referenced"), None
    )
    assert agent_finding is not None
    assert agent_finding["severity"] == "warning"


def test_plan_missing_section_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    # Write PLAN.md without required sections
    plan = tmp_path / "PLAN.md"
    plan.write_text(
        "# PLAN.md\n> **最後更新**: 2026-03-21\n> **Owner**: Test\n> **Freshness**: Sprint (7d)\n",
        encoding="utf-8",
    )
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    section_findings = [f for f in result.findings if f["check"] == "plan_required_sections_present"]
    assert len(section_findings) > 0
    assert all(f["severity"] == "warning" for f in section_findings)


# ── check_governance_drift — ok path ─────────────────────────────────────────

def test_clean_repo_is_ok(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    assert result.ok is True
    assert result.severity == "ok"
    assert result.checks["baseline_yaml_present"] is True
    assert result.checks["protected_files_present"] is True
    assert result.checks["protected_files_unmodified"] is True
    assert result.checks["protected_file_sentinel_present"] is True
    assert result.checks["contract_required_fields_present"] is True
    assert result.checks["contract_agents_base_referenced"] is True
    assert result.checks["plan_required_sections_present"] is True


def test_skip_hash_still_passes(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.ok is True


# ── check_governance_drift — version checks ───────────────────────────────────

def test_older_baseline_version_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        baseline_version="0.1.0",  # older than framework 1.0.0
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("framework_version_current") is False
    version_finding = next(
        (f for f in result.findings if f["check"] == "framework_version_current"), None
    )
    assert version_finding is not None
    assert version_finding["severity"] == "warning"
    assert any("--upgrade" in h for h in result.remediation_hints)


def test_current_baseline_version_passes(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("framework_version_current") is True


# ── check_governance_drift — freshness ───────────────────────────────────────

def test_stale_baseline_yaml_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        initialized_at="2020-01-01T00:00:00Z",  # very old
    )

    result = check_governance_drift(
        tmp_path,
        framework_root=FRAMEWORK_ROOT,
        skip_hash=True,
        freshness_threshold_days=30,
    )
    assert result.checks.get("baseline_yaml_freshness") is False


# ── Result fields ─────────────────────────────────────────────────────────────

def test_result_has_correct_repo_root(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    assert str(clean_repo.resolve()) == result.repo_root


def test_result_has_baseline_version(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    assert result.baseline_version == "1.0.0"


def test_result_has_framework_version(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    assert result.framework_version == "1.0.0"


# ── format_human ─────────────────────────────────────────────────────────────

def test_format_human_ok(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    out = format_human(result)
    assert "[governance_drift_check]" in out
    assert "severity           = ok" in out
    assert "PASS" in out


def test_format_human_critical(tmp_path):
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT)
    out = format_human(result)
    assert "critical" in out
    assert "remediation:" in out
    assert "$ bash" in out


# ── format_json ──────────────────────────────────────────────────────────────

def test_format_json_ok(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    data = json.loads(format_json(result))
    assert data["ok"] is True
    assert data["severity"] == "ok"
    assert isinstance(data["checks"], dict)
    assert isinstance(data["findings"], list)


def test_format_json_critical(tmp_path):
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT)
    data = json.loads(format_json(result))
    assert data["ok"] is False
    assert data["severity"] == "critical"


# ── to_dict ──────────────────────────────────────────────────────────────────

def test_to_dict_serializable(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    d = result.to_dict()
    # Must be JSON-serializable
    json.dumps(d)
    assert "ok" in d
    assert "severity" in d
    assert "checks" in d


# ── source_commit_recorded (12th check) ──────────────────────────────────────

def test_source_commit_recorded_passes_with_valid_sha(clean_repo):
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("source_commit_recorded") is True


def test_source_commit_missing_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        source_commit="",       # empty
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("source_commit_recorded") is False
    finding = next(f for f in result.findings if f["check"] == "source_commit_recorded")
    assert finding["severity"] == "warning"
    assert any("init-governance.sh" in h for h in result.remediation_hints)


def test_source_commit_unknown_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        source_commit="unknown",
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("source_commit_recorded") is False


def test_source_commit_invalid_sha_is_warning(tmp_path):
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        source_commit="not-a-valid-sha!",
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("source_commit_recorded") is False


def test_all_16_checks_present_in_ok_repo(clean_repo):
    """Verify exactly 16 named checks appear in a fully valid repo."""
    result = check_governance_drift(clean_repo, framework_root=FRAMEWORK_ROOT)
    expected_checks = {
        "baseline_yaml_present",
        "baseline_version_known",
        "framework_version_current",
        "source_commit_recorded",
        "protected_files_present",
        "protected_files_unmodified",
        "protected_file_sentinel_present",
        "contract_required_fields_present",
        "contract_agents_base_referenced",
        "contract_no_placeholders",
        "contract_not_framework_copy",
        "plan_required_sections_present",
        "agents_sections_filled",
        "plan_freshness",
        "plan_inventory_current",
        "baseline_yaml_freshness",
    }
    assert set(result.checks.keys()) == expected_checks
    assert len(result.checks) == 16


# ── Custom plan_required_sections (--adopt-existing use case) ─────────────────

def _write_plan_custom(repo: Path, sections: list[str]) -> Path:
    """Write a PLAN.md whose H2 headings are the given sections."""
    lines = [
        "# PLAN.md",
        "> **最後更新**: 2026-03-21",
        "> **Owner**: Test",
        "> **Freshness**: Sprint (7d)",
        "",
    ]
    for section in sections:
        lines += [section, "", "- content", ""]
    p = repo / "PLAN.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _write_baseline_yaml_custom_sections(
    repo: Path,
    agents_hash: str,
    plan_hash: str,
    contract_hash: str,
    plan_sections: list[str],
    source_commit: str = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
) -> Path:
    sections_block = "plan_required_sections:\n" + "".join(
        f'  - "{s}"\n' for s in plan_sections
    )
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: 1.0.0\n"
        f"source_commit: {source_commit}\n"
        f"framework_root: {FRAMEWORK_ROOT}\n"
        f"initialized_at: 2026-03-21T10:00:00Z\n"
        f"initialized_by: scripts/init-governance.sh\n"
        f"sha256.AGENTS.base.md: {agents_hash}\n"
        f"sha256.PLAN.md: {plan_hash}\n"
        f"sha256.contract.yaml: {contract_hash}\n"
        f"overridable.AGENTS.base.md: protected\n"
        f"overridable.PLAN.md: overridable\n"
        f"overridable.contract.yaml: overridable\n"
        f"contract_required_fields:\n"
        f"  - name\n"
        f"  - framework_interface_version\n"
        f"  - framework_compatible\n"
        f"  - domain\n"
        + sections_block
    )
    gov_dir = repo / ".governance"
    gov_dir.mkdir(exist_ok=True)
    p = gov_dir / "baseline.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_explicit_plan_required_sections_pass_when_present(tmp_path):
    """plan_required_sections explicitly set in baseline.yaml are enforced."""
    chinese_sections = ["## 🏗️ 當前階段", "## 🔥 本輪聚焦", "## 📦 Phase 詳細規劃"]
    agents = _write_agents_base(tmp_path)
    plan = _write_plan_custom(tmp_path, chinese_sections)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_custom_sections(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        plan_sections=chinese_sections,
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert result.checks["plan_required_sections_present"] is True
    assert result.severity in {"ok", "warning"}


def test_explicit_plan_required_sections_fail_when_missing(tmp_path):
    """If baseline.yaml declares required sections that don't exist in PLAN.md, check fails."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan_custom(tmp_path, ["## 🏗️ 當前階段", "## 🔥 本輪聚焦"])
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_custom_sections(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        plan_sections=["## 🏗️ 當前階段", "## 🔥 本輪聚焦", "## 📊 THIS SECTION DOES NOT EXIST"],
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert result.checks["plan_required_sections_present"] is False
    finding = next(f for f in result.findings if f["check"] == "plan_required_sections_present")
    assert "THIS SECTION DOES NOT EXIST" in finding["detail"]


def test_no_plan_required_sections_trivially_passes(tmp_path):
    """When plan_required_sections is absent (adopt-existing style), check passes trivially."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    # Write baseline.yaml WITHOUT plan_required_sections (adopt-existing scenario)
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: 1.0.0\n"
        f"source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        f"framework_root: {FRAMEWORK_ROOT}\n"
        f"initialized_at: 2026-03-21T10:00:00Z\n"
        f"initialized_by: scripts/init-governance.sh\n"
        f"sha256.AGENTS.base.md: {_compute_hash(agents)}\n"
        f"sha256.PLAN.md: {_compute_hash(plan)}\n"
        f"sha256.contract.yaml: {_compute_hash(contract)}\n"
        f"overridable.AGENTS.base.md: protected\n"
        f"overridable.PLAN.md: overridable\n"
        f"overridable.contract.yaml: overridable\n"
        f"contract_required_fields:\n"
        f"  - name\n"
        f"  - framework_interface_version\n"
        f"  - framework_compatible\n"
        f"  - domain\n"
        f"plan_section_inventory:\n"
        f"  - \"## 🏗️ 當前階段\"\n"
        f"  - \"## 🔥 本輪聚焦\"\n"
        # NO plan_required_sections
    )
    gov_dir = tmp_path / ".governance"
    gov_dir.mkdir(exist_ok=True)
    (gov_dir / "baseline.yaml").write_text(text, encoding="utf-8")

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert result.checks["plan_required_sections_present"] is True  # trivial pass
    assert result.severity in {"ok", "warning"}


def test_plan_section_inventory_surfaced_in_result(tmp_path):
    """plan_section_inventory from baseline.yaml is surfaced in result."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: 1.0.0\n"
        f"source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        f"initialized_at: 2026-03-21T10:00:00Z\n"
        f"sha256.AGENTS.base.md: {_compute_hash(agents)}\n"
        f"sha256.PLAN.md: {_compute_hash(plan)}\n"
        f"sha256.contract.yaml: {_compute_hash(contract)}\n"
        f"overridable.AGENTS.base.md: protected\n"
        f"overridable.PLAN.md: overridable\n"
        f"overridable.contract.yaml: overridable\n"
        f"contract_required_fields:\n"
        f"  - name\n"
        f"  - framework_interface_version\n"
        f"  - framework_compatible\n"
        f"  - domain\n"
        f"plan_section_inventory:\n"
        f"  - \"## 🏗️ 當前階段\"\n"
        f"  - \"## 🔥 本輪聚焦\"\n"
        f"  - \"## 📦 Phase 詳細規劃\"\n"
    )
    gov_dir = tmp_path / ".governance"
    gov_dir.mkdir(exist_ok=True)
    (gov_dir / "baseline.yaml").write_text(text, encoding="utf-8")

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert len(result.plan_section_inventory) == 3
    assert "## 🏗️ 當前階段" in result.plan_section_inventory
    assert "## 🔥 本輪聚焦" in result.plan_section_inventory


def test_adopt_existing_style_repo_passes(tmp_path):
    """Repo adopted via --adopt-existing (inventory only, no mandate) passes with no section failures."""
    chinese_sections = [
        "## 📋 專案目標",
        "## 🏗️ 當前階段",
        "## 🔥 本輪聚焦",
        "## 📦 Phase 詳細規劃",
        "## 🎯 當前決策",
        "## 🚫 現階段不要做",
        "## 📝 變更歷史",
    ]
    agents = _write_agents_base(tmp_path)
    plan = _write_plan_custom(tmp_path, chinese_sections)
    contract = _write_contract(tmp_path)
    # Write baseline.yaml with only plan_section_inventory (no plan_required_sections)
    inventory_block = "plan_section_inventory:\n" + "".join(
        f'  - "{s}"\n' for s in chinese_sections
    )
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: 1.0.0\n"
        f"source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        f"initialized_at: 2026-03-21T10:00:00Z\n"
        f"sha256.AGENTS.base.md: {_compute_hash(agents)}\n"
        f"sha256.PLAN.md: {_compute_hash(plan)}\n"
        f"sha256.contract.yaml: {_compute_hash(contract)}\n"
        f"overridable.AGENTS.base.md: protected\n"
        f"overridable.PLAN.md: overridable\n"
        f"overridable.contract.yaml: overridable\n"
        f"contract_required_fields:\n"
        f"  - name\n"
        f"  - framework_interface_version\n"
        f"  - framework_compatible\n"
        f"  - domain\n"
        + inventory_block
    )
    gov_dir = tmp_path / ".governance"
    gov_dir.mkdir(exist_ok=True)
    (gov_dir / "baseline.yaml").write_text(text, encoding="utf-8")

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert result.checks["plan_required_sections_present"] is True  # trivial pass
    assert result.checks["baseline_yaml_present"] is True
    assert result.checks["source_commit_recorded"] is True
    assert len(result.plan_section_inventory) == len(chinese_sections)
    assert result.severity in {"ok", "warning"}


def test_default_plan_required_sections_pass_fresh_init_repo(tmp_path):
    """Fresh-init repo with English defaults in plan_required_sections passes."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)  # has ## Current Phase / ## Active Sprint / ## Backlog
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )

    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)

    assert result.checks["plan_required_sections_present"] is True


# ── contract_no_placeholders ──────────────────────────────────────────────────

def test_contract_no_placeholders_passes_for_filled_contract(tmp_path):
    """contract.yaml with real values passes the placeholder check."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)  # name=test-contract, domain=test — no <...>
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_no_placeholders") is True


def test_contract_no_placeholders_fails_for_template_contract(tmp_path):
    """contract.yaml with <repo-name>/<domain> placeholder values is a warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        "name: <repo-name>-contract\n"
        "plugin_version: \"1.0.0\"\n"
        "framework_interface_version: \"1\"\n"
        "framework_compatible: \">=1.0.0,<2.0.0\"\n"
        "domain: <domain>\n"
        "documents:\n"
        "  - AGENTS.base.md\n"
        "ai_behavior_override:\n"
        "  - AGENTS.base.md\n"
        "validators:\n",
        encoding="utf-8",
    )
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_no_placeholders") is False
    assert any("name" in w and "domain" in w for w in result.warnings)


def test_contract_no_placeholders_not_present_when_contract_missing(tmp_path):
    """When contract.yaml is absent, contract_no_placeholders is not in checks."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash="0" * 64,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_required_fields_present") is False
    assert "contract_no_placeholders" not in result.checks


# ── agents_sections_filled ────────────────────────────────────────────────────

def _write_agents_md_template(repo: Path) -> Path:
    """Write the unmodified baseline AGENTS.md template (all sections empty)."""
    import shutil
    src = Path(__file__).parent.parent / "baselines" / "repo-min" / "AGENTS.md"
    dst = repo / "AGENTS.md"
    shutil.copy(src, dst)
    return dst


def _write_agents_md_filled(repo: Path) -> Path:
    """Write an AGENTS.md with all governance:key sections populated."""
    text = (
        "# AGENTS.md\n"
        "<!-- governance-baseline: overridable -->\n\n"
        "## Repo-Specific Risk Levels\n"
        "<!-- governance:key=risk_levels -->\n\n"
        "- HIGH: changes to auth paths\n"
        "- LOW: docs-only changes\n\n"
        "## Must-Test Paths\n"
        "<!-- governance:key=must_test_paths -->\n\n"
        "- src/auth/ requires integration tests\n\n"
        "## L1 → L2 Escalation Triggers\n"
        "<!-- governance:key=escalation_triggers -->\n\n"
        "- Any schema migration\n\n"
        "## Repo-Specific Forbidden Behaviors\n"
        "<!-- governance:key=forbidden_behaviors -->\n\n"
        "- Do not commit .env files\n"
    )
    p = repo / "AGENTS.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_agents_sections_filled_passes_when_content_present(tmp_path):
    """AGENTS.md with real content in all governance:key sections passes."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_agents_md_filled(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("agents_sections_filled") is True


def test_agents_sections_filled_fails_for_template_agents_md(tmp_path):
    """Unmodified baseline AGENTS.md (all sections empty) is a warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_agents_md_template(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("agents_sections_filled") is False
    assert any("risk_levels" in w for w in result.warnings)


def test_agents_sections_filled_passes_when_agents_md_absent(tmp_path):
    """Missing AGENTS.md is not penalised — check passes (file is optional)."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("agents_sections_filled") is True


def test_agents_sections_partially_filled_reports_empty_keys(tmp_path):
    """Only sections that are still empty appear in the warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)
    text = (
        "# AGENTS.md\n\n"
        "## Repo-Specific Risk Levels\n"
        "<!-- governance:key=risk_levels -->\n\n"
        "- HIGH: auth changes\n\n"
        "## Must-Test Paths\n"
        "<!-- governance:key=must_test_paths -->\n\n"
        "<!-- List modules here -->\n"
    )
    (tmp_path / "AGENTS.md").write_text(text, encoding="utf-8")
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("agents_sections_filled") is False
    warning_text = " ".join(result.warnings)
    assert "must_test_paths" in warning_text
    assert "risk_levels" not in warning_text


# ── plan_inventory_current ────────────────────────────────────────────────────

def _write_baseline_yaml_with_inventory(
    repo: Path,
    agents_hash: str,
    plan_hash: str,
    contract_hash: str,
    inventory_sections: list[str],
) -> Path:
    """Write baseline.yaml with an explicit plan_section_inventory."""
    sections_block = "".join(f'  - "{s}"\n' for s in inventory_sections)
    text = (
        f'schema_version: "1"\n'
        f'baseline_version: 1.0.0\n'
        f'source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n'
        f'framework_root: {FRAMEWORK_ROOT}\n'
        f'initialized_at: 2026-03-22T00:00:00Z\n'
        f'initialized_by: scripts/init-governance.sh\n'
        f'sha256.AGENTS.base.md: {agents_hash}\n'
        f'sha256.PLAN.md: {plan_hash}\n'
        f'sha256.contract.yaml: {contract_hash}\n'
        f'overridable.AGENTS.base.md: protected\n'
        f'overridable.PLAN.md: overridable\n'
        f'overridable.contract.yaml: overridable\n'
        f'contract_required_fields:\n'
        f'  - name\n  - framework_interface_version\n  - framework_compatible\n  - domain\n'
        f'plan_required_sections:\n'
        f'  - "## Current Phase"\n  - "## Active Sprint"\n  - "## Backlog"\n'
        f'plan_section_inventory:\n{sections_block}'
    )
    gov_dir = repo / ".governance"
    gov_dir.mkdir(exist_ok=True)
    p = gov_dir / "baseline.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_plan_inventory_current_passes_when_inventory_matches(tmp_path):
    """Recorded inventory matches current PLAN.md headings — check passes."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)  # has ## Current Phase, ## Active Sprint, ## Backlog
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_inventory(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        inventory_sections=["## Current Phase", "## Active Sprint", "## Backlog"],
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_inventory_current") is True


def test_plan_inventory_current_fails_when_section_removed(tmp_path):
    """Inventory has a section that was later removed from PLAN.md — warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)  # has ## Current Phase, ## Active Sprint, ## Backlog
    contract = _write_contract(tmp_path)
    # Inventory records an extra section that no longer exists
    _write_baseline_yaml_with_inventory(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        inventory_sections=["## Current Phase", "## Active Sprint", "## Backlog", "## Old Section"],
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_inventory_current") is False
    warning_text = " ".join(result.warnings)
    assert "Old Section" in warning_text
    assert "refresh-baseline" in " ".join(result.remediation_hints)


def test_plan_inventory_current_fails_when_section_added(tmp_path):
    """PLAN.md gained a new section not in inventory — warning."""
    agents = _write_agents_base(tmp_path)
    # PLAN.md has an extra section beyond what inventory recorded
    plan_text = (
        "# PLAN.md\n\n"
        "> **最後更新**: 2026-03-22\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\nwork\n\n"
        "## Active Sprint\n\ntasks\n\n"
        "## Backlog\n\nitems\n\n"
        "## New Section\n\nnewly added\n"
    )
    plan = tmp_path / "PLAN.md"
    plan.write_text(plan_text, encoding="utf-8")
    contract = _write_contract(tmp_path)
    agents_p = tmp_path / "AGENTS.base.md"
    agents_p.write_bytes(agents.read_bytes() if agents.exists() else b"")
    _write_baseline_yaml_with_inventory(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        inventory_sections=["## Current Phase", "## Active Sprint", "## Backlog"],
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_inventory_current") is False
    warning_text = " ".join(result.warnings)
    assert "New Section" in warning_text


def test_plan_inventory_current_passes_when_both_empty(tmp_path):
    """Empty inventory + PLAN.md with no ## sections — both empty, no drift."""
    agents = _write_agents_base(tmp_path)
    plan = tmp_path / "PLAN.md"
    plan.write_text("# PLAN\n\n> **最後更新**: 2026-03-22\n\nSome prose, no ## headings.\n",
                    encoding="utf-8")
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_inventory(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        inventory_sections=[],
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_inventory_current") is True


# ── contract_not_framework_copy ───────────────────────────────────────────────

def test_contract_not_framework_copy_passes_for_distinct_contract(tmp_path):
    """contract.yaml with a different name than the framework's own passes."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = _write_contract(tmp_path)  # name=test-contract — distinct from framework
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_not_framework_copy") is True


def test_contract_not_framework_copy_fails_when_name_matches_framework(tmp_path):
    """contract.yaml whose name matches the framework's own contract is a warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    fw_contract_text = (FRAMEWORK_ROOT / "contract.yaml").read_text(encoding="utf-8")
    contract = tmp_path / "contract.yaml"
    contract.write_text(fw_contract_text, encoding="utf-8")
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("contract_not_framework_copy") is False
    assert any("name" in w for w in result.warnings)


def test_contract_not_framework_copy_passes_when_repo_is_framework(tmp_path):
    """When repo_root == framework_root the check passes (framework validates itself)."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)
    contract = tmp_path / "contract.yaml"
    contract.write_text(
        (FRAMEWORK_ROOT / "contract.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write_baseline_yaml(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
    )
    result = check_governance_drift(tmp_path, framework_root=tmp_path, skip_hash=True)
    assert result.checks.get("contract_not_framework_copy") is True


# ── plan_freshness_threshold_days CONTRACT override ───────────────────────────

def _write_stale_plan(repo: Path, days_old: int = 10) -> Path:
    """Write a PLAN.md that is *days_old* days old with no explicit Freshness header."""
    from datetime import date, timedelta
    last_updated = (date.today() - timedelta(days=days_old)).isoformat()
    text = (
        "# PLAN.md\n"
        "<!-- governance-baseline: overridable -->\n\n"
        f"> **最後更新**: {last_updated}\n"
        "> **Owner**: Test\n\n"
        "## Current Phase\n\n- [ ] Phase A\n\n"
        "## Active Sprint\n\n- [ ] Task 1\n\n"
        "## Backlog\n\n- P1: none\n"
    )
    p = repo / "PLAN.md"
    p.write_text(text, encoding="utf-8")
    return p


def _write_baseline_yaml_with_freshness_override(
    repo: Path,
    agents_hash: str,
    plan_hash: str,
    contract_hash: str,
    freshness_threshold_days: int | None = None,
) -> Path:
    """Write baseline.yaml with optional plan_freshness_threshold_days override."""
    override_line = (
        f"plan_freshness_threshold_days: {freshness_threshold_days}\n"
        if freshness_threshold_days is not None
        else ""
    )
    text = (
        f'schema_version: "1"\n'
        f'baseline_version: 1.0.0\n'
        f'source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n'
        f'framework_root: {FRAMEWORK_ROOT}\n'
        f'initialized_at: 2026-03-22T00:00:00Z\n'
        f'initialized_by: scripts/init-governance.sh\n'
        f'sha256.AGENTS.base.md: {agents_hash}\n'
        f'sha256.PLAN.md: {plan_hash}\n'
        f'sha256.contract.yaml: {contract_hash}\n'
        f'overridable.AGENTS.base.md: protected\n'
        f'overridable.PLAN.md: overridable\n'
        f'overridable.contract.yaml: overridable\n'
        f'contract_required_fields:\n'
        f'  - name\n  - framework_interface_version\n  - framework_compatible\n  - domain\n'
        f'plan_required_sections:\n'
        f'  - "## Current Phase"\n  - "## Active Sprint"\n  - "## Backlog"\n'
        f'plan_section_inventory:\n'
        f'  - "## Current Phase"\n  - "## Active Sprint"\n  - "## Backlog"\n'
        + override_line
    )
    gov_dir = repo / ".governance"
    gov_dir.mkdir(exist_ok=True)
    p = gov_dir / "baseline.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_plan_freshness_override_relaxes_threshold(tmp_path):
    """plan_freshness_threshold_days: 30 allows a 10-day-old PLAN to pass."""
    agents = _write_agents_base(tmp_path)
    plan = _write_stale_plan(tmp_path, days_old=10)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=30,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_freshness") is True


def test_plan_freshness_override_tightens_threshold(tmp_path):
    """plan_freshness_threshold_days: 3 fails a 5-day-old PLAN that would otherwise pass framework default 14d."""
    agents = _write_agents_base(tmp_path)
    plan = _write_stale_plan(tmp_path, days_old=5)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=3,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_freshness") is False
    warning_text = " ".join(result.warnings)
    assert "contract override: 3d" in warning_text


def test_plan_freshness_override_visible_in_warning(tmp_path):
    """When override is active, warning message names the source as 'contract override'."""
    agents = _write_agents_base(tmp_path)
    plan = _write_stale_plan(tmp_path, days_old=10)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=5,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    assert result.checks.get("plan_freshness") is False
    warning_text = " ".join(result.warnings)
    assert "contract override: 5d" in warning_text


def test_plan_freshness_no_override_uses_plan_policy(tmp_path):
    """Without override, threshold comes from PLAN.md Freshness header (Sprint = 7d)."""
    agents = _write_agents_base(tmp_path)
    plan = _write_plan(tmp_path)  # has Freshness: Sprint (7d), dated 2026-03-21
    contract = _write_contract(tmp_path)
    # No override — threshold_days should come from PLAN.md policy
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=None,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    # plan is dated 2026-03-21 (1 day ago), Sprint 7d — should be FRESH
    assert result.checks.get("plan_freshness") is True


def test_plan_freshness_no_override_no_plan_policy_uses_framework_default(tmp_path):
    """No override and no PLAN.md Freshness header — uses framework default (14d)."""
    agents = _write_agents_base(tmp_path)
    # _write_stale_plan writes a PLAN.md with no Freshness header, 10 days old
    plan = _write_stale_plan(tmp_path, days_old=10)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=None,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    # 10 days old, framework default 14d → FRESH
    assert result.checks.get("plan_freshness") is True


def test_plan_freshness_override_above_default_emits_warning(tmp_path):
    """Override > framework default (14d) emits a guardrail warning."""
    agents = _write_agents_base(tmp_path)
    plan = _write_stale_plan(tmp_path, days_old=10)
    contract = _write_contract(tmp_path)
    _write_baseline_yaml_with_freshness_override(
        tmp_path,
        agents_hash=_compute_hash(agents),
        plan_hash=_compute_hash(plan),
        contract_hash=_compute_hash(contract),
        freshness_threshold_days=30,
    )
    result = check_governance_drift(tmp_path, framework_root=FRAMEWORK_ROOT, skip_hash=True)
    warning_text = " ".join(result.warnings)
    assert "threshold override" in warning_text
    assert "30" in warning_text
    assert "14" in warning_text  # framework default visible in warning
