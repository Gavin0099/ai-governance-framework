"""
Unit tests for governance_tools/memory_authority_guard.py

Coverage target: non_canonical_writer check (check_daily_memory)

Test cases:
  A. canonical writer entry          → no non_canonical_writer violation
  B. manual session-derived entry    → non_canonical_writer violation
  C. manual non-session-derived      → no non_canonical_writer violation unless session-shaped
  D. pre-cutoff old-format entry     → grandfathered (no non_canonical_writer)
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.memory_authority_guard import (
    check_daily_memory,
    filter_active_non_canonical_writer_violations,
)

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

SESSION_LIKE_NOTE_ENTRY = """\
- memory_type: note
  record_format_version: 1.0
  writer: manual.editor
  what_changed: mislabeled session entry
  commit: abc1234def5
  memory_binding: bound
  test_evidence: not relevant
  next_step: none
"""

OLD_FORMAT_ENTRY = """\
- what_changed: completed some task
  commit: abc1234def5
"""

# Claude Code's actual direct-write format (space, not underscore)
CLAUDE_CODE_DIRECT_ENTRY = """\
- what changed: added some feature
- commit hash: abc1234def5
- test evidence: manual
- next step: none
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

    def test_session_shaped_note_reports_bypass_warning(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-09.md", SESSION_LIKE_NOTE_ENTRY)
        violations, _ = check_daily_memory(mem)

        bypass = [
            v
            for v in violations
            if v["code"] == "session_like_non_session_memory_type"
        ]

        assert len(bypass) == 1
        assert bypass[0]["severity"] == "warning"
        assert "non_session_memory_type_with_session_fields:note" in bypass[0]["reason"]

    def test_session_shaped_note_before_active_window_is_grandfathered(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-01.md", SESSION_LIKE_NOTE_ENTRY)
        violations, _ = check_daily_memory(mem)

        bypass = [
            v
            for v in violations
            if v["code"] == "session_like_non_session_memory_type"
        ]

        assert bypass == []


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


# ── E. Claude Code direct-write format (regression) ──────────────────────────

class TestClaudeCodeDirectWriteFlagged:
    """Regression: Claude Code's '- what changed:' (space) direct-write format
    must be flagged as non_canonical_writer in post-cutoff files."""

    def test_claude_code_direct_write_is_flagged(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, POST_CUTOFF, CLAUDE_CODE_DIRECT_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert len(ncw) >= 1, (
            "Claude Code direct '- what changed:' format must trigger non_canonical_writer"
        )
        assert any(
            "old_format_entry_after_canonical_writer_cutoff" in v["reason"]
            for v in ncw
        )

    def test_claude_code_direct_write_pre_cutoff_is_grandfathered(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, PRE_CUTOFF, CLAUDE_CODE_DIRECT_ENTRY)
        violations, _ = check_daily_memory(mem)
        ncw = [v for v in violations if v["code"] == "non_canonical_writer"]
        assert ncw == [], (
            "pre-cutoff direct-write entries are grandfathered and must not be flagged"
        )


class TestActiveNonCanonicalWriterSentinel:
    def test_filter_ignores_historical_non_canonical_writer(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-01.md", CLAUDE_CODE_DIRECT_ENTRY)
        violations, _ = check_daily_memory(mem)

        active = filter_active_non_canonical_writer_violations(
            violations,
            active_from="2026-06-02",
        )

        assert active == []

    def test_filter_flags_active_non_canonical_writer(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-02.md", CLAUDE_CODE_DIRECT_ENTRY)
        violations, _ = check_daily_memory(mem)

        active = filter_active_non_canonical_writer_violations(
            violations,
            active_from="2026-06-02",
        )

        assert len(active) == 1
        assert active[0]["file"] == "2026-06-02.md"

    def test_cli_fail_flag_exits_nonzero_for_active_violation(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-03.md", CLAUDE_CODE_DIRECT_ENTRY)

        completed = subprocess.run(
            [
                sys.executable,
                "governance_tools/memory_authority_guard.py",
                "--memory-root",
                str(mem),
                "--project-root",
                str(tmp_path),
                "--skip-git",
                "--fail-on-active-non-canonical-writer",
                "--active-from",
                "2026-06-02",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 2
        assert '"count": 1' in completed.stdout

    def test_cli_fail_flag_allows_historical_only_violation(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        _write_daily(mem, "2026-06-01.md", CLAUDE_CODE_DIRECT_ENTRY)

        completed = subprocess.run(
            [
                sys.executable,
                "governance_tools/memory_authority_guard.py",
                "--memory-root",
                str(mem),
                "--project-root",
                str(tmp_path),
                "--skip-git",
                "--fail-on-active-non-canonical-writer",
                "--active-from",
                "2026-06-02",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0
        assert '"count": 0' in completed.stdout

    def test_fixture_reports_active_non_canonical_writer_without_blocking(self):
        fixture_memory = (
            Path(__file__).parent
            / "fixtures"
            / "memory_authority"
            / "active_non_canonical_writer"
            / "memory"
        )

        completed = subprocess.run(
            [
                sys.executable,
                "governance_tools/memory_authority_guard.py",
                "--memory-root",
                str(fixture_memory),
                "--project-root",
                str(fixture_memory.parent),
                "--skip-git",
                "--active-from",
                "2026-06-08",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0
        payload = json.loads(completed.stdout)
        active = payload["active_non_canonical_writer"]
        assert payload["mode"] == "warning"
        assert payload["ok"] is True
        assert active["mode"] == "report_only"
        assert active["count"] == 1
        assert active["violations"][0]["file"] == "2026-06-09.md"
        assert active["violations"][0]["code"] == "non_canonical_writer"
