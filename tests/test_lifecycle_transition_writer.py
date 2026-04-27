from governance_tools.lifecycle_transition_writer import (
    state_can_unblock_release,
    validate_lifecycle_transition,
)


def test_rejects_direct_active_to_resolved_confirmed():
    result = validate_lifecycle_transition(
        from_state="active",
        to_state="resolved_confirmed",
        actor="reviewer_confirmed",
        auto=False,
    )

    assert result["ok"] is False
    assert "transition_not_allowed" in result["errors"]
    assert "active_to_resolved_confirmed_forbidden" in result["errors"]


def test_rejects_auto_write_to_resolved_confirmed():
    result = validate_lifecycle_transition(
        from_state="resolved_provisional",
        to_state="resolved_confirmed",
        actor="reviewer_confirmed",
        auto=True,
    )

    assert result["ok"] is False
    assert "resolved_confirmed_auto_write_forbidden" in result["errors"]


def test_rejects_author_provisional_confirming_resolution():
    result = validate_lifecycle_transition(
        from_state="resolved_provisional",
        to_state="resolved_confirmed",
        actor="author_provisional",
        auto=False,
    )

    assert result["ok"] is False
    assert "author_provisional_cannot_confirm_resolution" in result["errors"]
    assert "resolved_confirmed_requires_reviewer_confirmation" in result["errors"]


def test_allows_reviewer_confirmed_resolution_transition():
    result = validate_lifecycle_transition(
        from_state="resolved_provisional",
        to_state="resolved_confirmed",
        actor="reviewer_confirmed",
        auto=False,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["release_unblock_allowed"] is True


def test_only_resolved_confirmed_can_unblock_release():
    assert state_can_unblock_release("resolved_confirmed") is True
    assert state_can_unblock_release("resolved_provisional") is False
    assert state_can_unblock_release("active") is False
    assert state_can_unblock_release("invalidated") is False
