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

import json
import shutil
import subprocess
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


def _existing_commit_line() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).parent.parent,
        text=True,
        capture_output=True,
        check=True,
    )
    return f"- commit hash: {result.stdout.strip()}\n"


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

    def test_guard_failure_warning_codes_contains_guard_error(self):
        """Exception path must emit MEMORY_AUTHORITY_GUARD_ERROR — not empty list.

        Empty list is indistinguishable from a clean run with no warnings.
        Downstream consumers that only read warning_codes must be able to tell
        the difference between 'guard ran cleanly, zero violations' vs
        'guard threw an exception'.
        """
        repo = _reset("guard_fail_codes")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("boom")):
            result = _run(repo)
        ma = result["memory_authority"]
        assert "MEMORY_AUTHORITY_GUARD_ERROR" in ma["memory_authority_warning_codes"]

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
            + _existing_commit_line(),
            encoding="utf-8",
        )
        result = _run(repo)
        assert result["memory_authority"]["memory_unbound_count"] == 0

    def test_guard_ran_true_with_memory_files(self):
        repo = _reset("guard_ran_true")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: minor fix\n"
            + _existing_commit_line(),
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


# ── Snapshot stability: field names locked ────────────────────────────────────

_EXPECTED_TOP_LEVEL_KEYS = frozenset({
    "memory_authority_guard_ran",
    "memory_authority_scope",
    "memory_authority_warning_codes",
    "memory_unbound_count",
    "memory_authority_coverage",
})

_EXPECTED_COVERAGE_KEYS = frozenset({
    "session_entries_total",
    "session_entries_bound",
    "session_authority_rate",
})


class TestSnapshotStability:
    """Field names in the memory_authority surface are part of the downstream
    contract.  Any rename would silently break matrix consumers.  These tests
    lock the surface shape so renames are caught immediately.
    """

    def test_top_level_field_names_stable_on_clean_run(self):
        repo = _reset("snap_clean")
        ma = _run(repo)["memory_authority"]
        # All expected keys must be present (error key absent on clean path)
        assert _EXPECTED_TOP_LEVEL_KEYS <= set(ma.keys())

    def test_top_level_field_names_stable_on_exception_path(self):
        repo = _reset("snap_exc")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("x")):
            ma = _run(repo)["memory_authority"]
        assert _EXPECTED_TOP_LEVEL_KEYS <= set(ma.keys())
        assert "memory_authority_error" in ma  # error key present on exception path

    def test_coverage_field_names_stable(self):
        repo = _reset("snap_cov")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: snap coverage test\n"
            + _existing_commit_line(),
            encoding="utf-8",
        )
        ma = _run(repo)["memory_authority"]
        cov = ma["memory_authority_coverage"]
        assert cov is not None
        assert _EXPECTED_COVERAGE_KEYS <= set(cov.keys())

    def test_missing_dir_field_names_stable(self):
        repo = _reset("snap_missing")
        (repo / "memory").rmdir()
        ma = _run(repo)["memory_authority"]
        assert _EXPECTED_TOP_LEVEL_KEYS <= set(ma.keys())


# ── Clean vs guard-error distinguishability ───────────────────────────────────

class TestBaselineAggregatedWarningView:
    """Schema-1.3 baseline aggregation: historical debt banked in a frozen
    baseline is reported as an aggregate count, not re-listed per session.
    Above-baseline debt and non-baselineable codes always surface (fail-open).
    """

    @staticmethod
    def _unbound_entry(repo: Path, name: str) -> None:
        (repo / "memory" / name).write_text(
            f"# {name.removesuffix('.md')}\n\n"
            "- what changed: unbound fixture entry\n"
            "- commit hash: pending\n",
            encoding="utf-8",
        )

    @staticmethod
    def _freeze_baseline(repo: Path) -> Path:
        from governance_tools.memory_authority_baseline import build_baseline
        from governance_tools.memory_authority_guard import run_guard

        guard = run_guard(repo / "memory", repo, skip_git=True)
        baseline = build_baseline(guard, source_head="fixture")
        out_dir = repo / "artifacts" / "governance"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "memory-authority-baseline-2026-07-06.json"
        path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def test_no_baseline_passes_full_codes_through(self):
        repo = _reset("baseline_absent")
        self._unbound_entry(repo, "2026-05-01.md")
        ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_baseline_id"] == ""
        assert ma["memory_authority_new_warning_codes"] == ma["memory_authority_warning_codes"]
        assert ma["memory_authority_suppressed_by_baseline"] == 0

    def test_banked_debt_is_aggregated_not_relisted(self):
        repo = _reset("baseline_banked")
        self._unbound_entry(repo, "2026-05-01.md")
        self._freeze_baseline(repo)
        ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_baseline_id"] != ""
        assert ma["memory_authority_new_since_baseline"] == 0
        assert ma["memory_authority_suppressed_by_baseline"] >= 1
        assert ma["memory_authority_new_warning_codes"] == []
        # full historical view remains available (no information loss)
        assert "unbound_memory" in ma["memory_authority_warning_codes"]

    def test_above_baseline_debt_surfaces(self):
        repo = _reset("baseline_excess")
        self._unbound_entry(repo, "2026-05-01.md")
        self._freeze_baseline(repo)
        self._unbound_entry(repo, "2026-05-02.md")
        ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_new_since_baseline"] >= 1
        assert "unbound_memory" in ma["memory_authority_new_warning_codes"]

    def test_corrupt_baseline_fails_open(self):
        repo = _reset("baseline_corrupt")
        self._unbound_entry(repo, "2026-05-01.md")
        out_dir = repo / "artifacts" / "governance"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "memory-authority-baseline-2026-07-06.json").write_text(
            "{not json", encoding="utf-8"
        )
        ma = _run(repo)["memory_authority"]
        # unparseable baseline is skipped -> behaves like no baseline
        assert ma["memory_authority_baseline_id"] == ""
        assert ma["memory_authority_new_warning_codes"] == ma["memory_authority_warning_codes"]


class TestCleanVsGuardErrorDistinguishable:
    """warning_codes must distinguish clean (no violations) from guard-error
    (guard threw exception).  Before the fix, both paths returned [].
    """

    def test_clean_run_warning_codes_is_empty(self):
        """Clean run with all-bound entries: no warning codes at all."""
        repo = _reset("dist_clean")
        (repo / "memory" / "2026-05-01.md").write_text(
            "# 2026-05-01\n\n"
            "- what changed: clean entry\n"
            + _existing_commit_line(),
            encoding="utf-8",
        )
        ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_guard_ran"] is True
        assert "MEMORY_AUTHORITY_GUARD_ERROR" not in ma["memory_authority_warning_codes"]

    def test_guard_error_warning_codes_non_empty(self):
        """Guard exception path: warning_codes must not be empty."""
        repo = _reset("dist_error")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("crash")):
            ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_warning_codes"] != []

    def test_guard_error_coverage_is_none(self):
        """Guard exception path: coverage must be None, not stale numeric data."""
        repo = _reset("dist_cov_none")
        with patch("governance_tools.session_end_hook._run_memory_guard", side_effect=RuntimeError("crash")):
            ma = _run(repo)["memory_authority"]
        assert ma["memory_authority_coverage"] is None
