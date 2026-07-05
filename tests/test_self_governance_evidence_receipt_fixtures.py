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

import pytest

from governance_tools.ci_memory_workflow_check import check as ci_check
from governance_tools.memory_authority_guard import (
    _EVIDENCE_RECEIPT_ADVISORY_FROM,
    load_blocking_policy,
    run_guard,
)
from governance_tools.memory_workflow import assess_memory_workflow

MISSING_CODE = "test_evidence_artifact_metadata_missing"
INVALID_CODE = "test_evidence_artifact_metadata_invalid"
CONTRADICTS_CODE = "test_evidence_exit_code_contradicts_claim"
MISMATCH_CODE = "test_evidence_linked_commit_mismatch"
NOT_DURABLE_CODE = "test_evidence_artifact_not_durable"
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


# ── R3 Option B: linked_commit consistency ────────────────────────────────────


def _write_anchored_evidence_repo(
    repo: Path,
    *,
    receipt: dict,
    entry_commit: str | None = "deadbee",
) -> None:
    _write(repo / _RECEIPT_RELPATH, json.dumps(receipt, indent=2))
    commit_line = f"  commit: {entry_commit}\n" if entry_commit else ""
    _write(
        repo / "memory" / _ADVISORY_FILENAME,
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: linked commit fixture entry\n"
        f"{commit_line}"
        f"  test_evidence: PASS: {_RECEIPT_RELPATH} -> 12 passed\n"
        "  next_step: none\n",
    )


def test_option_b_prefix_matching_anchor_is_silent(tmp_path: Path) -> None:
    # Entry carries the short hash, receipt carries the full hash: consistent.
    full = "deadbee" + "0" * 33
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit=full),
        entry_commit="deadbee",
    )

    assert MISMATCH_CODE not in _codes(tmp_path)


def test_option_b_mismatched_anchor_is_reported(tmp_path: Path) -> None:
    # The receipt records a run at some other commit than the one the entry
    # claims: the borrowed-evidence case Option B exists for.
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit="cafef00d" + "1" * 32),
        entry_commit="deadbee",
    )

    codes = _codes(tmp_path)
    assert codes[MISMATCH_CODE] == 1


def test_option_b_no_git_worktree_receipt_skips_comparison(tmp_path: Path) -> None:
    # A receipt honestly marked no_git_worktree has nothing to compare.
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit="no_git_worktree"),
        entry_commit="deadbee",
    )

    assert MISMATCH_CODE not in _codes(tmp_path)


def test_option_b_entry_without_commit_anchor_skips_comparison(tmp_path: Path) -> None:
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit="cafef00d" + "1" * 32),
        entry_commit=None,
    )

    assert MISMATCH_CODE not in _codes(tmp_path)


def test_option_b_exit_code_contradiction_takes_precedence(tmp_path: Path) -> None:
    # A failing run quoted as success is the stronger finding; the commit
    # comparison only runs on receipts that survive the earlier checks.
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(
            exit_code=1, linked_commit="cafef00d" + "1" * 32
        ),
        entry_commit="deadbee",
    )

    codes = _codes(tmp_path)
    assert codes[CONTRADICTS_CODE] == 1
    assert MISMATCH_CODE not in codes


def test_option_b_mismatch_is_report_only_and_not_blockable(tmp_path: Path) -> None:
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit="cafef00d" + "1" * 32),
        entry_commit="deadbee",
    )

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []

    _write(
        tmp_path / "governance" / "memory_blocking_policy.json",
        json.dumps({
            "policy_schema": "memory_blocking_policy.v0.1",
            "enabled": True,
            "blocking_codes": [MISMATCH_CODE],
        }),
    )
    policy = load_blocking_policy(tmp_path)
    assert policy["enabled_codes"] == []
    assert policy["error"] == f"blocking_policy_unknown_code:{MISMATCH_CODE}"


def test_option_b_ci_surfaces_mismatch_without_blocking(tmp_path: Path) -> None:
    _write_anchored_evidence_repo(
        tmp_path,
        receipt=_receipt_payload(linked_commit="cafef00d" + "1" * 32),
        entry_commit="deadbee",
    )

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_ADVISORY_FILENAME}"]
    )

    assert result.clean is True
    assert any(w.startswith(f"{MISMATCH_CODE}=") for w in result.warnings)


# ── R3 Option C: durable evidence path policy ─────────────────────────────────


def _init_git_repo_with_runtime_ignore(repo: Path) -> None:
    import subprocess

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    _write(repo / ".gitignore", "artifacts/runtime/\n")


def test_option_c_gitignored_evidence_artifact_warns_not_durable(tmp_path: Path) -> None:
    # A receipt under artifacts/runtime/ verifies locally but vanishes on a
    # fresh checkout: local-verifiable is not durable repo evidence.
    _init_git_repo_with_runtime_ignore(tmp_path)
    _write_evidence_repo(tmp_path, receipt=_receipt_payload())

    codes = _codes(tmp_path)

    assert codes[NOT_DURABLE_CODE] == 1


def test_option_c_tracked_lure_does_not_make_ignored_receipt_durable(tmp_path: Path) -> None:
    # Red-team regression: durability must be anchored to a durable receipt,
    # not to any unrelated trackable artifact mentioned in the same prose.
    _init_git_repo_with_runtime_ignore(tmp_path)
    lure = "artifacts/evidence/test-results/lure.txt"
    _write(tmp_path / _RECEIPT_RELPATH, json.dumps(_receipt_payload()))
    _write(tmp_path / lure, "not a receipt\n")
    _write(
        tmp_path / "memory" / _ADVISORY_FILENAME,
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: durable lure fixture entry\n"
        f"  test_evidence: PASS: {_RECEIPT_RELPATH} and {lure} -> 12 passed\n"
        "  next_step: none\n",
    )

    codes = _codes(tmp_path)

    assert codes[NOT_DURABLE_CODE] == 1
    assert MISSING_CODE not in codes


def test_option_c_tracked_evidence_artifact_is_silent(tmp_path: Path) -> None:
    _init_git_repo_with_runtime_ignore(tmp_path)
    durable = "artifacts/evidence/test-results/run.json"
    _write(tmp_path / durable, json.dumps(_receipt_payload()))
    _write(
        tmp_path / "memory" / _ADVISORY_FILENAME,
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: durable evidence fixture entry\n"
        f"  test_evidence: PASS: {durable} -> 12 passed\n"
        "  next_step: none\n",
    )

    codes = _codes(tmp_path)

    assert NOT_DURABLE_CODE not in codes


def test_option_c_without_worktree_durability_is_unknowable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No git worktree: durability cannot be determined, so the check skips
    # instead of guessing (honest boundary, mirrors anchor semantics).
    # The no-worktree condition is pinned via monkeypatch because a bare
    # tmp_path is environment-dependent: with a repo-local pytest basetemp,
    # git walks up to the enclosing repository and the outer gitignore
    # matches, which is exactly the class of flakiness this repo has hit
    # before (see the memory-truth provenance test task).
    import governance_tools.memory_authority_guard as guard_module

    monkeypatch.setattr(
        guard_module, "_project_has_git_worktree", lambda _root: False
    )
    _write_evidence_repo(tmp_path, receipt=_receipt_payload())

    codes = _codes(tmp_path)

    assert NOT_DURABLE_CODE not in codes


def test_option_c_not_durable_is_report_only_and_not_blockable(tmp_path: Path) -> None:
    _init_git_repo_with_runtime_ignore(tmp_path)
    _write_evidence_repo(tmp_path, receipt=_receipt_payload())

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []

    _write(
        tmp_path / "governance" / "memory_blocking_policy.json",
        json.dumps({
            "policy_schema": "memory_blocking_policy.v0.1",
            "enabled": True,
            "blocking_codes": [NOT_DURABLE_CODE],
        }),
    )
    policy = load_blocking_policy(tmp_path)
    assert policy["enabled_codes"] == []
    assert policy["error"] == f"blocking_policy_unknown_code:{NOT_DURABLE_CODE}"


def test_option_c_ci_surfaces_not_durable_without_blocking(tmp_path: Path) -> None:
    _init_git_repo_with_runtime_ignore(tmp_path)
    _write_evidence_repo(tmp_path, receipt=_receipt_payload())

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_ADVISORY_FILENAME}"]
    )

    assert result.clean is True
    assert any(w.startswith(f"{NOT_DURABLE_CODE}=") for w in result.warnings)


def test_ci_surfaces_metadata_warnings_without_blocking(tmp_path: Path) -> None:
    # CI surface parity (round-3 review finding): the CI gate consumer must
    # show the same R3 advisory codes as the workflow surface, still clean.
    _write_evidence_repo(tmp_path, receipt=_receipt_payload(exit_code=2))

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_ADVISORY_FILENAME}"]
    )

    assert result.clean is True
    assert result.blockers == []
    assert any(w.startswith(f"{CONTRADICTS_CODE}=") for w in result.warnings)


def test_ci_surfaces_metadata_missing_without_blocking(tmp_path: Path) -> None:
    _write_evidence_repo(
        tmp_path,
        artifact_text="38 passed\n",
        evidence_path="artifacts/runtime/test-results/pytest.txt",
    )

    result = ci_check(
        tmp_path, changed_files=[f"memory/{_ADVISORY_FILENAME}"]
    )

    assert result.clean is True
    assert any(w.startswith(f"{MISSING_CODE}=") for w in result.warnings)
