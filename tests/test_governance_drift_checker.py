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
) -> Path:
    text = (
        f"schema_version: \"1\"\n"
        f"baseline_version: {baseline_version}\n"
        f"source_commit: abc1234\n"
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
