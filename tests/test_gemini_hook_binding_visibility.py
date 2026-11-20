"""Gemini CLI hook installation: SessionStart/SessionEnd, explicit formal closeout.

Gemini CLI treats SessionEnd as best-effort on exit, and HookRunner measures
timeouts in milliseconds. The installer manages a SessionStart (identity,
read-back) and a SessionEnd (resumable checkpoint, 5,000 ms) hook in
.gemini/settings.json and removes any legacy governance SessionEnd closeout
hook (including legacy flat hook dicts without the outer {"hooks": [...]}
wrapper). Unreadable settings are never rewritten, installation is idempotent,
user hooks are preserved, and a governance hook in ~/.gemini/settings.json
blocks installation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from governance_tools import adopt_governance, manage_agent_closeout
from governance_tools.copilot_instructions_projection import extract_projection_region
from governance_tools.manage_agent_closeout import GeminiAdapter, _PENDING_HOOK_NOTE

FRAMEWORK = Path(__file__).resolve().parents[1]
LEGACY_SHELL = "python E:/external/governance_tools/session_closeout_entry.py --project-root . 2>/dev/null || true"


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    return GeminiAdapter()


def write_hook(repo, command, name="settings.json", event="SessionEnd", *, flat=False):
    path = repo / ".gemini" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "timeout": 30} if flat else {"hooks": [{"type": "command", "command": command}]}
    path.write_text(json.dumps({"security": {"auth": {}}, "hooks": {event: [entry]}}), encoding="utf-8")
    return path


def governance_hooks(data, event):
    found = []
    for group in data.get("hooks", {}).get(event, []):
        if not isinstance(group, dict):
            continue
        if "hooks" not in group and GeminiAdapter._is_governance_hook(group):
            found.append(group)
            continue
        for hook in group.get("hooks", []):
            if GeminiAdapter._is_governance_hook(hook):
                found.append(hook)
    return found


@pytest.mark.parametrize("hooks_already_installed", [False, True])
def test_gemini_only_install_projects_formal_closeout_guidance(
    adapter, tmp_path, monkeypatch, capsys, hooks_already_installed
):
    repo = tmp_path / "Gemini consumer"
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    assert adopt_governance.adopt_existing(repo, FRAMEWORK) == 0
    capsys.readouterr()
    gemini = repo / "GEMINI.md"
    agents = repo / "AGENTS.md"
    assert not gemini.exists()
    original_agents = agents.read_text(encoding="utf-8")
    assert "Formal Closeout on Request" not in original_agents

    if hooks_already_installed:
        settings = repo / ".gemini/settings.json"
        settings.parent.mkdir()
        hooks = adapter._expected_hooks(repo, FRAMEWORK)
        settings.write_text(json.dumps({"hooks": {
            event: [{"hooks": [hook]}] for event, hook in hooks.items()
        }}), encoding="utf-8")
        gemini.write_text("# Consumer Gemini instructions\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "manage_agent_closeout", "--project-root", str(repo), "--format", "json",
        "install", "--agent", "gemini",
    ])
    assert manage_agent_closeout.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == ("already_installed" if hooks_already_installed else "installed")
    assert "GEMINI.md and AGENTS.md" in result["message"]
    assert adapter.verify(repo, FRAMEWORK)["installed"]

    for path in (gemini, agents):
        guidance = path.read_text(encoding="utf-8")
        assert guidance.count("Formal Closeout on Request") == 1
        assert "governance_tools/prepare_closeout_candidate.py" in guidance
        assert "governance_tools.gemini_formal_closeout --owner-request" in guidance
    assert agents.read_text(encoding="utf-8").startswith(original_agents.rstrip())
    if hooks_already_installed:
        assert gemini.read_text(encoding="utf-8").startswith("# Consumer Gemini instructions\n")
    assert not (repo / "CLAUDE.md").exists()
    assert not (repo / ".github/copilot-instructions.md").exists()
    assert not (repo / ".github/hooks").exists()


def test_gemini_install_reuses_starter_pack_checkpoint_projection(adapter, tmp_path):
    target = tmp_path / "GEMINI.md"
    starter = (FRAMEWORK / "examples/starter-pack/GEMINI.md").read_bytes()
    target.write_bytes(starter)
    original_projection = extract_projection_region(starter.decode("utf-8"))[:2]

    assert adapter.install(tmp_path, FRAMEWORK)["status"] == "installed"
    installed = target.read_bytes()
    assert extract_projection_region(installed.decode("utf-8"))[:2] == original_projection
    assert installed.startswith(starter)
    assert b"governance_tools.gemini_formal_closeout --owner-request" in installed
    assert adapter.install(tmp_path, FRAMEWORK)["status"] == "already_installed"
    assert target.read_bytes() == installed


def test_missing_settings_installs_session_start_and_end_with_ms_timeout(adapter, tmp_path):
    path = tmp_path / ".gemini/settings.json"
    framework = tmp_path / "framework"
    assert adapter.install(tmp_path, framework)["status"] == "installed"
    data = json.loads(path.read_text(encoding="utf-8"))
    (start,) = governance_hooks(data, "SessionStart")
    (end,) = governance_hooks(data, "SessionEnd")
    assert start["type"] == "command"
    assert start["command"] == adapter._command(tmp_path, framework, "session_start")
    assert end["type"] == "command"
    assert end["command"] == adapter._command(tmp_path, framework, "session_end")
    assert end["timeout"] == 5000
    verify = adapter.verify(tmp_path, framework)
    assert verify["installed"] is True
    assert _PENDING_HOOK_NOTE not in verify["note"]
    assert "closeout is left to" not in verify["note"]


@pytest.mark.parametrize("original", [
    pytest.param({"security": {"auth": {"selectedType": "oauth-personal"}}}, id="security"),
    pytest.param({"hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "echo custom-start"}]}],
        "BeforeTool": [{"hooks": [{"type": "command", "command": "echo custom-pre"}]}],
    }}, id="custom_hooks"),
    pytest.param({"unknown_key": {"nested": [False, None, {"keep": "unchanged"}]},
                  "general": {"vimMode": False}}, id="unknown_top_level"),
])
def test_valid_utf8_settings_preserved_and_install_idempotent(adapter, tmp_path, original):
    path = tmp_path / ".gemini/settings.json"
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
            assert data["hooks"][event][:-1] == groups
        else:
            assert data["hooks"][event] == groups
    assert len(governance_hooks(data, "SessionStart")) == 1
    assert len(governance_hooks(data, "SessionEnd")) == 1
    before_retry = path.read_bytes()
    assert adapter.install(tmp_path, framework)["status"] == "already_installed"
    assert path.read_bytes() == before_retry


@pytest.mark.parametrize("payload", [
    pytest.param(b'\xef\xbb\xbf{"general":{"vimMode":false}}', id="utf8_bom"),
    pytest.param(b'{"general":{"vimMode":false}', id="malformed_json"),
    pytest.param(b'{"unknown_key":"\xff"}', id="invalid_utf8"),
    pytest.param(b'[]', id="non_object_settings"),
    pytest.param(b'{"hooks":[]}', id="non_object_hooks"),
    pytest.param(b'{"hooks":{"SessionStart":{}}}', id="non_list_session_start"),
    pytest.param(b'{"hooks":{"SessionEnd":[null]}}', id="non_object_session_end_group"),
    pytest.param(b'{"hooks":{"SessionEnd":[{"hooks":{}}]}}', id="non_list_group_hooks"),
])
def test_invalid_existing_settings_blocked_without_writes(adapter, tmp_path, payload):
    path = tmp_path / ".gemini/settings.json"
    path.parent.mkdir()
    path.write_bytes(payload)

    result = adapter.install(tmp_path, tmp_path / "framework")

    assert (result["status"], path.read_bytes()) == ("blocked", payload)
    assert result["location"] == str(path)
    assert "settings" in result["message"].lower()
    assert "not modified" in result["message"].lower()
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("flat", [False, True], ids=["grouped_legacy", "flat_legacy"])
def test_legacy_session_end_closeout_is_reported_stale_and_replaced(adapter, tmp_path, flat):
    path = write_hook(tmp_path, LEGACY_SHELL, flat=flat)
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"
    result = adapter.install(tmp_path, tmp_path / "fw")
    assert result["status"] == "installed" and "replaced" in result["message"]
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(governance_hooks(data, "SessionStart")) == 1
    assert len(governance_hooks(data, "SessionEnd")) == 1
    assert data["security"] == {"auth": {}}
    assert adapter.verify(tmp_path, tmp_path / "fw")["installed"] is True


def test_wrong_session_end_timeout_is_stale(adapter, tmp_path):
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    path = tmp_path / ".gemini/settings.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"] = 30
    path.write_text(json.dumps(data), encoding="utf-8")
    assert adapter.verify(tmp_path, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"


def test_user_home_conflict_blocks_install(adapter, tmp_path):
    home_settings = tmp_path / "home" / ".gemini" / "settings.json"
    home_settings.parent.mkdir(parents=True)
    home_settings.write_text(json.dumps({
        "hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": LEGACY_SHELL}]}]}
    }), encoding="utf-8")
    before = home_settings.read_bytes()
    assert adapter.install(tmp_path, tmp_path)["status"] == "blocked"
    assert home_settings.read_bytes() == before
    assert not (tmp_path / ".gemini/settings.json").exists()


def test_uninstall_removes_lifecycle_and_legacy_hooks_only(adapter, tmp_path):
    path = write_hook(tmp_path, LEGACY_SHELL, flat=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["BeforeTool"] = [{"hooks": [{"type": "command", "command": "echo custom"}]}]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    assert adapter.uninstall(tmp_path)["status"] == "uninstalled"
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["hooks"] == {"BeforeTool": [{"hooks": [{"type": "command", "command": "echo custom"}]}]}
    assert adapter.uninstall(tmp_path)["status"] == "not_found"


def test_print_manual_shows_gemini_formal_closeout(adapter, tmp_path):
    manual = adapter.print_manual(tmp_path)
    assert "gemini_formal_closeout.py" in manual
    assert "--owner-request" in manual
    assert "--authorization-ref" in manual
    assert "install --agent gemini" in manual


def _git_repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    return path.resolve()


def _run_installed_powershell(repo, event, payload):
    if os.name != "nt":
        pytest.skip("Windows PowerShell hook execution test")
    command = GeminiAdapter._command(repo, FRAMEWORK, event)
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    # Exact wrapper used by Gemini CLI HookRunner.executeCommandHook on Windows:
    ps_cmd = f"{command}; if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}"
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        cwd=repo, input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", timeout=60, env=env,
    )


def test_installed_commands_start_and_checkpoint_through_gemini_windows_shell(tmp_path):
    repo = _git_repo(tmp_path / "repo with spaces")
    base = {"session_id": "a1b2c3d4-0000-4000-8000-000000000021", "cwd": str(repo), "transcript_path": "t"}

    start = _run_installed_powershell(
        repo, "session_start", {**base, "hook_event_name": "SessionStart", "source": "startup"}
    )
    assert start.returncode == 0, start.stderr
    context = json.loads(start.stdout)["hookSpecificOutput"]
    assert context["hookEventName"] == "SessionStart"
    assert "identity=root_bound" in context["additionalContext"]

    end = _run_installed_powershell(
        repo, "session_end", {**base, "hook_event_name": "SessionEnd", "reason": "exit"}
    )
    assert end.returncode == 0, end.stderr
    assert not end.stdout
    checkpoint = repo / f"artifacts/runtime/session-checkpoints/{base['session_id']}.json"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["trigger_mode"] == "native_hook"
    assert not (repo / "artifacts/runtime/closeout-completions").exists()


def test_installed_command_failure_is_visible_and_never_exit_2(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    other = _git_repo(tmp_path / "other")
    result = _run_installed_powershell(repo, "session_start", {
        "session_id": "a1b2c3d4-0000-4000-8000-000000000022", "cwd": str(other),
        "hook_event_name": "SessionStart", "source": "startup", "transcript_path": "t",
    })
    assert result.returncode == 1
    assert "do not match" in result.stderr
    assert not result.stdout
    assert not (repo / "artifacts").exists() and not (other / "artifacts").exists()


def test_single_quote_in_project_path_executes_through_gemini_windows_shell(adapter, tmp_path):
    repo = _git_repo(tmp_path / "Author's Project")
    assert adapter.install(repo, FRAMEWORK)["status"] == "installed"
    assert adapter.verify(repo, FRAMEWORK)["installed"] is True

    base = {"session_id": "a1b2c3d4-0000-4000-8000-000000000023", "cwd": str(repo), "transcript_path": "t"}
    start = _run_installed_powershell(
        repo, "session_start", {**base, "hook_event_name": "SessionStart", "source": "startup"}
    )
    assert start.returncode == 0, start.stderr
    context = json.loads(start.stdout)["hookSpecificOutput"]
    assert "identity=root_bound" in context["additionalContext"]

    end = _run_installed_powershell(
        repo, "session_end", {**base, "hook_event_name": "SessionEnd", "reason": "exit"}
    )
    assert end.returncode == 0, end.stderr
    checkpoint = repo / f"artifacts/runtime/session-checkpoints/{base['session_id']}.json"
    assert checkpoint.is_file()


def test_gemini_cli_home_env_var_controls_user_settings_scope(adapter, tmp_path, monkeypatch):
    custom_home = tmp_path / "custom-gemini-home"
    custom_settings = custom_home / ".gemini" / "settings.json"
    custom_settings.parent.mkdir(parents=True)
    custom_settings.write_text(json.dumps({
        "hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": LEGACY_SHELL}]}]}
    }), encoding="utf-8")

    monkeypatch.setenv("GEMINI_CLI_HOME", str(custom_home))
    repo = tmp_path / "repo"
    repo.mkdir()
    assert adapter.verify(repo, tmp_path / "fw")["binding_state"] == "STALE_OR_WRONG_BINDING"
    blocked = adapter.install(repo, tmp_path / "fw")
    assert blocked["status"] == "blocked"
    assert blocked["location"] == str(custom_settings)


def test_uninstall_ignores_malformed_null_hooks_group_without_type_error(adapter, tmp_path):
    assert adapter.install(tmp_path, tmp_path / "fw")["status"] == "installed"
    path = tmp_path / ".gemini/settings.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["SessionEnd"].insert(0, {"hooks": None})
    path.write_text(json.dumps(data), encoding="utf-8")

    res = adapter.uninstall(tmp_path)
    assert res["status"] == "uninstalled"
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["hooks"] == {"SessionEnd": [{"hooks": None}]}
