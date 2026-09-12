"""Slice 2 identity checks; Slice 1 acquisition and severity remain separate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.review_evidence import assess_review_evidence
from governance_tools.review_head_identity import assess_review_head, compare_review_heads


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/review_evidence"
PR80_SHA = "c3eab1c7aafbc56a6fb904dc653733afbfdd0024"
PR80_REVIEW_ID = 5181702419


def load_case(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def pr(snapshot):
    return snapshot["data"]["repository"]["pullRequest"]


def test_pr81_historical_full_sha_pair_fails_identity():
    recorded = load_case("pr81_incomplete.json")["provenance"]
    result = compare_review_heads(recorded["current_head"], recorded["reviewed_sha"])
    assert result["CURRENT_PR_HEAD"] == "64027f90ef7c1b4255e9b74503e0d97869bcf348"
    assert result["REVIEWED_HEAD"] == "233430f1b71de34db6fde45916dec41eb150d278"
    assert result["MATCH"] == "NO"
    assert result["MERGE_READY"] == "NO"
    assert not result["errors"]  # Valid inputs, genuinely different identities.


def test_pr80_real_snapshot_passes_identity_without_merge_approval():
    snapshot = load_case("pr80_complete.json")
    result = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert result["CURRENT_PR_HEAD"] == result["REVIEWED_HEAD"] == PR80_SHA
    assert result["MATCH"] == "YES"
    assert result["MERGE_READY"] == "NOT_EVALUATED"
    assert result["REVIEW_EVIDENCE"] == assess_review_evidence(snapshot)
    assert result["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert result["REVIEW_EVIDENCE"]["FINDINGS"] == "UNKNOWN"
    assert not result["errors"]


def test_full_sha_comparison_normalizes_hex_case_only():
    assert compare_review_heads(PR80_SHA.upper(), PR80_SHA)["MATCH"] == "YES"
    assert compare_review_heads(PR80_SHA, PR80_SHA[:-1] + "5")["MATCH"] == "NO"


@pytest.mark.parametrize("value", [None, "", False, True, 123, [], {},
                                   "c3eab1c", "c3eab1c7aa", "g" * 40,
                                   "0" * 40, "a" * 39, "a" * 41, "a" * 64,
                                   PR80_SHA + "\n", " " + PR80_SHA])
def test_invalid_or_abbreviated_identity_never_matches(value):
    for pair in [(value, PR80_SHA), (PR80_SHA, value), (value, value)]:
        result = compare_review_heads(*pair)
        assert result["MATCH"] == "UNKNOWN"
        assert result["MERGE_READY"] == "NO"
        assert result["errors"]


def test_complete_snapshot_with_new_head_cannot_reuse_previous_match():
    snapshot = load_case("pr80_complete.json")
    before = assess_review_head(snapshot, PR80_REVIEW_ID)
    recorded = load_case("pr81_incomplete.json")["provenance"]
    pr(snapshot)["headRefOid"] = recorded["current_head"]
    # Deliberately synthetic new-HEAD scenario, not PR80's historical state.
    after = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert before["MATCH"] == "YES"
    assert after["MATCH"] == "NO"
    assert after["MERGE_READY"] == "NO"
    assert after["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "COMPLETE"


def test_incomplete_acquisition_is_not_overridden_by_matching_sha_or_borrowed_complete():
    snapshot = load_case("pr80_complete.json")
    prior_evidence = assess_review_evidence(snapshot)
    del pr(snapshot)["reviewThreads"]
    snapshot["REVIEW_EVIDENCE"] = prior_evidence  # Must not be trusted as input.
    result = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert result["MATCH"] == "YES"  # Independent identity observation remains true.
    assert result["MERGE_READY"] == "NO"
    assert result["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "INSUFFICIENT"
    assert result["REVIEW_EVIDENCE"]["FINDINGS"] == "UNKNOWN"


def test_pr81_incomplete_output_is_not_fabricated_into_a_complete_snapshot():
    result = assess_review_head(load_case("pr81_incomplete.json"), 5185092363)
    assert result["MATCH"] == "UNKNOWN"
    assert result["MERGE_READY"] == "NO"
    assert result["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "INSUFFICIENT"


@pytest.mark.parametrize("review_id", [None, False, True, -1, 0, "5181702419", 123])
def test_review_id_must_select_one_explicit_review(review_id):
    result = assess_review_head(load_case("pr80_complete.json"), review_id)
    assert result["MATCH"] == "UNKNOWN"
    assert result["MERGE_READY"] == "NO"


def test_review_selection_does_not_change_with_order_or_choose_latest_implicitly():
    snapshot = load_case("pr80_complete.json")
    reviews = pr(snapshot)["reviews"]
    other = copy.deepcopy(reviews["nodes"][0])
    other["databaseId"] = 9000000000
    other["commit"]["oid"] = "1" * 40
    other["submittedAt"] = "2026-09-12T01:00:00Z"
    reviews["nodes"].append(other)
    reviews["totalCount"] = 2
    for _ in range(2):
        assert assess_review_head(snapshot, PR80_REVIEW_ID)["MATCH"] == "YES"
        result = assess_review_head(snapshot, 9000000000)
        assert result["MATCH"] == "NO"
        assert result["MERGE_READY"] == "NO"
        reviews["nodes"].reverse()


def test_duplicate_selected_id_and_partial_api_error_cannot_qualify():
    snapshot = load_case("pr80_complete.json")
    reviews = pr(snapshot)["reviews"]
    reviews["nodes"] *= 2
    reviews["totalCount"] = 2
    result = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert result["MATCH"] == "UNKNOWN"
    assert result["MERGE_READY"] == "NO"
    snapshot = load_case("pr80_complete.json")
    snapshot["errors"] = [{"message": "partial acquisition"}]
    result = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert result["MATCH"] == "YES"
    assert result["MERGE_READY"] == "NO"


def test_findings_content_does_not_drive_identity_and_input_stays_unmodified():
    snapshot = load_case("pr80_complete.json")
    # A synthetic P1 body must not become a hidden Slice 3 severity parser.
    pr(snapshot)["reviewThreads"]["nodes"][0]["comments"]["nodes"][0]["body"] = "P1: unresolved"
    before = copy.deepcopy(snapshot)
    result = assess_review_head(snapshot, PR80_REVIEW_ID)
    assert result["MATCH"] == "YES"
    assert result["MERGE_READY"] == "NOT_EVALUATED"
    assert snapshot == before


def run_cli(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "governance_tools.review_head_identity", *args],
                          cwd=ROOT, input=stdin, text=True, encoding="utf-8",
                          capture_output=True, check=False)


def test_cli_pr81_mismatch_and_pr80_positive():
    recorded = load_case("pr81_incomplete.json")["provenance"]
    mismatch = run_cli("--current-head", recorded["current_head"],
                       "--reviewed-head", recorded["reviewed_sha"])
    assert mismatch.returncode == 2
    assert json.loads(mismatch.stdout)["MATCH"] == "NO"
    positive = run_cli("--input", str(FIXTURES / "pr80_complete.json"),
                       "--review-id", str(PR80_REVIEW_ID))
    assert positive.returncode == 0
    assert json.loads(positive.stdout)["MERGE_READY"] == "NOT_EVALUATED"


@pytest.mark.parametrize("raw", ["not JSON", "null", "{}", '{"data":null}'])
def test_cli_unavailable_input_is_unknown_and_nonzero(raw):
    result = run_cli("--input", "-", "--review-id", str(PR80_REVIEW_ID), stdin=raw)
    assert result.returncode == 2
    assert json.loads(result.stdout)["MATCH"] == "UNKNOWN"
    assert json.loads(result.stdout)["MERGE_READY"] == "NO"


def test_cli_same_head_with_missing_inline_evidence_returns_nonzero():
    snapshot = load_case("pr80_complete.json")
    del pr(snapshot)["reviewThreads"]
    result = run_cli("--input", "-", "--review-id", str(PR80_REVIEW_ID), stdin=json.dumps(snapshot))
    assert result.returncode == 2
    assert json.loads(result.stdout)["MATCH"] == "YES"
    assert json.loads(result.stdout)["MERGE_READY"] == "NO"
