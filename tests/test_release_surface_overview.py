import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_snapshot import (
    build_release_package_snapshot,
    write_release_root_index,
    write_snapshot_bundle,
)
from governance_tools.release_surface_overview import (
    assess_release_surface,
    format_human_result,
    format_markdown_result,
)


def test_release_surface_overview_passes_for_current_alpha():
    result = assess_release_surface(Path(".").resolve(), version="v1.0.0-alpha")

    assert result["ok"] is True
    assert result["readiness"]["ok"] is True
    assert result["package"]["ok"] is True
    assert result["bundle_manifest"]["source"] in {"unavailable", "docs-release", "artifact-bundle"}
    assert result["publication_manifest"]["source"] in {"unavailable", "docs-release-root", "artifact-bundle"}
    assert any(item["name"] == "release_package_snapshot_docs" for item in result["commands"])


def test_release_surface_overview_can_read_explicit_bundle_and_publication(tmp_path):
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package" / "v1.0.0-alpha")
    root_paths = write_release_root_index(tmp_path / "docs" / "releases" / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

    result = assess_release_surface(
        Path(".").resolve(),
        version="v1.0.0-alpha",
        bundle_manifest=Path(bundle["manifest_json"]),
        publication_manifest=Path(root_paths["generated_root_publication_manifest_json"]),
    )

    assert result["ok"] is True
    assert result["bundle_manifest"]["available"] is True
    assert result["bundle_manifest"]["source"] == "explicit"
    assert result["bundle_manifest"]["version"] == "v1.0.0-alpha"
    assert result["publication_manifest"]["available"] is True
    assert result["publication_manifest"]["source"] == "explicit"
    assert result["publication_manifest"]["publication_scope"] == "docs-release-root"


def test_release_surface_overview_human_and_markdown_outputs_are_summary_first(tmp_path):
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")

    result = assess_release_surface(
        Path(".").resolve(),
        version="v1.0.0-alpha",
        bundle_manifest=Path(bundle["manifest_json"]),
    )

    rendered_human = format_human_result(result)
    rendered_markdown = format_markdown_result(result)

    assert rendered_human.startswith("summary=ok=True | version=v1.0.0-alpha")
    assert "[release_surface_overview]" in rendered_human
    assert "[bundle_manifest]" in rendered_human
    assert "[publication_manifest]" in rendered_human
    assert rendered_markdown.startswith("# Release Surface Overview")
    assert "- Summary: `summary=ok=True | version=v1.0.0-alpha" in rendered_markdown
    assert "## Surface Status" in rendered_markdown
    assert "## Suggested Commands" in rendered_markdown


def test_release_surface_overview_cli_supports_direct_script_invocation(tmp_path):
    snapshot = build_release_package_snapshot(project_root=Path(".").resolve(), version="v1.0.0-alpha")
    bundle = write_snapshot_bundle(snapshot, tmp_path / "release-package")
    root_paths = write_release_root_index(tmp_path / "docs" / "releases" / "generated", version="v1.0.0-alpha", bundle_paths=bundle)

    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/release_surface_overview.py",
            "--version",
            "v1.0.0-alpha",
            "--bundle-manifest",
            bundle["manifest_json"],
            "--publication-manifest",
            root_paths["generated_root_publication_manifest_json"],
            "--format",
            "human",
        ],
        check=True,
        capture_output=True, stdin=subprocess.DEVNULL,
        text=True,
    )

    assert "summary=ok=True | version=v1.0.0-alpha" in result.stdout
    assert "[release_surface_overview]" in result.stdout
