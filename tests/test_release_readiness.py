import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_readiness import assess_release_readiness, format_human_result


@pytest.mark.integration
def test_release_readiness_passes_for_current_alpha():
    result = assess_release_readiness(Path(".").resolve(), version="v1.0.0-alpha")

    assert result["ok"] is True
    assert any(item["name"] == "release_note" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "release_index" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "release_index_version_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "release_index_generated_root_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "github_release_draft" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "release_note_generated_status_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "github_release_draft_generated_status_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "github_release_draft_status_links" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_release_version" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_snapshot_publish" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_docs_reader" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_release_package_snapshot" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_release_package_reader" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_release_surface_overview" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "publish_checklist_phase_gates" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_snapshot_publish" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_docs_reader" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_release_package_snapshot" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_release_package_reader" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_release_surface_overview" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_github_release_draft" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "alpha_checklist_publish_checklist" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "generated_release_root" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "generated_release_root_latest_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "release_note_generated_release_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "github_release_draft_generated_release_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "status_index" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_doc" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "status_index_reviewer_handoff_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_command" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_snapshot_command" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_reader_command" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_publication_reader_command" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_docs_status_publish" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_docs_status_reader" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_generated_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_artifact_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "reviewer_handoff_publication_manifest_path" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "trust_signal_dashboard" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "domain_enforcement_matrix" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "status_index_generated_readme_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "status_index_generated_site_link" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "readme_release_link" and item["ok"] for item in result["checks"])


@pytest.mark.integration
def test_release_readiness_human_output_is_scannable():
    result = assess_release_readiness(Path(".").resolve(), version="v1.0.0-alpha")
    output = format_human_result(result)

    assert "[release_readiness]" in output
    assert "summary=ok=True | version=v1.0.0-alpha" in output
    assert "version=v1.0.0-alpha" in output
    assert "check[reviewer_handoff_doc]=True" in output
    assert "check[release_note]=True" in output


# ── Fixture-based unit tests (no live repo dependency) ────────────────────────


def test_release_readiness_missing_badge_produces_check_failure(tmp_path):
    """Regression: README without version badge must produce readme_version_badge=False."""
    (tmp_path / "README.md").write_text(
        "# My Project\n\nThis is a prototype.\n",
        encoding="utf-8",
    )
    result = assess_release_readiness(tmp_path, version="v1.0.0-alpha")
    badge_check = next((c for c in result["checks"] if c["name"] == "readme_version_badge"), None)
    link_check = next((c for c in result["checks"] if c["name"] == "readme_release_link"), None)
    assert badge_check is not None and badge_check["ok"] is False
    assert link_check is not None and link_check["ok"] is False


def test_release_readiness_readme_with_badge_passes_badge_checks(tmp_path):
    """Unit: README containing version string and release link passes those specific checks."""
    (tmp_path / "README.md").write_text(
        "# My Project 1.0.0-alpha\n\n"
        "See [release notes](docs/releases/v1.0.0-alpha.md).\n\n"
        "This is a prototype.\n",
        encoding="utf-8",
    )
    result = assess_release_readiness(tmp_path, version="v1.0.0-alpha")
    badge_check = next(c for c in result["checks"] if c["name"] == "readme_version_badge")
    link_check = next(c for c in result["checks"] if c["name"] == "readme_release_link")
    assert badge_check["ok"] is True
    assert link_check["ok"] is True
    # Overall ok is False (missing docs/ files) — which is expected and correct
    assert result["ok"] is False
