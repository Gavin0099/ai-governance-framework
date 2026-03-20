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
from memory_pipeline.memory_promoter import promote_candidate
from memory_pipeline.promotion_policy import classify_promotion_policy
from memory_pipeline.session_snapshot import create_session_snapshot
from governance_tools.domain_governance_metadata import domain_risk_tier


RUNTIME_VERSION = "v2.6-draft-runtime"


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
) -> dict[str, Any]:
    override_present = bool(checks.get("override_trace") or checks.get("reviewer_override"))
    escalation_present = decision == "REVIEW_REQUIRED" or contract.get("oversight") != "auto"
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-verdict",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": {
            "governance_runtime_decision_model": "2.6-draft",
            "artifact_schema_version": "1.0",
            "runtime_version": RUNTIME_VERSION,
        },
        "verdict": {
            "decision": decision,
            "ok": len(errors) == 0,
            "risk": contract.get("risk"),
            "oversight": contract.get("oversight"),
            "memory_mode": contract.get("memory_mode"),
        },
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
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
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-failure-trace",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": {
            "governance_runtime_decision_model": "2.6-draft",
            "artifact_schema_version": "1.0",
            "runtime_version": RUNTIME_VERSION,
        },
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
        "runtime_contract": contract,
        "decision_path": [
            "normalize runtime contract",
            "runtime failure interception",
            "emit fail-closed trace artifact",
        ],
        "evidence_summary": {
            "check_keys": sorted(str(key) for key in checks.keys()),
            "check_ok": checks.get("ok"),
        },
        "result": {
            "decision": "RUNTIME_FAILURE",
            "policy": {"decision": "STOP"},
            "errors": [f"runtime_failure: {failure_message}"],
            "warnings": [],
        },
        "runtime_failure": {
            "violation_type": "runtime_failure",
            "detected_by": "runtime execution wrapper",
            "verdict_impact": "stop",
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
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": "runtime-trace",
        "session_id": session_id,
        "generated_at": now,
        "policy_ref": {
            "governance_runtime_decision_model": "2.6-draft",
            "artifact_schema_version": "1.0",
            "runtime_version": RUNTIME_VERSION,
        },
        "contract_identity": _contract_identity(contract_resolution, domain_contract),
        "runtime_contract": contract,
        "decision_path": [
            "normalize runtime contract",
            "evaluate promotion policy",
            "summarize evidence keys",
            "emit verdict and trace artifacts",
        ],
        "evidence_summary": {
            "check_keys": sorted(str(key) for key in checks.keys()),
            "check_ok": checks.get("ok"),
        },
        "result": {
            "decision": decision,
            "policy": policy,
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

    if decision == "AUTO_PROMOTE" and snapshot_result is not None:
        promotion_result = promote_candidate(
            memory_root=memory_root,
            candidate_file=Path(snapshot_result["snapshot_path"]),
            approved_by=approved_by_auto,
            title=contract["task"],
        )
    elif decision == "AUTO_PROMOTE" and snapshot_result is None:
        warnings.append("AUTO_PROMOTE policy resolved without a candidate snapshot.")

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
            "warning_count": len(warnings),
            "error_count": len(errors),
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
        "candidate_artifact": str(candidate_path),
        "curated_artifact": str(curated_path),
        "summary_artifact": str(summary_path),
        "verdict_artifact": str(verdict_path),
        "trace_artifact": str(trace_path),
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
