import json
import subprocess
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_reader import (
    assess_manifest,
    default_docs_release_manifest_path,
    default_manifest_path,
    format_human_result,
)
from governance_tools.release_package_snapshot import build_release_package_snapshot, write_snapshot_bundle


def _local_tmp(name: str) -> Path:
    path = Path("tests") / "_tmp_release_package_reader" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_assess_manifest_reads_generated_bundle():
    tmp_path = _local_tmp("generated_bundle")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")

        result = assess_manifest(Path(bundle["manifest_json"]))

        assert result["ok"] is True
        assert result["exists"] is True
        assert result["version"] == "v1.0.0-alpha"
        assert result["latest_md"].endswith("latest.md")
        assert result["readme_md"].endswith("README.md")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_format_human_result_surfaces_summary_and_paths():
    tmp_path = _local_tmp("human_result")
    manifest_path = tmp_path / "MANIFEST.json"
    try:
        manifest_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-15T00:00:00+00:00",
                "project_root": "D:/ai-governance-framework",
                "version": "v1.0.0-alpha",
                "ok": True,
                "release_doc_count": 5,
                "status_doc_count": 5,
                "existing_release_docs": 5,
                "existing_status_docs": 5,
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

        assert rendered.startswith("summary=ok=True | version=v1.0.0-alpha")
        assert "[release_package_reader]" in rendered
        assert "[latest]" in rendered
        assert "[history]" in rendered
        assert "[paths]" in rendered
        assert "readme_md=README.md" in rendered
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_default_manifest_path_points_to_artifacts_release_package():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_manifest_path(project_root, version="v1.0.0-alpha")

    assert resolved == project_root / "artifacts" / "release-package" / "v1.0.0-alpha" / "MANIFEST.json"


def test_default_docs_release_manifest_path_points_to_generated_release_path():
    project_root = Path("D:/ai-governance-framework")

    resolved = default_docs_release_manifest_path(project_root, version="v1.0.0-alpha")

    assert resolved == project_root / "docs" / "releases" / "generated" / "v1.0.0-alpha" / "MANIFEST.json"


def test_release_package_reader_cli_supports_direct_script_invocation():
    tmp_path = _local_tmp("cli")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")

        result = subprocess.run(
        [
            sys.executable,
            "governance_tools/release_package_reader.py",
            "--version",
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

        assert "summary=ok=True | version=v1.0.0-alpha" in result.stdout
        assert "[release_package_reader]" in result.stdout
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
