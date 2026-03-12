import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_hooks.adapters.claude_code.normalize_event import normalize_event as normalize_claude
from runtime_hooks.adapters.codex.normalize_event import normalize_event as normalize_codex
from runtime_hooks.adapters.gemini.normalize_event import normalize_event as normalize_gemini


def test_claude_normalize_event_maps_common_aliases():
    payload = {
        "cwd": "/repo",
        "prompt": "Add runtime hooks",
        "active_rules": "common,python",
        "risk_level": "high",
        "oversight_mode": "review-required",
        "memory": "candidate",
        "hook_event_name": "PreToolUse",
        "session_id": "2026-03-12-01",
    }
    normalized = normalize_claude(payload, "pre_task")
    assert normalized["project_root"] == "/repo"
    assert normalized["task"] == "Add runtime hooks"
    assert normalized["rules"] == ["common", "python"]
    assert normalized["metadata"]["harness"] == "claude_code"


def test_codex_normalize_event_maps_post_task_fields():
    payload = {
        "workspace": "/repo",
        "task": "Review output",
        "rules": ["common", "python"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "output_file": "out.txt",
        "run_id": "run-123",
    }
    normalized = normalize_codex(payload, "post_task")
    assert normalized["response_file"] == "out.txt"
    assert normalized["create_snapshot"] is True
    assert normalized["metadata"]["harness"] == "codex"


def test_gemini_normalize_event_uses_safe_defaults():
    payload = {
        "repo_root": "/repo",
        "title": "Implement memory policy",
    }
    normalized = normalize_gemini(payload, "pre_task")
    assert normalized["risk"] == "medium"
    assert normalized["oversight"] == "review-required"
    assert normalized["memory_mode"] == "candidate"
    assert normalized["metadata"]["harness"] == "gemini"
