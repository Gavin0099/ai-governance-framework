import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_publication_reader import (
    assess_publication_manifest,
    default_docs_release_publication_manifest_path,
    format_human_result,
)
from governance_tools.release_package_snapshot import (
    build_release_package_snapshot,
    write_release_root_index,
    write_snapshot_bundle,
)


def test_assess_publication_manifest_reads_bundle_publication_manifest(tmp_path):
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")

    result = assess_publication_manifest(Path(bundle["publication_manifest_json"]))

    assert result["ok"] is True
    assert result["publication_scope"] == "bundle"
    assert result["version"] == "v1.0.0-alpha"
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
                "publication_scope": "docs-release-root",
                "version": "v1.0.0-alpha",
                "release_doc_count": 5,
                "status_doc_count": 5,
                "existing_release_docs": 5,
                "existing_status_docs": 5,
                "latest_json": "latest.json",
                "latest_md": "latest.md",
                "readme_md": "README.md",
                "version_manifest_json": "v1.0.0-alpha/MANIFEST.json",
                "version_readme_md": "v1.0.0-alpha/README.md",
                "version_latest_md": "v1.0.0-alpha/latest.md",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = format_human_result(assess_publication_manifest(manifest_path))

    assert rendered.startswith("summary=ok=True | scope=docs-release-root | version=v1.0.0-alpha")
    assert "[release_package_publication_reader]" in rendered
    assert "version_manifest_json=v1.0.0-alpha/MANIFEST.json" in rendered


def test_default_docs_release_publication_manifest_path_points_to_generated_root():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_docs_release_publication_manifest_path(project_root)

    assert resolved == project_root / "docs" / "releases" / "generated" / "PUBLICATION_MANIFEST.json"


def test_release_package_publication_reader_cli_supports_docs_release_root(tmp_path):
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    project_root = tmp_path / "repo"
    bundle = write_snapshot_bundle(snapshot, project_root / "docs" / "releases" / "generated" / "v1.0.0-alpha")
    write_release_root_index(project_root / "docs" / "releases" / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/release_package_publication_reader.py",
            "--project-root",
            str(project_root),
            "--docs-release-root",
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=True | scope=docs-release-root | version=v1.0.0-alpha" in result.stdout
