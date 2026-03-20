import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_handoff_snapshot import (
    build_reviewer_handoff_snapshot,
    format_index,
    format_publication_index,
    resolve_publication_paths,
    resolve_bundle_dir,
    write_publication_manifest,
    write_snapshot_bundle,
)

FIXTURE_ROOT = Path("tests/_tmp_reviewer_handoff_snapshot")


def _reset_fixture(name: str) -> Path:
    root = FIXTURE_ROOT / name
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        root.rmdir()
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def test_resolve_publication_paths_can_default_to_docs_status_generated(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True, exist_ok=True)

    bundle_path, published_path, publication_root = resolve_publication_paths(
        project_root=project_root,
        release_version="v1.0.0-alpha",
        publish_docs_status=True,
    )

    expected_root = project_root / "docs" / "status" / "generated" / "reviewer-handoff"
    assert bundle_path == expected_root / "bundle"
    assert published_path == expected_root / "site"
    assert publication_root == expected_root


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


def test_reviewer_handoff_snapshot_publication_surfaces_external_fact_states():
    fixture_root = _reset_fixture("publication_external_fact_states")
    snapshot = {
        "ok": True,
        "generated_at": "2026-03-20T00:00:00+00:00",
        "project_root": str(Path(".").resolve()),
        "plan_path": "PLAN.md",
        "release_version": "v1.0.0-alpha",
        "contract_path": "example/contract.yaml",
        "external_contract_repos": ["/tmp/kernel-driver-contract"],
        "strict_runtime": False,
        "handoff": {
            "trust_signal": {
                "ok": True,
                "auditor": {
                    "external_onboarding": {
                        "top_issues": [
                            {
                                "repo_root": "/tmp/kernel-driver-contract",
                                "project_facts_summary": "status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md",
                            }
                        ]
                    }
                },
            },
            "release_surface": {"ok": True},
        },
    }

    rendered = format_publication_index(snapshot)
    publication = write_publication_manifest(snapshot, fixture_root / "handoff-publication")
    manifest_payload = json.loads(Path(publication["manifest_json"]).read_text(encoding="utf-8"))
    readme_text = Path(publication["readme_md"]).read_text(encoding="utf-8")

    assert "## External Fact States" in rendered
    assert "/tmp/kernel-driver-contract: status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md" in rendered
    assert manifest_payload["external_onboarding_project_facts"] == [
        "/tmp/kernel-driver-contract: status=drifted | artifact_exists=True | artifact_drift=True | source=02_project_facts.md"
    ]
    assert "## External Fact States" in readme_text
