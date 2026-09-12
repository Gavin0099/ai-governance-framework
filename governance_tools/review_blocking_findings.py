"""Slice 3: gate explicit P0/P1 dispositions after acquisition and HEAD checks.

Every acquired body requires a snapshot-bound caller classification. Coverage,
binding, and the blocking predicate are mechanical; classification, severity,
and claimed resolution remain the named caller's judgment, not verified truth.
No text/badge parser, GitHub mutation, CI qualification, or merge hook is added.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from governance_tools.review_head_identity import assess_review_head


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_keys(snapshot: dict[str, Any]) -> set[str]:
    """Called only after Slice 1 established complete connection structure."""
    pr = snapshot["data"]["repository"]["pullRequest"]
    keys = {f"review:{node['databaseId']}" for node in pr["reviews"]["nodes"]}
    keys.update(f"issue_comment:{node['databaseId']}" for node in pr["comments"]["nodes"])
    for thread in pr["reviewThreads"]["nodes"]:
        keys.update(f"inline_comment:{node['databaseId']}" for node in thread["comments"]["nodes"])
    return keys


def assess_blocking_findings(snapshot: Any, review_id: Any,
                             assessment: Any = None) -> dict[str, Any]:
    """Evaluate the caller's exhaustive disposition ledger; never approve merge.

    Ledger: snapshot_sha256, review_id, source, sources. Each source has key,
    classification (NON_FINDING/FINDINGS) and, for FINDINGS, a nonempty findings
    list. Each finding has id, severity (P0..P3), and disposition
    (UNRESOLVED/RESOLVED/UNKNOWN). RESOLVED P0/P1 also requires an explicit
    resolution_evidence reference. Merely resolving a GitHub thread is not used.

    Coverage includes ALL acquired bodies, including earlier reviews and issue
    comments; selecting a matching review does not discard older open findings.
    P2/P3 do not block, including when their disposition is explicitly UNKNOWN.
    """
    identity = assess_review_head(snapshot, review_id)
    evidence = identity["REVIEW_EVIDENCE"]
    errors: list[str] = []
    result: dict[str, Any] = {
        "BLOCKING_GATE": "UNKNOWN",
        "UNRESOLVED_P0": "UNKNOWN",
        "UNRESOLVED_P1": "UNKNOWN",
        "BLOCKING_FINDING_IDS": None,
        "MERGE_READY": "NO",
        "ASSESSMENT_SOURCE": None,
        "REVIEW_IDENTITY": identity,
        "errors": errors,
        "claim_ceiling": (
            "P0/P1 predicate over the named caller's snapshot-bound, exhaustive "
            "assessment only. Coverage does not prove NON_FINDING classification, "
            "severity, resolution, or defect absence. PASS is not merge approval."
        ),
    }
    if evidence["REVIEW_COMPLETENESS"] != "COMPLETE" or identity["MATCH"] != "YES":
        errors.append("prerequisites: complete acquisition and matching HEAD required")
        return result
    if (not isinstance(assessment, dict)
            or assessment.get("snapshot_sha256") != evidence["SNAPSHOT_SHA256"]
            or type(assessment.get("review_id")) is not int
            or assessment["review_id"] != review_id
            or not _text(assessment.get("source"))
            or not isinstance(assessment.get("sources"), list)):
        errors.append("assessment: matching snapshot_sha256, review_id, source, and sources required")
        return result

    expected = _source_keys(snapshot)
    seen: set[str] = set()
    finding_ids: set[str] = set()
    blockers: list[str] = []
    counts = {"P0": 0, "P1": 0}
    unknown_blocking = False
    for item in assessment["sources"]:
        if not isinstance(item, dict) or not _text(item.get("key")):
            errors.append("sources: invalid source entry")
            continue
        key = item["key"]
        if key not in expected or key in seen:
            errors.append("sources: unknown or duplicate source key")
            continue
        seen.add(key)
        classification = item.get("classification")
        findings = item.get("findings")
        if classification == "NON_FINDING":
            if "findings" in item and findings != []:
                errors.append(f"{key}: NON_FINDING cannot include finding data")
            continue
        if classification != "FINDINGS" or not isinstance(findings, list) or not findings:
            errors.append(f"{key}: explicit NON_FINDING or nonempty FINDINGS required")
            continue
        for finding in findings:
            if not isinstance(finding, dict) or not _text(finding.get("id")):
                errors.append(f"{key}: finding id required")
                continue
            fid = finding["id"]
            if fid in finding_ids:
                errors.append(f"{key}: duplicate finding id")
                continue
            finding_ids.add(fid)
            severity = finding.get("severity")
            disposition = finding.get("disposition")
            if severity not in ("P0", "P1", "P2", "P3"):
                errors.append(f"{key}: explicit P0/P1/P2/P3 severity required")
                continue
            if disposition not in ("UNRESOLVED", "RESOLVED", "UNKNOWN"):
                errors.append(f"{key}: explicit disposition required")
                continue
            if severity in ("P0", "P1"):
                if disposition == "UNRESOLVED":
                    counts[severity] += 1
                    blockers.append(fid)
                elif disposition == "UNKNOWN":
                    unknown_blocking = True
                elif not _text(finding.get("resolution_evidence")):
                    errors.append(f"{key}: resolved P0/P1 needs explicit resolution evidence reference")
    if seen != expected:
        errors.append("sources: every acquired body must be classified exactly once")
    if unknown_blocking:
        errors.append("findings: P0/P1 disposition is unknown")
    if errors:
        return result

    result["ASSESSMENT_SOURCE"] = assessment["source"]
    result["UNRESOLVED_P0"] = counts["P0"]
    result["UNRESOLVED_P1"] = counts["P1"]
    result["BLOCKING_FINDING_IDS"] = blockers
    result["BLOCKING_GATE"] = "BLOCKED" if blockers else "PASS"
    result["MERGE_READY"] = "NO" if blockers else "NOT_EVALUATED"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw GraphQL JSON file, or - for stdin")
    parser.add_argument("--review-id", required=True, type=int, help="Explicit review database ID")
    parser.add_argument("--assessment", help="Explicit disposition ledger JSON file; absent means UNKNOWN")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
        snapshot = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        result = assess_blocking_findings(None, args.review_id)
        result["errors"].append(f"input: {type(exc).__name__}")
    else:
        # Do not let an unreadable ledger obscure a failed acquisition/HEAD check.
        result = assess_blocking_findings(snapshot, args.review_id)
        identity = result["REVIEW_IDENTITY"]
        if (identity["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "COMPLETE"
                and identity["MATCH"] == "YES" and args.assessment):
            try:
                assessment = json.loads(Path(args.assessment).read_text(encoding="utf-8-sig"))
                result = assess_blocking_findings(snapshot, args.review_id, assessment)
            except (OSError, UnicodeError, ValueError) as exc:
                result["errors"].append(f"assessment: {type(exc).__name__}")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["BLOCKING_GATE"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
