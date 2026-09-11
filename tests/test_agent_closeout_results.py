"""Installation refusals must survive repair and CLI result aggregation."""

import json
import sys
from pathlib import Path

import pytest

from governance_tools import manage_agent_closeout as manager


@pytest.mark.parametrize("operation", ["install", "repair"])
def test_claude_conflict_returns_failure_without_changing_settings(
    tmp_path, monkeypatch, capsys, operation
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    adapter = manager.ClaudeAdapter()
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{
        "type": "command",
        "command": adapter._command(tmp_path, tmp_path / "other-framework"),
    }]}]}}), encoding="utf-8")
    before = settings.read_bytes()
    monkeypatch.setattr(sys, "argv", [
        "manage_agent_closeout", "--project-root", str(tmp_path),
        "--format", "json", operation, "--agent", "claude",
    ])

    code = manager.main()
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "blocked"
    assert code == 1
    if operation == "repair":
        assert result["repaired"] is False
    assert settings.read_bytes() == before
    assert not (settings.parent / "settings.json").exists()


@pytest.mark.parametrize("status,expected", [
    ("blocked", False), ("error", False), ("manual_only", False),
    ("installed", True), ("already_installed", False),
])
def test_default_repair_reports_install_outcome(tmp_path, monkeypatch, status, expected):
    adapter = manager.ClaudeAdapter()
    monkeypatch.setattr(adapter, "verify", lambda *_: {"installed": False})
    monkeypatch.setattr(adapter, "install", lambda *_: {
        "status": status, "location": "candidate", "message": "retained detail",
    })
    result = adapter.repair(tmp_path, tmp_path)
    assert result["repaired"] is expected
    assert result["status"] == status
    assert result["message"] == "retained detail"


@pytest.mark.parametrize("operation", ["install", "repair"])
@pytest.mark.parametrize("selection", ["claude", "all"])
@pytest.mark.parametrize("status,expected_code", [
    ("blocked", 1), ("error", 1), ("installed", 0),
    ("already_installed", 0), ("manual_only", 0), ("no_repair_needed", 0),
])
def test_cli_preserves_failure_and_nonfailure_statuses(
    tmp_path, monkeypatch, capsys, operation, selection, status, expected_code
):
    class ResultAdapter:
        def __init__(self, agent_id):
            self.agent_id = agent_id

        def install(self, *_):
            return {"agent": self.agent_id, "status": (
                status if self.agent_id == "claude" else "manual_only"
            )}

        repair = install

    monkeypatch.setattr(manager, "get_adapter", ResultAdapter)
    monkeypatch.setattr(sys, "argv", [
        "manage_agent_closeout", "--project-root", str(tmp_path),
        "--format", "json", operation, "--agent", selection,
    ])
    assert manager.main() == expected_code
    result = json.loads(capsys.readouterr().out)
    rows = result if isinstance(result, list) else [result]
    agents = manager.KNOWN_AGENTS if selection == "all" else ["claude"]
    assert rows == [
        {"agent": agent, "status": status if agent == "claude" else "manual_only"}
        for agent in agents
    ]


@pytest.mark.parametrize("verification", [
    {"installed": True}, {"installed": False, "manual_only": True},
])
def test_no_repair_needed_does_not_install(tmp_path, monkeypatch, verification):
    adapter = manager.ClaudeAdapter()
    monkeypatch.setattr(adapter, "verify", lambda *_: verification)

    def unexpected_install(*_):
        pytest.fail("No-op repair must not invoke install")

    monkeypatch.setattr(adapter, "install", unexpected_install)
    assert adapter.repair(tmp_path, tmp_path)["status"] == "no_repair_needed"
