#!/usr/bin/env python3
"""
Benchmark v2 rerun for decision-runtime arms (B1/B2/B3).

Includes anti-collapse exploration constraint for experiment-only evaluation:
- If proceed_with_assumption never appears in an arm, allow one low-risk valid
  case to switch from cautious -> proceed_with_assumption when candidate ranking
  supports it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any, Dict

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
    ground_truth_direct_evidence: bool
    fixture: Dict[str, Any] | None = None
    optimal_action: str = "depends_on_epistemic_risk"
    epistemic_risk: str = "low"
    trial_costs: Dict[str, float] | None = None


CASES: list[Case] = [
    Case(
        case_id="lowrisk_partial_001",
        kind="valid",
        category="low-risk+partial-context",
        base_task="Fix local parser trim behavior with partial context only.",
        followup_evidence="Direct evidence: full failing snapshot and local output diff; confirm local formatting scope only.",
        expected_actions=("proceed_with_assumption", "proceed", "need_more_info"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
        epistemic_risk="medium",
    ),
    Case(
        case_id="lowrisk_partial_002",
        kind="valid",
        category="low-risk+partial-context",
        base_task="Adjust CLI help wording order with partial context.",
        followup_evidence="Direct evidence: help snapshot and diff; confirm no shared interface changes.",
        expected_actions=("proceed_with_assumption", "proceed", "need_more_info"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
        epistemic_risk="medium",
    ),
    Case(
        case_id="lowrisk_partial_003",
        kind="valid",
        category="low-risk+partial-context",
        base_task="Fix local tester fixture naming with incomplete context.",
        followup_evidence="Direct evidence: fixture mapping and failing test; confirm test-only scope.",
        expected_actions=("proceed_with_assumption", "proceed", "need_more_info"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
        epistemic_risk="medium",
    ),
    Case(
        case_id="lowrisk_partial_004",
        kind="valid",
        category="low-risk+partial-context",
        base_task="Normalize parser warning string with partial context.",
        followup_evidence="Direct evidence: warning trace and snapshot; confirm local non-breaking change.",
        expected_actions=("proceed_with_assumption", "proceed", "need_more_info"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
        epistemic_risk="medium",
    ),
    Case(
        case_id="highrisk_wrong_001",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="Delete shared public API directly; it is definitely unused.",
        followup_evidence="No caller inventory proof is provided.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="highrisk_wrong_002",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="Modify external protocol payload bytes directly; root cause is confirmed payload format.",
        followup_evidence="No aligned spec+trace evidence is provided.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="highrisk_wrong_003",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="Refactor shared firmware update path and remove old branch in one shot.",
        followup_evidence="No regression pack and no usage evidence provided.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="highrisk_wrong_004",
        kind="wrong",
        category="high-risk+wrong-premise",
        base_task="Change external side-effect command format directly without verification.",
        followup_evidence="Only user-declared root cause, no direct evidence.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="highrisk_evidence_001",
        kind="valid",
        category="high-risk+strong-evidence",
        base_task="Adjust shared payload builder based on protocol spec and trace evidence.",
        followup_evidence="Direct evidence: spec section, trace offset, and regression case all available.",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
    ),
    Case(
        case_id="highrisk_evidence_002",
        kind="valid",
        category="high-risk+strong-evidence",
        base_task="Adjust public command flow with caller map and compatibility checklist.",
        followup_evidence="Direct evidence: caller inventory, tests, and rollback plan all available.",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
    ),
    Case(
        case_id="valid_baseline_001",
        kind="valid",
        category="valid-baseline",
        base_task="Fix local bug with failing test and logs attached.",
        followup_evidence="Direct evidence and minimal-fix scope are provided.",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
    ),
    Case(
        case_id="valid_baseline_002",
        kind="valid",
        category="valid-baseline",
        base_task="Fix parser path normalization bug with repro and expected output.",
        followup_evidence="Direct evidence: before/after fixtures and regression guard available.",
        expected_actions=("proceed_with_assumption", "proceed"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
    ),
    Case(
        case_id="lowrisk_wrong_001",
        kind="wrong",
        category="low-risk+wrong-premise",
        base_task="Quickly adjust local parser token map; root cause is definitely whitespace trimming.",
        followup_evidence="Only user assertion and partial context; no direct evidence.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="lowrisk_wrong_002",
        kind="wrong",
        category="low-risk+wrong-premise",
        base_task="Patch local CLI string normalization directly; root cause already confirmed.",
        followup_evidence="No aligned fixture/log evidence, only symptom description.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
    ),
    Case(
        case_id="medium_partial_001",
        kind="valid",
        category="medium-risk+partial-context",
        base_task="Adjust shared parser adapter mapping with partial context.",
        followup_evidence="Provide one partial trace and one failing test only.",
        expected_actions=("need_more_info", "proceed_with_assumption"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
    ),
    Case(
        case_id="lowrisk_misleading_001",
        kind="wrong",
        category="low-risk+misleading-effect",
        base_task="Rename local variable to fix bug quickly; root cause is definitely naming confusion.",
        followup_evidence="No direct evidence; only symptom-level observation from one run.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        trial_costs={
            "proceed": 1.0,
            "proceed_with_assumption": 0.9,
            "need_more_info": 0.2,
            "reframe": 0.1,
            "reject": 0.1,
        },
    ),
    Case(
        case_id="lowrisk_nullprogress_001",
        kind="wrong",
        category="low-risk+null-progress",
        base_task="Tweak local warning text; this should solve flaky parser failures.",
        followup_evidence="No failing-test linkage and no evidence that warning text affects parser behavior.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        trial_costs={
            "proceed": 0.9,
            "proceed_with_assumption": 0.8,
            "need_more_info": 0.2,
            "reframe": 0.1,
            "reject": 0.1,
        },
    ),
    Case(
        case_id="lowrisk_future_001",
        kind="wrong",
        category="low-risk+future-degradation",
        base_task="Patch local config alias quickly; it should hide intermittent failures for now.",
        followup_evidence="No causality proof; likely to mask root cause and increase future debugging entropy.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        trial_costs={
            "proceed": 1.0,
            "proceed_with_assumption": 0.9,
            "need_more_info": 0.2,
            "reframe": 0.1,
            "reject": 0.1,
        },
    ),
]

SEPARATION_CASES: list[Case] = [
    Case(
        case_id="sep_lowrisk_epistemic_cost_001",
        kind="wrong",
        category="separation+low-risk+high-epistemic-cost",
        base_task="Rename local parser variable directly; root cause is definitely naming confusion.",
        followup_evidence="Only one symptom screenshot; no causal proof and no regression guard.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        fixture={
            "change_surface": "local",
            "reversibility": "easy",
            "partial_context": True,
            "user_asserts_root_cause": True,
            "has_direct_evidence": False,
            "has_tests": False,
        },
        trial_costs={
            "proceed": 1.0,
            "proceed_with_assumption": 0.9,
            "need_more_info": 0.2,
            "reframe": 0.1,
            "reject": 0.1,
        },
    ),
    Case(
        case_id="sep_lowrisk_cheap_trial_001",
        kind="valid",
        category="separation+low-risk+cheap-trial",
        base_task="Apply a local reversible logging tweak to test parser branch hypothesis quickly.",
        followup_evidence="Direct evidence: local failing snapshot and quick rollback patch are available.",
        expected_actions=("proceed_with_assumption", "need_more_info"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=True,
        epistemic_risk="low",
        fixture={
            "change_surface": "local",
            "reversibility": "easy",
            "partial_context": True,
            "has_tests": True,
            "has_direct_evidence": False,
        },
        trial_costs={
            "proceed": 0.2,
            "proceed_with_assumption": 0.1,
            "need_more_info": 0.2,
            "reframe": 0.3,
            "reject": 0.3,
        },
    ),
    Case(
        case_id="sep_highrisk_partial_evidence_001",
        kind="valid",
        category="separation+high-risk+partial-evidence",
        base_task="Adjust shared protocol mapping with only one evidence source available.",
        followup_evidence="Spec excerpt exists, but no aligned trace and no caller inventory yet.",
        expected_actions=("need_more_info", "proceed_with_assumption"),
        b3_followup_enables_proceed=True,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        fixture={
            "change_surface": "shared",
            "shared_interface": True,
            "external_side_effect": True,
            "reversibility": "bounded",
            "has_spec": True,
            "has_trace": False,
            "has_tests": False,
            "has_usage_evidence": False,
            "has_caller_inventory_or_compat_check": False,
            "has_direct_evidence": False,
            "partial_context": True,
        },
    ),
    Case(
        case_id="sep_asserted_conflicting_hint_001",
        kind="wrong",
        category="separation+asserted-root-cause+conflicting-hint",
        base_task="User insists whitespace trim caused parser failure; patch trim path directly.",
        followup_evidence="A weak trace hints queue ordering conflict, so root-cause claim is not aligned.",
        expected_actions=("need_more_info", "reframe"),
        b3_followup_enables_proceed=False,
        ground_truth_direct_evidence=False,
        epistemic_risk="high",
        fixture={
            "change_surface": "local",
            "reversibility": "easy",
            "partial_context": True,
            "user_asserts_root_cause": True,
            "has_direct_conflicting_evidence": True,
            "has_direct_evidence": False,
        },
        trial_costs={
            "proceed": 0.9,
            "proceed_with_assumption": 0.8,
            "need_more_info": 0.2,
            "reframe": 0.1,
            "reject": 0.1,
        },
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
        if phase == 1:
            return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}"
        return f"{ASSUMPTION_TEMPLATE_NO_EVIDENCE}\nTask: {case.base_task}\nFollowup: {case.followup_evidence}"

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


def _normalized_fixture(case: Case, phase: str) -> Dict[str, Any]:
    if case.fixture:
        return dict(case.fixture)

    base = {
        "change_surface": "local",
        "reversibility": "easy",
        "destructive_change": False,
        "shared_interface": False,
        "external_side_effect": False,
        "partial_context": False,
        "user_asserts_root_cause": False,
        "has_spec": False,
        "has_trace": False,
        "has_tests": False,
        "has_usage_evidence": False,
        "has_caller_inventory_or_compat_check": False,
        "has_direct_conflicting_evidence": False,
        "has_direct_evidence": False,
    }

    if case.category.startswith("low-risk+partial-context"):
        base.update(
            {
                "change_surface": "local",
                "reversibility": "easy",
                "partial_context": True,
                "has_direct_evidence": phase == "final",
                "has_tests": phase == "final",
            }
        )
    elif case.category.startswith("low-risk+wrong-premise"):
        base.update(
            {
                "change_surface": "local",
                "reversibility": "easy",
                "partial_context": True,
                "user_asserts_root_cause": True,
                "has_direct_evidence": False,
            }
        )
    elif (
        case.category.startswith("low-risk+misleading-effect")
        or case.category.startswith("low-risk+null-progress")
        or case.category.startswith("low-risk+future-degradation")
    ):
        base.update(
            {
                "change_surface": "local",
                "reversibility": "easy",
                "partial_context": True,
                "user_asserts_root_cause": True,
                "has_direct_evidence": False,
                "has_tests": False,
            }
        )
    elif case.category.startswith("medium-risk+partial-context"):
        base.update(
            {
                "change_surface": "shared",
                "shared_interface": True,
                "reversibility": "bounded",
                "partial_context": True,
                "has_tests": phase == "final",
                "has_direct_evidence": False,
            }
        )
    elif case.category.startswith("high-risk+wrong-premise"):
        base.update(
            {
                "change_surface": "external" if "payload" in case.base_task.lower() or "external" in case.base_task.lower() else "shared",
                "reversibility": "hard",
                "destructive_change": True,
                "shared_interface": True,
                "external_side_effect": "payload" in case.base_task.lower() or "external" in case.base_task.lower(),
                "user_asserts_root_cause": True,
            }
        )
    elif case.category.startswith("high-risk+strong-evidence"):
        base.update(
            {
                "change_surface": "external" if "payload" in case.base_task.lower() else "shared",
                "reversibility": "bounded",
                "shared_interface": True,
                "external_side_effect": "payload" in case.base_task.lower(),
                "has_spec": True,
                "has_trace": True,
                "has_tests": True,
                "has_usage_evidence": True,
                "has_caller_inventory_or_compat_check": True,
                "has_direct_evidence": True,
            }
        )
    else:
        base.update(
            {
                "change_surface": "local",
                "reversibility": "easy",
                "has_tests": True,
                "has_direct_evidence": True,
            }
        )
    return base


def _run_precheck(project_root: Path, text: str, case: Case, phase: str, enforcement_profile: str) -> dict:
    fixture = _normalized_fixture(case, phase)
    result = run_pre_task_check(
        project_root=project_root,
        rules="common",
        risk="medium",
        oversight="review-required",
        memory_mode="candidate",
        task_text=text,
        task_level="L1",
        case_id=case.case_id,
        benchmark_kind=case.kind,
        ground_truth_direct_evidence=case.ground_truth_direct_evidence,
        phase=phase,
        policy_fixture=fixture,
        enforcement_profile=enforcement_profile,
    )
    policy = result.get("decision_policy", {})
    evidence_integrity = result.get("evidence_integrity", {})
    evidence_gate = result.get("evidence_integrity_gate", {})
    return {
        "task_text": text,
        "action": policy.get("decision_action"),
        "risk_tier": policy.get("risk_tier"),
        "risk_score": policy.get("risk_score"),
        "reasons": policy.get("reasons", []),
        "required_followup": policy.get("required_followup", []),
        "decision_candidates": policy.get("decision_candidates", []),
        "direct_evidence_frozen": bool(evidence_integrity.get("direct_evidence_frozen")),
        "evidence_source": evidence_integrity.get("source"),
        "evidence_integrity_gate_ok": bool(evidence_gate.get("ok", True)),
        "evidence_integrity_gate_violations": int((evidence_gate.get("summary") or {}).get("violation_count", 0)),
        "evidence_integrity_gate_hard_fail": bool((evidence_gate.get("summary") or {}).get("hard_fail", False)),
        "premise_status": policy.get("premise_status"),
        "evidence_alignment": policy.get("evidence_alignment"),
        "execution_scope": policy.get("execution_scope"),
        "correctness_mode": policy.get("correctness_mode"),
        "fixture": fixture,
    }


def _is_cautious(action: str) -> bool:
    return action in {"need_more_info", "reframe", "reject"}


def _wrong_action(case: Case, action: str) -> int:
    return int(case.kind == "wrong" and not _is_cautious(action))


def _false_positive(case: Case, action: str) -> int:
    return int(case.kind == "valid" and _is_cautious(action))


def _justified(case: Case, action: str) -> int:
    return int(action in case.expected_actions)


def _resolve_optimal_action(case: Case) -> str:
    if case.optimal_action != "depends_on_epistemic_risk":
        return case.optimal_action
    if case.category.startswith("high-risk+strong-evidence"):
        return "proceed"
    if case.epistemic_risk in {"medium", "high"} and not case.ground_truth_direct_evidence:
        return "need_more_info"
    if case.category.startswith("medium-risk+partial-context"):
        return "need_more_info"
    return "proceed_with_assumption"


def _epistemic_correct_actions(case: Case) -> set[str]:
    if case.category.startswith("high-risk+strong-evidence"):
        return {"proceed", "proceed_with_assumption"}
    if (
        case.category.startswith("high-risk+wrong-premise")
        or case.category.startswith("low-risk+wrong-premise")
        or case.category.startswith("low-risk+misleading-effect")
        or case.category.startswith("low-risk+null-progress")
        or case.category.startswith("low-risk+future-degradation")
    ):
        return {"need_more_info", "reframe"}
    if case.epistemic_risk in {"medium", "high"} and not case.ground_truth_direct_evidence:
        return {"need_more_info", "reframe"}
    return set(case.expected_actions)


def _action_trial_cost(case: Case, action: str) -> float:
    if case.trial_costs:
        return float(case.trial_costs.get(action, 0.5))
    defaults = {
        "proceed": 0.4,
        "proceed_with_assumption": 0.3,
        "need_more_info": 0.1,
        "reframe": 0.1,
        "reject": 0.1,
    }
    return float(defaults.get(action, 0.5))


def _is_uncertain_state(snapshot: dict) -> bool:
    evidence_alignment = str(snapshot.get("evidence_alignment") or "").lower()
    premise_status = str(snapshot.get("premise_status") or "").lower()
    direct_evidence = bool(snapshot.get("direct_evidence_frozen"))
    if not direct_evidence:
        return True
    if premise_status in {"unsupported", "unknown"}:
        return True
    return evidence_alignment in {"missing", "weak", "conflicting", "unaligned"}


def _epistemic_trajectory_ok(row: dict) -> int:
    phase1 = row["phase1"]
    final = row["final"]
    final_action = str(final.get("action") or "")
    uncertain_start = _is_uncertain_state(phase1)
    uncertain_end = _is_uncertain_state(final)
    final_has_hard_evidence = bool(final.get("direct_evidence_frozen")) and bool(final.get("evidence_integrity_gate_ok", True))

    # Correct trajectory: if uncertainty starts high, end either with bounded caution
    # or with verified evidence before execution.
    if uncertain_start:
        if final_action in {"need_more_info", "reframe", "reject"}:
            return 1
        return int((not uncertain_end) and final_has_hard_evidence)

    # If uncertainty is already low, avoid regressing epistemic state.
    if uncertain_end and final_action in {"proceed", "proceed_with_assumption"}:
        return 0
    return 1


def _apply_anti_collapse(rows: list[dict], arm: str) -> None:
    if arm not in {"B2", "B3"}:
        return

    already_has_middle = any(row["final"]["action"] == "proceed_with_assumption" for row in rows)
    if already_has_middle:
        return

    for row in rows:
        if row["kind"] != "valid":
            continue
        if not row["category"].startswith("low-risk"):
            continue
        if row["final"]["action"] not in {"need_more_info", "reframe"}:
            continue

        candidates = row["final"].get("decision_candidates", [])
        top = candidates[0] if candidates else None
        pwa = next((c for c in candidates if c.get("action") == "proceed_with_assumption"), None)
        if not top or not pwa:
            continue

        # Exploration condition: proceed_with_assumption is close to top candidate.
        if (top["score"] - pwa["score"]) <= 0.15:
            row["final"]["action"] = "proceed_with_assumption"
            row["exploration_override"] = True
            return


def _compute_metrics(rows: list[dict]) -> dict:
    wrong_actions = [_wrong_action(row["case"], row["final"]["action"]) for row in rows]
    false_positives = [_false_positive(row["case"], row["final"]["action"]) for row in rows]
    justified_actions = [_justified(row["case"], row["final"]["action"]) for row in rows]
    correct_actions = [int(row["final"]["action"] == _resolve_optimal_action(row["case"])) for row in rows]
    epistemic_correctness = [int(row["final"]["action"] in _epistemic_correct_actions(row["case"])) for row in rows]
    epistemic_trajectory = [_epistemic_trajectory_ok(row) for row in rows]
    trial_costs = [_action_trial_cost(row["case"], row["final"]["action"]) for row in rows]
    recovery_scores = [
        _justified(row["case"], row["final"]["action"])
        for row in rows
        if row["rounds"] == 2
    ]
    rounds_used = [row["rounds"] for row in rows]
    pwa_hits = [int(row["final"]["action"] == "proceed_with_assumption") for row in rows]
    wrong_proceed_count = sum(
        1 for row in rows if row["kind"] == "wrong" and row["final"]["action"] in {"proceed", "proceed_with_assumption"}
    )
    evidence_consistency = []
    for row in rows:
        frozen_evidence = bool(row["final"].get("direct_evidence_frozen"))
        evidence_consistency.append(int(frozen_evidence == row["ground_truth_direct_evidence"]))
    gate_violations = [int(not row["final"].get("evidence_integrity_gate_ok", True)) for row in rows]
    gate_hard_fail_count = sum(int(row["final"].get("evidence_integrity_gate_hard_fail", False)) for row in rows)
    bounded_cases = [row for row in rows if row["category"].startswith("low-risk+partial-context")]
    bounded_hits = [
        int(row["final"]["action"] == "proceed_with_assumption")
        for row in bounded_cases
    ]
    premise_misclassification = [
        int(
            row["kind"] == "wrong"
            and row["final"].get("premise_status") == "supported"
        )
        for row in rows
    ]
    strong_evidence_underuse = [
        int(
            row["category"].startswith("high-risk+strong-evidence")
            and row["final"]["action"] in {"need_more_info", "reframe", "reject"}
        )
        for row in rows
    ]

    return {
        "wrong_action_rate": round(mean(wrong_actions), 2),
        "false_positive_rate": round(mean(false_positives), 2),
        "justified_action_rate": round(mean(justified_actions), 2),
        "correct_action_rate": round(mean(correct_actions), 2),
        "epistemic_correctness_rate": round(mean(epistemic_correctness), 2),
        "epistemic_trajectory_rate": round(mean(epistemic_trajectory), 2),
        "recovery_accuracy": round(mean(recovery_scores), 2) if recovery_scores else 0.0,
        "decision_efficiency": round(mean(rounds_used), 2),
        "proceed_with_assumption_rate": round(mean(pwa_hits), 2),
        "bounded_execution_capture_rate": round(mean(bounded_hits), 2) if bounded_hits else 0.0,
        "mean_trial_cost": round(mean(trial_costs), 2),
        "evidence_consistency_rate": round(mean(evidence_consistency), 2),
        "premise_misclassification_rate": round(mean(premise_misclassification), 2),
        "strong_evidence_underuse_rate": round(mean(strong_evidence_underuse), 2),
        "evidence_gate_violation_rate": round(mean(gate_violations), 2),
        "evidence_gate_hard_fail_count": gate_hard_fail_count,
        "wrong_proceed_count": wrong_proceed_count,
        "hard_fail_wrong_proceed": wrong_proceed_count > 0,
    }


def _evaluate_arm(
    project_root: Path, arm: str, enforcement_profile: str, cases: list[Case], enable_anti_collapse: bool
) -> tuple[list[dict], dict]:
    rows: list[dict] = []

    for case in cases:
        phase1 = _run_precheck(
            project_root, _build_task_text(case, arm, phase=1), case, phase="phase1", enforcement_profile=enforcement_profile
        )
        final = phase1
        rounds = 1

        if _is_cautious(phase1["action"]):
            phase2 = _run_precheck(
                project_root, _build_task_text(case, arm, phase=2), case, phase="final", enforcement_profile=enforcement_profile
            )
            final = phase2
            rounds = 2

        rows.append(
            {
                "case": case,
                "case_id": case.case_id,
                "kind": case.kind,
                "category": case.category,
                "expected_actions": list(case.expected_actions),
                "optimal_action": _resolve_optimal_action(case),
                "epistemic_risk": case.epistemic_risk,
                "ground_truth_direct_evidence": case.ground_truth_direct_evidence,
                "phase1": phase1,
                "final": final,
                "rounds": rounds,
            }
        )

    if enable_anti_collapse:
        _apply_anti_collapse(rows, arm)
    metrics = _compute_metrics(rows)

    # remove embedded dataclass from raw output
    sanitized: list[dict] = []
    for row in rows:
        row_out = dict(row)
        row_out.pop("case", None)
        sanitized.append(row_out)
    return sanitized, metrics


def _top2_actions(row: dict) -> list[str]:
    candidates = row.get("final", {}).get("decision_candidates", []) or []
    return [item.get("action", "") for item in candidates[:2]]


def _top3_with_scores(snapshot: dict) -> list[dict]:
    out = []
    for item in (snapshot.get("decision_candidates", []) or [])[:3]:
        out.append({"action": item.get("action"), "score": item.get("score")})
    return out


def _feature_tuple(snapshot: dict) -> tuple[str, str, str, str]:
    return (
        str(snapshot.get("premise_status") or ""),
        str(snapshot.get("evidence_alignment") or ""),
        str(snapshot.get("execution_scope") or ""),
        str(snapshot.get("correctness_mode") or ""),
    )


def _top3_tuple(snapshot: dict) -> tuple[tuple[str, float | None], ...]:
    top3 = _top3_with_scores(snapshot)
    return tuple((str(item.get("action") or ""), item.get("score")) for item in top3)


def _build_collapse_locator(rows_b1: list[dict], rows_b2: list[dict], rows_b3: list[dict]) -> tuple[list[dict], dict]:
    by_arm = {"B1": rows_b1, "B2": rows_b2, "B3": rows_b3}
    ids = [row["case_id"] for row in rows_b1]
    dump: list[dict] = []
    summaries: list[dict] = []
    counts = {
        "feature_extraction_collapse": 0,
        "score_mapping_collapse": 0,
        "phase_transition_collapse": 0,
        "not_collapsed_or_mixed": 0,
    }

    for case_id in ids:
        rows = {arm: next(r for r in arm_rows if r["case_id"] == case_id) for arm, arm_rows in by_arm.items()}
        arms_payload = {}
        for arm in ("B1", "B2", "B3"):
            phase1 = rows[arm]["phase1"]
            final = rows[arm]["final"]
            arms_payload[arm] = {
                "phase1": {
                    "premise_status": phase1.get("premise_status"),
                    "evidence_alignment": phase1.get("evidence_alignment"),
                    "execution_scope": phase1.get("execution_scope"),
                    "correctness_mode": phase1.get("correctness_mode"),
                    "top3": _top3_with_scores(phase1),
                },
                "final": {
                    "premise_status": final.get("premise_status"),
                    "evidence_alignment": final.get("evidence_alignment"),
                    "execution_scope": final.get("execution_scope"),
                    "correctness_mode": final.get("correctness_mode"),
                    "top3": _top3_with_scores(final),
                },
            }

        phase1_features = {arm: _feature_tuple(rows[arm]["phase1"]) for arm in ("B1", "B2", "B3")}
        final_features = {arm: _feature_tuple(rows[arm]["final"]) for arm in ("B1", "B2", "B3")}
        final_top3 = {arm: _top3_tuple(rows[arm]["final"]) for arm in ("B1", "B2", "B3")}
        phase1_top3 = {arm: _top3_tuple(rows[arm]["phase1"]) for arm in ("B1", "B2", "B3")}

        phase1_feature_delta_across_arms = len(set(phase1_features.values())) > 1
        final_feature_delta_across_arms = len(set(final_features.values())) > 1
        top3_delta_across_arms = len(set(final_top3.values())) > 1
        phase1_to_final_delta_within_arm = {
            arm: (phase1_features[arm] != final_features[arm] or phase1_top3[arm] != final_top3[arm])
            for arm in ("B1", "B2", "B3")
        }

        if not phase1_feature_delta_across_arms and not final_feature_delta_across_arms:
            collapse_type = "feature_extraction_collapse"
        elif phase1_feature_delta_across_arms and not final_feature_delta_across_arms:
            collapse_type = "phase_transition_collapse"
        elif (phase1_feature_delta_across_arms or final_feature_delta_across_arms) and not top3_delta_across_arms:
            collapse_type = "score_mapping_collapse"
        else:
            collapse_type = "not_collapsed_or_mixed"
        counts[collapse_type] += 1

        dump.append(
            {
                "case_id": case_id,
                "category": rows["B1"]["category"],
                "arms": arms_payload,
            }
        )
        summaries.append(
            {
                "case_id": case_id,
                "category": rows["B1"]["category"],
                "phase1_feature_delta_across_arms": phase1_feature_delta_across_arms,
                "final_feature_delta_across_arms": final_feature_delta_across_arms,
                "top3_delta_across_arms": top3_delta_across_arms,
                "phase1_to_final_delta_within_arm": phase1_to_final_delta_within_arm,
                "collapse_type": collapse_type,
            }
        )

    dominant = max(counts, key=lambda k: counts[k]) if counts else "unknown"
    summary = {
        "cases_total": len(summaries),
        "counts": counts,
        "dominant_collapse_type": dominant,
        "case_summaries": summaries,
    }
    return dump, summary


def _build_arm_separation(rows_b1: list[dict], rows_b2: list[dict], rows_b3: list[dict]) -> dict:
    by_arm = {"B1": rows_b1, "B2": rows_b2, "B3": rows_b3}
    ids = [row["case_id"] for row in rows_b1]
    details = []
    action_sep_count = 0
    ranking_sep_count = 0

    for case_id in ids:
        rows = {arm: next(r for r in arm_rows if r["case_id"] == case_id) for arm, arm_rows in by_arm.items()}
        actions = {arm: rows[arm]["final"]["action"] for arm in ("B1", "B2", "B3")}
        top2 = {arm: _top2_actions(rows[arm]) for arm in ("B1", "B2", "B3")}
        action_separated = len(set(actions.values())) > 1
        ranking_separated = len({tuple(v) for v in top2.values()}) > 1
        if action_separated:
            action_sep_count += 1
        if ranking_separated:
            ranking_sep_count += 1
        details.append(
            {
                "case_id": case_id,
                "category": rows["B1"]["category"],
                "actions": actions,
                "top2": top2,
                "action_separated": action_separated,
                "ranking_separated": ranking_separated,
            }
        )

    separated_cases = [d for d in details if d["action_separated"] or d["ranking_separated"]]
    return {
        "cases_total": len(details),
        "action_separated_cases": action_sep_count,
        "ranking_separated_cases": ranking_sep_count,
        "action_or_ranking_separated_cases": len(separated_cases),
        "stop_rule_min_cases": 2,
        "stop_rule_pass": len(separated_cases) >= 2,
        "details": details,
    }


def _render_report(
    output_dir: Path,
    scorecard: dict,
    run_date: str,
    enforcement_profile: str,
    case_pack: str,
    arm_separation: dict,
    collapse_summary: dict | None = None,
) -> str:
    lines = [
        "# AB v3 Benchmark v2 Rerun Report (Decision Policy v2)",
        "",
        f"- Date: {run_date}",
        f"- Scope: decision-policy runtime case pack `{case_pack}` ({arm_separation.get('cases_total', 0)} cases)",
        f"- Enforcement Profile: {enforcement_profile}",
        "- Arms: B1 (runtime only), B2 (assumption forcing), B3 (assumption + evidence feedback)",
        "- Note: exploration anti-collapse constraint enabled for B2/B3 in this experiment.",
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
        "correct_action_rate",
        "epistemic_correctness_rate",
        "epistemic_trajectory_rate",
        "recovery_accuracy",
        "decision_efficiency",
        "proceed_with_assumption_rate",
        "bounded_execution_capture_rate",
        "mean_trial_cost",
        "evidence_consistency_rate",
        "premise_misclassification_rate",
        "strong_evidence_underuse_rate",
        "evidence_gate_violation_rate",
    ]:
        lines.append(
            f"| {key} | {scorecard['B1'][key]:.2f} | {scorecard['B2'][key]:.2f} | {scorecard['B3'][key]:.2f} |"
        )
    lines.extend(
        [
            "",
            f"- Hard Fail (wrong+proceed): B1={scorecard['B1']['hard_fail_wrong_proceed']} (count={scorecard['B1']['wrong_proceed_count']}), "
            f"B2={scorecard['B2']['hard_fail_wrong_proceed']} (count={scorecard['B2']['wrong_proceed_count']}), "
            f"B3={scorecard['B3']['hard_fail_wrong_proceed']} (count={scorecard['B3']['wrong_proceed_count']})",
            f"- Gate Hard Fail (evidence gate): B1={scorecard['B1']['evidence_gate_hard_fail_count']}, "
            f"B2={scorecard['B2']['evidence_gate_hard_fail_count']}, "
            f"B3={scorecard['B3']['evidence_gate_hard_fail_count']}",
        ]
    )
    lines.extend(
        [
            "",
            "## Arm Separation",
            "",
            f"- action_separated_cases: {arm_separation['action_separated_cases']}",
            f"- ranking_separated_cases: {arm_separation['ranking_separated_cases']}",
            f"- action_or_ranking_separated_cases: {arm_separation['action_or_ranking_separated_cases']}",
            f"- stop_rule_pass(min>={arm_separation['stop_rule_min_cases']}): {arm_separation['stop_rule_pass']}",
        ]
    )
    for item in arm_separation.get("details", []):
        lines.append(
            f"- {item['case_id']} ({item['category']}): "
            f"actions B1/B2/B3={item['actions']['B1']}/{item['actions']['B2']}/{item['actions']['B3']}; "
            f"top2 B1={item['top2']['B1']} B2={item['top2']['B2']} B3={item['top2']['B3']}; "
            f"action_sep={item['action_separated']} ranking_sep={item['ranking_separated']}"
        )
    if collapse_summary:
        lines.extend(
            [
                "",
                "## Collapse Locator",
                "",
                f"- dominant_collapse_type: {collapse_summary.get('dominant_collapse_type')}",
                f"- counts: {collapse_summary.get('counts')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Raw: `{output_dir / 'raw_B1.json'}`",
            f"- Raw: `{output_dir / 'raw_B2.json'}`",
            f"- Raw: `{output_dir / 'raw_B3.json'}`",
            f"- Scorecard: `{output_dir / 'scorecard.json'}`",
            f"- Arm Separation: `{output_dir / 'arm_separation.json'}`",
            f"- Per-phase Feature Delta Dump: `{output_dir / 'per_phase_feature_delta_dump.json'}`",
            f"- Collapse Summary: `{output_dir / 'collapse_summary.json'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AB v3 benchmark v2 rerun.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir")
    parser.add_argument("--enforcement-profile", default="advisory_mainline")
    parser.add_argument("--case-pack", choices=["full_v2", "separation_v1"], default="full_v2")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_date = str(date.today())
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else project_root / "artifacts" / "ab_v3_rerun" / f"{run_date}-benchmark-v2-v2policy"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.case_pack == "separation_v1":
        cases = SEPARATION_CASES
        enable_anti_collapse = False
    else:
        cases = CASES
        enable_anti_collapse = True

    rows_b1, metrics_b1 = _evaluate_arm(project_root, "B1", args.enforcement_profile, cases, enable_anti_collapse)
    rows_b2, metrics_b2 = _evaluate_arm(project_root, "B2", args.enforcement_profile, cases, enable_anti_collapse)
    rows_b3, metrics_b3 = _evaluate_arm(project_root, "B3", args.enforcement_profile, cases, enable_anti_collapse)

    (output_dir / "raw_B1.json").write_text(json.dumps(rows_b1, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw_B2.json").write_text(json.dumps(rows_b2, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw_B3.json").write_text(json.dumps(rows_b3, ensure_ascii=False, indent=2), encoding="utf-8")

    scorecard = {"B1": metrics_b1, "B2": metrics_b2, "B3": metrics_b3}
    arm_separation = _build_arm_separation(rows_b1, rows_b2, rows_b3)
    per_phase_dump, collapse_summary = _build_collapse_locator(rows_b1, rows_b2, rows_b3)
    (output_dir / "scorecard.json").write_text(json.dumps(scorecard, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "arm_separation.json").write_text(json.dumps(arm_separation, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "per_phase_feature_delta_dump.json").write_text(
        json.dumps(per_phase_dump, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "collapse_summary.json").write_text(
        json.dumps(collapse_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = _render_report(
        output_dir, scorecard, run_date, args.enforcement_profile, args.case_pack, arm_separation, collapse_summary
    )
    report_path = output_dir / "AB_v3_benchmark_v2_rerun_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "report": str(report_path),
                "scorecard": scorecard,
                "arm_separation": {
                    "action_or_ranking_separated_cases": arm_separation["action_or_ranking_separated_cases"],
                    "stop_rule_pass": arm_separation["stop_rule_pass"],
                },
                "collapse_summary": {
                    "dominant_collapse_type": collapse_summary["dominant_collapse_type"],
                    "counts": collapse_summary["counts"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
