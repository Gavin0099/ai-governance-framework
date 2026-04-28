import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.host_agent_memory_sync_signal import evaluate_memory_sync_signal


def test_required_event_without_host_sync_emits_missing_signal():
    result = evaluate_memory_sync_signal(
        event_level="memory_sync_required",
        repo_memory_written=True,
        host_memory_applicable=True,
        host_sync_completed=False,
    )

    assert result.ok is False
    assert result.signal == "memory_sync_missing"
    assert result.severity == "warning"


def test_required_event_with_non_applicable_host_memory_emits_info_signal():
    result = evaluate_memory_sync_signal(
        event_level="memory_sync_required",
        repo_memory_written=True,
        host_memory_applicable=False,
        host_sync_completed=False,
    )

    assert result.ok is True
    assert result.signal == "host_memory_not_applicable"
    assert result.severity == "info"


def test_optional_event_with_repo_memory_only_emits_repo_only_signal():
    result = evaluate_memory_sync_signal(
        event_level="memory_sync_optional",
        repo_memory_written=True,
        host_memory_applicable=True,
        host_sync_completed=False,
    )

    assert result.ok is True
    assert result.signal == "repo_memory_written_only"
    assert result.severity == "info"


def test_repo_only_event_without_repo_memory_write_emits_no_signal():
    result = evaluate_memory_sync_signal(
        event_level="repo_memory_only",
        repo_memory_written=False,
        host_memory_applicable=True,
        host_sync_completed=False,
    )

    assert result.ok is True
    assert result.signal is None


def test_completed_host_sync_clears_any_signal_need():
    result = evaluate_memory_sync_signal(
        event_level="memory_sync_required",
        repo_memory_written=True,
        host_memory_applicable=True,
        host_sync_completed=True,
    )

    assert result.ok is True
    assert result.signal is None
