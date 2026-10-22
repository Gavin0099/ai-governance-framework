"""VS Code root-bound session identity: own provider identity, worktree binding, no Codex disguise."""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from runtime_hooks.adapters.codex.session_start import run as codex_start
from runtime_hooks.adapters.copilot.lifecycle import run_lifecycle_event
from runtime_hooks.core import _canonical_closeout as core

SID = "vscode-session-a"


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "core.hooksPath=NUL", *args],
        check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "consumer vscode"
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    git(root, "commit", "--allow-empty", "-qm", "fixture")
    return root.resolve()


def vscode_start(root, sid=SID, surface="vscode"):
    payload = {"session_id": sid, "cwd": str(root), "hook_event_name": "SessionStart"}
    return run_lifecycle_event(payload, event_type="session_start", surface=surface)


def envelope_path(root, sid=SID):
    return root / "artifacts/runtime/sessions" / sid / "session-envelope.json"


def write_summary(root, sid=SID):
    (root / "evidence.txt").write_text("fixture evidence", encoding="utf-8")
    candidate = dict(task_intent="Inspect VS Code binding", work_summary="Inspected evidence.txt",
                     tools_used=["inspect"], artifacts_referenced=["evidence.txt"], open_risks=[])
    core.write_candidate(sid, root, candidate)
    text = root / "artifacts/session-closeout.txt"
    text.write_text("TASK_INTENT: Inspect VS Code binding\nWORK_COMPLETED: Inspected evidence.txt\n"
                    "FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n"
                    "NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n", encoding="utf-8")
    envelope = core.read_session_envelope(sid, root)
    later = datetime.fromisoformat(envelope["started_at"]).timestamp() + 1
    os.utime(text, (later, later))
    return candidate


def test_vscode_start_is_bound_with_real_vscode_identity(repo):
    result = vscode_start(repo)
    assert result["ok"] and result["status"] == "session_envelope_written"
    assert result["session_envelope_binding"] == "root_bound"
    payload = json.loads(envelope_path(repo).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.1"
    assert payload["provider"] == "github-copilot-vscode"
    assert payload["repo_binding"] == {"consumer_root": str(repo), "source": "vscode_session_start"}
    assert core.read_session_envelope(SID, repo) is not None


def test_repeated_vscode_start_preserves_identity_bytes(repo):
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    again = vscode_start(repo)
    assert again["ok"] and again["status"] == "session_envelope_preserved"
    assert envelope_path(repo).read_bytes() == before


def test_existing_legacy_vscode_envelope_is_never_migrated(repo):
    core.write_session_envelope(SID, repo, provider="github-copilot-vscode")
    before = envelope_path(repo).read_bytes()
    result = vscode_start(repo)
    assert result["ok"] and result["session_envelope_binding"] == "legacy"
    assert envelope_path(repo).read_bytes() == before


def test_copilot_cli_surface_stays_legacy(repo):
    result = vscode_start(repo, sid="cli-session", surface="copilot")
    assert result["ok"] and result["session_envelope_binding"] == "legacy"
    assert json.loads(envelope_path(repo, "cli-session").read_text())["schema_version"] == "1.0"


def test_unbindable_session_id_fails_closed_without_legacy_fallback(repo):
    result = vscode_start_safe(repo, "dotted.session")
    assert result is None
    assert not (repo / "artifacts/runtime/sessions/dotted.session").exists()


def vscode_start_safe(root, sid):
    try:
        vscode_start(root, sid)
    except ValueError:
        return None
    return "started"


def test_subdirectory_workspace_fails_closed(repo):
    sub = repo / "sub"
    sub.mkdir()
    with pytest.raises(ValueError, match="do not match"):
        vscode_start(sub)
    assert not (repo / "artifacts").exists() and not (sub / "artifacts").exists()


@pytest.mark.parametrize("provider,source", [
    ("codex", "vscode_session_start"),
    ("github-copilot-vscode", "codex_session_start"),
    ("github-copilot", "vscode_session_start"),
    ("github-copilot", "codex_session_start"),
])
def test_reader_rejects_provider_source_mismatch(repo, provider, source):
    vscode_start(repo)
    path = envelope_path(repo)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider"] = provider
    payload["repo_binding"]["source"] = source
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope(SID, repo) is None


def test_vscode_provider_cannot_be_written_as_codex_and_vice_versa(repo):
    for provider in ("claude", "github-copilot", "unknown"):
        with pytest.raises(ValueError, match="Codex or VS Code"):
            core.write_session_envelope("x-" + provider, repo, provider=provider, bound_consumer_root=repo)
    codex_start(dict(hook_event_name="SessionStart", source="startup", session_id="codex-a", cwd=str(repo)), repo)
    payload = json.loads(envelope_path(repo, "codex-a").read_text())
    assert payload["provider"] == "codex"
    assert payload["repo_binding"]["source"] == "codex_session_start"


def test_vscode_start_cannot_adopt_a_codex_session_identity(repo):
    codex_start(dict(hook_event_name="SessionStart", source="startup", session_id="codex-a", cwd=str(repo)), repo)
    before = envelope_path(repo, "codex-a").read_bytes()
    pointer = repo / "artifacts/runtime/.current-session-id"
    pointer_before = pointer.read_bytes() if pointer.exists() else None
    with pytest.raises(ValueError, match="another provider"):
        vscode_start(repo, sid="codex-a")
    assert envelope_path(repo, "codex-a").read_bytes() == before
    assert (pointer.read_bytes() if pointer.exists() else None) == pointer_before


def test_codex_start_cannot_adopt_a_vscode_session_identity(repo):
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    with pytest.raises(ValueError, match="another provider"):
        codex_start(dict(hook_event_name="SessionStart", source="startup", session_id=SID, cwd=str(repo)), repo)
    assert envelope_path(repo).read_bytes() == before


def test_git_toplevel_decodes_utf8_regardless_of_console_codepage(repo, monkeypatch):
    from runtime_hooks.core import _bound_session_start as bound
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout=str(repo) + "\n", stderr="")

    monkeypatch.setattr(bound.subprocess, "run", fake_run)
    assert bound.git_toplevel(str(repo)) == repo
    assert seen.get("encoding") == "utf-8"


def test_codex_and_vscode_identities_are_not_interchangeable(repo):
    vscode_start(repo)
    path = envelope_path(repo)
    payload = json.loads(path.read_text())
    payload["provider"] = "codex"  # relabel without changing the source
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert core.read_session_envelope(SID, repo) is None


def test_vscode_session_closeout_saves_summary_for_own_session(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo)
    before = envelope_path(repo).read_bytes()
    candidate = write_summary(repo)
    result = run_session_end_hook(repo, hook_session_id=SID, ledger_write_allowed=False)
    assert result["session_binding"]["status"] == "valid"
    assert result["closeout_status"] == "valid"
    canonical = json.loads((repo / f"artifacts/runtime/closeouts/{SID}.json").read_text())
    assert canonical["task_intent"] == candidate["task_intent"]
    assert canonical["work_summary"] == candidate["work_summary"]
    assert envelope_path(repo).read_bytes() == before


def test_missing_summary_keeps_failure_state(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo)
    result = run_session_end_hook(repo, hook_session_id=SID, ledger_write_allowed=False)
    assert result["closeout_status"] == "closeout_missing" and result["decision"] == "DO_NOT_PROMOTE"
    assert result["session_binding"]["status"] == "session_candidate_missing"
    recorded = json.loads((repo / f"artifacts/runtime/closeouts/{SID}.json").read_text())
    assert recorded["closeout_status"] == "missing" and recorded["work_summary"] is None


def test_other_session_summary_is_rejected(repo):
    from governance_tools.session_end_hook import run_session_end_hook
    vscode_start(repo, "vscode-session-a")
    vscode_start(repo, "vscode-session-b")
    write_summary(repo, "vscode-session-a")
    result = run_session_end_hook(repo, hook_session_id="vscode-session-b", ledger_write_allowed=False)
    assert result["closeout_status"] != "valid"
    assert result["session_binding"]["status"] != "valid"
    recorded = json.loads((repo / "artifacts/runtime/closeouts/vscode-session-b.json").read_text())
    assert recorded["closeout_status"] == "missing" and recorded["work_summary"] is None
    assert not (repo / "artifacts/runtime/closeouts/vscode-session-a.json").exists()


def test_copied_vscode_identity_is_rejected_in_other_worktree(repo, tmp_path):
    vscode_start(repo)
    other = tmp_path / "other-worktree"
    git(repo, "worktree", "add", "--detach", str(other))
    copied = envelope_path(other)
    copied.parent.mkdir(parents=True)
    copied.write_bytes(envelope_path(repo).read_bytes())
    assert core.read_session_envelope(SID, other) is None
    before = copied.read_bytes()
    result = vscode_start_result(other)
    assert result["ok"] is False
    assert copied.read_bytes() == before
    assert not (other / "artifacts/runtime/.current-session-id").exists()


def vscode_start_result(root):
    try:
        return vscode_start(root)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
