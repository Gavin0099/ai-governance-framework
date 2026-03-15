import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_handoff_publication_reader import (
    assess_publication_manifest,
    default_manifest_path,
    format_human_result,
)
from governance_tools.reviewer_handoff_snapshot import build_reviewer_handoff_snapshot, write_snapshot_bundle


def test_assess_publication_manifest_reads_generated_bundle(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff")

    result = assess_publication_manifest(Path(bundle["publication_manifest_json"]))

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["publication_scope"] == "bundle"
    assert result["release_version"] == "v1.0.0-alpha"
    assert result["latest_md"].endswith("latest.md")


def test_format_human_result_surfaces_publication_scope_and_paths(tmp_path):
    manifest_path = tmp_path / "PUBLICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "publication_root": str(tmp_path),
                "publication_scope": "bundle",
                "plan_path": "D:/ai-governance-framework/PLAN.md",
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "external_contract_repos": [],
                "external_contract_repo_count": 0,
                "strict_runtime": False,
                "trust_ok": True,
                "release_ok": True,
                "latest_json": "latest.json",
                "latest_txt": "latest.txt",
                "latest_md": "latest.md",
                "history_json": "history.json",
                "history_txt": "history.txt",
                "history_md": "history.md",
                "index_md": "INDEX.md",
                "manifest_json": "MANIFEST.json",
                "readme_md": "README.md",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = format_human_result(assess_publication_manifest(manifest_path))

    assert rendered.startswith("summary=ok=True | scope=bundle | trust=True | release=True | release_version=v1.0.0-alpha")
    assert "[reviewer_handoff_publication_reader]" in rendered
    assert "manifest_json=MANIFEST.json" in rendered
    assert "readme_md=README.md" in rendered


def test_default_manifest_path_points_to_artifacts_reviewer_handoff_publication():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_manifest_path(project_root, release_version="v1.0.0-alpha")

    assert resolved == project_root / "artifacts" / "reviewer-handoff" / "v1.0.0-alpha" / "PUBLICATION_MANIFEST.json"


def test_reviewer_handoff_publication_reader_cli_supports_direct_script_invocation(tmp_path):
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
            "governance_tools/reviewer_handoff_publication_reader.py",
            "--release-version",
            "v1.0.0-alpha",
            "--file",
            bundle["publication_manifest_json"],
            "--format",
            "human",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "summary=ok=True | scope=bundle | trust=True | release=True | release_version=v1.0.0-alpha" in result.stdout
    assert "[reviewer_handoff_publication_reader]" in result.stdout
