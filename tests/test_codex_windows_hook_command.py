import base64
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from governance_tools.manage_agent_closeout import CodexCLIAdapter


def test_literal_transport_and_posix_unchanged(tmp_path):
    hook = CodexCLIAdapter._hook_payload(tmp_path)
    command = hook["commandWindows"]
    assert "$" not in command
    script = base64.b64decode(command.split()[-1]).decode("utf-16-le")
    assert "if (-not $python)" in script
    assert "Test-Path $_" in script
    assert "exit $LASTEXITCODE" in script
    assert hook["timeout"] == 30
    entry = (tmp_path / "governance_tools/session_closeout_entry.py").as_posix()
    args = f'"{entry}" --format json --agent-id codex --trigger-mode native_hook'
    assert hook["command"] == (
        'repo_root="$(git rev-parse --show-toplevel)" && '
        f'if [ -x "$repo_root/.venv/bin/python" ]; then "$repo_root/.venv/bin/python" {args} '
        f'--project-root "$repo_root"; else python3 {args} --project-root "$repo_root"; fi'
    )


def test_old_windows_command_is_replaced_once(tmp_path):
    adapter = CodexCLIAdapter()
    hook = adapter._hook_payload(tmp_path)
    script = base64.b64decode(hook["commandWindows"].split()[-1]).decode("utf-16-le")
    hook["commandWindows"] = 'powershell -NoProfile -Command "& { ' + script + ' }"'
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [hook]}]}}))
    assert adapter.install(tmp_path, tmp_path)["status"] == "installed"
    after = path.read_bytes()
    assert adapter.install(tmp_path, tmp_path)["status"] == "already_installed"
    assert path.read_bytes() == after
    hooks = json.loads(after)["hooks"]
    assert list(hooks) == ["Stop"]
    assert len(hooks["Stop"][0]["hooks"]) == 1


@pytest.mark.parametrize("encoded", ["!invalid!", "YQ=="])
def test_invalid_encoded_command_is_not_current(tmp_path, encoded):
    hook = CodexCLIAdapter._hook_payload(tmp_path)
    hook["commandWindows"] = "powershell -NoProfile -EncodedCommand " + encoded
    assert not CodexCLIAdapter._is_current_hook(hook, tmp_path)


def assert_requested_framework_binding(payload, framework_root):
    hooks = [hook for group in payload["hooks"]["Stop"] for hook in group["hooks"]]
    governance_hooks = [hook for hook in hooks
                        if "session_closeout_entry.py" in hook.get("command", "")]
    assert len(governance_hooks) == 1
    hook = governance_hooks[0]
    entry = (framework_root / "governance_tools/session_closeout_entry.py").as_posix()
    assert f'"{entry}"' in hook["command"]
    windows_script = base64.b64decode(hook["commandWindows"].split()[-1]).decode("utf-16-le")
    assert f"& $python '{entry}' --project-root $repo" in windows_script
    return hook


@pytest.mark.parametrize("operation", ["install", "repair"])
@pytest.mark.parametrize("moved", [False, True], ids=["old_root_exists", "old_root_missing"])
def test_stale_framework_binding_is_replaced_and_custom_hooks_preserved(tmp_path, operation, moved):
    adapter = CodexCLIAdapter()
    project = tmp_path / "consumer"
    old_root = tmp_path / "framework-a"
    new_root = tmp_path / "framework-b"
    old_entry = old_root / "governance_tools/session_closeout_entry.py"
    old_entry.parent.mkdir(parents=True)
    old_entry.write_text("# isolated fixture\n", encoding="utf-8")
    assert adapter.install(project, old_root)["status"] == "installed"
    path = project / ".codex/hooks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    custom = {"type": "command", "command": "echo custom-stop", "timeout": 7}
    data["hooks"]["Stop"][0]["hooks"].append(custom)
    data["hooks"]["SessionStart"] = [{"hooks": [{"type": "command", "command": "echo custom-start"}]}]
    data["unknown_setting"] = {"preserve": [True, None, "value"]}
    path.write_text(json.dumps(data), encoding="utf-8")
    if moved:
        old_root.rename(new_root)
        assert not old_root.exists()
    else:
        new_entry = new_root / "governance_tools/session_closeout_entry.py"
        new_entry.parent.mkdir(parents=True)
        new_entry.write_text("# isolated fixture\n", encoding="utf-8")
        assert old_root.exists()

    before_verify = path.read_bytes()
    assert adapter.verify(project, new_root)["installed"] is False
    assert path.read_bytes() == before_verify
    result = getattr(adapter, operation)(project, new_root)
    assert result["status"] == "installed"
    if operation == "repair":
        assert result["repaired"] is True
    repaired = json.loads(path.read_text(encoding="utf-8"))
    hook = assert_requested_framework_binding(repaired, new_root)
    assert old_entry.as_posix() not in hook["command"]
    windows_script = base64.b64decode(hook["commandWindows"].split()[-1]).decode("utf-16-le")
    assert old_entry.as_posix() not in windows_script
    assert repaired["hooks"]["Stop"][0]["hooks"][0] == custom
    assert repaired["hooks"]["SessionStart"] == data["hooks"]["SessionStart"]
    assert repaired["unknown_setting"] == data["unknown_setting"]
    assert adapter.verify(project, new_root)["installed"] is True
    before_retry = path.read_bytes()
    assert adapter.install(project, new_root)["status"] == "already_installed"
    assert adapter.repair(project, new_root)["status"] == "no_repair_needed"
    assert path.read_bytes() == before_retry


@pytest.mark.parametrize("stale_field", ["command", "commandWindows"])
def test_mixed_platform_framework_binding_is_not_current_and_repair_rebinds_both(tmp_path, stale_field):
    adapter = CodexCLIAdapter()
    framework = tmp_path / "framework"
    other = tmp_path / "other-framework"
    hook = adapter._hook_payload(framework)
    hook[stale_field] = adapter._hook_payload(other)[stale_field]
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [hook]}]}}), encoding="utf-8")

    before_verify = path.read_bytes()
    assert adapter.verify(tmp_path, framework)["installed"] is False
    assert path.read_bytes() == before_verify
    assert adapter.repair(tmp_path, framework)["status"] == "installed"
    assert_requested_framework_binding(json.loads(path.read_text(encoding="utf-8")), framework)
    assert adapter.verify(tmp_path, framework)["installed"] is True


@pytest.mark.parametrize("duplicate_is_current", [True, False], ids=["both_current", "mixed_roots"])
def test_duplicate_governance_hooks_repair_to_one_binding(tmp_path, duplicate_is_current):
    adapter = CodexCLIAdapter()
    framework = tmp_path / "framework"
    duplicate_root = framework if duplicate_is_current else tmp_path / "old-framework"
    custom = {"type": "command", "command": "echo preserve-custom"}
    payload = {"hooks": {"Stop": [
        {"hooks": [adapter._hook_payload(framework)]},
        {"hooks": [custom, adapter._hook_payload(duplicate_root)], "custom_group_key": "keep"},
    ]}}
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert adapter.verify(tmp_path, framework)["installed"] is False
    assert adapter.repair(tmp_path, framework)["status"] == "installed"
    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert_requested_framework_binding(repaired, framework)
    assert repaired["hooks"]["Stop"][1] == {"hooks": [custom], "custom_group_key": "keep"}
    before_retry = path.read_bytes()
    assert adapter.repair(tmp_path, framework)["status"] == "no_repair_needed"
    assert path.read_bytes() == before_retry


@pytest.mark.parametrize("operation", ["install", "repair"])
@pytest.mark.parametrize("custom_command", [
    "echo session_closeout_entry.py",
    'echo "{entry}"',
    'echo python "{entry}"',
    "python C:/custom-tools/session_closeout_entry.py --custom-purpose",
    "python session_closeout_entry.py --custom-purpose",
    "powershell -NoProfile -EncodedCommand " + base64.b64encode(
        "& $python 'C:/custom-tools/session_closeout_entry.py' --custom-purpose".encode("utf-16-le")
    ).decode("ascii"),
    'repo_root="$(git rev-parse --show-toplevel)" && '
    'if [ -x "$repo_root/.venv/bin/python" ]; then "$repo_root/.venv/bin/python" '
    'C:/custom-tools/session_closeout_entry.py --custom-purpose; else python3 '
    'C:/custom-tools/session_closeout_entry.py --custom-purpose; fi',
], ids=["filename-mention", "path-mention", "python-mention",
        "custom-executable-path", "custom-executable-relative",
        "custom-executable-windows", "custom-executable-posix"])
def test_closeout_text_in_custom_hook_is_preserved(tmp_path, operation, custom_command):
    adapter = CodexCLIAdapter()
    framework = tmp_path / "framework"
    entry = (framework / "governance_tools/session_closeout_entry.py").as_posix()
    custom = {"type": "command", "command": custom_command.format(entry=entry), "timeout": 7}
    current = adapter._hook_payload(framework)
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    data = {"hooks": {"Stop": [{"hooks": [current, custom]}]}}
    path.write_text(json.dumps(data), encoding="utf-8")

    before = path.read_bytes()
    assert adapter.verify(tmp_path, framework)["installed"] is True
    expected = "already_installed" if operation == "install" else "no_repair_needed"
    assert getattr(adapter, operation)(tmp_path, framework)["status"] == expected
    assert path.read_bytes() == before

    data["hooks"]["Stop"][0]["hooks"][0] = adapter._hook_payload(tmp_path / "old-framework")
    path.write_text(json.dumps(data), encoding="utf-8")
    assert adapter.verify(tmp_path, framework)["installed"] is False
    assert getattr(adapter, operation)(tmp_path, framework)["status"] == "installed"
    hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]["Stop"][0]["hooks"]
    assert hooks == [custom, current]
    assert adapter.verify(tmp_path, framework)["installed"] is True
    before_retry = path.read_bytes()
    assert getattr(adapter, operation)(tmp_path, framework)["status"] == expected
    assert path.read_bytes() == before_retry


@pytest.mark.skipif(os.name != "nt", reason="Windows native shell regression")
@pytest.mark.parametrize("exit_code", [0, 7])
def test_outer_powershell_reaches_python_with_space_paths(tmp_path, exit_code):
    repo = tmp_path / "consumer with spaces"
    framework = repo / "framework's space path"
    entry = framework / "governance_tools/session_closeout_entry.py"
    entry.parent.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    entry.write_text(
        "import json, pathlib, sys\n"
        "pathlib.Path('invocation.json').write_text(json.dumps({'argv': sys.argv, 'python': sys.executable}))\n"
        f"sys.exit({exit_code})\n", encoding="utf-8"
    )
    hook = CodexCLIAdapter._hook_payload(framework)
    result = subprocess.run(
        [shutil.which("powershell.exe"), "-NoProfile", "-Command",
         hook["commandWindows"] + "; exit $LASTEXITCODE"],
        cwd=repo, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == exit_code, result.stderr
    assert "ParserError" not in result.stderr
    invocation = json.loads((repo / "invocation.json").read_text())
    assert Path(invocation["argv"][0]).resolve() == entry.resolve()
    assert Path(invocation["argv"][2]).resolve() == repo.resolve()
    assert invocation["argv"][3:] == ["--format", "json", "--agent-id", "codex", "--trigger-mode", "native_hook"]
    assert Path(invocation["python"]).is_file()
