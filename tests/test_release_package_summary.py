import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_package_summary import (
    assess_release_package,
    format_human_result,
    format_markdown_result,
)


def test_release_package_summary_passes_for_current_alpha():
    result = assess_release_package(Path(".").resolve(), version="v1.0.0-alpha")

    assert result["ok"] is True
    assert result["readiness"]["ok"] is True
    assert result["release_doc_count"] == 5
    assert result["status_doc_count"] == 5
    assert result["existing_release_docs"] == 5
    assert result["existing_status_docs"] >= 4
    assert any(item["name"] == "release_note" and item["exists"] for item in result["release_docs"])
    assert any(item["name"] == "generated_status_root" for item in result["status_docs"])
    assert any(item["name"] == "phase_gates" for item in result["commands"])


def test_release_package_summary_human_output_is_summary_first():
    result = assess_release_package(Path(".").resolve(), version="v1.0.0-alpha")

    rendered = format_human_result(result)

    assert rendered.startswith("summary=ok=True | version=v1.0.0-alpha")
    assert "[release_package_summary]" in rendered
    assert "[release_docs]" in rendered
    assert "[status_docs]" in rendered
    assert "[commands]" in rendered
    assert "release_readiness=python governance_tools/release_readiness.py --version v1.0.0-alpha --format human" in rendered


def test_release_package_summary_markdown_output_is_scannable():
    result = assess_release_package(Path(".").resolve(), version="v1.0.0-alpha")

    rendered = format_markdown_result(result)

    assert rendered.startswith("# Release Package Summary")
    assert "- Summary: `summary=ok=True | version=v1.0.0-alpha" in rendered
    assert "## Release Docs" in rendered
    assert "## Status Docs" in rendered
    assert "## Suggested Commands" in rendered
    assert "`python governance_tools/trust_signal_publication_reader.py --project-root . --docs-status --format human`" in rendered


def test_release_package_summary_cli_supports_direct_script_invocation():
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/release_package_summary.py",
            "--version",
            "v1.0.0-alpha",
            "--format",
            "human",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "summary=ok=True | version=v1.0.0-alpha" in result.stdout
    assert "[release_package_summary]" in result.stdout
