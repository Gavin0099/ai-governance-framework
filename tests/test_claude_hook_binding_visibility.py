"""Claude Code hook installation: SessionStart/SessionEnd, no governance Stop closeout.

Claude Code's Stop fires after every response, not at session end (a real
session here ran the old Stop closeout 44 times).  The installer now manages a
SessionStart (identity, read-back) and a SessionEnd (resumable checkpoint, 5 s)
hook and removes any legacy governance Stop hook.  The safety properties of
the previous installer are kept: unreadable settings are never rewritten,
installation is idempotent, user hooks are preserved, and a governance hook in
another settings scope blocks installation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from governance_tools.manage_agent_closeout import ClaudeAdapter

FRAMEWORK = Path(__file__).resolve().parents[1]
LEGACY_V1 = ("python -c " + "'# governance:claude-closeout-v1\nimport sys\n'")
LEGACY_SHELL = "python E:/external/governance_tools/session_closeout_entry.py --project-root . 2>/dev/null || true"


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    return ClaudeAdapter()


def write_hook(repo, command, name="settings.json", event="Stop"):
    path = repo / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"permissions": {"allow": []}, "hooks": {
        event: [{"hooks": [{"type": "command", "command": command}]}]}}))
    return path


def governance_hooks(data, event):
    return [hook for group in data.get("hooks", {}).get(event, [])
            for hook in group.get("hooks", []) if ClaudeAdapter._is_governance_hook(hook)]


def test_missing_settings_installs_session_start_and_end_only(adapter, tmp_path):
    path = tmp_path / ".claude/settings.json"
    framework = tmp_path / "framework"
    assert adapter.install(tmp_path, framework)["status"] == "installed"
    data = json.loads(path.read_text(encoding="utf-8"))
    (start,) = governance_hooks(data, "SessionStart")
    (end,) = governance_hooks(data, "SessionEnd")
    assert start["command"] == adapter._command(tmp_path, framework, "session_start")
    assert end["command"] == adapter._command(tmp_path, framework, "session_end")
    assert end["timeout"] == 5
    assert "Stop" not in data["hooks"]
    assert adapter.verify(tmp_path, framework)["installed"] is True


@pytest.mark.parametrize("original", [
    pytest.param({"permissions": {"allow": ["Read"], "deny": ["Bash(private)"]}},
                 id="permissions"),
    pytest.param({"hooks": {
        "Stop": [{"matcher": "", "custom_group_key": {"keep": True}, "hooks": [
            {"type": "command", "command": "echo custom-stop", "timeout": 17},
        ]}],
        "SessionStart": [{"hooks": [{"type": "command", "command": "echo custom-start"}]}],
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
        if event == "SessionStart":
            assert data["hooks"][event][:-1] == groups  # user hook kept, ours appended
        else:
            assert data["hooks"][event] == groups  # custom Stop untouched
    assert len(governance_hooks(data, "SessionStart")) == 1
    assert len(governance_hooks(data, "SessionEnd")) == 1
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
    pytest.param(b'{"hooks":{"SessionStart":{}}}', id="non_list_session_start"),
    pytest.param(b'{"hooks":{"SessionEnd":[null]}}', id="non_object_session_end_group"),
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
    ], cwd=FRAMEWORK, capture_output=True, text=True, timeout=30)

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


@pytest.mark.parametrize("legacy", [LEGACY_SHELL, LEGACY_V1], ids=["shell_or_true", "closeout_v1"])
def test_legacy_stop_closeout_is_reported_stale_and_replaced(adapter, tmp_path, legacy):
    path = write_hook(tmp_path, legacy)
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"
    result = adapter.install(tmp_path, tmp_path / "fw")
    assert result["status"] == "installed" and "replaced" in result["message"]
    data = json.loads(path.read_text())
    assert "Stop" not in data["hooks"]  # the governance-only group and event are gone
    assert len(governance_hooks(data, "SessionStart")) == 1
    assert len(governance_hooks(data, "SessionEnd")) == 1
    assert data["permissions"] == {"allow": []}
    assert adapter.verify(tmp_path, tmp_path / "fw")["installed"] is True


def test_wrong_framework_binding_is_replaced_without_duplication(adapter, tmp_path):
    path = write_hook(tmp_path, adapter._command(tmp_path, tmp_path / "old-fw", "session_start"),
                      event="SessionStart")
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    data = json.loads(path.read_text())
    (start,) = governance_hooks(data, "SessionStart")
    assert start["command"] == adapter._command(tmp_path, tmp_path / "fw", "session_start")


def test_wrong_session_end_timeout_is_stale(adapter, tmp_path):
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    path = tmp_path / ".claude/settings.json"
    data = json.loads(path.read_text())
    data["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"] = 60
    path.write_text(json.dumps(data))
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"


def test_similar_text_is_neither_current_nor_deleted(adapter, tmp_path):
    text = "echo session_closeout_entry session_lifecycle.py"
    path = write_hook(tmp_path, text)
    assert adapter.verify(tmp_path, tmp_path)["binding_state"] == "NOT_INSTALLED"
    adapter.install(tmp_path, tmp_path)
    assert json.loads(path.read_text())["hooks"]["Stop"][0]["hooks"][0]["command"] == text


@pytest.mark.parametrize("event", ["Stop", "SessionStart", "SessionEnd"])
def test_override_conflict_does_not_create_second_hook(adapter, tmp_path, event):
    command = LEGACY_SHELL if event == "Stop" else adapter._command(tmp_path, tmp_path / "other", "session_start")
    path = write_hook(tmp_path, command, "settings.local.json", event=event)
    before = path.read_bytes()
    assert adapter.install(tmp_path, tmp_path)["status"] == "blocked"
    assert path.read_bytes() == before
    assert not (tmp_path / ".claude/settings.json").exists()


def consumer_layout(tmp_path, *, markers=True, registration=True, relative="fw"):
    """A consumer layout, with the two stable preconditions independently removable."""
    consumer = tmp_path / "consumer"
    framework = consumer / relative
    framework.mkdir(parents=True)
    if markers:
        (consumer / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
        (consumer / "governance").mkdir()
    if registration:
        (consumer / ".gitmodules").write_text(
            '[submodule "framework"]\n\tpath = ' + relative + "\n\turl = ../framework\n",
            encoding="utf-8")
    return consumer, framework


def test_install_reports_a_layout_that_cannot_run_the_declared_command(adapter, tmp_path):
    """install declares a save-progress command; the layout that rejects it is reported (#257)."""
    consumer, framework = consumer_layout(tmp_path, markers=False, registration=False)
    result = adapter.install(consumer, framework)
    assert result["status"] == "installed"
    readiness = result["closeout_readiness"]
    assert readiness["ready"] is False and readiness["undetermined"] == []
    reasons = " ".join(readiness["unmet"])
    assert "ROOT_BINDING_WOULD_FAIL" in reasons and "AGENTS.md" in reasons
    assert "FRAMEWORK_NOT_REGISTERED_SUBMODULE" in reasons
    assert "cannot be shown to run in this layout" in result["message"]
    assert adapter.verify(consumer, framework)["closeout_readiness"] == readiness


@pytest.mark.parametrize("missing", ["markers", "registration"])
def test_each_precondition_is_reported_on_its_own(adapter, tmp_path, missing):
    consumer, framework = consumer_layout(
        tmp_path, markers=missing != "markers", registration=missing != "registration")
    readiness = adapter.install(consumer, framework)["closeout_readiness"]
    expected = ("ROOT_BINDING_WOULD_FAIL" if missing == "markers"
                else "FRAMEWORK_NOT_REGISTERED_SUBMODULE")
    assert [reason.split(":")[0] for reason in readiness["unmet"]] == [expected]


def test_a_ready_layout_is_reported_without_a_caveat(adapter, tmp_path):
    consumer, framework = consumer_layout(tmp_path)
    result = adapter.install(consumer, framework)
    assert result["closeout_readiness"] == {
        "ready": True, "unmet": [], "undetermined": [],
        "declared_entry": "governance_tools/prepare_closeout_candidate.py"}
    assert "cannot be shown to run" not in result["message"]
    assert adapter.verify(consumer, framework)["note"] == (
        "Configuration binding only; native execution is not verified.")


def test_framework_outside_the_project_is_reported_not_merely_installed(adapter, tmp_path):
    """The external-absolute-path install: status installed, no success path (#257)."""
    consumer, _ = consumer_layout(tmp_path)
    outside = tmp_path / "outside-framework"
    outside.mkdir()
    result = adapter.install(consumer, outside)
    assert result["status"] == "installed"
    assert [reason.split(":")[0] for reason in result["closeout_readiness"]["unmet"]] == [
        "FRAMEWORK_NOT_INSIDE_PROJECT"]


def test_an_unreadable_layout_is_undetermined_not_unmet(adapter, tmp_path, monkeypatch):
    """A layout that could not be read must never be reported as a failed precondition."""
    from governance_tools import manage_agent_closeout as manage
    consumer, framework = consumer_layout(tmp_path)
    monkeypatch.setattr(manage, "_registered_submodule_paths", lambda _consumer: None)
    readiness = manage.closeout_execution_readiness(consumer, framework)
    assert readiness["ready"] is False and readiness["unmet"] == []
    assert [reason.split(":")[0] for reason in readiness["undetermined"]] == [
        "SUBMODULE_REGISTRATION_UNREADABLE"]


def test_uninstall_removes_lifecycle_and_legacy_hooks_only(adapter, tmp_path):
    path = write_hook(tmp_path, LEGACY_SHELL)
    data = json.loads(path.read_text())
    data["hooks"]["PreToolUse"] = [{"hooks": [{"type": "command", "command": "echo custom"}]}]
    path.write_text(json.dumps(data))
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    assert adapter.uninstall(tmp_path)["status"] == "uninstalled"
    after = json.loads(path.read_text())
    assert after["hooks"] == {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo custom"}]}]}
    assert adapter.uninstall(tmp_path)["status"] == "not_found"


# ── the installed commands, executed the way Claude Code runs them ───────────

def _bash():
    bash = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
    if not bash or not Path(bash).exists():
        pytest.skip("Native Bash unavailable")
    return bash


def _git_repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    return path.resolve()


def _run_installed(bash, repo, event, payload):
    command = ClaudeAdapter._command(repo, FRAMEWORK, event)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return subprocess.run([bash, "-c", command], cwd=repo, input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)


def test_installed_commands_start_and_checkpoint_through_bash(tmp_path):
    bash = _bash()
    repo = _git_repo(tmp_path / "repo with spaces")
    base = {"session_id": "a1b2c3d4-0000-4000-8000-000000000001", "cwd": str(repo), "transcript_path": "t"}

    start = _run_installed(bash, repo, "session_start",
                           {**base, "hook_event_name": "SessionStart", "source": "startup"})
    assert start.returncode == 0, start.stderr
    context = json.loads(start.stdout)["hookSpecificOutput"]
    assert context["hookEventName"] == "SessionStart"
    assert "identity=root_bound" in context["additionalContext"]

    end = _run_installed(bash, repo, "session_end",
                         {**base, "hook_event_name": "SessionEnd", "reason": "prompt_input_exit"})
    assert end.returncode == 0, end.stderr
    assert not end.stdout  # SessionEnd output is discarded by Claude Code anyway
    checkpoint = repo / f"artifacts/runtime/session-checkpoints/{base['session_id']}.json"
    assert json.loads(checkpoint.read_text())["trigger_mode"] == "native_hook"
    assert not (repo / "artifacts/runtime/closeout-completions").exists()


def test_installed_command_failure_is_visible_and_never_exit_2(tmp_path):
    bash = _bash()
    repo = _git_repo(tmp_path / "repo")
    other = _git_repo(tmp_path / "other")
    result = _run_installed(bash, repo, "session_start", {
        "session_id": "a1b2c3d4-0000-4000-8000-000000000002", "cwd": str(other),
        "hook_event_name": "SessionStart", "source": "startup", "transcript_path": "t"})
    assert result.returncode == 1
    assert "do not match" in result.stderr
    assert not result.stdout
    assert not (repo / "artifacts").exists() and not (other / "artifacts").exists()
