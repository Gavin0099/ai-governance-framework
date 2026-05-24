#!/usr/bin/env python3
"""
compare_failure_topology.py

Compare a current pytest run against a frozen failure topology baseline.

Classifies failures into:
  stable_failures    — in baseline AND current (expected, pre-existing)
  new_regressions    — in current but NOT in baseline (warrants investigation)
  recoveries         — in baseline but NOT in current (improvement)
  unparsed           — lines that looked like failures but couldn't be parsed

Output: human-readable report + optional JSON.
Does NOT gate CI. Diagnostic only.

Usage examples:

  # From pytest -v output piped to file
  pytest -v --tb=no 2>&1 | grep "^FAILED" > current_failures.txt
  python scripts/compare_failure_topology.py --current current_failures.txt

  # From pytest JSON report (requires pytest-json-report)
  pytest --json-report --json-report-file=report.json
  python scripts/compare_failure_topology.py --current-json report.json

  # Check baseline admissibility (print metadata only)
  python scripts/compare_failure_topology.py --baseline-info

  # Explicit baseline path
  python scripts/compare_failure_topology.py \\
      --baseline artifacts/test-baseline/failure-topology-v0.1.json \\
      --current current_failures.txt \\
      --format json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_DEFAULT_BASELINE = Path(__file__).parent.parent / "artifacts" / "test-baseline" / "failure-topology-v0.1.json"
_FAILED_LINE_RE = re.compile(r"^FAILED\s+(tests/\S+)", re.MULTILINE)
_NODEID_RE = re.compile(r"^tests/\S+::\S+$")


def _load_baseline(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_nodeid_file(path: Path) -> tuple[list[str], list[str]]:
    """Parse a file of node IDs — one per line, or 'FAILED tests/...' format."""
    nodeids = []
    unparsed = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # 'FAILED tests/foo.py::test_bar' format (from pytest -v stdout)
        m = _FAILED_LINE_RE.match(line)
        if m:
            nodeids.append(m.group(1))
            continue
        # bare node ID format
        if _NODEID_RE.match(line):
            nodeids.append(line)
            continue
        unparsed.append(line)
    return nodeids, unparsed


def _parse_pytest_json_report(path: Path) -> tuple[list[str], list[str]]:
    """Parse a pytest-json-report output file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    nodeids = []
    unparsed = []
    # pytest-json-report format: {"tests": [{"nodeid": "...", "outcome": "failed"}, ...]}
    for test in data.get("tests", []):
        if test.get("outcome") == "failed":
            nodeid = test.get("nodeid", "")
            if _NODEID_RE.match(nodeid):
                nodeids.append(nodeid)
            else:
                unparsed.append(nodeid)
    return nodeids, unparsed


def compare(baseline_failures: set[str], current_failures: set[str]) -> dict:
    return {
        "stable_failures": sorted(baseline_failures & current_failures),
        "new_regressions": sorted(current_failures - baseline_failures),
        "recoveries": sorted(baseline_failures - current_failures),
    }


def format_human(baseline: dict, result: dict, unparsed: list[str], runtime_note: str = "") -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("FAILURE TOPOLOGY COMPARISON")
    lines.append("=" * 60)
    lines.append(f"baseline commit:  {baseline.get('captured_at_commit', '?')}")
    lines.append(f"baseline date:    {baseline.get('captured_at_date', '?')}")
    lines.append(f"baseline runtime: Python {baseline.get('python_version', '?')} / pytest {baseline.get('pytest_version', '?')}")
    if runtime_note:
        lines.append(f"runtime note:     {runtime_note}")
    lines.append("")

    stable = result["stable_failures"]
    regressions = result["new_regressions"]
    recoveries = result["recoveries"]

    lines.append(f"stable failures:   {len(stable)}  (pre-existing, expected)")
    lines.append(f"new regressions:   {len(regressions)}  {'<-- INVESTIGATE' if regressions else ''}")
    lines.append(f"recoveries:        {len(recoveries)}  {'<-- IMPROVEMENT' if recoveries else ''}")
    if unparsed:
        lines.append(f"unparsed lines:    {len(unparsed)}")
    lines.append("")

    if regressions:
        lines.append("NEW REGRESSIONS (not in baseline):")
        for n in regressions:
            lines.append(f"  {n}")
        lines.append("")

    if recoveries:
        lines.append("RECOVERIES (in baseline, now passing):")
        for n in recoveries:
            lines.append(f"  {n}")
        lines.append("")

    if unparsed:
        lines.append("UNPARSED LINES:")
        for u in unparsed[:10]:
            lines.append(f"  {u}")
        if len(unparsed) > 10:
            lines.append(f"  ... and {len(unparsed) - 10} more")
        lines.append("")

    lines.append("-" * 60)
    lines.append("DIAGNOSTIC ONLY — baseline does not make failures acceptable.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare current pytest failures against frozen baseline topology")
    parser.add_argument("--baseline", default=str(_DEFAULT_BASELINE), help="Path to baseline JSON (default: artifacts/test-baseline/failure-topology-v0.1.json)")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--current", help="Text file: one node ID per line, or 'FAILED tests/...' lines from pytest -v")
    source.add_argument("--current-json", help="pytest-json-report JSON output file")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--baseline-info", action="store_true", help="Print baseline metadata and exit")
    parser.add_argument("--runtime-note", default="", help="Note about current runtime (e.g. 'Python 3.12 — runtime-changed comparison')")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"ERROR: baseline not found: {baseline_path}", file=sys.stderr)
        return 2

    baseline = _load_baseline(baseline_path)

    if args.baseline_info:
        print(json.dumps({k: v for k, v in baseline.items() if not k.startswith("stable_failures")}, indent=2, ensure_ascii=False))
        print(f"stable_failures count: {len(baseline.get('stable_failures', []))}")
        return 0

    if not args.current and not args.current_json:
        parser.error("one of --current or --current-json is required (unless --baseline-info)")

    if args.current:
        current_nodeids, unparsed = _parse_nodeid_file(Path(args.current))
    else:
        current_nodeids, unparsed = _parse_pytest_json_report(Path(args.current_json))

    baseline_set = set(baseline.get("stable_failures", []))
    current_set = set(current_nodeids)
    result = compare(baseline_set, current_set)

    if args.format == "json":
        output = {
            "baseline_commit": baseline.get("captured_at_commit"),
            "baseline_runtime": f"Python {baseline.get('python_version')} / pytest {baseline.get('pytest_version')}",
            **result,
            "unparsed": unparsed,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(format_human(baseline, result, unparsed, args.runtime_note))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
