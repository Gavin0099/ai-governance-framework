"""
Deterministic advisory decision policy for pre-task runtime.

This module is advisory-only. It never blocks execution.
"""

from __future__ import annotations

from enum import Enum


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INVALID = "invalid"


class DecisionAction(str, Enum):
    PROCEED = "proceed"
    PROCEED_WITH_ASSUMPTION = "proceed_with_assumption"
    NEED_MORE_INFO = "need_more_info"
    REFRAME = "reframe"
    REJECT = "reject"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in markers)


def _classify_task_type(task_text: str, task_topic: str | None) -> str:
    text = (task_text or "").lower()
    if _contains_any(text, ("payload", "packet", "protocol", "wire format", "payload format")):
        return "payload_change"
    if _contains_any(text, ("delete", "remove", "drop", "retire", "deprecate", "刪", "移除")):
        if _contains_any(text, ("api", "interface", "public", "command", "function", "method")):
            return "delete_interface"
    if _contains_any(text, ("api", "endpoint", "contract", "schema")) and _contains_any(
        text, ("modify", "change", "adjust", "update", "rewrite", "調整", "修改")
    ):
        return "modify_api"
    if _contains_any(text, ("refactor", "重構")):
        return "refactor"
    if _contains_any(text, ("bug", "bugfix", "regression", "fix", "錯誤", "修")):
        return "bugfix"
    if task_topic == "api_schema":
        return "modify_api"
    return "unknown"


def _extract_context_signals(task_text: str) -> dict:
    text = (task_text or "").lower()
    destructive_change = _contains_any(
        text,
        (
            "delete",
            "remove",
            "drop",
            "retire",
            "deprecate",
            "刪",
            "移除",
        ),
    )
    shared_interface = _contains_any(
        text,
        (
            "api",
            "public",
            "interface",
            "command",
            "contract",
            "schema",
            "shared",
        ),
    )
    external_side_effect = _contains_any(
        text,
        (
            "payload",
            "protocol",
            "packet",
            "network",
            "external",
            "firmware",
            "ddc",
            "i2c",
        ),
    )
    partial_context = _contains_any(
        text,
        (
            "partial context",
            "without full log",
            "without logs",
            "no log",
            "不給完整",
            "只給部分",
            "資訊不完整",
        ),
    )
    user_asserts_root_cause = _contains_any(
        text,
        (
            "root cause",
            "because",
            "caused by",
            "the issue is",
            "問題是",
            "是因為",
            "因為",
        ),
    )
    return {
        "destructive_change": destructive_change,
        "shared_interface": shared_interface,
        "external_side_effect": external_side_effect,
        "partial_context": partial_context,
        "user_asserts_root_cause": user_asserts_root_cause,
    }


def _classify_impact(task_type: str, signals: dict) -> int:
    if signals["destructive_change"] or signals["shared_interface"] or signals["external_side_effect"]:
        return 3
    if task_type in {"payload_change", "refactor", "modify_api"}:
        return 2
    return 1


def _classify_uncertainty(assumption_check: dict, signals: dict) -> int:
    score = 1
    if not assumption_check.get("evidence_present"):
        score += 1
    if signals["partial_context"] or signals["user_asserts_root_cause"]:
        score += 1
    if int(assumption_check.get("alternatives_count", 0)) < 2:
        score += 1
    return min(score, 3)


def _classify_reversibility(signals: dict) -> int:
    if signals["destructive_change"]:
        return 3
    if signals["shared_interface"] or signals["external_side_effect"]:
        return 2
    return 1


def _map_risk_tier(score: int, assumption_check: dict, signals: dict) -> RiskTier:
    if signals["destructive_change"] and not assumption_check.get("evidence_present"):
        return RiskTier.INVALID
    if score >= 7:
        return RiskTier.HIGH
    if score >= 5:
        return RiskTier.MEDIUM
    return RiskTier.LOW


def _decide_action(risk_tier: RiskTier, assumption_check: dict) -> DecisionAction:
    if risk_tier == RiskTier.INVALID:
        return DecisionAction.REFRAME
    if risk_tier == RiskTier.HIGH:
        return DecisionAction.NEED_MORE_INFO
    if risk_tier == RiskTier.MEDIUM:
        if not assumption_check.get("evidence_present"):
            return DecisionAction.NEED_MORE_INFO
        return DecisionAction.PROCEED_WITH_ASSUMPTION
    if assumption_check.get("evidence_present"):
        return DecisionAction.PROCEED
    return DecisionAction.PROCEED_WITH_ASSUMPTION


def _build_reasons(signals: dict, assumption_check: dict) -> list[str]:
    reasons: list[str] = []
    if signals["destructive_change"] and not assumption_check.get("evidence_present"):
        reasons.append("destructive_change_without_usage_evidence")
    if signals["user_asserts_root_cause"] and not assumption_check.get("evidence_present"):
        reasons.append("user_declared_root_cause_unverified")
    if signals["partial_context"]:
        reasons.append("partial_context_detected")
    if int(assumption_check.get("alternatives_count", 0)) < 2:
        reasons.append("limited_alternative_root_causes")
    if signals["shared_interface"]:
        reasons.append("shared_interface_change")
    if signals["external_side_effect"]:
        reasons.append("external_side_effect_change")
    if not assumption_check.get("evidence_present"):
        reasons.append("assumption_evidence_missing")
    return reasons


def _build_followup(reasons: list[str]) -> list[str]:
    followup: list[str] = []
    if "destructive_change_without_usage_evidence" in reasons:
        followup.append("collect_callers_or_usage")
    if "user_declared_root_cause_unverified" in reasons:
        followup.append("collect_spec_or_protocol_evidence")
    if "partial_context_detected" in reasons:
        followup.append("request_full_logs_or_repro")
    if "limited_alternative_root_causes" in reasons:
        followup.append("enumerate_at_least_two_alternative_root_causes")
    if "assumption_evidence_missing" in reasons:
        followup.append("add_direct_evidence_before_high_impact_change")
    return followup


def _build_reframed_task(task_type: str, action: DecisionAction, task_text: str) -> str:
    if action not in {DecisionAction.REFRAME, DecisionAction.NEED_MORE_INFO}:
        return ""
    if task_type == "delete_interface":
        return "Verify whether the target interface/function is truly unused before deletion."
    if task_type == "payload_change":
        return "Validate protocol/payload spec and runtime trace before changing payload format."
    if "root cause" in (task_text or "").lower() or "因為" in (task_text or ""):
        return "Validate root-cause evidence first, then apply the smallest reversible change."
    return "Collect missing evidence and re-define the task before implementation."


def evaluate_decision_policy_v1(task_text: str, assumption_check: dict, task_topic: str | None = None) -> dict:
    task_type = _classify_task_type(task_text, task_topic)
    signals = _extract_context_signals(task_text)
    impact = _classify_impact(task_type, signals)
    uncertainty = _classify_uncertainty(assumption_check, signals)
    reversibility = _classify_reversibility(signals)
    risk_score = impact + uncertainty + reversibility
    risk_tier = _map_risk_tier(risk_score, assumption_check, signals)
    action = _decide_action(risk_tier, assumption_check)
    reasons = _build_reasons(signals, assumption_check)
    required_followup = _build_followup(reasons)
    fallback_plan = (
        "Proceed with minimal reversible changes and targeted verification; rollback if evidence conflicts."
        if action == DecisionAction.PROCEED_WITH_ASSUMPTION
        else ""
    )
    confidence = round(max(0.35, min(0.9, 1.0 - (risk_score * 0.08))), 2)

    return {
        "task_type": task_type,
        "context_signals": signals,
        "risk_factors": {
            "impact": impact,
            "uncertainty": uncertainty,
            "reversibility": reversibility,
        },
        "risk_tier": risk_tier.value,
        "risk_score": risk_score,
        "decision_action": action.value,
        "confidence": confidence,
        "reasons": reasons,
        "required_followup": required_followup,
        "fallback_plan": fallback_plan,
        "reframed_task": _build_reframed_task(task_type, action, task_text),
    }
