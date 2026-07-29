from pathlib import Path
import subprocess

from governance_tools.session_end_hook import (
    MEMORY_TIER_NONE,
    STATUS_MISSING,
    STATUS_VALID,
    _build_runtime_contract,
    _derive_daily_memory_write_surface,
    run_session_end_hook,
)
from runtime_hooks.core._canonical_closeout import write_session_envelope


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Memory Truth Test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "memory-truth@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
    )
    marker = repo / "README.md"
    marker.write_text("memory truth fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "test fixture"],
        cwd=repo,
        check=True,
    )


def test_written_daily_memory_is_independent_of_promotion() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "promotion": None,
            "daily_memory_write_attempted": True,
            "daily_memory_write_status": "written",
            "daily_memory_path": "memory/2026-07-28.md",
            "daily_memory_record_identity": "a" * 64,
            "daily_memory_writer": "governance_tools.memory_record",
            "daily_memory_write_error": None,
        },
        closeout_status=STATUS_VALID,
    )

    assert surface["daily_memory_write_status"] == "written"
    assert surface["daily_memory_state_status"] == "satisfied"
    assert surface["memory_update_result"] == "updated"
    assert surface["memory_update_skipped_reason"] is None


def test_already_present_is_satisfied_but_not_updated() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "daily_memory_write_attempted": True,
            "daily_memory_write_status": "already_present",
            "daily_memory_path": "memory/2026-07-28.md",
            "daily_memory_record_identity": "b" * 64,
            "daily_memory_writer": "governance_tools.memory_record",
        },
        closeout_status=STATUS_VALID,
    )

    assert surface["daily_memory_state_status"] == "satisfied"
    assert surface["memory_update_result"] == "skipped"
    assert (
        surface["memory_update_skipped_reason"]
        == "equivalent_record_already_present"
    )


def test_missing_closeout_pre_writer_skip_is_unsatisfied() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "daily_memory_write_expected": True,
            "daily_memory_write_attempted": False,
            "daily_memory_write_status": "skipped",
            "daily_memory_writer": "governance_tools.memory_record",
        },
        closeout_status=STATUS_MISSING,
    )

    assert surface["daily_memory_state_status"] == "unsatisfied"
    assert surface["memory_update_result"] == "skipped"
    assert surface["memory_update_skipped_reason"] == "memory_writer_not_reached"


def test_writer_failure_is_unsatisfied() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "daily_memory_write_attempted": True,
            "daily_memory_write_status": "failed",
            "daily_memory_writer": "governance_tools.memory_record",
            "daily_memory_write_error": (
                "RuntimeError: canonical memory writer failed"
            ),
        },
        closeout_status=STATUS_VALID,
    )

    assert surface["daily_memory_state_status"] == "unsatisfied"
    assert surface["memory_update_result"] == "skipped"
    assert surface["memory_update_skipped_reason"] == "memory_writer_failed"


def test_pre_writer_runtime_failure_is_unsatisfied_without_false_attempt() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "daily_memory_write_expected": True,
            "daily_memory_write_attempted": False,
            "daily_memory_write_status": "skipped",
            "daily_memory_writer": "governance_tools.memory_record",
            "memory_closeout": {"promotion_considered": False},
        },
        closeout_status=STATUS_VALID,
    )

    assert surface["daily_memory_write_attempted"] is False
    assert surface["daily_memory_write_expected"] is True
    assert surface["daily_memory_state_status"] == "unsatisfied"
    assert surface["memory_update_result"] == "skipped"
    assert surface["memory_update_skipped_reason"] == "memory_writer_not_reached"


def test_no_update_promotion_tier_keeps_non_promoting_runtime_contract() -> None:
    contract = _build_runtime_contract({}, MEMORY_TIER_NONE)

    assert contract["memory_mode"] == "stateless"


def test_missing_closeout_writes_fail_closed_daily_record(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    write_session_envelope(
        "missing-closeout-memory-truth",
        tmp_path,
        provider="test",
    )

    result = run_session_end_hook(
        tmp_path,
        hook_session_id="missing-closeout-memory-truth",
        ledger_write_allowed=False,
    )

    assert result["closeout_status"] == STATUS_MISSING
    assert result["daily_memory_write_attempted"] is True
    assert result["daily_memory_write_status"] == "written"
    assert result["daily_memory_state_status"] == "satisfied"
    assert result["memory_update_result"] == "updated"
    assert result["promoted"] is False
    assert result["decision"] == "DO_NOT_PROMOTE"

    daily_memory_path = Path(result["daily_memory_path"])
    assert daily_memory_path.is_file()
    daily_memory = daily_memory_path.read_text(encoding="utf-8")
    assert "FAIL_CLOSED_CLOSEOUT_MISSING" in daily_memory
    assert "canonical_closeout_status=missing" in daily_memory


def test_schema_invalid_closeout_writes_fail_closed_daily_record(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    write_session_envelope(
        "invalid-closeout-memory-truth",
        tmp_path,
        provider="test",
    )

    closeout_path = tmp_path / "artifacts" / "session-closeout.txt"
    closeout_path.parent.mkdir(parents=True, exist_ok=True)
    closeout_path.write_text(
        "TASK_INTENT: incomplete closeout for memory truth replay\n",
        encoding="utf-8",
    )

    result = run_session_end_hook(
        tmp_path,
        hook_session_id="invalid-closeout-memory-truth",
        ledger_write_allowed=False,
    )

    assert result["closeout_status"] == "schema_invalid"
    assert result["daily_memory_write_attempted"] is True
    assert result["daily_memory_write_status"] == "written"
    assert result["daily_memory_state_status"] == "satisfied"
    assert result["memory_update_result"] == "updated"
    assert result["promoted"] is False
    assert result["decision"] == "DO_NOT_PROMOTE"

    daily_memory_path = Path(result["daily_memory_path"])
    assert daily_memory_path.is_file()
    daily_memory = daily_memory_path.read_text(encoding="utf-8")
    assert "FAIL_CLOSED_CLOSEOUT_SCHEMA_INVALID" in daily_memory
    assert "closeout_status=schema_invalid" in daily_memory
    assert "canonical_closeout_status=missing" in daily_memory
