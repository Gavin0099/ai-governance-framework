"""Accepted closeouts consume once; rejected attempts remain correctable."""
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from runtime_hooks.core import session_end as core
from runtime_hooks.core._canonical_closeout import (
    assess_session_closeout_binding,
    pick_latest_candidate,
    write_candidate,
    write_session_envelope,
)


PROVIDERS = ("claude", "codex", "github-copilot")
SESSION = "completion-integrity"


@pytest.fixture
def synthetic_repo(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    root = tmp_path / "synthetic repo"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / "AGENTS.md").write_text("# Synthetic fixture\n", encoding="utf-8")
    (root / "governance").mkdir()
    (root / "evidence.txt").write_text("Synthetic evidence.\n", encoding="utf-8")
    return root


@pytest.fixture
def repo(synthetic_repo, monkeypatch):
    def forbid_memory(*args, **kwargs):
        pytest.fail("Stateless completion must not reach the memory writer")

    monkeypatch.setattr(core, "_append_daily_memory_entry", forbid_memory)
    return synthetic_repo


def candidate(**overrides):
    return {
        "task_intent": "Inspect synthetic evidence",
        "work_summary": "Inspected evidence.txt.",
        "tools_used": ["inspect"],
        "artifacts_referenced": ["evidence.txt"],
        "open_risks": [],
        **overrides,
    }


def closeout(root, *, with_memory=False):
    return core.run_session_end(
        project_root=root,
        session_id=SESSION,
        runtime_contract={
            "task": "Inspect synthetic evidence",
            "rules": ["common"],
            "risk": "low",
            "oversight": "auto",
            "memory_mode": "candidate" if with_memory else "stateless",
        },
        summary="Inspected evidence.txt.",
        enforce_session_binding=True,
        daily_memory_write_required=with_memory,
        ledger_write_allowed=False,
    )


def marker_path(root):
    return root / "artifacts/runtime/closeout-completions" / f"{SESSION}.json"


def snapshot(root):
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        if path.is_file() else None
        for directory in ("artifacts", "memory")
        for path in (root / directory).rglob("*")
    }


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("overrides, status", [
    ({"tools_used": ["pytest"]}, "inconsistent"),
    ({"artifacts_referenced": ["missing.txt"]}, "inconsistent"),
    ({"work_summary": ""}, "content_insufficient"),
    ({"work_summary": 7}, "schema_invalid"),
])
def test_unaccepted_canonical_can_retry_same_session(repo, provider, overrides, status):
    write_session_envelope(SESSION, repo, provider=provider)
    write_candidate(SESSION, repo, candidate(**overrides), timestamp="000001")

    first = closeout(repo)

    assert first["session_binding"]["status"] == "valid"
    assert first["canonical_closeout"]["closeout_status"] == status
    assert Path(first["canonical_closeout_artifact"]).is_file()
    assert not marker_path(repo).exists()

    write_candidate(SESSION, repo, candidate(), timestamp="000002")
    corrected = closeout(repo)

    assert corrected["ok"] is True
    assert corrected["session_binding"]["status"] == "valid"
    assert corrected["canonical_closeout"]["closeout_status"] == "valid"
    assert marker_path(repo).is_file()


@pytest.mark.parametrize("provider", PROVIDERS)
def test_accepted_closeout_records_digest_and_replays_without_writes(repo, provider):
    write_session_envelope(SESSION, repo, provider=provider)
    write_candidate(SESSION, repo, candidate())
    accepted = closeout(repo)
    canonical_path = Path(accepted["canonical_closeout_artifact"])
    marker = json.loads(marker_path(repo).read_text(encoding="utf-8"))

    assert accepted["ok"] is True
    assert accepted["canonical_closeout"]["closeout_status"] == "valid"
    assert marker["canonical_closeout_sha256"] == hashlib.sha256(canonical_path.read_bytes()).hexdigest()
    before = snapshot(repo)

    replay = closeout(repo)

    assert replay["ok"] is True
    assert replay["decision"] == "ALREADY_CONSUMED"
    assert replay["canonical_closeout"] == accepted["canonical_closeout"]
    assert replay["daily_memory_write_attempted"] is False
    assert snapshot(repo) == before


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("malformed", [False, True])
def test_changed_accepted_closeout_is_not_accepted_or_rewritten(repo, provider, malformed):
    write_session_envelope(SESSION, repo, provider=provider)
    write_candidate(SESSION, repo, candidate())
    accepted = closeout(repo)
    canonical_path = Path(accepted["canonical_closeout_artifact"])
    changed = {**accepted["canonical_closeout"], "work_summary": "Changed after completion."}
    canonical_path.write_bytes(b"{broken" if malformed else json.dumps(changed).encode("utf-8"))
    before = snapshot(repo)

    replay = closeout(repo)

    assert replay["ok"] is False
    assert replay["decision"] == "CLOSEOUT_REPLAY_MISMATCH"
    assert replay["policy"] == {"decision": "STOP", "reason": "canonical_closeout_digest_mismatch"}
    assert replay["session_binding"]["status"] == "already_consumed"
    assert replay["canonical_closeout"]["closeout_status"] != "valid"
    assert replay["errors"]
    assert replay["daily_memory_write_attempted"] is False
    assert snapshot(repo) == before


@pytest.mark.parametrize("entry", ["core", "hook"])
@pytest.mark.parametrize("marker_state, missing", [
    ("digest", ("closeouts",)),
    ("digest", ("traces",)),
    ("digest", ("closeouts", "traces")),
    ("legacy", ("closeouts", "traces")),
    ("no-marker", ("closeouts", "traces")),
])
def test_missing_accepted_artifacts_replay(synthetic_repo, monkeypatch, entry, marker_state, missing):
    from governance_tools import session_end_hook
    from governance_tools.prepare_closeout_candidate import render_inputs

    repo = synthetic_repo
    monkeypatch.setenv("AI_GOVERNANCE_NO_LEDGER_WRITE", "1")
    (repo / "governance/gate_policy.yaml").write_text("fail_mode: audit\n", encoding="utf-8")
    (repo / "PLAN.md").write_text(
        f"> **Last Updated**: {date.today().isoformat()}\n"
        "> **Owner**: Fixture\n> **Freshness**: Sprint (7d)\n", encoding="utf-8",
    )
    write_session_envelope(SESSION, repo, provider="codex", bound_consumer_root=repo)
    inputs = candidate()
    write_candidate(SESSION, repo, inputs)
    _, text = render_inputs({**inputs, "checks_run": "NONE"})
    (repo / "artifacts/session-closeout.txt").write_bytes(text)

    def run():
        if entry == "core":
            return closeout(repo)
        return session_end_hook.run_session_end_hook(repo, hook_session_id=SESSION)

    accepted = run()
    assert accepted["ok"] is True, accepted
    canonical = repo / "artifacts/runtime/closeouts" / f"{SESSION}.json"
    marker = marker_path(repo)
    completion = json.loads(marker.read_bytes())
    assert completion["canonical_closeout_sha256"] == hashlib.sha256(canonical.read_bytes()).hexdigest()
    for directory in missing:
        relative = f"artifacts/runtime/{directory}/{SESSION}.json"
        assert relative in {Path(path).as_posix() for path in completion["required_artifacts"]}
        (repo / relative).unlink()
    if marker_state == "legacy":
        del completion["canonical_closeout_sha256"]
        marker.write_text(json.dumps(completion), encoding="utf-8")
    elif marker_state == "no-marker":
        marker.unlink()
    before = snapshot(repo)

    replay = run()

    if marker_state == "digest":
        assert replay["decision"] == "CLOSEOUT_REPLAY_MISMATCH", replay
        assert replay["ok"] is False
        assert replay["session_binding"]["status"] == "already_consumed"
        assert replay["daily_memory_write_attempted"] is False
        assert snapshot(repo) == before
    else:
        assert replay["ok"] is True, replay
        assert replay["session_binding"]["status"] == "valid"
        assert canonical.is_file()
        assert json.loads(marker.read_bytes())["canonical_closeout_sha256"] == hashlib.sha256(
            canonical.read_bytes()
        ).hexdigest()


@pytest.mark.parametrize("entry", ["hook", "cli"])
@pytest.mark.parametrize("marker_bytes", [
    pytest.param(b"[]", id="array"),
    pytest.param(b'"x"', id="string"),
    pytest.param(b"{broken", id="invalid-json"),
    pytest.param(b"{}", id="missing-identity"),
    pytest.param(b'{"session_id":"completion-integrity","required_artifacts":[]}', id="invalid-legacy"),
    pytest.param(None, id="unreadable"),
])
def test_invalid_completion_marker_refuses_replay(synthetic_repo, monkeypatch, capsys, entry, marker_bytes):
    from governance_tools import session_end_hook
    from governance_tools.prepare_closeout_candidate import render_inputs

    repo = synthetic_repo
    monkeypatch.setenv("AI_GOVERNANCE_NO_LEDGER_WRITE", "1")
    (repo / "governance/gate_policy.yaml").write_text("fail_mode: audit\n", encoding="utf-8")
    write_session_envelope(SESSION, repo, provider="codex", bound_consumer_root=repo)
    inputs = candidate()
    write_candidate(SESSION, repo, inputs)
    _, closeout_text = render_inputs({**inputs, "checks_run": "NONE"})
    (repo / "artifacts/session-closeout.txt").write_bytes(closeout_text)
    assert closeout(repo)["ok"] is True
    marker = marker_path(repo)
    if marker_bytes is None:
        read_text = Path.read_text

        def deny_marker_read(path, *args, **kwargs):
            if path == marker:
                raise PermissionError("Synthetic unreadable completion marker")
            return read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", deny_marker_read)
    else:
        marker.write_bytes(marker_bytes)

    contract = repo / "runtime-contract.json"
    contract.write_text(json.dumps({
        "task": inputs["task_intent"],
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "stateless",
    }), encoding="utf-8")
    before = snapshot(repo)

    if entry == "hook":
        report = session_end_hook.run_session_end_hook(repo, hook_session_id=SESSION)
    else:
        monkeypatch.setattr(sys, "argv", [
            "session_end", "--project-root", str(repo), "--session-id", SESSION,
            "--runtime-contract-file", str(contract), "--format", "json", "--no-ledger-write",
        ])
        with pytest.raises(SystemExit) as exc:
            core.main()
        report = json.loads(capsys.readouterr().out)
        assert exc.value.code == 1, report

    assert report["decision"] == "CLOSEOUT_REPLAY_MISMATCH", report
    assert report["ok"] is False
    assert report["session_binding"]["status"] == "completion_marker_invalid"
    assert report["daily_memory_write_attempted"] is False
    assert snapshot(repo) == before


@pytest.mark.parametrize("entry, provider", [
    ("copilot-cli", "github-copilot"),
    ("copilot-shared-vscode", "github-copilot-vscode"),
    ("entry-run", "codex"),
    ("hook-cli", "github-copilot"),
    ("powershell-wrapper", "github-copilot"),
])
def test_real_entry_refuses_changed_accepted_closeout(
    synthetic_repo, monkeypatch, capsys, entry, provider,
):
    from governance_tools import session_closeout_entry, session_end_hook
    from governance_tools.prepare_closeout_candidate import render_inputs
    from runtime_hooks.adapters.copilot import lifecycle

    root = synthetic_repo
    framework = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AI_GOVERNANCE_NO_LEDGER_WRITE", "1")
    monkeypatch.setenv("AI_GOVERNANCE_FRAMEWORK_ROOT", str(framework))
    home = root.with_name("fixture-home")
    home.mkdir()
    for name in ("HOME", "USERPROFILE", "COPILOT_HOME"):
        monkeypatch.setenv(name, str(home))
    (root / "governance/gate_policy.yaml").write_text("fail_mode: audit\n", encoding="utf-8")
    (root / "PLAN.md").write_text(
        f"> **Last Updated**: {date.today().isoformat()}\n"
        "> **Owner**: Fixture\n> **Freshness**: Sprint (7d)\n", encoding="utf-8",
    )
    write_session_envelope(SESSION, root, provider=provider, bound_consumer_root=root)
    inputs = candidate()
    write_candidate(SESSION, root, inputs)
    _, text = render_inputs({**inputs, "checks_run": "NONE"})
    (root / "artifacts/session-closeout.txt").write_bytes(text)
    accepted = session_end_hook.run_session_end_hook(root, hook_session_id=SESSION)
    assert accepted["ok"] is True and accepted["closeout_status"] == "valid", accepted
    assert not list((root / "artifacts").glob("codeburn*.db"))
    canonical = root / "artifacts/runtime/closeouts" / f"{SESSION}.json"
    original = canonical.read_bytes()
    marker = json.loads(marker_path(root).read_bytes())
    assert marker["canonical_closeout_sha256"] == hashlib.sha256(original).hexdigest()
    canonical.write_bytes(original + b"\n")
    assert json.loads(original) == json.loads(canonical.read_bytes())
    assert not (root / "artifacts/runtime/shared-closeout/owner.json").exists()

    def tree():
        return {path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
                if path.is_file() else None for path in root.rglob("*")}

    before = tree()
    capsys.readouterr()
    exit_code = None
    if entry.startswith("copilot-"):
        identity = (
            {"sessionId": SESSION, "hookEventName": "sessionEnd"}
            if entry == "copilot-cli"
            else {"session_id": SESSION, "hook_event_name": "SessionEnd"}
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({**identity, "cwd": str(root)})))
        exit_code = lifecycle.main(["--event-type", "session_end", "--surface", "auto"])
        report = json.loads(capsys.readouterr().out)
        assert report["status"] == "session_end_invoked", report
        assert report["session_binding_status"] == "already_consumed"
        assert report["surface"] == ("copilot" if entry == "copilot-cli" else "vscode")
        assert report["provider"] == provider
    elif entry == "entry-run":
        report = session_closeout_entry.run(root, hook_session_id=SESSION)
    elif entry == "hook-cli":
        monkeypatch.setattr(sys, "argv", ["session_end_hook", "--project-root", str(root), "--format", "json"])
        exit_code = session_end_hook.main()
        report = json.loads(capsys.readouterr().out)
    else:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            pytest.skip("PowerShell is not installed")
        env = {
            **os.environ,
            "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.environ["PATH"])),
            "PYTHONPATH": os.pathsep.join(filter(None, (str(framework), os.environ.get("PYTHONPATH")))),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
        command = [shell, "-NoProfile", "-File", str(framework / "scripts/run_closeout.ps1")]
        if os.name == "nt":
            command[2:2] = ["-ExecutionPolicy", "Bypass"]
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=60)
        assert "decision=CLOSEOUT_REPLAY_MISMATCH" in completed.stdout, completed.stdout + completed.stderr
        assert "ok=False" in completed.stdout, completed.stdout + completed.stderr
        assert completed.returncode == 1, completed.stdout + completed.stderr
        assert tree() == before
        return

    assert report["decision"] == "CLOSEOUT_REPLAY_MISMATCH", report
    assert report["ok"] is False
    if exit_code is not None:
        assert exit_code == 1
    assert tree() == before


@pytest.mark.parametrize("state", [
    "tampered", "intact", "legacy", "no-marker", "missing-trace", "missing-canonical-and-trace",
])
def test_standalone_cli_completion_replay(repo, state):
    write_session_envelope(SESSION, repo, provider="codex")
    write_candidate(SESSION, repo, candidate())
    marker = marker_path(repo)
    canonical = repo / "artifacts/runtime/closeouts" / f"{SESSION}.json"
    if state != "no-marker":
        accepted = closeout(repo)
        assert accepted["ok"] is True, accepted
        original = canonical.read_bytes()
        completion = json.loads(marker.read_bytes())
        assert completion["canonical_closeout_sha256"] == hashlib.sha256(original).hexdigest()
        if state == "legacy":
            del completion["canonical_closeout_sha256"]
            marker.write_text(json.dumps(completion), encoding="utf-8")
        if state in {"tampered", "legacy"}:
            canonical.write_bytes(original + b"\n")
        if state in {"missing-trace", "missing-canonical-and-trace"}:
            trace = f"artifacts/runtime/traces/{SESSION}.json"
            assert trace in {Path(path).as_posix() for path in completion["required_artifacts"]}
            (repo / trace).unlink()
        if state == "missing-canonical-and-trace":
            canonical.unlink()

    contract = repo / "runtime-contract.json"
    contract.write_text(json.dumps({
        "task": "Inspect synthetic evidence",
        "rules": ["common"],
        "risk": "low",
        "oversight": "auto",
        "memory_mode": "stateless",
    }), encoding="utf-8")
    before = snapshot(repo)
    framework = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(framework), "PYTHONUTF8": "1"}
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "runtime_hooks.core.session_end",
         "--project-root", str(repo), "--session-id", SESSION,
         "--runtime-contract-file", str(contract), "--format", "json", "--no-ledger-write"],
        cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert completed.stdout, completed.stderr
    report = json.loads(completed.stdout)
    if state not in {"legacy", "no-marker"}:
        assert report["decision"] == (
            "ALREADY_CONSUMED" if state == "intact" else "CLOSEOUT_REPLAY_MISMATCH"
        ), report
        assert report["ok"] is (state == "intact")
        assert completed.returncode == (0 if state == "intact" else 1)
        assert report["session_binding"]["status"] == "already_consumed"
        assert report["runtime_completeness"]["canonical_closeout_written"] is False
        assert report["daily_memory_write_attempted"] is False
        assert snapshot(repo) == before
    else:
        assert completed.returncode == 0, report
        assert report["ok"] is True
        assert report["decision"] == "DO_NOT_PROMOTE"
        assert report["session_binding"] == {"status": "not_enforced", "session_id": SESSION}
        assert report["runtime_completeness"]["canonical_closeout_written"] is True
        assert report["daily_memory_write_attempted"] is False
        assert json.loads(marker.read_bytes())["canonical_closeout_sha256"] == hashlib.sha256(
            canonical.read_bytes()
        ).hexdigest()
        if state == "legacy":
            assert canonical.read_bytes() != original + b"\n"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_legacy_marker_without_digest_keeps_existing_replay(repo, provider):
    write_session_envelope(SESSION, repo, provider=provider)
    write_candidate(SESSION, repo, candidate())
    accepted = closeout(repo)
    marker = marker_path(repo)
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload.pop("canonical_closeout_sha256", None)
    marker.write_text(json.dumps(payload), encoding="utf-8")
    changed = {**accepted["canonical_closeout"], "work_summary": "Legacy replay content."}
    Path(accepted["canonical_closeout_artifact"]).write_text(json.dumps(changed), encoding="utf-8")
    before = snapshot(repo)

    replay = closeout(repo)

    assert replay["ok"] is True
    assert replay["decision"] == "ALREADY_CONSUMED"
    assert replay["canonical_closeout"] == changed
    assert snapshot(repo) == before


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("phase", ["readback", "marker"])
@pytest.mark.parametrize("malformed", [False, True])
def test_canonical_changed_before_completion_is_retryable(repo, monkeypatch, provider, phase, malformed):
    write_session_envelope(SESSION, repo, provider=provider)
    write_candidate(SESSION, repo, candidate())
    canonical_path = repo / "artifacts/runtime/closeouts" / f"{SESSION}.json"
    before_failure = None

    def change_canonical():
        nonlocal before_failure
        changed = json.loads(canonical_path.read_bytes())
        changed["work_summary"] = "Not the validated summary."
        canonical_path.write_bytes(b"{broken" if malformed else json.dumps(changed).encode("utf-8"))
        before_failure = snapshot(repo)

    with monkeypatch.context() as m:
        if phase == "readback":
            original = core.write_canonical_closeout

            def changed_write(*args, **kwargs):
                path = original(*args, **kwargs)
                change_canonical()
                return path

            m.setattr(core, "write_canonical_closeout", changed_write)
        else:
            original = core.write_closeout_completion_marker

            def changed_marker(*args, **kwargs):
                change_canonical()
                return original(*args, **kwargs)

            m.setattr(core, "write_closeout_completion_marker", changed_marker)
        rejected = closeout(repo)

    assert rejected["ok"] is False
    assert rejected["decision"] == "CLOSEOUT_ACCEPTANCE_MISMATCH"
    assert rejected["policy"] == {
        "decision": "STOP",
        "reason": "canonical_closeout_readback_mismatch" if phase == "readback"
        else "canonical_closeout_changed_before_completion",
    }
    assert any("not accepted" in error for error in rejected["errors"])
    assert rejected["canonical_closeout_artifact"] == str(canonical_path)
    assert not marker_path(repo).exists()
    assert assess_session_closeout_binding(SESSION, repo, pick_latest_candidate(SESSION, repo))["status"] == "valid"
    assert before_failure is not None
    assert snapshot(repo) == before_failure

    corrected = closeout(repo)

    assert corrected["ok"] is True
    assert corrected["session_binding"]["status"] == "valid"
    assert corrected["canonical_closeout"]["closeout_status"] == "valid"
    assert marker_path(repo).is_file()


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_digest_uses_emitted_lf_or_crlf_bytes(repo, monkeypatch, newline):
    write_session_envelope(SESSION, repo, provider="codex")
    write_candidate(SESSION, repo, candidate())
    original = core.write_canonical_closeout

    def write_with_newline(*args, **kwargs):
        path = original(*args, **kwargs)
        text = path.read_text(encoding="utf-8")
        with path.open("w", encoding="utf-8", newline=newline) as stream:
            stream.write(text)
        return path

    monkeypatch.setattr(core, "write_canonical_closeout", write_with_newline)
    accepted = closeout(repo)
    data = Path(accepted["canonical_closeout_artifact"]).read_bytes()
    marker = json.loads(marker_path(repo).read_bytes())

    assert accepted["ok"] is True
    assert (b"\r\n" in data) == (newline == "\r\n")
    assert json.loads(data) == accepted["canonical_closeout"]
    assert marker["canonical_closeout_sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("tampered", [False, True])
def test_replay_preserves_existing_work_record(synthetic_repo, provider, tampered):
    root = synthetic_repo
    write_session_envelope(SESSION, root, provider=provider)
    write_candidate(SESSION, root, candidate())
    accepted = closeout(root, with_memory=True)
    daily = Path(accepted["daily_memory_path"])
    assert accepted["daily_memory_write_status"] == "written"
    assert daily.read_bytes().count(b"Summary: Inspected evidence.txt.") == 1
    if tampered:
        changed = {**accepted["canonical_closeout"], "work_summary": "Changed after completion."}
        Path(accepted["canonical_closeout_artifact"]).write_bytes(json.dumps(changed).encode("utf-8"))
    before = snapshot(root)

    replay = closeout(root, with_memory=True)

    assert replay["ok"] is (not tampered)
    assert replay["decision"] == ("CLOSEOUT_REPLAY_MISMATCH" if tampered else "ALREADY_CONSUMED")
    assert replay["daily_memory_write_attempted"] is False
    assert daily.read_bytes().count(b"Summary: Inspected evidence.txt.") == 1
    assert snapshot(root) == before


def test_missing_required_artifact_prevents_completion(repo, monkeypatch):
    write_session_envelope(SESSION, repo, provider="codex")
    write_candidate(SESSION, repo, candidate())
    original = core.write_closeout_completion_marker

    def remove_required_artifact(*args, **kwargs):
        (repo / "artifacts/runtime/verdicts" / f"{SESSION}.json").unlink()
        return original(*args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(core, "write_closeout_completion_marker", remove_required_artifact)
        failed = closeout(repo)

    assert failed["ok"] is False
    assert any("requires emitted artifacts" in error for error in failed["errors"])
    assert not marker_path(repo).exists()
    assert assess_session_closeout_binding(SESSION, repo, pick_latest_candidate(SESSION, repo))["status"] == "valid"
    assert closeout(repo)["ok"] is True
    assert marker_path(repo).is_file()
