#!/usr/bin/env python3
"""
Drift Gate Policy — Phase Gate 2b 的 warning 分類

功能:
  讀取 governance_drift_checker.py --format json 的結果，判斷 warning 是否
  全部屬於「只因時間經過而成立」的提醒。只有這類提醒可以通過 Gate 2b，
  且仍會印出。critical、bookkeeping warning、無法判讀的輸入一律阻擋。

  可通過的提醒（其餘全部阻擋）:
    expansion_boundary       transitional_key_stale
    baseline_yaml_freshness  baseline.yaml is N days old

用法:
  python governance_tools/governance_drift_checker.py --format json \
    | python governance_tools/drift_gate_policy.py

退出碼:
  0 = 所有 findings 都是時間型提醒
  1 = 至少一項需阻擋，或輸入無法判讀
"""
import json
import sys


def is_time_based_advisory(finding) -> bool:
    if not isinstance(finding, dict) or finding.get("severity") != "warning":
        return False
    detail = finding.get("detail")
    if not isinstance(detail, str):
        return False
    check = finding.get("check")
    if check == "expansion_boundary":
        return detail.startswith("transitional_key_stale: ")
    if check == "baseline_yaml_freshness":
        # "cannot parse initialized_at" is corrupted bookkeeping, not age.
        return detail.startswith("baseline.yaml is ") and " days old (" in detail
    return False


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    try:
        findings = json.load(sys.stdin)["findings"]
        if not isinstance(findings, list):
            raise TypeError("findings is not a list")
    except (ValueError, KeyError, TypeError) as exc:
        print(f"  BLOCK unreadable drift result: {exc}")
        return 1
    if not findings:
        print("  BLOCK warning exit without findings")
        return 1
    blocking = 0
    for finding in findings:
        advisory = is_time_based_advisory(finding)
        blocking += not advisory
        label = "ADVISORY" if advisory else "BLOCK"
        if isinstance(finding, dict):
            print(f"  {label} {finding.get('check')}: {finding.get('detail')}")
        else:
            print(f"  {label} malformed finding: {finding!r}")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
