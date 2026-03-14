import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.release_readiness import assess_release_readiness, format_human_result


def test_release_readiness_passes_for_current_alpha():
    result = assess_release_readiness(Path(".").resolve(), version="v1.0.0-alpha")

    assert result["ok"] is True
    assert any(item["name"] == "release_note" and item["ok"] for item in result["checks"])
    assert any(item["name"] == "readme_release_link" and item["ok"] for item in result["checks"])


def test_release_readiness_human_output_is_scannable():
    result = assess_release_readiness(Path(".").resolve(), version="v1.0.0-alpha")
    output = format_human_result(result)

    assert "[release_readiness]" in output
    assert "version=v1.0.0-alpha" in output
    assert "check[release_note]=True" in output
