#!/usr/bin/env python3
"""
Claude Code UserPromptSubmit hook — session-start governance check.

Runs plan_freshness and validator preflight on every new conversation.
Output goes to stdout so Claude Code injects it as session context.

Configure in .claude/settings.json:
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{"type": "command",
                   "command": "python examples/nextjs-byok-contract/hooks/check_session.py"}]
      }
    ]
  }
}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow imports from the ai-governance-framework root when invoked from the
# target project directory.
_HERE = Path(__file__).resolve().parent
for candidate in [
    _HERE.parents[3],                          # framework root if example is embedded
    Path("D:/ai-governance-framework"),        # absolute fallback
    Path("../ai-governance-framework"),
]:
    if (candidate / "governance_tools").exists():
        sys.path.insert(0, str(candidate))
        break


def _plan_freshness(plan_path: Path, threshold_days: int = 7) -> dict:
    """Run plan_freshness check; return a simple status dict."""
    try:
        from governance_tools.plan_freshness import check_plan_freshness
        result = check_plan_freshness(plan_path, threshold_days=threshold_days)
        return result
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


def _validator_preflight(contract_path: Path) -> dict:
    """Load the domain contract validators; return preflight status."""
    try:
        from governance_tools.domain_validator_loader import preflight_domain_validators
        from governance_tools.domain_contract_loader import load_domain_contract
        contract = load_domain_contract(contract_path)
        if contract is None:
            return {"ok": False, "error": "contract not found"}
        result = preflight_domain_validators(contract)
        return {"ok": result.get("ok", False), "validators": result.get("validators", [])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    plan_path = Path("PLAN.md")
    contract_path = Path("examples/nextjs-byok-contract/contract.yaml")

    freshness = _plan_freshness(plan_path)
    preflight = _validator_preflight(contract_path)

    status = freshness.get("status", "UNKNOWN")
    ok = preflight.get("ok", False)

    lines = ["[governance:session-start]"]
    lines.append(f"plan_freshness={status}")
    lines.append(f"validator_preflight_ok={ok}")

    if status in ("STALE", "CRITICAL", "ERROR"):
        lines.append(
            f"WARNING: PLAN.md is {status} — update before architectural changes."
        )
    if not ok:
        lines.append(
            "WARNING: domain validator preflight failed — check contract.yaml paths."
        )

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
