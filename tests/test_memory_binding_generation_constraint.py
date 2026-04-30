"""
Tests for Memory Binding Generation Constraint v0.1

Covers:
  - guard._entry_is_bound() binding logic for 4 canonical states
  - run_guard() authority_coverage_rate computation
  - _resolve_memory_binding() via session_end._build_daily_memory_record()
  - guard check_daily_memory() entry detection for both field name formats

See: governance/MEMORY_AUTHORITY_CONTRACT.md
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.memory_authority_guard import (
    _entry_is_bound,
    _parse_promotion_status,
    check_daily_memory,
    check_structural_memory,
    run_guard,
)
from runtime_hooks.core.session_end import _resolve_memory_binding


# ── _entry_is_bound: 4 canonical binding states ───────────────────────────────

def _make_entry(commit_hash: str = "", session_id: str = "") -> str:
    """Build a minimal daily memory entry block for testing."""
    lines = ["- what changed: test change"]
    if commit_hash:
        lines.append(f"  commit hash: {commit_hash}")
    if session_id:
        lines.append(f"  session_id: {session_id}")
    lines.append("  test_evidence: ok")
    return "\n".join(lines)


def test_entry_is_bound_real_commit_hash():
    """Real commit hash → bound regardless of session_id."""
    block = _make_entry(commit_hash="abc1234")
    bound, reason = _entry_is_bound(block)
    assert bound is True
    assert reason == "ok"


def test_entry_is_bound_pending_no_session_id():
    """commit hash: pending with no session_id → unbound (VIOLATION)."""
    block = _make_entry(commit_hash="pending")
    bound, reason = _entry_is_bound(block)
    assert bound is False
    assert reason == "commit_hash_pending_no_session_id"


def test_entry_is_bound_no_commit_with_session_id():
    """No commit hash but session_id present → bound (valid fallback)."""
    block = _make_entry(session_id="session-20260430T120000-abc123")
    bound, reason = _entry_is_bound(block)
    assert bound is True
    assert reason == "ok"


def test_entry_is_bound_no_commit_no_session_id():
    """No commit hash and no session_id → unbound (VIOLATION)."""
    block = _make_entry()
    bound, reason = _entry_is_bound(block)
    assert bound is False
    assert reason == "no_anchor"


# ── additional edge cases ─────────────────────────────────────────────────────

def test_entry_is_bound_uncommitted_no_session_id():
    """commit: UNCOMMITTED with no session_id → unbound."""
    block = "- what changed: test\n  commit: UNCOMMITTED\n  test_evidence: ok"
    bound, reason = _entry_is_bound(block)
    assert bound is False
    assert reason == "commit_uncommitted_no_session_id"


def test_entry_is_bound_uncommitted_with_session_id():
    """commit: UNCOMMITTED + session_id → bound (session_id is valid fallback)."""
    block = (
        "- what changed: test\n"
        "  commit: UNCOMMITTED\n"
        "  session_id: session-20260430T120000-def456\n"
        "  test_evidence: ok"
    )
    bound, reason = _entry_is_bound(block)
    assert bound is True
    assert reason == "ok"


def test_entry_is_bound_pending_with_session_id():
    """commit hash: pending + session_id → bound (session_id overrides pending)."""
    block = _make_entry(commit_hash="pending", session_id="session-20260430T120000-ghi789")
    bound, reason = _entry_is_bound(block)
    assert bound is True
    assert reason == "ok"


def test_entry_is_bound_auto_generated_format():
    """Auto-generated entry uses 'commit:' (not 'commit hash:') — must be detected."""
    # Real hash in auto-generated format
    block = (
        "- what_changed: session_end auto-closeout recorded for `task` "
        "(session=session-20260430T120000-xyz, decision=AUTO_PROMOTE).\n"
        "  commit: dc69408\n"
        "  session_id: session-20260430T120000-xyz\n"
        "  memory_binding: bound\n"
        "  test_evidence: ok\n"
        "  next_step: continue"
    )
    bound, reason = _entry_is_bound(block)
    assert bound is True
    assert reason == "ok"


# ── _resolve_memory_binding ───────────────────────────────────────────────────

def test_resolve_memory_binding_real_hash():
    assert _resolve_memory_binding("dc69408", "session-abc") == "bound"


def test_resolve_memory_binding_uncommitted_with_session():
    assert _resolve_memory_binding("UNCOMMITTED", "session-abc") == "bound_session_id"


def test_resolve_memory_binding_uncommitted_no_session():
    assert _resolve_memory_binding("UNCOMMITTED", "") == "unbound"


def test_resolve_memory_binding_empty_commit_with_session():
    assert _resolve_memory_binding("", "session-abc") == "bound_session_id"


def test_resolve_memory_binding_neither():
    assert _resolve_memory_binding("", "") == "unbound"


# ── authority_coverage_rate in run_guard ─────────────────────────────────────

@pytest.fixture
def tmp_memory_root(tmp_path):
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    return memory_root


def _write_daily_file(memory_root: Path, date: str, content: str) -> None:
    (memory_root / f"{date}.md").write_text(
        f"# {date}\n\n{content}", encoding="utf-8"
    )


def test_authority_coverage_rate_all_bound(tmp_memory_root, tmp_path):
    _write_daily_file(
        tmp_memory_root, "2026-04-30",
        "- what changed: change A\n  commit hash: `abc1234`\n  test_evidence: ok\n\n"
        "- what changed: change B\n  commit hash: `def5678`\n  test_evidence: ok\n",
    )
    result = run_guard(tmp_memory_root, tmp_path, skip_git=True)
    acr = result["authority_coverage_rate"]["session_derived"]
    assert acr["total_entries"] == 2
    assert acr["bound_entries"] == 2
    assert acr["rate"] == 1.0
    assert result["violation_count"] == 0


def test_authority_coverage_rate_none_bound(tmp_memory_root, tmp_path):
    _write_daily_file(
        tmp_memory_root, "2026-04-30",
        "- what changed: change A\n  commit hash: pending\n  test_evidence: ok\n\n"
        "- what changed: change B\n  commit hash: pending\n  test_evidence: ok\n",
    )
    result = run_guard(tmp_memory_root, tmp_path, skip_git=True)
    acr = result["authority_coverage_rate"]["session_derived"]
    assert acr["total_entries"] == 2
    assert acr["bound_entries"] == 0
    assert acr["rate"] == 0.0
    # Both entries flagged as unbound_memory
    assert result["violation_counts_by_code"].get("unbound_memory", 0) == 2


def test_authority_coverage_rate_mixed(tmp_memory_root, tmp_path):
    _write_daily_file(
        tmp_memory_root, "2026-04-30",
        "- what changed: change A\n  commit hash: `abc1234`\n  test_evidence: ok\n\n"
        "- what changed: change B\n  commit hash: pending\n  test_evidence: ok\n\n"
        "- what changed: change C\n  session_id: session-20260430T120000-xyz\n  test_evidence: ok\n",
    )
    result = run_guard(tmp_memory_root, tmp_path, skip_git=True)
    acr = result["authority_coverage_rate"]["session_derived"]
    assert acr["total_entries"] == 3
    assert acr["bound_entries"] == 2   # A (real hash) + C (session_id)
    assert acr["rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert result["violation_counts_by_code"].get("unbound_memory", 0) == 1


def test_authority_coverage_rate_no_files(tmp_memory_root, tmp_path):
    result = run_guard(tmp_memory_root, tmp_path, skip_git=True)
    acr = result["authority_coverage_rate"]["session_derived"]
    assert acr["total_entries"] == 0
    assert acr["bound_entries"] == 0
    assert acr["rate"] is None  # undefined for empty set


# ── check_daily_memory detects both entry field name formats ──────────────────

def test_check_daily_memory_detects_space_format(tmp_memory_root):
    """'- what changed:' (human format with space) should be detected."""
    (tmp_memory_root / "2026-04-30.md").write_text(
        "# 2026-04-30\n\n- what changed: test\n  commit hash: abc1234\n",
        encoding="utf-8",
    )
    violations, coverage = check_daily_memory(tmp_memory_root)
    assert coverage["total_entries"] == 1
    assert coverage["bound_entries"] == 1


def test_check_daily_memory_detects_underscore_format(tmp_memory_root):
    """'- what_changed:' (auto-generated format with underscore) should be detected."""
    (tmp_memory_root / "2026-04-30.md").write_text(
        "# 2026-04-30\n\n"
        "- what_changed: session_end auto-closeout\n"
        "  commit: dc69408\n"
        "  session_id: session-20260430T120000-abc\n"
        "  memory_binding: bound\n",
        encoding="utf-8",
    )
    violations, coverage = check_daily_memory(tmp_memory_root)
    assert coverage["total_entries"] == 1
    assert coverage["bound_entries"] == 1
    assert len(violations) == 0


def test_check_daily_memory_flags_pending_in_either_format(tmp_memory_root):
    """Both 'commit hash: pending' and 'commit: pending' should be flagged."""
    content = (
        "- what changed: entry A\n  commit hash: pending\n\n"
        "- what_changed: entry B\n  commit: pending\n"
    )
    (tmp_memory_root / "2026-04-30.md").write_text(
        f"# 2026-04-30\n\n{content}", encoding="utf-8"
    )
    violations, coverage = check_daily_memory(tmp_memory_root)
    assert coverage["total_entries"] == 2
    assert coverage["bound_entries"] == 0
    assert len(violations) == 2
    reasons = {v["reason"] for v in violations}
    assert "commit_hash_pending_no_session_id" in reasons


# ── structural promotion marker detection ────────────────────────────────────

def _make_long_term(sections: list[tuple[str, str]], tmp_path: Path) -> Path:
    """
    Build a 00_long_term.md in tmp_path with given sections.
    sections = [(heading, body_markdown), ...]
    """
    lines = ["# Long-Term Memory\n"]
    for heading, body in sections:
        lines.append(f"## {heading}\n{body}\n")
    p = tmp_path / "00_long_term.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_parse_promotion_status_candidate():
    text = "<!-- promotion_status: candidate -->"
    assert _parse_promotion_status(text) == "candidate"


def test_parse_promotion_status_authoritative():
    text = "<!-- promotion_status: authoritative -->\n<!-- promoted_by: Gavin / 2026-04-30 -->"
    assert _parse_promotion_status(text) == "authoritative"


def test_parse_promotion_status_stale():
    text = "<!-- promotion_status: stale -->"
    assert _parse_promotion_status(text) == "stale"


def test_parse_promotion_status_none_when_missing():
    text = "Some section text without any markers"
    assert _parse_promotion_status(text) == "none"


def test_structural_candidate_section_is_info_not_warning(tmp_path):
    """candidate sections emit info-severity, not warning."""
    _make_long_term([
        ("My Section",
         "<!-- memory_type: structural_long_term -->\n"
         "<!-- promotion_status: candidate -->\n"
         "<!-- proposed_by: ai / 2026-04-30 -->\n"
         "Some content here.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert coverage["total_sections"] == 1
    assert coverage["promoted_sections"] == 0
    assert len(violations) == 1
    assert violations[0]["severity"] == "info"
    assert violations[0]["reason"] == "not_yet_authoritative"
    assert violations[0]["promotion_status"] == "candidate"


def test_structural_no_marker_is_warning(tmp_path):
    """Sections without any promotion marker emit warning-severity."""
    _make_long_term([
        ("My Section", "Some content without markers.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert len(violations) == 1
    assert violations[0]["severity"] == "warning"
    assert violations[0]["reason"] == "missing_marker"
    assert violations[0]["promotion_status"] == "none"


def test_structural_authoritative_with_promoted_by_is_clear(tmp_path):
    """authoritative + promoted_by = no violation, counts in coverage rate."""
    _make_long_term([
        ("My Section",
         "<!-- memory_type: structural_long_term -->\n"
         "<!-- promotion_status: authoritative -->\n"
         "<!-- promoted_by: Gavin / 2026-04-30 -->\n"
         "<!-- source_anchor: commit:abc1234 -->\n"
         "Confirmed content.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert coverage["total_sections"] == 1
    assert coverage["promoted_sections"] == 1
    assert len(violations) == 0


def test_structural_authoritative_without_promoted_by_is_warning(tmp_path):
    """authoritative without promoted_by = violation (missing_promoted_by)."""
    _make_long_term([
        ("My Section",
         "<!-- promotion_status: authoritative -->\n"
         "Content without promoted_by marker.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert coverage["promoted_sections"] == 0
    assert len(violations) == 1
    assert violations[0]["severity"] == "warning"
    assert violations[0]["reason"] == "missing_promoted_by"


def test_structural_stale_section_is_warning(tmp_path):
    """stale sections emit warning-severity."""
    _make_long_term([
        ("Old Section",
         "<!-- promotion_status: stale -->\n"
         "<!-- stale_reason: superseded by v2 -->\n"
         "Old content.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert violations[0]["severity"] == "warning"
    assert violations[0]["reason"] == "stale_section"


def test_structural_coverage_rate_mixed(tmp_path):
    """Mixed sections: authoritative counts, candidate does not."""
    _make_long_term([
        ("Auth Section",
         "<!-- promotion_status: authoritative -->\n"
         "<!-- promoted_by: Gavin / 2026-04-30 -->\n"
         "Confirmed.\n"),
        ("Candidate Section",
         "<!-- promotion_status: candidate -->\n"
         "Proposed.\n"),
        ("Unmarked Section", "No markers.\n"),
    ], tmp_path)
    violations, coverage = check_structural_memory(tmp_path)
    assert coverage["total_sections"] == 3
    assert coverage["promoted_sections"] == 1
    assert coverage["promoted_sections"] / coverage["total_sections"] == pytest.approx(1/3, rel=1e-3)
    # candidate (info) + unmarked (warning) = 2 violations
    assert len(violations) == 2
    severities = {v["severity"] for v in violations}
    assert "info" in severities    # candidate
    assert "warning" in severities  # missing_marker


def test_structural_authority_coverage_rate_in_run_guard(tmp_path):
    """run_guard authority_coverage_rate.structural reflects promoted sections."""
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    _make_long_term([
        ("Auth Section",
         "<!-- promotion_status: authoritative -->\n"
         "<!-- promoted_by: Gavin / 2026-04-30 -->\n"
         "Confirmed.\n"),
        ("Candidate Section",
         "<!-- promotion_status: candidate -->\n"
         "Proposed.\n"),
    ], memory_root)
    result = run_guard(memory_root, tmp_path, skip_git=True)
    st = result["authority_coverage_rate"]["structural"]
    assert st["total_sections"] == 2
    assert st["promoted_sections"] == 1
    assert st["rate"] == pytest.approx(0.5, rel=1e-3)
