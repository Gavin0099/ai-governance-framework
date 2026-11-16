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
    29: 29, 1824: 1837, 1845: 1852, 1860: 1872, 1880: 1886,
    1894: 1899, 1907: 1912, 1920: 1927, 1947: 1951, 1959: 1966,
    1974: 1977, 1985: 1988, 1996: 2003, 2021: 2024, 2032: 2039,
    2047: 2051, 2073: 2078, 2913: 2913,
}
# Explicit named safety sections plus inline claim paragraphs. Their bodies,
# including tables, wrapped conditions and nested sections, are the oracle.
# These ranges cover the reviewed verbatim condition/scope excerpts after the
# history cutover; completed-source limits also have a relocation inventory in
# test_plan_summary_completed_boundaries. No range is derived from the parser.
CONSTRAINT_RANGES = [
    (3, 26), (31, 31), (35, 35), (39, 39), (41, 47),
    (49, 54), (56, 62), (64, 68), (70, 75), (77, 83),
    (85, 87), (89, 91), (95, 95), (97, 107), (111, 111),
    (113, 117), (121, 121), (123, 131), (135, 135), (137, 144),
    (148, 148), (150, 159), (163, 163), (165, 177), (181, 181),
    (183, 198), (202, 202), (204, 239), (243, 243), (245, 264),
    (268, 268), (270, 298), (302, 302), (304, 325), (329, 329),
    (331, 345), (349, 349), (351, 360), (362, 370), (372, 379),
    (381, 391), (393, 403), (407, 407), (409, 422), (426, 426),
    (428, 434), (436, 444), (446, 456), (458, 465), (467, 472),
    (476, 476), (478, 491), (493, 506), (508, 511), (513, 524),
    (528, 528), (530, 534), (536, 547), (549, 571), (573, 577),
    (579, 597), (599, 605), (607, 615), (619, 619), (621, 626),
    (628, 633), (635, 642), (644, 651), (653, 657), (659, 680),
    (682, 691), (693, 728), (730, 733), (735, 738), (747, 747),
    (749, 758), (760, 767), (769, 774), (776, 779), (781, 785),
    (787, 791), (793, 797), (799, 802), (804, 820), (822, 828),
    (830, 835), (837, 843), (847, 847), (849, 859), (861, 869),
    (871, 878), (880, 884), (886, 895), (897, 902), (904, 910),
    (912, 919), (921, 932), (934, 943), (945, 951), (953, 960),
    (962, 968), (970, 974), (976, 980), (982, 987), (989, 995),
    (997, 1002), (1004, 1011), (1015, 1015), (1017, 1028), (1030, 1036),
    (1038, 1044), (1046, 1051), (1053, 1060), (1062, 1074), (1078, 1078),
    (1080, 1093), (1095, 1121), (1123, 1138), (1142, 1142), (1144, 1148),
    (1150, 1164), (1166, 1180), (1182, 1186), (1188, 1206), (1208, 1251),
    (1253, 1294), (1296, 1317), (1319, 1330), (1332, 1349), (1351, 1362),
    (1364, 1377), (1379, 1394), (1396, 1401), (1403, 1408), (1410, 1414),
    (1416, 1419), (1421, 1428), (1430, 1435), (1437, 1441), (1443, 1450),
    (1452, 1455), (1457, 1460), (1462, 1467), (1469, 1474), (1476, 1478),
    (1480, 1496), (1500, 1500), (1502, 1505), (1507, 1517), (1519, 1526),
    (1530, 1530), (1532, 1536), (1538, 1540), (1542, 1544), (1546, 1548),
    (1550, 1552), (1554, 1556), (1558, 1560), (1562, 1566), (1568, 1570),
    (1572, 1574), (1576, 1580), (1582, 1584), (1586, 1588), (1590, 1592),
    (1594, 1596), (1598, 1601), (1603, 1605), (1607, 1609), (1611, 1613),
    (1615, 1617), (1619, 1621), (1623, 1625), (1627, 1629), (1631, 1634),
    (1636, 1638), (1640, 1642), (1644, 1647), (1651, 1651), (1653, 1656),
    (1658, 1661), (1663, 1665), (1667, 1670), (1672, 1676), (1678, 1682),
    (1686, 1686), (1688, 1693), (1695, 1698), (1700, 1704), (1706, 1709),
    (1711, 1716), (1718, 1723), (1725, 1731), (1735, 1735), (1737, 1740),
    (1742, 1747), (1751, 1751), (1753, 1757), (1759, 1763), (1769, 1769),
    (1780, 1780), (1781, 1781), (1788, 1788), (1793, 1793), (1795, 1808),
    (1810, 1810), (1812, 1812), (1816, 1816), (1820, 1820), (1841, 1841),
    (1856, 1856), (1876, 1876), (1890, 1890), (1903, 1903), (1916, 1916),
    (1931, 1931), (1935, 1939), (1943, 1943), (1955, 1955), (1970, 1970),
    (1981, 1981), (1992, 1992), (2007, 2007), (2011, 2013), (2017, 2017),
    (2028, 2028), (2043, 2043), (2055, 2055), (2059, 2065), (2069, 2069),
    (2084, 2084), (2086, 2093), (2101, 2106), (2108, 2112), (2114, 2118),
    (2120, 2125), (2127, 2132), (2134, 2139), (2141, 2146), (2148, 2152),
    (2154, 2159), (2161, 2166), (2168, 2188), (2190, 2204), (2206, 2210),
    (2212, 2216), (2218, 2222), (2224, 2229), (2231, 2234), (2236, 2239),
    (2241, 2244), (2246, 2251), (2255, 2255), (2257, 2263), (2265, 2270),
    (2272, 2277), (2279, 2286), (2288, 2294), (2296, 2303), (2305, 2311),
    (2313, 2323), (2325, 2336), (2338, 2352), (2354, 2359), (2363, 2363),
    (2365, 2371), (2373, 2378), (2380, 2386), (2388, 2392), (2394, 2399),
    (2401, 2409), (2411, 2421), (2423, 2434), (2438, 2438), (2440, 2443),
    (2445, 2448), (2450, 2452), (2454, 2456), (2458, 2461), (2463, 2467),
    (2469, 2473), (2475, 2479), (2481, 2486), (2488, 2493), (2497, 2497),
    (2499, 2503), (2505, 2510), (2512, 2516), (2518, 2522), (2526, 2526),
    (2528, 2534), (2536, 2545), (2547, 2555), (2557, 2563), (2565, 2573),
    (2575, 2577), (2581, 2581), (2583, 2593), (2595, 2600), (2602, 2611),
    (2615, 2615), (2617, 2622), (2624, 2628), (2630, 2634), (2636, 2640),
    (2642, 2649), (2651, 2659), (2661, 2668), (2670, 2672), (2674, 2688),
    (2690, 2701), (2705, 2705), (2707, 2714), (2716, 2725), (2727, 2735),
    (2737, 2747), (2751, 2751), (2753, 2757), (2759, 2763), (2765, 2770),
    (2772, 2777), (2779, 2783), (2785, 2789), (2793, 2793), (2795, 2797),
    (2799, 2801), (2803, 2805), (2807, 2810), (2812, 2816), (2818, 2822),
    (2824, 2828), (2830, 2833), (2835, 2839), (2841, 2844), (2846, 2849),
    (2851, 2854), (2860, 2860), (2862, 2869), (2871, 2879), (2881, 2886),
    (2888, 2893), (2895, 2905), (2917, 2917), (2919, 2921), (2923, 2925),
    (2927, 2929), (2931, 2933), (2935, 2937), (2939, 2944), (2946, 2951),
    (2953, 2962), (2968, 2968), (2970, 2974), (2976, 2992), (2998, 2998),
    (3000, 3000), (3002, 3007), (3012, 3012), (3014, 3017), (3019, 3022),
    (3024, 3027), (3029, 3032), (3034, 3037), (3039, 3042), (3044, 3054),
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
    assert actual[29]["status"] == "in_progress"
    assert actual[2021]["priority"] == "P3"
    assert real_summary["backlog_open"] == {"P0": 0, "P1": 5, "P2": 8}
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
    for start in [37, 93, 109, 119, 133, 146, 161, 179, 200, 241, 266, 300, 327, 347, 405, 424, 526, 617, 745, 845, 1076, 1498, 1528, 1649, 1684, 1733, 1749, 2082, 2253, 2361]:
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
    assert len(real_summary["open_sprint_items"]) == 1
    assert real_summary["open_phase_e_tasks"] == real_summary["open_sprint_items"]
    assert "reviewable" in real_summary["open_sprint_items"][0]


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
