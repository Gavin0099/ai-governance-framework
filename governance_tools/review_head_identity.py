"""Slice 2: compare supplied PR/review commit identities, without merge approval.

The snapshot entrypoint calls Slice 1 on that same input and selects an explicit
review database ID. It does not parse findings, choose a reviewer, query GitHub,
validate CI commits, or wire any delivery/merge hook. Snapshot HEAD is an
observation, not proof that GitHub HEAD is still current at a later operation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from governance_tools.review_evidence import assess_review_evidence


def _full_sha(value: Any) -> str | None:
    if (isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value)
            and value != "0" * 40):
        return value.lower()
    return None


def compare_review_heads(current_head: Any, reviewed_head: Any) -> dict[str, Any]:
    """Compare full SHA-1 identities; prefixes and missing values are unknown."""
    current = _full_sha(current_head)
    reviewed = _full_sha(reviewed_head)
    errors = []
    if current is None:
        errors.append("CURRENT_PR_HEAD: requires a nonzero full 40-character hexadecimal SHA")
    if reviewed is None:
        errors.append("REVIEWED_HEAD: requires a nonzero full 40-character hexadecimal SHA")
    match = "UNKNOWN" if errors else ("YES" if current == reviewed else "NO")
    return {
        "CURRENT_PR_HEAD": current,
        "REVIEWED_HEAD": reviewed,
        "MATCH": match,
        "MERGE_READY": "NOT_EVALUATED" if match == "YES" else "NO",
        "errors": errors,
        "claim_ceiling": (
            "Equality of supplied commit identities only. A match is not merge "
            "approval. Acquisition authenticity/freshness, reviewer qualification, "
            "finding disposition, and required test commits are not evaluated."
        ),
    }


def assess_review_head(snapshot: Any, review_id: Any) -> dict[str, Any]:
    """Use Slice 1 as an independent prerequisite from this same snapshot.

    No external COMPLETE flag is accepted. Selecting a review is caller-owned;
    never infer 'latest', ignore old reviews by ordering, or parse review prose.
    An independently known mismatch remains visible if acquisition is incomplete.
    """
    evidence = assess_review_evidence(snapshot)
    data = snapshot.get("data") if isinstance(snapshot, dict) else None
    repo = data.get("repository") if isinstance(data, dict) else None
    pr = repo.get("pullRequest") if isinstance(repo, dict) else None
    current = pr.get("headRefOid") if isinstance(pr, dict) else None
    reviews = pr.get("reviews") if isinstance(pr, dict) else None
    nodes = reviews.get("nodes") if isinstance(reviews, dict) else None
    selected = []
    if type(review_id) is int and review_id > 0 and isinstance(nodes, list):
        selected = [node for node in nodes if isinstance(node, dict)
                    and type(node.get("databaseId")) is int
                    and node["databaseId"] == review_id]
    review = selected[0] if len(selected) == 1 else None
    commit = review.get("commit") if isinstance(review, dict) else None
    reviewed = commit.get("oid") if isinstance(commit, dict) else None
    result = compare_review_heads(current, reviewed)
    result["REVIEW_ID"] = review_id if type(review_id) is int and review_id > 0 else None
    result["REVIEW_EVIDENCE"] = evidence
    if review is None:
        result["errors"].append("review_id: requires exactly one matching review database ID")
    if evidence["REVIEW_COMPLETENESS"] != "COMPLETE":
        result["MERGE_READY"] = "NO"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", help="Raw GraphQL JSON file, or - for stdin")
    mode.add_argument("--current-head", help="Full SHA for identity-only comparison")
    parser.add_argument("--reviewed-head", help="Full SHA, used with --current-head")
    parser.add_argument("--review-id", type=int, help="Explicit review database ID, used with --input")
    args = parser.parse_args(argv)
    if args.input is not None:
        if args.review_id is None or args.reviewed_head is not None:
            parser.error("--input requires --review-id and excludes --reviewed-head")
        try:
            raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
            result = assess_review_head(json.loads(raw), args.review_id)
        except (OSError, UnicodeError, ValueError) as exc:
            result = assess_review_head(None, args.review_id)
            result["errors"].append(f"input: {type(exc).__name__}")
    else:
        if args.reviewed_head is None or args.review_id is not None:
            parser.error("--current-head requires --reviewed-head and excludes --review-id")
        result = compare_review_heads(args.current_head, args.reviewed_head)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    # Success qualifies only this identity check and, if supplied, acquisition.
    evidence = result.get("REVIEW_EVIDENCE")
    complete = evidence is None or evidence["REVIEW_COMPLETENESS"] == "COMPLETE"
    return 0 if result["MATCH"] == "YES" and complete and not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
