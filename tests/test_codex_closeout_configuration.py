"""#319: configuration repair must preserve a project's formal Stop entry.

Fixtures are synthetic. These tests import the real manager; no hook or
closeout is executed, and no execution/trust claim follows from a declaration.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import shlex
import sys

import pytest

from governance_tools import manage_agent_closeout as manager


def _project_hook() -> dict:
    args = '--format json --agent-id codex --trigger-mode native_hook'
    entry = '"$work_root/scripts/turn_adapter.py"'
    windows = (
        '$work_root = git rev-parse --show-toplevel; '
        '& python "$work_root/scripts/turn_adapter.py" '
        + args + ' --project-root $work_root; exit $LASTEXITCODE'
    )
    return {
        "type": "command",
        "command": (
            'work_root="$(git rev-parse --show-toplevel)" && '
            'if [ -x "$work_root/.venv/bin/python" ]; then '
            f'"$work_root/.venv/bin/python" {entry} {args} --project-root "$work_root"; '
            f'else python3 {entry} {args} --project-root "$work_root"; fi'
        ),
        "commandWindows": "powershell -NoProfile -EncodedCommand "
        + base64.b64encode(windows.encode("utf-16-le")).decode("ascii"),
        "timeout": 30,
        "statusMessage": "Checking project prerequisites",
    }


def _consumer(tmp_path: Path, hooks: list[dict]) -> tuple[Path, Path, Path]:
    root = tmp_path / "consumer"
    framework = root / "framework"
    entry = framework / "governance_tools/session_closeout_entry.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("# synthetic framework location\n", encoding="utf-8")
    script = root / "scripts/turn_adapter.py"
    script.parent.mkdir()
    script.write_text(
        "from governance_tools import session_closeout_entry\n"
        "raise SystemExit(session_closeout_entry.main())\n",
        encoding="utf-8",
    )
    path = root / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"hooks": {
        "SessionStart": [{"matcher": "startup", "hooks": [
            {"type": "command", "command": "python scripts/session_identity.py"},
        ]}],
        "Stop": [{"hooks": hooks}],
    }}, indent=2) + "\n", encoding="utf-8")
    return root, framework, path


def _stop_hooks(path: Path) -> list[dict]:
    return [hook for group in json.loads(path.read_text(encoding="utf-8"))["hooks"]["Stop"]
            for hook in group["hooks"]]


@pytest.mark.parametrize("operation", ["install", "repair"])
def test_project_adapter_sequence_does_not_add_a_second_entry(tmp_path, operation):
    root, framework, path = _consumer(tmp_path, [_project_hook()])
    adapter = manager.CodexCLIAdapter()
    before_bytes = path.read_bytes()
    before = adapter.verify(root, framework)
    before_count = len(_stop_hooks(path))

    result = getattr(adapter, operation)(root, framework)
    after = adapter.verify(root, framework)
    observed = {
        "before_stop_count": before_count,
        "before_installed": before["installed"],
        "after_stop_count": len(_stop_hooks(path)),
        "after_installed": after["installed"],
        "action_status": result["status"],
    }
    # This assertion exposes the original 1 -> 2 / false -> true defect.
    assert observed == {
        "before_stop_count": 1,
        "before_installed": False,
        "after_stop_count": 1,
        "after_installed": False,
        "action_status": "blocked",
    }
    assert path.read_bytes() == before_bytes
    assert before["configuration_state"] == after["configuration_state"] == "project_adapter_unverified"
    assert "Configuration binding only" in after["note"]
    assert "native execution is not verified" in after["note"]
    assert "decide" in result["message"].lower()
    for _ in range(2):
        assert getattr(adapter, operation)(root, framework)["status"] == "blocked"
        assert path.read_bytes() == before_bytes


def _declare(root: Path, hook: dict, **changes) -> Path:
    declaration = {key: hook[key] for key in ("command", "commandWindows") if key in hook}
    declaration["delegates_to"] = "framework/governance_tools/session_closeout_entry.py"
    declaration.update(changes)
    path = root / ".codex/closeout-adapter.json"
    path.write_text(json.dumps(declaration), encoding="utf-8")
    return path


def test_declared_project_adapter_install_and_repair_are_successful_noops(tmp_path):
    hook = _project_hook()
    root, framework, path = _consumer(tmp_path, [hook])
    declaration = _declare(root, hook)
    before = path.read_bytes(), declaration.read_bytes()
    adapter = manager.CodexCLIAdapter()

    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "project_adapter_verified"
    assert result["installed"] is True
    assert result["formal_closeout_count"] == 1
    assert "runtime delegation is not verified" in result["note"]
    assert "native execution is not verified" in result["note"]
    assert result["note"].endswith(manager._PENDING_HOOK_NOTE)
    assert "manual_fallback" in result["note"]
    for operation in ("install", "repair", "repair", "install"):
        outcome = getattr(adapter, operation)(root, framework)
        assert outcome["status"] == ("already_configured" if operation == "install" else "no_repair_needed")
        assert outcome["configuration_state"] == "project_adapter_verified"
        assert "Configuration binding only" in outcome["message"]
        assert "native execution, hook trust and formal closeout are not verified" in outcome["message"]
        if operation == "repair":
            assert outcome["repaired"] is False
        assert (path.read_bytes(), declaration.read_bytes()) == before


@pytest.mark.parametrize("defect", [
    "wrong-target", "missing-target", "command-mismatch", "windows-mismatch",
    "windows-omitted", "invalid-json", "not-an-object", "unknown-field",
])
def test_adapter_declaration_must_match_both_commands_and_requested_entry(tmp_path, defect):
    hook = _project_hook()
    root, framework, path = _consumer(tmp_path, [hook])
    declaration = _declare(root, hook)
    data = json.loads(declaration.read_text(encoding="utf-8"))
    if defect == "wrong-target":
        data["delegates_to"] = "other-framework/governance_tools/session_closeout_entry.py"
    elif defect == "missing-target":
        (framework / "governance_tools/session_closeout_entry.py").unlink()
    elif defect == "command-mismatch":
        data["command"] += " --extra"
    elif defect == "windows-mismatch":
        data["commandWindows"] = "python scripts/another_adapter.py"
    elif defect == "windows-omitted":
        del data["commandWindows"]
    elif defect == "not-an-object":
        data = []
    elif defect == "unknown-field":
        data["trust"] = True
    declaration.write_text("{" if defect == "invalid-json" else json.dumps(data), encoding="utf-8")
    before = path.read_bytes(), declaration.read_bytes()
    adapter = manager.CodexCLIAdapter()
    for operation in ("install", "repair"):
        verified = adapter.verify(root, framework)
        assert verified["configuration_state"] == "project_adapter_unverified"
        assert verified["installed"] is False
        assert manager._PENDING_HOOK_NOTE not in verified["note"]
        assert getattr(adapter, operation)(root, framework)["status"] == "blocked"
        assert (path.read_bytes(), declaration.read_bytes()) == before


def test_opaque_project_adapter_requires_an_exact_declaration(tmp_path):
    # No filename/argument heuristic is needed to verify this declared command.
    hook = {"type": "command", "command": "python scripts/opaque.py"}
    root, framework, path = _consumer(tmp_path, [hook])
    adapter = manager.CodexCLIAdapter()
    assert adapter.verify(root, framework)["configuration_state"] == "missing"
    _declare(root, hook)
    before = path.read_bytes()
    assert adapter.verify(root, framework)["configuration_state"] == "project_adapter_verified"
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"
    assert path.read_bytes() == before


def test_unmatched_declaration_reserves_even_an_opaque_stop_configuration(tmp_path):
    root, framework, path = _consumer(tmp_path, [{"type": "command", "command": "python scripts/opaque.py"}])
    _declare(root, {"command": "python scripts/previous_adapter.py"})
    before = path.read_bytes()
    adapter = manager.CodexCLIAdapter()
    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "project_adapter_unverified"
    assert result["installed"] is False
    assert adapter.install(root, framework)["status"] == "blocked"
    assert path.read_bytes() == before


@pytest.mark.parametrize("command", [
    "python scripts/unknown.py --agent-id=codex --trigger-mode=native_hook",
    "bash scripts/unknown.sh --trigger-mode native_hook --agent-id codex",
    "python -m governance_tools.session_closeout_entry --project-root .",
    'python -c "from governance_tools import session_closeout_entry; session_closeout_entry.main()"',
    'python -c "from governance_tools.session_closeout_entry import main; main()"',
    'python -c "import governance_tools.session_closeout_entry as entry; entry.main()"',
])
def test_unknown_formal_invocations_are_unverified_and_preserved(tmp_path, command):
    root, framework, path = _consumer(tmp_path, [{"type": "command", "command": command}])
    before = path.read_bytes()
    adapter = manager.CodexCLIAdapter()
    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "project_adapter_unverified"
    assert result["installed"] is False
    assert result["formal_closeout_count"] == 1
    assert adapter.repair(root, framework)["status"] == "blocked"
    assert path.read_bytes() == before


@pytest.mark.parametrize("platform", ["posix", "windows"])
def test_mixed_project_and_framework_platform_commands_are_not_replaced(tmp_path, platform):
    root, framework, path = _consumer(tmp_path, [])
    adapter = manager.CodexCLIAdapter()
    hook = adapter._hook_payload(framework, root)
    field = "command" if platform == "posix" else "commandWindows"
    hook[field] = _project_hook()[field]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["Stop"][0]["hooks"] = [hook]
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    assert adapter.verify(root, framework)["configuration_state"] == "project_adapter_unverified"
    assert adapter.install(root, framework)["status"] == "blocked"
    assert path.read_bytes() == before


@pytest.mark.parametrize("shell", ["powershell", "powershell.exe", "pwsh"])
@pytest.mark.parametrize("entry_kind", ["project", "framework"])
def test_unowned_windows_invocations_are_reserved_for_verification(tmp_path, shell, entry_kind):
    root, framework, path = _consumer(tmp_path, [])
    entry = ("scripts/unknown.py" if entry_kind == "project"
             else (framework / "governance_tools/session_closeout_entry.py").as_posix())
    script = f"& python '{entry}' --agent-id codex --trigger-mode native_hook"
    hook = {
        "type": "command", "command": "echo unrelated",
        "commandWindows": shell + " -NoProfile -EncodedCommand "
        + base64.b64encode(script.encode("utf-16-le")).decode("ascii"),
    }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["Stop"][0]["hooks"] = [hook]
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    adapter = manager.CodexCLIAdapter()
    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "project_adapter_unverified"
    assert result["installed"] is False
    assert result["formal_closeout_count"] == 1
    assert adapter.repair(root, framework)["status"] == "blocked"
    assert path.read_bytes() == before


@pytest.mark.parametrize("declared", [False, True])
def test_project_plus_direct_entry_is_conflict_even_with_an_adapter_declaration(tmp_path, declared):
    hook = _project_hook()
    root, framework, path = _consumer(tmp_path, [hook])
    if declared:
        _declare(root, hook)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["Stop"].append({"hooks": [
        {"type": "command", "command": "echo unrelated"},
        manager.CodexCLIAdapter._hook_payload(framework, root),
    ]})
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    adapter = manager.CodexCLIAdapter()
    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "conflict"
    assert result["formal_closeout_count"] == 2
    assert result["installed"] is False
    assert "2 possible formal" in result["note"]
    assert "single" not in result["note"].lower()
    assert manager._PENDING_HOOK_NOTE not in result["note"]
    for operation in ("install", "repair", "repair"):
        assert getattr(adapter, operation)(root, framework)["status"] == "blocked"
        assert path.read_bytes() == before


@pytest.mark.parametrize("adapter_kind", ["project", "declared", "unknown", "opaque-declared", "declared-owned"])
def test_framework_duplicates_with_any_project_or_unknown_entry_remain_blocked(tmp_path, adapter_kind):
    root, framework, path = _consumer(tmp_path, [])
    adapter = manager.CodexCLIAdapter()
    hook = _project_hook()
    if adapter_kind == "unknown":
        hook = {"type": "command", "command": "python -m governance_tools.session_closeout_entry"}
    elif adapter_kind == "opaque-declared":
        hook = {"type": "command", "command": "python scripts/opaque.py"}
    elif adapter_kind == "declared-owned":
        hook = adapter._hook_payload(framework, root)
    if adapter_kind in {"declared", "opaque-declared", "declared-owned"}:
        _declare(root, hook)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["hooks"]["Stop"] = [{"hooks": [
        adapter._hook_payload(framework, root),
        {"type": "command", "command": "echo unrelated"},
        adapter._hook_payload(root / "previous-framework", root),
        hook,
    ]}]
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    verified = adapter.verify(root, framework)
    assert verified["installed"] is False
    assert verified["configuration_state"] == "conflict"
    assert verified["formal_closeout_count"] == 3
    for operation in ("install", "repair", "repair"):
        assert getattr(adapter, operation)(root, framework)["status"] == "blocked"
        assert path.read_bytes() == before


@pytest.mark.parametrize("command", [
    'echo python governance_tools/session_closeout_entry.py --agent-id codex --trigger-mode native_hook',
    'python scripts/session_closeout_entry.py --custom-purpose',
    'python scripts/report.py --agent-id codex --trigger-mode checkpoint',
    'python -c "print(\'governance_tools.session_closeout_entry\')"',
])
def test_other_purpose_stop_is_never_counted_as_a_formal_conflict(tmp_path, command):
    root, framework, path = _consumer(tmp_path, [{"type": "command", "command": command}])
    adapter = manager.CodexCLIAdapter()
    before = _stop_hooks(path)[0]
    result = adapter.verify(root, framework)
    assert result["configuration_state"] == "missing"
    assert result["formal_closeout_count"] == 0
    assert adapter.install(root, framework)["status"] == "installed"
    assert _stop_hooks(path)[0] == before
    installed_bytes = path.read_bytes()
    result = adapter.verify(root, framework)
    assert result["installed"] is True
    assert result["configuration_state"] == "standard"
    assert result["formal_closeout_count"] == 1
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"
    assert path.read_bytes() == installed_bytes


@pytest.mark.parametrize("initial", ["missing", "stale", "wrong-root", "duplicate", "triplicate"])
def test_standard_install_and_repair_preserve_unrelated_json_bytes(tmp_path, initial):
    root, framework, path = _consumer(tmp_path, [])
    adapter = manager.CodexCLIAdapter()
    session = '"SessionStart" : [ {"hooks":[{"type":"command", "command":"echo start\\u0021"}]} ]'
    other = '{"type":"command", "command" : "echo audit\\u0021", "timeout":7}'
    standard = ""
    if initial != "missing":
        old_root = framework if initial == "stale" else root / "previous-framework"
        hook = adapter._hook_payload(old_root, root)
        if initial == "stale":
            hook["commandWindows"] = "python session_closeout_entry.py"
        standard = json.dumps(hook) + ", "
        if initial in {"duplicate", "triplicate"}:
            standard += json.dumps(adapter._hook_payload(framework, root)) + ", "
        if initial == "triplicate":
            standard += json.dumps(adapter._hook_payload(root / "another-framework", root)) + ", "
    source = ('{\r\n "hooks" : {' + session + ',\r\n "Stop" : [{"hooks" : ['
              + standard + other + ']}]},\r\n "custom": "kept\\u0021"\r\n}\r\n')
    path.write_bytes(source.encode("utf-8"))
    before = adapter.verify(root, framework)
    expected_state = ("missing" if initial == "missing" else
                      "standard_duplicate" if initial in {"duplicate", "triplicate"} else "standard_stale")
    assert before["configuration_state"] == expected_state
    assert before["installed"] is False
    assert adapter.repair(root, framework)["status"] == "installed"
    after = path.read_bytes()
    assert session.encode("utf-8") in after
    assert other.encode("utf-8") in after
    assert b'"custom": "kept\\u0021"\r\n}\r\n' in after
    assert adapter.verify(root, framework)["configuration_state"] == "standard"
    assert len(_stop_hooks(path)) == 2
    assert adapter.install(root, framework)["status"] == "already_installed"
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"
    assert path.read_bytes() == after


@pytest.mark.parametrize("stop", [None, [], [{"matcher": "keep"}], [{"hooks": []}]])
def test_missing_stop_container_installs_without_changing_sessionstart(tmp_path, stop):
    root, framework, path = _consumer(tmp_path, [])
    session = '"SessionStart" : [ {"hooks":[]} ]'
    source = '{"hooks":{' + session
    if stop is not None:
        source += ', "Stop":' + json.dumps(stop)
    source += '}}'
    path.write_text(source, encoding="utf-8")
    adapter = manager.CodexCLIAdapter()
    assert adapter.install(root, framework)["status"] == "installed"
    assert session.encode("utf-8") in path.read_bytes()
    if stop and "matcher" in stop[0]:
        assert json.loads(path.read_text(encoding="utf-8"))["hooks"]["Stop"][0]["matcher"] == "keep"
    assert adapter.verify(root, framework)["installed"] is True


def test_legacy_owned_wrapper_remains_replaceable_as_a_stale_framework_entry(tmp_path):
    code = ("# governance:claude-closeout-v1\n"
            "from governance_tools import session_closeout_entry\n"
            "session_closeout_entry.main()\n")
    root, framework, path = _consumer(tmp_path, [{"type": "command", "command": "python -c " + shlex.quote(code)}])
    adapter = manager.CodexCLIAdapter()
    assert adapter.verify(root, framework)["configuration_state"] == "standard_stale"
    assert adapter.repair(root, framework)["status"] == "installed"
    assert adapter.verify(root, framework)["installed"] is True
    assert len(_stop_hooks(path)) == 1


@pytest.mark.parametrize("source", [
    '{', '[]', '{"hooks":[]}', '{"hooks":{"Stop":{}}}',
    '{"hooks":{"Stop":[{"hooks":null}]}}',
    '{"hooks":{"Stop":[{"hooks":[null]}]}}',
    '{"hooks":{}, "hooks":{"Stop":[]}}',
])
def test_invalid_configuration_is_not_treated_as_missing(tmp_path, source):
    root, framework, path = _consumer(tmp_path, [])
    path.write_text(source, encoding="utf-8")
    before = path.read_bytes()
    adapter = manager.CodexCLIAdapter()
    result = adapter.verify(root, framework)
    assert result["installed"] is False
    assert result["configuration_state"] == "invalid"
    assert adapter.install(root, framework)["status"] == "blocked"
    assert adapter.repair(root, framework)["status"] == "blocked"
    assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["verify", "install", "repair"])
@pytest.mark.parametrize("declared", [False, True])
def test_cli_preserves_unverified_failure_and_verified_adapter_success(
    tmp_path, monkeypatch, capsys, operation, declared
):
    hook = _project_hook()
    root, framework, path = _consumer(tmp_path, [hook])
    if declared:
        _declare(root, hook)
    before = path.read_bytes()
    monkeypatch.setattr(manager, "_resolve_framework_root", lambda: framework)
    monkeypatch.setattr(sys, "argv", [
        "manage_agent_closeout", "--project-root", str(root), "--format", "json",
        operation, "--agent", "codex",
    ])
    exit_code = manager.main()
    result = json.loads(capsys.readouterr().out)
    assert exit_code == (0 if declared else 1)
    assert result["configuration_state"] == (
        "project_adapter_verified" if declared else "project_adapter_unverified"
    )
    if operation != "verify":
        expected_status = ("already_configured" if operation == "install" else "no_repair_needed")
        assert result["status"] == (expected_status if declared else "blocked")
    assert path.read_bytes() == before


def test_documented_adapter_declaration_is_valid_json_and_matches_the_hook(tmp_path):
    doc = (Path(__file__).resolve().parents[1] / "docs/hook-coverage-model.md").read_text(encoding="utf-8")
    example = json.loads(doc.split("```json\n", 1)[1].split("```", 1)[0])
    hook = {"type": "command", "command": example["command"]}
    root, framework, path = _consumer(tmp_path, [hook])
    declaration = root / ".codex/closeout-adapter.json"
    declaration.write_text(json.dumps(example), encoding="utf-8")
    before = path.read_bytes(), declaration.read_bytes()
    adapter = manager.CodexCLIAdapter()
    assert adapter.verify(root, framework)["configuration_state"] == "project_adapter_verified"
    assert adapter.install(root, framework)["status"] == "already_configured"
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"
    assert (path.read_bytes(), declaration.read_bytes()) == before


@pytest.mark.parametrize("state", ["project_adapter_unverified", "project_adapter_verified", "conflict"])
def test_status_distinguishes_a_project_decision_from_missing_installation(tmp_path, monkeypatch, state):
    hook = _project_hook()
    root, framework, path = _consumer(tmp_path, [hook])
    if state == "project_adapter_verified":
        _declare(root, hook)
    elif state == "conflict":
        data = json.loads(path.read_text(encoding="utf-8"))
        data["hooks"]["Stop"][0]["hooks"].append(manager.CodexCLIAdapter._hook_payload(framework, root))
        path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    row = next(item for item in manager.op_status(root, framework) if item["agent"] == "codex")
    assert row["configuration_state"] == state
    assert row["compliance_status"] == ("READY" if state == "project_adapter_verified" else "NEEDS_DECISION")
    assert path.read_bytes() == before
