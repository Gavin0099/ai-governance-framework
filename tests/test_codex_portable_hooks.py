"""#288 portability: hooks written for a framework checkout inside the consumer
resolve the repository root and Python at run time, so a committed
.codex/hooks.json works on another machine, user or clone location. The
absolute form stays accepted for existing consumers."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.codex_session_start_wiring import (
    INSTALLED_CORRECTLY,
    assess_codex_session_start,
)
from governance_tools.manage_agent_closeout import CodexCLIAdapter
from runtime_hooks.adapters.codex import session_start as ss


def _consumer(base: Path, name: str = "consumer", rel: str = "ai-governance-framework") -> tuple[Path, Path]:
    root = base / name
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    framework = root / rel
    framework.mkdir(parents=True)
    return root.resolve(), framework.resolve()


def _hooks(root: Path) -> Path:
    return root / ".codex" / "hooks.json"


def _install_both(root: Path, framework: Path, monkeypatch) -> None:
    monkeypatch.setattr(ss, "FRAMEWORK_ROOT", framework)
    assert ss.install(root)["status"] == "installed"
    assert CodexCLIAdapter().install(root, framework)["status"] == "installed"


def test_installed_hooks_carry_no_machine_specific_path(tmp_path, monkeypatch):
    root, framework = _consumer(tmp_path)
    _install_both(root, framework, monkeypatch)
    text = _hooks(root).read_text(encoding="utf-8")
    data = json.loads(text)
    import base64
    decoded = [
        base64.b64decode(hook["commandWindows"].split()[-1]).decode("utf-16-le")
        for event in ("SessionStart", "Stop")
        for group in data["hooks"][event]
        for hook in group["hooks"]
    ]
    for blob in [text, *decoded]:
        assert str(tmp_path) not in blob and tmp_path.as_posix() not in blob
        assert sys.executable not in blob
    assert all('"$repo/ai-governance-framework/' in script for script in decoded)


def test_portable_hooks_are_correct_in_the_installing_clone_and_a_moved_clone(tmp_path, monkeypatch):
    root, framework = _consumer(tmp_path / "machine-a")
    _install_both(root, framework, monkeypatch)
    report = assess_codex_session_start(root, framework)
    assert report["status"] == INSTALLED_CORRECTLY, report["reasons"]
    assert report["stop_wiring"] == "consistent"

    # Same committed file, another location (another machine, user or clone).
    other, other_framework = _consumer(tmp_path / "machine-b", name="elsewhere")
    _hooks(other).parent.mkdir(parents=True)
    shutil.copyfile(_hooks(root), _hooks(other))
    moved = assess_codex_session_start(other, other_framework)
    assert moved["status"] == INSTALLED_CORRECTLY, moved["reasons"]
    assert moved["stop_wiring"] == "consistent"


def test_portable_hook_for_another_framework_path_is_not_correct(tmp_path, monkeypatch):
    root, framework = _consumer(tmp_path)
    _install_both(root, framework, monkeypatch)
    other_framework = root / "vendor" / "ai-governance-framework"
    other_framework.mkdir(parents=True)
    report = assess_codex_session_start(root, other_framework.resolve())
    assert report["status"] != INSTALLED_CORRECTLY
    assert report["stop_wiring"] == "inconsistent"


def test_existing_absolute_bindings_stay_current_and_are_not_rewritten(tmp_path, monkeypatch):
    root, framework = _consumer(tmp_path)
    legacy = {
        "hooks": {
            "SessionStart": [{"matcher": ss.SESSION_START_MATCHER, "hooks": [ss.hook_payload(root)]}],
            "Stop": [{"hooks": [CodexCLIAdapter._hook_payload(framework)]}],
        }
    }
    _hooks(root).parent.mkdir(parents=True)
    _hooks(root).write_text(json.dumps(legacy, indent=2), encoding="utf-8")
    before = _hooks(root).read_bytes()

    monkeypatch.setattr(ss, "FRAMEWORK_ROOT", Path(ss.__file__).resolve().parents[3])
    assert CodexCLIAdapter().install(root, framework)["status"] == "already_installed"
    assert CodexCLIAdapter().verify(root, framework)["installed"] is True
    assert ss.install(root)["status"] == "already_installed"
    assert _hooks(root).read_bytes() == before


def test_framework_outside_the_consumer_keeps_the_absolute_form(tmp_path):
    root, _ = _consumer(tmp_path)
    outside = (tmp_path / "shared-framework").resolve()
    outside.mkdir()
    assert ss.portable_framework_path(root, outside) is None
    assert ss.portable_hook_payload(root, outside) is None
    assert CodexCLIAdapter._hook_payload(outside, root) == CodexCLIAdapter._hook_payload(outside)


@pytest.mark.parametrize("rel", ["ai governance", "fw$x", "it's"])
def test_paths_that_would_need_shell_quoting_keep_the_absolute_form(tmp_path, rel):
    root, framework = _consumer(tmp_path, rel=rel)
    assert ss.portable_framework_path(root, framework) is None
