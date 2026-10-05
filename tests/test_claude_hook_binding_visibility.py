import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

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


def test_missing_settings_creates_governance_stop_hook(adapter, tmp_path):
    path = tmp_path / ".claude/settings.json"
    framework = tmp_path / "framework"
    assert not path.exists()

    assert adapter.install(tmp_path, framework)["status"] == "installed"

    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = [hook for group in data["hooks"]["Stop"] for hook in group["hooks"]]
    assert len(hooks) == 1
    assert hooks[0]["command"] == adapter._command(tmp_path, framework)
    assert adapter.verify(tmp_path, framework)["installed"] is True


@pytest.mark.parametrize("original", [
    pytest.param({"permissions": {"allow": ["Read"], "deny": ["Bash(private)"]}},
                 id="permissions"),
    pytest.param({"hooks": {
        "Stop": [{"matcher": "", "custom_group_key": {"keep": True}, "hooks": [
            {"type": "command", "command": "echo custom-stop", "timeout": 17},
        ]}],
        "PreToolUse": [{"hooks": [{"type": "command", "command": "echo custom-pre"}]}],
    }}, id="custom_hooks"),
    pytest.param({"unknown_key": {"nested": [False, None, {"keep": "unchanged"}]},
                  "env": {"CUSTOM_SETTING": "preserved"}}, id="unknown_top_level"),
])
def test_valid_utf8_settings_preserved_and_install_idempotent(adapter, tmp_path, original):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    path.write_text(json.dumps(original), encoding="utf-8")
    framework = tmp_path / "framework"

    assert adapter.install(tmp_path, framework)["status"] == "installed"

    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in original.items():
        if key != "hooks":
            assert data[key] == value
    for event, groups in original.get("hooks", {}).items():
        if event == "Stop":
            assert data["hooks"][event][:-1] == groups
        else:
            assert data["hooks"][event] == groups
    governance_hooks = [hook for group in data["hooks"]["Stop"] for hook in group["hooks"]
                        if adapter._is_governance_hook(hook)]
    assert len(governance_hooks) == 1
    assert governance_hooks[0]["command"] == adapter._command(tmp_path, framework)
    before_retry = path.read_bytes()
    assert adapter.install(tmp_path, framework)["status"] == "already_installed"
    assert path.read_bytes() == before_retry


@pytest.mark.parametrize("payload", [
    pytest.param(b'\xef\xbb\xbf{"permissions":{"deny":["Bash(private)"]}}', id="utf8_bom"),
    pytest.param(b'{"permissions":{"deny":["Bash(private)"]}', id="malformed_json"),
    pytest.param(b'{"unknown_key":"\xff"}', id="invalid_utf8"),
    pytest.param(b'[]', id="non_object_settings"),
    pytest.param(b'{"hooks":[]}', id="non_object_hooks"),
    pytest.param(b'{"hooks":{"Stop":{}}}', id="non_list_stop"),
    pytest.param(b'{"hooks":{"Stop":[null]}}', id="non_object_stop_group"),
    pytest.param(b'{"hooks":{"Stop":[{"hooks":{}}]}}', id="non_list_group_hooks"),
])
def test_invalid_existing_settings_blocked_without_writes(adapter, tmp_path, payload):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    path.write_bytes(payload)

    result = adapter.install(tmp_path, tmp_path / "framework")

    assert (result["status"], path.read_bytes()) == ("blocked", payload)
    assert result["location"] == str(path)
    assert "settings" in result["message"].lower()
    assert "not modified" in result["message"].lower()
    assert list(path.parent.iterdir()) == [path]


def test_settings_read_error_blocked_without_writes(adapter, tmp_path, monkeypatch):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    original = b'{"permissions":{"deny":["Bash(private)"]}}'
    path.write_bytes(original)
    read_text = Path.read_text

    def fail_target_read(candidate, *args, **kwargs):
        if candidate == path:
            raise PermissionError("settings read denied")
        return read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_target_read)
    result = adapter.install(tmp_path, tmp_path / "framework")

    assert result["status"] == "blocked"
    assert "settings read denied" in result["message"]
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


def test_settings_parser_recursion_error_blocked_without_writes(adapter, tmp_path, monkeypatch):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    original = b'{"permissions":{"deny":["Bash(private)"]}}'
    path.write_bytes(original)

    def parser_failure(_content):
        raise RecursionError("settings nesting exceeds parser limit")

    with monkeypatch.context() as patch:
        patch.setattr(json, "loads", parser_failure)
        result = adapter.install(tmp_path, tmp_path / "framework")

    assert result["status"] == "blocked"
    assert result["location"] == str(path)
    assert "not modified" in result["message"].lower()
    assert "parser limit" in result["message"]
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


def test_deep_settings_cli_returns_structured_failure_without_writes(tmp_path):
    path = tmp_path / ".claude/settings.json"
    path.parent.mkdir()
    original = b'{"unknown_key":' + b'[' * 5000 + b'0' + b']' * 5000 + b'}'
    path.write_bytes(original)

    result = subprocess.run([
        sys.executable, "-B", "-m", "governance_tools.manage_agent_closeout",
        "--project-root", str(tmp_path), "--format", "json", "install", "--agent", "claude",
    ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)

    assert result.returncode == 1
    assert result.stdout, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["location"] == str(path)
    assert "not modified" in payload["message"].lower()
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


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
