from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import hook_installer as installer


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
    # Root-discovery marker only; dry-run never imports or executes this stub.
    marker = framework / "governance_tools/session_end_hook.py"
    marker.parent.mkdir(parents=True)
    marker.write_text("raise AssertionError('core must not execute in dry-run')\n")
    envelope_marker = framework / "runtime_hooks/core/_canonical_closeout.py"
    envelope_marker.parent.mkdir(parents=True)
    envelope_marker.write_text("raise AssertionError('envelope must not execute in dry-run')\n")
    return repo, framework


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
    assert result.backups == []
    for name in protected:
        assert (repo / name).read_bytes() == b"consumer-owned\r\n"
    config = json.loads((repo / CONFIG).read_text())
    assert set(config["hooks"]) == {"Stop"}
    entry = config["hooks"]["Stop"][0]
    assert entry["command"] == "python .github/hooks/ai-governance-lifecycle.py --event-type session_end --surface auto"
    assert entry["timeout"] == 30
    assert entry["env"]["AI_GOVERNANCE_FRAMEWORK_ROOT"] == str(framework.resolve())
    assert (repo / BRIDGE).read_bytes() == (framework / "runtime_hooks/adapters/copilot/lifecycle.py").read_bytes()


def test_does_not_create_second_session_end_and_is_idempotent(targets):
    repo, framework = targets
    assert installer.install_copilot_vscode_lifecycle(repo, framework).ok
    before = {p: (repo / p).stat().st_mtime_ns for p in (BRIDGE, CONFIG, MANIFEST)}
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok
    assert result.changed_files == result.backups == []
    assert before == {p: (repo / p).stat().st_mtime_ns for p in before}
    assert not (repo / ".github/hooks/ai-governance-copilot.json").exists()
    assert not (repo / ".github/hooks/session-end.json").exists()


def test_wrong_binding_replaced_with_backup_and_manifest_tracks_output(targets):
    repo, framework = targets
    installer.install_copilot_vscode_lifecycle(repo, framework)
    config = json.loads((repo / CONFIG).read_text())
    config["hooks"]["Stop"][0]["env"]["AI_GOVERNANCE_FRAMEWORK_ROOT"] = "wrong framework"
    wrong = json.dumps(config).encode()
    (repo / CONFIG).write_bytes(wrong)
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert result.ok
    assert CONFIG in {Path(p).relative_to(repo) for p in result.changed_files}
    assert any(Path(p).read_bytes() == wrong for p in result.backups)
    entry = json.loads((repo / CONFIG).read_text())["hooks"]["Stop"][0]
    assert entry["env"]["AI_GOVERNANCE_FRAMEWORK_ROOT"] == str(framework.resolve())
    manifest = installer._read_managed_manifest(repo)
    assert manifest[CONFIG.as_posix()] == hashlib.sha256((repo / CONFIG).read_text().replace("\r\n", "\n").strip().encode()).hexdigest()


def test_emitted_environment_overrides_stale_binding_in_actual_bridge_dry_run(targets):
    repo, framework = targets
    assert installer.install_copilot_vscode_lifecycle(repo, framework).ok
    entry = json.loads((repo / CONFIG).read_text())["hooks"]["Stop"][0]
    env = {**os.environ, "AI_GOVERNANCE_FRAMEWORK_ROOT": "wrong", **entry["env"]}
    result = subprocess.run(
        [sys.executable, str(repo / BRIDGE), "--event-type", "session_end", "--surface", "auto", "--dry-run"],
        input=json.dumps({"session_id": "scope-probe", "cwd": str(repo), "hook_event_name": "Stop"}),
        cwd=entry["cwd"], env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert Path(output["framework_root"]) == framework.resolve()
    assert output["would_invoke_session_end"] is True
    assert output["would_write_session_envelope"] is False


@pytest.mark.parametrize("invalid", ["missing_bridge", "missing_config", "invalid_json", "extra_event"])
def test_invalid_source_fails_before_deployment(targets, invalid):
    repo, framework = targets
    config = framework / "governance/copilot-hooks-vscode-template.json"
    if invalid == "missing_bridge":
        (framework / "runtime_hooks/adapters/copilot/lifecycle.py").unlink()
    elif invalid == "missing_config":
        config.unlink()
    elif invalid == "invalid_json":
        config.write_text("not json")
    else:
        config.write_text('{"hooks":{"Stop":[],"SessionStart":[]}}')
    result = installer.install_copilot_vscode_lifecycle(repo, framework)
    assert not result.ok
    assert result.errors
    assert result.changed_files == []
    assert not (repo / ".github").exists()


def test_public_cli_routes_to_scoped_installer(targets, capsys):
    repo, framework = targets
    assert installer.main(["--repo", str(repo), "--framework-root", str(framework), "--copilot-vscode-only", "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["changed_files"]) == 3
    assert not (repo / ".github/hooks/ai-governance-copilot.json").exists()


@pytest.mark.parametrize("flag", ["--copilot-only", "--hooks-only", "--identity-config-only", "--copilot-instructions-only"])
def test_scoped_mode_rejects_other_install_modes(targets, flag):
    repo, framework = targets
    with pytest.raises(SystemExit) as exc:
        installer.main(["--repo", str(repo), "--framework-root", str(framework), "--copilot-vscode-only", flag])
    assert exc.value.code == 2
    assert not (repo / ".github").exists()
