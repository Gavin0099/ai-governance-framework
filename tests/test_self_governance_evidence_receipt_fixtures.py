"""R3 Option A fixtures: structured test-evidence receipt metadata checks.

Contract: docs/governance/self-governance-evidence-artifact-metadata-design-2026-07-04.md

These pin the advisory metadata layer added on top of the existence-only
`test_evidence_provenance_not_found` check:

* a valid receipt with exit_code 0 stays silent;
* a receipt recording a failing run under success prose contradicts the claim;
* a malformed receipt is visible and does not count;
* an existing non-receipt artifact warns softly (advisory window only);
* pre-window files stay silent (historical artifacts predate the shape);
* all three codes are report-only and not policy-blockable.

Every field of a receipt remains fabricatable by a hostile writer: these
checks raise fabrication cost, they never prove evidence truth.
"""

from __future__ import annotations

import json
from pathlib import Path

from governance_tools.memory_authority_guard import (
    _EVIDENCE_RECEIPT_ADVISORY_FROM,
    load_blocking_policy,
    run_guard,
)
from governance_tools.memory_workflow import assess_memory_workflow

MISSING_CODE = "test_evidence_artifact_metadata_missing"
INVALID_CODE = "test_evidence_artifact_metadata_invalid"
CONTRADICTS_CODE = "test_evidence_exit_code_contradicts_claim"
PROVENANCE_CODE = "test_evidence_provenance_not_found"

_ADVISORY_FILENAME = f"{_EVIDENCE_RECEIPT_ADVISORY_FROM}.md"
_PRE_ADVISORY_FILENAME = "2026-06-20.md"
_RECEIPT_RELPATH = "artifacts/runtime/test-results/run.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _receipt_payload(**overrides) -> dict:
    payload = {
        "receipt_schema": "test_evidence_receipt.v0.1",
        "status": "report_only",
        "command": "python -m pytest tests/test_example.py -q",
        "exit_code": 0,
        "started_at": "2026-07-05T10:00:00Z",
        "finished_at": "2026-07-05T10:00:12Z",
        "runner": "codex-pytest-wrapper",
        "linked_commit": "22e3ff0",
        "output_artifacts": ["artifacts/runtime/test-results/pytest.txt"],
        "cannot_claim": ["semantic correctness of the tested behavior"],
    }
    payload.update(overrides)
    return payload


def _write_evidence_repo(
    repo: Path,
    *,
    filename: str = _ADVISORY_FILENAME,
    artifact_text: str | None = None,
    receipt: dict | None = None,
    evidence_path: str = _RECEIPT_RELPATH,
) -> None:
    if receipt is not None:
        _write(repo / _RECEIPT_RELPATH, json.dumps(receipt, indent=2))
    elif artifact_text is not None:
        _write(repo / evidence_path, artifact_text)
    _write(
        repo / "memory" / filename,
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: evidence receipt fixture entry\n"
        f"  test_evidence: PASS: {evidence_path} -> 12 passed\n"
        "  next_step: none\n",
    )


def _codes(repo: Path) -> dict[str, int]:
    result = run_guard(repo / "memory", repo, skip_git=True)
    return result["violation_counts_by_code"]


def test_valid_receipt_with_exit_zero_is_silent(tmp_path: Path) -> None:
    _write_evidence_repo(tmp_path, receipt=_receipt_payload())

    codes = _codes(tmp_path)

    for code in (MISSING_CODE, INVALID_CODE, CONTRADICTS_CODE, PROVENANCE_CODE):
        assert code not in codes


def test_failing_exit_code_under_success_prose_contradicts_claim(tmp_path: Path) -> None:
    _write_evidence_repo(tmp_path, receipt=_receipt_payload(exit_code=1))

    codes = _codes(tmp_path)

    assert codes[CONTRADICTS_CODE] == 1
    assert INVALID_CODE not in codes


def test_schema_mismatch_receipt_is_invalid_not_missing(tmp_path: Path) -> None:
    _write_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(receipt_schema="test_evidence_receipt.v9.9"),
    )

    codes = _codes(tmp_path)

    assert codes[INVALID_CODE] == 1
    assert MISSING_CODE not in codes


def test_missing_required_field_is_invalid(tmp_path: Path) -> None:
    receipt = _receipt_payload()
    del receipt["runner"]
    _write_evidence_repo(tmp_path, receipt=receipt)

    codes = _codes(tmp_path)

    assert codes[INVALID_CODE] == 1


def test_wrong_typed_exit_code_is_invalid(tmp_path: Path) -> None:
    _write_evidence_repo(tmp_path, receipt=_receipt_payload(exit_code="0"))

    codes = _codes(tmp_path)

    assert codes[INVALID_CODE] == 1


def test_existing_plain_artifact_warns_metadata_missing(tmp_path: Path) -> None:
    # Soft documentation warning: the artifact exists but carries no
    # structured metadata. This is the adoption-pressure mechanism, not a
    # block, because historical tooling predates the receipt shape.
    _write_evidence_repo(
        tmp_path,
        artifact_text="38 passed\n",
        evidence_path="artifacts/runtime/test-results/pytest.txt",
    )

    codes = _codes(tmp_path)

    assert codes[MISSING_CODE] == 1
    assert PROVENANCE_CODE not in codes


def test_pre_advisory_window_files_stay_silent(tmp_path: Path) -> None:
    # Backcompat pin: artifacts referenced by pre-window daily files predate
    # the receipt shape and must not flood the signal.
    _write_evidence_repo(
        tmp_path,
        filename=_PRE_ADVISORY_FILENAME,
        artifact_text="38 passed\n",
        evidence_path="artifacts/runtime/test-results/pytest.txt",
    )

    codes = _codes(tmp_path)

    for code in (MISSING_CODE, INVALID_CODE, CONTRADICTS_CODE):
        assert code not in codes


def test_missing_artifact_stays_with_provenance_check_only(tmp_path: Path) -> None:
    # No existing artifact: the existence-only layer owns that case; the
    # metadata layer must not double-report.
    _write_evidence_repo(tmp_path)  # evidence path never written

    codes = _codes(tmp_path)

    assert codes[PROVENANCE_CODE] == 1
    for code in (MISSING_CODE, INVALID_CODE, CONTRADICTS_CODE):
        assert code not in codes


def test_metadata_codes_are_report_only_and_not_blockable(tmp_path: Path) -> None:
    _write_evidence_repo(tmp_path, receipt=_receipt_payload(exit_code=1))

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []

    # A policy trying to enable a metadata code fails visibly (F3 rule):
    # advisory codes are not blockable without a separate policy decision.
    _write(
        tmp_path / "governance" / "memory_blocking_policy.json",
        json.dumps({
            "policy_schema": "memory_blocking_policy.v0.1",
            "enabled": True,
            "blocking_codes": [CONTRADICTS_CODE],
        }),
    )
    policy = load_blocking_policy(tmp_path)
    assert policy["enabled_codes"] == []
    assert policy["error"] == f"blocking_policy_unknown_code:{CONTRADICTS_CODE}"


def test_workflow_surfaces_metadata_warnings(tmp_path: Path) -> None:
    _write(tmp_path / "governance" / "MEMORY_PROTOCOL.md", "# Memory Protocol\n")
    _write(tmp_path / "governance_tools" / "memory_record.py", "# writer\n")
    _write(tmp_path / "governance_tools" / "memory_authority_guard.py", "# guard\n")
    _write_evidence_repo(tmp_path, receipt=_receipt_payload(exit_code=2))

    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_ADVISORY_FILENAME}"],
        run_guard_check=True,
    )

    assert CONTRADICTS_CODE in workflow.warnings
    assert workflow.guard_summary.get(CONTRADICTS_CODE, 0) == 1
    assert workflow.blockers == []
