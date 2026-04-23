from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional


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


@dataclass
class AlternativeCause:
    layer: str
    hypothesis: str

    @classmethod
    def from_obj(cls, obj: Any) -> "AlternativeCause":
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(
                layer=str(obj.get("layer", "unknown")).strip() or "unknown",
                hypothesis=str(obj.get("hypothesis", "")).strip(),
            )
        return cls(layer="unknown", hypothesis=str(obj).strip())


@dataclass
class EvidenceBlock:
    direct_evidence_found: bool = False
    items: List[str] = field(default_factory=list)

    @classmethod
    def from_obj(cls, obj: Any) -> "EvidenceBlock":
        if isinstance(obj, cls):
            return obj
        if not isinstance(obj, dict):
            return cls()
        items = obj.get("items", []) or []
        return cls(
            direct_evidence_found=bool(obj.get("direct_evidence_found", False)),
            items=[str(x).strip() for x in items if str(x).strip()],
        )


@dataclass
class AssumptionAudit:
    stated_premise: str = ""
    alternative_root_causes: List[AlternativeCause] = field(default_factory=list)
    evidence: EvidenceBlock = field(default_factory=EvidenceBlock)
    action_decision: str = ""
    reframed_task: str = ""

    @classmethod
    def from_obj(cls, obj: Any) -> "AssumptionAudit":
        if isinstance(obj, cls):
            return obj
        if not isinstance(obj, dict):
            return cls()
        alternatives = obj.get("alternative_root_causes", []) or []
        return cls(
            stated_premise=str(obj.get("stated_premise", "")).strip(),
            alternative_root_causes=[AlternativeCause.from_obj(x) for x in alternatives],
            evidence=EvidenceBlock.from_obj(obj.get("evidence", {})),
            action_decision=str(obj.get("action_decision", "")).strip(),
            reframed_task=str(obj.get("reframed_task", "")).strip(),
        )


@dataclass
class ContextSignals:
    destructive_change: bool = False
    shared_interface: bool = False
    external_side_effect: bool = False
    partial_context: bool = False
    user_asserts_root_cause: bool = False
    valid_request: bool = False

    @classmethod
    def from_obj(cls, obj: Any) -> "ContextSignals":
        if isinstance(obj, cls):
            return obj
        if not isinstance(obj, dict):
            return cls()
        return cls(
            destructive_change=bool(obj.get("destructive_change", False)),
            shared_interface=bool(obj.get("shared_interface", False)),
            external_side_effect=bool(obj.get("external_side_effect", False)),
            partial_context=bool(obj.get("partial_context", False)),
            user_asserts_root_cause=bool(obj.get("user_asserts_root_cause", False)),
            valid_request=bool(obj.get("valid_request", False)),
        )


@dataclass
class PolicyInput:
    task_text: str
    task_type: str = "unknown"
    assumption_audit: AssumptionAudit = field(default_factory=AssumptionAudit)
    context_signals: ContextSignals = field(default_factory=ContextSignals)

    @classmethod
    def from_obj(cls, obj: Dict[str, Any]) -> "PolicyInput":
        return cls(
            task_text=str(obj.get("task_text", "")).strip(),
            task_type=str(obj.get("task_type", "unknown")).strip() or "unknown",
            assumption_audit=AssumptionAudit.from_obj(obj.get("assumption_audit", {})),
            context_signals=ContextSignals.from_obj(obj.get("context_signals", {})),
        )


@dataclass
class ActionScore:
    action: DecisionAction
    score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class DecisionPolicyResult:
    risk_tier: RiskTier
    risk_score: float
    selected_action: DecisionAction
    ranked_actions: List[ActionScore]
    confidence: float
    reasons: List[str]
    required_followup: List[str]
    fallback_plan: str
    reframed_task: str
    advisory_signals: List[str]

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["risk_tier"] = self.risk_tier.value
        out["selected_action"] = self.selected_action.value
        out["ranked_actions"] = [
            {"action": item.action.value, "score": round(item.score, 4), "reasons": item.reasons}
            for item in self.ranked_actions
        ]
        out["confidence"] = round(self.confidence, 4)
        out["risk_score"] = round(self.risk_score, 4)
        return out


class DecisionPolicyV1:
    def __init__(self, *, exploration_rate: float = 0.12, enable_soft_exploration: bool = True) -> None:
        self.exploration_rate = max(0.0, min(1.0, exploration_rate))
        self.enable_soft_exploration = enable_soft_exploration

    def evaluate(self, policy_input: PolicyInput) -> DecisionPolicyResult:
        impact = self._impact_score(policy_input)
        uncertainty = self._uncertainty_score(policy_input)
        reversibility = self._reversibility_score(policy_input)
        risk_score = impact + uncertainty + reversibility
        risk_tier = self._risk_tier(policy_input, risk_score)
        ranked_actions = self._rank_actions(policy_input, risk_tier)
        selected_action = self._select_action(policy_input, ranked_actions)
        confidence = self._compute_confidence(ranked_actions)

        reasons = [f"risk_tier:{risk_tier.value}"]
        if policy_input.context_signals.destructive_change:
            reasons.append("destructive_change")
            if not policy_input.assumption_audit.evidence.direct_evidence_found:
                reasons.append("destructive_change_without_usage_evidence")
        if policy_input.context_signals.user_asserts_root_cause:
            reasons.append("user_asserted_root_cause")
            if not policy_input.assumption_audit.evidence.direct_evidence_found:
                reasons.append("user_declared_root_cause_unverified")
        if not policy_input.assumption_audit.evidence.direct_evidence_found:
            reasons.append("assumption_evidence_missing")
        if len(policy_input.assumption_audit.alternative_root_causes) >= 2:
            reasons.append("alternative_causes_available")

        followup: List[str] = []
        if selected_action in {DecisionAction.NEED_MORE_INFO, DecisionAction.REFRAME, DecisionAction.REJECT}:
            if policy_input.context_signals.destructive_change:
                followup.append("collect_callers_or_usage")
            if policy_input.context_signals.user_asserts_root_cause:
                followup.append("collect_spec_or_protocol_evidence")
            if policy_input.context_signals.partial_context:
                followup.append("request_full_logs_or_repro")
        if selected_action == DecisionAction.PROCEED_WITH_ASSUMPTION:
            followup.extend(["mark_assumption_explicitly", "prepare_rollback_or_fallback"])

        fallback = ""
        if selected_action == DecisionAction.PROCEED_WITH_ASSUMPTION:
            fallback = "Proceed with minimal reversible change and rollback scope."

        reframed = policy_input.assumption_audit.reframed_task
        if selected_action in {DecisionAction.REFRAME, DecisionAction.NEED_MORE_INFO} and not reframed:
            if policy_input.context_signals.destructive_change:
                reframed = f"Verify unused claim before deletion: {policy_input.task_text}"
            elif policy_input.context_signals.user_asserts_root_cause:
                reframed = f"Verify root cause before patching: {policy_input.task_text}"
            else:
                reframed = f"Gather evidence before acting on: {policy_input.task_text}"

        advisories: List[str] = []
        if not policy_input.assumption_audit.evidence.direct_evidence_found:
            advisories.append("assumption_evidence_missing")
        if selected_action == DecisionAction.PROCEED_WITH_ASSUMPTION:
            advisories.append("proceeding_under_assumption")
        if policy_input.context_signals.destructive_change and selected_action != DecisionAction.PROCEED:
            advisories.append("destructive_change_requires_review")

        return DecisionPolicyResult(
            risk_tier=risk_tier,
            risk_score=risk_score,
            selected_action=selected_action,
            ranked_actions=ranked_actions,
            confidence=confidence,
            reasons=reasons,
            required_followup=followup,
            fallback_plan=fallback,
            reframed_task=reframed,
            advisory_signals=advisories,
        )

    def _impact_score(self, inp: PolicyInput) -> float:
        s = inp.context_signals
        if s.destructive_change or s.shared_interface or s.external_side_effect:
            return 3.0
        if inp.task_type in {"refactor", "payload_change", "modify_api", "delete_interface"}:
            return 2.0
        return 1.0

    def _uncertainty_score(self, inp: PolicyInput) -> float:
        a = inp.assumption_audit
        s = inp.context_signals
        score = 0.5
        if not a.stated_premise:
            score += 0.7
        if not a.evidence.direct_evidence_found:
            score += 0.9
        if len(a.alternative_root_causes) < 2:
            score += 0.5
        if s.partial_context:
            score += 0.8
        if s.user_asserts_root_cause:
            score += 0.6
        return min(score, 3.0)

    def _reversibility_score(self, inp: PolicyInput) -> float:
        s = inp.context_signals
        if s.destructive_change:
            return 3.0
        if s.shared_interface or s.external_side_effect:
            return 2.0
        return 1.0

    def _risk_tier(self, inp: PolicyInput, risk_score: float) -> RiskTier:
        if inp.context_signals.destructive_change and not inp.assumption_audit.evidence.direct_evidence_found:
            return RiskTier.INVALID
        if risk_score >= 7.0:
            return RiskTier.HIGH
        if risk_score >= 5.0:
            return RiskTier.MEDIUM
        return RiskTier.LOW

    def _rank_actions(self, inp: PolicyInput, risk_tier: RiskTier) -> List[ActionScore]:
        a = inp.assumption_audit
        s = inp.context_signals
        direct = a.evidence.direct_evidence_found
        disallowed: set[DecisionAction] = set()

        # Evidence-integrity hard gate: do not keep risky "proceed" branches
        # in candidate space when direct evidence is missing.
        if not direct and risk_tier in {RiskTier.HIGH, RiskTier.INVALID}:
            disallowed.add(DecisionAction.PROCEED)
        if not direct and risk_tier == RiskTier.INVALID:
            disallowed.add(DecisionAction.PROCEED_WITH_ASSUMPTION)

        scores: Dict[DecisionAction, float] = {
            DecisionAction.PROCEED: 0.0,
            DecisionAction.PROCEED_WITH_ASSUMPTION: 0.0,
            DecisionAction.NEED_MORE_INFO: 0.0,
            DecisionAction.REFRAME: 0.0,
            DecisionAction.REJECT: 0.0,
        }
        reasons: Dict[DecisionAction, List[str]] = {k: [] for k in scores}

        if direct:
            scores[DecisionAction.PROCEED] += 1.2
            reasons[DecisionAction.PROCEED].append("direct_evidence_present")
        if s.valid_request:
            scores[DecisionAction.PROCEED] += 0.8
            reasons[DecisionAction.PROCEED].append("request_marked_valid")
        if risk_tier == RiskTier.LOW:
            scores[DecisionAction.PROCEED] += 0.5
            reasons[DecisionAction.PROCEED].append("low_risk")
        if s.destructive_change:
            scores[DecisionAction.PROCEED] -= 1.2
            reasons[DecisionAction.PROCEED].append("destructive_change_penalty")

        if not direct and risk_tier in {RiskTier.LOW, RiskTier.MEDIUM}:
            scores[DecisionAction.PROCEED_WITH_ASSUMPTION] += 1.0
            reasons[DecisionAction.PROCEED_WITH_ASSUMPTION].append("uncertain_but_not_high_risk")
        if len(a.alternative_root_causes) >= 2:
            scores[DecisionAction.PROCEED_WITH_ASSUMPTION] += 0.5
            reasons[DecisionAction.PROCEED_WITH_ASSUMPTION].append("alternatives_present")
        if s.partial_context and risk_tier == RiskTier.LOW:
            scores[DecisionAction.PROCEED_WITH_ASSUMPTION] += 0.3
            reasons[DecisionAction.PROCEED_WITH_ASSUMPTION].append("partial_context_low_risk")
        if s.destructive_change:
            scores[DecisionAction.PROCEED_WITH_ASSUMPTION] -= 0.7
            reasons[DecisionAction.PROCEED_WITH_ASSUMPTION].append("destructive_penalty")

        if not direct:
            scores[DecisionAction.NEED_MORE_INFO] += 0.9
            reasons[DecisionAction.NEED_MORE_INFO].append("direct_evidence_missing")
        if risk_tier == RiskTier.HIGH:
            scores[DecisionAction.NEED_MORE_INFO] += 0.8
            reasons[DecisionAction.NEED_MORE_INFO].append("high_risk")
        if s.partial_context:
            scores[DecisionAction.NEED_MORE_INFO] += 0.6
            reasons[DecisionAction.NEED_MORE_INFO].append("partial_context")

        if risk_tier == RiskTier.INVALID:
            scores[DecisionAction.REFRAME] += 1.4
            reasons[DecisionAction.REFRAME].append("invalid_destructive_claim")
        if s.user_asserts_root_cause and not direct:
            scores[DecisionAction.REFRAME] += 0.6
            reasons[DecisionAction.REFRAME].append("unverified_user_root_cause")

        if risk_tier == RiskTier.INVALID and s.destructive_change:
            scores[DecisionAction.REJECT] += 0.9
            reasons[DecisionAction.REJECT].append("hard_invalid_destructive_change")

        ranked = [
            ActionScore(action=k, score=v, reasons=reasons[k])
            for k, v in scores.items()
            if k not in disallowed
        ]
        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked

    def _select_action(self, inp: PolicyInput, ranked: List[ActionScore]) -> DecisionAction:
        if not ranked:
            return DecisionAction.NEED_MORE_INFO
        selected = ranked[0].action
        if not self.enable_soft_exploration or len(ranked) < 2:
            return selected
        key = f"{inp.task_text}|{inp.task_type}|{inp.assumption_audit.stated_premise}"
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        draw = int(h[:8], 16) / 0xFFFFFFFF
        margin = ranked[0].score - ranked[1].score
        if draw < self.exploration_rate and margin < 0.35:
            return ranked[1].action
        return selected

    def _compute_confidence(self, ranked: List[ActionScore]) -> float:
        if len(ranked) < 2:
            return 1.0
        margin = max(0.0, ranked[0].score - ranked[1].score)
        return min(1.0, 0.5 + margin)


def build_decision_policy_input(
    task_text: str,
    *,
    assumption_audit: Optional[Dict[str, Any]] = None,
    context_signals: Optional[Dict[str, Any]] = None,
    task_type: str = "unknown",
) -> PolicyInput:
    return PolicyInput.from_obj(
        {
            "task_text": task_text,
            "task_type": task_type,
            "assumption_audit": assumption_audit or {},
            "context_signals": context_signals or {},
        }
    )


def evaluate_decision_policy(
    task_text: str,
    *,
    assumption_audit: Optional[Dict[str, Any]] = None,
    context_signals: Optional[Dict[str, Any]] = None,
    task_type: str = "unknown",
    exploration_rate: float = 0.12,
    enable_soft_exploration: bool = True,
) -> Dict[str, Any]:
    policy_input = build_decision_policy_input(
        task_text,
        assumption_audit=assumption_audit,
        context_signals=context_signals,
        task_type=task_type,
    )
    engine = DecisionPolicyV1(
        exploration_rate=exploration_rate,
        enable_soft_exploration=enable_soft_exploration,
    )
    return engine.evaluate(policy_input).to_dict()
