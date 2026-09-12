"""Slice 3 regression: classify all sources before allowing a P0/P1 predicate."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.review_blocking_findings import assess_blocking_findings
from governance_tools.review_evidence import snapshot_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/review_evidence"
REVIEW80 = 5181702419
REVIEW81 = 5185092363


def case(number):
    return tuple(json.loads((FIXTURES / f"pr{number}_{suffix}.json").read_text(encoding="utf-8"))
                 for suffix in ("complete", "assessment"))


def synthetic_exact_head_pr81():
    snapshot, assessment = case(81)
    pr = snapshot["data"]["repository"]["pullRequest"]
    pr["headRefOid"] = pr["reviews"]["nodes"][0]["commit"]["oid"]
    snapshot["test_scenario"] = "SYNTHETIC exact HEAD; not PR81's historical final state"
    assessment["source"] = "Synthetic exact-HEAD replay carrying manually assessed real PR81 findings"
    assessment["snapshot_sha256"] = snapshot_sha256(snapshot)
    return snapshot, assessment


def assert_unknown(result):
    assert result["BLOCKING_GATE"] == "UNKNOWN"
    assert result["UNRESOLVED_P0"] == "UNKNOWN"
    assert result["UNRESOLVED_P1"] == "UNKNOWN"
    assert result["BLOCKING_FINDING_IDS"] is None
    assert result["ASSESSMENT_SOURCE"] is None
    assert result["MERGE_READY"] == "NO"
    assert result["errors"]


def test_pr81_actual_final_state_stops_at_identity_not_a_qualified_count():
    snapshot, assessment = case(81)
    result = assess_blocking_findings(snapshot, REVIEW81, assessment)
    assert result["REVIEW_IDENTITY"]["MATCH"] == "NO"
    assert result["REVIEW_IDENTITY"]["REVIEW_EVIDENCE"]["REVIEW_COMPLETENESS"] == "COMPLETE"
    assert_unknown(result)


def test_pr81_original_incomplete_output_stops_before_disposition():
    snapshot = json.loads((FIXTURES / "pr81_incomplete.json").read_text(encoding="utf-8"))
    assert_unknown(assess_blocking_findings(snapshot, REVIEW81, {"sources": []}))


def test_real_pr81_p1_blocks_in_explicitly_synthetic_exact_head_case():
    snapshot, assessment = synthetic_exact_head_pr81()
    body = snapshot["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]["comments"]["nodes"][0]
    assert body["databaseId"] == 3994999882
    assert "Today Mode" in body["body"]
    result = assess_blocking_findings(snapshot, REVIEW81, assessment)
    assert result["BLOCKING_GATE"] == "BLOCKED"
    assert result["UNRESOLVED_P0"] == 0
    assert result["UNRESOLVED_P1"] == 1
    assert result["BLOCKING_FINDING_IDS"] == ["github-inline-3994999882"]
    assert result["MERGE_READY"] == "NO"
    assert result["ASSESSMENT_SOURCE"] == assessment["source"]


def test_pr80_real_p2_positive_control_does_not_false_block():
    snapshot, assessment = case(80)
    result = assess_blocking_findings(snapshot, REVIEW80, assessment)
    assert result["BLOCKING_GATE"] == "PASS"
    assert result["UNRESOLVED_P0"] == result["UNRESOLVED_P1"] == 0
    assert result["BLOCKING_FINDING_IDS"] == []
    assert result["MERGE_READY"] == "NOT_EVALUATED"
    assert result["REVIEW_IDENTITY"]["REVIEW_EVIDENCE"]["FINDINGS"] == "UNKNOWN"
    assert not result["errors"]


@pytest.mark.parametrize("fault", ["missing_inline", "missing_review", "missing_issue",
                                  "empty_sources", "duplicate", "extra", "nonfinding_with_data", "empty_findings"])
def test_exhaustive_source_coverage_cannot_omit_or_hide_an_entry(fault):
    snapshot, assessment = synthetic_exact_head_pr81()
    sources = assessment["sources"]
    if fault == "missing_inline":
        del sources[2]
    elif fault == "missing_review":
        del sources[0]
    elif fault == "missing_issue":
        del sources[1]
    elif fault == "empty_sources":
        sources.clear()
    elif fault == "duplicate":
        sources.append(copy.deepcopy(sources[2]))
    elif fault == "extra":
        sources.append({"key": "inline_comment:999", "classification": "NON_FINDING"})
    elif fault == "nonfinding_with_data":
        sources[2]["classification"] = "NON_FINDING"
    elif fault == "empty_findings":
        sources[2]["findings"] = []
    assert_unknown(assess_blocking_findings(snapshot, REVIEW81, assessment))


@pytest.mark.parametrize("field", ["snapshot_sha256", "review_id", "source", "sources"])
def test_assessment_must_be_explicit_and_bound(field):
    snapshot, assessment = case(80)
    del assessment[field]
    assert_unknown(assess_blocking_findings(snapshot, REVIEW80, assessment))


def test_no_assessment_and_wrong_review_binding_remain_unknown():
    snapshot, assessment = case(80)
    assert_unknown(assess_blocking_findings(snapshot, REVIEW80))
    for wrong_id in (REVIEW81, True, str(REVIEW80)):
        assessment["review_id"] = wrong_id
        assert_unknown(assess_blocking_findings(snapshot, REVIEW80, assessment))


def test_changed_body_cannot_reuse_earlier_zero_blocker_assessment():
    snapshot, assessment = case(80)
    pr = snapshot["data"]["repository"]["pullRequest"]
    pr["comments"]["nodes"][0]["body"] += "\nNew issue."
    assert_unknown(assess_blocking_findings(snapshot, REVIEW80, assessment))


@pytest.mark.parametrize("field,value", [("id", None), ("severity", None), ("severity", "UNKNOWN"),
                                       ("severity", True), ("severity", ["P1"]),
                                       ("disposition", None), ("disposition", "FIXED")])
def test_missing_or_invalid_finding_fields_never_clear_a_blocker(field, value):
    snapshot, assessment = synthetic_exact_head_pr81()
    assessment["sources"][2]["findings"][0][field] = value
    assert_unknown(assess_blocking_findings(snapshot, REVIEW81, assessment))


def test_unknown_p0_p1_disposition_remains_unknown():
    snapshot, assessment = synthetic_exact_head_pr81()
    for severity in ("P0", "P1"):
        finding = assessment["sources"][2]["findings"][0]
        finding.update(severity=severity, disposition="UNKNOWN")
        assert_unknown(assess_blocking_findings(snapshot, REVIEW81, assessment))


def test_p0_also_blocks_but_p2_unknown_disposition_does_not():
    snapshot, assessment = case(80)
    finding = assessment["sources"][2]["findings"][0]
    finding["severity"] = "P0"  # Explicit synthetic classification boundary.
    result = assess_blocking_findings(snapshot, REVIEW80, assessment)
    assert result["BLOCKING_GATE"] == "BLOCKED" and result["UNRESOLVED_P0"] == 1
    finding.update(severity="P2", disposition="UNKNOWN")
    result = assess_blocking_findings(snapshot, REVIEW80, assessment)
    assert result["BLOCKING_GATE"] == "PASS"
    assert result["MERGE_READY"] == "NOT_EVALUATED"


def test_resolved_thread_metadata_alone_cannot_clear_p1():
    snapshot, assessment = synthetic_exact_head_pr81()
    snapshot["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]["isResolved"] = True
    assessment["snapshot_sha256"] = snapshot_sha256(snapshot)
    assert assess_blocking_findings(snapshot, REVIEW81, assessment)["BLOCKING_GATE"] == "BLOCKED"
    finding = assessment["sources"][2]["findings"][0]
    finding["disposition"] = "RESOLVED"
    assert_unknown(assess_blocking_findings(snapshot, REVIEW81, assessment))
    finding["resolution_evidence"] = "synthetic verifier report: fixture-only resolution judgment"
    result = assess_blocking_findings(snapshot, REVIEW81, assessment)
    assert result["BLOCKING_GATE"] == "PASS"  # Caller judgment, not proof of real PR81 fix.
    assert result["MERGE_READY"] == "NOT_EVALUATED"


def test_duplicate_finding_ids_are_not_silently_deduplicated():
    snapshot, assessment = synthetic_exact_head_pr81()
    assessment["sources"][3]["findings"][0]["id"] = assessment["sources"][2]["findings"][0]["id"]
    assert_unknown(assess_blocking_findings(snapshot, REVIEW81, assessment))


def test_prior_review_sources_must_also_be_accounted_for():
    snapshot, assessment = case(80)
    reviews = snapshot["data"]["repository"]["pullRequest"]["reviews"]
    older = copy.deepcopy(reviews["nodes"][0])
    older["databaseId"] = 100
    older["commit"]["oid"] = "1" * 40
    reviews["nodes"].append(older)
    reviews["totalCount"] += 1
    assessment["snapshot_sha256"] = snapshot_sha256(snapshot)
    assert_unknown(assess_blocking_findings(snapshot, REVIEW80, assessment))
    assessment["sources"].append({"key": "review:100", "classification": "FINDINGS", "findings": [
        {"id": "old-p1", "severity": "P1", "disposition": "UNRESOLVED"}]})
    assert assess_blocking_findings(snapshot, REVIEW80, assessment)["BLOCKING_GATE"] == "BLOCKED"


def test_complete_matching_input_with_missing_inline_stays_unknown():
    snapshot, assessment = case(80)
    del snapshot["data"]["repository"]["pullRequest"]["reviewThreads"]
    assessment["snapshot_sha256"] = snapshot_sha256(snapshot)
    assert_unknown(assess_blocking_findings(snapshot, REVIEW80, assessment))


def test_inputs_are_not_mutated_and_classification_remains_caller_owned():
    snapshot, assessment = case(80)
    before = copy.deepcopy((snapshot, assessment))
    result = assess_blocking_findings(snapshot, REVIEW80, assessment)
    assert (snapshot, assessment) == before
    assert result["ASSESSMENT_SOURCE"] == assessment["source"]
    assert "does not prove NON_FINDING" in result["claim_ceiling"]


def run_cli(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "governance_tools.review_blocking_findings", *args],
                          cwd=ROOT, input=stdin, text=True, encoding="utf-8", capture_output=True, check=False)


def test_cli_real_positive_and_real_stale_head():
    positive = run_cli("--input", str(FIXTURES / "pr80_complete.json"), "--review-id", str(REVIEW80),
                       "--assessment", str(FIXTURES / "pr80_assessment.json"))
    assert positive.returncode == 0 and json.loads(positive.stdout)["BLOCKING_GATE"] == "PASS"
    negative = run_cli("--input", str(FIXTURES / "pr81_complete.json"), "--review-id", str(REVIEW81),
                       "--assessment", str(FIXTURES / "pr81_assessment.json"))
    assert negative.returncode == 2
    assert_unknown(json.loads(negative.stdout))


def test_cli_synthetic_p1_blocks(tmp_path):
    snapshot, assessment = synthetic_exact_head_pr81()
    ledger = tmp_path / "synthetic-assessment.json"
    ledger.write_text(json.dumps(assessment), encoding="utf-8")
    result = run_cli("--input", "-", "--review-id", str(REVIEW81), "--assessment", str(ledger), stdin=json.dumps(snapshot))
    assert result.returncode == 2
    assert json.loads(result.stdout)["BLOCKING_GATE"] == "BLOCKED"


def test_cli_invalid_or_missing_inputs_are_unknown(tmp_path):
    missing = str(tmp_path / "not-present.json")
    calls = [
        run_cli("--input", missing, "--review-id", str(REVIEW80)),
        run_cli("--input", "-", "--review-id", str(REVIEW80), stdin="not JSON"),
        run_cli("--input", str(FIXTURES / "pr80_complete.json"), "--review-id", str(REVIEW80), "--assessment", missing),
        run_cli("--input", str(FIXTURES / "pr80_complete.json"), "--review-id", str(REVIEW80)),
    ]
    for result in calls:
        assert result.returncode == 2
        assert_unknown(json.loads(result.stdout))


def test_cli_failed_identity_is_preserved_before_reading_bad_ledger(tmp_path):
    result = run_cli("--input", str(FIXTURES / "pr81_complete.json"), "--review-id", str(REVIEW81),
                     "--assessment", str(tmp_path / "absent.json"))
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output["REVIEW_IDENTITY"]["MATCH"] == "NO"
    assert output["errors"] == ["prerequisites: complete acquisition and matching HEAD required"]
