#!/usr/bin/env python3
"""
Codex pre-task governance hook for nextjs-byok-contract.

Codex CLI reads AGENTS.md automatically (no hook needed for rules).
This script handles the runtime governance layer: plan_freshness check
and validator preflight, which Codex cannot run on its own.

Usage — wire via Codex project config or run manually before each session:

  python examples/nextjs-byok-contract/hooks/codex_pre_task.py

Output format: one key=value line per signal, suitable for Codex context
injection or CI stdout capture.

Codex AGENTS.md integration:
  The contract's AGENTS.md is read by Codex automatically when placed at:
    - project root  →  AGENTS.md
    - subdirectory  →  <subdir>/AGENTS.md (for scoped rules)
  No additional configuration needed for rule loading.

Runtime hook integration (optional, for plan_freshness):
  Codex supports a --before-task flag that runs a shell command.
  Example .codex/config.json:
  {
    "before_task": "python examples/nextjs-byok-contract/hooks/codex_pre_task.py"
  }
"""

from __future__ import annotations

import sys
from pathlib import Path

# Locate the framework root
_HERE = Path(__file__).resolve().parent
for candidate in [
    _HERE.parents[3],
    Path("D:/ai-governance-framework"),
    Path("../ai-governance-framework"),
]:
    if (candidate / "governance_tools").exists():
        sys.path.insert(0, str(candidate))
        break


def _plan_freshness(plan_path: Path, threshold_days: int = 7) -> dict:
    try:
        from governance_tools.plan_freshness import check_plan_freshness
        return check_plan_freshness(plan_path, threshold_days=threshold_days)
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


def _validator_preflight(contract_path: Path) -> dict:
    try:
        from governance_tools.domain_validator_loader import preflight_domain_validators
        from governance_tools.domain_contract_loader import load_domain_contract
        contract = load_domain_contract(contract_path)
        if contract is None:
            return {"ok": False, "error": "contract not found"}
        return preflight_domain_validators(contract)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    plan_path = Path("PLAN.md")
    contract_path = Path("examples/nextjs-byok-contract/contract.yaml")

    freshness = _plan_freshness(plan_path)
    preflight = _validator_preflight(contract_path)

    status = freshness.get("status", "UNKNOWN")
    ok = preflight.get("ok", False)

    # Codex reads stdout as pre-task context
    print("[governance:pre-task]")
    print(f"harness=codex")
    print(f"plan_freshness={status}")
    print(f"validator_preflight_ok={ok}")
    print(f"domain=nextjs-byok")
    print(f"active_rules=BYOK_INGEST_KEY_PROPAGATION,ROUTE_RATE_LIMIT_COVERAGE")

    if status in ("STALE", "CRITICAL", "ERROR"):
        print(f"WARNING: PLAN.md is {status} — update before architectural changes.")
    if not ok:
        print("WARNING: validator preflight failed — check contract.yaml.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
