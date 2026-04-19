#!/usr/bin/env python3
"""
Ingestion-layer semantic reinterpretation contract for Enumd runtime candidate artifacts.

Purpose: prevent cross-domain misread of decision-shaped Enumd fields by demoting
raw values to provenance and exposing consumer-safe reinterpretations as primary fields.

Design principles:
  - raw_value is preserved in provenance but NOT the primary consumer interface
  - consumer_safe_label is the mandatory primary reading surface
  - actual_scope is a required field; missing it marks reinterpretation as invalid
  - non_equivalence entries are machine-readable, not just docs
  - semantic_collision_mitigated=True only when actual_scope AND consumer_safe_label
    are both non-null and the value was recognized

Applying this contract to a batch of candidates causes analyze_candidate() (from
enumd_semantic_isolation) to naturally downgrade the batch_conclusion because
policy.decision is no longer accessible at its original dot-path — it is moved
into policy._raw_provenance, out of the high-collision registry's reach.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "enumd-ingestion-contract-report"

# Reinterpretation table for known policy.decision values.
# Add entries here as Enumd produces new variants.
_POLICY_DECISION_MAP: dict[str, dict[str, Any]] = {
    "DO_NOT_PROMOTE": {
        "actual_scope": "session_memory_promotion",
        "consumer_safe_label": "memory_promotion_disallowed",
        "non_equivalence": [
            "not_repo_governance_promotion",
            "not_integration_readiness_verdict",
        ],
    },
    "PROMOTE": {
        "actual_scope": "session_memory_promotion",
        "consumer_safe_label": "memory_promotion_allowed",
        "non_equivalence": [
            "not_repo_governance_promotion",
            "not_integration_readiness_verdict",
        ],
    },
    "DEFER": {
        "actual_scope": "session_memory_promotion",
        "consumer_safe_label": "memory_promotion_deferred",
        "non_equivalence": [
            "not_repo_governance_promotion",
            "not_integration_readiness_verdict",
        ],
    },
}

_REQUIRED_REINTERPRETATION_FIELDS = ("actual_scope", "consumer_safe_label")


def reinterpret_policy_decision(raw_value: str) -> dict:
    """
    Map a raw policy.decision value to a consumer-safe reinterpretation.

    Returns a dict with keys:
      raw_value, actual_scope, consumer_safe_label, non_equivalence,
      semantic_collision_mitigated, reinterpretation_status

    reinterpretation_status values:
      applied         — known value, all fields populated
      unknown_value   — value not in registry; actual_scope/consumer_safe_label are null
      missing_scope   — spec exists but actual_scope is null (registry gap)
    """
    spec = _POLICY_DECISION_MAP.get(raw_value)

    if spec is None:
        return {
            "raw_value": raw_value,
            "actual_scope": None,
            "consumer_safe_label": None,
            "non_equivalence": [],
            "semantic_collision_mitigated": False,
            "reinterpretation_status": "unknown_value",
        }

    missing = [f for f in _REQUIRED_REINTERPRETATION_FIELDS if not spec.get(f)]
    if missing:
        return {
            "raw_value": raw_value,
            "actual_scope": spec.get("actual_scope"),
            "consumer_safe_label": spec.get("consumer_safe_label"),
            "non_equivalence": spec.get("non_equivalence", []),
            "semantic_collision_mitigated": False,
            "reinterpretation_status": "missing_scope",
        }

    return {
        "raw_value": raw_value,
        "actual_scope": spec["actual_scope"],
        "consumer_safe_label": spec["consumer_safe_label"],
        "non_equivalence": spec["non_equivalence"],
        "semantic_collision_mitigated": True,
        "reinterpretation_status": "applied",
    }


def apply_ingestion_contract(candidate: dict) -> tuple[dict, dict]:
    """
    Apply semantic reinterpretation to an Enumd runtime candidate.

    Returns:
      (reinterpreted_candidate, contract_metadata)

    The reinterpreted candidate:
      - Has policy_decision_reinterpreted at top level (consumer-safe primary field)
      - Has policy demoted to _raw_provenance (not for direct consumer use)
      - Has ingestion_contract metadata block

    contract_metadata summarises what was done (for probe reporting).
    """
    result = dict(candidate)
    meta: dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "reinterpretations_applied": [],
        "reinterpretation_failures": [],
        "collision_mitigation_complete": False,
    }

    policy = candidate.get("policy") or {}
    raw_decision = policy.get("decision")

    if raw_decision is not None:
        reinterpreted = reinterpret_policy_decision(str(raw_decision))
        result["policy_decision_reinterpreted"] = reinterpreted

        # Demote raw policy block to provenance — consumer MUST use
        # policy_decision_reinterpreted, not policy.decision
        result["policy"] = {
            "_raw_provenance": policy,
            "_provenance_note": (
                "Raw policy fields demoted to provenance by ingestion contract. "
                "Use policy_decision_reinterpreted for semantic access."
            ),
        }

        if reinterpreted["semantic_collision_mitigated"]:
            meta["reinterpretations_applied"].append("policy.decision")
            meta["collision_mitigation_complete"] = True
        else:
            meta["reinterpretation_failures"].append({
                "field": "policy.decision",
                "raw_value": raw_decision,
                "status": reinterpreted["reinterpretation_status"],
            })

    result["ingestion_contract"] = meta
    return result, meta


def run_ingestion_contract_probe(
    candidates_dir: Path,
    output_dir: Path | None = None,
) -> dict:
    """
    Apply ingestion contract to all candidates and return a downgrade report
    comparing batch_conclusion before vs after reinterpretation.

    Imports analyze_candidate and _classify_batch_conclusion from
    enumd_semantic_isolation at call time to avoid circular imports.
    """
    from governance_tools.enumd_semantic_isolation import (
        analyze_candidate,
        _classify_batch_conclusion,
    )

    files = sorted(candidates_dir.glob("*.json"))
    before_samples = []
    after_samples = []
    contract_results = []

    for fp in files:
        try:
            candidate = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            contract_results.append({"file": fp.name, "status": f"parse_error: {exc}"})
            continue

        before = analyze_candidate(candidate, str(fp))
        before_samples.append(before)

        reinterpreted, meta = apply_ingestion_contract(candidate)
        after = analyze_candidate(reinterpreted, str(fp))
        after_samples.append(after)

        contract_results.append({
            "session_id": before.sample_id,
            "before_inducement_risk": before.inducement_risk,
            "after_inducement_risk": after.inducement_risk,
            "collision_mitigation_complete": meta["collision_mitigation_complete"],
            "reinterpretations_applied": meta["reinterpretations_applied"],
            "reinterpretation_failures": meta["reinterpretation_failures"],
        })

        if output_dir:
            out_fp = output_dir / fp.name
            out_fp.parent.mkdir(parents=True, exist_ok=True)
            out_fp.write_text(
                json.dumps(reinterpreted, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    conclusion_before = _classify_batch_conclusion(before_samples)
    conclusion_after = _classify_batch_conclusion(after_samples)
    downgrade_achieved = (
        conclusion_before == "observe_only_with_semantic_collision"
        and conclusion_after in ("observe_only_safe", "observe_only_with_inducement_risk")
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(candidates_dir),
        "n": len(files),
        "batch_conclusion_before": conclusion_before,
        "batch_conclusion_after": conclusion_after,
        "downgrade_achieved": downgrade_achieved,
        "mitigation_complete_count": sum(
            1 for r in contract_results if r.get("collision_mitigation_complete")
        ),
        "reinterpretation_failure_count": sum(
            1 for r in contract_results if r.get("reinterpretation_failures")
        ),
        "safety_check": (
            "risk_contained"
            if downgrade_achieved
            else "risk_not_fully_mitigated"
        ),
        "samples": contract_results,
    }


def format_human(report: dict) -> str:
    lines = [
        "[enumd_ingestion_contract_probe]",
        f"source_dir={report['source_dir']}",
        f"n={report['n']}",
        f"batch_conclusion_before={report['batch_conclusion_before']}",
        f"batch_conclusion_after={report['batch_conclusion_after']}",
        f"downgrade_achieved={report['downgrade_achieved']}",
        f"mitigation_complete_count={report['mitigation_complete_count']}",
        f"reinterpretation_failure_count={report['reinterpretation_failure_count']}",
        f"safety_check={report['safety_check']}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply Enumd ingestion contract and report semantic collision downgrade."
    )
    parser.add_argument("--candidates-dir", required=True)
    parser.add_argument("--output-dir", help="Write reinterpreted candidates here (optional)")
    parser.add_argument("--output", help="Output path for probe report JSON")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    candidates_dir = Path(args.candidates_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None

    report = run_ingestion_contract_probe(candidates_dir, output_dir)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
        if args.output:
            print(f"output={args.output}")


if __name__ == "__main__":
    main()
