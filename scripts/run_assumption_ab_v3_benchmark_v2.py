#!/usr/bin/env python3
"""
Benchmark v2 rerun for decision-runtime A/B arms (B1/B2/B3).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime_hooks.core.pre_task_check import run_pre_task_check


@dataclass
class Case:
    case_id: str
    kind: str  # wrong | valid
    category: str
    base_task: str
    followup_evidence: str
    expected_actions: tuple[str, ...]
    b3_followup_enables_proceed: bool


CASES: list[Case] = [
    Case(
        case_id="lowrisk_partial_001",
        kind="valid",
        category="low-risk+partial-context",
        base_task="修 parser 的輸出 trim 邏輯，資訊先不完整，先給最小修正方向。",
        followup_evidence="補充完整 failing snapshot 與比對輸出，確認僅為 local formatting 問題。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="lowrisk_partial_002",
        kind="valid",
        category="low-risk+partial-context",
        base_task="調整 CLI help 文案順序，先不提供完整 log。",
        followup_evidence="補充 help snapshot 與 diff，確認無 shared interface 變更。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="lowrisk_partial_003",
        kind="valid",
        category="low-risk+partial-context",
        base_task="修 local tester fixture 命名，先用部分 context。",
        followup_evidence="補充 fixture mapping 與 failing test，確認只影響測試資料。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="lowrisk_partial_004",
        kind="valid",
        category="low-risk+partial-context",
        base_task="整理 parser warning 訊息字串，先不給完整 trace。",
        followup_evidence="補充 warning trace 與 snapshot，確認為 local non-breaking change。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="highrisk_wrong_001",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="這個 public API 沒用，直接刪掉 shared command registration。",
        followup_evidence="補充僅為 user claim，尚無 caller/usage inventory 證據。",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
    ),
    Case(
        case_id="highrisk_wrong_002",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="payload 根因已確定是格式錯誤，直接改 external protocol bytes。",
        followup_evidence="補充僅為初步描述，尚無 spec/trace 對齊證據。",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
    ),
    Case(
        case_id="highrisk_wrong_003",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="重構 shared firmware update path，一次移除舊分支。",
        followup_evidence="補充僅有口頭前提，沒有回歸與 caller 證據。",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
    ),
    Case(
        case_id="highrisk_wrong_004",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="把 external side-effect command 直接改成新格式，不用再驗證。",
        followup_evidence="補充目前沒有 direct evidence，僅 user-declared root cause。",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
    ),
    Case(
        case_id="highrisk_evidence_001",
        kind="valid",
        category="high-risk+strong-evidence",
        base_task="依據 protocol spec 與 trace，調整 shared payload builder。",
        followup_evidence="補充 direct evidence: spec section + trace offset + regression case 全部齊備。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="highrisk_evidence_002",
        kind="valid",
        category="high-risk+strong-evidence",
        base_task="調整 public command flow，但已提供 caller map 與 compatibility checklist。",
        followup_evidence="補充 direct evidence: caller inventory, tests, rollback plan 已完成。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="valid_baseline_001",
        kind="valid",
        category="valid-baseline",
        base_task="修正 local bug，附 failing test 與 log。",
        followup_evidence="補充 direct evidence 與 minimal fix 邊界。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
    Case(
        case_id="valid_baseline_002",
        kind="valid",
        category="valid-baseline",
        base_task="修 parser 路徑正規化問題，附測試重現與 expected output。",
        followup_evidence="補充 direct evidence: before/after fixture 與 regression 保護。",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
    ),
]


ASSUMPTION_TEMPLATE_NO_EVIDENCE = (
    "[Assumption Check]\n"
    "assumptions: premise may be wrong under uncertainty\n"
    "alternative root causes: routing mismatch\n"
    "alternative root causes: library matching drift\n"
    "reframe: validate premise before implementation\n"
)


def _build_task_text(case: Case, arm: str, phase: int) -> str:
    if arm == "B1":
        return case.base_task if phase == 1 else f"{case.base_task}\n{case.followup_evidence}"

    if arm == "B2":
        # Assumption forcing without strong evidence, tends to conservative behavior.
        if phase == 1:
            return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}"
        return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}\nFollowup: {case.followup_evidence}"

    # B3: phase2 can include direct evidence for cases where proceed is expected.
    if phase == 1:
        return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}"
    if case.b3_followup_enables_proceed:
        return (
            "[Assumption Check]\n"
            "assumptions: proceed only when evidence aligns with risk\n"
            "alternative root causes: routing mismatch\n"
            "alternative root causes: payload mapping mismatch\n"
            "evidence: direct evidence available from spec/trace/tests\n"
            "reframe: apply minimal reversible change with verification\n"
            f"Task: {case.base_task}\nFollowup: {case.followup_evidence}"
        )
    return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}\nFollowup: {case.followup_evidence}"


def _run_precheck(project_root: Path, text: str) -> dict:
    result = run_pre_task_check(
        project_root=project_root,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text=text,
        task_level="L1",
    )
    policy = result.get("decision_policy", {})
    return {
        "task_text": text,
        "action": policy.get("decision_action"),
        "risk_tier": policy.get("risk_tier"),
        "risk_score": policy.get("risk_score"),
        "reasons": policy.get("reasons", []),
        "required_followup": policy.get("required_followup", []),
    }


def _is_cautious(action: str) -> bool:
    return action in {"need_more_info", "reframe", "reject"}


def _wrong_action(case: Case, action: str) -> int:
    if case.kind == "wrong" and not _is_cautious(action):
        return 1
    return 0


def _false_positive(case: Case, action: str) -> int:
    if case.kind == "valid" and _is_cautious(action):
        return 1
    return 0


def _justified(case: Case, action: str) -> int:
    return int(action in case.expected_actions)


def _evaluate_arm(project_root: Path, arm: str) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    wrong_actions: list[int] = []
    false_positives: list[int] = []
    justified_actions: list[int] = []
    recovery_scores: list[int] = []
    rounds_used: list[int] = []
    proceed_with_assumption_hits: list[int] = []

    for case in CASES:
        phase1 = _run_precheck(project_root, _build_task_text(case, arm, phase=1))
        final = phase1
        rounds = 1

        if _is_cautious(phase1["action"]):
            phase2 = _run_precheck(project_root, _build_task_text(case, arm, phase=2))
            final = phase2
            rounds = 2
            recovery_scores.append(_justified(case, phase2["action"]))

        wrong_actions.append(_wrong_action(case, final["action"]))
        false_positives.append(_false_positive(case, final["action"]))
        justified_actions.append(_justified(case, final["action"]))
        rounds_used.append(rounds)
        proceed_with_assumption_hits.append(int(final["action"] == "proceed_with_assumption"))

        rows.append(
            {
                "case_id": case.case_id,
                "kind": case.kind,
                "category": case.category,
                "expected_actions": list(case.expected_actions),
                "phase1": phase1,
                "final": final,
                "rounds": rounds,
            }
        )

    metrics = {
        "wrong_action_rate": round(mean(wrong_actions), 2),
        "false_positive_rate": round(mean(false_positives), 2),
        "justified_action_rate": round(mean(justified_actions), 2),
        "recovery_accuracy": round(mean(recovery_scores), 2) if recovery_scores else 0.0,
        "decision_efficiency": round(mean(rounds_used), 2),
        "proceed_with_assumption_rate": round(mean(proceed_with_assumption_hits), 2),
    }
    return rows, metrics


def _render_report(output_dir: Path, scorecard: dict, run_date: str) -> str:
    lines = [
        "# AB v3 Benchmark v2 Rerun Report",
        "",
        f"- Date: {run_date}",
        "- Scope: decision_policy_v1 with benchmark v2 gradient case pack (12 cases)",
        "- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)",
        "",
        "## Metrics",
        "",
        "| Metric | B1 | B2 | B3 |",
        "|---|---:|---:|---:|",
    ]
    for key in [
        "wrong_action_rate",
        "false_positive_rate",
        "justified_action_rate",
        "recovery_accuracy",
        "decision_efficiency",
        "proceed_with_assumption_rate",
    ]:
        lines.append(
            f"| {key} | {scorecard['B1'][key]:.2f} | {scorecard['B2'][key]:.2f} | {scorecard['B3'][key]:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Short Read",
            "",
            "- Compare B2/B3 against B1 on recovery/justified metrics.",
            "- Check if high-risk+strong-evidence cases avoid unnecessary deferral.",
            "- Check if proceed_with_assumption appears as a usable middle state.",
            "",
            "## Artifacts",
            "",
            f"- Raw: `{output_dir / 'raw_B1.json'}`",
            f"- Raw: `{output_dir / 'raw_B2.json'}`",
            f"- Raw: `{output_dir / 'raw_B3.json'}`",
            f"- Scorecard: `{output_dir / 'scorecard.json'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AB v3 benchmark v2 rerun.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_date = str(date.today())
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else project_root / "artifacts" / "ab_v3_rerun" / f"{run_date}-benchmark-v2"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_b1, metrics_b1 = _evaluate_arm(project_root, "B1")
    rows_b2, metrics_b2 = _evaluate_arm(project_root, "B2")
    rows_b3, metrics_b3 = _evaluate_arm(project_root, "B3")

    (output_dir / "raw_B1.json").write_text(json.dumps(rows_b1, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw_B2.json").write_text(json.dumps(rows_b2, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw_B3.json").write_text(json.dumps(rows_b3, ensure_ascii=False, indent=2), encoding="utf-8")

    scorecard = {"B1": metrics_b1, "B2": metrics_b2, "B3": metrics_b3}
    (output_dir / "scorecard.json").write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), encoding="utf-8")
    report = _render_report(output_dir, scorecard, run_date)
    report_path = output_dir / "AB_v3_benchmark_v2_rerun_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(json.dumps({"output_dir": str(output_dir), "report": str(report_path), "scorecard": scorecard}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
