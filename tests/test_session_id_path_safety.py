"""
Regression tests for issue #215: session_id is interpolated into artifact paths
(closeouts/{id}.json, memory-candidates/{id}.json, claim-enforcement/{id}/...),
so an unsafe value ("../../governance/framework.lock") must be rejected before
any write, and legitimate Codex / Copilot / generated ids must keep working.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.memory_significance import write_candidate_and_advisory
from governance_tools.session_end_hook import run_session_end_hook
from runtime_hooks.core._canonical_closeout import (
    InvalidSessionIdError,
    _generate_session_id,
    is_valid_session_id,
    pick_latest_candidate,
    read_session_envelope,
    read_current_session_id,
    validate_session_id,
    write_candidate,
    write_canonical_closeout,
    write_closeout_completion_marker,
    write_current_session_id,
)
from runtime_hooks.core.session_end import run_session_end

UNSAFE_IDS = [
    "../../../governance/framework.lock",
    "../../../../outside_repo",
    "..\\..\\outside_repo",
    "/etc/passwd",
    "C:\\Windows\\x",
    "C:x",
    "a/b",
    "a\\b",
    "..",
    ".",
    ".hidden",
    "trailing.",
    "with space",
    "line\nbreak",
    "x" * 129,
    "CON",
    "nul",
    "COM1",
    "lpt9.txt",
    "",
]

SAFE_IDS = [
    _generate_session_id(),
    "session-20260101T000000-abc123",
    "019e5f7b-77d2-7a31-9c0f-0123456789ab",  # codex-style uuid
    "codex_abc-123",
    "_copilot-1",  # copilot adapter may start with "_" / "-"
    "copilot.v1.session",  # copilot adapter allows "."
    "x" * 128,
]


def _tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _project(tmp_path: Path) -> tuple[Path, Path]:
    """Return (sandbox, repo) where sandbox is the parent that must stay untouched."""
    sandbox = tmp_path / "sandbox"
    repo = sandbox / "a" / "b" / "repo"
    (repo / "governance").mkdir(parents=True)
    (repo / "governance" / "framework.lock.json").write_text('{"lock":"original"}', encoding="utf-8")
    return sandbox, repo


def _write_pointer(path: Path, session_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"session_id": session_id, "written_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


@pytest.mark.parametrize("session_id", UNSAFE_IDS)
def test_unsafe_ids_are_rejected(session_id):
    assert not is_valid_session_id(session_id)
    with pytest.raises(InvalidSessionIdError):
        validate_session_id(session_id)


@pytest.mark.parametrize("session_id", SAFE_IDS)
def test_legitimate_ids_are_accepted_unchanged(session_id):
    assert is_valid_session_id(session_id)
    assert validate_session_id(session_id) == session_id


@pytest.mark.parametrize("bad", [None, 123, b"abc", ["a"]])
def test_non_string_ids_are_rejected(bad):
    with pytest.raises(InvalidSessionIdError):
        validate_session_id(bad)


@pytest.mark.parametrize("pointer", [".current-session-id", "artifacts/runtime/.current-session-id"])
def test_unsafe_current_session_pointer_is_ignored(tmp_path, pointer):
    _, repo = _project(tmp_path)
    _write_pointer(repo / pointer, "../../../governance/framework.lock")
    assert read_current_session_id(repo) is None


def test_safe_current_session_pointer_still_read(tmp_path):
    _, repo = _project(tmp_path)
    _write_pointer(repo / ".current-session-id", "copilot.v1.session")
    assert read_current_session_id(repo) == "copilot.v1.session"


def test_unsafe_pointer_falls_through_to_next_safe_pointer(tmp_path):
    _, repo = _project(tmp_path)
    _write_pointer(repo / "artifacts/runtime/.current-session-id", "../evil")
    _write_pointer(repo / ".current-session-id", "good-session-1")
    assert read_current_session_id(repo) == "good-session-1"


def test_hook_with_traversal_pointer_writes_nothing_outside_artifacts(tmp_path):
    """Issue #215 repro: .current-session-id must not redirect writes."""
    sandbox, repo = _project(tmp_path)
    lock = repo / "governance" / "framework.lock.json"
    _write_pointer(repo / ".current-session-id", "../../../governance/framework.lock")
    before_outside = {k: v for k, v in _tree(sandbox).items() if not k.startswith("a/b/repo/")}

    run_session_end_hook(repo)

    assert lock.read_text(encoding="utf-8") == '{"lock":"original"}'
    assert not (repo / "governance" / "framework.lock").exists()
    after = _tree(sandbox)
    assert {k: v for k, v in after.items() if not k.startswith("a/b/repo/")} == before_outside
    # nothing was created next to the lock file the pointer tried to reach
    assert sorted(p.name for p in (repo / "governance").iterdir()) == ["framework.lock.json"]


@pytest.mark.parametrize(
    "hook_id",
    ["../../../../hook_escape", "..\\..\\hook_escape", "/tmp/abs", "a/b"],
)
def test_hook_payload_session_id_traversal_fails_closed_with_zero_writes(tmp_path, hook_id):
    sandbox, repo = _project(tmp_path)
    before = _tree(sandbox)

    with pytest.raises(InvalidSessionIdError):
        run_session_end_hook(repo, hook_session_id=hook_id)

    assert _tree(sandbox) == before
    assert not list(sandbox.rglob("hook_escape*"))


@pytest.mark.parametrize("session_id", ["codex_abc-123", "copilot.v1.session", "_c-1"])
def test_hook_accepts_legitimate_hook_session_ids(tmp_path, session_id):
    _, repo = _project(tmp_path)
    run_session_end_hook(repo, hook_session_id=session_id)
    # the id was accepted and used verbatim as the artifact name
    assert (repo / "artifacts" / "runtime" / "verdicts" / f"{session_id}.json").is_file()


@pytest.mark.parametrize("session_id", ["../../../../escape", "a/b", "..\\x"])
def test_core_sinks_reject_unsafe_ids_with_zero_writes(tmp_path, session_id):
    sandbox, repo = _project(tmp_path)
    before = _tree(sandbox)

    with pytest.raises(InvalidSessionIdError):
        write_current_session_id(session_id, repo)
    with pytest.raises(InvalidSessionIdError):
        write_candidate(session_id, repo, {"task_intent": "x"})
    with pytest.raises(InvalidSessionIdError):
        write_canonical_closeout({"session_id": session_id}, repo)
    with pytest.raises(InvalidSessionIdError):
        write_closeout_completion_marker(session_id, repo, [])
    with pytest.raises(InvalidSessionIdError):
        write_candidate_and_advisory(
            repo_root=repo, session_id=session_id, commit_hash="abc",
            task_intent="x", checks={},
        )
    with pytest.raises(InvalidSessionIdError):
        run_session_end(
            project_root=repo,
            session_id=session_id,
            runtime_contract={"task": "t", "rules": ["r"], "risk": "low",
                              "oversight": "auto", "memory_mode": "candidate"},
        )

    assert _tree(sandbox) == before
    assert not list(sandbox.rglob("*escape*"))


def test_empty_session_id_writes_nothing(tmp_path):
    # Previously recorded "session_id is required" but still wrote artifacts
    # named ".json" under closeouts/, verdicts/, traces/, ...
    sandbox, repo = _project(tmp_path)
    before = _tree(sandbox)
    with pytest.raises(InvalidSessionIdError):
        run_session_end(
            project_root=repo,
            session_id="",
            runtime_contract={"task": "t", "rules": ["r"], "risk": "low",
                              "oversight": "auto", "memory_mode": "candidate"},
        )
    assert _tree(sandbox) == before


@pytest.mark.parametrize("session_id", SAFE_IDS[:6])
def test_core_sinks_still_write_for_legitimate_ids(tmp_path, session_id):
    _, repo = _project(tmp_path)
    assert write_current_session_id(session_id, repo).is_file()
    assert write_candidate(session_id, repo, {"task_intent": "x"}).is_file()
    assert write_canonical_closeout({"session_id": session_id}, repo).name == f"{session_id}.json"
    paths = write_candidate_and_advisory(
        repo_root=repo, session_id=session_id, commit_hash="abc", task_intent="x", checks={},
    )
    assert Path(paths["candidate_path"]).is_file()


@pytest.mark.parametrize("session_id", ["../../../../escape", "a/b", "", "CON"])
def test_read_apis_keep_not_found_contract_for_unsafe_ids(tmp_path, session_id):
    _, repo = _project(tmp_path)
    assert read_session_envelope(session_id, repo) is None
    assert pick_latest_candidate(session_id, repo) is None
