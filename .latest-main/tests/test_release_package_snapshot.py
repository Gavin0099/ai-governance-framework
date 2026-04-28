import json
import subprocess
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_snapshot import (
    build_release_package_snapshot,
    format_index,
    resolve_bundle_dir,
    write_release_root_index,
    write_snapshot_bundle,
)


def _local_tmp(name: str) -> Path:
    path = Path("tests") / "_tmp_release_package_snapshot" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_build_release_package_snapshot_passes_for_current_alpha():
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")

    assert snapshot["ok"] is True
    assert snapshot["package"]["ok"] is True
    assert snapshot["package"]["release_doc_count"] == 5
    assert snapshot["package"]["status_doc_count"] == 5


def test_write_release_package_snapshot_bundle_creates_latest_history_manifest():
    tmp_path = _local_tmp("bundle")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")

        assert Path(bundle["latest_json"]).is_file()
        assert Path(bundle["latest_txt"]).is_file()
        assert Path(bundle["latest_md"]).is_file()
        assert Path(bundle["history_json"]).is_file()
        assert Path(bundle["history_txt"]).is_file()
        assert Path(bundle["history_md"]).is_file()
        assert Path(bundle["index_md"]).is_file()
        assert Path(bundle["manifest_json"]).is_file()
        assert Path(bundle["readme_md"]).is_file()

        manifest = json.loads(Path(bundle["manifest_json"]).read_text(encoding="utf-8"))
        assert manifest["version"] == "v1.0.0-alpha"
        assert manifest["ok"] is True
        assert manifest["latest"]["json"].endswith("latest.json")
        assert "# Generated Release Package" in Path(bundle["readme_md"]).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_format_index_handles_empty_history():
    tmp_path = _local_tmp("empty_history")
    history_dir = tmp_path / "history"
    try:
        history_dir.mkdir(parents=True, exist_ok=True)
        rendered = format_index(history_dir)
        assert "[release_package_snapshot_index]" in rendered
        assert "reports=0" in rendered
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_resolve_bundle_dir_can_default_to_docs_release_generated():
    tmp_path = _local_tmp("resolve_bundle")
    project_root = tmp_path / "repo"
    try:
        project_root.mkdir(parents=True, exist_ok=True)
        resolved = resolve_bundle_dir(
            project_root=project_root,
            version="v1.0.0-alpha",
            publish_docs_release=True,
        )

        assert resolved == (project_root / "docs" / "releases" / "generated" / "v1.0.0-alpha").resolve()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_release_package_snapshot_cli_supports_direct_script_invocation():
    tmp_path = _local_tmp("cli")
    bundle_dir = tmp_path / "release-bundle"
    try:
        result = subprocess.run(
        [
            sys.executable,
            "governance_tools/release_package_snapshot.py",
            "--version",
            "v1.0.0-alpha",
            "--write-bundle",
            str(bundle_dir),
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

        assert "summary=ok=True | version=v1.0.0-alpha" in result.stdout
        assert "[release_package_snapshot]" in result.stdout
        assert (bundle_dir / "latest.json").is_file()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_write_release_root_index_creates_generated_release_landing_page():
    tmp_path = _local_tmp("root_index")
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    try:
        bundle = write_snapshot_bundle(snapshot, tmp_path / "generated" / "v1.0.0-alpha")
        root_paths = write_release_root_index(tmp_path / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

        assert Path(root_paths["generated_root_readme_md"]).is_file()
        assert Path(root_paths["generated_root_latest_json"]).is_file()
        assert Path(root_paths["generated_root_latest_md"]).is_file()
        readme_text = Path(root_paths["generated_root_readme_md"]).read_text(encoding="utf-8")
        assert "# Generated Release Packages" in readme_text
        assert "[Version README](v1.0.0-alpha/README.md)" in readme_text
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
