import base64
import builtins
import io
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from runtime_hooks.adapters.codex import session_start
from runtime_hooks.adapters.codex.session_start import hook_payload, install, run
from runtime_hooks.core._canonical_closeout import read_session_envelope, write_candidate, assess_session_closeout_binding, write_closeout_completion_marker


@pytest.fixture(autouse=True)
def memory_delivery_off_by_default(monkeypatch):
    monkeypatch.delenv("AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY", raising=False)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "consumer's space path"
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    return root.resolve()


def event(repo, source="startup", sid="known-session"):
    return {"hook_event_name": "SessionStart", "source": source,
            "session_id": sid, "cwd": str(repo)}


def test_identity_survives_all_sources_and_keeps_candidate_bound(repo):
    first = run(event(repo), repo)
    envelope_path = Path(first["session_envelope_path"])
    before = envelope_path.read_bytes()
    write_candidate("known-session", repo, dict(task_intent="task", work_summary="work",
                    tools_used=["inspect"], artifacts_referenced=[], open_risks=[]))
    candidate = next((repo/"artifacts/runtime/closeout_candidates/known-session").glob("*.json"))
    for source in ["startup", "resume", "compact", "clear", "resume"]:
        assert run(event(repo, source), repo)["status"] == "preserved"
        assert envelope_path.read_bytes() == before
        assert assess_session_closeout_binding("known-session", repo, json.loads(candidate.read_text()))["status"] == "valid"
        assert json.loads((repo/"artifacts/runtime/.current-session-id").read_text())["session_id"] == "known-session"


def test_consumption_record_never_rewritten(repo):
    result = run(event(repo), repo)
    path = write_closeout_completion_marker("known-session", repo, [Path(result["session_envelope_path"])])
    before = path.read_bytes()
    identity = Path(result["session_envelope_path"]).read_bytes()
    run(event(repo, "compact"), repo)
    assert path.read_bytes() == before
    assert Path(result["session_envelope_path"]).read_bytes() == identity
    assert assess_session_closeout_binding("known-session", repo, None)["status"] == "already_consumed"


def test_start_compact_closeout_and_resume_preserve_identity(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    first = run(event(repo), repo)
    envelope = Path(first["session_envelope_path"]).read_bytes()
    (repo/"evidence.txt").write_text("isolated lifecycle test")
    write_candidate("known-session", repo, dict(task_intent="Known lifecycle task",
        work_summary="Inspected evidence.txt for lifecycle validation", tools_used=["inspect"],
        artifacts_referenced=["evidence.txt"], open_risks=[]))
    (repo/"artifacts/session-closeout.txt").write_text(
        "TASK_INTENT: Known lifecycle task\n"
        "WORK_COMPLETED: Inspected evidence.txt for lifecycle validation\n"
        "FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n"
        "NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n")
    run(event(repo, "compact"), repo)
    result = run_session_end_hook(repo, hook_session_id="known-session", ledger_write_allowed=False)
    assert result["closeout_status"] == "valid"
    canonical = json.loads((repo/"artifacts/runtime/closeouts/known-session.json").read_text())
    assert canonical["task_intent"] == "Known lifecycle task"
    assert canonical["work_summary"] == "Inspected evidence.txt for lifecycle validation"
    run(event(repo, "resume"), repo)
    assert Path(first["session_envelope_path"]).read_bytes() == envelope
    assert assess_session_closeout_binding("known-session", repo, None)["status"] == "already_consumed"


@pytest.mark.parametrize("source", ["resume", "compact"])
def test_missing_resume_identity_is_not_invented(repo, source):
    with pytest.raises(ValueError, match="Existing envelope required"):
        run(event(repo, source), repo)
    assert not (repo/"artifacts").exists()


def test_distinct_new_session_and_subdirectory(repo):
    run(event(repo), repo)
    child = repo/"src"; child.mkdir()
    payload = event(child, "clear", "new-session")
    assert run(payload, repo)["status"] == "created"
    assert read_session_envelope("known-session", repo)["session_id"] == "known-session"
    assert read_session_envelope("new-session", repo)["session_id"] == "new-session"


def test_wrong_root_rejected_without_writes(repo, tmp_path):
    other = tmp_path/"other"
    subprocess.run(["git", "init", str(other)], check=True, capture_output=True)
    with pytest.raises(ValueError, match="do not match"):
        run(event(other), repo)
    assert not (repo/"artifacts").exists()
    assert not (other/"artifacts").exists()


@pytest.mark.parametrize("sid", ["", "../escape", "a/b", "a\\b", "COM1"])
def test_invalid_identity_rejected(repo, sid):
    with pytest.raises(ValueError, match="session_id"):
        run(event(repo, sid=sid), repo)
    assert not (repo/"artifacts").exists()


def test_corrupt_envelope_not_overwritten(repo):
    path = repo/"artifacts/runtime/sessions/known-session/session-envelope.json"
    path.parent.mkdir(parents=True); path.write_text('{"invalid":true}')
    with pytest.raises(ValueError, match="invalid"):
        run(event(repo), repo)
    assert path.read_text() == '{"invalid":true}'


def test_missing_identity_with_completion_not_recreated(repo):
    path = repo/"artifacts/runtime/closeout-completions/known-session.json"
    path.parent.mkdir(parents=True); path.write_text('{}')
    with pytest.raises(ValueError, match="Completion marker"):
        run(event(repo), repo)
    assert read_session_envelope("known-session", repo) is None
    assert path.read_text() == '{}'


def test_foreign_event_never_creates_identity(repo):
    payload = event(repo); payload["hook_event_name"] = "Stop"
    with pytest.raises(ValueError, match="SessionStart"):
        run(payload, repo)
    assert not (repo/"artifacts").exists()


def test_concurrent_event_does_not_reset_identity(repo):
    path = repo/"artifacts/runtime/sessions/known-session/.codex-start.lock"
    path.parent.mkdir(parents=True); path.touch()
    with pytest.raises(ValueError, match="already running"):
        run(event(repo), repo)
    assert path.exists()
    assert not (path.parent/"session-envelope.json").exists()


def test_installer_adds_only_start_preserves_stop_and_is_idempotent(repo):
    path = repo/".codex/hooks.json"; path.parent.mkdir()
    original = {"description":"consumer", "hooks":{"Stop":[{"hooks":[{"type":"command","command":"original stop"}]}],
                "SessionStart":[{"matcher":"startup","hooks":[{"command":"consumer custom"}]}]}}
    path.write_text(json.dumps(original))
    assert install(repo)["status"] == "installed"
    installed = json.loads(path.read_text())
    assert installed["hooks"]["Stop"] == original["hooks"]["Stop"]
    assert installed["hooks"]["SessionStart"][0] == original["hooks"]["SessionStart"][0]
    before = path.read_bytes()
    assert install(repo)["status"] == "already_installed"
    assert path.read_bytes() == before


def test_installer_refuses_changed_owned_binding(repo):
    install(repo)
    path = repo/".codex/hooks.json"
    data = json.loads(path.read_text())
    data["hooks"]["SessionStart"][0]["matcher"] = "startup"
    path.write_text(json.dumps(data)); before = path.read_bytes()
    with pytest.raises(ValueError, match="differs"):
        install(repo)
    assert path.read_bytes() == before


def test_installer_preserves_invalid_json_for_inspection(repo):
    path = repo/".codex/hooks.json"; path.parent.mkdir(); path.write_text('{')
    with pytest.raises(ValueError):
        install(repo)
    assert path.read_text() == '{'


def test_cli_consumes_native_json_without_generated_id(repo):
    entry = Path(__file__).resolve().parents[1]/"runtime_hooks/adapters/codex/session_start.py"
    result = subprocess.run([sys.executable,str(entry),"--project-root",str(repo)],
                            input=json.dumps(event(repo)),text=True,capture_output=True,timeout=15)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {}
    assert read_session_envelope("known-session",repo)["provider"] == "codex"


@pytest.mark.skipif(os.name != "nt", reason="Windows native transport")
def test_installed_windows_command_transports_stdin_and_space_paths(repo):
    install(repo)
    config = json.loads((repo/".codex/hooks.json").read_text())
    command = config["hooks"]["SessionStart"][0]["hooks"][0]["commandWindows"]
    for source in ("startup","resume","compact"):
        result = subprocess.run([shutil.which("powershell.exe"),"-NoProfile","-Command",command+"; exit $LASTEXITCODE"],
            cwd=repo,input=json.dumps(event(repo,source)),text=True,capture_output=True,timeout=20)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {}
        envelope = read_session_envelope("known-session", repo)
        if source == "startup": original = envelope
        assert envelope == original


def _invoke_main(repo, monkeypatch, *args, raw_payload=None):
    monkeypatch.setattr(sys, "argv", ["session_start.py", "--project-root", str(repo), *args])
    monkeypatch.setattr(sys, "stdin", io.StringIO(
        json.dumps(event(repo)) if raw_payload is None else raw_payload))
    return session_start.main()


@pytest.fixture
def delivery_hooks(monkeypatch):
    from runtime_hooks.core import memory_delivery

    delivery = {
        "inject": True, "reason": "verified", "fallback": None,
        "payload": "[WORKING_STATE_DATA]\nsource: canonical_closeout\nstate: valid",
        "telemetry": {"elapsed_ms": 0.25, "files_read_count": 3, "payload_chars": 60,
                      "fallback_to_original_read": False},
    }
    build = Mock(return_value=delivery)
    formatter = Mock(wraps=memory_delivery.format_platform_envelope)
    monkeypatch.setattr(memory_delivery, "build_memory_delivery", build)
    monkeypatch.setattr(memory_delivery, "format_platform_envelope", formatter)
    return build, formatter, delivery


@pytest.mark.parametrize("env_value", [None, "0", "true", " 1 "])
def test_main_default_off_preserves_identity_audit_and_empty_stdout(
    repo, monkeypatch, capsys, delivery_hooks, env_value,
):
    if env_value is not None:
        monkeypatch.setenv("AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY", env_value)
    assert _invoke_main(repo, monkeypatch) == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    audit = json.loads(captured.err)
    assert audit == {
        "status": "created", "session_id": "known-session", "project_root": str(repo),
        "session_envelope_path": str(repo / "artifacts/runtime/sessions/known-session/session-envelope.json"),
        "envelope_schema_version": "1.1",
    }
    assert read_session_envelope("known-session", repo)["provider"] == "codex"
    build, formatter, _ = delivery_hooks
    build.assert_not_called()
    formatter.assert_not_called()


def test_main_default_off_does_not_import_optional_delivery(repo, monkeypatch, capsys):
    original_import = builtins.__import__

    def forbid_delivery(name, *args, **kwargs):
        if name == "runtime_hooks.core.memory_delivery":
            raise AssertionError("Default OFF must not import memory delivery")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", forbid_delivery)
    assert _invoke_main(repo, monkeypatch, "--memory-delivery-max-chars", "1") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    assert "memory_delivery" not in json.loads(captured.err)


@pytest.mark.parametrize("via_flag, env_value", [(True, "0"), (False, "1"), (True, "1")])
@pytest.mark.parametrize("max_chars", [None, 450])
def test_main_opt_in_delivers_exact_envelope_only_after_binding(
    repo, monkeypatch, capsys, delivery_hooks, via_flag, env_value, max_chars,
):
    build, formatter, delivery = delivery_hooks
    monkeypatch.setenv("AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY", env_value)

    def after_binding(project_root, **kwargs):
        assert project_root == repo
        assert read_session_envelope(kwargs["session_id"], project_root)["provider"] == "codex"
        pointer = json.loads((repo / "artifacts/runtime/.current-session-id").read_text())
        assert pointer["session_id"] == "known-session"
        return delivery

    build.side_effect = after_binding
    args = ["--enable-memory-delivery"] if via_flag else []
    if max_chars is not None:
        args += ["--memory-delivery-max-chars", str(max_chars)]
    assert _invoke_main(repo, monkeypatch, *args) == 0
    captured = capsys.readouterr()
    assert captured.out == json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": delivery["payload"],
    }}) + "\n"
    audit = json.loads(captured.err)
    assert audit["memory_delivery"] == {
        "inject": True, "reason": "verified", "source": "canonical_closeout",
        "self_cost": delivery["telemetry"],
    }
    assert audit["status"] == "created" and audit["session_id"] == "known-session"
    build.assert_called_once_with(repo, session_id="known-session", max_chars=600 if max_chars is None else max_chars)
    formatter.assert_called_once_with(delivery, "codex")


def test_main_delivery_refusal_never_emits_rejected_context(repo, monkeypatch, capsys, delivery_hooks):
    build, formatter, delivery = delivery_hooks
    delivery.update(inject=False, reason="verification_failed", payload="rejected context")
    # Even a non-empty formatter result cannot override the delivery refusal.
    formatter.return_value = {"hookSpecificOutput": {"additionalContext": "rejected context"}}
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    assert json.loads(captured.err)["memory_delivery"] == {
        "inject": False, "reason": "verification_failed", "source": None,
        "self_cost": delivery["telemetry"],
    }
    build.assert_called_once()
    formatter.assert_called_once_with(delivery, "codex")


def test_main_empty_envelope_is_audited_without_injection(repo, monkeypatch, capsys, delivery_hooks):
    _, formatter, delivery = delivery_hooks
    formatter.return_value = {}
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    assert json.loads(captured.err)["memory_delivery"] == {
        "inject": False, "reason": "empty_envelope", "source": "canonical_closeout",
        "self_cost": delivery["telemetry"],
    }


@pytest.mark.parametrize("stage, error", [
    ("build", RuntimeError("unexpected delivery failure")),
    ("build", OSError("unreadable delivery source")),
    ("format", ValueError("unexpected formatting failure")),
])
def test_main_delivery_exceptions_fail_open_after_binding(
    repo, monkeypatch, capsys, delivery_hooks, stage, error,
):
    build, formatter, _ = delivery_hooks
    (build if stage == "build" else formatter).side_effect = error
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    audit = json.loads(captured.err)
    assert audit["status"] == "created"
    assert audit["memory_delivery"] == {
        "inject": False, "reason": f"unexpected_error:{type(error).__name__}",
        "source": None, "self_cost": {},
    }
    assert read_session_envelope("known-session", repo)["provider"] == "codex"
    if stage == "build":
        formatter.assert_not_called()


def test_main_optional_delivery_import_failure_falls_back(repo, monkeypatch, capsys, delivery_hooks):
    original_import = builtins.__import__

    def unavailable_delivery(name, *args, **kwargs):
        if name == "runtime_hooks.core.memory_delivery":
            raise ImportError("Optional memory delivery unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable_delivery)
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    assert json.loads(captured.err)["memory_delivery"] == {
        "inject": False, "reason": "unexpected_error:ImportError", "source": None, "self_cost": {},
    }
    assert read_session_envelope("known-session", repo)["provider"] == "codex"
    build, formatter, _ = delivery_hooks
    build.assert_not_called()
    formatter.assert_not_called()


@pytest.mark.parametrize("case, message", [
    ("invalid_json", "Expecting"), ("non_object", "Expected a SessionStart"),
    ("wrong_event", "Expected a SessionStart"), ("unsupported_source", "Unsupported"),
    ("unsafe_session", "unsafe session_id"), ("wrong_root", "do not match"),
    ("missing_resume", "Existing envelope required"), ("missing_compact", "Existing envelope required"),
    ("lock_failure", "already running"), ("corrupt_envelope", "invalid"),
])
def test_main_opt_in_keeps_identity_failures_closed(
    repo, monkeypatch, capsys, delivery_hooks, tmp_path, case, message,
):
    payload = event(repo)
    session_dir = repo / "artifacts/runtime/sessions/known-session"
    if case == "wrong_event":
        payload["hook_event_name"] = "Stop"
    elif case == "unsupported_source":
        payload["source"] = "unknown"
    elif case == "unsafe_session":
        payload["session_id"] = "../escape"
    elif case == "wrong_root":
        other = tmp_path / "other"
        subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
        payload["cwd"] = str(other)
    elif case in {"missing_resume", "missing_compact"}:
        payload["source"] = case.removeprefix("missing_")
    elif case in {"lock_failure", "corrupt_envelope"}:
        session_dir.mkdir(parents=True)
        path = session_dir / (".codex-start.lock" if case == "lock_failure" else "session-envelope.json")
        path.write_text("preserve invalid state", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in session_dir.glob("*")}
    raw_payload = {"invalid_json": "{", "non_object": "[]"}.get(case, json.dumps(payload))
    monkeypatch.setenv("AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY", "1")
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery", raw_payload=raw_payload) == 1
    captured = capsys.readouterr()
    error = json.loads(captured.out)
    assert set(error) == {"systemMessage"}
    assert error["systemMessage"].startswith("Governance SessionStart failed: ")
    assert message in error["systemMessage"]
    assert captured.err == ""
    assert {p.name: p.read_bytes() for p in session_dir.glob("*")} == before
    assert not (repo / "artifacts/runtime/.current-session-id").exists()
    build, formatter, _ = delivery_hooks
    build.assert_not_called()
    formatter.assert_not_called()


@pytest.mark.parametrize("error_type", [ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError])
def test_main_binding_errors_cannot_enter_memory_fail_open(
    repo, monkeypatch, capsys, delivery_hooks, error_type,
):
    monkeypatch.setattr(session_start, "establish_bound_session", Mock(side_effect=error_type("binding failed")))
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery") == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"systemMessage": "Governance SessionStart failed: binding failed"}
    assert captured.err == ""
    assert not (repo / "artifacts").exists()
    build, formatter, _ = delivery_hooks
    build.assert_not_called()
    formatter.assert_not_called()


@pytest.mark.parametrize("via_flag", [False, True])
def test_cli_opt_in_with_no_source_falls_back_and_preserves_binding(repo, via_flag):
    entry = Path(session_start.__file__)
    args = [sys.executable, str(entry), "--project-root", str(repo)]
    env = os.environ.copy()
    if via_flag:
        args.append("--enable-memory-delivery")
    else:
        env["AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY"] = "1"
    result = subprocess.run(args, input=json.dumps(event(repo)), env=env,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "{}\n"
    audit = json.loads(result.stderr)["memory_delivery"]
    assert audit["inject"] is False and audit["reason"] == "missing_source"
    assert audit["source"] is None
    assert set(audit) == {"inject", "reason", "source", "self_cost"}
    assert audit["self_cost"]["fallback_to_original_read"] is True
    assert read_session_envelope("known-session", repo)["provider"] == "codex"


@pytest.mark.parametrize("via_flag", [False, True])
def test_install_never_delivers_or_adds_opt_in_even_when_enabled(
    repo, monkeypatch, capsys, delivery_hooks, via_flag,
):
    monkeypatch.setenv("AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY", "1")
    args = ["--install"] + (["--enable-memory-delivery"] if via_flag else [])
    assert _invoke_main(repo, monkeypatch, *args, raw_payload="not JSON") == 0
    captured = capsys.readouterr()
    assert captured.out == "{}\n"
    assert json.loads(captured.err)["status"] == "installed"
    assert "memory_delivery" not in json.loads(captured.err)
    assert not (repo / "artifacts").exists()
    installed = json.loads((repo / ".codex/hooks.json").read_text())
    absolute = hook_payload(repo)
    assert installed["hooks"]["SessionStart"] == [{
        "matcher": session_start.SESSION_START_MATCHER, "hooks": [absolute],
    }]
    portable = session_start.portable_hook_payload(repo, repo / "ai-governance-framework")
    assert portable is not None
    for hook in (absolute, portable):
        windows = base64.b64decode(hook["commandWindows"].split()[-1]).decode("utf-16-le")
        for command in (hook["command"], windows):
            assert "--enable-memory-delivery" not in command
            assert "AI_GOVERNANCE_ENABLE_MEMORY_DELIVERY" not in command
            assert "--memory-delivery-max-chars" not in command
    build, formatter, _ = delivery_hooks
    build.assert_not_called()
    formatter.assert_not_called()


@pytest.mark.parametrize("max_chars, reason", [(600, "verified"), (1, "payload_budget_exceeded"),
                                             (0, "invalid_configuration"), (-1, "invalid_configuration")])
def test_main_real_canonical_delivery_and_budget_fallback(repo, monkeypatch, capsys, max_chars, reason):
    from runtime_hooks.core import memory_delivery
    from runtime_hooks.core._canonical_closeout import (
        build_canonical_closeout, write_canonical_closeout, write_session_envelope,
    )

    now = datetime(2026, 11, 28, 12, tzinfo=timezone.utc)
    write_session_envelope("known-session", repo, provider="codex", bound_consumer_root=repo,
                           started_at=(now - timedelta(hours=1)).isoformat())
    (repo / "evidence.txt").write_text("verified evidence", encoding="utf-8")
    canonical = build_canonical_closeout(
        session_id="known-session", closed_at=now.isoformat(),
        candidate_payload={"task_intent": "Deliver session memory", "work_summary": "Evidence is ready.",
                           "tools_used": [], "artifacts_referenced": ["evidence.txt"], "open_risks": []},
        existing_artifacts=frozenset({"evidence.txt"}), runtime_signals={},
    )
    assert canonical["closeout_status"] == "valid"
    path = write_canonical_closeout(canonical, repo)
    os.utime(path, (now.timestamp(), now.timestamp()))
    before = path.read_bytes()
    original_build = memory_delivery.build_memory_delivery

    def fixed_clock_build(*args, **kwargs):
        return original_build(*args, **kwargs, now=now)

    monkeypatch.setattr(memory_delivery, "build_memory_delivery", fixed_clock_build)
    assert _invoke_main(repo, monkeypatch, "--enable-memory-delivery",
                        "--memory-delivery-max-chars", str(max_chars)) == 0
    captured = capsys.readouterr()
    output, audit = json.loads(captured.out), json.loads(captured.err)
    assert audit["status"] == "preserved"
    delivery = audit["memory_delivery"]
    assert delivery["reason"] == reason
    assert delivery["inject"] is (reason == "verified")
    assert path.read_bytes() == before
    if reason == "verified":
        assert set(output) == {"hookSpecificOutput"}
        assert set(output["hookSpecificOutput"]) == {"hookEventName", "additionalContext"}
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        payload = output["hookSpecificOutput"]["additionalContext"]
        assert payload.startswith("[WORKING_STATE_DATA]\n")
        assert "\nsource: canonical_closeout\n" in payload
        assert len(payload) <= max_chars
        assert delivery["source"] == "canonical_closeout"
        assert delivery["self_cost"]["payload_chars"] == len(payload)
        assert delivery["self_cost"]["files_read_count"] == 3
    else:
        assert captured.out == "{}\n"
        assert delivery["source"] is None
        assert delivery["self_cost"]["fallback_to_original_read"] is True
