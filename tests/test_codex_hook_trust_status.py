from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from governance_tools import codex_hook_trust_status as trust


def _write_hooks(repo: Path, *, extra: bool = False, command: str = "do not execute") -> Path:
    path = repo / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    hook = {"type": "command", "command": command}
    path.write_text(json.dumps({"hooks": {
        "SessionStart": [{"hooks": [hook]}],
        "Stop": [{"hooks": [hook, hook] if extra else [hook]}],
    }}), encoding="utf-8")
    return path


def _metadata(path: str, event: str = "stop", *, status: str = "trusted", enabled=True, index=0):
    key_event = "session_start" if event == "sessionStart" else event
    return {
        "key": f"{path}:{key_event}:0:{index}", "sourcePath": path,
        "eventName": event, "trustStatus": status, "enabled": enabled,
        "currentHash": "sha256:opaque-client-value", "source": "project",
        "isManaged": status == "managed", "displayOrder": index, "timeoutSec": 30,
        "handlerType": "command", "command": "never expose or execute this command",
    }


def _both(path: Path, **kwargs):
    return [_metadata(str(path), event, **kwargs) for event in ("sessionStart", "stop")]


@pytest.fixture
def fake_server(tmp_path: Path, monkeypatch):
    scenario_path = tmp_path / "scenario.json"
    fixture = Path(__file__).parent / "fixtures" / "codex_hook_app_server.py"
    command = [sys.executable, "-X", "utf8", str(fixture), str(scenario_path)]
    monkeypatch.setattr(trust, "_resolve_codex", lambda explicit: command)
    original_popen = subprocess.Popen
    processes = []

    def tracked_popen(*args, **kwargs):
        proc = original_popen(*args, **kwargs)
        processes.append(proc)
        return proc

    monkeypatch.setattr(trust.subprocess, "Popen", tracked_popen)

    def configure(**scenario):
        scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
        return scenario_path

    yield configure, processes
    leaked = [proc for proc in processes if proc.poll() is None]
    for proc in leaked:
        proc.kill()
        proc.wait(timeout=2)
    assert not leaked, "diagnostic left an app-server running"


@pytest.mark.parametrize("status,expected,adopted", [
    ("trusted", "installed_trusted", True),
    ("managed", "installed_trusted", True),
    ("untrusted", "installed_untrusted", False),
    ("modified", "installed_modified", False),
])
def test_authoritative_status_and_handshake_are_reported_without_writes(
    tmp_path, fake_server, status, expected, adopted,
):
    path = _write_hooks(tmp_path)
    before = path.read_bytes()
    configure, processes = fake_server
    scenario = configure(hooks=_both(path, status=status))
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == expected
    assert report["adopted"] is adopted
    assert report["report_only"] is True
    assert all(h["state"] == expected and h["trust_status"] == status for h in report["hooks"])
    assert path.read_bytes() == before
    assert processes and all(p.poll() is not None for p in processes)
    trace = [json.loads(line) for line in scenario.with_suffix(".trace").read_text().splitlines()]
    assert [m["method"] for m in trace] == ["initialize", "initialized", "hooks/list"]
    assert trace[2]["params"] == {"cwds": [str(tmp_path.resolve())]}
    assert "not mean executed or closed out" in report["claim_boundary"]
    assert "never expose" not in json.dumps(report)
    assert "sourcePath" not in json.dumps(report)


def test_trusted_but_disabled_does_not_count_as_adopted(tmp_path, fake_server):
    path = _write_hooks(tmp_path)
    fake_server[0](hooks=_both(path, enabled=False))
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "installed_trusted"
    assert not report["adopted"]
    assert all(h["enabled"] is False and not h["adopted"] for h in report["hooks"])


def test_changed_definition_uses_modified_status_from_codex(tmp_path, fake_server):
    path = _write_hooks(tmp_path)
    configure, _ = fake_server
    configure(hooks=_both(path))
    assert trust.inspect_codex_hook_trust(tmp_path)["adopted"] is True
    _write_hooks(tmp_path, command="changed definition")
    configure(hooks=_both(path, status="modified"))
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "installed_modified"
    assert not report["adopted"]


def test_missing_file_and_missing_expected_events_are_not_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(trust, "_resolve_codex", lambda explicit: pytest.fail("must not spawn"))
    for content in (None, {"hooks": {"Stop": []}}):
        if content is not None:
            path = tmp_path / ".codex" / "hooks.json"
            path.parent.mkdir()
            path.write_text(json.dumps(content), encoding="utf-8")
        report = trust.inspect_codex_hook_trust(tmp_path)
        assert report["state"] == "not_installed"
        assert not report["adopted"] and not report["probe_attempted"]
        assert {h["event"] for h in report["hooks"]} == {"SessionStart", "Stop"}


def test_file_definitions_not_returned_by_codex_are_not_loaded(tmp_path, fake_server):
    _write_hooks(tmp_path)
    fake_server[0](hooks=[])
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "installed_not_loaded"
    assert all(h["state"] == "installed_not_loaded" and not h["adopted"] for h in report["hooks"])


def test_extra_configured_hook_is_not_silently_counted_as_trusted(tmp_path, fake_server):
    path = _write_hooks(tmp_path, extra=True)
    fake_server[0](hooks=_both(path))
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert [h["state"] for h in report["hooks"]] == [
        "installed_trusted", "installed_trusted", "installed_not_loaded",
    ]
    assert report["hooks"][2]["hook_index"] == 1
    assert not report["adopted"]


@pytest.mark.parametrize("mode", [
    "initialize_timeout", "timeout", "malformed", "error", "wrong_id", "closed", "invalid_initialize_id",
])
def test_protocol_failures_are_unknown_and_child_is_reaped(tmp_path, fake_server, mode):
    _write_hooks(tmp_path)
    fake_server[0](mode=mode)
    started = time.monotonic()
    report = trust.inspect_codex_hook_trust(tmp_path, timeout_seconds=0.4 if "timeout" in mode else 5)
    assert time.monotonic() - started < 4
    assert report["state"] == "trust_unknown" and not report["adopted"]
    assert all(h["enabled"] is None and not h["adopted"] for h in report["hooks"])
    if "timeout" in mode:
        assert "timed out" in report["hooks"][0]["reason"]
    assert fake_server[1] and all(p.poll() is not None for p in fake_server[1])


@pytest.mark.parametrize("response", [[], {}, {"data": []}, {"data": [None]}])
def test_unexpected_response_shape_is_unknown(tmp_path, fake_server, response):
    _write_hooks(tmp_path)
    fake_server[0](response=response)
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "trust_unknown" and not report["adopted"]


@pytest.mark.parametrize("field,value", [("trustStatus", "future"), ("trustStatus", []),
                                         ("enabled", "true"), ("eventName", "sessionEnd")])
def test_unexpected_metadata_cannot_promote_partial_trust(tmp_path, fake_server, field, value):
    path = _write_hooks(tmp_path)
    metadata = _both(path)
    metadata[1][field] = value
    fake_server[0](hooks=metadata)
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "trust_unknown"
    assert all(h["state"] == "trust_unknown" and not h["adopted"] for h in report["hooks"])


def test_server_load_errors_and_wrong_cwd_are_unknown(tmp_path, fake_server):
    path = _write_hooks(tmp_path)
    entry = {"cwd": str(tmp_path), "hooks": _both(path), "errors": [{"message": "failure", "path": "private"}], "warnings": []}
    for change in ({}, {"cwd": str(tmp_path / "other"), "errors": []}):
        fake_server[0](response={"data": [{**entry, **change}]})
        report = trust.inspect_codex_hook_trust(tmp_path)
        assert report["state"] == "trust_unknown" and not report["adopted"]
        assert "private" not in json.dumps(report)


def test_another_project_hook_cannot_satisfy_the_definition(tmp_path, fake_server):
    path = _write_hooks(tmp_path)
    fake_server[0](hooks=_both(tmp_path / "other" / ".codex" / "hooks.json"))
    assert trust.inspect_codex_hook_trust(tmp_path)["state"] == "installed_not_loaded"
    metadata = _both(path)
    metadata[1]["key"] = str(tmp_path / "other" / ".codex" / "hooks.json") + ":stop:0:0"
    fake_server[0](hooks=metadata)
    assert trust.inspect_codex_hook_trust(tmp_path)["state"] == "trust_unknown"


@pytest.mark.parametrize("repo,path,key", [
    ("C:/workspace/example", "C:/workspace/example/.codex/hooks.json",
     "c:\\WORKSPACE\\example\\.codex\\hooks.json:stop:0:0"),
    ("/workspace/example", "/workspace/example/.codex/hooks.json",
     "/workspace/example/.codex/hooks.json:stop:0:0"),
])
def test_fake_server_windows_and_posix_keys_match_exact_identity(tmp_path, fake_server, repo, path, key):
    metadata = _metadata(path)
    metadata["key"] = key
    fake_server[0](response={"data": [{"cwd": repo, "hooks": [metadata], "errors": [], "warnings": []}]})
    response = trust._query_hooks(tmp_path, trust._resolve_codex(None), 5)
    rows = [trust._row("Stop", 0, 0, "trust_unknown", "pending")]
    trust._apply_response(rows, repo, path, response)
    assert rows[0]["state"] == "installed_trusted" and rows[0]["adopted"] is True


def test_duplicate_key_is_unknown(tmp_path, fake_server):
    path = _write_hooks(tmp_path)
    metadata = _both(path)
    fake_server[0](hooks=[*metadata, metadata[1]])
    assert trust.inspect_codex_hook_trust(tmp_path)["state"] == "trust_unknown"


@pytest.mark.parametrize("content", ["not json", "[]", '{"hooks": []}', '{"hooks":{"Stop":[{}]}}'])
def test_malformed_hooks_are_unknown_without_spawning(tmp_path, monkeypatch, content):
    path = _write_hooks(tmp_path)
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(trust, "_resolve_codex", lambda explicit: pytest.fail("must not spawn"))
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "trust_unknown" and not report["probe_attempted"]


def test_unreadable_hooks_are_unknown(tmp_path, monkeypatch):
    path = _write_hooks(tmp_path)
    original = Path.read_bytes

    def read_bytes(selected):
        if selected == path:
            raise PermissionError("fixture")
        return original(selected)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "trust_unknown" and not report["adopted"]


def test_missing_binary_is_unknown_and_never_installed(tmp_path):
    _write_hooks(tmp_path)
    report = trust.inspect_codex_hook_trust(tmp_path, codex_binary=tmp_path / "missing-codex")
    assert report["state"] == "trust_unknown" and not report["probe_attempted"]


@pytest.mark.parametrize("explicit,env,selected", [
    ("explicit-codex", "env-codex", "explicit-codex"),
    (None, "env-codex", "env-codex"), (None, "", "codex"),
])
def test_binary_resolution_honors_explicit_then_env_then_path(monkeypatch, explicit, env, selected):
    calls = []
    monkeypatch.setenv("CODEX_BINARY", env)
    monkeypatch.setattr(trust.shutil, "which", lambda value: calls.append(value) or sys.executable)
    assert trust._resolve_codex(explicit) == [str(Path(sys.executable).resolve())]
    assert calls == [selected]


def test_failed_start_is_unknown(tmp_path, monkeypatch):
    _write_hooks(tmp_path)
    monkeypatch.setattr(trust.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("fixture")))
    report = trust.inspect_codex_hook_trust(tmp_path, codex_binary=sys.executable)
    assert report["state"] == "trust_unknown" and not report["adopted"]


def test_definitions_changed_during_probe_are_unknown(tmp_path, fake_server, monkeypatch):
    path = _write_hooks(tmp_path)
    fake_server[0](hooks=_both(path))
    original = trust._query_hooks

    def changed(*args):
        result = original(*args)
        _write_hooks(tmp_path, command="edited during probe")
        return result

    monkeypatch.setattr(trust, "_query_hooks", changed)
    report = trust.inspect_codex_hook_trust(tmp_path)
    assert report["state"] == "trust_unknown" and not report["adopted"]


def test_cli_reports_untrusted_without_blocking(tmp_path, fake_server, capsys):
    path = _write_hooks(tmp_path)
    fake_server[0](hooks=_both(path, status="untrusted"))
    assert trust.main(["--repo", str(tmp_path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["state"] == "installed_untrusted" and not report["adopted"]
    assert "R1/R2" in report["claim_boundary"]
