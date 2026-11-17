"""Accepted closeouts consume once; rejected attempts remain correctable."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

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
