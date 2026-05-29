"""
Memory authority observation surface smoke tests.

Verifies that run_session_end_hook() includes a persistent memory_authority
field so guard output is no longer console-only.

DONE criteria:
  1. memory_authority key present in result
  2. memory_authority_guard_ran is bool
  3. memory_authority_warning_codes is list
  4. memory_unbound_count is int >= 0
  5. memory_authority_coverage is dict or None
  6. guard failure does not break session_end (memory_authority_error recorded)
  7. unbound memory entry produces non-zero memory_unbound_count
  8. memory_authority_scope is "repo"

Non-goals:
  - Does not test guard enforcement (Phase 1 = observation only)
  - Does not test git-based missing_canonical_memory check (skip_git=True)
  - Does not test significance classification
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.session_end_hook import run_session_end_hook

_FIXTURE_ROOT = Path(__file__).parent / "_tmp_memory_authority_surface"


def _reset(name: str) -> Path:
    path = _FIXTURE_ROOT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / "memory").mkdir()
    return path


def _run(repo: Path) -> dict:
    return run_session_end_hook(repo)


# ── Criterion 1-5: surface shape ─────────────────────────────────────────────

class TestMemoryAuthoritySurfaceShape:
    def test_memory_authority_key_present(self):
        repo = _reset("shape_present")
        result = _run(repo)
        assert "memory_authority" in result

    def test_guard_ran_is_bool(self):
        repo = _reset("shape_bool")
        result = _run(repo)
        assert isinstance(result["memory_authority"]["memory_authority_guard_ran"], bool)

    def test_warning_codes_is_list(self):
        repo = _reset("shape_list")
        result = _run(repo)
        assert isinstance(result["memory_authority"]["memory_authority_warning_codes"], list)

    def test_unbound_count_is_int(self):
        repo = _reset("shape_int")
        result = _run(repo)
        assert isinstance(result["memory_authority"]["memory_unbound_count"], int)
        assert result["memory_authority"]["memory_unbound_count"] >= 0

    def test_scope_is_repo(self):
        repo = _reset("shape_scope")
        result = _run(repo)
        assert result["memory_authority"]["memory_authority_scope"] == "repo"

    def test_coverage_is_dict_or_none(self):
        repo = _reset("shape_coverage")
        result = _run(repo)
        cov = result["memory_authority"]["memory_authority_coverage"]
        assert cov is None or isinstance(cov, dict)


# ── Criterion 6: guard failure does not break session_end ─────────────────────

class TestGuardFailureIsolation:
    def test_guard_exception_does_not_raise(self):
        repo = _reset("guard_fail")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("boom")):
            result = _run(repo)
        assert "memory_authority" in result
        ma = result["memory_authority"]
        assert ma["memory_authority_guard_ran"] is False
        assert "memory_authority_error" in ma
        assert "boom" in ma["memory_authority_error"]

    def test_guard_failure_does_not_affect_ok(self):
        repo = _reset("guard_fail_ok")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("fail")):
            result = _run(repo)
        # ok may be True or False depending on closeout — what matters is no exception raised
        assert "ok" in result


# ── Criterion 7: unbound memory entry detection ───────────────────────────────

class TestUnboundMemoryDetection:
    def test_empty_memory_dir_produces_zero_unbound(self):
        repo = _reset("unbound_zero")
        result = _run(repo)
        assert result["memory_authority"]["memory_unbound_count"] == 0

    def test_unbound_entry_produces_nonzero_count(self):
        repo = _reset("unbound_nonzero")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: added feature X to src/x.py\n"
            "- commit hash: pending\n",
            encoding="utf-8",
        )
        result = _run(repo)
        assert result["memory_authority"]["memory_unbound_count"] >= 1

    def test_bound_entry_does_not_increment_unbound_count(self):
        repo = _reset("unbound_bound")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: added feature Y to src/y.py\n"
            "- commit hash: abc1234\n",
            encoding="utf-8",
        )
        result = _run(repo)
        assert result["memory_authority"]["memory_unbound_count"] == 0

    def test_guard_ran_true_with_memory_files(self):
        repo = _reset("guard_ran_true")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: minor fix\n"
            "- commit hash: def5678\n",
            encoding="utf-8",
        )
        result = _run(repo)
        assert result["memory_authority"]["memory_authority_guard_ran"] is True


# ── Criterion 8: missing memory dir handled gracefully ────────────────────────

class TestMissingMemoryDir:
    def test_missing_memory_dir_guard_ran_false(self):
        repo = _reset("missing_dir")
        (repo / "memory").rmdir()  # remove the dir
        result = _run(repo)
        ma = result["memory_authority"]
        assert ma["memory_authority_guard_ran"] is False
        assert ma.get("memory_authority_error") == "memory_root_missing"
        assert ma["memory_unbound_count"] == 0
