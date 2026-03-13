import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.change_control_index import build_change_control_index


def test_change_control_index_lists_generated_artifacts(tmp_path):
    (tmp_path / "claude_change_control_summary.txt").write_text(
        "[change_control_summary]\nsummary=task=Refactor boundary | proposal_risk=medium | promoted=False\n",
        encoding="utf-8",
    )
    (tmp_path / "claude_session_start.txt").write_text("handoff", encoding="utf-8")
    (tmp_path / "claude_session_start.json").write_text("{}", encoding="utf-8")

    output = build_change_control_index(tmp_path)

    assert "[change_control_index]" in output
    assert "summary=change_control_summaries=1 | session_start_notes=1 | session_start_envelopes=1" in output
    assert "[review_order]" in output
    assert "claude_change_control_summary.txt | summary=task=Refactor boundary | proposal_risk=medium | promoted=False" in output
    assert "claude_session_start.txt" in output
    assert "claude_session_start.json" in output
