#!/usr/bin/env python3
"""
Tests for governance_tools/adopt_governance.py
"""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.adopt_governance import (
    adopt_existing,
    refresh_baseline,
    _discover_plan_path,
    _read_baseline_state,
)

FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()
BASELINE_SOURCE = FRAMEWORK_ROOT / "baselines" / "repo-min"
FIXTURE_ROOT = Path("tests/_tmp_adopt_governance")


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_git_repo(path: Path) -> Path:
    """Create a minimal git repo structure."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir(exist_ok=True)
    (path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return path


def _reset_fixture(name: str) -> Path:
    root = FIXTURE_ROOT / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_plan(repo: Path, content: str | None = None) -> Path:
    text = content or (
        "# PLAN.md\n\n"
        "> **最後更新**: 2026-03-21\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n- Phase A\n\n"
        "## Active Sprint\n\n- Task 1\n\n"
        "## Backlog\n\n- none\n"
    )
    p = repo / "PLAN.md"
    p.write_text(text, encoding="utf-8")
    return p


def _write_contract(repo: Path) -> Path:
    text = (
        "name: test-repo\n"
        'plugin_version: "1.0.0"\n'
        'framework_interface_version: "1"\n'
        'framework_compatible: ">=1.0.0,<2.0.0"\n'
        "domain: test\n"
        "documents:\n  - AGENTS.base.md\n  - PLAN.md\n"
        "  - governance/TESTING.md\n  - governance/ARCHITECTURE.md\n"
        "ai_behavior_override:\n  - AGENTS.base.md\n"
        "validators:\n"
    )
    p = repo / "contract.yaml"
    p.write_text(text, encoding="utf-8")
    return p


# ── _discover_plan_path ───────────────────────────────────────────────────────

def test_discover_plan_path_finds_root_plan(tmp_path):
    _write_plan(tmp_path)
    result = _discover_plan_path(tmp_path)
    assert result == tmp_path / "PLAN.md"


def test_discover_plan_path_finds_governance_subdir(tmp_path):
    sub = tmp_path / "governance"
    sub.mkdir()
    (sub / "PLAN.md").write_text("# PLAN\n", encoding="utf-8")
    result = _discover_plan_path(tmp_path)
    assert result == sub / "PLAN.md"


def test_discover_plan_path_returns_none_when_absent(tmp_path):
    result = _discover_plan_path(tmp_path)
    assert result is None


def test_discover_plan_path_prefers_root_over_subdir(tmp_path):
    _write_plan(tmp_path)
    sub = tmp_path / "governance"
    sub.mkdir()
    (sub / "PLAN.md").write_text("# OTHER\n", encoding="utf-8")
    result = _discover_plan_path(tmp_path)
    assert result == tmp_path / "PLAN.md"


# ── adopt_existing ────────────────────────────────────────────────────────────

def test_adopt_copies_agents_base(tmp_path):
    """AGENTS.base.md is always copied from framework baseline."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)

    rc = adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 0
    assert (repo / "AGENTS.base.md").exists()
    assert "governance-baseline: protected" in (repo / "AGENTS.base.md").read_text(encoding="utf-8")


def test_adopt_creates_contract_from_template_when_missing(tmp_path):
    """contract.yaml created from template when not present."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)

    rc = adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 0
    assert (repo / "contract.yaml").exists()


def test_adopt_keeps_existing_contract(tmp_path):
    """Existing contract.yaml is never overwritten."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    contract = _write_contract(repo)
    original = contract.read_text(encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert contract.read_text(encoding="utf-8") == original


def test_adopt_repairs_existing_contract_with_missing_agents_base_reference():
    """Existing contract.yaml keeps custom content but gains AGENTS.base.md reference."""
    repo = _make_git_repo(_reset_fixture("repair_contract_reference") / "repo")
    _write_plan(repo)
    contract = repo / "contract.yaml"
    contract.write_text(
        "name: test-repo\n"
        'plugin_version: "1.0.0"\n'
        'framework_interface_version: "1"\n'
        'framework_compatible: ">=1.0.0,<2.0.0"\n'
        "domain: test\n"
        "documents:\n  - PLAN.md\n"
        "ai_behavior_override:\n  - governance_project/AGENTS.md\n"
        "validators:\n",
        encoding="utf-8",
    )

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    repaired = contract.read_text(encoding="utf-8")
    assert "  - governance_project/AGENTS.md" in repaired
    assert "  - AGENTS.base.md" in repaired


def test_adopt_dry_run_does_not_repair_existing_contract():
    """Dry-run reports the repair but does not mutate contract.yaml."""
    repo = _make_git_repo(_reset_fixture("dry_run_contract_reference") / "repo")
    _write_plan(repo)
    contract = repo / "contract.yaml"
    original = (
        "name: test-repo\n"
        'plugin_version: "1.0.0"\n'
        'framework_interface_version: "1"\n'
        'framework_compatible: ">=1.0.0,<2.0.0"\n'
        "domain: test\n"
        "documents:\n  - PLAN.md\n"
        "ai_behavior_override:\n  - governance_project/AGENTS.md\n"
        "validators:\n"
    )
    contract.write_text(original, encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=True)

    assert contract.read_text(encoding="utf-8") == original


def test_adopt_creates_agents_md_from_template_when_missing(tmp_path):
    """AGENTS.md created from template when not present."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert (repo / "AGENTS.md").exists()


def test_adopt_creates_minimal_memory_scaffold():
    """Adopt seeds the minimum memory schema for new repos."""
    repo = _make_git_repo(_reset_fixture("minimal_memory_scaffold") / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert (repo / "memory" / "01_active_task.md").exists()
    assert (repo / "memory" / "02_tech_stack.md").exists()
    assert (repo / "memory" / "03_knowledge_base.md").exists()
    assert (repo / "memory" / "04_review_log.md").exists()


def test_adopt_copies_governance_markdown_pack():
    """Adopt should seed the canonical governance markdown pack for consuming repos."""
    repo = _make_git_repo(_reset_fixture("governance_markdown_pack") / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert (repo / "governance" / "AGENT.md").exists()
    assert (repo / "governance" / "SYSTEM_PROMPT.md").exists()
    assert (repo / "governance" / "TESTING.md").exists()
    assert (repo / "governance" / "PLAN.md").exists() is False


def test_adopt_keeps_existing_governance_markdown_pack_file():
    """Existing governance markdown files must not be overwritten during adopt."""
    repo = _make_git_repo(_reset_fixture("governance_markdown_pack_kept") / "repo")
    _write_plan(repo)
    _write_contract(repo)
    gov_dir = repo / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)
    custom = gov_dir / "AGENT.md"
    custom.write_text("# Custom governance agent\n", encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert custom.read_text(encoding="utf-8") == "# Custom governance agent\n"


def test_adopt_repairs_existing_contract_with_missing_governance_documents():
    """Existing contract.yaml should gain required governance documents when missing."""
    repo = _make_git_repo(_reset_fixture("repair_contract_governance_docs") / "repo")
    _write_plan(repo)
    contract = repo / "contract.yaml"
    contract.write_text(
        "\n".join(
            [
                "name: demo-contract",
                "plugin_version: \"1.0.0\"",
                "framework_interface_version: \"1\"",
                "framework_compatible: \">=1.0.0,<2.0.0\"",
                "domain: demo",
                "documents:",
                "  - AGENTS.base.md",
                "  - PLAN.md",
                "ai_behavior_override:",
                "  - AGENTS.base.md",
                "rule_roots:",
                "  - governance/rules",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    content = contract.read_text(encoding="utf-8")
    assert "  - governance/TESTING.md" in content
    assert "  - governance/ARCHITECTURE.md" in content


def test_adopt_copies_governance_rules_pack():
    """Adopt should seed the canonical governance rules pack for consuming repos."""
    repo = _make_git_repo(_reset_fixture("governance_rules_pack") / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert (repo / "governance" / "rules" / "python" / "coding.md").exists()


def test_adopt_keeps_existing_governance_rule_file():
    """Existing governance rule files must not be overwritten during adopt."""
    repo = _make_git_repo(_reset_fixture("governance_rules_pack_kept") / "repo")
    _write_plan(repo)
    _write_contract(repo)
    rule_dir = repo / "governance" / "rules" / "python"
    rule_dir.mkdir(parents=True, exist_ok=True)
    custom = rule_dir / "coding.md"
    custom.write_text("# Custom coding rule\n", encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert custom.read_text(encoding="utf-8") == "# Custom coding rule\n"


def test_adopt_creates_governance_drift_workflow_when_missing():
    """Adopt should seed the minimal drift workflow for new repos."""
    repo = _make_git_repo(_reset_fixture("drift_workflow_created") / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    workflow = repo / ".github" / "workflows" / "governance-drift.yml"
    assert workflow.exists()
    content = workflow.read_text(encoding="utf-8")
    assert "governance_drift_checker.py" in content
    assert "--framework-root governance" in content


def test_adopt_keeps_existing_governance_drift_workflow():
    """Adopt should not overwrite a repo's existing drift workflow."""
    repo = _make_git_repo(_reset_fixture("drift_workflow_kept") / "repo")
    _write_plan(repo)
    _write_contract(repo)
    workflow = repo / ".github" / "workflows" / "governance-drift.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("# custom workflow\n", encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert workflow.read_text(encoding="utf-8") == "# custom workflow\n"


def test_adopt_surfaces_repo_specific_agents_prompts_in_next_steps(capsys):
    """Adopt should point out template AGENTS.md sections that are still uncustomized."""
    repo = _make_git_repo(_reset_fixture("agents_prompt_summary") / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)
    output = capsys.readouterr().out

    assert "Repo-specific AGENTS.md sections still worth filling:" in output
    assert "risk_levels" in output
    assert "must_test_paths" in output
    assert "escalation_triggers" in output
    assert "forbidden_behaviors" in output


def test_adopt_keeps_existing_agents_md(tmp_path):
    """Existing AGENTS.md is never overwritten."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)
    agents = repo / "AGENTS.md"
    agents.write_text("# Custom AGENTS\n", encoding="utf-8")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert agents.read_text(encoding="utf-8") == "# Custom AGENTS\n"


def test_adopt_creates_plan_from_template_when_missing(tmp_path):
    """PLAN.md created from template when no PLAN.md found anywhere."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert (repo / "PLAN.md").exists()


def test_adopt_writes_baseline_yaml(tmp_path):
    """baseline.yaml is always written after adoption."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    baseline = repo / ".governance" / "baseline.yaml"
    assert baseline.exists()
    content = baseline.read_text(encoding="utf-8")
    assert "schema_version" in content
    assert "sha256.AGENTS.base.md" in content
    assert "initialized_by: governance_tools/adopt_governance.py" in content


def test_adopt_baseline_has_plan_inventory(tmp_path):
    """baseline.yaml records plan_section_inventory when PLAN.md has sections."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    content = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")
    assert "plan_section_inventory" in content
    assert "## Current Phase" in content


def test_adopt_baseline_no_plan_required_sections(tmp_path):
    """adopt-existing never sets plan_required_sections (no mandate imposed)."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    content = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")
    # plan_required_sections must not appear as a YAML key (only as comment text)
    for line in content.splitlines():
        if not line.strip().startswith("#"):
            assert not line.startswith("plan_required_sections:"), (
                "adopt-existing must not impose plan_required_sections"
            )


def test_adopt_records_nonstandard_plan_path(tmp_path):
    """When PLAN.md is in a subdirectory, plan_path is recorded in baseline."""
    repo = _make_git_repo(tmp_path / "repo")
    gov_dir = repo / "governance"
    gov_dir.mkdir()
    (gov_dir / "PLAN.md").write_text(
        "> **最後更新**: 2026-03-21\n> **Owner**: Test\n## Phase A\n",
        encoding="utf-8",
    )
    _write_contract(repo)

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    content = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")
    assert "plan_path: governance/PLAN.md" in content


def test_adopt_dry_run_writes_nothing(tmp_path):
    """--dry-run must not create or modify any files."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)
    files_before = set(repo.rglob("*"))

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=True)

    files_after = set(repo.rglob("*"))
    # Only .git internals may differ; no governance files written
    new_files = {f for f in (files_after - files_before) if ".git" not in str(f)}
    assert not new_files, f"dry-run wrote files: {new_files}"


def test_adopt_fails_gracefully_without_git_dir(tmp_path):
    """Returns exit code 1 when target is not a git repo."""
    repo = tmp_path / "not-a-git-repo"
    repo.mkdir()

    rc = adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 1


def test_adopt_fails_gracefully_with_missing_baseline_source(tmp_path):
    """Returns exit code 1 when framework root has no baselines/repo-min."""
    repo = _make_git_repo(tmp_path / "repo")
    fake_framework = tmp_path / "fake-framework"
    fake_framework.mkdir()

    rc = adopt_existing(repo, fake_framework, dry_run=False)

    assert rc == 1


# ── refresh_baseline ──────────────────────────────────────────────────────────

def _adopt_repo(tmp_path: Path) -> Path:
    """Create a fully adopted repo for refresh tests."""
    repo = _make_git_repo(tmp_path / "repo")
    _write_plan(repo)
    _write_contract(repo)
    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)
    return repo


def test_refresh_updates_hashes(tmp_path):
    """--refresh rewrites baseline.yaml with updated hashes after file change."""
    repo = _adopt_repo(tmp_path)
    baseline_before = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")

    # Modify PLAN.md to trigger a hash change
    (repo / "PLAN.md").write_text(
        "> **最後更新**: 2026-03-22\n> **Owner**: Updated\n> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n- Phase B\n\n"
        "## Active Sprint\n\n- Task 2\n\n"
        "## Backlog\n\n- none\n",
        encoding="utf-8",
    )

    rc = refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 0
    baseline_after = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")
    assert baseline_before != baseline_after


def test_refresh_preserves_plan_required_sections(tmp_path):
    """--refresh preserves plan_required_sections from existing baseline."""
    repo = _adopt_repo(tmp_path)

    # Manually add plan_required_sections to baseline
    baseline_path = repo / ".governance" / "baseline.yaml"
    content = baseline_path.read_text(encoding="utf-8")
    content += 'plan_required_sections:\n  - "## Custom Section"\n'
    baseline_path.write_text(content, encoding="utf-8")

    rc = refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 0
    refreshed = baseline_path.read_text(encoding="utf-8")
    assert "## Custom Section" in refreshed


def test_refresh_updates_inventory(tmp_path):
    """--refresh detects new PLAN.md sections added after adoption."""
    repo = _adopt_repo(tmp_path)

    # Add a new section to PLAN.md
    plan = repo / "PLAN.md"
    plan.write_text(
        plan.read_text(encoding="utf-8") + "\n## New Section\n\n- item\n",
        encoding="utf-8",
    )

    refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)

    content = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")
    assert "## New Section" in content


def test_refresh_reports_changed_tracked_hashes(capsys):
    """Refresh should summarize which tracked files changed."""
    repo = _adopt_repo(_reset_fixture("refresh_hash_delta"))
    (repo / "AGENTS.md").write_text("# Custom AGENTS\n", encoding="utf-8")

    refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)
    output = capsys.readouterr().out

    assert "Refresh delta summary:" in output
    assert "tracked hash changes: AGENTS.md" in output


def test_refresh_reports_plan_inventory_delta(capsys):
    """Refresh should summarize added or removed PLAN headings."""
    repo = _adopt_repo(_reset_fixture("refresh_inventory_delta"))
    plan = repo / "PLAN.md"
    plan.write_text(plan.read_text(encoding="utf-8") + "\n## New Section\n\n- item\n", encoding="utf-8")

    refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)
    output = capsys.readouterr().out

    assert "Refresh delta summary:" in output
    assert "plan sections added: ## New Section" in output


def test_refresh_does_not_copy_template_files(tmp_path):
    """--refresh must not copy AGENTS.md, contract.yaml, or PLAN.md templates."""
    repo = _adopt_repo(tmp_path)

    # Delete AGENTS.md to verify refresh does NOT recreate it
    (repo / "AGENTS.md").unlink()

    refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)

    assert not (repo / "AGENTS.md").exists(), "--refresh must not copy template files"


def test_refresh_fails_without_baseline(tmp_path):
    """--refresh returns exit code 1 when no baseline.yaml exists."""
    repo = _make_git_repo(tmp_path / "repo")

    rc = refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=False)

    assert rc == 1


def test_refresh_dry_run_writes_nothing(tmp_path):
    """--refresh --dry-run must not modify any files."""
    repo = _adopt_repo(tmp_path)
    baseline_before = (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8")

    rc = refresh_baseline(repo, FRAMEWORK_ROOT, dry_run=True)

    assert rc == 0
    assert (repo / ".governance" / "baseline.yaml").read_text(encoding="utf-8") == baseline_before


def test_read_baseline_state_reads_plan_path(tmp_path):
    """_read_baseline_state returns plan_rel from baseline plan_path key."""
    repo = _make_git_repo(tmp_path / "repo")
    gov_dir = repo / ".governance"
    gov_dir.mkdir()
    (gov_dir / "baseline.yaml").write_text(
        'schema_version: "1"\nplan_path: governance/PLAN.md\n',
        encoding="utf-8",
    )

    state = _read_baseline_state(repo)
    assert state["plan_rel"] == "governance/PLAN.md"


def test_read_baseline_state_defaults_plan_path(tmp_path):
    """_read_baseline_state defaults to PLAN.md when plan_path absent."""
    repo = _make_git_repo(tmp_path / "repo")
    gov_dir = repo / ".governance"
    gov_dir.mkdir()
    (gov_dir / "baseline.yaml").write_text('schema_version: "1"\n', encoding="utf-8")

    state = _read_baseline_state(repo)
    assert state["plan_rel"] == "PLAN.md"


def test_read_baseline_state_reads_required_sections(tmp_path):
    """_read_baseline_state reads plan_required_sections list."""
    repo = _make_git_repo(tmp_path / "repo")
    gov_dir = repo / ".governance"
    gov_dir.mkdir()
    (gov_dir / "baseline.yaml").write_text(
        'schema_version: "1"\nplan_required_sections:\n  - "## Phase"\n  - "## Sprint"\n',
        encoding="utf-8",
    )

    state = _read_baseline_state(repo)
    assert state["required"] == ["## Phase", "## Sprint"]


def test_adopt_contract_template_has_no_placeholders(tmp_path):
    """contract.yaml from template must have repo-slug substituted, no <...> tokens."""
    repo = _make_git_repo(tmp_path / "my-service")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    contract_text = (repo / "contract.yaml").read_text(encoding="utf-8")
    import re
    placeholders = re.findall(r"<[^>]+>", contract_text)
    assert not placeholders, f"contract.yaml still contains placeholder(s): {placeholders}"
    assert "my-service" in contract_text


def test_adopt_plan_template_has_no_date_placeholder(tmp_path):
    """PLAN.md from template must have today's date, not YYYY-MM-DD."""
    repo = _make_git_repo(tmp_path / "repo")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    plan_text = (repo / "PLAN.md").read_text(encoding="utf-8")
    assert "YYYY-MM-DD" not in plan_text
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", plan_text), "PLAN.md must contain an ISO date"


def test_adopt_minimal_repo_drift_ok(tmp_path):
    """Empty git repo + adopt should produce drift ok=True (no critical failures)."""
    repo = _make_git_repo(tmp_path / "empty-repo")

    adopt_existing(repo, FRAMEWORK_ROOT, dry_run=False)

    from governance_tools.governance_drift_checker import check_governance_drift
    result = check_governance_drift(repo, framework_root=FRAMEWORK_ROOT)
    assert result.ok is True, (
        f"adopt on empty repo must yield ok=True; failed: "
        f"{[k for k, v in result.checks.items() if v is False]}"
    )
