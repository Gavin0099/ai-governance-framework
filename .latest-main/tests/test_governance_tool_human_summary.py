from governance_tools.human_summary import build_summary_line


def test_build_summary_line_skips_empty_parts() -> None:
    assert build_summary_line("ok=True", None, "checks=3", "") == "summary=ok=True | checks=3"
