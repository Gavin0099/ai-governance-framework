import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from governance_tools.manage_agent_closeout import ClaudeAdapter


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    return ClaudeAdapter()


def write_hook(repo, command, name="settings.json"):
    path = repo / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"permissions": {"allow": []}, "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": command}]}]}}))
    return path


def test_correct_binding_is_idempotent(adapter, tmp_path):
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    path = tmp_path / ".claude/settings.json"
    before = path.read_bytes()
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "CORRECTLY_INSTALLED"
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "already_installed"
    assert path.read_bytes() == before


def test_wrong_external_binding_is_replaced_without_duplication(adapter, tmp_path):
    path = write_hook(tmp_path, "python E:/external/governance_tools/session_closeout_entry.py --project-root . 2>/dev/null || true")
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    data = json.loads(path.read_text())
    hooks = [h for g in data["hooks"]["Stop"] for h in g["hooks"]]
    assert len(hooks) == 1
    assert hooks[0]["command"] == adapter._command(tmp_path, tmp_path / "fw")
    assert data["permissions"] == {"allow": []}
    assert "|| true" not in hooks[0]["command"]
    assert "2>/dev/null" not in hooks[0]["command"]


def test_similar_text_is_neither_current_nor_deleted(adapter, tmp_path):
    text = "echo session_closeout_entry"
    path = write_hook(tmp_path, text)
    assert adapter.verify(tmp_path, tmp_path)["binding_state"] == "NOT_INSTALLED"
    adapter.install(tmp_path, tmp_path)
    assert json.loads(path.read_text())["hooks"]["Stop"][0]["hooks"][0]["command"] == text


def test_override_conflict_does_not_create_second_hook(adapter, tmp_path):
    path = write_hook(tmp_path, adapter._command(tmp_path, tmp_path / "other"), "settings.local.json")
    before = path.read_bytes()
    assert adapter.install(tmp_path, tmp_path)["status"] == "blocked"
    assert path.read_bytes() == before
    assert not (tmp_path / ".claude/settings.json").exists()


@pytest.mark.parametrize("code,ok,expected", [(0, True, 0), (1, False, 1), (2, False, 1), (7, False, 1), (0, False, 1)])
def test_native_shell_failure_translation_and_stderr(adapter, tmp_path, code, ok, expected):
    repo = tmp_path / "repo with spaces"
    framework = repo / "framework's path"
    entry = framework / "governance_tools/session_closeout_entry.py"
    entry.parent.mkdir(parents=True)
    entry.write_text(
        "import json,sys,pathlib\n"
        "pathlib.Path('invocation.json').write_text(json.dumps({'argv':sys.argv, 'stdin':sys.stdin.read()}))\n"
        "sys.stderr.write('known-error\\n')\n"
        f"print(json.dumps({{'ok': {ok!r}, 'decision': 'block'}}))\n"
        f"sys.exit({code})\n"
    )
    bash = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
    if not bash or not Path(bash).exists():
        pytest.skip("Native Bash unavailable")
    result = subprocess.run([bash, "-c", adapter._command(repo, framework)], cwd=repo,
                            input='{"hook_event_name":"Stop"}', capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == expected, result.stderr
    assert "known-error" in result.stderr
    assert not result.stdout  # core JSON must not become Claude decision control
    record = json.loads((repo / "invocation.json").read_text())
    assert Path(record["argv"][0]).resolve() == entry.resolve()
    assert Path(record["argv"][2]).resolve() == repo.resolve()
    assert record["stdin"] == '{"hook_event_name":"Stop"}'
    assert record["argv"][3:] == ["--format", "json", "--agent-id", "claude", "--trigger-mode", "native_hook"]
