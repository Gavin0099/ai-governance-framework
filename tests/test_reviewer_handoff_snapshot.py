import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_handoff_snapshot import (
    build_reviewer_handoff_snapshot,
    format_index,
    resolve_bundle_dir,
    write_snapshot_bundle,
)


def test_build_reviewer_handoff_snapshot_passes_for_current_alpha():
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    assert snapshot["ok"] is True
    assert snapshot["handoff"]["ok"] is True
    assert snapshot["handoff"]["trust_signal"]["ok"] is True
    assert snapshot["handoff"]["release_surface"]["ok"] is True


def test_write_reviewer_handoff_snapshot_bundle_creates_latest_history_manifest(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_reviewer_handoff_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )

    bundle = write_snapshot_bundle(snapshot, tmp_path / "reviewer-handoff")

    assert Path(bundle["latest_json"]).is_file()
    assert Path(bundle["latest_txt"]).is_file()
    assert Path(bundle["latest_md"]).is_file()
    assert Path(bundle["history_json"]).is_file()
    assert Path(bundle["history_txt"]).is_file()
    assert Path(bundle["history_md"]).is_file()
    assert Path(bundle["index_md"]).is_file()
    assert Path(bundle["manifest_json"]).is_file()
    assert Path(bundle["publication_manifest_json"]).is_file()
    assert Path(bundle["publication_index_md"]).is_file()
    assert Path(bundle["readme_md"]).is_file()

    manifest = json.loads(Path(bundle["manifest_json"]).read_text(encoding="utf-8"))
    assert manifest["release_version"] == "v1.0.0-alpha"
    assert manifest["ok"] is True
    assert manifest["latest"]["json"].endswith("latest.json")
    assert manifest["trust_ok"] is True
    assert manifest["release_ok"] is True
    assert "# Reviewer Handoff Snapshot" in Path(bundle["readme_md"]).read_text(encoding="utf-8")
    publication = json.loads(Path(bundle["publication_manifest_json"]).read_text(encoding="utf-8"))
    assert publication["publication_scope"] == "bundle"
    assert publication["ok"] is True
    assert publication["release_version"] == "v1.0.0-alpha"


def test_format_index_handles_empty_history(tmp_path):
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    rendered = format_index(history_dir)

    assert "[reviewer_handoff_snapshot_index]" in rendered
    assert "reports=0" in rendered


def test_resolve_bundle_dir_defaults_to_artifacts_version_dir(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)

    resolved = resolve_bundle_dir(
        project_root=project_root,
        release_version="v1.0.0-alpha",
    )

    assert resolved == project_root / "artifacts" / "reviewer-handoff" / "v1.0.0-alpha"


def test_reviewer_handoff_snapshot_cli_supports_direct_script_invocation(tmp_path):
    bundle_dir = tmp_path / "reviewer-handoff"
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_handoff_snapshot.py",
            "--project-root",
            str(project_root),
            "--plan",
            str(project_root / "PLAN.md"),
            "--release-version",
            "v1.0.0-alpha",
            "--contract",
            str(contract_file),
            "--write-bundle",
            str(bundle_dir),
            "--format",
            "human",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "summary=ok=True | trust=True | release=True | release_version=v1.0.0-alpha" in result.stdout
    assert "[reviewer_handoff_snapshot]" in result.stdout
    assert (bundle_dir / "latest.json").is_file()
