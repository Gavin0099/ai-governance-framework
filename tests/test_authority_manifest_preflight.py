import json
import subprocess
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.authority_manifest import build_authority_manifest, manifest_to_dict
from governance_tools.authority_manifest_preflight import (
    assess_manifest_path,
    assess_manifest_payload,
    build_generated_receipt,
)

FRAMEWORK_ROOT = Path(__file__).parent.parent


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


def _commit(repo: Path, message: str) -> str:
    _run(repo, "-c", "user.name=Test User", "-c", "user.email=test@example.invalid", "add", ".")
    _run(repo, "-c", "user.name=Test User", "-c", "user.email=test@example.invalid", "commit", "-m", message)
    return _run(repo, "rev-parse", "--short", "HEAD").stdout.strip()


def _write_minimal_repo(repo: Path) -> None:
    _run(repo, "init")
    _run(repo, "config", "core.autocrlf", "false")
    (repo / "memory").mkdir()
    for name in ("01_active_task.md", "02_tech_stack.md", "03_knowledge_base.md", "04_review_log.md"):
        (repo / "memory" / name).write_text(f"# {name}\n", encoding="utf-8")

    (repo / "AGENTS.base.md").write_text(
        "# AGENTS.base.md\n"
        "<!-- governance-baseline: protected -->\n"
        "<!-- baseline_version: 1.0.0 -->\n",
        encoding="utf-8",
    )
    (repo / "PLAN.md").write_text(
        "# PLAN.md\n\n"
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n"
        "## Active Sprint\n\n"
        "## Backlog\n",
        encoding="utf-8",
    )
    (repo / "contract.yaml").write_text(
        "name: test-contract\n"
        "framework_interface_version: \"1\"\n"
        "framework_compatible: \">=1.0.0,<2.0.0\"\n"
        "domain: test\n"
        "documents:\n"
        "  - AGENTS.base.md\n"
        "  - PLAN.md\n",
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text(
        "# AGENTS.md\n\n"
        "<!-- governance:key=risk_levels -->\n"
        "- Low\n\n"
        "<!-- governance:key=must_test_paths -->\n"
        "- tests\n",
        encoding="utf-8",
    )
    (repo / ".governance").mkdir()
    baseline = build_authority_manifest_inputs(repo)
    (repo / ".governance" / "baseline.yaml").write_text(baseline, encoding="utf-8")
    _commit(repo, "baseline")


def build_authority_manifest_inputs(repo: Path) -> str:
    import hashlib

    def _hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    return (
        "schema_version: \"1\"\n"
        "baseline_version: 1.0.0\n"
        "source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        f"framework_root: {FRAMEWORK_ROOT}\n"
        f"initialized_at: {_date.today().isoformat()}T10:00:00Z\n"
        "initialized_by: governance_tools/adopt_governance.py\n"
        f"sha256.AGENTS.base.md: {_hash(repo / 'AGENTS.base.md')}\n"
        f"sha256.PLAN.md: {_hash(repo / 'PLAN.md')}\n"
        f"sha256.contract.yaml: {_hash(repo / 'contract.yaml')}\n"
        f"sha256.AGENTS.md: {_hash(repo / 'AGENTS.md')}\n"
        "overridable.AGENTS.base.md: protected\n"
        "overridable.PLAN.md: overridable\n"
        "overridable.contract.yaml: overridable\n"
        "overridable.AGENTS.md: overridable\n"
        "contract_required_fields:\n"
        "  - name\n"
        "  - framework_interface_version\n"
        "  - framework_compatible\n"
        "  - domain\n"
        "plan_section_inventory:\n"
        "  - \"## Current Phase\"\n"
        "  - \"## Active Sprint\"\n"
        "  - \"## Backlog\"\n"
    )


def _manifest_payload(repo: Path, *, base_ref: str, head_ref: str) -> dict:
    manifest = build_authority_manifest(repo, base_ref=base_ref, head_ref=head_ref, framework_root=FRAMEWORK_ROOT)
    return manifest_to_dict(manifest)


def test_unreadable_manifest_json_is_cache_unsafe(tmp_path: Path) -> None:
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not-json", encoding="utf-8")

    receipt = assess_manifest_path(bad_manifest, project_root=tmp_path)

    assert receipt.decision == "cache_unsafe"
    assert receipt.required_action == "manual_review"
    assert receipt.decision_reason == "manifest_json_unreadable"


def test_wrong_manifest_schema_is_cache_unsafe(tmp_path: Path) -> None:
    payload = {
        "schema": "WRONG_SCHEMA",
        "status": "candidate",
        "manifest_hash": "abc",
        "repo": str(tmp_path),
        "base_ref": "a",
        "head_ref": "b",
        "checks": {"governance_drift_checker": {"severity": "ok"}},
        "invalidation": {
            "authority_changed_between_refs": False,
            "cache_invalidating_authority_changed": False,
        },
        "repo_enforces_prompt_cache": False,
    }

    receipt = assess_manifest_payload(payload)

    assert receipt.decision == "cache_unsafe"
    assert receipt.required_action == "manual_review"
    assert receipt.decision_reason == "wrong_or_missing_manifest_schema"


def test_missing_required_field_is_not_checked(tmp_path: Path) -> None:
    payload = {
        "schema": "AUTHORITY_MANIFEST v1",
        "status": "candidate",
        "manifest_hash": "abc",
        "repo": str(tmp_path),
        "base_ref": "a",
        "head_ref": "b",
        "checks": {"governance_drift_checker": {"severity": "ok"}},
        "repo_enforces_prompt_cache": False,
    }

    receipt = assess_manifest_payload(payload)

    assert receipt.decision == "not_checked"
    assert receipt.required_action == "manual_review"
    assert "missing_required_fields" in receipt.decision_reason


def test_plan_churn_still_allows_reuse_candidate(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    base = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()
    (tmp_path / "PLAN.md").write_text(
        "# PLAN.md\n\n"
        f"> **最後更新**: {_date.today().isoformat()}\n"
        "> **Owner**: Test\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n"
        "## Active Sprint\n\n"
        "## Backlog\n\n"
        "- authority planning changed\n",
        encoding="utf-8",
    )
    head = _commit(tmp_path, "change plan")

    receipt = build_generated_receipt(tmp_path, base_ref=base, head_ref=head, framework_root=FRAMEWORK_ROOT)

    assert receipt.decision == "reuse_candidate"
    assert receipt.required_action == "none"
    assert receipt.authority_changed_between_refs is False
    assert receipt.cache_invalidating_authority_changed is False


def test_changed_cache_stable_authority_requires_reload(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    base = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS.md\n\n"
        "<!-- governance:key=risk_levels -->\n"
        "- High\n\n"
        "<!-- governance:key=must_test_paths -->\n"
        "- tests\n",
        encoding="utf-8",
    )
    head = _commit(tmp_path, "change agents")

    receipt = build_generated_receipt(tmp_path, base_ref=base, head_ref=head, framework_root=FRAMEWORK_ROOT)

    assert receipt.decision == "reload_required"
    assert receipt.required_action == "reload_authority_files"
    assert receipt.authority_changed_between_refs is True
    assert receipt.cache_invalidating_authority_changed is True
    assert receipt.decision_reason == "cache_invalidating_authority_changed"


def test_unchanged_manifest_is_reuse_candidate(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()

    receipt = build_generated_receipt(tmp_path, base_ref=head, head_ref=head, framework_root=FRAMEWORK_ROOT)

    assert receipt.decision == "reuse_candidate"
    assert receipt.required_action == "none"
    assert receipt.cache_behavior_claim == "not_observed"
    assert receipt.runtime_enforcement_claim == "not_enforced_by_repo"


def test_cli_generated_mode_is_no_write_and_serializable(tmp_path: Path) -> None:
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()
    before = _run(tmp_path, "status", "--short").stdout

    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "governance_tools.authority_manifest_preflight",
            "--project-root",
            str(tmp_path),
            "--base-ref",
            head,
            "--head-ref",
            head,
            "--framework-root",
            str(FRAMEWORK_ROOT),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    after = _run(tmp_path, "status", "--short").stdout
    payload = json.loads(proc.stdout)

    assert before == after
    assert payload["schema"] == "AUTHORITY_MANIFEST_PREFLIGHT_RECEIPT v0.1"
    assert payload["decision"] == "reuse_candidate"
    assert payload["cache_behavior_claim"] == "not_observed"
