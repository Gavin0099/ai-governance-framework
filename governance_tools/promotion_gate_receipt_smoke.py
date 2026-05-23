#!/usr/bin/env python3
"""
Smoke check for promotion gate receipt determinism without pytest dependency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.change_control_summary import build_change_control_summary


def _build_case(task_status: str) -> dict:
    return build_change_control_summary(
        session_start={
            "task_text": "promotion gate smoke",
            "task_provenance": {"status": task_status, "source_key": "prompt"},
            "proposal_summary": {
                "recommended_risk": "medium",
                "recommended_oversight": "review-required",
            },
        },
        session_end={
            "decision": "AUTO_PROMOTE",
            "promoted": True,
            "public_api_diff_present": False,
        },
    )


def main() -> int:
    base_a = _build_case("accepted")
    base_b = _build_case("accepted")
    changed = _build_case("placeholder_suppressed")

    gate_a = base_a.get("promotion_gate") or {}
    gate_b = base_b.get("promotion_gate") or {}
    gate_c = changed.get("promotion_gate") or {}

    checks = {
        "same_input_digest_stable": gate_a.get("gate_inputs_digest") == gate_b.get("gate_inputs_digest"),
        "relevant_input_change_digest_changes": gate_a.get("gate_inputs_digest") != gate_c.get("gate_inputs_digest"),
        "contract_version_is_v0_1": gate_a.get("promotion_gate_contract_version") == "0.1",
    }

    ok = all(checks.values())
    payload = {
        "ok": ok,
        "checks": checks,
        "base_digest": gate_a.get("gate_inputs_digest"),
        "changed_digest": gate_c.get("gate_inputs_digest"),
        "base_allowed": gate_a.get("allowed"),
        "changed_allowed": gate_c.get("allowed"),
        "changed_blocking_reasons": gate_c.get("blocking_reasons"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

