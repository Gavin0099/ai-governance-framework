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


def _ensure_runtime_artifact_dirs(project_root: Path) -> tuple[Path, Path, Path]:
    runtime_root = project_root / "artifacts" / "runtime"
    candidates_dir = runtime_root / "candidates"
    curated_dir = runtime_root / "curated"
    summaries_dir = runtime_root / "summaries"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    curated_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    return candidates_dir, curated_dir, summaries_dir


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_runtime_contract(runtime_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": runtime_contract.get("task", "unspecified-task"),
        "rules": runtime_contract.get("rules", []) or [],
        "risk": runtime_contract.get("risk", "medium"),
        "oversight": runtime_contract.get("oversight", "auto"),
        "memory_mode": runtime_contract.get("memory_mode", "candidate"),
    }


def run_session_end(
    project_root: Path,
    session_id: str,
    runtime_contract: dict[str, Any],
    checks: dict[str, Any] | None = None,
    event_log: list[dict[str, Any]] | None = None,
    response_text: str = "",
    summary: str = "",
    approved_by_auto: str = "governance-auto",
) -> dict[str, Any]:
    contract = _normalize_runtime_contract(runtime_contract)
    checks = checks or {}
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
    candidate_artifact, curated_artifact, summary_artifact = _ensure_runtime_artifact_dirs(project_root)
    candidate_path = candidate_artifact / f"{session_id}.json"
    curated_path = curated_artifact / f"{session_id}.json"
    summary_path = summary_artifact / f"{session_id}.json"

    candidate_payload = {
        "session_id": session_id,
        "closed_at": now,
        "runtime_contract": contract,
        "checks": checks,
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
        "snapshot_created": snapshot_result is not None,
        "promoted": promotion_result is not None,
        "warning_count": len(warnings),
        "error_count": len(errors),
    }

    _write_json(candidate_path, candidate_payload)
    curated_result = curate_candidate_artifact(candidate_path, output_path=curated_path)
    _write_json(summary_path, summary_payload)

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
        "warnings": warnings,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Close a governance runtime session.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--runtime-contract-file", required=True)
    parser.add_argument("--checks-file")
    parser.add_argument("--event-log-file")
    parser.add_argument("--response-file")
    parser.add_argument("--summary", default="")
    parser.add_argument("--approved-by-auto", default="governance-auto")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    runtime_contract = json.loads(Path(args.runtime_contract_file).read_text(encoding="utf-8"))
    checks = json.loads(Path(args.checks_file).read_text(encoding="utf-8")) if args.checks_file else None
    event_log = json.loads(Path(args.event_log_file).read_text(encoding="utf-8")) if args.event_log_file else None
    response_text = Path(args.response_file).read_text(encoding="utf-8") if args.response_file else ""

    result = run_session_end(
        project_root=Path(args.project_root).resolve(),
        session_id=args.session_id,
        runtime_contract=runtime_contract,
        checks=checks,
        event_log=event_log,
        response_text=response_text,
        summary=args.summary,
        approved_by_auto=args.approved_by_auto,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        print(f"session_id={result['session_id']}")
        print(f"decision={result['decision']}")
        print(f"candidate_artifact={result['candidate_artifact']}")
        print(f"curated_artifact={result['curated_artifact']}")
        print(f"summary_artifact={result['summary_artifact']}")
        if result["snapshot"]:
            print(f"snapshot={result['snapshot']['snapshot_path']}")
        if result["promotion"]:
            print(f"promotion={result['promotion']['status']}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
