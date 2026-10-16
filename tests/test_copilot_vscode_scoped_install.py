from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import hook_installer as installer
from governance_tools.hook_install_validator import _vscode_hook_config_safe


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = Path(".github/hooks/ai-governance-lifecycle.py")
CONFIG = Path(".github/hooks/ai-governance-vscode.json")
MANIFEST = Path(".github/hooks/.ai-governance-managed.json")


@pytest.fixture
def targets(tmp_path):
    repo = tmp_path / "consumer with spaces"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    framework = repo / "SubModule" / "framework with spaces"
    for rel in (
        "runtime_hooks/adapters/copilot/lifecycle.py",
        "governance/copilot-hooks-vscode-template.json",
        "governance/copilot-hooks-session-end-template.json",
    ):
        target = framework / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    marker = framework / "governance_tools/session_end_hook.py"
    marker.parent.mkdir(parents=True)
    marker.write_text("raise AssertionError('core must not execute in dry-run')\n")
    envelope_marker = framework / "runtime_hooks/core/_canonical_closeout.py"
    envelope_marker.parent.mkdir(parents=True)
    envelope_marker.write_text("raise AssertionError('envelope must not execute in dry-run')\n")
    return repo, framework


def legacy_entry(event_type="session_end"):
    return {"type": "command", "command": (
        f"python .github/hooks/ai-governance-lifecycle.py --event-type {event_type} --surface auto"
    ), "timeout": 30}


def snapshot(repo):
    return {p.relative_to(repo): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in repo.rglob("*") if p.is_file() and ".git" not in p.relative_to(repo).parts}


def test_only_three_surfaces_and_preserves_legacy_and_instructions(targets):
    repo, framework = targets
    protected = (
        ".github/hooks/session-end.json", ".github/hooks/ai-governance-copilot.json",
        "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md",
        ".codex/hooks.json", ".claude/settings.json",
    )
    for name in protected:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"consumer-owned\r\n")
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok, result.errors
    assert {Path(p).relative_to(repo) for p in result.changed_files} == {BRIDGE, CONFIG, MANIFEST}
    for name in protected:
        assert (repo / name).read_bytes() == b"consumer-owned\r\n"
    assert json.loads((repo / CONFIG).read_text())["hooks"] == {}
    assert _vscode_hook_config_safe(repo / CONFIG)


def test_does_not_create_second_session_end_and_is_idempotent(targets):
    repo, framework = targets
    assert installer.install_copilot_vscode_lifecycle(repo, framework).ok
    before = snapshot(repo)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok
    assert result.changed_files == result.backups == []
    assert snapshot(repo) == before
    assert not (repo / ".github/hooks/ai-governance-copilot.json").exists()


@pytest.mark.parametrize("bound", [False, True])
def test_upgrade_retires_only_legacy_entries_and_preserves_custom_hooks(targets, bound):
    repo, framework = targets
    entry = legacy_entry()
    if bound:
        entry.update(env={"AI_GOVERNANCE_FRAMEWORK_ROOT": "old framework"}, cwd="old consumer")
    custom = {"type": "command", "command": "python my-stop.py", "windows": "custom.exe"}
    config = {"version": 1, "customMetadata": {"owner": "consumer"}, "hooks": {
        "Stop": [entry, custom], "UserPromptSubmit": [{"type": "command", "command": "echo mine"}],
        "SessionStart": [legacy_entry("session_start")],
    }}
    (repo / CONFIG).parent.mkdir(parents=True)
    original = (json.dumps(config, indent=4) + "\r\n").encode()
    (repo / CONFIG).write_bytes(original)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok, result.errors
    repaired = json.loads((repo / CONFIG).read_text())
    assert repaired == {**config, "hooks": {"Stop": [custom], "UserPromptSubmit": config["hooks"]["UserPromptSubmit"]}}
    assert any(Path(p).read_bytes() == original for p in result.backups)
    assert _vscode_hook_config_safe(repo / CONFIG)
    before = snapshot(repo)
    again = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert again.ok and again.changed_files == again.backups == []
    assert snapshot(repo) == before


def test_custom_only_config_keeps_exact_bytes(targets):
    repo, framework = targets
    (repo / CONFIG).parent.mkdir(parents=True)
    original = b'{"version":1,"hooks":{"Stop":[{"command":"my-cleanup"}]},"mine":true}\r\n'
    (repo / CONFIG).write_bytes(original)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok, result.errors
    assert (repo / CONFIG).read_bytes() == original
    assert result.backups == []


@pytest.mark.parametrize("entry", [
    {"type": "command", "command": "echo done", "env": {"DOC_NOTE": "ai-governance-lifecycle.py"}},
    {"type": "command", "command": "echo done", "cwd": "C:/notes/ai-governance-lifecycle.py"},
    {"type": "command", "command": "echo ai-governance-lifecycle.py retired"},
])
def test_bridge_name_in_custom_data_is_not_lifecycle_wiring(targets, entry):
    repo, framework = targets
    (repo / CONFIG).parent.mkdir(parents=True)
    original = (json.dumps({"version": 1, "hooks": {"Stop": [entry]}}) + "\r\n").encode()
    (repo / CONFIG).write_bytes(original)
    assert _vscode_hook_config_safe(repo / CONFIG)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok, result.errors
    assert (repo / CONFIG).read_bytes() == original


@pytest.mark.parametrize("raw", [
    '{"version":1,"hooks":{"UserPromptSubmit":[{"command":"echo first"}],'
    '"UserPromptSubmit":[{"command":"echo second"}],"Stop":[' + json.dumps(legacy_entry()) + ']}}',
    '{"version":1,"mine":1,"mine":2,"hooks":{"Stop":[]}}',
    '{"version":1,"hooks":{"Stop":[],"Stop":[]}}',
    '{"version":1,"hooks":{"Stop":[{"command":"echo first","command":"echo second"}]}}',
])
def test_duplicate_keys_are_rejected_and_preserved(targets, raw):
    repo, framework = targets
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text(raw)
    before = snapshot(repo)
    assert not _vscode_hook_config_safe(repo / CONFIG)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert not result.ok and any("duplicate" in error for error in result.errors)
    assert snapshot(repo) == before


@pytest.mark.parametrize("command", [
    "echo note; python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto",
    "echo $(python .github/hooks/ai-governance-lifecycle.py --event-type session_end)",
    "Write-Output (python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto)",
    "echo ai-governance-lifecycle.py >(python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto)",
])
def test_shell_execution_is_not_mistaken_for_pure_echo(targets, command):
    repo, framework = targets
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text(json.dumps({"version": 1, "hooks": {"Stop": [{"command": command}]}}))
    before = snapshot(repo)
    assert not _vscode_hook_config_safe(repo / CONFIG)
    assert not installer.install_copilot_vscode_lifecycle(repo, framework).ok
    assert snapshot(repo) == before


@pytest.mark.parametrize("raw", ["{", "[]", '{"version":true,"hooks":{}}', '{"version":1,"hooks":[]}',
    '{"version":1,"hooks":{"Stop":{}}}', json.dumps({"version": 1, "hooks": {"Stop": [
        {**legacy_entry(), "windows": "custom.exe"}]}})])
def test_unknown_or_malformed_consumer_config_fails_without_writes(targets, raw):
    repo, framework = targets
    (repo / CONFIG).parent.mkdir(parents=True)
    (repo / CONFIG).write_text(raw)
    before = snapshot(repo)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert not result.ok and result.errors
    assert result.changed_files == result.backups == []
    assert snapshot(repo) == before


def test_genuine_session_end_bridge_remains_available(targets):
    repo, framework = targets
    assert installer.install_copilot_vscode_lifecycle(repo, framework).ok
    genuine = json.loads((framework / "governance/copilot-hooks-session-end-template.json").read_text())
    assert set(genuine["hooks"]) == {"sessionStart", "sessionEnd"}
    assert "--event-type session_end" in genuine["hooks"]["sessionEnd"][0]["command"]
    result = subprocess.run(
        [sys.executable, str(repo / BRIDGE), "--event-type", "session_end", "--surface", "auto", "--dry-run"],
        input=json.dumps({"session_id": "genuine-end", "cwd": str(repo), "hook_event_name": "sessionEnd"}),
        cwd=repo, env={**os.environ, "AI_GOVERNANCE_FRAMEWORK_ROOT": str(framework)}, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["would_invoke_session_end"] is True


@pytest.mark.parametrize("raw", ["not json", "[]", '{"hooks":{}}', '{"version":true,"hooks":{}}',
    '{"version":2,"hooks":{}}', json.dumps({"version": 1, "hooks": {"Stop": [legacy_entry()]}})])
@pytest.mark.parametrize("existing", [False, True])
def test_invalid_source_fails_before_deployment(targets, raw, existing):
    repo, framework = targets
    if existing:
        assert installer.install_copilot_vscode_lifecycle(repo, framework).ok
    source = framework / "governance/copilot-hooks-vscode-template.json"
    source.write_text(raw)
    before = snapshot(repo)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert not result.ok and result.errors
    assert result.changed_files == result.installed_files == result.backups == []
    assert snapshot(repo) == before


@pytest.mark.parametrize("missing", ["runtime_hooks/adapters/copilot/lifecycle.py", "governance/copilot-hooks-vscode-template.json"])
def test_missing_source_fails_before_deployment(targets, missing):
    repo, framework = targets
    (framework / missing).unlink()
    before = snapshot(repo)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert not result.ok and result.errors
    assert result.changed_files == result.backups == []
    assert snapshot(repo) == before


def test_public_cli_routes_to_scoped_installer(targets, capsys):
    repo, framework = targets
    assert installer.main(["--repo", str(repo), "--framework-root", str(framework), "--copilot-vscode-only", "--format", "json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["changed_files"]) == 3
    assert not (repo / ".github/hooks/ai-governance-copilot.json").exists()


@pytest.mark.parametrize("flag", ["--copilot-only", "--hooks-only", "--identity-config-only", "--copilot-instructions-only"])
def test_scoped_mode_rejects_other_install_modes(targets, flag):
    repo, framework = targets
    with pytest.raises(SystemExit) as exc:
        installer.main(["--repo", str(repo), "--framework-root", str(framework), "--copilot-vscode-only", flag])
    assert exc.value.code == 2
