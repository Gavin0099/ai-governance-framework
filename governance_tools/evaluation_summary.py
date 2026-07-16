#!/usr/bin/env python3
"""Repo-local evaluation summary — pure aggregation, no LLM, no network.

Aggregates closeout receipts (schema 1.4+) into per-runtime-profile groups
per schemas/evaluation_summary.schema.json. By design there is no single
total score, and this tool cannot emit one.

Claim boundaries:
- model_binding is conservatively derived from runtime_detection_status:
  only "full" (agent+model+surface all signal-verified) maps to "verified";
  everything else maps to "unknown". Detected-tier model values are never
  silently merged into verified groups.
- counts.verified means "closeout completed with exit 0 and no blocker
  codes" — it is a receipt-state derivation, not proof of task correctness.
- maturity is capped at "provisional": the "established" rung additionally
  requires task diversity, which this tool cannot judge; promotion is a
  human decision recorded elsewhere.
- This artifact establishes observability; it is not G4 evidence.

Budget entry: docs/governance/agent-runtime-evaluation-budget-entry-2026-07-16.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EVALUATION_SUMMARY_SCHEMA_VERSION = "1.0"
TOOL_NAME = "governance_tools.evaluation_summary"
TOOL_VERSION = "0.1.0"
RECEIPTS_RELPATH = Path("artifacts") / "runtime" / "closeout-receipts"
MIN_RUNTIME_BOUND_SCHEMA = (1, 4)

_MATURITY_LADDER = (
    (3, "uncalibrated"),
    (10, "observed"),
    (30, "provisional"),
)
# >=30 stays "provisional" here: "established" additionally requires task
# diversity, which is a human judgment this tool must not automate.
_AUTOMATED_MATURITY_CEILING = "provisional"

_MODEL_BINDING_BY_DETECTION_STATUS = {"full": "verified"}


def _parse_period(raw: str) -> int:
    match = re.fullmatch(r"(\d+)d", raw.strip())
    if not match:
        raise ValueError(f"period must look like '30d', got {raw!r}")
    days = int(match.group(1))
    if days < 1:
        raise ValueError("period must be at least 1d")
    return days


def _parse_timestamp(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _schema_at_least(version: Any, minimum: tuple) -> bool:
    try:
        parts = tuple(int(p) for p in str(version).split("."))
    except ValueError:
        return False
    return parts >= minimum


def _rate(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else round(numerator / denominator, 4)


def _final_status(receipt: dict) -> str:
    """Receipt-state derivation, never agent self-assessment."""
    blockers = receipt.get("memory_workflow_blocker_codes") or []
    if blockers or receipt.get("output_mode_decision") == "block":
        return "blocked"
    if receipt.get("exit_code") == 0:
        return "verified"
    return "unproven"


def _evidence_complete(receipt: dict) -> bool:
    return all(receipt.get(k) not in (None, "", "unknown")
               for k in ("runtime_profile_id", "runtime_profile_coarse_id",
                         "runtime_detection_status", "sample_origin"))


def collect_receipts(repo_root: Path, since: datetime,
                     until: datetime) -> tuple:
    """Return (in-window runtime-bound receipts, excluded counters)."""
    receipts = []
    excluded = {"non_natural_samples": 0, "unreadable_receipts": 0,
                "pre_binding_receipts": 0}
    receipts_dir = repo_root / RECEIPTS_RELPATH
    if not receipts_dir.is_dir():
        return receipts, excluded
    for path in sorted(receipts_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            excluded["unreadable_receipts"] += 1
            continue
        stamp = _parse_timestamp(payload.get("timestamp"))
        if stamp is None or not (since <= stamp <= until):
            continue
        if not _schema_at_least(payload.get("schema_version"), MIN_RUNTIME_BOUND_SCHEMA):
            excluded["pre_binding_receipts"] += 1
            continue
        receipts.append(payload)
    return receipts, excluded


def build_summary(repo_root: Path, days: int,
                  now: Optional[datetime] = None) -> dict:
    until = now or datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    receipts, excluded = collect_receipts(repo_root, since, until)

    grouped: dict = {}
    for receipt in receipts:
        origin = receipt.get("sample_origin", "unknown")
        if origin not in ("natural_task", "benchmark", "regression_test",
                          "synthetic", "unknown"):
            origin = "unknown"
        if origin != "natural_task":
            excluded["non_natural_samples"] += 1
        coarse_id = receipt.get("runtime_profile_coarse_id") or "unknown"
        detection_status = receipt.get("runtime_detection_status", "unknown")
        model_binding = _MODEL_BINDING_BY_DETECTION_STATUS.get(
            detection_status, "unknown")
        grouped.setdefault((coarse_id, model_binding, origin), []).append(receipt)

    groups = []
    for (coarse_id, model_binding, origin), members in sorted(grouped.items()):
        statuses = [_final_status(r) for r in members]
        samples = len(members)
        full_ids = {r.get("runtime_profile_id") or "unknown" for r in members}
        drift_events = max(0, len(full_ids - {"unknown"}) - 1)
        unknown_detection = sum(
            1 for r in members
            if r.get("runtime_detection_status") in ("unknown", "none"))

        if drift_events > 0:
            maturity = "drifted"
        else:
            maturity = _AUTOMATED_MATURITY_CEILING
            for threshold, rung in _MATURITY_LADDER:
                if samples < threshold:
                    maturity = rung
                    break

        signal_tiers = {"test_backed": 0, "structural_only": 0,
                        "self_reported": 0, "unknown": 0}
        for receipt in members:
            signal = receipt.get("validator_signal")
            if isinstance(signal, dict) and signal.get("tier") in signal_tiers:
                signal_tiers[signal["tier"]] += 1

        group = {
            "coarse_id": coarse_id,
            "fingerprint_schema_version": "1.0",
            "model_binding": model_binding,
            "sample_origin": origin,
            "maturity": maturity,
            "counts": {
                "samples": samples,
                "verified": statuses.count("verified"),
                "blocked": statuses.count("blocked"),
                "unproven": statuses.count("unproven"),
            },
            "rates": {
                "evidence_completeness_rate": _rate(
                    sum(1 for r in members if _evidence_complete(r)), samples),
                "unknown_detection_ratio": _rate(unknown_detection, samples),
                # Validator execution/pass rates need validator receipts,
                # which closeout receipts do not carry yet: null, not 0.
                "validator_execution_rate": None,
                "validator_pass_rate": None,
            },
            "validator_signal_tiers": signal_tiers,
            "drift_events": drift_events,
        }
        if maturity == "provisional" and samples >= 30:
            group["task_diversity_note"] = (
                f"{samples} samples reach the 'established' count threshold, "
                "but task diversity is a human judgment; automated maturity "
                "is capped at provisional.")
        groups.append(group)

    return {
        "schema_version": EVALUATION_SUMMARY_SCHEMA_VERSION,
        "generated_at": until.isoformat(),
        "period": {"start": since.isoformat(), "end": until.isoformat(),
                   "days": days},
        "groups": groups,
        "excluded": excluded,
        "notes": [
            "observability artifact only; not G4 evidence",
            "counts.verified = clean closeout (exit 0, no blockers), "
            "not proof of task correctness",
        ],
        "generator": {"tool": TOOL_NAME, "tool_version": TOOL_VERSION,
                      "llm_calls": 0},
    }


def _render_summary(summary: dict) -> str:
    lines = [
        f"evaluation summary  period={summary['period']['days']}d  "
        f"groups={len(summary['groups'])}  (no total score by design; "
        "not G4 evidence)",
    ]
    for group in summary["groups"]:
        counts = group["counts"]
        lines.append(
            f"  {group['coarse_id']:16} model_binding={group['model_binding']:9} "
            f"origin={group['sample_origin']:15} maturity={group['maturity']:12} "
            f"samples={counts['samples']} verified={counts['verified']} "
            f"blocked={counts['blocked']} unproven={counts['unproven']} "
            f"drift_events={group['drift_events']}")
        note = group.get("task_diversity_note")
        if note:
            lines.append(f"{'':18} note: {note}")
    excluded = summary["excluded"]
    lines.append(f"  excluded: non_natural={excluded['non_natural_samples']} "
                 f"unreadable={excluded['unreadable_receipts']} "
                 f"pre_binding={excluded['pre_binding_receipts']}")
    return "\n".join(lines)


def _print_console_safe(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding))
    sys.stdout.write("\n")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Repo-local evaluation summary over closeout receipts. "
                    "Pure aggregation; no LLM; no total score.")
    parser.add_argument("--period", default="30d", help="window, e.g. 30d")
    parser.add_argument("--repo", default=".", help="repo root (default: cwd)")
    parser.add_argument("--out", default=None,
                        help="write summary JSON (UTF-8 bytes) to this path")
    parser.add_argument("--json", dest="print_json", action="store_true",
                        help="print summary JSON to stdout")
    args = parser.parse_args(argv)

    try:
        days = _parse_period(args.period)
    except ValueError as exc:
        _print_console_safe(f"error: {exc}")
        return 2

    summary = build_summary(Path(args.repo).resolve(), days)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(
            json.dumps(summary, indent=2, ensure_ascii=False).encode("utf-8"))
    if args.print_json:
        _print_console_safe(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        _print_console_safe(_render_summary(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
