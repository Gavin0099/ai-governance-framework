import json
from pathlib import Path

import pytest
from governance_tools.manage_agent_closeout import CopilotAdapter


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "consumer space"
    framework = tmp_path / "framework space"
    root.mkdir()
    return CopilotAdapter(), root, framework


def read(root):
    return json.loads((root / ".github/hooks/session-end.json").read_text())


def write(root, data):
    path = root / ".github/hooks/session-end.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_install_binding_and_idempotency(setup):
    adapter, root, framework = setup
    assert adapter.install(root, framework)["status"] == "installed"
    data = read(root)
    assert data["version"] == 1
    assert str(framework.as_posix()) in data["hooks"]["sessionEnd"][0]["bash"]
    assert adapter.verify(root, framework)["binding_state"] == "CORRECTLY_INSTALLED"
    assert adapter.install(root, framework)["status"] == "already_installed"
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"


@pytest.mark.parametrize("change", ["framework", "consumer", "missing_version", "version2", "bool_version", "powershell", "duplicate"])
def test_stale_binding_is_repaired(setup, change):
    adapter, root, framework = setup
    adapter.install(root, framework)
    data = read(root)
    h = data["hooks"]["sessionEnd"][0]
    if change == "framework":
        h["bash"] = h["bash"].replace("framework space", "wrong framework")
    elif change == "consumer":
        h["bash"] = h["bash"].replace("consumer space", "wrong consumer")
    elif change == "missing_version":
        del data["version"]
    elif change == "version2":
        data["version"] = 2
    elif change == "bool_version":
        data["version"] = True
    elif change == "powershell":
        h["powershell"] = h["powershell"].replace("framework space", "wrong framework")
    else:
        data["hooks"]["sessionEnd"].append(dict(h))
    unrelated = {"type": "command", "bash": "echo session_closeout_entry"}
    data["hooks"]["sessionEnd"].append(unrelated)
    data["hooks"]["sessionStart"] = [{"type": "command", "bash": "echo start"}]
    write(root, data)
    assert adapter.verify(root, framework)["installed"] is False
    assert adapter.verify(root, framework)["binding_state"] == "STALE_OR_WRONG_BINDING"
    assert adapter.repair(root, framework)["status"] != "no_repair_needed"
    assert adapter.verify(root, framework)["installed"] is True
    repaired = read(root)
    assert unrelated in repaired["hooks"]["sessionEnd"]
    assert len(repaired["hooks"]["sessionEnd"]) == 2
    assert repaired["hooks"]["sessionStart"] == data["hooks"]["sessionStart"]


def test_name_mention_is_not_binding(setup):
    adapter, root, framework = setup
    write(root, {"version": 1, "hooks": {"sessionEnd": [{"bash": "echo session_closeout_entry"}]}})
    assert not adapter.verify(root, framework)["installed"]


@pytest.mark.parametrize("raw", ["{", "[]", '{"hooks": []}', '{"version": 1, "hooks": {"sessionEnd": {}}}'])
def test_malformed_config_rejected_without_overwrite(setup, raw):
    adapter, root, framework = setup
    write(root, {})
    path = root / ".github/hooks/session-end.json"
    path.write_text(raw)
    assert not adapter.verify(root, framework)["installed"]
    adapter.repair(root, framework)
    assert path.read_text() == raw


def test_observed_legacy_external_binding(setup):
    adapter, root, framework = setup
    write(root, {"hooks": {"sessionEnd": [{"type": "command", "bash": "python E:/other/governance_tools/session_closeout_entry.py --project-root . 2>/dev/null || true", "powershell": "python E:/other/governance_tools/session_closeout_entry.py --project-root . 2>$null || true", "timeoutSec": 30}]}})
    assert not adapter.verify(root, framework)["installed"]
    adapter.repair(root, framework)
    assert adapter.verify(root, framework)["installed"]
    assert len(read(root)["hooks"]["sessionEnd"]) == 1


@pytest.mark.parametrize("blocker", ["disabled", "sessionStart", "preToolUse", "sibling"])
def test_review_blockers_preserve_all_files(setup, blocker):
    adapter, root, framework = setup
    adapter.install(root, framework)
    data = read(root)
    if blocker == "disabled":
        data["disableAllHooks"] = True
    elif blocker == "sibling":
        sibling = root / ".github/hooks/legacy.json"
        sibling.write_text(json.dumps({"version": 1, "hooks": {"sessionEnd": [
            {"type": "command", "bash": "python /wrong/governance_tools/session_closeout_entry.py --project-root ."}
        ]}}))
    else:
        data["hooks"][blocker] = {}
    write(root, data)
    directory = root / ".github/hooks"
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = adapter.verify(root, framework)
    assert result["installed"] is False
    assert result["binding_state"] == "STALE_OR_WRONG_BINDING"
    if blocker == "sibling":
        assert "legacy.json" in result["note"]
    assert adapter.install(root, framework)["status"] == "error"
    assert adapter.repair(root, framework)["status"] != "no_repair_needed"
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before


def test_disabled_sibling_does_not_conflict(setup):
    adapter, root, framework = setup
    adapter.install(root, framework)
    sibling = root / ".github/hooks/legacy.json"
    sibling.write_text(json.dumps({"version": 1, "disableAllHooks": True, "hooks": {
        "sessionEnd": [{"bash": "python /wrong/governance_tools/session_closeout_entry.py"}]}}))
    before = sibling.read_bytes()
    assert adapter.verify(root, framework)["installed"]
    assert adapter.repair(root, framework)["status"] == "no_repair_needed"
    assert sibling.read_bytes() == before

@pytest.mark.parametrize("hook", [
    {"type": "command", "bash": "/usr/bin/python3 /wrong/governance_tools/session_closeout_entry.py --project-root ."},
    {"type": "command", "bash": "python -B /wrong/governance_tools/session_closeout_entry.py --project-root ."},
    {"type": "command", "exec": "python", "args": ["/wrong/governance_tools/session_closeout_entry.py", "--project-root", "."]},
])
def test_observed_sibling_invocation_forms_block_without_mutation(setup, hook):
    adapter, root, framework = setup
    adapter.install(root, framework)
    directory = root / ".github/hooks"
    (directory / "legacy.json").write_text(json.dumps({
        "version": 1, "hooks": {"sessionEnd": [hook]}}), encoding="utf-8")
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = adapter.verify(root, framework)
    assert not result["installed"]
    assert result["binding_state"] == "STALE_OR_WRONG_BINDING"
    assert "legacy.json" in result["note"]
    assert adapter.repair(root, framework)["status"] != "no_repair_needed"
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
