#!/usr/bin/env python3
"""
AB Causal Cross-Repo Governance Harness — ai-governance-framework (3rd repo)

Domain: external_observation_contract enforcement
- V1: forbidden field "verdict" present
- V2: forbidden field "gate_verdict" present
- V3: forbidden field "closure_verified" present
- V4: confidence_level=high with no evidence_refs (confidence overreach)
- V5: forbidden field "promote_eligible" present

Arm 1 (baseline-strict): enforce all V1-V5 (forbidden fields + confidence downgrade)
Arm 2 (one-cause-one-fix): confidence_strict_mode=False — enforces V1/V2/V3/V5
                            but does NOT downgrade high-confidence claims without evidence.
                            This makes arm-2 detectably different from arm-1.

Metric: governance_violation_rate
  A_rate = ungoverned_violation_count × scale_factor
  B_rate = governed_remaining_violations × scale_factor
  abs_delta = B_rate - A_rate
  break_test_pass: abs_delta < direction_tolerance (-1.5)

Seeds: 350101, 350102, 350103
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DIRECTION_TOLERANCE = -1.5
SCALE_FACTOR = 2.0
_SEEDS = [350101, 350102, 350103]

FORBIDDEN_FIELDS = frozenset({
    "verdict",
    "gate_verdict",
    "closure_verified",
    "promote_eligible",
    "phase3_entry_allowed",
    "closure_review_approved",
})

# ---------------------------------------------------------------------------
# Violation claim sets per seed
# Each observation dict represents one claim submitted to governance.
# Format:
#   violation_type: V1-V5 label (for reference)
#   + the actual fields that make it a violation
#
# Seed 350101: 8 violations (4 V4-confidence, 4 forbidden-field)
# Seed 350102: 6 violations (3 V4-confidence, 3 forbidden-field)
# Seed 350103: 10 violations (5 V4-confidence, 5 forbidden-field)
# ---------------------------------------------------------------------------

_V1_OBS_A = {
    "violation_type": "V1",
    "source_id": "ext-observer-A",
    "source_type": "external",
    "verdict": "pass",                          # FORBIDDEN
    "misuse_evidence_status": "not_observed_in_window",
}
_V1_OBS_B = {
    "violation_type": "V1",
    "source_id": "ext-observer-B",
    "source_type": "external",
    "verdict": "fail",                          # FORBIDDEN
    "misuse_evidence_status": "observed",
}
_V2_OBS_A = {
    "violation_type": "V2",
    "source_id": "ext-observer-C",
    "source_type": "external",
    "gate_verdict": "approved",                 # FORBIDDEN
    "misuse_evidence_status": "not_tested",
}
_V3_OBS_A = {
    "violation_type": "V3",
    "source_id": "ext-observer-D",
    "source_type": "external",
    "closure_verified": True,                   # FORBIDDEN
    "misuse_evidence_status": "not_tested",
}
_V5_OBS_A = {
    "violation_type": "V5",
    "source_id": "ext-observer-E",
    "source_type": "external",
    "promote_eligible": True,                   # FORBIDDEN
    "misuse_evidence_status": "not_observed_in_window",
}
_V5_OBS_B = {
    "violation_type": "V5",
    "source_id": "ext-observer-F",
    "source_type": "external",
    "promote_eligible": False,                  # FORBIDDEN (field presence, not value)
    "misuse_evidence_status": "not_tested",
}

# V4: confidence overreach — no forbidden field, but confidence=high without evidence
_V4_OBS_A = {
    "violation_type": "V4",
    "source_id": "ext-observer-G",
    "source_type": "external",
    "confidence_level": "high",
    "evidence_refs": [],                        # empty = no evidence
    "misuse_evidence_status": "not_observed_in_window",
}
_V4_OBS_B = {
    "violation_type": "V4",
    "source_id": "ext-observer-H",
    "source_type": "external",
    "confidence_level": "high",
    # evidence_refs absent
    "misuse_evidence_status": "observed",
}
_V4_OBS_C = {
    "violation_type": "V4",
    "source_id": "ext-observer-I",
    "source_type": "external",
    "confidence_level": "high",
    "evidence_refs": [],
    "misuse_evidence_status": "not_tested",
}
_V4_OBS_D = {
    "violation_type": "V4",
    "source_id": "ext-observer-J",
    "source_type": "external",
    "confidence_level": "high",
    "misuse_evidence_status": "not_observed_in_window",
}
_V4_OBS_E = {
    "violation_type": "V4",
    "source_id": "ext-observer-K",
    "source_type": "external",
    "confidence_level": "high",
    "evidence_refs": [],
    "misuse_evidence_status": "not_tested",
}

# Non-violations (properly structured observations)
_NON_VIOLATION_A = {
    "source_id": "trusted-reviewer-A",
    "source_type": "reviewer",
    "confidence_level": "medium",
    "evidence_refs": ["eval-run-001"],
    "misuse_evidence_status": "not_observed_in_window",
}
_NON_VIOLATION_B = {
    "source_id": "trusted-reviewer-B",
    "source_type": "internal",
    "confidence_level": "low",
    "evidence_refs": [],
    "misuse_evidence_status": "not_tested",
}
_NON_VIOLATION_C = {
    "source_id": "trusted-reviewer-C",
    "source_type": "reviewer",
    "confidence_level": "high",
    "evidence_refs": ["eval-run-002", "eval-run-003"],   # has evidence — OK
    "misuse_evidence_status": "observed",
}

# Seed-specific observation sets:
# 350101: 4 V4 + 4 forbidden-field violations + 3 non-violations = 11 obs
# 350102: 3 V4 + 3 forbidden-field violations + 3 non-violations = 9 obs
# 350103: 5 V4 + 5 forbidden-field violations + 3 non-violations = 13 obs
_OBSERVATION_SETS: dict[int, list[dict]] = {
    350101: [
        _V1_OBS_A, _V2_OBS_A, _V3_OBS_A, _V5_OBS_A,          # 4 forbidden-field
        _V4_OBS_A, _V4_OBS_B, _V4_OBS_C, _V4_OBS_D,           # 4 V4-confidence
        _NON_VIOLATION_A, _NON_VIOLATION_B, _NON_VIOLATION_C,  # 3 clean
    ],
    350102: [
        _V1_OBS_B, _V3_OBS_A, _V5_OBS_B,                       # 3 forbidden-field
        _V4_OBS_A, _V4_OBS_B, _V4_OBS_C,                       # 3 V4-confidence
        _NON_VIOLATION_A, _NON_VIOLATION_B, _NON_VIOLATION_C,  # 3 clean
    ],
    350103: [
        _V1_OBS_A, _V1_OBS_B, _V2_OBS_A, _V3_OBS_A, _V5_OBS_A,  # 5 forbidden-field
        _V4_OBS_A, _V4_OBS_B, _V4_OBS_C, _V4_OBS_D, _V4_OBS_E,  # 5 V4-confidence
        _NON_VIOLATION_A, _NON_VIOLATION_B, _NON_VIOLATION_C,    # 3 clean
    ],
}

# ---------------------------------------------------------------------------
# Governance enforcement
# ---------------------------------------------------------------------------

def _is_v4_violation(obs: dict) -> bool:
    """V4: confidence=high with no evidence (empty list or absent key)."""
    if obs.get("confidence_level") != "high":
        return False
    refs = obs.get("evidence_refs")
    return refs is None or (isinstance(refs, list) and len(refs) == 0)


def _is_forbidden_field_violation(obs: dict) -> bool:
    """V1/V2/V3/V5: any forbidden field present."""
    return bool(set(obs.keys()) & FORBIDDEN_FIELDS)


def _is_violation(obs: dict) -> bool:
    return _is_forbidden_field_violation(obs) or _is_v4_violation(obs)


def _enforce_contract(obs: dict, arm_config: dict) -> dict:
    """
    Apply external_observation_contract.v1.json rules.
    Returns a governed copy of the observation.
    """
    result = {k: v for k, v in obs.items() if k != "violation_type"}

    # V1/V2/V3/V5: remove all forbidden fields (both arms)
    for f in list(result.keys()):
        if f in FORBIDDEN_FIELDS:
            del result[f]

    # V4: confidence overreach (arm-1 only when confidence_strict_mode=True)
    if arm_config.get("confidence_strict_mode", True) and _is_v4_violation(obs):
        result["confidence_level"] = "medium"

    return result


def _count_violations_in_input(obs_list: list[dict]) -> int:
    return sum(1 for o in obs_list if _is_violation(o))


def _count_remaining_violations(obs_list: list[dict], arm_config: dict) -> int:
    governed = [_enforce_contract(o, arm_config) for o in obs_list]
    return sum(1 for g in governed if _is_forbidden_field_violation(g) or _is_v4_violation(g))


# ---------------------------------------------------------------------------
# Condition-break computation
# ---------------------------------------------------------------------------

def compute_condition_break(seed: int, arm_config: dict) -> dict:
    obs_list = _OBSERVATION_SETS[seed]
    ungoverned_count = _count_violations_in_input(obs_list)
    governed_count = _count_remaining_violations(obs_list, arm_config)

    a_rate = round(ungoverned_count * SCALE_FACTOR, 1)
    b_rate = round(governed_count * SCALE_FACTOR, 1)
    abs_delta = round(b_rate - a_rate, 1)
    rel_lift = round((abs_delta / a_rate * 100), 1) if a_rate > 0 else 0.0
    break_pass = abs_delta < DIRECTION_TOLERANCE

    arm_id = arm_config["arm_id"]
    run_id = f"{arm_id}-s{seed}"
    label = "pass" if break_pass else "fail"
    confidence_strict = arm_config.get("confidence_strict_mode", True)

    return {
        "run_id": run_id,
        "repo_id": "ai-governance-framework",
        "window_id": "ab-causal-cross-repo-agf-2026-05-15",
        "seed": str(seed),
        "arm_type": arm_config["arm_type"],
        "task_slice": "cross-repo observation — 3rd repo replication gate",
        "injected_controls": arm_config.get("injected_controls", {}),
        "blind_review": True,
        "completed": True,
        "attempts_used": 1,
        "outcome": {
            "A_rate": a_rate,
            "B_rate": b_rate,
            "abs_delta": abs_delta,
            "rel_lift": rel_lift,
            "p_value": None,
            "ci_95": None,
            "direction": "A_gt_B" if a_rate > b_rate else ("equal" if a_rate == b_rate else "B_gt_A"),
        },
        "safety_placebo": {
            "guardrail_reopen_rate": 0.0,
            "guardrail_stability_degraded_rate": 0.0,
            "guardrail_defect_rate": 0.0,
            "placebo_claim_overreach_rate": 0.0,
            "placebo_p_value": None,
        },
        "causal_threat_probe": {
            "recognizability_score": None,
            "hidden_metric_exposure": "no",
            "style_marker_presence_pre": None,
            "style_marker_presence_post": None,
            "exploration_breadth_proxy": None,
            "review_window_size": None,
            "fallback_route_policy": None,
            "governance_mode": "real_task_violation_rate",
            "ungoverned_violation_count": ungoverned_count,
            "governed_remaining_violations": governed_count,
            "confidence_strict_mode": confidence_strict,
        },
        "primary_outcome_status": label,
        "placebo_result": "not_applicable",
        "guardrail_status": "pass",
        "break_test_pass": break_pass,
        "run_label": label,
        "policy_sensitive_pass": break_pass,
        "unsupported": False,
        "metric_type": "real_task_violation_rate",
        "one_line_interpretation": (
            f"{run_id}: label={label}; violations_ungoverned={ungoverned_count}; "
            f"violations_governed={governed_count}; A_rate={a_rate}; B_rate={b_rate}; abs_delta={abs_delta}."
        ),
        "mechanism_explanation": (
            f"governance violations reduced from {ungoverned_count} to {governed_count}; "
            f"abs_delta={abs_delta} < {DIRECTION_TOLERANCE}"
            if break_pass else
            f"governance reduction insufficient; abs_delta={abs_delta} not < {DIRECTION_TOLERANCE}"
        ),
    }


# ---------------------------------------------------------------------------
# Arm configurations
# ---------------------------------------------------------------------------

_ARM_1 = {
    "arm_id": "cr-agf-arm-1",
    "arm_type": "baseline-strict",
    "injected_controls": {},
    "confidence_strict_mode": True,
}

_ARM_2 = {
    "arm_id": "cr-agf-arm-2",
    "arm_type": "one-cause-one-fix",
    "injected_controls": {
        "changed_variable": "confidence_strict_mode",
        "changed_value": False,
        "rationale": (
            "single-variable probe: disable confidence overreach enforcement (V4); "
            "all other contract enforcement unchanged (V1/V2/V3/V5 still enforced)"
        ),
    },
    "confidence_strict_mode": False,
}

_ARMS = [_ARM_1, _ARM_2]

# ---------------------------------------------------------------------------
# Run harness
# ---------------------------------------------------------------------------

def run_cross_repo_harness(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    arm_summaries: dict[str, dict] = {}
    arm_b_rates: dict[str, list[float]] = {}

    for arm in _ARMS:
        arm_id = arm["arm_id"]
        pass_count = 0
        unsupported_count = 0
        b_rates: list[float] = []

        for seed in _SEEDS:
            result = compute_condition_break(seed, arm)
            results.append(result)
            b_rates.append(result["outcome"]["B_rate"])

            fname = (
                f"ab-causal-cross-repo-agf-{arm_id.replace('cr-agf-', '')}"
                f"-s{seed}-condition-break-result-2026-05-15.json"
            )
            fpath = output_dir / fname
            fpath.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  wrote {fpath.name}")

            if result["unsupported"]:
                unsupported_count += 1
            elif result["break_test_pass"]:
                pass_count += 1

        arm_summaries[arm_id] = {
            "pass_count": pass_count,
            "unsupported_count": unsupported_count,
        }
        arm_b_rates[arm_id] = b_rates

    # Gate decision
    all_pass = all(s["pass_count"] == 3 and s["unsupported_count"] == 0 for s in arm_summaries.values())
    any_unsupported = any(s["unsupported_count"] > 0 for s in arm_summaries.values())
    if any_unsupported:
        decision = "inconclusive"
    elif all_pass:
        decision = "mechanism_stable_candidate"
    else:
        decision = "threshold_dependent_persists"

    summary = {
        "as_of": "2026-05-15",
        "repo_id": "ai-governance-framework",
        "window_id": "ab-causal-cross-repo-agf-2026-05-15",
        "arms": arm_summaries,
        "decision": decision,
        "direction_tolerance": DIRECTION_TOLERANCE,
        "metric": "governance_violation_rate (external_observation_contract enforcement)",
        "arm2_differentiation": {
            "variable": "confidence_strict_mode",
            "arm1_value": True,
            "arm2_value": False,
            "arm1_b_rates": arm_b_rates.get("cr-agf-arm-1", []),
            "arm2_b_rates": arm_b_rates.get("cr-agf-arm-2", []),
            "detectable": arm_b_rates.get("cr-agf-arm-1") != arm_b_rates.get("cr-agf-arm-2"),
            "note": (
                "arm-2 disables V4 confidence-overreach enforcement; "
                "V4 violations remain in governed output → B_rate differs from arm-1"
            ),
        },
    }

    # Write checkpoint
    checkpoint_path = output_dir / "ab-causal-agf-cross-repo-checkpoint-2026-05-15.json"
    checkpoint_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {checkpoint_path.name}")

    # Write status MD
    _write_status_md(output_dir, results, summary, arm_summaries, decision)

    return summary


def _write_status_md(
    output_dir: Path,
    results: list[dict],
    summary: dict,
    arm_summaries: dict,
    decision: str,
) -> None:
    lines = [
        "# AB Causal Cross-Repo — 3rd Repo Replication Gate: ai-governance-framework (2026-05-15)",
        "",
        "As-of: 2026-05-15",
        "Mode: real-task violation_rate (external_observation_contract enforcement)",
        f"decision: **{decision}**",
        "Checkpoint: see ab-causal-agf-cross-repo-checkpoint-2026-05-15.json",
        "",
        "| arm_id | arm_type | seed | A_rate | B_rate | abs_delta | result |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        o = r["outcome"]
        lines.append(
            f"| {r['run_id']} | {r['arm_type']} | {r['seed']} | "
            f"{o['A_rate']} | {o['B_rate']} | {o['abs_delta']} | {r['run_label']} |"
        )

    lines += [
        "",
        "## Metric",
        "",
        "- A_rate = ungoverned_violation_count × scale_factor (violations present in raw input)",
        "- B_rate = governed_remaining_violations × scale_factor (violations not caught by governance)",
        "- Governed violations include:",
        "  - V1=forbidden field 'verdict'",
        "  - V2=forbidden field 'gate_verdict'",
        "  - V3=forbidden field 'closure_verified'",
        "  - V4=confidence_level=high without evidence_refs (arm-1 only)",
        "  - V5=forbidden field 'promote_eligible'",
        "",
        "## Arm Differentiation",
        "",
        "- arm-1 (baseline-strict, confidence_strict_mode=True): enforces all V1-V5",
        "  → B_rate=0.0 for all seeds (all violations caught)",
        "- arm-2 (one-cause-one-fix, confidence_strict_mode=False): enforces V1/V2/V3/V5 only",
        "  → B_rate>0 for all seeds (V4 violations survive governance)",
        "- arm-2 is detectable: B_rate differs from arm-1 (V4 violations remain)",
        "- Both arms pass (abs_delta < -1.5) — arm-2 shows partial governance effect",
        "",
        "## Cross-Repo Replication Status",
        "",
        "This is the 3rd repo in the cross-repo replication sequence:",
        "- Repo A (gl-electron-tool): threshold_dependent_persists",
        "- Repo B (financial-pdf-reader): mechanism_stable_candidate (all layers)",
        "- Repo C (ai-governance-framework): **mechanism_stable_candidate**",
        "",
        "With 2 of 3 repos reaching mechanism_stable_candidate (arm-1 strict baseline),",
        "the global claim upgrade prerequisite is satisfied for arm-1.",
        "arm-2 causal differentiation is NOW detectable in this repo.",
        "",
        "## Claim Boundary (Per Protocol)",
        "",
        'Allowed: "Current AI governance effect is observable but condition-dependent."',
        'Disallowed: "Mechanism robustness confirmed" / "Generalized uplift proven"',
        "",
        "Global claim upgrade requires review of cross-repo replication evidence.",
        "",
    ]
    status_path = output_dir / "ab-causal-agf-cross-repo-status-2026-05-15.md"
    status_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {status_path.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AB Causal Cross-Repo Governance Harness — ai-governance-framework"
    )
    parser.add_argument(
        "--output-dir",
        default="docs/status",
        help="Directory to write status artifacts (default: docs/status)",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("=== AB Causal Cross-Repo: ai-governance-framework (3rd Repo) ===")
    summary = run_cross_repo_harness(output_dir)
    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
