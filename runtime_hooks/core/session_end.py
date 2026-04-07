#!/usr/bin/env python3
"""
Runtime session-end lifecycle closeout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from memory_pipeline.memory_curator import curate_candidate_artifact
from memory_pipeline.memory_layout import MEMORY_FILE_ALIASES
from memory_pipeline.memory_promoter import promote_candidate
from memory_pipeline.promotion_policy import classify_promotion_policy
from memory_pipeline.session_snapshot import create_session_snapshot
from governance_tools.decision_model_loader import build_runtime_policy_ref, final_verdict_owner, runtime_decision_source, violation_verdict_impact
from governance_tools.domain_governance_metadata import domain_risk_tier
from governance_tools.execution_surface_coverage import build_execution_surface_coverage
from governance_tools.runtime_surface_manifest import build_runtime_surface_manifest


def _ensure_runtime_artifact_dirs(project_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    runtime_root = project_root / "artifacts" / "runtime"
    candidates_dir = runtime_root / "candidates"
    curated_dir = runtime_root / "curated"
    summaries_dir = runtime_root / "summaries"
    verdicts_dir = runtime_root / "verdicts"
    traces_dir = runtime_root / "traces"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    curated_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)
    return candidates_dir, curated_dir, summaries_dir, verdicts_dir, traces_dir


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _force_runtime_failure_if_requested(checks: dict[str, Any], stage: str) -> None:
    if checks.get("force_runtime_failure_stage") == stage:
        raise RuntimeError(f"forced runtime failure at stage: {stage}")


def _normalize_session_start_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("event_type") == "session_start" and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def _normalize_runtime_contract(runtime_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": runtime_contract.get("task", "unspecified-task"),
        "rules": runtime_contract.get("rules", []) or [],
        "risk": runtime_contract.get("risk", "medium"),
        "oversight": runtime_contract.get("oversight", "auto"),
        "memory_mode": runtime_contract.get("memory_mode", "candidate"),
    }


def _contract_identity(contract_resolution: dict[str, Any], domain_contract: dict[str, Any]) -> dict[str, Any]:
    domain_raw = domain_contract.get("raw") or {}
    return {
        "source": contract_resolution.get("source"),
        "path": contract_resolution.get("path"),
        "name": domain_contract.get("name"),
        "domain": domain_raw.get("domain"),
        "plugin_version": domain_raw.get("plugin_version"),
        "risk_tier": contract_resolution.get("risk_tier"),
    }


def _structured_decision_path(*steps: str) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "step": step,
        }
        for index, step in enumerate(steps, start=1)
    ]


def _memory_schema_complete(project_root: Path) -> bool:
    memory_root = project_root / "memory"
    for names in MEMORY_FILE_ALIASES.values():
        if not any((memory_root / name).exists() for name in names):
            return False
    return True


def _classify_governance_strategy(
    project_root: Path,
    checks: dict[str, Any],
) -> dict[str, Any]:
    """
    Derive governance classification from observable session-end evidence.

    Conservative: classify down when uncertain.
    See docs/governance-strategy-runtime.md for decision rules and field specs.
    """
    # Tool gate: session_end hook is executing — active and observed
    tool_gate = "active"
    tool_gate_source = "observed"

    # File access: session_end runs with file I/O — confirmed observed
    has_file_access = True
    file_access_source = "observed"

    # Instruction loaded: check for CLAUDE.md or AGENTS.md in project root or framework root
    framework_root = Path(__file__).resolve().parents[2]
    instruction_candidates = [
        project_root / "CLAUDE.md",
        project_root / "AGENTS.md",
        framework_root / "CLAUDE.md",
    ]
    instruction_found = any(f.exists() for f in instruction_candidates)
    instruction_loaded = "true" if instruction_found else "unknown"
    instruction_source = "observed" if instruction_found else "assumed"

    # Context integrity: look for degradation signals in post-task checks dict
    context_integrity = "full"
    context_source = "observed"
    if checks:
        _warnings = checks.get("warnings") or []
        _errors = checks.get("errors") or []
        _all_messages = " ".join(str(m) for m in _warnings + _errors).lower()
        if any(sig in _all_messages for sig in ("truncat", "context_degraded", "token_budget", "token_warning")):
            context_integrity = "degraded"
            context_source = "observed"

    classification_evidence = {
        "has_file_access": {"value": has_file_access, "source": file_access_source},
        "instruction_loaded": {"value": instruction_loaded, "source": instruction_source},
        "context_integrity": {"value": context_integrity, "source": context_source},
        "tool_gate": {"value": tool_gate, "source": tool_gate_source},
    }

    # Classification decision: conservative (classify down when uncertain)
    # Mirrors the decision rules in docs/governance-strategy-runtime.md
    if tool_gate == "missing":
        effective_agent_class = "wrapper_only"
    elif context_integrity == "degraded" or instruction_loaded == "false":
        effective_agent_class = "instruction_limited"
    elif (
        has_file_access
        and instruction_loaded in ("true", "unknown")
        and context_integrity in ("full", "unknown")
        and tool_gate == "active"
    ):
        effective_agent_class = "instruction_capable"
    else:
        effective_agent_class = "instruction_limited"  # conservative default

    _strategy_map = {
        "instruction_capable": "injection+enforcement",
        "instruction_limited": "minimal_injection+enforcement",
        "wrapper_only": "no_injection+strict_enforcement",
    }
    governance_strategy = _strategy_map[effective_agent_class]

    return {
        "classification_evidence": classification_evidence,
        "effective_agent_class": effective_agent_class,
        "governance_strategy": governance_strategy,
        "injection_reliance": "none",  # invariant: enforcement never depends on injection
    }


def _build_decision_context(
    project_root: Path,
    memory_mode: str,
    checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    framework_root = Path(__file__).resolve().parents[2]
    try:
        manifest = build_runtime_surface_manifest(framework_root)
        consistency = manifest["consistency"]
        surface_validity = (
            "complete"
            if not (
                consistency["unknown_surfaces"]
                or consistency["orphan_surfaces"]
                or consistency["evidence_surface_mismatch"]
            )
            else "partial"
        )
    except Exception:
        surface_validity = "unknown"

    try:
        coverage = build_execution_surface_coverage(framework_root)["coverage"]
        coverage_completeness = (
            "complete"
            if not (
                coverage["missing_hard_required"]
                or coverage["missing_soft_required"]
                or coverage["dead_surfaces"]["never_observed"]
                or coverage["dead_surfaces"]["never_required"]
            )
            else "partial"
        )
    except Exception:
        coverage_completeness = "missing"

    if memory_mode == "stateless":
        memory_integrity = "not_applicable"
    else:
        memory_integrity = "complete" if _memory_schema_complete(project_root) else "partial"

    result: dict[str, Any] = {
        "surface_validity": surface_validity,
        "coverage_completeness": coverage_completeness,
        "memory_integrity": memory_integrity,
    }
    result.update(_classify_governance_strategy(project_root, checks or {}))
    return result


def _build_policy_summary(policy: dict[str, Any]) -> dict[str, Any]:
    reasons = [str(reason) for reason in policy.get("reasons", []) if str(reason).strip()]
    return {
        "decision": str(policy.get("decision", "unknown")),
        "reason_count": len(reasons),
        "reasons": reasons,
        "reasoning_fragments": [
            {
                "kind": "promotion-policy-reason",
                "text": reason,
            }
            for reason in reasons
        ],
    }


def _detect_memory_candidate_signals(
    *,
    checks: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    architecture_impact_preview: dict[str, Any],
    proposal_summary: dict[str, Any],
) -> list[str]:
    signals: list[str] = []

    lowered_errors = " ".join(errors).lower()
    lowered_warnings = " ".join(warnings).lower()

    if any(token in lowered_errors for token in ("runtime_failure", "crash", "exception", "traceback")):
        signals.append("crash_or_runtime_failure")

    public_api_diff = checks.get("public_api_diff") if checks else None
    if isinstance(public_api_diff, dict) and (
        public_api_diff.get("removed") or public_api_diff.get("added") or public_api_diff.get("breaking_changes")
    ):
        signals.append("public_api_change")

    if architecture_impact_preview.get("concerns"):
        signals.append("architecture_boundary_risk")

    if proposal_summary.get("concerns") or proposal_summary.get("required_evidence"):
        signals.append("proposal_risk_or_required_evidence")

    if "regression" in lowered_errors or "regression" in lowered_warnings:
        signals.append("regression_fix")

    return signals


def _build_memory_closeout(
    *,
    contract: dict[str, Any],
    policy: dict[str, Any],
    snapshot_result: dict[str, Any] | None,
    promotion_result: dict[str, Any] | None,
    candidate_signals: list[str],
    warnings: list[str],
    errors: list[str],
) -> dict[str, Any]:
    reasons = [str(reason) for reason in policy.get("reasons", []) if str(reason).strip()]
    if errors and any(error.startswith("runtime_failure:") for error in errors):
        primary_reason = next((error for error in errors if error.startswith("runtime_failure:")), errors[0])
    elif reasons:
        primary_reason = reasons[0]
    elif snapshot_result is None and contract.get("memory_mode") != "stateless":
        primary_reason = "candidate snapshot not created"
    else:
        primary_reason = "no explicit closeout reason"

    if contract.get("memory_mode") == "stateless":
        primary_reason = "memory_mode=stateless disables durable memory closeout"
    elif snapshot_result is None and "Session-end completed without response_text; candidate snapshot was skipped." in warnings:
        primary_reason = "response_text missing; candidate snapshot skipped"

    return {
        "candidate_detected": bool(candidate_signals),
        "candidate_signals": candidate_signals,
        "promotion_considered": contract.get("memory_mode") != "stateless",
        "snapshot_created": snapshot_result is not None,
        "decision": str(policy.get("decision", "unknown")),
        "promoted": promotion_result is not None,
        "reason": primary_reason,
    }


def _build_verdict_artifact(
    *,
    session_id: str,
    now: str,
    contract: dict[str, Any],
    checks: dict[str, Any],
    decision: str,
    errors: list[str],
    warnings: list[str],
    contract_resolution: dict[str, Any],
    domain_contract: dict[str, Any],
    decision_context: dict[str, str],
) -> dict[str, Any]:
    override_present = bool(checks.get("override_trace") or checks.get("reviewer_override"))
    escalation_present = decision == "REVIEW_REQUIRED" or contract.get("oversight") != "auto"
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-verdict",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": build_runtime_policy_ref(),
        "verdict": {
            "decision": decision,
            "ok": len(errors) == 0,
            "risk": contract.get("risk"),
            "oversight": contract.get("oversight"),
            "memory_mode": contract.get("memory_mode"),
        },
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
        "decision_governance": {
            "decision_source": runtime_decision_source(),
            "decision_owner": final_verdict_owner(),
            "policy_source": "memory_pipeline.promotion_policy.classify_promotion_policy",
        },
        "decision_context": decision_context,
        "evidence_summary": {
            "check_keys": sorted(str(key) for key in checks.keys()),
            "public_api_diff_present": checks.get("public_api_diff") is not None,
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "override_or_escalation": {
            "override_present": override_present,
            "escalation_present": escalation_present,
        },
    }


def _build_runtime_failure_trace_artifact(
    *,
    session_id: str,
    now: str,
    contract: dict[str, Any],
    checks: dict[str, Any],
    contract_resolution: dict[str, Any],
    domain_contract: dict[str, Any],
    stage: str,
    failure_message: str,
    decision_context: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-failure-trace",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": build_runtime_policy_ref(),
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
        "runtime_contract": contract,
        "decision_governance": {
            "decision_source": runtime_decision_source(),
            "decision_owner": final_verdict_owner(),
            "policy_source": "memory_pipeline.promotion_policy.classify_promotion_policy",
        },
        "decision_context": decision_context,
        "decision_path": _structured_decision_path(
            "normalize runtime contract",
            "runtime failure interception",
            "emit fail-closed trace artifact",
        ),
        "evidence_summary": {
            "check_keys": sorted(str(key) for key in checks.keys()),
            "check_ok": checks.get("ok"),
        },
        "result": {
            "decision": "RUNTIME_FAILURE",
            "policy": {
                "decision": "STOP",
                "reason_count": 1,
                "reasons": [failure_message],
                "reasoning_fragments": [
                    {
                        "kind": "runtime-failure",
                        "text": failure_message,
                    }
                ],
            },
            "errors": [f"runtime_failure: {failure_message}"],
            "warnings": [],
        },
        "runtime_failure": {
            "violation_type": "runtime_failure",
            "detected_by": "runtime execution wrapper",
            "verdict_impact": violation_verdict_impact("runtime_failure", "stop"),
            "stage": stage,
            "message": failure_message,
        },
        "override_or_escalation": {
            "override_present": bool(checks.get("override_trace") or checks.get("reviewer_override")),
            "escalation_present": True,
        },
    }


def _build_trace_artifact(
    *,
    session_id: str,
    now: str,
    contract: dict[str, Any],
    checks: dict[str, Any],
    decision: str,
    policy: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    contract_resolution: dict[str, Any],
    domain_contract: dict[str, Any],
    decision_context: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-trace",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": build_runtime_policy_ref(),
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
        "runtime_contract": contract,
        "decision_governance": {
            "decision_source": runtime_decision_source(),
            "decision_owner": final_verdict_owner(),
            "policy_source": "memory_pipeline.promotion_policy.classify_promotion_policy",
        },
        "decision_context": decision_context,
        "decision_path": _structured_decision_path(
            "normalize runtime contract",
            "evaluate promotion policy",
            "summarize evidence keys",
            "emit verdict and trace artifacts",
        ),
        "evidence_summary": {
            "check_keys": sorted(str(key) for key in checks.keys()),
            "check_ok": checks.get("ok"),
        },
        "result": {
            "decision": decision,
            "policy": _build_policy_summary(policy),
            "errors": errors,
            "warnings": warnings,
        },
        "override_or_escalation": {
            "override_present": bool(checks.get("override_trace") or checks.get("reviewer_override")),
            "escalation_present": decision == "REVIEW_REQUIRED" or contract.get("oversight") != "auto",
        },
    }


def run_session_end(
    project_root: Path,
    session_id: str,
    runtime_contract: dict[str, Any],
    checks: dict[str, Any] | None = None,
    architecture_impact_preview: dict[str, Any] | None = None,
    proposal_summary: dict[str, Any] | None = None,
    contract_resolution: dict[str, Any] | None = None,
    domain_contract: dict[str, Any] | None = None,
    event_log: list[dict[str, Any]] | None = None,
    response_text: str = "",
    summary: str = "",
    approved_by_auto: str = "governance-auto",
) -> dict[str, Any]:
    contract = _normalize_runtime_contract(runtime_contract)
    checks = checks or {}
    architecture_impact_preview = architecture_impact_preview or {}
    proposal_summary = proposal_summary or {}
    contract_resolution = dict(contract_resolution or {})
    domain_contract = domain_contract or {}
    if not contract_resolution.get("risk_tier"):
        contract_resolution["risk_tier"] = domain_risk_tier((domain_contract.get("raw") or {}).get("domain"))
    event_log = event_log or []
    errors: list[str] = []
    warnings: list[str] = []

    if not session_id.strip():
        errors.append("session_id is required")

    required_fields = ("task", "rules", "risk", "oversight", "memory_mode")
    missing_fields = [field for field in required_fields if not contract.get(field)]
    if missing_fields:
        errors.append(f"runtime_contract missing required fields: {missing_fields}")

    if checks and checks.get("ok") is False:
        warnings.append("Session ended with failing runtime checks.")

    public_api_diff = (checks or {}).get("public_api_diff") if checks else None

    snapshot_result = None
    curated_result = None
    promotion_result = None
    policy = classify_promotion_policy(contract, check_result=checks)
    decision = policy["decision"]
    decision_context = _build_decision_context(project_root, contract["memory_mode"], checks)

    memory_root = project_root / "memory"
    if contract["memory_mode"] != "stateless" and response_text:
        snapshot_result = create_session_snapshot(
            memory_root=memory_root,
            task=contract["task"],
            summary=summary or "Session-end candidate memory snapshot",
            source_text=response_text,
            risk=contract["risk"],
            oversight=contract["oversight"],
        )
    elif contract["memory_mode"] != "stateless":
        warnings.append("Session-end completed without response_text; candidate snapshot was skipped.")

    candidate_signals = _detect_memory_candidate_signals(
        checks=checks,
        errors=errors,
        warnings=warnings,
        architecture_impact_preview=architecture_impact_preview,
        proposal_summary=proposal_summary,
    )

    if decision == "AUTO_PROMOTE" and snapshot_result is not None:
        promotion_result = promote_candidate(
            memory_root=memory_root,
            candidate_file=Path(snapshot_result["snapshot_path"]),
            approved_by=approved_by_auto,
            title=contract["task"],
        )
    elif decision == "AUTO_PROMOTE" and snapshot_result is None:
        warnings.append("AUTO_PROMOTE policy resolved without a candidate snapshot.")

    memory_closeout = _build_memory_closeout(
        contract=contract,
        policy=policy,
        snapshot_result=snapshot_result,
        promotion_result=promotion_result,
        candidate_signals=candidate_signals,
        warnings=warnings,
        errors=errors,
    )

    now = datetime.now(timezone.utc).isoformat()
    candidate_artifact, curated_artifact, summary_artifact, verdict_artifact_dir, trace_artifact_dir = _ensure_runtime_artifact_dirs(project_root)
    candidate_path = candidate_artifact / f"{session_id}.json"
    curated_path = curated_artifact / f"{session_id}.json"
    summary_path = summary_artifact / f"{session_id}.json"
    verdict_path = verdict_artifact_dir / f"{session_id}.json"
    trace_path = trace_artifact_dir / f"{session_id}.json"

    try:
        _force_runtime_failure_if_requested(checks, "artifact_emission")

        candidate_payload = {
            "session_id": session_id,
            "closed_at": now,
            "runtime_contract": contract,
            "checks": checks,
            "architecture_impact_preview": architecture_impact_preview,
            "proposal_summary": proposal_summary,
            "contract_resolution": contract_resolution,
            "domain_contract": domain_contract,
            "public_api_diff": public_api_diff,
            "event_log": event_log,
            "snapshot": snapshot_result,
            "policy": policy,
            "promotion": promotion_result,
            "warnings": warnings,
            "errors": errors,
        }
        summary_payload = {
            "session_id": session_id,
            "closed_at": now,
            "task": contract["task"],
            "decision": decision,
            "risk": contract["risk"],
            "oversight": contract["oversight"],
            "memory_mode": contract["memory_mode"],
            "rules": contract["rules"],
            "architecture_impact_present": bool(architecture_impact_preview),
            "architecture_impact_concern_count": len(architecture_impact_preview.get("concerns", []) or []),
            "architecture_impact_boundary_risk": architecture_impact_preview.get("boundary_risk"),
            "architecture_impact_recommended_risk": architecture_impact_preview.get("recommended_risk"),
            "architecture_impact_recommended_oversight": architecture_impact_preview.get("recommended_oversight"),
            "proposal_summary_present": bool(proposal_summary),
            "proposal_summary_recommended_risk": proposal_summary.get("recommended_risk"),
            "proposal_summary_recommended_oversight": proposal_summary.get("recommended_oversight"),
            "proposal_summary_concern_count": len(proposal_summary.get("concerns", []) or []),
            "proposal_summary_expected_validator_count": len(proposal_summary.get("expected_validators", []) or []),
            "contract_resolution_present": bool(contract_resolution),
            "contract_source": contract_resolution.get("source"),
            "contract_path": contract_resolution.get("path"),
            "contract_name": domain_contract.get("name"),
            "contract_domain": (domain_contract.get("raw") or {}).get("domain"),
            "contract_plugin_version": (domain_contract.get("raw") or {}).get("plugin_version"),
            "contract_risk_tier": contract_resolution.get("risk_tier"),
            "public_api_diff_present": public_api_diff is not None,
            "public_api_removed_count": len(public_api_diff.get("removed", [])) if public_api_diff else 0,
            "public_api_added_count": len(public_api_diff.get("added", [])) if public_api_diff else 0,
            "snapshot_created": snapshot_result is not None,
            "promoted": promotion_result is not None,
            "memory_closeout": memory_closeout,
            "warning_count": len(warnings),
            "error_count": len(errors),
            "decision_context": decision_context,
        }
        verdict_payload = _build_verdict_artifact(
            session_id=session_id,
            now=now,
            contract=contract,
            checks=checks,
            decision=decision,
            errors=errors,
            warnings=warnings,
            contract_resolution=contract_resolution,
            domain_contract=domain_contract,
            decision_context=decision_context,
        )
        trace_payload = _build_trace_artifact(
            session_id=session_id,
            now=now,
            contract=contract,
            checks=checks,
            decision=decision,
            policy=policy,
            errors=errors,
            warnings=warnings,
            contract_resolution=contract_resolution,
            domain_contract=domain_contract,
            decision_context=decision_context,
        )

        _write_json(candidate_path, candidate_payload)
        curated_result = curate_candidate_artifact(candidate_path, output_path=curated_path)
        _write_json(summary_path, summary_payload)
        _write_json(verdict_path, verdict_payload)
        _write_json(trace_path, trace_payload)
    except Exception as exc:
        failure_message = str(exc)
        errors.append(f"runtime_failure: {failure_message}")
        decision = "RUNTIME_FAILURE"
        policy = {"decision": "STOP", "reason": "runtime_failure"}
        failure_trace_payload = _build_runtime_failure_trace_artifact(
            session_id=session_id,
            now=now,
            contract=contract,
            checks=checks,
            contract_resolution=contract_resolution,
            domain_contract=domain_contract,
            stage="artifact_emission",
            failure_message=failure_message,
            decision_context=decision_context,
        )
        _write_json(trace_path, failure_trace_payload)

    return {
        "ok": len(errors) == 0,
        "session_id": session_id,
        "decision": decision,
        "policy": policy,
        "curated": curated_result,
        "snapshot": snapshot_result,
        "promotion": promotion_result,
        "memory_closeout": memory_closeout,
        "candidate_artifact": str(candidate_path),
        "curated_artifact": str(curated_path),
        "summary_artifact": str(summary_path),
        "verdict_artifact": str(verdict_path),
        "trace_artifact": str(trace_path),
        "decision_context": decision_context,
        "warnings": warnings,
        "errors": errors,
    }


def format_human_result(result: dict[str, Any]) -> str:
    lines = [
        f"ok={result['ok']}",
        f"session_id={result['session_id']}",
        f"decision={result['decision']}",
        f"candidate_artifact={result['candidate_artifact']}",
        f"curated_artifact={result['curated_artifact']}",
        f"summary_artifact={result['summary_artifact']}",
        f"verdict_artifact={result['verdict_artifact']}",
        f"trace_artifact={result['trace_artifact']}",
    ]
    summary_payload = json.loads(Path(result["summary_artifact"]).read_text(encoding="utf-8"))
    if summary_payload.get("contract_resolution_present"):
        lines.append(f"contract_source={summary_payload.get('contract_source')}")
        lines.append(f"contract_path={summary_payload.get('contract_path')}")
        lines.append(f"contract_name={summary_payload.get('contract_name')}")
        lines.append(f"contract_domain={summary_payload.get('contract_domain')}")
        lines.append(f"contract_plugin_version={summary_payload.get('contract_plugin_version')}")
        lines.append(f"contract_risk_tier={summary_payload.get('contract_risk_tier')}")
    if summary_payload.get("decision_context"):
        lines.append(f"surface_validity={summary_payload['decision_context'].get('surface_validity')}")
        lines.append(f"coverage_completeness={summary_payload['decision_context'].get('coverage_completeness')}")
        lines.append(f"memory_integrity={summary_payload['decision_context'].get('memory_integrity')}")
    memory_closeout = summary_payload.get("memory_closeout") or {}
    if memory_closeout:
        lines.append(f"memory_candidate_detected={memory_closeout.get('candidate_detected')}")
        candidate_signals = memory_closeout.get("candidate_signals") or []
        if candidate_signals:
            lines.append(f"memory_candidate_signals={','.join(candidate_signals)}")
        lines.append(f"memory_promotion_considered={memory_closeout.get('promotion_considered')}")
        lines.append(f"memory_closeout_decision={memory_closeout.get('decision')}")
        lines.append(f"memory_closeout_reason={memory_closeout.get('reason')}")
    if result["snapshot"]:
        lines.append(f"snapshot={result['snapshot']['snapshot_path']}")
    if result["promotion"]:
        lines.append(f"promotion={result['promotion']['status']}")
    for warning in result["warnings"]:
        lines.append(f"warning: {warning}")
    for error in result["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Close a governance runtime session.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--runtime-contract-file", required=True)
    parser.add_argument("--checks-file")
    parser.add_argument("--impact-preview-file")
    parser.add_argument("--proposal-summary-file")
    parser.add_argument("--session-start-file")
    parser.add_argument("--event-log-file")
    parser.add_argument("--response-file")
    parser.add_argument("--summary", default="")
    parser.add_argument("--approved-by-auto", default="governance-auto")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    runtime_contract = json.loads(Path(args.runtime_contract_file).read_text(encoding="utf-8"))
    checks = json.loads(Path(args.checks_file).read_text(encoding="utf-8")) if args.checks_file else None
    architecture_impact_preview = (
        json.loads(Path(args.impact_preview_file).read_text(encoding="utf-8")) if args.impact_preview_file else None
    )
    proposal_summary = (
        json.loads(Path(args.proposal_summary_file).read_text(encoding="utf-8")) if args.proposal_summary_file else None
    )
    session_start_payload = (
        _normalize_session_start_payload(json.loads(Path(args.session_start_file).read_text(encoding="utf-8")))
        if args.session_start_file
        else {}
    )
    event_log = json.loads(Path(args.event_log_file).read_text(encoding="utf-8")) if args.event_log_file else None
    response_text = Path(args.response_file).read_text(encoding="utf-8") if args.response_file else ""

    result = run_session_end(
        project_root=Path(args.project_root).resolve(),
        session_id=args.session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        architecture_impact_preview=architecture_impact_preview,
        proposal_summary=proposal_summary,
        contract_resolution=session_start_payload.get("contract_resolution"),
        domain_contract=session_start_payload.get("domain_contract"),
        event_log=event_log,
        response_text=response_text,
        summary=args.summary,
        approved_by_auto=args.approved_by_auto,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
