#!/usr/bin/env python3
"""
State reconciliation validator for governance phase status vs runtime capability.

Primary guard:
- If Phase D is marked completed/passed while Phase C release-surface precedence
  integration is not present, fail closed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.state_generator import parse_gate_status


def _extract_phase_d_from_state_yaml(state_text: str) -> str | None:
    m = re.search(r"^\s*PhaseD:\s*([A-Za-z_]+)\s*$", state_text, re.MULTILINE)
    return m.group(1) if m else None


def _release_surface_precedence_ready(release_surface_text: str) -> bool:
    required_markers = (
        "precedence_applied",
        "lifecycle_effective_by_escalation",
    )
    return all(marker in release_surface_text for marker in required_markers)


def validate_state_reconciliation(
    *,
    plan_path: Path,
    state_path: Path,
    release_surface_path: Path,
) -> dict[str, Any]:
    plan_text = plan_path.read_text(encoding="utf-8")
    state_text = state_path.read_text(encoding="utf-8") if state_path.exists() else ""
    release_surface_text = (
        release_surface_path.read_text(encoding="utf-8")
        if release_surface_path.exists()
        else ""
    )

    plan_gate_status = parse_gate_status(plan_text)
    plan_phase_d = plan_gate_status.get("PhaseD")
    state_phase_d = _extract_phase_d_from_state_yaml(state_text)
    release_surface_ready = _release_surface_precedence_ready(release_surface_text)

    violations: list[str] = []
    if plan_phase_d == "passed" and not release_surface_ready:
        violations.append(
            "plan_marks_phase_d_completed_while_phase_c_release_surface_precedence_pending"
        )
    if state_phase_d == "passed" and not release_surface_ready:
        violations.append(
            "state_marks_phase_d_completed_while_phase_c_release_surface_precedence_pending"
        )

    return {
        "ok": len(violations) == 0,
        "plan_phase_d_status": plan_phase_d,
        "state_phase_d_status": state_phase_d,
        "release_surface_precedence_ready": release_surface_ready,
        "violations": violations,
    }


def _format_human(result: dict[str, Any]) -> str:
    lines = [
        "[state_reconciliation]",
        f"ok={result['ok']}",
        f"plan_phase_d_status={result.get('plan_phase_d_status')}",
        f"state_phase_d_status={result.get('state_phase_d_status')}",
        f"release_surface_precedence_ready={result.get('release_surface_precedence_ready')}",
    ]
    violations = result.get("violations") or []
    if violations:
        lines.append("violations=" + ",".join(violations))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate governance state reconciliation for Phase D closeout drift."
    )
    parser.add_argument("--plan", default="PLAN.md")
    parser.add_argument("--state", default=".governance-state.yaml")
    parser.add_argument(
        "--release-surface",
        default="governance_tools/release_surface_overview.py",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    result = validate_state_reconciliation(
        plan_path=Path(args.plan),
        state_path=Path(args.state),
        release_surface_path=Path(args.release_surface),
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_human(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
