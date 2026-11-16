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
    740: 743, 2095: 2099,
}
# Explicit retained or superseding condition ranges from the original completed
# sources. Their full source text must survive even after checkbox-to-prose moves.
RELOCATED_CONSTRAINT_RANGES = [
    (428, 434), (446, 456), (467, 472), (478, 491), (493, 506),
    (549, 571), (599, 605), (607, 615), (635, 642), (653, 657),
    (659, 680), (682, 691), (735, 738), (787, 791), (830, 835),
    (861, 869), (871, 878), (886, 895), (912, 919), (921, 932),
    (934, 943), (962, 968), (970, 974), (976, 980), (1017, 1028),
    (1038, 1044), (1046, 1051), (1062, 1074), (1080, 1093), (1095, 1121),
    (1123, 1138), (1144, 1148), (1150, 1164), (1166, 1180), (1188, 1206),
    (1208, 1251), (1253, 1294), (1296, 1317), (1319, 1330), (1332, 1349),
    (1351, 1362), (1364, 1377), (1379, 1394), (1396, 1401), (1502, 1505),
    (1507, 1517), (1959, 1966), (1974, 1977), (1996, 2003), (2086, 2093),
    (2120, 2125), (2161, 2166), (2231, 2234), (2279, 2286), (2288, 2294),
    (2296, 2303), (2388, 2392), (2394, 2399), (2423, 2434), (2454, 2456),
    (2528, 2534), (2583, 2593), (2602, 2611), (2670, 2672),
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
    assert {740, 2095}.issubset(actual)
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
