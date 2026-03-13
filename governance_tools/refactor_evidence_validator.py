#!/usr/bin/env python3
"""
Validate evidence required by refactor governance rules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REGRESSION_PATTERNS = [
    r"regression",
    r"characterization",
    r"behavior[_\- ]?lock",
    r"contract",
    r"compat",
]

INTERFACE_STABILITY_PATTERNS = [
    r"interface",
    r"signature",
    r"contract",
    r"public[_\- ]?api",
    r"compat",
    r"callback",
]

CLEANUP_PATTERNS = [
    r"rollback",
    r"cleanup",
    r"clean[_\- ]?up",
    r"dispose",
    r"release",
    r"revert",
]


def _normalize_names(test_names: list[str] | None) -> list[str]:
    return [str(name).strip().lower() for name in (test_names or []) if str(name).strip()]


def _has_pattern(values: list[str], patterns: list[str]) -> bool:
    return any(re.search(pattern, value, re.IGNORECASE) for value in values for pattern in patterns)


def validate_refactor_evidence(checks: dict | None) -> dict:
    checks = checks or {}
    test_names = _normalize_names(checks.get("test_names"))
    failure_validation = checks.get("failure_test_validation") or {}

    signals_detected = {
        "regression_evidence": _has_pattern(test_names, REGRESSION_PATTERNS),
        "interface_stability_evidence": _has_pattern(test_names, INTERFACE_STABILITY_PATTERNS)
        or bool(checks.get("interface_stability_verified")),
        "cleanup_evidence": _has_pattern(test_names, CLEANUP_PATTERNS)
        or bool(checks.get("cleanup_verified"))
        or (
            (failure_validation.get("coverage") or {}).get("rollback_cleanup", {}).get("count", 0) > 0
        ),
    }

    warnings: list[str] = []
    errors: list[str] = []

    if not signals_detected["regression_evidence"]:
        errors.append("Missing refactor evidence: regression-oriented test signal")

    if not signals_detected["interface_stability_evidence"]:
        errors.append("Missing refactor evidence: interface stability signal")

    if not signals_detected["cleanup_evidence"]:
        warnings.append("Refactor cleanup / rollback evidence was not detected.")

    return {
        "ok": len(errors) == 0,
        "evidence_required": [
            "regression_evidence",
            "interface_stability_evidence",
            "cleanup_evidence",
        ],
        "signals_detected": signals_detected,
        "warnings": warnings,
        "errors": errors,
        "evidence_summary": {
            "test_names_count": len(test_names),
            "failure_validation_present": bool(failure_validation),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate refactor evidence from runtime checks.")
    parser.add_argument("--file", required=True, help="JSON checks file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    checks = json.loads(Path(args.file).read_text(encoding="utf-8"))
    result = validate_refactor_evidence(checks)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']}")
        for key, value in result["signals_detected"].items():
            print(f"{key}={str(value).lower()}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
