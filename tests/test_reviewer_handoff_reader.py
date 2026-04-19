import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_handoff_reader import (
    assess_manifest,
    default_manifest_path,
    format_human_result,
)
from governance_tools.reviewer_handoff_snapshot import build_reviewer_handoff_snapshot, write_snapshot_bundle


def test_assess_manifest_reads_generated_bundle(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff")

    result = assess_manifest(Path(bundle["manifest_json"]))

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["release_version"] == "v1.0.0-alpha"
    assert result["latest_md"].endswith("latest.md")
    assert result["readme_md"].endswith("README.md")


def test_format_human_result_surfaces_summary_and_paths(tmp_path):
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "plan_path": "D:/ai-governance-framework/PLAN.md",
                "release_version": "v1.0.0-alpha",
                "contract_path": "D:/ai-governance-framework/examples/usb-hub-contract/contract.yaml",
                "external_contract_repos": [],
                "external_contract_repo_count": 0,
                "strict_runtime": False,
                "ok": True,
                "upstream_ok": True,
                "trust_ok": True,
                "release_ok": True,
                "lint_status": "clean",
                "lint_violation_count": 0,
                "lint_highest_severity": "none",
                "lint_violations": [],
                "latest": {
                    "json": "latest.json",
                    "text": "latest.txt",
                    "markdown": "latest.md",
                },
                "history": {
                    "json": "history.json",
                    "text": "history.txt",
                    "markdown": "history.md",
                },
                "index": "INDEX.md",
                "readme": "README.md",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = format_human_result(assess_manifest(manifest_path))

    assert rendered.startswith("summary=ok=True | upstream_ok=True | trust=True | release=True | lint=clean | release_version=v1.0.0-alpha")
    assert "[reviewer_handoff_reader]" in rendered
    assert "[latest]" in rendered
    assert "[history]" in rendered
    assert "[paths]" in rendered
    assert "readme_md=README.md" in rendered


def test_default_manifest_path_points_to_artifacts_reviewer_handoff():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_manifest_path(project_root, release_version="v1.0.0-alpha")

    assert resolved == project_root / "artifacts" / "reviewer-handoff" / "v1.0.0-alpha" / "MANIFEST.json"


def test_reviewer_handoff_reader_cli_supports_direct_script_invocation(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff")

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_handoff_reader.py",
            "--release-version",
            "v1.0.0-alpha",
            "--file",
            bundle["manifest_json"],
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=True | upstream_ok=True | trust=True | release=True | lint=clean | release_version=v1.0.0-alpha" in result.stdout
    assert "[reviewer_handoff_reader]" in result.stdout


def test_reader_surfaces_lint_by_severity_claim_excerpt(tmp_path):
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "plan_path": "D:/ai-governance-framework/PLAN.md",
                "release_version": "v1.0.0-alpha",
                "contract_path": "D:/ai-governance-framework/examples/usb-hub-contract/contract.yaml",
                "external_contract_repos": [],
                "external_contract_repo_count": 0,
                "strict_runtime": False,
                "ok": False,
                "upstream_ok": True,
                "trust_ok": True,
                "release_ok": True,
                "lint_status": "non-clean",
                "lint_violation_count": 1,
                "lint_highest_severity": "high",
                "lint_violations": [
                    {
                        "severity": "high",
                        "claim_type": "stability_claim",
                        "excerpt": "Status: stable enough for next phase",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rendered = format_human_result(assess_manifest(manifest_path))
    assert "lint_status=non-clean" in rendered
    assert "lint_highest_severity=high" in rendered
    assert "high|stability_claim|Status: stable enough for next phase" in rendered
