import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.trust_signal_publication_reader import (
    assess_publication_manifest,
    default_manifest_path,
    format_human_result,
)
from governance_tools.trust_signal_snapshot import (
    build_trust_signal_snapshot,
    write_publication_manifest,
    write_published_status,
    write_snapshot_bundle,
)


def test_assess_publication_manifest_reads_generated_bundle(tmp_path):
    project_root = Path(".").resolve()
    contract_file = project_root / "examples" / "usb-hub-contract" / "contract.yaml"
    snapshot = build_trust_signal_snapshot(
        project_root=project_root,
        plan_path=project_root / "PLAN.md",
        release_version="v1.0.0-alpha",
        contract_file=contract_file,
    )
    bundle = write_snapshot_bundle(snapshot, tmp_path / "status")
    published = write_published_status(snapshot, tmp_path / "status" / "published")
    publication = write_publication_manifest(
        snapshot,
        tmp_path / "status",
        bundle_paths=bundle,
        published_paths=published,
    )

    result = assess_publication_manifest(Path(publication["manifest_json"]))

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["bundle_published"] is True
    assert result["status_pages_published"] is True
    assert result["release_version"] == "v1.0.0-alpha"


def test_format_human_result_surfaces_summary_and_paths(tmp_path):
    manifest_path = tmp_path / "PUBLICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "publication_root": str(tmp_path),
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "external_contract_repo_count": 3,
                "external_contract_policy_ok": True,
                "external_contract_profile_counts": {"mixed": 2, "advisory-only": 1},
                "external_contract_policies": [
                    {
                        "repo_root": "D:/Kernel-Driver-Contract",
                        "ok": True,
                        "domain": "kernel-driver",
                        "enforcement_profile": "mixed",
                        "validator_ready_count": 2,
                        "validator_count": 2,
                        "hard_stop_rules": ["KD-002", "KD-003"],
                    },
                    {
                        "repo_root": "D:/USB-Hub-Firmware-Architecture-Contract",
                        "ok": True,
                        "domain": "firmware",
                        "enforcement_profile": "mixed",
                        "validator_ready_count": 1,
                        "validator_count": 1,
                        "hard_stop_rules": ["HUB-004"],
                    },
                ],
                "strict_runtime": False,
                "bundle_published": True,
                "status_pages_published": True,
                "bundle": {
                    "latest_json": "latest.json",
                    "latest_txt": "latest.txt",
                    "latest_md": "latest.md",
                    "index_md": "INDEX.md",
                    "manifest_json": "MANIFEST.json",
                },
                "published": {
                    "latest_md": "published/trust-signal-latest.md",
                    "latest_json": "published/trust-signal-latest.json",
                    "readme_md": "published/README.md",
                    "index_md": "published/INDEX.md",
                    "manifest_json": "published/manifest.json",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = format_human_result(assess_publication_manifest(manifest_path))

    assert rendered.startswith("summary=ok=True")
    assert "external_contracts=True" in rendered
    assert "release=v1.0.0-alpha" in rendered
    assert "external_contract_profile_counts={'mixed': 2, 'advisory-only': 1}" in rendered
    assert "[bundle]" in rendered
    assert "[published]" in rendered
    assert "[external_contract_policies]" in rendered
    assert "hard_stop_rules=KD-002,KD-003" in rendered


def test_default_manifest_path_points_to_artifacts_root():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_manifest_path(project_root)

    assert resolved == project_root / "artifacts" / "trust-signals" / "PUBLICATION_MANIFEST.json"


def test_publication_reader_cli_supports_direct_script_invocation(tmp_path):
    manifest_path = tmp_path / "PUBLICATION_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "ok": True,
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "publication_root": str(tmp_path),
                "release_version": "v1.0.0-alpha",
                "contract_path": "examples/usb-hub-contract/contract.yaml",
                "strict_runtime": False,
                "bundle_published": True,
                "status_pages_published": False,
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
            "governance_tools/trust_signal_publication_reader.py",
            "--file",
            str(manifest_path),
            "--format",
            "human",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "summary=ok=True" in result.stdout
    assert "status_pages_published=False" in result.stdout
