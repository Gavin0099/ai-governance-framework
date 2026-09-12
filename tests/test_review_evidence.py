"""Slice 1 acceptance: historical omission must not become a zero-count claim."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.review_evidence import assess_review_evidence, snapshot_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/review_evidence"


def load_case(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def judgment(snapshot, count):
    return {
        "snapshot_sha256": snapshot_sha256(snapshot),
        "source": "test reviewer: explicit content assessment of this snapshot",
        "findings": count,
    }


def pr(snapshot):
    return snapshot["data"]["repository"]["pullRequest"]


def assert_insufficient(result):
    assert result["REVIEW_COMPLETENESS"] == "INSUFFICIENT"
    assert result["FINDINGS"] == "UNKNOWN"
    assert result["MERGE_READY"] == "NO"
    assert result["ASSESSMENT_SOURCE"] is None
    assert result["errors"]


def test_pr81_actual_historical_output_cannot_preserve_false_zero():
    snapshot = load_case("pr81_incomplete.json")
    recorded = snapshot["provenance"]
    raw = recorded["stdout"]
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == recorded["stdout_sha256"]
    assert recorded["exit_code"] == 0
    assert "**Completed**" in raw and "status:\tcommented" in raw
    assert "👍" in raw and "Reviewed commit:" in raw
    assert recorded["reviewed_sha"].startswith("233430f")
    assert recorded["current_head"].startswith("64027f9")
    assert recorded["inline_findings"] == "NOT RETRIEVED"
    assert_insufficient(assess_review_evidence(snapshot, judgment(snapshot, 0)))


def test_pr80_real_complete_snapshot_preserves_explicit_one_finding():
    snapshot = load_case("pr80_complete.json")
    inline = pr(snapshot)["reviewThreads"]["nodes"][0]["comments"]["nodes"][0]
    # The independently inspected fixture has a real P2. No production regex
    # counts badges or guesses severity from the review's boilerplate text.
    assert inline["databaseId"] == 3991812364
    assert "Bind the closeout to the reviewed implementation commit" in inline["body"]
    result = assess_review_evidence(snapshot, judgment(snapshot, 1))
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == 1
    assert result["MERGE_READY"] == "NOT_EVALUATED"
    assert result["ASSESSMENT_SOURCE"]
    assert not result["errors"]


def test_complete_acquisition_does_not_infer_count_from_boilerplate():
    result = assess_review_evidence(load_case("pr80_complete.json"))
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == "UNKNOWN"
    assert result["MERGE_READY"] == "NOT_EVALUATED"
    assert not result["errors"]


@pytest.mark.parametrize("surface", ["reviews", "comments", "reviewThreads", "nested_comments"])
@pytest.mark.parametrize("failure", ["missing", "null", "unpaged", "more_pages", "short_page", "null_node", "duplicate", "missing_body"])
def test_incomplete_surfaces_always_override_a_claimed_zero(surface, failure):
    snapshot = load_case("pr80_complete.json")
    parent, key = pr(snapshot), surface
    if surface == "nested_comments":
        parent, key = parent["reviewThreads"]["nodes"][0], "comments"
    connection = parent[key]
    if failure == "missing":
        del parent[key]
    elif failure == "null":
        parent[key] = None
    elif failure == "unpaged":
        del connection["pageInfo"]
    elif failure == "more_pages":
        connection["pageInfo"]["hasNextPage"] = True
    elif failure == "short_page":
        connection["totalCount"] += 1
    elif failure == "null_node":
        connection["nodes"] = [None]
    elif failure == "duplicate":
        connection["nodes"] *= 2
        connection["totalCount"] = 2
    else:
        node = connection["nodes"][0]
        if surface == "reviewThreads":
            del node["comments"]["nodes"][0]["body"]
        else:
            del node["body"]
    assert_insufficient(assess_review_evidence(snapshot, judgment(snapshot, 0)))


@pytest.mark.parametrize("error_state", [[{"message": "permission denied"}], None, {}])
def test_graphql_partial_data_is_not_success(error_state):
    snapshot = load_case("pr80_complete.json")
    snapshot["errors"] = error_state
    assert_insufficient(assess_review_evidence(snapshot, judgment(snapshot, 0)))


@pytest.mark.parametrize("state", ["PENDING", "Completed", None])
def test_unsubmitted_or_unknown_review_is_insufficient(state):
    snapshot = load_case("pr80_complete.json")
    pr(snapshot)["reviews"]["nodes"][0]["state"] = state
    assert_insufficient(assess_review_evidence(snapshot, judgment(snapshot, 0)))


def empty_connection():
    return {"totalCount": 0, "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}


def test_no_review_is_not_a_zero_finding_review():
    snapshot = load_case("pr80_complete.json")
    pr(snapshot)["reviews"] = empty_connection()
    pr(snapshot)["reviewThreads"] = empty_connection()
    assert_insufficient(assess_review_evidence(snapshot, judgment(snapshot, 0)))


def test_successfully_empty_surfaces_allow_explicit_zero_but_do_not_create_it():
    # Synthetic boundary case, deliberately NOT represented as a historical PR.
    snapshot = load_case("pr80_complete.json")
    pr(snapshot)["comments"] = empty_connection()
    pr(snapshot)["reviewThreads"] = empty_connection()
    pr(snapshot)["reviews"]["nodes"][0]["body"] = "Reviewed: no findings."
    assert assess_review_evidence(snapshot)["FINDINGS"] == "UNKNOWN"
    result = assess_review_evidence(snapshot, judgment(snapshot, 0))
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == 0
    assert result["MERGE_READY"] == "NOT_EVALUATED"


@pytest.mark.parametrize("count", [-1, False, True, 0.0, "0", None])
def test_invalid_assessment_cannot_publish_a_count(count):
    snapshot = load_case("pr80_complete.json")
    result = assess_review_evidence(snapshot, judgment(snapshot, count))
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == "UNKNOWN"
    assert result["errors"]


@pytest.mark.parametrize("missing", ["source", "snapshot_sha256", "findings"])
def test_assessment_requires_explicit_provenance(missing):
    snapshot = load_case("pr80_complete.json")
    assessment = judgment(snapshot, 0)
    del assessment[missing]
    assert assess_review_evidence(snapshot, assessment)["FINDINGS"] == "UNKNOWN"


def test_changed_evidence_invalidates_an_earlier_content_assessment():
    snapshot = load_case("pr80_complete.json")
    assessment = judgment(snapshot, 0)
    pr(snapshot)["reviews"]["nodes"][0]["body"] += "\nAdditional finding."
    result = assess_review_evidence(snapshot, assessment)
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == "UNKNOWN"
    assert result["errors"]


def test_review_head_mismatch_is_deferred_not_silently_implemented():
    snapshot = load_case("pr80_complete.json")
    pr(snapshot)["headRefOid"] = "64027f90ef7c1b4255e9b74503e0d97869bcf348"
    result = assess_review_evidence(snapshot, judgment(snapshot, 1))
    assert result["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["FINDINGS"] == 1
    assert result["MERGE_READY"] == "NOT_EVALUATED"


def test_parent_review_must_be_retrieved_and_no_thread_may_be_empty():
    snapshot = load_case("pr80_complete.json")
    connection = pr(snapshot)["reviewThreads"]["nodes"][0]["comments"]
    connection["nodes"][0]["pullRequestReview"] = None
    assert_insufficient(assess_review_evidence(snapshot))
    pr(snapshot)["reviewThreads"]["nodes"][0]["comments"] = empty_connection()
    assert_insufficient(assess_review_evidence(snapshot))


def test_snapshot_digest_is_format_independent_and_input_is_not_mutated():
    snapshot = load_case("pr80_complete.json")
    original = copy.deepcopy(snapshot)
    reformatted = json.loads(json.dumps(snapshot, sort_keys=True, indent=4))
    assert snapshot_sha256(snapshot) == snapshot_sha256(reformatted)
    assess_review_evidence(snapshot, judgment(snapshot, 1))
    assert snapshot == original


@pytest.mark.parametrize("snapshot", [None, [], {}, {"data": None}, {"data": {"repository": None}}])
def test_missing_or_unavailable_data_is_unknown(snapshot):
    assert_insufficient(assess_review_evidence(snapshot))


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "governance_tools.review_evidence", *args],
        cwd=ROOT, input=stdin, text=True, encoding="utf-8", capture_output=True,
        check=False,
    )


def test_cli_historical_replay_fails_with_safe_machine_output(tmp_path):
    snapshot = load_case("pr81_incomplete.json")
    assessment = tmp_path / "assessment.json"
    assessment.write_text(json.dumps(judgment(snapshot, 0)), encoding="utf-8")
    result = run_cli("--input", str(FIXTURES / "pr81_incomplete.json"),
                     "--assessment", str(assessment))
    assert result.returncode == 2
    assert_insufficient(json.loads(result.stdout))
    assert not result.stderr


def test_cli_real_complete_pr_does_not_false_block(tmp_path):
    snapshot = load_case("pr80_complete.json")
    assessment = tmp_path / "assessment.json"
    assessment.write_text(json.dumps(judgment(snapshot, 1)), encoding="utf-8")
    result = run_cli("--input", str(FIXTURES / "pr80_complete.json"),
                     "--assessment", str(assessment))
    assert result.returncode == 0
    assert json.loads(result.stdout)["FINDINGS"] == 1


def test_cli_raw_historical_text_is_also_unknown():
    result = run_cli(stdin=load_case("pr81_incomplete.json")["provenance"]["stdout"])
    assert result.returncode == 2
    assert_insufficient(json.loads(result.stdout))


def test_cli_query_is_read_only_and_requests_nested_pagination():
    result = run_cli("--print-query")
    assert result.returncode == 0
    assert result.stdout.startswith("query(")
    assert "mutation" not in result.stdout
    assert result.stdout.count("totalCount pageInfo { hasNextPage endCursor }") == 4
