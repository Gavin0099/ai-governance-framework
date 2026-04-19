import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_handoff_publication_reader import (
    assess_publication_manifest,
    default_docs_status_manifest_path,
    default_manifest_path,
    format_human_result,
)
from governance_tools.reviewer_handoff_snapshot import (
    build_reviewer_handoff_snapshot,
    write_publication_manifest,
    write_published_status,
    write_snapshot_bundle,
)


def test_assess_publication_manifest_reads_generated_bundle(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff" / "v1.0.0-alpha")
    published = write_published_status(snapshot, tmp_path / "reviewer-handoff" / "published")
    publication = write_publication_manifest(
        snapshot,
        tmp_path / "reviewer-handoff",
        bundle_paths=bundle,
        published_paths=published,
    )

    result = assess_publication_manifest(Path(publication["manifest_json"]))

    assert result["ok"] == snapshot["ok"]
    assert result["exists"] is True
    assert result["publication_scope"] == "reviewer-handoff-root"
    assert result["bundle_published"] is True
    assert result["status_pages_published"] is True
    assert result["release_version"] == "v1.0.0-alpha"


def test_format_human_result_surfaces_publication_scope_and_paths(tmp_path):
    manifest_path = tmp_path / "PUBLICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "publication_root": str(tmp_path),
                "publication_scope": "reviewer-handoff-root",
                "plan_path": "D:/ai-governance-framework/PLAN.md",
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "external_contract_repos": [],
                "external_contract_repo_count": 0,
                "strict_runtime": False,
                "trust_ok": True,
                "release_ok": True,
                "handoff_clean_identity": True,
                "lint_status": "clean",
                "lint_violation_count": 0,
                "lint_highest_severity": "none",
                "lint_violations": [],
                "lint_policy": {
                    "override_reason_code": None,
                    "override_blocked_by_non_overridable": False,
                    "non_overridable_claim_types": [],
                },
                "bundle_published": True,
                "status_pages_published": True,
                "bundle": {
                    "latest_json": "bundle/latest.json",
                    "latest_txt": "bundle/latest.txt",
                    "latest_md": "bundle/latest.md",
                    "history_json": "bundle/history.json",
                    "history_txt": "bundle/history.txt",
                    "history_md": "bundle/history.md",
                    "index_md": "bundle/INDEX.md",
                    "manifest_json": "bundle/MANIFEST.json",
                },
                "published": {
                    "latest_json": "published/reviewer-handoff-latest.json",
                    "latest_md": "published/reviewer-handoff-latest.md",
                    "readme_md": "published/README.md",
                    "history_json": "published/history.json",
                    "history_md": "published/history.md",
                    "index_md": "published/INDEX.md",
                    "manifest_json": "published/manifest.json",
                },
                "readme_md": "README.md",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = format_human_result(assess_publication_manifest(manifest_path))

    assert rendered.startswith(
        "summary=ok=True | scope=reviewer-handoff-root | trust=True | release=True | lint=clean | identity=clean | release_version=v1.0.0-alpha"
    )
    assert "[reviewer_handoff_publication_reader]" in rendered
    assert "[policy_not_clean]" in rendered
    assert "bundle_published=True" in rendered
    assert "status_pages_published=True" in rendered
    assert "[bundle]" in rendered
    assert "[published]" in rendered
    assert "readme_md=README.md" in rendered


def test_default_manifest_path_points_to_artifacts_reviewer_handoff_publication():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_manifest_path(project_root, release_version="v1.0.0-alpha")

    assert resolved == project_root / "artifacts" / "reviewer-handoff" / "PUBLICATION_MANIFEST.json"


def test_default_docs_status_manifest_path_points_to_generated_reviewer_handoff_root():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_docs_status_manifest_path(project_root)

    assert resolved == (
        project_root / "docs" / "status" / "generated" / "reviewer-handoff" / "PUBLICATION_MANIFEST.json"
    )


def test_reviewer_handoff_publication_reader_cli_supports_direct_script_invocation(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff" / "v1.0.0-alpha")
    published = write_published_status(snapshot, tmp_path / "reviewer-handoff" / "published")
    publication = write_publication_manifest(
        snapshot,
        tmp_path / "reviewer-handoff",
        bundle_paths=bundle,
        published_paths=published,
    )

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_handoff_publication_reader.py",
            "--release-version",
            "v1.0.0-alpha",
            "--file",
            publication["manifest_json"],
            "--format",
            "human",
        ],
        check=False,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=" in result.stdout
    assert "scope=reviewer-handoff-root" in result.stdout
    assert "release_version=v1.0.0-alpha" in result.stdout
    assert "[reviewer_handoff_publication_reader]" in result.stdout


def test_reviewer_handoff_publication_reader_cli_can_use_docs_status_flag(tmp_path):
    project_root = tmp_path / "repo"
    manifest_path = project_root / "docs" / "status" / "generated" / "reviewer-handoff" / "PUBLICATION_MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": str(project_root),
                "publication_root": str(manifest_path.parent),
                "publication_scope": "reviewer-handoff-root",
                "plan_path": str(project_root / "PLAN.md"),
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "strict_runtime": False,
                "trust_ok": True,
                "release_ok": True,
                "handoff_clean_identity": True,
                "lint_status": "clean",
                "lint_violation_count": 0,
                "lint_highest_severity": "none",
                "lint_violations": [],
                "lint_policy": {
                    "override_reason_code": None,
                    "override_blocked_by_non_overridable": False,
                    "non_overridable_claim_types": [],
                },
                "bundle_published": False,
                "status_pages_published": False,
                "readme_md": str(manifest_path.parent / "README.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_handoff_publication_reader.py",
            "--project-root",
            str(project_root),
            "--release-version",
            "v1.0.0-alpha",
            "--docs-status",
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=True | scope=reviewer-handoff-root | trust=True | release=True | lint=clean | identity=clean | release_version=v1.0.0-alpha" in result.stdout
    assert f"manifest_file={manifest_path}" in result.stdout


def test_publication_reader_surfaces_policy_not_clean_frozen_fields(tmp_path):
    manifest_path = tmp_path / "PUBLICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": False,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "publication_root": str(tmp_path),
                "publication_scope": "reviewer-handoff-root",
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "strict_runtime": False,
                "trust_ok": True,
                "release_ok": True,
                "handoff_clean_identity": False,
                "lint_status": "non-clean",
                "lint_violation_count": 2,
                "lint_highest_severity": "high",
                "lint_violations": [
                    {
                        "severity": "medium",
                        "claim_type": "quality_verdict",
                        "excerpt": "Status: healthy",
                    },
                    {
                        "severity": "high",
                        "claim_type": "stability_claim",
                        "excerpt": "Status: stable enough for next phase",
                    },
                ],
                "lint_policy": {
                    "override_reason_code": "manual_audit_required",
                    "override_blocked_by_non_overridable": True,
                    "non_overridable_claim_types": ["stability_claim"],
                },
                "bundle_published": False,
                "status_pages_published": False,
                "readme_md": "README.md",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rendered = format_human_result(assess_publication_manifest(manifest_path))
    assert "[policy_not_clean]" in rendered
    assert "lint_status=non-clean" in rendered
    assert "override_reason_code=manual_audit_required" in rendered
    assert "override_blocked_by_non_overridable=True" in rendered
    assert "non_overridable_claim_types=stability_claim" in rendered
    assert "top_violation_excerpt=Status: stable enough for next phase" in rendered
