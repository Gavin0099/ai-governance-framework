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


# ── Execute the generated commands (review: string checks alone cannot catch
#    broken shell syntax or a wrong repository root) ─────────────────────────

_STUB = (
    "import pathlib, sys\n"
    "pathlib.Path(sys.argv[0]).with_name('ran.txt').write_text(' '.join(sys.argv[1:]), encoding='utf-8')\n"
)


def _stub_framework(root: Path, rel: str = "ai-governance-framework") -> None:
    for entry in ("governance_tools/session_closeout_entry.py",
                  "runtime_hooks/adapters/codex/session_start.py"):
        path = root / rel / entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_STUB, encoding="utf-8")


def _run(hook: dict, cwd: Path) -> subprocess.CompletedProcess:
    if sys.platform == "win32":
        return subprocess.run(hook["commandWindows"], cwd=cwd, shell=True, capture_output=True)
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available")
    return subprocess.run([bash, "-c", hook["command"]], cwd=cwd, capture_output=True)


def _portable_hooks(root: Path, framework: Path) -> list[dict]:
    return [CodexCLIAdapter._hook_payload(framework, root), ss.portable_hook_payload(root, framework)]


@pytest.mark.skipif(sys.platform == "win32" and shutil.which("powershell") is None,
                    reason="powershell not available")
def test_portable_hooks_run_the_consumer_entry_from_a_subdirectory(tmp_path):
    root, framework = _consumer(tmp_path / "with space")
    _stub_framework(root)
    (root / ".codex").mkdir()
    (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
    sub = root / "src" / "deep"
    sub.mkdir(parents=True)
    for hook, ran in zip(_portable_hooks(root, framework),
                         ("governance_tools/ran.txt", "runtime_hooks/adapters/codex/ran.txt")):
        result = _run(hook, sub)
        assert result.returncode == 0, result.stderr
        args = (framework / ran).read_text(encoding="utf-8")
        assert Path(args.split("--project-root ", 1)[1].split(" --", 1)[0]).resolve() == root


@pytest.mark.skipif(sys.platform == "win32" and shutil.which("powershell") is None,
                    reason="powershell not available")
def test_portable_hooks_refuse_a_nested_repository_without_codex_hooks(tmp_path):
    root, framework = _consumer(tmp_path)
    (root / ".codex").mkdir()
    (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
    nested = root / "third_party" / "lib"
    subprocess.run(["git", "init", "-q", str(nested)], check=True)
    _stub_framework(nested)  # a nested repo that ships same-named scripts
    for hook in _portable_hooks(root, framework):
        result = _run(hook, nested)
        assert result.returncode != 0
    assert not list(nested.rglob("ran.txt")), "a nested repository's entry must not run"
