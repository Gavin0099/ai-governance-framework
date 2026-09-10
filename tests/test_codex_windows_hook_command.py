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
    assert not CodexCLIAdapter._is_current_hook(hook)


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
