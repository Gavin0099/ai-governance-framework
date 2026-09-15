import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from runtime_hooks.adapters.codex.session_start import hook_payload, install, run
from runtime_hooks.core._canonical_closeout import read_session_envelope, write_candidate, assess_session_closeout_binding, write_closeout_completion_marker


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
