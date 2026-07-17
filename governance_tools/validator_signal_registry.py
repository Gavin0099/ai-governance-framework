#!/usr/bin/env python3
"""Registry-derived validator signal tiers — lookup only, never agent-filled.

Resolves a validator id to a trust tier (test_backed / structural_only /
self_reported / unknown) from governance/runtime/validator_signal_registry.json.
The tier says how much a validator's pass/fail signal can be trusted, so that
downstream evaluation statistics can separate test-backed validation from
coverage theater (2026-07-06 consumer test-quality audit).

Claim boundary: a tier is a registry classification made by human review at
`since_version`; it is not proof the validator is currently correct. A missing
registry entry always resolves to "unknown" — this module never guesses and
never accepts a tier supplied by the agent being evaluated.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VALIDATOR_SIGNAL_TIERS = ("test_backed", "structural_only", "self_reported", "unknown")
DEFAULT_REGISTRY_RELPATH = Path("governance") / "runtime" / "validator_signal_registry.json"
FALLBACK_REGISTRY_ID = "registry-unavailable"


def load_registry(repo_root: Path) -> dict:
    """Load the registry; unreadable or malformed files degrade to empty."""
    try:
        payload = json.loads(
            (repo_root / DEFAULT_REGISTRY_RELPATH).read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("entries"), dict):
            return payload
    except (OSError, ValueError):
        pass
    return {"registry_id": FALLBACK_REGISTRY_ID, "entries": {}}


def resolve_validator_signal(validator_id: str, repo_root: Path,
                             validator_version: Optional[str] = None,
                             registry: Optional[dict] = None) -> dict:
    """Return a receipt-ready validator_signal object for validator_id.

    Output conforms to the validator_signal property of
    schemas/closeout_receipt.schema.json (schema 1.4). Unregistered ids and
    invalid registry tiers resolve to "unknown".
    """
    registry = registry if registry is not None else load_registry(repo_root)
    registry_id = str(registry.get("registry_id") or FALLBACK_REGISTRY_ID)
    entry = registry.get("entries", {}).get(validator_id)

    tier = "unknown"
    if isinstance(entry, dict) and entry.get("tier") in VALIDATOR_SIGNAL_TIERS:
        tier = entry["tier"]

    signal = {
        "validator_id": validator_id,
        "tier": tier,
        "tier_source": registry_id,
    }
    if validator_version:
        signal["validator_version"] = str(validator_version)
    return signal


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="governance_tools.validator_signal_registry",
        description="Resolve a validator id to its registry-derived signal tier.")
    parser.add_argument("validator_id")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--validator-version", default=None)
    args = parser.parse_args(argv)

    signal = resolve_validator_signal(
        args.validator_id, Path(args.repo).resolve(),
        validator_version=args.validator_version)
    print(json.dumps(signal, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
