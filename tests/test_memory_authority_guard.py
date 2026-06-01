"""
Unit tests for governance_tools/memory_authority_guard.py

Coverage target: non_canonical_writer check (check_daily_memory)

Test cases:
  A. canonical writer entry          → no non_canonical_writer violation
  B. manual session-derived entry    → non_canonical_writer violation
  C. manual non-session-derived      → no non_canonical_writer violation
  D. pre-cutoff old-format entry     → grandfathered (no non_canonical_writer)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.memory_authority_guard import check_daily_memory

# ── helpers ───────────────────────────────────────────────────────────────────

POST_CUTOFF = "2026-05-15.md"
PRE_CUTOFF  = "2026-04-15.md"

CANONICAL_ENTRY = """\
- memory_type: session-derived
  writer: governance_tools.memory_record
  record_format_version: 1.0
  commit: abc1234def5
  session_id: test-session-001
  what_changed: verified canonical writer path
  next_step: none
"""

MANUAL_SESSION_DERIVED_ENTRY = """\
- memory_type: session-derived
  what_changed: manually appended session entry
  commit: abc1234def5
"""

MANUAL_HUMAN_NOTE_ENTRY = """\
- memory_type: human-note
  what_changed: human curated note about the project
"""

OLD_FORMAT_ENTRY = """\
- what_changed: completed some task
  commit: abc1234def5
"""


def _write_daily(memory_root: Path, filename: str, content: str) -> None:
    (memory_root / filename).write_text(content, encoding="utf-8")


def _violation_codes(violations: list) -> list[str]:
    return [v["code"] for v in violations]


# ── A. Canonical writer passes ────────────────────────────────────────────────

class TestCanonicalWriterPasses:
    def test_no_non_canonical_writer_violation(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, CANONICAL_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], f"unexpected non_canonical_writer violations: {ncw}"


# ── B. Manual session-derived fails ───────────────────────────────────────────

class TestManualSessionDerivedFails:
    def test_non_canonical_writer_violation_raised(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, MANUAL_SESSION_DERIVED_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert len(ncw) >= 1, "expected non_canonical_writer violation for manual session-derived entry"
        assert ncw[0]["severity"] == "warning"

    def test_violation_reason_identifies_canonical_writer_requirement(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, MANUAL_SESSION_DERIVED_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert any("session_derived" in v["reason"] for v in ncw)


# ── C. Manual non-session-derived is ignored ──────────────────────────────────

class TestManualNonSessionDerivedIgnored:
    def test_human_note_memory_type_not_flagged(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, MANUAL_HUMAN_NOTE_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], f"human-note entry must not trigger non_canonical_writer: {ncw}"


# ── D. Pre-cutoff old-format is grandfathered ─────────────────────────────────

class TestPreCutoffGrandfathered:
    def test_old_format_entry_before_cutoff_not_flagged(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, PRE_CUTOFF, OLD_FORMAT_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], (
            f"pre-cutoff old-format entries are grandfathered and must not "
            f"trigger non_canonical_writer: {ncw}"
        )

    def test_same_old_format_post_cutoff_is_flagged(self, tmp_path):
        """Contrast: same format in a post-cutoff file IS flagged."""
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, OLD_FORMAT_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert len(ncw) >= 1, (
            "old-format entries in post-cutoff files must trigger non_canonical_writer"
        )
