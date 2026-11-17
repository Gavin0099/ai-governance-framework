"""#213: invalid closeout input is an audit event, never an agent work record."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from governance_tools import shared_closeout_ownership as ownership
from governance_tools.memory_record import WRITER_ID
from runtime_hooks.adapters.claude_code import session_lifecycle as claude
from runtime_hooks.adapters.copilot import lifecycle
from runtime_hooks.core import _canonical_closeout as canonical
from runtime_hooks.core import session_end as core


SID = "memory-input-session"
TASK = "Review synthetic closeout input"
WORK = "Inspected evidence.txt in the synthetic repository."
DEFAULT_SUMMARY = "Session closeout recorded without an explicit summary."
DEFAULT_NEXT_STEP = "Continue the next session from the recorded closeout and pending memory state."


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("GIT_"):
            monkeypatch.delenv(name)
    home = tmp_path / "isolated-home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("COPILOT_HOME", str(home / "copilot"))
    root = tmp_path / "synthetic repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    (root / "AGENTS.md").write_text("# Synthetic test repository\n", encoding="utf-8")
    (root / "governance").mkdir()
    (root / "evidence.txt").write_text("synthetic evidence\n", encoding="utf-8")
    return root.resolve()


def memory_text(root):
    return "\n".join(p.read_text(encoding="utf-8") for p in (root / "memory").rglob("*.md"))


def assert_audit_only(text):
    assert "session_end closeout audit" in text
    assert "No agent work is recorded" in text
    assert "next_step: NOT CLAIMED:" in text
    assert DEFAULT_SUMMARY not in text
    assert DEFAULT_NEXT_STEP not in text
    assert "open_risk_count=" not in text
    assert "Summary:" not in text
    assert "session_end auto-closeout recorded for" not in text


def start_copilot(root, surface, sid=SID):
    state = Path(os.environ["COPILOT_HOME"]) / "session-state" / sid
    state.mkdir(parents=True)
    client = "vscode-agent-host" if surface == "vscode" else "github/cli"
    (state / "workspace.yaml").write_text(f"id: {sid}\nclient_name: {client}\n", encoding="utf-8")
    result = lifecycle.run_lifecycle_event(
        {"sessionId": sid, "cwd": str(root), "source": "new"},
        event_type="session_start", surface="auto",
    )
    assert result["session_envelope_binding"] == "root_bound", result


def end_copilot(root, surface):
    payload = ({"session_id": SID, "hook_event_name": "SessionEnd"} if surface == "vscode"
               else {"sessionId": SID, "hookEventName": "sessionEnd"})
    return lifecycle.run_lifecycle_event(
        {**payload, "cwd": str(root)}, event_type="session_end", surface=surface,
    )


def write_input(root, *, candidate=True):
    text = (
        f"TASK_INTENT: {TASK}\nWORK_COMPLETED: {WORK}\n"
        "FILES_TOUCHED: evidence.txt\nCHECKS_RUN: NONE\nOPEN_RISKS: NONE\n"
        "NOT_DONE: NONE\nRECOMMENDED_MEMORY_UPDATE: NO_UPDATE\n"
    )
    (root / "artifacts" / "session-closeout.txt").write_text(text, encoding="utf-8")
    if candidate:
        canonical.write_candidate(SID, root, {
            "task_intent": TASK, "work_summary": WORK, "tools_used": [],
            "artifacts_referenced": ["evidence.txt"], "open_risks": [],
        })


@pytest.mark.parametrize(
    ("canonical_status", "observed_status"),
    [
        ("missing", None), ("schema_invalid", None), ("content_insufficient", None),
        ("inconsistent", None), ("stale_or_mismatched", None),
        ("valid", "missing"), ("valid", "schema_invalid"),
        ("valid", "content_insufficient"), ("valid", "inconsistent"),
        ("valid", "stale_or_mismatched"), ("missing", "valid"),
    ],
)
def test_unusable_input_is_written_as_audit_only(repo, canonical_status, observed_status):
    outcome = core._append_daily_memory_entry(
        project_root=repo, session_id=SID, task="Untrusted task input",
        decision="DO_NOT_PROMOTE", summary="Untrusted work summary",
        promoted=False, snapshot_created=False,
        canonical_closeout={"closeout_status": canonical_status, "open_risks": []},
        observed_closeout_status=observed_status,
    )
    assert outcome.status == "written" and outcome.writer == WRITER_ID
    text = memory_text(repo)
    assert_audit_only(text)
    assert "Untrusted task input" not in text and "Untrusted work summary" not in text
    assert f"canonical_closeout_status={canonical_status}" in text
    assert f"closeout_status={observed_status or canonical_status}" in text


@pytest.mark.parametrize("surface", ["vscode", "copilot"])
@pytest.mark.parametrize("input_state", ["missing", "invalid", "unbound", "mismatched"])
def test_copilot_generic_closeout_never_projects_invalid_input_as_work(repo, surface, input_state):
    start_copilot(repo, surface)
    if input_state == "invalid":
        (repo / "artifacts" / "session-closeout.txt").write_text(
            "TASK_INTENT: Untrusted task input\n", encoding="utf-8",
        )
    elif input_state in {"unbound", "mismatched"}:
        write_input(repo, candidate=input_state == "mismatched")
        if input_state == "mismatched":
            path = repo / "artifacts" / "session-closeout.txt"
            path.write_text(path.read_text(encoding="utf-8").replace(
                WORK, "Untrusted work summary about evidence.txt from a different synthetic task.",
            ), encoding="utf-8")

    result = end_copilot(repo, surface)

    assert result["status"] == "session_end_invoked", result
    expected = {"missing": "closeout_missing", "invalid": "schema_invalid",
                "unbound": "stale_or_mismatched", "mismatched": "stale_or_mismatched"}[input_state]
    assert result["closeout_status"] == expected, result
    assert result["ok"] is False and result["decision"] == "DO_NOT_PROMOTE", result
    text = memory_text(repo)
    assert_audit_only(text)
    assert "Untrusted task input" not in text and "Untrusted work summary" not in text
    assert TASK not in text and WORK not in text
    label = "MISSING" if input_state == "missing" else expected.upper()
    assert f"FAIL_CLOSED_CLOSEOUT_{label}" in text


@pytest.mark.parametrize("surface", ["vscode", "copilot"])
def test_valid_copilot_summary_keeps_the_existing_work_record(repo, surface):
    start_copilot(repo, surface)
    write_input(repo)

    result = end_copilot(repo, surface)

    assert result["closeout_status"] == "valid", result
    summary = json.loads((repo / f"artifacts/runtime/summaries/{SID}.json").read_text(encoding="utf-8"))
    record = summary["daily_memory_record"]
    assert record["what_changed"] == (
        f"session_end auto-closeout recorded for `{TASK}` "
        f"(session={SID}, decision=AUTO_PROMOTE, snapshot_created=True, promoted=True). Summary: {TASK}"
    )
    assert record["test_evidence"] == (
        "`session_end` => closeout_status=valid, canonical_closeout_status=valid, "
        "snapshot_created=True, promoted=True, open_risk_count=0"
    )
    assert record["next_step"] == "Resume from the latest canonical closeout state (status=valid)."
    assert record["writer"] == WRITER_ID
    assert record["what_changed"] in memory_text(repo)


@pytest.mark.parametrize(
    ("tier", "classification", "signals"),
    [("B", "incomplete_observation", ["closeout_missing_tier_b"]), ("C", "not_applicable", [])],
)
def test_missing_input_audit_keeps_optional_tier_and_r2_initialization(repo, tier, classification, signals):
    from governance_tools.session_end_hook import run_session_end_hook

    start_copilot(repo, "copilot")
    start_copilot(repo, "copilot", "identity-only-session")
    (repo / "governance" / "gate_policy.yaml").write_text(
        f"version: '1'\nfail_mode: audit\nhook_coverage_tier: {tier}\n", encoding="utf-8",
    )
    result = run_session_end_hook(repo, hook_session_id=SID, ledger_write_allowed=False)
    evaluation = result["closeout_evaluation"]
    assert evaluation["classification"] == classification
    assert evaluation["signals"] == signals and evaluation["ok_effect"] == "pass"
    assert result["closeout_status"] == "closeout_missing" and result["decision"] == "DO_NOT_PROMOTE"
    assert_audit_only(memory_text(repo))
    assert "FAIL_CLOSED_CLOSEOUT_MISSING" in memory_text(repo)
    with ownership.execution_exclusion(repo) as lease:
        record = ownership.acquire_owner(lease, "identity-only-session", {
            "relative_path": "artifacts/runtime/closeout_candidates/identity-only-session/000001.json",
            "sha256": "a" * 64,
        }, "b" * 64)
    assert record["state"] == "HOLD"


def test_claude_native_session_end_still_only_checkpoints(repo):
    claude.session_start({"hook_event_name": "SessionStart", "session_id": SID,
                          "cwd": str(repo), "source": "startup"}, repo)
    result = claude.session_end({"hook_event_name": "SessionEnd", "session_id": SID,
                                "cwd": str(repo)}, repo)
    assert Path(result["checkpoint_path"]).is_file()
    assert not (repo / "memory").exists()
    assert not (repo / f"artifacts/runtime/closeout-completions/{SID}.json").exists()
