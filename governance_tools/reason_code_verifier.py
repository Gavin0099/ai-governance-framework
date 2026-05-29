from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VerificationResult:
    ok: bool
    violations: list[str]


def load_registry_codes(registry_path: Path) -> set[str]:
    text = registry_path.read_text(encoding="utf-8")
    codes: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            codes.add(match.group(1))
    return codes


def _verify_gate_policy_codes(gate_policy_path: Path, codes: set[str]) -> list[str]:
    violations: list[str] = []
    doc = yaml.safe_load(gate_policy_path.read_text(encoding="utf-8")) or {}

    for reason in doc.get("blocking_actions", []) or []:
        if reason not in codes:
            violations.append(
                f"{gate_policy_path}: blocking_actions contains non-registered code '{reason}'"
            )

    unknown_mode = (doc.get("unknown_treatment") or {}).get("mode")
    if unknown_mode and unknown_mode not in codes:
        violations.append(
            f"{gate_policy_path}: unknown_treatment.mode contains non-registered code '{unknown_mode}'"
        )
    return violations


def _iter_signal_codes(audit_log_path: Path) -> list[str]:
    found: list[str] = []
    for line_no, line in enumerate(audit_log_path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = line.strip()
        if not raw:
            continue
        try:
            row: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for signal in row.get("signals", []) or []:
            found.append(f"{line_no}:{signal}")
    return found


def _verify_canonical_audit_codes(audit_log_path: Path, codes: set[str]) -> list[str]:
    if not audit_log_path.exists():
        print(f"[reason_code_verifier] notice: audit log not found, skipping: {audit_log_path}")
        return []
    violations: list[str] = []
    for tagged in _iter_signal_codes(audit_log_path):
        line_no, signal = tagged.split(":", 1)
        if signal not in codes:
            violations.append(
                f"{audit_log_path}:{line_no}: signals contains non-registered code '{signal}'"
            )
    return violations


def verify_gate_consumed_reason_fields(
    registry_path: Path, gate_policy_path: Path, audit_log_path: Path
) -> VerificationResult:
    codes = load_registry_codes(registry_path)
    violations = []
    violations.extend(_verify_gate_policy_codes(gate_policy_path, codes))
    violations.extend(_verify_canonical_audit_codes(audit_log_path, codes))
    return VerificationResult(ok=not violations, violations=violations)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minimal verification pass for gate-consumed reason fields."
    )
    parser.add_argument(
        "--registry",
        default="docs/governance/reason-code-registry.md",
        help="Path to reason code registry markdown",
    )
    parser.add_argument(
        "--gate-policy",
        default="governance/gate_policy.yaml",
        help="Path to gate policy yaml",
    )
    parser.add_argument(
        "--audit-log",
        default="artifacts/runtime/canonical-audit-log.jsonl",
        help="Path to canonical audit log jsonl",
    )
    args = parser.parse_args()

    result = verify_gate_consumed_reason_fields(
        registry_path=Path(args.registry),
        gate_policy_path=Path(args.gate_policy),
        audit_log_path=Path(args.audit_log),
    )
    if result.ok:
        print("PASS: gate-consumed reason fields use registered codes.")
        return 0

    print("FAIL: non-registered gate-consumed reason fields found.")
    for item in result.violations:
        print(f"- {item}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
