#!/usr/bin/env python3
"""
Estimate proposal-time architecture impact from before/after files and active rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from governance_tools.architecture_drift_checker import check_architecture_drift
from governance_tools.public_api_diff_checker import check_public_api_diff


def _required_evidence(active_rules: list[str], drift_result: dict, api_result: dict | None) -> list[str]:
    evidence = ["architecture-review"]

    if "refactor" in active_rules:
        evidence.extend(
            [
                "regression-evidence",
                "interface-stability-evidence",
                "cleanup-or-rollback-evidence",
            ]
        )

    if api_result and (api_result.get("removed") or api_result.get("added")):
        evidence.append("public-api-review")

    if "kernel-driver" in active_rules:
        evidence.extend(
            [
                "driver-static-analysis",
                "irql-verification",
                "ioctl-boundary-verification",
            ]
        )

    if drift_result.get("errors") or drift_result.get("warnings"):
        evidence.append("architecture-drift-review")

    deduped = []
    for item in evidence:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _recommended_controls(active_rules: list[str], drift_result: dict, api_result: dict | None) -> dict:
    risk = "medium"
    oversight = "review-required"

    if "kernel-driver" in active_rules:
        risk = "high"
        oversight = "human-approval"
    elif "refactor" in active_rules:
        risk = "medium"
        oversight = "review-required"

    if drift_result.get("errors") or (api_result and api_result.get("removed")):
        risk = "high"
        oversight = "human-approval"

    return {
        "recommended_risk": risk,
        "recommended_oversight": oversight,
    }


def estimate_architecture_impact(
    before_files: list[Path],
    after_files: list[Path],
    *,
    scope: str = "feature",
    active_rules: list[str] | None = None,
) -> dict:
    active_rules = active_rules or []
    drift_result = check_architecture_drift(before_files=before_files, after_files=after_files, scope=scope)
    api_result = check_public_api_diff(before_files, after_files) if any(
        path.suffix.lower() in {".cs", ".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx", ".swift"}
        for path in before_files + after_files
    ) else None

    controls = _recommended_controls(active_rules, drift_result, api_result)
    required_evidence = _required_evidence(active_rules, drift_result, api_result)

    concerns = []
    if drift_result.get("errors"):
        concerns.append("structural-drift-risk")
    if drift_result.get("warnings"):
        concerns.append("boundary-change-risk")
    if api_result and api_result.get("removed"):
        concerns.append("public-api-break-risk")
    elif api_result and api_result.get("added"):
        concerns.append("public-api-expansion-risk")
    if "kernel-driver" in active_rules:
        concerns.append("high-privilege-platform-risk")

    return {
        "ok": len(drift_result.get("errors", [])) == 0 and not (api_result and api_result.get("removed")),
        "scope": scope,
        "active_rules": active_rules,
        "drift_result": drift_result,
        "public_api_diff": api_result,
        "required_evidence": required_evidence,
        "concerns": concerns,
        **controls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate architecture impact before code is merged.")
    parser.add_argument("--before", action="append", default=[])
    parser.add_argument("--after", action="append", default=[])
    parser.add_argument("--scope", default="feature")
    parser.add_argument("--rules", default="")
    args = parser.parse_args()

    active_rules = [item.strip() for item in args.rules.split(",") if item.strip()]
    result = estimate_architecture_impact(
        [Path(path) for path in args.before],
        [Path(path) for path in args.after],
        scope=args.scope,
        active_rules=active_rules,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
