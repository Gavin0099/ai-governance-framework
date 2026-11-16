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
    29: 29, 2069: 2082, 2090: 2097, 2105: 2117, 2125: 2131,
    2139: 2144, 2152: 2157, 2165: 2172, 2192: 2196, 2204: 2211,
    2219: 2222, 2230: 2233, 2241: 2248, 2266: 2269, 2277: 2284,
    2292: 2296, 2318: 2323, 3200: 3200,
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
    (723, 728), (730, 737), (739, 746), (748, 752), (754, 775),
    (777, 786), (788, 802), (804, 839), (841, 844), (846, 849),
    (858, 858), (860, 869), (871, 878), (880, 885), (887, 890),
    (892, 896), (898, 902), (904, 908), (910, 913), (915, 931),
    (933, 939), (941, 946), (948, 954), (958, 958), (960, 970),
    (972, 980), (982, 989), (991, 995), (997, 1006), (1008, 1013),
    (1015, 1021), (1023, 1030), (1032, 1043), (1045, 1054), (1056, 1062),
    (1064, 1071), (1073, 1079), (1081, 1085), (1087, 1091), (1093, 1098),
    (1100, 1106), (1108, 1113), (1115, 1122), (1126, 1126), (1128, 1146),
    (1148, 1158), (1160, 1173), (1175, 1187), (1189, 1202), (1204, 1223),
    (1227, 1227), (1229, 1242), (1244, 1270), (1272, 1287), (1291, 1291),
    (1293, 1297), (1299, 1313), (1315, 1329), (1331, 1335), (1337, 1355),
    (1357, 1400), (1402, 1443), (1445, 1466), (1468, 1479), (1481, 1498),
    (1500, 1511), (1513, 1526), (1528, 1543), (1545, 1550), (1552, 1557),
    (1559, 1563), (1565, 1568), (1570, 1577), (1579, 1584), (1586, 1590),
    (1592, 1599), (1601, 1604), (1606, 1609), (1611, 1616), (1618, 1623),
    (1625, 1627), (1629, 1645), (1649, 1649), (1651, 1654), (1656, 1666),
    (1668, 1675), (1679, 1679), (1681, 1685), (1687, 1689), (1691, 1693),
    (1695, 1697), (1699, 1704), (1706, 1708), (1710, 1712), (1714, 1717),
    (1719, 1722), (1724, 1728), (1730, 1732), (1734, 1736), (1738, 1742),
    (1744, 1746), (1748, 1751), (1753, 1755), (1757, 1759), (1761, 1763),
    (1765, 1768), (1770, 1772), (1774, 1777), (1779, 1782), (1784, 1786),
    (1788, 1791), (1793, 1795), (1797, 1800), (1802, 1804), (1806, 1810),
    (1812, 1816), (1818, 1820), (1822, 1825), (1827, 1870), (1872, 1874),
    (1876, 1879), (1883, 1883), (1885, 1890), (1892, 1897), (1899, 1903),
    (1905, 1908), (1910, 1914), (1916, 1920), (1924, 1924), (1926, 1931),
    (1933, 1939), (1941, 1945), (1947, 1952), (1954, 1959), (1961, 1966),
    (1968, 1974), (1978, 1978), (1980, 1983), (1985, 1990), (1994, 1994),
    (1996, 2000), (2002, 2008), (2014, 2014), (2025, 2025), (2026, 2026),
    (2038, 2038), (2040, 2053), (2055, 2055), (2057, 2057), (2061, 2061),
    (2065, 2065), (2086, 2086), (2101, 2101), (2121, 2121), (2135, 2135),
    (2148, 2148), (2161, 2161), (2176, 2176), (2180, 2184), (2188, 2188),
    (2200, 2200), (2215, 2215), (2226, 2226), (2237, 2237), (2252, 2252),
    (2256, 2258), (2262, 2262), (2273, 2273), (2288, 2288), (2300, 2300),
    (2304, 2310), (2314, 2314), (2329, 2329), (2331, 2338), (2346, 2351),
    (2353, 2357), (2359, 2363), (2365, 2370), (2372, 2377), (2379, 2384),
    (2386, 2391), (2393, 2397), (2399, 2404), (2406, 2411), (2413, 2433),
    (2435, 2449), (2451, 2455), (2457, 2461), (2463, 2467), (2469, 2474),
    (2476, 2479), (2481, 2484), (2486, 2489), (2491, 2496), (2500, 2500),
    (2502, 2508), (2510, 2515), (2517, 2522), (2524, 2531), (2533, 2539),
    (2541, 2548), (2550, 2557), (2559, 2565), (2567, 2577), (2579, 2590),
    (2592, 2606), (2608, 2613), (2617, 2617), (2619, 2625), (2627, 2632),
    (2634, 2640), (2642, 2651), (2653, 2663), (2665, 2673), (2675, 2685),
    (2687, 2698), (2702, 2702), (2704, 2707), (2709, 2712), (2714, 2716),
    (2718, 2720), (2722, 2725), (2727, 2731), (2733, 2737), (2739, 2743),
    (2745, 2750), (2752, 2757), (2761, 2761), (2763, 2767), (2769, 2774),
    (2776, 2780), (2782, 2786), (2790, 2790), (2792, 2798), (2800, 2809),
    (2811, 2819), (2821, 2827), (2829, 2837), (2839, 2841), (2843, 2856),
    (2860, 2860), (2862, 2872), (2874, 2879), (2881, 2890), (2894, 2894),
    (2896, 2901), (2903, 2907), (2909, 2913), (2915, 2919), (2921, 2928),
    (2930, 2938), (2940, 2947), (2949, 2951), (2953, 2967), (2969, 2980),
    (2984, 2984), (2986, 2993), (2995, 3004), (3006, 3014), (3016, 3026),
    (3030, 3030), (3032, 3036), (3038, 3042), (3044, 3049), (3051, 3055),
    (3057, 3062), (3064, 3068), (3070, 3074), (3078, 3078), (3080, 3082),
    (3084, 3086), (3088, 3090), (3092, 3095), (3097, 3101), (3103, 3107),
    (3109, 3113), (3115, 3118), (3120, 3124), (3126, 3129), (3131, 3134),
    (3136, 3139), (3145, 3145), (3147, 3154), (3156, 3164), (3166, 3171),
    (3173, 3178), (3180, 3192), (3204, 3204), (3206, 3208), (3210, 3212),
    (3214, 3216), (3218, 3220), (3222, 3224), (3226, 3231), (3233, 3238),
    (3240, 3249), (3255, 3255), (3257, 3261), (3263, 3281), (3287, 3287),
    (3289, 3289), (3291, 3296), (3301, 3301), (3303, 3306), (3308, 3311),
    (3313, 3316), (3318, 3321), (3323, 3326), (3328, 3331), (3333, 3343),
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
    assert actual[2266]["priority"] == "P3"
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
    for start in [37, 93, 112, 129, 149, 167, 182, 212, 239, 285, 317, 356, 389, 409, 491, 510, 614, 712, 856, 956, 1225, 1647, 1677, 1881, 1922, 1976, 1992, 2327, 2498, 2615]:
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
