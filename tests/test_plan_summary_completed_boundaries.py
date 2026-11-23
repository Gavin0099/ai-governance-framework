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
    856: 859, 2379: 2383,
}
# Explicit retained or superseding condition ranges from the original completed
# sources. Their full source text must survive even after checkbox-to-prose moves.
RELOCATED_CONSTRAINT_RANGES = [
    (97, 110), (116, 127), (133, 147), (153, 165), (186, 210),
    (216, 237), (243, 283), (289, 315), (321, 354), (360, 387),
    (413, 430), (432, 446), (448, 461), (463, 477), (514, 520),
    (532, 544), (555, 560), (566, 579), (581, 594), (637, 659),
    (687, 693), (695, 710), (730, 742), (753, 757), (759, 780),
    (782, 791), (793, 807), (851, 854), (903, 907), (946, 951),
    (977, 985), (987, 994), (1002, 1011), (1028, 1035), (1037, 1048),
    (1050, 1059), (1078, 1084), (1086, 1090), (1092, 1096), (1133, 1151),
    (1153, 1163), (1165, 1178), (1180, 1192), (1194, 1207), (1209, 1228),
    (1234, 1247), (1249, 1275), (1277, 1292), (1298, 1302), (1304, 1318),
    (1320, 1334), (1342, 1360), (1362, 1408), (1410, 1451), (1453, 1474),
    (1476, 1487), (1489, 1506), (1508, 1519), (1521, 1538), (1540, 1555),
    (1557, 1562), (1598, 1605), (1666, 1669), (1671, 1681), (1714, 1719),
    (1729, 1732), (1734, 1739), (1765, 1770), (1780, 1784), (1795, 1798),
    (1800, 1803), (1809, 1812), (1818, 1821), (1827, 1831), (1833, 1837),
    (1848, 1891), (1906, 1911), (1913, 1918), (1920, 1924), (1954, 1960),
    (1968, 1973), (2023, 2029), (2243, 2250), (2258, 2261), (2280, 2287),
    (2370, 2377), (2404, 2409), (2445, 2450), (2515, 2518), (2563, 2573),
    (2575, 2581), (2583, 2590), (2592, 2599), (2684, 2693), (2695, 2705),
    (2729, 2740), (2760, 2762), (2834, 2840), (2885, 2898), (2904, 2914),
    (2923, 2932), (2991, 2993), (2995, 3024), (3108, 3112), (3237, 3249),
    (3320, 3338),
]


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
    assert {856, 2379}.issubset(actual)
    assert {t["line"] for t in summary["open_items"]}.isdisjoint(actual)


def test_real_plan_relocated_completed_constraints_keep_their_full_effective_text():
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    summary = plan_summary.build_plan_summary(PLAN, ROOT)
    human = plan_summary.format_human(summary)
    spans = (summary["carried_sections"] + summary["open_items"]
             + summary["completed_item_boundaries"])
    for start, end in RELOCATED_CONSTRAINT_RANGES:
        expected = "\n".join(lines[start - 1:end]).rstrip()
        assert expected in human, f"Missing relocated constraint at PLAN.md:{start}-{end}"
        assert any(span["line"] <= start and span["end_line"] >= end
                   for span in spans)


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
