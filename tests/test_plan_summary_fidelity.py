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
    29: 29, 2099: 2112, 2120: 2127, 2135: 2147, 2160: 2166,
    2174: 2179, 2187: 2192, 2200: 2211, 2231: 2235, 2243: 2250,
    2258: 2261, 2269: 2272, 2280: 2287, 2305: 2308, 2316: 2323,
    2331: 2335, 2357: 2362, 3257: 3257,
}
# Explicit named safety sections plus inline claim paragraphs. Their bodies,
# including tables, wrapped conditions and nested sections, are the oracle.
# These ranges cover the reviewed verbatim condition/scope excerpts after the
# history cutover; completed-source limits also have a relocation inventory in
# test_plan_summary_completed_boundaries. No range is derived from the parser.
CONSTRAINT_RANGES = [
    (3, 26), (31, 31), (35, 35), (39, 39), (41, 47),
    (49, 54), (56, 62), (64, 68), (70, 75), (77, 83),
    (85, 87), (89, 91), (95, 95), (97, 110), (114, 114),
    (116, 127), (131, 131), (133, 147), (151, 151), (153, 165),
    (169, 169), (171, 180), (184, 184), (186, 210), (214, 214),
    (216, 237), (241, 241), (243, 283), (287, 287), (289, 315),
    (319, 319), (321, 354), (358, 358), (360, 387), (391, 391),
    (393, 407), (411, 411), (413, 430), (432, 446), (448, 461),
    (463, 477), (479, 489), (493, 493), (495, 508), (512, 512),
    (514, 520), (522, 530), (532, 544), (546, 553), (555, 560),
    (564, 564), (566, 579), (581, 594), (596, 599), (601, 612),
    (616, 616), (618, 622), (624, 635), (637, 659), (661, 665),
    (667, 685), (687, 693), (695, 710), (714, 714), (716, 721),
    (723, 728), (730, 742), (744, 751), (753, 757), (759, 780),
    (782, 791), (793, 807), (809, 844), (846, 849), (851, 854),
    (863, 863), (865, 874), (876, 883), (885, 890), (892, 895),
    (897, 901), (903, 907), (909, 913), (915, 918), (920, 936),
    (938, 944), (946, 951), (953, 959), (963, 963), (965, 975),
    (977, 985), (987, 994), (996, 1000), (1002, 1011), (1013, 1018),
    (1020, 1026), (1028, 1035), (1037, 1048), (1050, 1059), (1061, 1067),
    (1069, 1076), (1078, 1084), (1086, 1090), (1092, 1096), (1098, 1103),
    (1105, 1111), (1113, 1118), (1120, 1127), (1131, 1131), (1133, 1151),
    (1153, 1163), (1165, 1178), (1180, 1192), (1194, 1207), (1209, 1228),
    (1232, 1232), (1234, 1247), (1249, 1275), (1277, 1292), (1296, 1296),
    (1298, 1302), (1304, 1318), (1320, 1334), (1336, 1340), (1342, 1360),
    (1362, 1408), (1410, 1451), (1453, 1474), (1476, 1487), (1489, 1506),
    (1508, 1519), (1521, 1538), (1540, 1555), (1557, 1562), (1564, 1569),
    (1571, 1575), (1577, 1580), (1582, 1589), (1591, 1596), (1598, 1605),
    (1607, 1614), (1616, 1619), (1621, 1624), (1626, 1631), (1633, 1638),
    (1640, 1642), (1644, 1660), (1664, 1664), (1666, 1669), (1671, 1681),
    (1683, 1690), (1694, 1694), (1696, 1700), (1702, 1704), (1706, 1708),
    (1710, 1712), (1714, 1719), (1721, 1723), (1725, 1727), (1729, 1732),
    (1734, 1739), (1741, 1745), (1747, 1749), (1751, 1753), (1755, 1759),
    (1761, 1763), (1765, 1770), (1772, 1774), (1776, 1778), (1780, 1784),
    (1786, 1789), (1791, 1793), (1795, 1798), (1800, 1803), (1805, 1807),
    (1809, 1812), (1814, 1816), (1818, 1821), (1823, 1825), (1827, 1831),
    (1833, 1837), (1839, 1841), (1843, 1846), (1848, 1891), (1893, 1895),
    (1897, 1900), (1904, 1904), (1906, 1911), (1913, 1918), (1920, 1924),
    (1926, 1929), (1931, 1935), (1937, 1941), (1945, 1945), (1947, 1952),
    (1954, 1960), (1962, 1966), (1968, 1973), (1975, 1980), (1982, 1987),
    (1989, 1995), (1999, 1999), (2001, 2004), (2006, 2011), (2015, 2015),
    (2017, 2021), (2023, 2029), (2033, 2034), (2036, 2038),
    (2044, 2044), (2055, 2055), (2056, 2056),
    (2068, 2068), (2070, 2083), (2085, 2085), (2087, 2087), (2091, 2091),
    (2095, 2095), (2116, 2116), (2131, 2131), (2149, 2152),
    (2156, 2156), (2170, 2170),
    (2183, 2183), (2196, 2196), (2215, 2215), (2219, 2223), (2227, 2227),
    (2239, 2239), (2254, 2254), (2265, 2265), (2276, 2276), (2291, 2291),
    (2295, 2297), (2301, 2301), (2312, 2312), (2327, 2327), (2339, 2339),
    (2343, 2349), (2353, 2353), (2368, 2368), (2370, 2377), (2385, 2390),
    (2392, 2396), (2398, 2402), (2404, 2409), (2411, 2416), (2418, 2423),
    (2425, 2430), (2432, 2436), (2438, 2443), (2445, 2450), (2452, 2472),
    (2474, 2488), (2490, 2494), (2496, 2500), (2502, 2506), (2508, 2513),
    (2515, 2518), (2520, 2523), (2525, 2528), (2530, 2535), (2539, 2539),
    (2541, 2547), (2549, 2554), (2556, 2561), (2563, 2573), (2575, 2581),
    (2583, 2590), (2592, 2599), (2601, 2607), (2609, 2619), (2621, 2632),
    (2634, 2648), (2650, 2655), (2659, 2659), (2661, 2667), (2669, 2674),
    (2676, 2682), (2684, 2693), (2695, 2705), (2707, 2715), (2717, 2727),
    (2729, 2740), (2744, 2744), (2746, 2749), (2751, 2754), (2756, 2758),
    (2760, 2762), (2764, 2767), (2769, 2773), (2775, 2779), (2781, 2785),
    (2787, 2792), (2794, 2799), (2803, 2803), (2805, 2809), (2811, 2816),
    (2818, 2822), (2824, 2828), (2832, 2832), (2834, 2840), (2842, 2851),
    (2853, 2861), (2863, 2869), (2871, 2879), (2881, 2883), (2885, 2898),
    (2902, 2902), (2904, 2914), (2916, 2921), (2923, 2932), (2936, 2936),
    (2938, 2943), (2945, 2949), (2951, 2955), (2957, 2961), (2963, 2970),
    (2972, 2980), (2982, 2989), (2991, 2993), (2995, 3024), (3026, 3037),
    (3041, 3041), (3043, 3050), (3052, 3061), (3063, 3071), (3073, 3083),
    (3087, 3087), (3089, 3093), (3095, 3099), (3101, 3106), (3108, 3112),
    (3114, 3119), (3121, 3125), (3127, 3131), (3135, 3135), (3137, 3139),
    (3141, 3143), (3145, 3147), (3149, 3152), (3154, 3158), (3160, 3164),
    (3166, 3170), (3172, 3175), (3177, 3181), (3183, 3186), (3188, 3191),
    (3193, 3196), (3202, 3202), (3204, 3211), (3213, 3221), (3223, 3228),
    (3230, 3235), (3237, 3249), (3261, 3261), (3263, 3265), (3267, 3269),
    (3271, 3273), (3275, 3277), (3279, 3281), (3283, 3288), (3290, 3295),
    (3297, 3306), (3312, 3312), (3314, 3318), (3320, 3338), (3344, 3344),
    (3346, 3346), (3348, 3353), (3358, 3358), (3360, 3363), (3365, 3368),
    (3370, 3373), (3375, 3378), (3380, 3383), (3385, 3388), (3390, 3400),
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
    assert actual[2305]["priority"] == "P3"
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
    for start in [37, 93, 112, 129, 149, 167, 182, 212, 239, 285, 317, 356, 389, 409, 491, 510, 614, 712, 861, 961, 1230, 1662, 1692, 1902, 1943, 1997, 2013, 2031, 2366, 2537, 2657]:
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
