#!/usr/bin/env python3
"""
CI Governance Check — Runtime Enforcement Attachment v0.1

Proves governance can execute on a real repo lifecycle boundary.
Non-goal: prove governance effectiveness.

A bypass is "unmitigated" when evidence_basis=observed AND
neither a non-empty `resolution` field nor `accepted_risk: true` is present.

Exit codes:
  0 — clean, or --warn-only flag set
  1 — unmitigated observed bypasses detected
  2 — internal error (malformed ledger)

Usage:
    python -m governance_tools.ci_governance_check --project-root .
    python -m governance_tools.ci_governance_check --project-root . --warn-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_tools.honest_state_report import _load_ndjson, build_report

_BYPASS_PATH = "artifacts/governance/bypass-events.ndjson"
_INTERCEPTED_PATH = "artifacts/governance/intercepted-events.ndjson"


def _is_mitigated(bypass: dict) -> bool:
    if bypass.get("accepted_risk") is True:
        return True
    resolution = bypass.get("resolution", "")
    return bool(resolution and str(resolution).strip())


def check(project_root: Path) -> dict[str, Any]:
    bypass_path = project_root / _BYPASS_PATH
    intercepted_path = project_root / _INTERCEPTED_PATH

    bypasses = _load_ndjson(bypass_path)
    observed_bypasses = [e for e in bypasses if e.get("evidence_basis") == "observed"]
    unmitigated = [e for e in observed_bypasses if not _is_mitigated(e)]

    report = build_report(project_root)

    return {
        "governance_present": True,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "ledger_files": {
            "intercepted": intercepted_path.exists(),
            "bypass": bypass_path.exists(),
        },
        "observed_bypass_count": len(observed_bypasses),
        "unmitigated_bypass_count": len(unmitigated),
        "unmitigated_bypass_ids": [e.get("event_id", "?") for e in unmitigated],
        "operational_effectiveness": report["operational_effectiveness"],
        "clean": len(unmitigated) == 0,
    }


def format_human(result: dict[str, Any]) -> str:
    lines = [
        "[CI Governance Check — Runtime Enforcement Attachment v0.1]",
        f"executed_at:             {result['executed_at']}",
        f"governance_present:      {result['governance_present']}",
        "",
        f"ledger.intercepted:      {'present' if result['ledger_files']['intercepted'] else 'absent'}",
        f"ledger.bypass:           {'present' if result['ledger_files']['bypass'] else 'absent'}",
        "",
        f"observed_bypass_count:   {result['observed_bypass_count']}",
        f"unmitigated_bypasses:    {result['unmitigated_bypass_count']}",
    ]
    if result["unmitigated_bypass_ids"]:
        for eid in result["unmitigated_bypass_ids"]:
            lines.append(f"  - {eid}")
    lines += [
        "",
        f"operational_effectiveness: {result['operational_effectiveness']}",
        "",
        f"check: {'PASS' if result['clean'] else 'FAIL — unmitigated observed bypasses'}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CI Governance Check — proves governance executes on repo lifecycle boundary. "
            "Non-goal: prove governance effectiveness."
        )
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print warnings but always exit 0 (non-blocking CI mode)",
    )
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    result = check(Path(args.project_root).resolve())

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human(result))

    if result["clean"] or args.warn_only:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
