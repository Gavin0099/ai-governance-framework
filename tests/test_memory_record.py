from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.memory_record import (
    WRITER_ID,
    append_session_derived_entry,
    build_memory_record_suggestion,
    build_session_derived_record,
)


def test_build_session_derived_record_includes_canonical_fields() -> None:
    record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-1",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
    )
    assert record["memory_type"] == "session-derived"
    assert record["record_format_version"] == "1.0"
    assert record["writer"] == WRITER_ID
    assert record["commit_hash"] == "abc1234"


def test_append_session_derived_entry_writes_expected_lines(tmp_path: Path) -> None:
    record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-1",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
    )
    output = append_session_derived_entry(project_root=tmp_path, record=record)
    text = output.read_text(encoding="utf-8")
    assert "- memory_type: session-derived" in text
    assert "record_format_version: 1.0" in text
    assert f"writer: {WRITER_ID}" in text
    assert "commit_hash: abc1234" in text


def test_cli_writes_canonical_entry(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "cli test change",
            "--next-step", "verify cli output",
            "--commit", "abc1234",
            "--session-id", "test-session-cli",
            "--test-evidence", "subprocess invocation ok",
            "--plan-reconciliation", "not_applicable",
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "[memory_record] Written:" in result.stdout
    daily_files = list(tmp_path.glob("memory/*.md"))
    assert len(daily_files) == 1
    text = daily_files[0].read_text(encoding="utf-8")
    assert "- memory_type: session-derived" in text
    assert f"writer: {WRITER_ID}" in text
    assert "cli test change" in text
    assert "test-session-cli" in text
    assert "memory_binding: bound" in text


def test_build_memory_record_suggestion_returns_cli_command() -> None:
    cmd = build_memory_record_suggestion(
        what_changed="test change",
        commit="abc1234",
        session_id="session-1",
        plan_reconciliation="not_applicable",
        next_step="verify",
    )
    assert cmd.startswith("python governance_tools/memory_record.py")
    assert "--what-changed" in cmd
    assert "--commit abc1234" in cmd
    assert "--session-id session-1" in cmd


def test_append_session_derived_entry_deduplicates_equivalent_content(tmp_path: Path) -> None:
    record_a = build_session_derived_record(
        what_changed="changed (session=session-a)",
        commit="abc1234",
        session_id="session-a",
        memory_binding="bound",
        test_evidence="same evidence",
        next_step="same next step",
    )
    record_b = build_session_derived_record(
        what_changed="changed (session=session-b)",
        commit="abc1234",
        session_id="session-b",
        memory_binding="bound",
        test_evidence="same evidence",
        next_step="same next step",
    )
    output = append_session_derived_entry(project_root=tmp_path, record=record_a)
    append_session_derived_entry(project_root=tmp_path, record=record_b)
    text = output.read_text(encoding="utf-8")
    assert text.count("- memory_type: session-derived") == 1


def test_validate_plan_reconciliation_accepts_canonical_values() -> None:
    from governance_tools.memory_record import validate_plan_reconciliation

    assert validate_plan_reconciliation("updated") == ("updated", None)
    assert validate_plan_reconciliation("not_applicable") == ("not_applicable", None)
    value, error = validate_plan_reconciliation("deferred:requires-human-plan-review")
    assert value == "deferred:requires-human-plan-review"
    assert error is None


def test_validate_plan_reconciliation_missing_is_not_declared_advisory() -> None:
    from governance_tools.memory_record import validate_plan_reconciliation

    assert validate_plan_reconciliation(None) == ("not_declared", None)
    assert validate_plan_reconciliation("   ") == ("not_declared", None)


def test_validate_plan_reconciliation_rejects_vacuous_and_unknown_reasons() -> None:
    from governance_tools.memory_record import validate_plan_reconciliation

    for vacuous in ("deferred:later", "deferred:TODO", "deferred:pending"):
        _, error = validate_plan_reconciliation(vacuous)
        assert error is not None and "vacuous" in error

    _, error = validate_plan_reconciliation("deferred:")
    assert error is not None and "non-empty" in error

    _, error = validate_plan_reconciliation("deferred:some-novel-reason")
    assert error is not None and "taxonomy" in error

    _, error = validate_plan_reconciliation("done")
    assert error is not None


def test_record_and_render_include_plan_reconciliation() -> None:
    from governance_tools.memory_record import (
        build_session_derived_record,
        render_session_derived_entry,
    )

    record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-1",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
        plan_reconciliation="updated",
    )
    assert record["plan_reconciliation"] == "updated"
    assert "  plan_reconciliation: updated\n" in render_session_derived_entry(record)

    default_record = build_session_derived_record(
        what_changed="changed",
        commit="abc1234",
        session_id="session-2",
        memory_binding="bound",
        test_evidence="ok",
        next_step="next",
    )
    assert "  plan_reconciliation: not_declared\n" in render_session_derived_entry(default_record)


def test_cli_rejects_malformed_plan_reconciliation(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "cli test change",
            "--next-step", "verify rejection",
            "--commit", "abc1234",
            "--session-id", "test-session-reject",
            "--plan-reconciliation", "deferred:later",
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "vacuous" in result.stdout
    assert not (tmp_path / "memory").exists()


def test_cli_missing_plan_reconciliation_rejects_before_memory_write(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "cli test change",
            "--next-step", "verify required declaration",
            "--commit", "abc1234",
            "--session-id", "test-session-advisory",
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "--plan-reconciliation" in result.stderr
    assert not (tmp_path / "memory").exists()


@pytest.mark.parametrize(
    "plan_reconciliation",
    (
        "updated",
        "not_applicable",
        "deferred:scope-split-next-slice",
    ),
)
def test_cli_writes_each_explicit_plan_reconciliation_value(
    tmp_path: Path,
    plan_reconciliation: str,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "explicit declaration test",
            "--next-step", "verify explicit write",
            "--commit", "abc1234",
            "--session-id", f"test-session-{plan_reconciliation}",
            "--plan-reconciliation", plan_reconciliation,
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    written = list((tmp_path / "memory").glob("*.md"))
    assert len(written) == 1
    assert f"plan_reconciliation: {plan_reconciliation}" in written[0].read_text(encoding="utf-8")


# ── Write-time evidence provenance advisory ───────────────────────────────────

def _run_record_cli(tmp_path: Path, test_evidence: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "governance_tools/memory_record.py",
            "--what-changed", "provenance advisory test",
            "--next-step", "verify advisory",
            "--commit", "abc1234",
            "--session-id", "test-session-provenance",
            "--test-evidence", test_evidence,
            "--plan-reconciliation", "not_applicable",
            "--project-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )


def test_evidence_provenance_advisory_helper() -> None:
    from governance_tools.memory_authority_guard import evidence_provenance_advisory

    assert evidence_provenance_advisory("PASS: 5 tests green", None) == (
        "test_evidence_success_claim_without_artifact"
    )
    assert evidence_provenance_advisory("NOT RUN: planning-only entry", None) is None
    assert evidence_provenance_advisory("", None) is None


def test_evidence_provenance_advisory_accepts_existing_artifact(tmp_path: Path) -> None:
    from governance_tools.memory_authority_guard import evidence_provenance_advisory

    receipt = tmp_path / "artifacts" / "evidence" / "test-results" / "receipt-x.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}", encoding="utf-8")
    evidence = "PASS: focused suite; receipt artifacts/evidence/test-results/receipt-x.json"
    assert evidence_provenance_advisory(evidence, tmp_path) is None
    # a cited path that does not exist keeps the advisory
    missing = "PASS: focused suite; receipt artifacts/evidence/test-results/missing.json"
    assert evidence_provenance_advisory(missing, tmp_path) == (
        "test_evidence_success_claim_without_artifact"
    )


def test_cli_success_evidence_without_artifact_prints_advisory(tmp_path: Path) -> None:
    result = _run_record_cli(tmp_path, "PASS: 5 focused tests green")
    assert result.returncode == 0  # advisory never blocks the canonical writer
    assert "test_evidence_provenance_not_found" in result.stdout
    assert list((tmp_path / "memory").glob("*.md"))  # entry still written


def test_cli_success_evidence_with_receipt_has_no_advisory(tmp_path: Path) -> None:
    receipt = tmp_path / "artifacts" / "evidence" / "test-results" / "receipt-ok.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}", encoding="utf-8")
    result = _run_record_cli(
        tmp_path,
        "PASS: focused suite; receipt artifacts/evidence/test-results/receipt-ok.json",
    )
    assert result.returncode == 0
    assert "test_evidence_provenance_not_found" not in result.stdout
