#!/usr/bin/env python3
"""
Governance Intervention Reality Report

Consumes intercepted-events.ndjson and bypass-events.ndjson to produce
a deliberately honest account of what the governance framework has actually
changed in practice.

Only 'observed' evidence counts toward operational effectiveness.
retroactive_analysis and test_derived entries are surfaced but do not advance
any effectiveness claim.

Usage:
    python -m governance_tools.honest_state_report --project-root .
    python -m governance_tools.honest_state_report --project-root . --format json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_INTERCEPTED_PATH = "artifacts/governance/intercepted-events.ndjson"
_BYPASS_PATH = "artifacts/governance/bypass-events.ndjson"

_OBSERVED = "observed"
_HIGH = "high"


def _load_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def _derive_effectiveness(
    observed_interception_count: int,
    high_materiality_observed_count: int,
) -> str:
    """
    Operational effectiveness vocabulary (intentionally bounded):

    not_yet_demonstrated  — no observed interceptions at all
    insufficient_evidence — some observed interceptions but none high-materiality
    partially_demonstrated — at least one high-materiality observed interception

    'demonstrated' is not in this vocabulary.
    Demonstrated effectiveness requires external validation, not self-report.
    """
    if observed_interception_count == 0:
        return "not_yet_demonstrated"
    if high_materiality_observed_count == 0:
        return "insufficient_evidence"
    return "partially_demonstrated"


def _permitted_conclusion(effectiveness: str, observed_bypass_count: int) -> str:
    if effectiveness == "not_yet_demonstrated":
        if observed_bypass_count > 0:
            return (
                "ineffective regions have begun to be observed; "
                "operational leverage not yet demonstrated"
            )
        return "ledger established; no operational evidence yet recorded in either direction"
    if effectiveness == "insufficient_evidence":
        return (
            "some observed interceptions exist but no high-materiality observed event; "
            "effectiveness not demonstrable"
        )
    return (
        "partial operational evidence exists; "
        "external validation required before claiming effectiveness"
    )


def _forbidden_conclusion() -> str:
    return "framework has demonstrated operational leverage in real-world execution"


def build_report(project_root: Path) -> dict[str, Any]:
    intercepted = _load_ndjson(project_root / _INTERCEPTED_PATH)
    bypassed = _load_ndjson(project_root / _BYPASS_PATH)

    observed_interceptions = [e for e in intercepted if e.get("evidence_basis") == _OBSERVED]
    observed_bypasses = [e for e in bypassed if e.get("evidence_basis") == _OBSERVED]

    # High-materiality observed across BOTH ledgers (interceptions only for effectiveness)
    high_mat_observed_interceptions = [
        e for e in intercepted
        if e.get("evidence_basis") == _OBSERVED and e.get("materiality") == _HIGH
    ]

    basis_dist = dict(Counter(e.get("evidence_basis", "unknown") for e in intercepted))

    effectiveness = _derive_effectiveness(
        len(observed_interceptions),
        len(high_mat_observed_interceptions),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_version": "v0.1",
        "intercepted_total": len(intercepted),
        "bypass_total": len(bypassed),
        "observed_interception_count": len(observed_interceptions),
        "observed_bypass_count": len(observed_bypasses),
        "high_materiality_observed_count": len(high_mat_observed_interceptions),
        "interception_basis_distribution": basis_dist,
        "operational_effectiveness": effectiveness,
        "permitted_conclusion": _permitted_conclusion(effectiveness, len(observed_bypasses)),
        "forbidden_conclusion": _forbidden_conclusion(),
        "sources": {
            "intercepted": _INTERCEPTED_PATH,
            "bypass": _BYPASS_PATH,
        },
    }


def format_human(report: dict[str, Any]) -> str:
    lines = [
        "[Governance Intervention Reality Report]",
        f"generated:  {report['generated_at']}",
        f"ledger:     {report['ledger_version']}",
        "",
        f"OBSERVED INTERCEPTIONS:        {report['observed_interception_count']}",
        f"OBSERVED BYPASSES:             {report['observed_bypass_count']}",
        f"HIGH-MATERIALITY (observed):   {report['high_materiality_observed_count']}",
        "",
        "INTERCEPTION BASIS DISTRIBUTION:",
    ]
    dist = report["interception_basis_distribution"]
    if dist:
        for basis in sorted(dist):
            lines.append(f"  {basis:<26} {dist[basis]}")
    else:
        lines.append("  (no entries)")
    lines += [
        "",
        f"OPERATIONAL EFFECTIVENESS:     {report['operational_effectiveness']}",
        "",
        "---",
        f"Permitted:  {report['permitted_conclusion']}",
        f"Forbidden:  {report['forbidden_conclusion']}",
        "",
        f"Sources: {report['sources']['intercepted']}",
        f"         {report['sources']['bypass']}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Governance Intervention Reality Report — "
            "honest account of what governance has changed in practice"
        )
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    report = build_report(Path(args.project_root).resolve())
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
