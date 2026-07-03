from __future__ import annotations

from pathlib import Path

from governance_tools.memory_authority_guard import _entry_is_bound, run_guard


def test_fabricated_commit_hash_is_currently_treated_as_bound_vulnerable_baseline() -> None:
    block = """\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: fabricated commit anchor fixture
  commit: deadbee
  test_evidence: not relevant
  next_step: none
"""

    assert _entry_is_bound(block) == (True, "ok")


def test_fabricated_session_id_is_currently_treated_as_bound_vulnerable_baseline() -> None:
    block = """\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: fabricated session anchor fixture
  session_id: invented-session-token
  test_evidence: not relevant
  next_step: none
"""

    assert _entry_is_bound(block) == (True, "ok")


def test_unverified_test_evidence_currently_has_no_truth_violation_code(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    (memory_root / "2026-07-04.md").write_text(
        """\
# 2026-07-04

- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: claimed tests without a verifiable execution artifact
  commit: deadbee
  commit_hash: deadbee
  session_id: invented-session-token
  memory_binding: bound
  test_evidence: PASS: tests/example.py -> 38 passed
  next_step: none
  plan_reconciliation: not_applicable
""",
        encoding="utf-8",
    )

    result = run_guard(memory_root, tmp_path, skip_git=True)

    assert result["ok"] is True
    assert result["phase"] == "phase1"
    assert result["mode"] == "warning"
    assert result["violation_counts_by_code"] == {}
    assert result["authority_coverage_rate"]["session_derived"] == {
        "total_entries": 1,
        "bound_entries": 1,
        "rate": 1.0,
    }
