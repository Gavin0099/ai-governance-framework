#!/usr/bin/env python3
"""Join the immutable report receipt to the operator's final container snapshot."""
from __future__ import annotations

import argparse
import json

from evidence_io import atomic_write_json


def load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def verify(adapter_rows: list[dict], snapshot: dict) -> dict:
    reports = [
        row for row in adapter_rows
        if row.get("verb") == "report" and row.get("decision") == "executed"
    ]
    successful = [
        row for row in reports
        if row.get("exit") == 0
        and isinstance(row.get("result_receipt"), dict)
        and row["result_receipt"].get("written") is True
        and row["result_receipt"].get("content_matches_request") is True
    ]
    artifact = (snapshot.get("work_out_artifacts") or {}).get("result.json")
    checks = {
        "exactly_one_successful_immutable_report": len(successful) == 1,
        "snapshot_contains_result_json": isinstance(artifact, dict),
        "receipt_digest_matches_final_artifact": False,
        "receipt_bytes_match_final_artifact": False,
        "result_json_is_parseable": (
            isinstance(artifact, dict)
            and isinstance(artifact.get("parsed_json"), dict)
        ),
    }
    receipt = successful[0]["result_receipt"] if len(successful) == 1 else None
    if receipt and isinstance(artifact, dict):
        checks["receipt_digest_matches_final_artifact"] = (
            receipt.get("sha256") == artifact.get("sha256")
        )
        checks["receipt_bytes_match_final_artifact"] = (
            receipt.get("bytes") == artifact.get("bytes")
        )
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "report_attempts": len(reports),
        "successful_reports": len(successful),
        "receipt": receipt,
        "final_artifact": artifact,
        "claim_boundary": (
            "This proves the final result artifact equals the one successful "
            "report payload. It does not prove the payload's claims are true."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-log", required=True)
    parser.add_argument("--after-snapshot", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    with open(args.after_snapshot, encoding="utf-8") as handle:
        snapshot = json.load(handle)
    result = verify(load_jsonl(args.adapter_log), snapshot)
    atomic_write_json(args.json_out, result)
    for name, passed in result["checks"].items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"---\n{result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
