"""Completed work can still bind future work; completion does not expire rules.

The reviewed ranges are an independent inventory of the real source, not copied
PLAN text. Fixture expectations exercise the explicit wording policy separately
from that inventory. Historical narrative without a lexical limit stays indexed.
"""
import re
from pathlib import Path

import pytest

from governance_tools.state_generator import parse_plan_tasks
from scripts import plan_summary


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "PLAN.md"
COMPLETED_BOUNDARY_RANGES = {
    653: 658, 659: 661, 683: 686, 729: 733, 743: 755, 764: 771,
    772: 779, 780: 790, 794: 808, 810: 832, 864: 867, 980: 980,
    991: 997, 998: 1004, 1005: 1012, 1071: 1075, 1308: 1309,
    1383: 1403, 1442: 1446, 1455: 1466, 1475: 1484, 1491: 1494,
    1495: 1540, 1576: 1578, 1583: 1584, 1615: 1619, 1625: 1630,
    1631: 1632, 1634: 1641, 1700: 1701,
    1702: 1703, 1706: 1715, 1723: 1733, 1748: 1758, 1762: 1768,
    1773: 1780, 1786: 1835, 1805: 1810, 1811: 1822, 1823: 1835,
    1858: 1862, 1863: 1865, 1866: 1868, 1869: 1871, 1997: 2005,
    2053: 2083, 2098: 2109,
    2111: 2124, 2126: 2140, 2158: 2178, 2180: 2200, 2202: 2239,
    2241: 2266, 2268: 2274, 2276: 2288, 2290: 2306, 2321: 2357, 2359: 2423,
    2425: 2492, 2494: 2550, 2552: 2575, 2577: 2612, 2614: 2641,
    2643: 2663, 2665: 2697, 2699: 2709, 2862: 2874, 2876: 2889,
}


def _completed_section(human):
    return human.split("## Standing boundaries recorded in completed items\n", 1)[1].split(
        "## Authorization, navigation and standing constraints", 1)[0]


def test_real_plan_every_matching_completed_boundary_has_full_text_in_its_section():
    text = PLAN.read_text(encoding="utf-8")
    lines = text.splitlines()
    matching = {t["line"]: t["end_line"] for t in parse_plan_tasks(text)
                if t["done"] and plan_summary._completed_boundary_signals(t["text"])}
    assert matching == COMPLETED_BOUNDARY_RANGES, "Review the inventory when PLAN or the wording rule changes"
    summary = plan_summary.build_plan_summary(PLAN, ROOT)
    actual = {t["line"]: t for t in summary["completed_item_boundaries"]}
    assert set(actual) == set(matching)
    section = _completed_section(plan_summary.format_human(summary))
    for start, end in COMPLETED_BOUNDARY_RANGES.items():
        expected = "\n".join(lines[start - 1:end])
        assert re.match(r"\s*[-+*] \[[xX]\]", lines[start - 1])
        assert actual[start]["end_line"] == end
        assert actual[start]["text"] == expected
        assert actual[start]["done"] is True
        assert actual[start]["status"] == "done"
        assert f"PLAN.md:{start}-{end} | completed |" in section
        assert expected in section, f"Missing full completed boundary at PLAN.md:{start}-{end}"
    # These were missed by the original evaluation; neither becomes pending work.
    assert {659, 1702}.issubset(actual)
    assert {t["line"] for t in summary["open_items"]}.isdisjoint(actual)


@pytest.mark.parametrize("prose", [
    "Do not create a parallel authority map.",
    "Changes MUST NOT widen the scope.",
    "The tool shall not promote old warnings.",
    "A reviewer should not claim live coverage.",
    "A sample may not be reused.",
    "Never claim effectiveness from this result.",
    "Never prove an approval by inference.",
    "Never authorize a run from old evidence.",
    "Advisory only; never blocks.",
    "Live execution remains unauthorized.",
    "A new run is not currently authorized.",
    "The retry is not yet authorised.",
    "A retry is not allowed.",
    "Live execution is not currently permitted.",
    "No further census action is currently authorized.",
    "Claim ceiling: offline synthetic evidence only.",
    "NOT_CLAIMED: runtime correctness.",
    "Not claimed: future freshness prevented.",
    "Independent outcomes remain unclaimed.",
    "This cannot claim handle-bound verification.",
    "This result cannot prove comprehension.",
    "A receipt cannot establish framework correctness.",
    "A directory swap cannot be excluded by these checks.",
    "This does not authorize implementation.",
    "The result does not claim coverage of any later tip.",
    "A test does not prove production safety.",
    "This evidence does not establish treatment effectiveness.",
    "The preregistration does not approve a run.",
    "Reopen only after a natural failure.",
    "Proceed only if the owner approves.",
    "Start only once independent review exists.",
    "Publish only when the canonical conditions hold.",
    "Use only with separate approval.",
    "Consumer proof is required before any release-prep slice.",
    "Independent review is mandatory before execution.",
    "A new run requires separate owner approval.",
    "Promotion needs explicit authorization.",
    "The next slice is pending separate explicit owner authority.",
    "No promotion without separate approval.",
    "Separate approval is required.",
    "Owner authority required.",
    "The agent must obtain separate approval before a run.",
    "A change shall be approved before publication.",
    "Every run must retain a matching package check.",
    "The manifest must reuse or extend the existing baseline.",
    "Continuation requires a separate preregistration.",
    "Implementation needs fresh scorer authority.",
    "Hooks are advisory only.",
    "Historical warnings are warning-only.",
    "The migration is deferred until a real membership change.",
    "Publication remains gated.",
    "Implementation stays blocked.",
    "Hooks remain advisory.",
    "The result is still warning-only.",
    "The draft is gated behind fail-closed refusal.",
    # Conservative by design: quoting an imperative does not prove its expiry.
    "The completed review recorded 'do not retry' as its finding.",
])
def test_explicit_completed_boundary_wording_is_carried_even_under_history(prose):
    text = "# Plan\n## Historical tasks\n- [x] " + prose + "\n## Other\n- [x] Wrote the changelog.\n"
    summary = plan_summary._fidelity_context(text)
    assert [t["line"] for t in summary["completed_item_boundaries"]] == [3]
    item = summary["completed_item_boundaries"][0]
    assert item["text"] == "- [x] " + prose
    assert item["end_line"] == 3
    assert item["historical"] is True
    assert item["boundary_signals"]
    assert "These items grant no new authority" in summary["completed_item_boundary_rule"]


@pytest.mark.parametrize("prose", [
    "Generated the report and added the tests.",
    "The completed slice did not execute a live run.",
    "The completed run did not require a retry.",
    "The completed run did need another fixture.",
    "The parser was not changed.",
    "The design was never executed.",
    "No files were modified.",
    "Only the report was updated.",
    "The owner authorized the completed slice.",
    "Approval was received before the completed run.",
    "Added a field before any report was rendered.",
    "The old error no longer appears.",
    "Closed the documentation phase with claim ceilings.",
    "The report indexes cannot-claim headings.",
    "The description contains the words 'do nothing'.",
])
def test_finished_work_narratives_without_explicit_boundary_stay_out(prose):
    summary = plan_summary._fidelity_context("# Plan\n## Completed\n- [x] " + prose + "\n")
    assert summary["completed_item_boundaries"] == []
    assert summary["section_index"][-1]["coverage"] == "indexed"


def test_completed_boundary_keeps_wrapping_nested_conditions_and_exact_ranges(tmp_path):
    text = ("# Plan\n## Historical tasks\n- [X] Decision recorded.\n"
            "  Do not promote warnings\n  without separate approval.\n"
            "  - [x] Claim ceiling:\n    point-in-time consistency only.\n\n"
            "    No future guarantee.\n- [x] Generated the report.\n")
    path = tmp_path / "PLAN.md"
    path.write_text(text, encoding="utf-8")
    summary = plan_summary.build_plan_summary(path, tmp_path)
    items = summary["completed_item_boundaries"]
    assert [(t["line"], t["end_line"]) for t in items] == [(3, 9), (6, 9)]
    section = _completed_section(plan_summary.format_human(summary))
    for item in items:
        assert item["text"] == "\n".join(text.splitlines()[item["line"] - 1:item["end_line"]])
        assert item["text"] in section
        assert f"PLAN.md:{item['line']}-{item['end_line']}" in section
    assert "Generated the report." not in section
    assert summary["open_items"] == []
    # Coverage must include the newly carried completed items, but the history
    # heading and nonmatching narrative are still only indexed.
    assert summary["section_index"][-1]["coverage"] == "partial"


def test_fenced_restrictions_are_examples_not_completed_boundaries():
    text = ("# Plan\n```markdown\n- [x] Do not retry.\n```\n## Completed\n"
            "- [x] Documented a diagnostic example:\n  ```text\n"
            "  Do not retry.\n  ```\n  Example output only.\n")
    summary = plan_summary._fidelity_context(text)
    assert summary["completed_item_boundaries"] == []


def test_completed_boundary_signal_does_not_join_unrelated_clauses():
    summary = plan_summary._fidelity_context(
        "# Plan\n- [x] Tests required new fixtures. Before that, the file was empty.\n"
        "- [x] The old parser required UTF-8. Owner approval was recorded yesterday.\n")
    assert summary["completed_item_boundaries"] == []
