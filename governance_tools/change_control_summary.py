#!/usr/bin/env python3
"""
Build a reviewable change-control summary from session-start and session-end artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.contract_context import contract_label, extract_contract_context, normalize_session_start_payload
from governance_tools.human_summary import build_summary_line

_PLACEHOLDER_TASKS = {
    "Refactor Avalonia boundary".lower(),
}
_PROMOTION_GATE_CONTRACT_VERSION = "0.1"
_GATE_INPUT_FIELDS = [
    "task_provenance.status",
    "requested_promoted",
    "runtime.promoted_reported",
    "runtime.public_api_diff_reported",
    "signal_profile[*].signal_class",
    "signal_profile[*].decision_effect",
]


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def _normalize_session_end_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("event_type") == "session_end" and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def _normalize_task(task: Any) -> str:
    text = str(task or "").strip()
    if not text:
        return ""
    if text.lower() in _PLACEHOLDER_TASKS:
        return ""
    return text


def _build_signal_profile(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runtime = result.get("runtime") or {}
    proposal = result.get("proposal") or {}
    profile = {
        "task": {
            "signal_class": "descriptive",
            "decision_effect": "none",
            "promotion_allowed": False,
        },
        "proposal.recommended_risk": {
            "signal_class": "advisory",
            "decision_effect": "none",
            "promotion_allowed": False,
        },
        "proposal.recommended_oversight": {
            "signal_class": "advisory",
            "decision_effect": "none",
            "promotion_allowed": False,
        },
        "runtime.decision": {
            "signal_class": "enforcement",
            "decision_effect": "routing",
            "promotion_allowed": True,
        },
        "runtime.public_api_diff_present": {
            "signal_class": "admissibility",
            "decision_effect": "approval_required",
            "promotion_allowed": True,
        },
        "runtime.promoted": {
            "signal_class": "enforcement",
            "decision_effect": "promotion_outcome",
            "promotion_allowed": True,
        },
    }
    # Runtime decision contributes authority only when actually reported.
    if not runtime.get("decision"):
        profile["runtime.decision"]["signal_class"] = "descriptive"
        profile["runtime.decision"]["decision_effect"] = "unknown"
        profile["runtime.decision"]["promotion_allowed"] = False
    # public_api_diff contributes admissibility only when reported by runtime artifact.
    if not runtime.get("public_api_diff_reported"):
        profile["runtime.public_api_diff_present"]["signal_class"] = "descriptive"
        profile["runtime.public_api_diff_present"]["decision_effect"] = "none"
        profile["runtime.public_api_diff_present"]["promotion_allowed"] = False
    # "promoted" without a reported runtime field is descriptive.
    if not runtime.get("promoted_reported"):
        profile["runtime.promoted"]["signal_class"] = "descriptive"
        profile["runtime.promoted"]["decision_effect"] = "none"
        profile["runtime.promoted"]["promotion_allowed"] = False
    # If proposal fields are absent, keep them descriptive-only.
    if not proposal.get("recommended_risk"):
        profile["proposal.recommended_risk"]["signal_class"] = "descriptive"
    if not proposal.get("recommended_oversight"):
        profile["proposal.recommended_oversight"]["signal_class"] = "descriptive"
    return profile


def _evaluate_promotion_gate(
    *,
    signal_profile: dict[str, dict[str, Any]],
    task_provenance: dict[str, Any],
    runtime: dict[str, Any],
    requested_promoted: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    known_signal_classes = {"descriptive", "advisory", "enforcement", "admissibility"}
    effective_promoted = bool(requested_promoted)

    # Rule 1: advisory-only signals cannot promote.
    non_descriptive_classes = {
        (meta.get("signal_class") or "").strip()
        for meta in signal_profile.values()
        if (meta.get("signal_class") or "").strip() not in {"", "descriptive"}
        and (meta.get("decision_effect") or "").strip() in {"routing", "approval_required"}
    }
    if non_descriptive_classes and non_descriptive_classes <= {"advisory"}:
        reasons.append("advisory_only_signals_cannot_promote")

    # Rule 2: descriptive signals are never promotion evidence.
    if signal_profile:
        only_descriptive = all(
            (meta.get("signal_class") or "").strip() in {"", "descriptive"}
            for meta in signal_profile.values()
        )
        if only_descriptive:
            reasons.append("descriptive_signals_not_promotion_evidence")

    # Rule 3: promotion requires at least one enforcement or admissibility signal.
    has_promotion_class = any(
        (meta.get("signal_class") or "").strip() in {"enforcement", "admissibility"}
        and (meta.get("decision_effect") or "").strip() in {"routing", "approval_required"}
        for meta in signal_profile.values()
    )
    if not has_promotion_class:
        reasons.append("missing_enforcement_or_admissibility_signal")

    # Rule 4: placeholder suppression blocks promotion.
    if (task_provenance.get("status") or "").strip() == "placeholder_suppressed":
        reasons.append("task_provenance_placeholder_suppressed_blocks_promotion")

    # Rule 5: unknown signal class blocks promotion (fail-closed).
    unknown_classes = sorted(
        {
            cls
            for cls in ((meta.get("signal_class") or "").strip() for meta in signal_profile.values())
            if cls and cls not in known_signal_classes
        }
    )
    if unknown_classes:
        reasons.append(f"unknown_signal_class_blocks_promotion:{','.join(unknown_classes)}")

    if reasons:
        effective_promoted = False

    gate_input = _build_canonical_gate_input(
        signal_profile=signal_profile,
        task_provenance=task_provenance,
        runtime=runtime,
        requested_promoted=requested_promoted,
    )
    gate_inputs_digest = hashlib.sha256(
        json.dumps(gate_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "promotion_gate_contract_version": _PROMOTION_GATE_CONTRACT_VERSION,
        "requested_promoted": bool(requested_promoted),
        "effective_promoted": bool(effective_promoted),
        "allowed": len(reasons) == 0,
        "reasons": reasons,
        "blocking_reasons": reasons,
        "gate_input_fields": list(_GATE_INPUT_FIELDS),
        "gate_inputs_digest": gate_inputs_digest,
    }


def _normalize_gate_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)


def _normalize_gate_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_canonical_gate_input(
    *,
    signal_profile: dict[str, dict[str, Any]],
    task_provenance: dict[str, Any],
    runtime: dict[str, Any],
    requested_promoted: Any,
) -> dict[str, Any]:
    # Unknown fields are intentionally excluded from digest input.
    canonical_profile = {
        key: {
            "signal_class": _normalize_gate_text((meta or {}).get("signal_class")),
            "decision_effect": _normalize_gate_text((meta or {}).get("decision_effect")),
        }
        for key, meta in sorted(signal_profile.items())
    }
    return {
        "task_provenance_status": _normalize_gate_text(task_provenance.get("status")),
        "requested_promoted": _normalize_gate_bool(requested_promoted),
        "runtime_promoted_reported": _normalize_gate_bool(runtime.get("promoted_reported")),
        "runtime_public_api_diff_reported": _normalize_gate_bool(runtime.get("public_api_diff_reported")),
        "signal_profile": canonical_profile,
    }


def build_change_control_summary(
    *,
    session_start: dict[str, Any] | None = None,
    session_end: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session_start = normalize_session_start_payload(session_start or {})
    session_end = _normalize_session_end_payload(session_end or {})

    proposal_summary = session_start.get("proposal_summary") or {}
    runtime_contract = session_start.get("runtime_contract") or {}
    resolved_contract_context = extract_contract_context(session_start)
    end_summary = session_end
    task_provenance = session_start.get("task_provenance") or {}
    task = (
        _normalize_task(session_start.get("task_text"))
        or _normalize_task(end_summary.get("task"))
        or _normalize_task(runtime_contract.get("task"))
    )

    result = {
        "task": task,
        "requested_rules": proposal_summary.get("requested_rules", []) or [],
        "active_rules": runtime_contract.get("rules", []) or end_summary.get("rules", []) or [],
        "suggested_rules_preview": session_start.get("suggested_rules_preview", []) or [],
        "suggested_skills": session_start.get("suggested_skills", []) or [],
        "suggested_agent": session_start.get("suggested_agent"),
        "contract_resolution": resolved_contract_context,
        "proposal": {
            "recommended_risk": proposal_summary.get("recommended_risk"),
            "recommended_oversight": proposal_summary.get("recommended_oversight"),
            "expected_validators": proposal_summary.get("expected_validators", []) or [],
            "required_evidence": proposal_summary.get("required_evidence", []) or [],
            "concerns": proposal_summary.get("concerns", []) or [],
        },
        "runtime": {
            "decision": end_summary.get("decision"),
            "risk": end_summary.get("risk") or runtime_contract.get("risk"),
            "oversight": end_summary.get("oversight") or runtime_contract.get("oversight"),
            "public_api_diff_present": bool(end_summary.get("public_api_diff_present")),
            "public_api_diff_reported": "public_api_diff_present" in end_summary,
            "public_api_added_count": end_summary.get("public_api_added_count", 0),
            "public_api_removed_count": end_summary.get("public_api_removed_count", 0),
            "warning_count": end_summary.get("warning_count", 0),
            "error_count": end_summary.get("error_count", 0),
            "promoted": bool(end_summary.get("promoted")),
            "promoted_reported": "promoted" in end_summary,
        },
        "task_provenance": {
            "status": task_provenance.get("status") or "unknown",
            "source_key": task_provenance.get("source_key") or "none",
        },
        "signal_profile": {},
        "promotion_gate": {},
    }
    result["signal_profile"] = _build_signal_profile(result)
    result["promotion_gate"] = _evaluate_promotion_gate(
        signal_profile=result["signal_profile"],
        task_provenance=result["task_provenance"],
        runtime=result["runtime"],
        requested_promoted=result["runtime"].get("promoted", False),
    )
    result["runtime"]["promoted"] = bool(result["promotion_gate"]["effective_promoted"])
    return result


def format_human_result(result: dict[str, Any]) -> str:
    proposal = result.get("proposal") or {}
    runtime = result.get("runtime") or {}
    contract_resolution = result.get("contract_resolution") or {}
    lines = ["[change_control_summary]"]
    label = contract_label(contract_resolution)
    risk_tier = contract_resolution.get("risk_tier")
    contract_part = None
    if label:
        contract_part = f"contract={label}/{risk_tier}" if risk_tier and risk_tier != "unknown" else f"contract={label}"
    lines.append(
        build_summary_line(
            f"task={result['task']}" if result.get("task") else None,
            f"proposal_risk={proposal.get('recommended_risk')}" if proposal.get("recommended_risk") else None,
            f"runtime_decision={runtime.get('decision')}" if runtime.get("decision") else None,
            f"promoted={runtime.get('promoted')}" if runtime.get("promoted") is not None else None,
            contract_part,
        )
    )

    if result.get("task"):
        lines.append(f"task={result['task']}")
    if result.get("active_rules"):
        lines.append(f"active_rules={','.join(result['active_rules'])}")
    if any(contract_resolution.get(key) for key in ("source", "path", "name", "domain", "plugin_version", "risk_tier")):
        lines.append("[contract_resolution]")
        lines.append(f"contract_source={contract_resolution.get('source')}")
        lines.append(f"contract_risk_tier={contract_resolution.get('risk_tier')}")

    lines.append("[proposal]")
    lines.append(f"recommended_risk={proposal.get('recommended_risk')}")
    lines.append(f"recommended_oversight={proposal.get('recommended_oversight')}")
    if proposal.get("concerns"):
        lines.append(f"concerns={','.join(proposal['concerns'])}")

    lines.append("[runtime]")
    lines.append(f"decision={runtime.get('decision')}")
    lines.append(f"risk={runtime.get('risk')}")
    lines.append(f"oversight={runtime.get('oversight')}")
    lines.append(f"public_api_diff_present={runtime.get('public_api_diff_present')}")
    lines.append(f"public_api_added_count={runtime.get('public_api_added_count')}")
    lines.append(f"public_api_removed_count={runtime.get('public_api_removed_count')}")
    lines.append(f"promoted={runtime.get('promoted')}")
    task_provenance = result.get("task_provenance") or {}
    lines.append("[task_provenance]")
    lines.append(f"status={task_provenance.get('status')}")
    lines.append(f"source_key={task_provenance.get('source_key')}")
    profile = result.get("signal_profile") or {}
    if profile:
        lines.append("[signal_profile]")
        for key in ("runtime.decision", "runtime.public_api_diff_present", "runtime.promoted"):
            meta = profile.get(key) or {}
            lines.append(
                f"{key}: class={meta.get('signal_class')} effect={meta.get('decision_effect')} promotion_allowed={meta.get('promotion_allowed')}"
            )
    gate = result.get("promotion_gate") or {}
    if gate:
        lines.append("[promotion_gate]")
        lines.append(f"contract_version={gate.get('promotion_gate_contract_version')}")
        lines.append(f"allowed={gate.get('allowed')}")
        lines.append(f"requested_promoted={gate.get('requested_promoted')}")
        lines.append(f"effective_promoted={gate.get('effective_promoted')}")
        if gate.get("reasons"):
            lines.append(f"reasons={','.join(gate['reasons'])}")
        lines.append(f"gate_inputs_digest={gate.get('gate_inputs_digest')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a change-control summary.")
    parser.add_argument("--session-start-file")
    parser.add_argument("--session-end-file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = build_change_control_summary(
        session_start=_load_json(Path(args.session_start_file)) if args.session_start_file else None,
        session_end=_load_json(Path(args.session_end_file)) if args.session_end_file else None,
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else format_human_result(result)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
