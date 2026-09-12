"""Guard finding-count claims against incomplete GitHub review acquisition.

Slice 1 only: checks the supplied, caller-visible GraphQL snapshot, not GitHub
truth, current-HEAD identity, finding severity, or permission to merge. A count
is an explicit caller assessment bound to these exact input contents; this
module neither infers nor verifies that semantic judgment. No hooks are wired.

Run ``python -m governance_tools.review_evidence --print-query`` to obtain the
read-only acquisition query, then pass its raw JSON response via --input.
Connections over 100 items fail closed; this bounded tool does not paginate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ACQUISITION_QUERY = """query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      url headRefOid
      reviews(first:100) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { databaseId state body submittedAt commit { oid } url }
      }
      comments(first:100) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { databaseId body url }
      }
      reviewThreads(first:100) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes {
          id
          comments(first:100) {
            totalCount pageInfo { hasNextPage endCursor }
            nodes { databaseId body url pullRequestReview { databaseId } }
          }
        }
      }
    }
  }
}"""


def snapshot_sha256(snapshot: Any) -> str:
    """Fingerprint parsed JSON, preserving array order and all input fields."""
    encoded = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _connection(value: Any, path: str, errors: list[str],
                id_key: str = "databaseId") -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        errors.append(f"{path}: connection not retrieved")
        return []
    nodes = value.get("nodes")
    count = value.get("totalCount")
    page = value.get("pageInfo")
    if not isinstance(nodes, list):
        errors.append(f"{path}: nodes missing or invalid")
        return []
    if type(count) is not int or count < 0 or count != len(nodes):
        errors.append(f"{path}: totalCount missing or does not match retrieved nodes")
    if not isinstance(page, dict) or page.get("hasNextPage") is not False:
        errors.append(f"{path}: terminal pagination not established")
    valid = []
    seen: set[Any] = set()
    for node in nodes:
        if not isinstance(node, dict):
            errors.append(f"{path}: null or invalid node")
            continue
        identity = node.get(id_key)
        valid_id = (_text(identity) if id_key == "id" else
                    type(identity) is int and identity > 0)
        if not valid_id:
            errors.append(f"{path}: missing or invalid {id_key}")
        elif identity in seen:
            errors.append(f"{path}: duplicate {id_key}")
        else:
            seen.add(identity)
        valid.append(node)
    return valid


def _bodies(nodes: list[dict[str, Any]], path: str, errors: list[str]) -> None:
    for node in nodes:
        # Empty bodies are valid retrieved data; absent/null bodies are not.
        if not isinstance(node.get("body"), str) or not _text(node.get("url")):
            errors.append(f"{path}: body or source URL not retrieved")


def assess_review_evidence(snapshot: Any, assessment: Any = None) -> dict[str, Any]:
    """Return UNKNOWN on acquisition failure, even when the caller supplies 0.

    An optional assessment has snapshot_sha256, source, and findings (a
    nonnegative integer). Complete acquisition alone never creates a count.
    COMPLETE is limited to submitted reviews, issue comments, and inline thread
    comments visible in this snapshot, not future events or invisible drafts.
    """
    errors: list[str] = []
    result: dict[str, Any] = {
        "REVIEW_COMPLETENESS": "INSUFFICIENT",
        "FINDINGS": "UNKNOWN",
        "MERGE_READY": "NO",
        "SNAPSHOT_SHA256": None,
        "ASSESSMENT_SOURCE": None,
        "errors": errors,
        "claim_ceiling": (
            "Supplied snapshot completeness only. A reported count is the named "
            "caller's content assessment, not an independently verified finding "
            "count. HEAD identity, severity, and merge readiness are not assessed."
        ),
    }
    try:
        result["SNAPSHOT_SHA256"] = snapshot_sha256(snapshot)
    except (TypeError, ValueError):
        errors.append("snapshot: not valid JSON data")
        return result
    if not isinstance(snapshot, dict):
        errors.append("snapshot: expected raw GraphQL response object")
        return result
    if "errors" in snapshot and snapshot["errors"] != []:
        errors.append("snapshot: GraphQL errors or ambiguous error state")
    data = snapshot.get("data")
    repo = data.get("repository") if isinstance(data, dict) else None
    pr = repo.get("pullRequest") if isinstance(repo, dict) else None
    if not isinstance(pr, dict):
        errors.append("snapshot: pull request data not retrieved")
        return result
    if not _text(pr.get("url")) or not _text(pr.get("headRefOid")):
        errors.append("snapshot: pull request identity not retrieved")

    reviews = _connection(pr.get("reviews"), "reviews", errors)
    _bodies(reviews, "reviews", errors)
    if not reviews:
        errors.append("reviews: no submitted review evidence")
    review_ids = set()
    for review in reviews:
        identity = review.get("databaseId")
        if type(identity) is int and identity > 0:
            review_ids.add(identity)
        if (review.get("state") not in
                ("APPROVED", "COMMENTED", "CHANGES_REQUESTED", "DISMISSED")
                or not _text(review.get("submittedAt"))):
            errors.append("reviews: unsubmitted or unknown review state")
        commit = review.get("commit")
        if not isinstance(commit, dict) or not _text(commit.get("oid")):
            errors.append("reviews: reviewed commit not retrieved")

    comments = _connection(pr.get("comments"), "comments", errors)
    _bodies(comments, "comments", errors)
    threads = _connection(pr.get("reviewThreads"), "reviewThreads", errors, "id")
    inline_ids: set[int] = set()
    for index, thread in enumerate(threads):
        path = f"reviewThreads[{index}].comments"
        inline = _connection(thread.get("comments"), path, errors)
        _bodies(inline, path, errors)
        if not inline:
            errors.append(f"{path}: thread without retrieved comments")
        for comment in inline:
            identity = comment.get("databaseId")
            if type(identity) is int and identity > 0:
                if identity in inline_ids:
                    errors.append(f"{path}: inline comment repeated across threads")
                inline_ids.add(identity)
            parent = comment.get("pullRequestReview")
            parent_id = parent.get("databaseId") if isinstance(parent, dict) else None
            if type(parent_id) is not int or parent_id not in review_ids:
                errors.append(f"{path}: parent review not retrieved")
    if errors:
        return result

    result["REVIEW_COMPLETENESS"] = "COMPLETE"
    result["MERGE_READY"] = "NOT_EVALUATED"
    if assessment is not None:
        if (not isinstance(assessment, dict)
                or assessment.get("snapshot_sha256") != result["SNAPSHOT_SHA256"]
                or not _text(assessment.get("source"))
                or type(assessment.get("findings")) is not int
                or assessment["findings"] < 0):
            errors.append("assessment: requires matching snapshot_sha256, source, and nonnegative integer findings")
        else:
            result["FINDINGS"] = assessment["findings"]
            result["ASSESSMENT_SOURCE"] = assessment["source"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="Raw GraphQL JSON file, or - for stdin")
    parser.add_argument("--assessment", help="Optional explicit assessment JSON file")
    parser.add_argument("--print-query", action="store_true", help="Print read-only GraphQL query and exit")
    args = parser.parse_args(argv)
    if args.print_query:
        print(ACQUISITION_QUERY)
        return 0
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
        snapshot = json.loads(raw)
        assessment = (json.loads(Path(args.assessment).read_text(encoding="utf-8-sig"))
                      if args.assessment else None)
        result = assess_review_evidence(snapshot, assessment)
    except (OSError, UnicodeError, ValueError) as exc:
        result = assess_review_evidence(None)
        result["errors"] = [f"input: {type(exc).__name__}"]
    print(json.dumps(result, ensure_ascii=True, indent=2))
    # 0 means this acquisition/assessment-input check passed, never merge-ready.
    return 0 if result["REVIEW_COMPLETENESS"] == "COMPLETE" and not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
