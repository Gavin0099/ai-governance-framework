"""Acceptance oracles come from the requested PLAN fidelity contract.

The real-source ranges below are a reviewed inventory, not a PLAN copy or a
second parser. A planning edit can legitimately require updating that inventory.
"""
import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts import plan_summary
from governance_tools import state_generator

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "PLAN.md"
OPEN_RANGES = {
    188: 188, 461: 464, 791: 792, 868: 870, 876: 878, 879: 881,
    1721: 1722, 1738: 1741, 1742: 1742, 1743: 1744,
    1769: 1770, 1771: 1772, 1836: 1838, 1927: 1928, 1929: 1930,
    1931: 1932, 2006: 2040,
}
# Explicit named safety sections plus inline claim paragraphs. Their bodies,
# including tables, wrapped conditions and nested sections, are the oracle.
CONSTRAINT_RANGES = [
    (152, 158), (175, 181), (218, 223), (468, 470), (483, 486),
    (498, 500), (564, 570), (601, 607), (883, 903), (1060, 1063),
    (1077, 1082), (1083, 1278), (1295, 1298), (1321, 1326),
    (1415, 1451), (1613, 1657), (1856, 1877), (2042, 2051),
    (2711, 2776), (2801, 2836), (2846, 2860), (2891, 2897),
    (2924, 2931), (2933, 2981), (3003, 3021), (3023, 3034),
]


@pytest.fixture(scope="module")
def real_summary():
    return plan_summary.build_plan_summary(PLAN, ROOT)


def _build(tmp_path, text):
    plan = tmp_path / "PLAN.md"
    plan.write_text(text, encoding="utf-8")
    return plan_summary.build_plan_summary(plan, tmp_path)


def test_real_plan_every_current_checkbox_has_exact_full_text_and_lines(real_summary):
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    # No unchecked/in-progress examples occur in the current file's historical
    # sections. Scan the actual file independently to catch any newly lost item.
    observed = {n for n, line in enumerate(lines, 1) if re.match(r"\s*- \[[ >~]\]", line)}
    assert observed == set(OPEN_RANGES), "Review the inventory when PLAN changes"
    actual = {item["line"]: item for item in real_summary["open_items"]}
    assert set(actual) == observed
    human = plan_summary.format_human(real_summary)
    for start, end in OPEN_RANGES.items():
        expected = "\n".join(lines[start - 1:end])
        assert actual[start]["end_line"] == end
        assert actual[start]["text"] == expected
        assert expected in human
        assert f"PLAN.md:{start}-{end}" in human
    assert actual[461]["status"] == "in_progress"
    assert actual[2006]["priority"] == "P3"
    assert real_summary["backlog_open"] == {"P0": 0, "P1": 4, "P2": 6}
    assert state_generator.parse_backlog_counts("\n".join(lines)) == real_summary["backlog_open"]


def test_real_plan_constraint_sections_carry_content_not_just_titles(real_summary):
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    human = plan_summary.format_human(real_summary)
    for start, end in CONSTRAINT_RANGES:
        # Ignore terminal blank lines when the merged excerpt stops at the last
        # substantive line; every source content line must remain verbatim.
        expected = "\n".join(lines[start - 1:end]).rstrip()
        assert expected in human, f"Missing safety content at PLAN.md:{start}-{end}"
        assert any(span["line"] <= start and span["end_line"] >= end - (not lines[end - 1].strip())
                   for span in real_summary["carried_sections"])


def test_real_plan_index_is_valid_gap_free_and_contains_every_markdown_heading(real_summary):
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    sections = real_summary["section_index"]
    assert sections[0]["line"] == 1
    assert sections[-1]["end_line"] == len(lines)
    cursor = 1
    for section in sections:
        assert section["line"] == cursor
        assert section["line"] <= section["end_line"] <= len(lines)
        cursor = section["end_line"] + 1
        if section["kind"] == "markdown":
            assert section["line"] <= section["subtree_end_line"] <= len(lines)
            assert section["heading"] in lines[section["line"] - 1]
    expected = {n for n, line in enumerate(lines, 1) if re.match(r"^#{1,6}\s", line)}
    assert {s["line"] for s in sections if s["kind"] == "markdown"} == expected
    assert "only indexed" in real_summary["read_rule"]
    assert real_summary["source"] == {
        "sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "bytes": len(PLAN.read_bytes()), "lines": len(lines),
    }


def test_real_plan_decisions_have_date_effect_and_source_range(real_summary):
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    decisions = {d["line"]: d for d in real_summary["decision_index"]}
    # Authorizations, decided priorities, and the append-only owner decisions
    # carry audit authority even when their engineering work is completed.
    for start in [5, 21, 38, 58, 71, 84, 112, 1563, 1634, 1840, 1878, 3036,
                  3048, 3063, 3073, 3143, 3176, 3259, 3288, 3406]:
        decision = decisions[start]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision["date"])
        assert decision["effect"]
        assert "\n" not in decision["effect"]
        assert start <= decision["effect_line"] <= decision["end_line"] <= len(lines)
        assert decision["heading"] in " ".join(lines[start - 1:start + 2])


def test_real_plan_legacy_keys_keep_types_and_phase_e_uses_current_sprint(real_summary):
    expected = {
        "generated_at": str, "head_commit": str, "plan_path": str,
        "last_updated": str, "owner": str, "current_phase": dict,
        "gate_status": dict, "open_sprint_items": list, "open_phase_e_tasks": list,
        "active_blockers": list, "backlog_open": dict, "sa_layer1_log": list,
        "sa_layer1_stability": str, "phase2_gate_conditions": list,
        "recent_decisions": list, "plan_context_provenance": dict,
    }
    for key, kind in expected.items():
        assert isinstance(real_summary[key], kind)
    assert real_summary["current_phase"]["id"] == "PhaseE"
    assert len(real_summary["open_sprint_items"]) == 5
    assert real_summary["open_phase_e_tasks"] == real_summary["open_sprint_items"]
    assert "reviewed." in real_summary["open_sprint_items"][2]


def test_summary_preserves_nested_constraints_and_excludes_explicit_history(tmp_path):
    text = ("# Plan\n## Current Sprint\n### Live\n- [>] Work\n"
            "  condition one\n  - [ ] Nested\n    condition two\n\n"
            "  paragraph three\n- [~] Another\n  tail\n"
            "### Historical tasks\n- [ ] Old task\n## Pending Work - Ordered\n"
            "P2 - New work:\n- [ ] Current task\n")
    s = _build(tmp_path, text)
    assert [(t["line"], t["end_line"], t["status"]) for t in s["open_items"]] == [
        (4, 9, "in_progress"), (6, 7, "open"), (10, 11, "in_progress"), (16, 16, "open")]
    assert s["open_items"][0]["text"] == "\n".join(text.splitlines()[3:9])
    assert s["open_items"][-1]["priority"] == "P2"


def test_fenced_examples_do_not_create_headings_or_work(tmp_path):
    s = _build(tmp_path, "# Plan\n~~~markdown\n## Bogus\n- [ ] Example\n~~~\n"
               "## Current Sprint\n- [ ] Real\n  ```text\n  ## Still example\n"
               "  - [ ] Not a task\n  ```\n  complete condition\n")
    assert [t["line"] for t in s["open_items"]] == [7]
    assert s["open_items"][0]["end_line"] == 12
    assert {h["heading"] for h in s["section_index"]} == {"Plan", "Current Sprint"}
    assert s["section_index"][-1]["coverage"] == "partial"


def test_wrapped_labels_and_nested_safety_sections_are_carried(tmp_path):
    s = _build(tmp_path, "## Pending Work - Ordered\nP1-F - standing policy\n"
               "(decided 2026-06-12):\n- [ ] Wait\n  until approved.\n\n"
               "## Active Claim Boundaries\n### Scope\nNo expansion.\n\n"
               "Claim ceiling:\n\n- Cannot claim success.\n  Until proved.\n\n"
               "## Other\nUnrelated history.\n")
    human = plan_summary.format_human(s)
    assert "P1-F - standing policy (decided 2026-06-12)" in human
    assert "### Scope\nNo expansion." in human
    assert "- Cannot claim success.\n  Until proved." in human
    assert s["section_index"][-1]["coverage"] == "indexed"
    assert "Unrelated history." not in human


def test_decision_effect_keeps_wrapped_sentence_and_never_grants_authority(tmp_path):
    s = _build(tmp_path, "# Plan\n## Owner adoption — 2026-09-06\n\n"
               "Owner adopts the exact\nreviewed input, conditional on a new approval.\n"
               "No production is authorized.\n")
    d = s["decision_index"][0]
    assert d["effect"] == "Owner adopts the exact reviewed input, conditional on a new approval."
    assert (d["line"], d["end_line"], d["date"]) == (2, 6, "2026-09-06")
    assert "No production is authorized." in plan_summary.format_human(s)
    assert "not complete grants of authority" in s["read_rule"]


def test_dated_context_with_child_labels_has_effect_inside_whole_context(tmp_path):
    s = _build(tmp_path, "## Current Sprint\nCurrent refresh - 2026-09-06:\n\n"
               "Theme:\n\nKeep the existing boundary.\n\nCurrent refresh - 2026-09-07:\n"
               "\nNo expansion is authorized.\n")
    d = s["decision_index"][0]
    assert (d["line"], d["end_line"], d["effect_line"]) == (2, 7, 6)
    assert d["effect"] == "Keep the existing boundary."
    assert s["section_index"][1]["end_line"] == 3


def test_legacy_decision_table_and_cli_options_remain_available(tmp_path, monkeypatch, capsys):
    plan = tmp_path / "PLAN.md"
    plan.write_text("## 決策紀錄\n| 日期 | 決策 | 說明 |\n|---|---|---|\n"
                    "| 2026-04-15 | Keep advisory | No blocker |\n", encoding="utf-8")
    output = tmp_path / "view.json"
    monkeypatch.setattr("sys.argv", ["plan_summary", "--plan", str(plan), "--format", "json", "--out", str(output)])
    plan_summary.main()
    s = json.loads(output.read_text(encoding="utf-8"))
    assert s["recent_decisions"] == [{"date": "2026-04-15", "decision": "Keep advisory", "note": "No blocker"}]
    assert str(output) in capsys.readouterr().out
    sidecar = tmp_path / plan_summary._PROVENANCE_SIDECAR_PATH
    assert json.loads(sidecar.read_text(encoding="utf-8")) == plan_summary._PLAN_CONTEXT_PROVENANCE


def test_cli_stdout_writes_existing_provenance_but_builder_does_not(tmp_path, monkeypatch, capsys):
    _build(tmp_path, "# Plan\n")
    sidecar = tmp_path / plan_summary._PROVENANCE_SIDECAR_PATH
    assert not sidecar.exists()
    monkeypatch.setattr("sys.argv", ["plan_summary", "--plan", str(tmp_path / "PLAN.md")])
    plan_summary.main()
    assert capsys.readouterr().out.splitlines()[0] == plan_summary._PROVENANCE_MARKER
    assert json.loads(sidecar.read_text(encoding="utf-8")) == plan_summary._PLAN_CONTEXT_PROVENANCE


def test_missing_plan_fails_without_sidecar(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["plan_summary", "--plan", str(tmp_path / "missing.md")])
    with pytest.raises(SystemExit) as error:
        plan_summary.main()
    assert error.value.code == 1
    assert "not found" in capsys.readouterr().err
    assert not (tmp_path / plan_summary._PROVENANCE_SIDECAR_PATH).exists()


def test_sidecar_failure_stays_nonblocking(tmp_path, monkeypatch, capsys):
    _build(tmp_path, "# Plan\n")
    (tmp_path / "artifacts").write_text("file, not directory", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["plan_summary", "--plan", str(tmp_path / "PLAN.md"), "--format", "json"])
    plan_summary.main()
    assert json.loads(capsys.readouterr().out)["plan_context_provenance"] == plan_summary._PLAN_CONTEXT_PROVENANCE


@pytest.mark.parametrize("text, ranges", [("", []), ("preamble", [(1, 1)]),
    ("preamble\n\n## Work\nbody\n### Child\nmore\n", [(1, 2), (3, 4), (5, 6)])])
def test_index_empty_preamble_and_nested_heading_boundaries(tmp_path, text, ranges):
    s = _build(tmp_path, text)
    assert [(x["line"], x["end_line"]) for x in s["section_index"]] == ranges
