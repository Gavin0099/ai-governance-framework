from __future__ import annotations

import subprocess
from pathlib import Path

from governance_tools.memory_authority_guard import _entry_is_bound, run_guard


def test_fabricated_commit_hash_no_longer_counts_as_bound_when_git_checked() -> None:
    block = """\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: fabricated commit anchor fixture
  commit: deadbee
  test_evidence: not relevant
  next_step: none
"""

    project_root = Path(__file__).resolve().parent.parent

    assert _entry_is_bound(block, project_root) == (
        False,
        "commit_hash_not_found_no_session_id",
    )


def test_existing_commit_hash_still_counts_as_bound_when_git_checked() -> None:
    project_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    head = completed.stdout.strip()
    block = f"""\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: real commit anchor fixture
  commit: {head}
  test_evidence: not relevant
  next_step: none
"""

    assert _entry_is_bound(block, project_root) == (True, "ok")


def test_fabricated_session_id_no_longer_counts_as_bound_without_artifact_provenance() -> None:
    block = """\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: fabricated session anchor fixture
  session_id: invented-session-token
  test_evidence: not relevant
  next_step: none
"""

    project_root = Path(__file__).resolve().parent.parent

    assert _entry_is_bound(block, project_root) == (
        False,
        "session_id_provenance_not_found",
    )


def test_session_id_with_canonical_closeout_artifact_still_counts_as_bound(tmp_path: Path) -> None:
    session_id = "session-20260704T120000-abc123"
    closeouts = tmp_path / "artifacts" / "runtime" / "closeouts"
    closeouts.mkdir(parents=True)
    (closeouts / f"{session_id}.json").write_text(
        f'{{"session_id": "{session_id}"}}\n',
        encoding="utf-8",
    )
    block = f"""\
- memory_type: session-derived
  record_format_version: 1.0
  writer: governance_tools.memory_record
  what_changed: real session anchor fixture
  session_id: {session_id}
  test_evidence: not relevant
  next_step: none
"""

    assert _entry_is_bound(block, tmp_path) == (True, "ok")


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
    assert "evidence_truth_unverified" not in result["violation_counts_by_code"]
    assert result["authority_coverage_rate"]["session_derived"] == {
        "total_entries": 1,
        "bound_entries": 0,
        "rate": 0.0,
    }
