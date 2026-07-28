from governance_tools.session_end_hook import (
    STATUS_MISSING,
    STATUS_VALID,
    _derive_daily_memory_write_surface,
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


def test_missing_closeout_keeps_current_stateless_skip_policy() -> None:
    surface = _derive_daily_memory_write_surface(
        {
            "daily_memory_write_expected": False,
            "daily_memory_write_attempted": False,
            "daily_memory_write_status": "skipped",
            "daily_memory_writer": "governance_tools.memory_record",
        },
        closeout_status=STATUS_MISSING,
    )

    assert surface["daily_memory_state_status"] == "not_required"
    assert surface["memory_update_result"] == "skipped"
    assert (
        surface["memory_update_skipped_reason"]
        == "missing_session_closeout_artifact"
    )


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
