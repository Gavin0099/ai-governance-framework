"""The active-task-summary projection converges instead of growing per record.

Before this change every ``memory_record --surface active-task-summary`` write
appended one more projection line to ``memory/01_active_task.md``; in consumer
repositories those lines became most of the file and pushed it to §7.4
EMERGENCY. The converging writer replaces its own previous projection, moves it
byte-exact to ``memory/archive/active_task_projection_history.md`` and leaves
every other byte alone.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import memory_record
from governance_tools.memory_record import (
    ACTIVE_TASK_PROJECTION_HISTORY,
    MEMORY_WRITE_STATUS_ALREADY_PRESENT,
    MEMORY_WRITE_STATUS_WRITTEN,
    SURFACE_ACTIVE_TASK_SUMMARY,
    append_projection_with_outcome,
    append_session_derived_entry_with_outcome,
    build_session_derived_record,
    render_active_task_projection,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTION_TOKEN = "memory_record_projection:active-task-summary:"

# Agent-authored header modelled on a consumer active-task file: headings,
# status bullets, mixed CJK/ASCII. Content is synthetic.
AGENT_HEADER = (
    "# Active Task\n\n## Current Status\n\n"
    "- Adopted governance baseline (synthetic fixture, `adopt_governance.py`).\n"
    "- Tech route chosen: native client; see `docs/TECH_DECISION.md`.\n"
    "- Rules Draft v0.2：Owner 決策已記錄於 `docs/DECISIONS.md`，其餘待審項目保留。\n"
    "- Reference engine plus three skills; 75 tests pass in the fixture.\n"
    "- UI-1 delivered：視窗版棋盤可操作，回饋待 Owner 試玩後決定。\n\n"
    "## Next Steps\n\n"
    "- Owner tries UI-1 and reports feel/clarity problems; then decide UI-2.\n"
    "- Before any push of the public repo: resolve the open protocol question.\n"
    "- 禁止：未經 Owner 同意不得推送或發布。\n"
)


def make_record(index: int) -> dict[str, str]:
    return build_session_derived_record(
        what_changed=f"synthetic slice {index} delivered",
        commit=f"{index:07x}",
        session_id=f"session-{index}",
        memory_binding="bound",
        test_evidence=f"NOT CLAIMED: synthetic fixture record {index}",
        next_step=f"continue synthetic slice {index + 1}",
        plan_reconciliation="not_applicable",
    )


def make_summary(index: int) -> str:
    return (
        f"Slice {index}：候選工程已交付並凍結，Owner 驗收前不得宣稱完成；"
        f"evidence bound to synthetic commit {index:07x}, tests listed in the daily "
        "record, remaining gaps tracked in docs/NEXT_GATE.md and not expanded here."
    )


def write_record(root: Path, index: int, *, converge: bool, daily: bool = True):
    record = make_record(index)
    if daily:
        append_session_derived_entry_with_outcome(project_root=root, record=record)
    return append_projection_with_outcome(
        project_root=root,
        record=record,
        surface=SURFACE_ACTIVE_TASK_SUMMARY,
        active_task_summary=make_summary(index),
        converge=converge,
    )


def build_tacticalgo_shaped(root: Path, projections: int = 106) -> Path:
    """Agent header plus a legacy backlog written by the old append-only path."""
    active = root / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))
    for index in range(projections):
        write_record(root, index, converge=False)
    return active


def strip_projections(data: bytes) -> bytes:
    """Remove projection lines and the blank separator the writer put before each."""
    lines = data.splitlines(keepends=True)
    drop: set[int] = set()
    for index, line in enumerate(lines):
        if PROJECTION_TOKEN.encode() in line:
            drop.add(index)
            if index > 0 and lines[index - 1] in (b"\n", b"\r\n"):
                drop.add(index - 1)
    return b"".join(line for index, line in enumerate(lines) if index not in drop)


def count_projections(path: Path) -> int:
    return path.read_bytes().count(PROJECTION_TOKEN.encode())


def test_steady_state_keeps_exactly_one_current_projection(tmp_path: Path) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))

    for index in range(30):
        outcome = write_record(tmp_path, index, converge=True)
        assert outcome.status == MEMORY_WRITE_STATUS_WRITTEN

    last = memory_record.prepare_projection_record(make_record(29))
    expected = (
        AGENT_HEADER.encode("utf-8")
        + b"\n"
        + render_active_task_projection(last, summary=make_summary(29)).encode("utf-8")
    )
    assert active.read_bytes() == expected
    assert outcome.superseded_record_identity == memory_record.prepare_projection_record(
        make_record(28)
    )["record_identity"]

    history = (tmp_path / ACTIVE_TASK_PROJECTION_HISTORY).read_bytes()
    for index in range(29):
        prepared = memory_record.prepare_projection_record(make_record(index))
        line = render_active_task_projection(prepared, summary=make_summary(index))
        assert history.count(line.encode("utf-8")) == 1
    assert count_projections(tmp_path / ACTIVE_TASK_PROJECTION_HISTORY) == 29


def test_retries_are_idempotent_and_superseded_records_are_not_resurrected(
    tmp_path: Path,
) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))
    for index in range(3):
        write_record(tmp_path, index, converge=True)
    history_path = tmp_path / ACTIVE_TASK_PROJECTION_HISTORY
    snapshot = (active.read_bytes(), history_path.read_bytes())

    current_retry = write_record(tmp_path, 2, converge=True)
    superseded_retry = write_record(tmp_path, 0, converge=True)

    assert current_retry.status == MEMORY_WRITE_STATUS_ALREADY_PRESENT
    assert superseded_retry.status == MEMORY_WRITE_STATUS_ALREADY_PRESENT
    assert (active.read_bytes(), history_path.read_bytes()) == snapshot


def test_agent_content_around_projection_is_preserved_byte_for_byte(
    tmp_path: Path,
) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    # CRLF agent content, then a projection, then agent text written after it.
    active.write_bytes(b"# Task\r\n\r\n- keep me\r\n")
    write_record(tmp_path, 1, converge=False)
    with active.open("ab") as fh:
        fh.write(b"\r\n## Notes written after the projection\r\n- note \xe5\x82\x99\xe8\xa8\xbb\r\n")
    before = active.read_bytes()

    outcome = write_record(tmp_path, 2, converge=True)

    after = active.read_bytes()
    assert outcome.superseded_record_identity is not None
    assert strip_projections(after) == strip_projections(before)
    assert count_projections(active) == 1
    assert make_summary(2).encode("utf-8") in after
    assert b"\r\n## Notes written after the projection\r\n" in after


def test_legacy_backlog_stops_growing_and_is_left_for_verified_cutover(
    tmp_path: Path,
) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=106)
    before = active.read_bytes()
    before_lines = before.splitlines(keepends=True)

    write_record(tmp_path, 500, converge=True)
    write_record(tmp_path, 501, converge=True)

    after = active.read_bytes()
    after_lines = after.splitlines(keepends=True)
    assert count_projections(active) == 106
    assert len(after_lines) == len(before_lines)
    # Only the writer's own most recent projection was replaced; the backlog
    # (and the agent header) is untouched until an explicit verified cutover.
    assert after_lines[:-1] == before_lines[:-1]
    assert make_summary(501).encode("utf-8") in after_lines[-1]
    assert strip_projections(after) == strip_projections(before)


def test_supersession_relation_endpoint_is_never_removed(tmp_path: Path) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))
    write_record(tmp_path, 1, converge=False)
    write_record(tmp_path, 2, converge=False)
    first = memory_record.prepare_projection_record(make_record(1))["record_identity"]
    second = memory_record.prepare_projection_record(make_record(2))["record_identity"]
    with active.open("ab") as fh:
        fh.write(
            memory_record.render_active_task_supersession_relation(
                predecessor_record_identity=first,
                predecessor_projection_sha256="a" * 64,
                successor_record_identity=second,
                successor_projection_sha256="b" * 64,
            ).encode("ascii")
        )
    before = active.read_bytes()

    outcome = write_record(tmp_path, 3, converge=True)

    assert outcome.superseded_record_identity is None
    assert active.read_bytes().startswith(before)
    assert count_projections(active) == 3


def test_unparseable_surface_falls_back_to_append_without_rewriting(
    tmp_path: Path,
) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(
        AGENT_HEADER.encode("utf-8")
        + b"- forged <!-- memory_record_projection:active-task-summary:zz -->\n"
    )
    before = active.read_bytes()

    outcome = write_record(tmp_path, 1, converge=True)

    assert outcome.status == MEMORY_WRITE_STATUS_WRITTEN
    assert outcome.superseded_record_identity is None
    assert active.read_bytes().startswith(before)
    assert not (tmp_path / ACTIVE_TASK_PROJECTION_HISTORY).exists()


def test_concurrent_change_during_convergence_replaces_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))
    write_record(tmp_path, 1, converge=True)
    original = memory_record._append_projection_history_line

    def racing_history_append(history_path: Path, payload: bytes) -> None:
        original(history_path, payload)
        with active.open("ab") as fh:
            fh.write(b"- concurrent agent edit\n")

    monkeypatch.setattr(memory_record, "_append_projection_history_line", racing_history_append)
    with pytest.raises(ValueError, match="changed during convergence"):
        write_record(tmp_path, 2, converge=True, daily=False)
    assert active.read_bytes().endswith(b"- concurrent agent edit\n")
    assert make_summary(2).encode("utf-8") not in active.read_bytes()


def _init_git_repo(repo: Path) -> str:
    for command in (
        ["git", "-C", str(repo), "init"],
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        ["git", "-C", str(repo), "config", "user.name", "Test User"],
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "seed"],
    ):
        subprocess.run(command, check=True, capture_output=True)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _run_cli(repo: Path, head: str, index: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "governance_tools" / "memory_record.py"),
            "--what-changed", f"cli slice {index}",
            "--next-step", f"cli next {index}",
            "--commit", head,
            "--session-id", f"cli-session-{index}",
            "--test-evidence", f"NOT CLAIMED: convergence CLI test {index}",
            "--plan-reconciliation", "not_applicable",
            "--project-root", str(repo),
            "--surface", "daily",
            "--surface", "active-task-summary",
            "--active-task-summary", f"CLI checkpoint {index}.",
        ],
        capture_output=True,
        text=True,
    )


def test_cli_active_task_summary_converges(tmp_path: Path) -> None:
    head = _init_git_repo(tmp_path)
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))

    for index in range(3):
        result = _run_cli(tmp_path, head, index)
        assert result.returncode == 0, result.stdout + result.stderr

    assert "Superseded previous active-task projection" in result.stdout
    assert count_projections(active) == 1
    assert b"CLI checkpoint 2." in active.read_bytes()
    assert strip_projections(active.read_bytes()) == AGENT_HEADER.encode("utf-8")

    snapshot = active.read_bytes()
    rerun = _run_cli(tmp_path, head, 2)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert "Already present" in rerun.stdout
    assert active.read_bytes() == snapshot
