"""VS Code Copilot Stop is an execution point for an already prepared closeout (ruling 2026-11-11).

Stop fires at the end of every agent turn. It never prepares a candidate, never releases
ownership on its own and never infers session end. Only when this VS Code session is the R2
owner of a prepared candidate does it run the protected closeout entry, which first checks
the VS Code root-bound identity and that the transcript is the Copilot runtime's own record
of this session in this consumer. Anything else refuses with no state change.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from governance_tools import copilot_session_state as state
from governance_tools import shared_closeout_ownership as own
from runtime_hooks.adapters.copilot.lifecycle import run_lifecycle_event
from tests.test_shared_closeout_ownership import owner, prepare, repo  # noqa: F401 - fixture

SID = "vscode-stop-a"


@pytest.fixture(autouse=True)
def copilot_home(tmp_path_factory, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    home = tmp_path_factory.mktemp("copilot-home")
    monkeypatch.setenv("COPILOT_HOME", str(home))
    return home


def register(sid, client="vscode-agent-host", *, record_id=None):
    directory = state.session_state_dir(sid)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "workspace.yaml").write_text(
        f"id: {record_id or sid}\nclient_name: {client}\n", encoding="utf-8")
    return directory


def transcript(root, sid=SID, *, records=None, cwd=None):
    """The runtime's events.jsonl shape: session.start first, then tool records."""
    where = str(cwd or root)
    rows = records if records is not None else [
        {"type": "session.start", "data": {"sessionId": sid, "context": {"cwd": where, "gitRoot": where}}},
        {"type": "tool.execution_start", "data": {"toolName": "read_file",
                                                   "input": {"sessionId": sid, "cwd": where}}},
        {"type": "tool.execution_complete", "data": {"workingDirectory": where}},
    ]
    path = state.session_state_dir(sid) / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))
    return path


def start_vscode(root, sid=SID):
    register(sid)
    result = run_lifecycle_event({"session_id": sid, "cwd": str(root), "hook_event_name": "SessionStart"},
                                 event_type="session_start", surface="vscode")
    assert result["ok"] and result["session_envelope_binding"] == "root_bound", result
    return result


def stop(root, sid=SID, transcript_path=None):
    payload = {"session_id": sid, "cwd": str(root), "hook_event_name": "Stop"}
    if transcript_path is not None:
        payload["transcript_path"] = str(transcript_path)
    return run_lifecycle_event(payload, event_type="agent_stop", surface="vscode")


def runtime_bytes(root):
    base = root / "artifacts"
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in base.rglob("*") if p.is_file()} if base.exists() else {}


# ── ordinary Stop: no state change ──────────────────────────────────────────

def test_stop_without_a_governed_vscode_identity_does_nothing(repo):
    result = stop(repo, "never-started")
    assert result["ok"] and result["status"] == "no_governed_vscode_identity"
    assert runtime_bytes(repo) == {}


def test_ordinary_stop_without_a_prepared_candidate_does_nothing(repo):
    start_vscode(repo)
    before = runtime_bytes(repo)
    for _ in range(3):  # every turn ends with Stop
        result = stop(repo, transcript_path=transcript(repo))
        assert result["ok"] and result["status"] == "no_prepared_candidate"
    assert runtime_bytes(repo) == before


def test_stop_while_another_closeout_holds_the_lock_changes_nothing(repo):
    prepare(repo, SID, session_start=start_vscode)
    path = transcript(repo)
    before = runtime_bytes(repo)
    with own.execution_exclusion(repo):
        result = stop(repo, transcript_path=path)
    assert result["ok"] is False and result["status"] == "ownership_unavailable", result
    assert runtime_bytes(repo) == before and owner(repo)["state"] == "OWNED"


def test_stop_of_another_session_does_not_touch_the_prepared_owner(repo):
    prepare(repo, SID, session_start=start_vscode)
    start_vscode(repo, "vscode-stop-b")
    before = runtime_bytes(repo)
    result = stop(repo, "vscode-stop-b", transcript_path=transcript(repo, "vscode-stop-b"))
    assert result["status"] == "no_prepared_candidate"
    assert runtime_bytes(repo) == before
    assert owner(repo)["state"] == "OWNED" and owner(repo)["session_id"] == SID


def test_stop_is_refused_for_the_copilot_cli_surface(repo):
    with pytest.raises(ValueError, match="VS Code Stop execution point only"):
        run_lifecycle_event({"sessionId": SID, "cwd": str(repo), "hookEventName": "agentStop"},
                            event_type="agent_stop", surface="copilot")


def test_cli_identity_never_reaches_the_closeout(repo):
    register("cli-a", "github/cli")
    run_lifecycle_event({"sessionId": "cli-a", "cwd": str(repo), "hookEventName": "sessionStart"},
                        event_type="session_start", surface="copilot")
    before = runtime_bytes(repo)
    result = stop(repo, "cli-a", transcript_path=transcript(repo, "cli-a"))
    assert result["status"] == "no_governed_vscode_identity"
    assert runtime_bytes(repo) == before


# ── prepared candidate: the protected entry runs and is the only judge ────────

def test_prepared_candidate_with_its_own_transcript_closes_out(repo):
    prepare(repo, SID, session_start=start_vscode)
    result = stop(repo, transcript_path=transcript(repo))
    assert result["status"] == "closeout_invoked", result
    assert result["ok"] is True and result["closeout_exit_code"] == 0, result
    assert result["closeout_status"] == "valid"
    assert owner(repo)["state"] == "RELEASED"
    receipt = json.loads(Path(result["closeout_receipt_artifact"]).read_text(encoding="utf-8"))
    assert receipt["agent_id"] == "copilot" and receipt["trigger_mode"] == "native_hook"
    # Stop after the release is an ordinary Stop again.
    again = stop(repo, transcript_path=transcript(repo))
    assert again["status"] == "no_prepared_candidate"


@pytest.mark.parametrize("damage", [
    "missing_transcript", "other_session_transcript", "foreign_session_record",
    "other_repository", "cli_client", "record_mismatch", "malformed", "empty", "wrong_first_record",
])
def test_bad_transcript_or_runtime_record_refuses_without_state_change(repo, tmp_path, damage):
    prepare(repo, SID, session_start=start_vscode)
    path = transcript(repo)
    if damage == "missing_transcript":
        path = None
    elif damage == "other_session_transcript":
        register("vscode-stop-other")
        path = transcript(repo, "vscode-stop-other")
    elif damage == "foreign_session_record":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows.append({"type": "tool.execution_start", "data": {"input": {"sessionId": "someone-else"}}})
        path = transcript(repo, records=rows)
    elif damage == "other_repository":
        other = tmp_path / "other repo"
        subprocess.run(["git", "init", "--quiet", str(other)], check=True)
        path = transcript(repo, cwd=other.resolve())
    elif damage == "cli_client":
        register(SID, "github/cli")
    elif damage == "record_mismatch":
        register(SID, record_id="someone-else")
    elif damage == "malformed":
        path.write_bytes(path.read_bytes() + b"{not json\n")
    elif damage == "empty":
        path.write_bytes(b"")
    elif damage == "wrong_first_record":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        path = transcript(repo, records=rows[1:])
    before = runtime_bytes(repo)
    result = stop(repo, transcript_path=path)
    assert result["status"] == "closeout_invoked" and result["ok"] is False, result
    assert result["closeout_error"].startswith("COPILOT_"), result
    assert runtime_bytes(repo) == before
    assert owner(repo)["state"] == "OWNED"


def test_failed_attempt_can_be_retried_once_the_transcript_is_valid(repo):
    prepare(repo, SID, session_start=start_vscode)
    path = transcript(repo, records=[])
    failed = stop(repo, transcript_path=path)
    assert failed["ok"] is False and owner(repo)["state"] == "OWNED"
    retried = stop(repo, transcript_path=transcript(repo))
    assert retried["ok"] is True and retried["closeout_status"] == "valid", retried
    assert owner(repo)["state"] == "RELEASED"


def test_framework_drive_letter_case_does_not_break_the_consumer_match(repo):
    if os.name != "nt":
        pytest.skip("drive-letter case exists on Windows only")
    prepare(repo, SID, session_start=start_vscode)
    text = str(repo)
    flipped = text[0].swapcase() + text[1:]
    result = stop(repo, transcript_path=transcript(repo, cwd=flipped))
    assert result["ok"] is True and result["closeout_status"] == "valid", result


# ── the protected entry refuses Copilot native closeout without the identity ──

def test_entry_refuses_copilot_native_closeout_for_a_legacy_identity(repo):
    import sys
    from runtime_hooks.core import _canonical_closeout as core
    from tests.test_shared_closeout_ownership import FRAMEWORK
    register("cli-b", "github/cli")
    core.write_session_envelope("cli-b", repo, provider="github-copilot")  # legacy 1.0
    before = runtime_bytes(repo)
    done = subprocess.run(
        [sys.executable, str(FRAMEWORK / "governance_tools/session_closeout_entry.py"), "--project-root",
         str(repo), "--format", "json", "--agent-id", "copilot", "--trigger-mode", "native_hook",
         "--session-id", "cli-b"],
        input=json.dumps({"session_id": "cli-b", "transcript_path": str(transcript(repo, "cli-b"))}),
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert done.returncode == 1
    assert json.loads(done.stdout)["error"] == "COPILOT_IDENTITY_NOT_ROOT_BOUND"
    assert runtime_bytes(repo) == before


# ── Copilot CLI sessionEnd of a prepared session releases R2 (P1 review on #297) ──

def start_cli(root, sid):
    register(sid, "github/cli")
    result = run_lifecycle_event({"sessionId": sid, "cwd": str(root), "hookEventName": "sessionStart"},
                                 event_type="session_start", surface="copilot")
    assert result["ok"] and result["provider"] == "github-copilot", result
    assert result["session_envelope_binding"] == "root_bound"
    return result


def cli_end(root, sid, **extra):
    return run_lifecycle_event({"sessionId": sid, "cwd": str(root), "hookEventName": "sessionEnd",
                                "reason": "complete", **extra}, event_type="session_end", surface="copilot")


def test_cli_a_prepares_ends_and_releases_then_cli_b_takes_over(repo):
    """The reported sequence: start -> prepare -> sessionEnd used to say valid but stay OWNED."""
    first = prepare(repo, "cli-a", session_start=start_cli)
    transcript(repo, "cli-a")  # the runtime's own record; the CLI payload names no transcript
    ended = cli_end(repo, "cli-a")
    assert ended["status"] == "closeout_invoked", ended
    assert ended["ok"] is True and ended["closeout_status"] == "valid", ended
    assert owner(repo)["state"] == "RELEASED" and owner(repo)["session_id"] == "cli-a"
    receipt = json.loads(Path(ended["closeout_receipt_artifact"]).read_text(encoding="utf-8"))
    assert receipt["agent_id"] == "copilot" and receipt["trigger_mode"] == "native_hook"
    second = prepare(repo, "cli-b", session_start=start_cli)  # no OWNER_CONFLICT
    assert second["generation"] == first["generation"] + 1
    assert owner(repo)["state"] == "OWNED" and owner(repo)["session_id"] == "cli-b"
    transcript(repo, "cli-b")
    assert cli_end(repo, "cli-b")["closeout_status"] == "valid"
    assert owner(repo)["state"] == "RELEASED" and owner(repo)["session_id"] == "cli-b"


def test_cli_end_with_a_bad_record_never_reports_valid_while_owned(repo, tmp_path):
    prepare(repo, "cli-a", session_start=start_cli)
    other = tmp_path / "other repo"
    subprocess.run(["git", "init", "--quiet", str(other)], check=True)
    transcript(repo, "cli-a", cwd=other.resolve())
    before = runtime_bytes(repo)
    ended = cli_end(repo, "cli-a")
    assert ended["ok"] is False and ended["closeout_status"] != "valid", ended
    assert ended["closeout_error"] == "COPILOT_TRANSCRIPT_REPOSITORY_MISMATCH"
    assert runtime_bytes(repo) == before and owner(repo)["state"] == "OWNED"
    transcript(repo, "cli-a")  # the session can still be closed out once the record is right
    assert cli_end(repo, "cli-a")["closeout_status"] == "valid"
    assert owner(repo)["state"] == "RELEASED"


def test_cli_end_cannot_use_a_vscode_record(repo):
    prepare(repo, "cli-a", session_start=start_cli)
    transcript(repo, "cli-a")
    register("cli-a", "vscode-agent-host")  # record now names another client
    ended = cli_end(repo, "cli-a")
    assert ended["ok"] is False and ended["closeout_error"] == "COPILOT_PROVIDER_MISMATCH"
    assert owner(repo)["state"] == "OWNED"


def test_cli_end_without_a_prepared_candidate_keeps_the_existing_path(repo):
    start_cli(repo, "cli-a")
    ended = cli_end(repo, "cli-a")
    assert ended["status"] == "session_end_invoked", ended
    assert not (repo / own.AREA / "owner.json").exists()


def test_cli_end_of_another_sessions_prepared_owner_does_not_release_it(repo):
    prepare(repo, "cli-a", session_start=start_cli)
    start_cli(repo, "cli-b")
    ended = cli_end(repo, "cli-b")
    assert ended["status"] == "session_end_invoked", ended
    assert owner(repo)["state"] == "OWNED" and owner(repo)["session_id"] == "cli-a"


def test_cli_end_while_r2_is_busy_fails_closed(repo):
    prepare(repo, "cli-a", session_start=start_cli)
    transcript(repo, "cli-a")
    before = runtime_bytes(repo)
    with own.execution_exclusion(repo):
        ended = cli_end(repo, "cli-a")
    assert ended["ok"] is False and ended["status"] == "ownership_unavailable", ended
    assert runtime_bytes(repo) == before and owner(repo)["state"] == "OWNED"


# ── unit: client mapping ─────────────────────────────────────────────────────

def test_client_mapping_is_explicit_and_closed():
    assert state.PROVIDER_BY_CLIENT == {"vscode-agent-host": "github-copilot-vscode",
                                        "github/cli": "github-copilot"}
    register("map-vs")
    register("map-cli", "github/cli")
    register("map-quoted", '"github/cli"')
    assert state.provider_for_session("map-vs") == "github-copilot-vscode"
    assert state.provider_for_session("map-cli") == "github-copilot"
    assert state.provider_for_session("map-quoted") == "github-copilot"
    for client in ("", "vscode", "GitHub/CLI", "github/cli-next"):
        register("map-odd", client)
        with pytest.raises(state.CopilotSessionStateError, match="COPILOT_CLIENT_UNKNOWN"):
            state.provider_for_session("map-odd")


@pytest.mark.parametrize("sid", ["../escape", "a/b", "", "x" * 200])
def test_unsafe_session_id_never_reads_outside_the_state_directory(sid):
    with pytest.raises(state.CopilotSessionStateError, match="COPILOT_SESSION_ID_INVALID"):
        state.provider_for_session(sid)


def test_copilot_home_defaults_to_the_user_profile():
    assert state.copilot_home({}) == Path.home() / ".copilot"
    assert state.copilot_home({"COPILOT_HOME": "D:/elsewhere"}) == Path("D:/elsewhere")
