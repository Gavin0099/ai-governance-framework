import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_proposal_builder import build_change_proposal, format_human_result


@pytest.fixture
def local_change_proposal_root():
    path = Path("tests") / "_tmp_change_proposal"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_change_proposal_builder_includes_suggestions_and_impact(local_change_proposal_root):
    (local_change_proposal_root / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8")
    (local_change_proposal_root / "MainWindow.axaml.cs").write_text(
        "using Avalonia.Threading;\npublic class MainWindow {}", encoding="utf-8"
    )

    before_file = local_change_proposal_root / "application" / "before.cs"
    after_file = local_change_proposal_root / "application" / "after.cs"
    before_file.parent.mkdir(parents=True, exist_ok=True)
    before_file.write_text("public class Service { public int Run() => 1; }\n", encoding="utf-8")
    after_file.write_text(
        "public class Service { public int Run() => 1; public int Ping() => 0; }\n",
        encoding="utf-8",
    )

    result = build_change_proposal(
        project_root=local_change_proposal_root,
        task_text="Refactor Avalonia boundary",
        rules="common,refactor",
        impact_before_files=[before_file],
        impact_after_files=[after_file],
    )

    assert result["requested_rules"] == ["common", "refactor"]
    assert result["suggested_rules_preview"] == ["common", "csharp", "avalonia", "refactor"]
    assert result["proposal_guidance"]["recommended_risk"] == "medium"
    assert "public_api_diff_checker" in result["proposal_guidance"]["expected_validators"]
    assert result["proposal_summary"]["recommended_risk"] == "medium"
    assert result["proposal_summary"]["requested_rules"] == ["common", "refactor"]


def test_change_proposal_builder_human_output_is_actionable(local_change_proposal_root):
    result = build_change_proposal(
        project_root=local_change_proposal_root,
        task_text="Implement feature without impact files",
        rules="common",
    )

    output = format_human_result(result)
    assert "[change_proposal]" in output
    assert "task=Implement feature without impact files" in output
    assert "requested_rules=common" in output
