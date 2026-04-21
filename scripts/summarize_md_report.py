#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize contract-driven markdown rerun report.")
    parser.add_argument("--report", required=True, help="Path to rerun report JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report).resolve()
    with report_path.open("r", encoding="utf-8") as fh:
        report = json.load(fh)

    print(f"contract_id: {report.get('contract_id')}")
    print(f"generated_at_utc: {report.get('generated_at_utc')}")
    print(f"contract_path: {report.get('contract_path')}")
    print(f"runner_sha256: {report.get('tooling', {}).get('runner_sha256')}")
    print()

    repos = report.get("repos", [])
    for repo in repos:
        aggregate = repo.get("aggregate", {})
        print(repo.get("repo"))
        print(f"  targets_scanned: {repo.get('targets_scanned')}")
        print(f"  missing_targets: {len(repo.get('missing_targets', []))}")
        print(f"  any_clean_fail: {aggregate.get('any_clean_fail')}")
        print(f"  any_noise_fail: {aggregate.get('any_noise_fail')}")
        print(f"  closure_gate: {aggregate.get('closure_gate')}")
        print(f"  scope_filter_compliance: {aggregate.get('scope_filter_compliance')}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
