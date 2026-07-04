"""B0 mutation fixtures for the memory blocking policy RFC.

Contract: docs/governance/self-governance-memory-blocking-policy-rfc-2026-07-04.md

These fixtures pin the current Phase 1 (report-only) behavior of the B0
candidate blocking class `session_like_non_session_memory_type` against the
six bypass scenarios enumerated in the RFC. The guard stays report-only:
nothing here asserts blocking. Scenarios that the future switch must close
but the current detector misses are pinned as misses on purpose, so closing
them later forces a conscious test update instead of a silent behavior change.

Scenario map (RFC "Mutation Contract Required Before The Switch"):
  1. prose rewording           -> still detected (field-based, not prose-based)
  2. novel memory_type value   -> still detected
  3. pre-window file append    -> currently NOT detected (known file-date bypass)
  4. hook bypass / CI parity   -> guard and workflow surfaces agree, report-only
  5. authority_override field  -> currently no effect (semantics not implemented)
  6. kill switch               -> current default IS Phase 1 semantics (pinned)
"""

from __future__ import annotations

from pathlib import Path

from governance_tools.memory_authority_guard import (
    _ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM,
    run_guard,
)
from governance_tools.memory_workflow import assess_memory_workflow

B0_CODE = "session_like_non_session_memory_type"

_IN_WINDOW_FILENAME = f"{_ACTIVE_NON_CANONICAL_WRITER_DEFAULT_FROM}.md"
_PRE_WINDOW_FILENAME = "2026-01-01.md"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_framework_surface(repo: Path) -> None:
    _write(repo / "governance" / "MEMORY_PROTOCOL.md", "# Memory Protocol\n")
    _write(repo / "governance_tools" / "memory_record.py", "# writer\n")
    _write(repo / "governance_tools" / "memory_authority_guard.py", "# guard\n")


def _write_memory(repo: Path, filename: str, entry: str) -> None:
    _write(repo / "memory" / filename, entry)


def _b0_counts(repo: Path) -> dict[str, int]:
    result = run_guard(repo / "memory", repo, skip_git=True)
    return result["violation_counts_by_code"]


def test_b0_scenario1_prose_rewording_does_not_evade_detection(tmp_path: Path) -> None:
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: routine observations captured for later reference\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


def test_b0_scenario1_minimal_session_field_residue_still_detected(tmp_path: Path) -> None:
    # Aggressive rewording: all anchors and evidence removed, only a single
    # session-shaped field (next_step) survives. Detection is field-based,
    # so one residue field is enough.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  what_changed: informal working notes, nothing session related here\n"
        "  next_step: continue tomorrow\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


def test_b0_scenario2_novel_memory_type_value_does_not_evade_detection(tmp_path: Path) -> None:
    # memory_type values are not matched against an allowlist; any non-session
    # value with session-shaped fields must keep triggering.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: reflection_shard\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: session entry hidden behind an invented type\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    assert _b0_counts(tmp_path)[B0_CODE] == 1


def test_b0_scenario3_pre_window_file_append_currently_evades_detection(tmp_path: Path) -> None:
    # KNOWN BYPASS (VULNERABLE): the active window is classified by daily
    # filename date, so a new session-shaped entry appended to a pre-window
    # file is not reported. The RFC requires closing this (window from entry,
    # not file date alone) before the B0 switch may ship. When that lands,
    # this fixture must flip to asserting detection.
    _write_memory(
        tmp_path,
        _PRE_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: session entry backdated into a pre-window file\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    assert B0_CODE not in _b0_counts(tmp_path)


def test_b0_scenario4_guard_and_workflow_surfaces_report_same_verdict(tmp_path: Path) -> None:
    # Ownership rule: hook and CI must consume the same guard verdict. A hook
    # bypass via --no-verify is out of a test's reach, but surface parity is
    # not: the workflow entrypoint used by pre-commit and CI must report the
    # same B0 count as run_guard, and both must stay report-only.
    _make_framework_surface(tmp_path)
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: parity fixture entry\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    guard_counts = _b0_counts(tmp_path)
    workflow = assess_memory_workflow(
        tmp_path,
        changed_files=[f"memory/{_IN_WINDOW_FILENAME}"],
        run_guard_check=True,
    )

    assert guard_counts[B0_CODE] == 1
    assert workflow.guard_summary[B0_CODE] == guard_counts[B0_CODE]
    assert B0_CODE in workflow.warnings
    assert workflow.blockers == []
    assert workflow.completion_claim_allowed is True


def test_b0_scenario5_authority_override_field_has_no_effect_in_phase1(tmp_path: Path) -> None:
    # The RFC defines authority_override as a future per-entry downgrade that
    # must emit authority_override_used. None of that exists yet: the field
    # must be inert, the violation still reported, and no override code
    # emitted. Implementing override semantics must consciously update this.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: override fixture entry\n"
        "  authority_override: reviewer-x pre-rfc-fixture\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    counts = _b0_counts(tmp_path)

    assert counts[B0_CODE] == 1
    assert "authority_override_used" not in counts


def test_b0_scenario6_phase1_semantics_pinned_even_when_b0_fires(tmp_path: Path) -> None:
    # Kill-switch precondition: the current default must equal Phase 1
    # report-only semantics with no policy input. When the policy switch
    # lands, its default-off state must keep this exact shape.
    _write_memory(
        tmp_path,
        _IN_WINDOW_FILENAME,
        "- memory_type: note\n"
        "  record_format_version: 1.0\n"
        "  writer: manual.editor\n"
        "  what_changed: phase1 semantics fixture entry\n"
        "  commit: deadbee\n"
        "  memory_binding: bound\n"
        "  test_evidence: not relevant\n"
        "  next_step: none\n",
    )

    result = run_guard(tmp_path / "memory", tmp_path, skip_git=True)

    assert result["ok"] is True
    assert result["ok_meaning"] == "guard_executed_report_only_not_authority_clean"
    assert result["phase"] == "phase1"
    assert result["mode"] == "warning"
    assert result["enforcement_action"] == "allow"
    assert result["blocking_violation_codes"] == []
    assert result["claim_ceiling"] == "report_only_phase1"
    assert "blocking_enforcement" in result["not_claimed"]
    assert result["violation_counts_by_code"][B0_CODE] == 1
    assert B0_CODE in result["report_only_violation_codes"]
