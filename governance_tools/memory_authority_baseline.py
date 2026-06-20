#!/usr/bin/env python3
"""memory_authority_baseline.py — advisory count-bucket baseline for the memory
authority guard.

Read-layer above ``memory_authority_guard`` (see
``docs/governance/memory-authority-baseline-spec.md`` v0.2). It freezes the
current warning debt as per-key counts and later reports
``new-since-baseline + active`` instead of the standing total, to reduce warning
fatigue.

It is advisory only: ``blocking`` is always False, it never changes the guard,
enforcement, or memory content.

Model (spec §2): per-record identity is not viable (the guard's ``entry`` field
is only the entry header line, which repeats), so violations are banked as
**counts per identity_key bucket**, not per-record ids.

Invariants (spec §4):
  SI-1  active findings are computed OUTSIDE baseline subtraction (full count).
  SI-2  writing a baseline is refused if active_non_canonical_writer > 0.
  SI-3  per baselineable key, only the snapshot count is debt; excess is new.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from governance_tools.memory_authority_guard import (
    filter_active_non_canonical_writer_violations,
    run_guard,
)

# Codes that may be banked into a baseline. active_non_canonical_writer is a
# recency-filtered subset of non_canonical_writer and is excluded by id (SI-1),
# never by code.
BASELINEABLE_CODES = (
    "unbound_memory",
    "non_canonical_writer",
    "structural_memory_auto_write",
    "missing_canonical_memory",
)

# Per-class identity fields pinned against real guard JSON (spec §2).
IDENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "unbound_memory": ("file", "entry", "reason"),
    "non_canonical_writer": ("file", "entry", "reason"),
    "structural_memory_auto_write": ("file", "section", "reason"),
    "missing_canonical_memory": ("date", "reason"),
}
_DEFAULT_FIELDS = ("file", "entry", "section", "date", "reason")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def identity_key(violation: dict) -> str:
    """Stable bucket key (NOT a per-record id) over pinned per-class fields."""
    code = str(violation.get("code", ""))
    fields = IDENTITY_FIELDS.get(code, _DEFAULT_FIELDS)
    parts = [code] + [_norm(violation.get(f)) for f in fields]
    raw = "\x1f".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _display(violation: dict) -> str:
    code = str(violation.get("code", ""))
    fields = IDENTITY_FIELDS.get(code, _DEFAULT_FIELDS)
    bits = [f"{f}={violation.get(f)!r}" for f in fields if violation.get(f) is not None]
    return code + (" · " + " · ".join(bits) if bits else "")


def bucket_counts(violations: Sequence[dict]) -> "OrderedDict[str, dict]":
    """Collapse baselineable violations into {identity_key: {code, count, ...}}."""
    buckets: "OrderedDict[str, dict]" = OrderedDict()
    for violation in violations:
        if violation.get("code") not in BASELINEABLE_CODES:
            continue
        key = identity_key(violation)
        bucket = buckets.get(key)
        if bucket is None:
            buckets[key] = {
                "identity_key": key,
                "code": violation.get("code"),
                "count": 1,
                "reason": violation.get("reason"),
                "display": _display(violation),
            }
        else:
            bucket["count"] += 1
    return buckets


def _split_active(guard_result: dict, active_from: str | None) -> tuple[list[dict], list[dict]]:
    """Return (active_violations, baselineable_violations).

    active is computed via the guard's own recency filter; baselineable is the
    rest (SI-1: active is never bucketed/suppressed).
    """
    violations = list(guard_result.get("violations", []))
    if active_from is None:
        active = filter_active_non_canonical_writer_violations(violations)
    else:
        active = filter_active_non_canonical_writer_violations(violations, active_from=active_from)
    active_ids = {id(v) for v in active}
    baselineable = [
        v for v in violations
        if id(v) not in active_ids and v.get("code") in BASELINEABLE_CODES
    ]
    return active, baselineable


def build_baseline(
    guard_result: dict,
    *,
    active_from: str | None = None,
    source_head: str = "",
) -> dict:
    """Freeze current debt as a count-bucket baseline. Refuses if active > 0 (SI-2)."""
    active, baselineable = _split_active(guard_result, active_from)
    if active:
        raise ValueError(
            f"refusing to write baseline: active_non_canonical_writer={len(active)} "
            f"(SI-2 — an active blocker must not be frozen as historical debt)"
        )
    buckets = list(bucket_counts(baselineable).values())
    by_code: dict[str, int] = {}
    for bucket in buckets:
        by_code[bucket["code"]] = by_code.get(bucket["code"], 0) + bucket["count"]
    return {
        "schema_version": "0.2",
        "model": "count_bucket",
        "baseline_id": f"memory-authority-baseline-{datetime.now(timezone.utc):%Y-%m-%d}",
        "created_at": _utc_now(),
        "source_command": "python -m governance_tools.memory_authority_guard --format json",
        "source_head": source_head,
        "claim_class": "advisory",
        "blocking": False,
        "not_enforcement": True,
        "safety_invariant": "active_non_canonical_writer is never part of this baseline (SI-2).",
        "summary": {"total": sum(b["count"] for b in buckets), "by_code": by_code},
        "buckets": buckets,
    }


def compare(guard_result: dict, baseline: dict, *, active_from: str | None = None) -> dict:
    """Compare current guard output against a frozen baseline (count-delta)."""
    active, baselineable = _split_active(guard_result, active_from)
    current = bucket_counts(baselineable)
    baseline_buckets = {b["identity_key"]: b for b in baseline.get("buckets", [])}

    suppressed = 0
    new = 0
    new_detail: list[dict] = []
    for key in set(current) | set(baseline_buckets):
        cc = current.get(key, {}).get("count", 0)
        bc = baseline_buckets.get(key, {}).get("count", 0)
        suppressed += min(cc, bc)
        delta = max(0, cc - bc)
        if delta:
            new += delta
            src = current.get(key) or baseline_buckets.get(key, {})
            new_detail.append({
                "identity_key": key,
                "code": src.get("code"),
                "display": src.get("display"),
                "baseline_count": bc,
                "current_count": cc,
                "new": delta,
            })

    current_total = int(guard_result.get("violation_count", len(guard_result.get("violations", []))))
    baseline_total = int(baseline.get("summary", {}).get("total", 0))
    return {
        "tool": "memory_authority_baseline",
        "claim_class": "advisory",
        "blocking": False,
        "baseline_id": baseline.get("baseline_id"),
        "total_historical_debt": baseline_total,
        "current_total": current_total,
        "suppressed_by_baseline": suppressed,
        "new_since_baseline": new,
        "active_fresh_findings": len(active),
        "baseline_shrink_hint": current_total < baseline_total,
        "new_buckets": sorted(new_detail, key=lambda d: -d["new"]),
    }


def format_human(payload: dict) -> str:
    line = (
        f"[memory-authority-baseline] "
        f"new={payload['new_since_baseline']} | "
        f"active={payload['active_fresh_findings']} | "
        f"suppressed={payload['suppressed_by_baseline']} | "
        f"current_total={payload['current_total']} | "
        f"baseline={payload['total_historical_debt']}"
    )
    lines = [line]
    if payload.get("baseline_shrink_hint"):
        lines.append("  hint: current_total < baseline — baseline can be re-frozen smaller")
    for bucket in payload.get("new_buckets", [])[:10]:
        lines.append(
            f"  +{bucket['new']} {bucket['code']}: {bucket['display']} "
            f"(baseline={bucket['baseline_count']} current={bucket['current_count']})"
        )
    return "\n".join(lines)


def _load_guard(project_root: Path, memory_root: Path, skip_git: bool) -> dict:
    return run_guard(memory_root, project_root, skip_git=skip_git)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory count-bucket baseline for the memory authority guard."
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--memory-root", type=Path, default=None)
    parser.add_argument("--baseline", type=Path, default=None, help="Baseline JSON to compare against.")
    parser.add_argument("--write-baseline", type=Path, default=None, help="Freeze current debt to this path (SI-2).")
    parser.add_argument("--active-from", default=None)
    parser.add_argument("--skip-git", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    memory_root = args.memory_root or (args.project_root / "memory")
    guard_result = _load_guard(args.project_root, memory_root, args.skip_git)

    if args.write_baseline is not None:
        try:
            baseline = build_baseline(guard_result, active_from=args.active_from)
        except ValueError as exc:
            print(f"[memory-authority-baseline] {exc}", file=sys.stderr)
            return 1
        args.write_baseline.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[memory-authority-baseline] wrote baseline ({baseline['summary']['total']} debt) to {args.write_baseline}")
        return 0

    if args.baseline is None:
        parser.error("either --baseline or --write-baseline is required")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    payload = compare(guard_result, baseline, active_from=args.active_from)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_human(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
