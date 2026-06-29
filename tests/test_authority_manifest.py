import hashlib
import json
import subprocess
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.authority_manifest import (
    build_authority_manifest,
    format_json,
    manifest_to_dict,
)

FRAMEWORK_ROOT = Path(__file__).parent.parent


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)


def _commit(repo: Path, message: str) -> str:
    _run(repo, "-c", "user.name=Test User", "-c", "user.email=test@example.invalid", "add", ".")
    _run(repo, "-c", "user.name=Test User", "-c", "user.email=test@example.invalid", "commit", "-m", message)
    return _run(repo, "rev-parse", "--short", "HEAD").stdout.strip()


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_minimal_repo(repo: Path) -> dict[str, str]:
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
        f"> **Last updated**: {_date.today().isoformat()}\n"
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

    hashes = {
        "AGENTS.base.md": _hash(repo / "AGENTS.base.md"),
        "PLAN.md": _hash(repo / "PLAN.md"),
        "contract.yaml": _hash(repo / "contract.yaml"),
        "AGENTS.md": _hash(repo / "AGENTS.md"),
    }
    (repo / ".governance").mkdir()
    (repo / ".governance" / "baseline.yaml").write_text(
        "schema_version: \"1\"\n"
        "baseline_version: 1.0.0\n"
        "source_commit: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n"
        f"framework_root: {FRAMEWORK_ROOT}\n"
        f"initialized_at: {_date.today().isoformat()}T10:00:00Z\n"
        "initialized_by: governance_tools/adopt_governance.py\n"
        f"sha256.AGENTS.base.md: {hashes['AGENTS.base.md']}\n"
        f"sha256.PLAN.md: {hashes['PLAN.md']}\n"
        f"sha256.contract.yaml: {hashes['contract.yaml']}\n"
        f"sha256.AGENTS.md: {hashes['AGENTS.md']}\n"
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
        "  - \"## Backlog\"\n",
        encoding="utf-8",
    )
    _commit(repo, "baseline")
    return hashes


def test_manifest_derives_authority_files_and_hashes_from_baseline(tmp_path):
    baseline_hashes = _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()

    manifest = build_authority_manifest(
        tmp_path,
        base_ref=head,
        head_ref=head,
        framework_root=FRAMEWORK_ROOT,
    )
    data = manifest_to_dict(manifest)

    by_path = {item["path"]: item for item in data["authority_files"]}
    assert set(by_path) == set(baseline_hashes)
    for path, expected_hash in baseline_hashes.items():
        assert by_path[path]["baseline_hash"] == expected_hash
        assert by_path[path]["baseline_hash_source"] == f".governance/baseline.yaml:sha256.{path}"
        assert by_path[path]["current_hash"] == expected_hash
        assert by_path[path]["current_hash_source"] == "working_tree_bytes"
        assert by_path[path]["base_hash"] == expected_hash
        assert by_path[path]["base_hash_source"] == f"git_blob:{head}:{path}"
        assert by_path[path]["head_hash"] == expected_hash
        assert by_path[path]["head_hash_source"] == f"git_blob:{head}:{path}"
    assert data["baseline_source"]["authority_paths_source"] == "sha256.* keys from .governance/baseline.yaml"
    assert data["baseline_source"]["source_commit"] == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    assert data["baseline_source"]["baseline_version"] == "1.0.0"
    assert data["baseline_source"]["initialized_at"] == f"{_date.today().isoformat()}T10:00:00Z"
    assert data["baseline_source"]["initialized_by"] == "governance_tools/adopt_governance.py"
    assert data["repo_enforces_prompt_cache"] is False
    assert data["invalidation"]["authority_changed_between_refs"] is False


def test_invalidation_signal_is_false_when_refs_match(tmp_path):
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()

    manifest = build_authority_manifest(
        tmp_path,
        base_ref=head,
        head_ref=head,
        framework_root=FRAMEWORK_ROOT,
    )

    assert manifest.invalidation["authority_changed_between_refs"] is False
    assert manifest.invalidation["changed_paths"] == []


def test_invalidation_signal_detects_authority_file_change_between_refs(tmp_path):
    _write_minimal_repo(tmp_path)
    base = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()
    (tmp_path / "PLAN.md").write_text(
        "# PLAN.md\n\n"
        f"> **Last updated**: {_date.today().isoformat()}\n"
        "> **Freshness**: Sprint (7d)\n\n"
        "## Current Phase\n\n"
        "## Active Sprint\n\n"
        "## Backlog\n\n"
        "- authority planning changed\n",
        encoding="utf-8",
    )
    head = _commit(tmp_path, "change plan")

    manifest = build_authority_manifest(
        tmp_path,
        base_ref=base,
        head_ref=head,
        framework_root=FRAMEWORK_ROOT,
    )

    assert manifest.invalidation["authority_changed_between_refs"] is True
    assert manifest.invalidation["changed_paths"] == ["PLAN.md"]
    plan_entry = next(item for item in manifest.authority_files if item.path == "PLAN.md")
    assert plan_entry.changed_between_refs is True
    assert plan_entry.base_hash != plan_entry.head_hash


def test_manifest_hash_excludes_generated_at_dynamic_tail(tmp_path, monkeypatch):
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()

    import governance_tools.authority_manifest as authority_manifest

    class FirstDateTime:
        @classmethod
        def now(cls, tz):
            from datetime import datetime

            return datetime(2026, 6, 29, 1, 0, 0, tzinfo=tz)

    class SecondDateTime:
        @classmethod
        def now(cls, tz):
            from datetime import datetime

            return datetime(2026, 6, 29, 2, 0, 0, tzinfo=tz)

    monkeypatch.setattr(authority_manifest, "datetime", FirstDateTime)
    first = build_authority_manifest(tmp_path, base_ref=head, head_ref=head, framework_root=FRAMEWORK_ROOT)
    monkeypatch.setattr(authority_manifest, "datetime", SecondDateTime)
    second = build_authority_manifest(tmp_path, base_ref=head, head_ref=head, framework_root=FRAMEWORK_ROOT)

    assert first.generated_at != second.generated_at
    assert first.manifest_hash == second.manifest_hash


def test_cli_json_outputs_candidate_manifest(tmp_path):
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()

    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "governance_tools.authority_manifest",
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

    data = json.loads(proc.stdout)
    assert data["schema"] == "AUTHORITY_MANIFEST v1"
    assert data["status"] == "candidate"
    assert data["repo_enforces_prompt_cache"] is False
    assert "prompt-cache enforcement" in data["claim_ceiling"]


def test_format_json_is_serializable(tmp_path):
    _write_minimal_repo(tmp_path)
    head = _run(tmp_path, "rev-parse", "HEAD").stdout.strip()
    manifest = build_authority_manifest(tmp_path, base_ref=head, head_ref=head, framework_root=FRAMEWORK_ROOT)

    payload = json.loads(format_json(manifest))

    assert payload["schema"] == "AUTHORITY_MANIFEST v1"
    assert payload["checks"]["governance_drift_checker"]["severity"] in {"ok", "warning", "critical"}
