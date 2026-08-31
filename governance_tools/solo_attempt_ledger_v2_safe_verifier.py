#!/usr/bin/env python3
"""Whitelist-only verifier for the Solo public lifecycle ledger v2."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Final

from governance_tools.solo_attempt_ledger_v2 import (
    ATTEMPT_CEILING_TOTAL,
    LEDGER_SCHEMA,
    LedgerError,
    LedgerSummary,
    validate_ledger_file,
)


VERIFIER_SCHEMA: Final = "solo_attempt_ledger_v2_safe_verifier.v1"
OUTPUT_KEYS: Final = (
    "verifier_schema",
    "status",
    "code",
    "schema_version",
    "ledger_event_count",
    "pair_count",
    "admitted_attempt_count",
    "initiated_attempt_count",
    "terminal_execution_count",
    "scoring_record_count",
    "unblinding_record_count",
    "attempt_ceiling_total",
    "next_event_seq",
    "public_schema_closed",
)


def _result(*, status: str, code: str, **updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "verifier_schema": VERIFIER_SCHEMA,
        "status": status,
        "code": code,
        "schema_version": "UNAVAILABLE",
        "ledger_event_count": 0,
        "pair_count": 0,
        "admitted_attempt_count": 0,
        "initiated_attempt_count": 0,
        "terminal_execution_count": 0,
        "scoring_record_count": 0,
        "unblinding_record_count": 0,
        "attempt_ceiling_total": ATTEMPT_CEILING_TOTAL,
        "next_event_seq": 0,
        "public_schema_closed": True,
    }
    result.update(updates)
    return result


def _summary_result(summary: LedgerSummary) -> dict[str, object]:
    return _result(
        status="PASS",
        code="OK",
        schema_version=summary.schema_version,
        ledger_event_count=summary.ledger_event_count,
        pair_count=summary.pair_count,
        admitted_attempt_count=summary.admitted_attempt_count,
        initiated_attempt_count=summary.initiated_attempt_count,
        terminal_execution_count=summary.terminal_execution_count,
        scoring_record_count=summary.scoring_record_count,
        unblinding_record_count=summary.unblinding_record_count,
        attempt_ceiling_total=summary.attempt_ceiling_total,
        next_event_seq=summary.next_event_seq,
        public_schema_closed=summary.public_schema_closed,
    )


def verify_public_ledger(path: Path) -> dict[str, object]:
    """Validate a ledger while returning only fixed flat scalar fields."""

    try:
        return _summary_result(validate_ledger_file(path))
    except LedgerError as exc:
        return _result(status="FAIL", code=exc.code)
    except Exception:  # pragma: no cover - last-resort redaction boundary
        return _result(status="FAIL", code="UNEXPECTED_ERROR")


def render_result(result: dict[str, object]) -> str:
    """Render only the fixed flat scalar output contract."""

    if tuple(result.keys()) != OUTPUT_KEYS:
        raise ValueError("SAFE_OUTPUT_KEY_MISMATCH")
    if any(isinstance(value, (dict, list, tuple, set)) for value in result.values()):
        raise ValueError("SAFE_OUTPUT_NESTING_REJECTED")
    return json.dumps(result, ensure_ascii=True, sort_keys=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != "--ledger":
        result = _result(status="FAIL", code="ARGUMENT_ERROR")
    else:
        result = verify_public_ledger(Path(args[1]))

    try:
        output = render_result(result)
    except Exception:  # pragma: no cover - fixed fail-closed fallback
        output = render_result(_result(status="FAIL", code="OUTPUT_CONTRACT_ERROR"))
        print(output)
        return 2
    print(output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
