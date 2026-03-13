import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.smoke_test import run_smoke
from runtime_hooks.smoke_test import run_shared_smoke


def test_smoke_test_claude_pre_runs():
    envelope = run_smoke("claude_code", "pre_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "pre_task"


def test_smoke_test_codex_post_runs_and_creates_snapshot():
    envelope = run_smoke("codex", "post_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["event_type"] == "post_task"
    assert envelope["result"]["snapshot"] is not None


def test_smoke_test_gemini_post_runs():
    envelope = run_smoke("gemini", "post_task")
    assert envelope["result"]["ok"] is True
    assert envelope["normalized_event"]["metadata"]["harness"] == "gemini"


def test_smoke_test_session_start_shared_runs():
    envelope = run_shared_smoke("session_start")
    assert envelope["result"]["ok"] is True
    assert envelope["event_type"] == "session_start"
    assert envelope["result"]["suggested_agent"] == "python-agent"
