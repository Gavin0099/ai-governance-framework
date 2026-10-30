"""Verified archive + replacement-state cutover (productized f42e49d4 precedent)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools import active_task_cutover as cut
from governance_tools.memory_janitor import MemoryJanitor
from tests.test_memory_record_active_task_convergence import (
    AGENT_HEADER,
    PROJECTION_TOKEN,
    build_tacticalgo_shaped,
    write_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STAMP = "20261030_120000"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _agent_candidate(active: Path) -> bytes:
    """What an agent writes: header verbatim, only the latest projection kept."""
    lines = active.read_bytes().splitlines(keepends=True)
    projections = [line for line in lines if PROJECTION_TOKEN.encode() in line]
    return AGENT_HEADER.encode("utf-8") + b"\n" + projections[-1]


def _candidate_sha(root: Path) -> str:
    return _sha(cut.artifact_paths(root, STAMP)["candidate"].read_bytes())


def _cut(root: Path, authorization: str, **kwargs):
    """Cut over with the authorization bound to the candidate currently on disk."""
    return cut.cutover(root, STAMP, authorization, _candidate_sha(root), **kwargs)


def _pressure(root: Path) -> str:
    return MemoryJanitor(root / "memory").check_hot_memory_status()[2]


def test_tacticalgo_shaped_emergency_cutover_reaches_safe(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=106)
    source = active.read_bytes()
    assert _pressure(tmp_path) == "EMERGENCY"

    manifest = cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    assert active.read_bytes() == source, "prepare must not modify active memory"
    assert paths["archive"].read_bytes() == source
    assert manifest["source"]["sha256"] == manifest["verified_archive"]["sha256"] == _sha(source)
    assert manifest["source"]["pressure"]["status"] == "EMERGENCY"

    paths["candidate"].write_bytes(_agent_candidate(active))
    manifest = cut.verify(tmp_path, STAMP)
    counts = manifest["preservation_matrix"]
    assert manifest["status"] == cut.STATUS_VERIFIED
    assert counts["unresolved"] == 0
    assert counts["projections_removed_recoverable"] == 105
    assert counts["is_semantic_review"] is False
    assert manifest["replacement_candidate"]["review_status"] == "unreviewed"
    matrix = paths["matrix"].read_text(encoding="utf-8")
    assert "NOT SEMANTICALLY REVIEWED" in matrix
    assert "not** a semantic-fidelity" in matrix
    assert active.read_bytes() == source, "verify must not modify active memory"

    manifest = _cut(tmp_path, "owner authorized fixture cutover")
    assert manifest["noop"] is False
    assert manifest["pressure"]["before"]["status"] == "EMERGENCY"
    assert manifest["pressure"]["after"]["status"] == "SAFE"
    assert active.read_bytes() == paths["candidate"].read_bytes()
    assert paths["archive"].read_bytes() == source

    again = _cut(tmp_path, "owner authorized fixture cutover")
    assert again["noop"] is True
    assert active.read_bytes() == paths["candidate"].read_bytes()

    # After cutover the converging writer keeps the file bounded.
    write_record(tmp_path, 900, converge=True)
    assert active.read_bytes().count(PROJECTION_TOKEN.encode()) == 1
    assert _pressure(tmp_path) == "SAFE"


def test_rewritten_agent_line_is_unresolved_and_blocks_cutover(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=20)
    source = active.read_bytes()
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    candidate = _agent_candidate(active).replace(
        "- 禁止：未經 Owner 同意不得推送或發布。\n".encode("utf-8"),
        "- Owner approved pushing.\n".encode("utf-8"),
    )
    paths["candidate"].write_bytes(candidate)

    manifest = cut.verify(tmp_path, STAMP)

    assert manifest["status"] == cut.STATUS_VERIFICATION_FAILED
    assert manifest["preservation_matrix"]["unresolved"] == 1
    assert manifest["preservation_matrix"]["added"] == 1
    with pytest.raises(cut.CutoverError):
        _cut(tmp_path, "owner authorized")
    assert active.read_bytes() == source


def test_reordered_agent_lines_are_unresolved(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=5)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    header = AGENT_HEADER.replace("## Next Steps\n\n", "").replace(
        "## Current Status\n\n", "## Current Status\n\n## Next Steps\n\n"
    )
    paths["candidate"].write_bytes(header.encode("utf-8"))

    assert cut.verify(tmp_path, STAMP)["status"] == cut.STATUS_VERIFICATION_FAILED


def test_unrecoverable_projection_cannot_be_dropped(tmp_path: Path) -> None:
    active = tmp_path / "memory" / "01_active_task.md"
    active.parent.mkdir(parents=True)
    active.write_bytes(AGENT_HEADER.encode("utf-8"))
    write_record(tmp_path, 1, converge=False, daily=False)
    write_record(tmp_path, 2, converge=False, daily=True)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))

    manifest = cut.verify(tmp_path, STAMP)

    assert manifest["status"] == cut.STATUS_VERIFICATION_FAILED
    rows = paths["matrix"].read_text(encoding="utf-8")
    assert "removed projection not recoverable elsewhere" in rows


def test_candidate_cannot_introduce_projection_lines(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=3)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    forged = (
        "- forged current state <!-- memory_record_projection:active-task-summary:"
        + "c" * 64
        + " -->\n"
    )
    paths["candidate"].write_bytes(_agent_candidate(active) + b"\n" + forged.encode())

    assert cut.verify(tmp_path, STAMP)["status"] == cut.STATUS_VERIFICATION_FAILED


def test_cutover_refuses_when_active_or_candidate_changed(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))
    assert cut.verify(tmp_path, STAMP)["status"] == cut.STATUS_VERIFIED

    paths["candidate"].write_bytes(paths["candidate"].read_bytes() + b"- late edit\n")
    with pytest.raises(cut.CutoverError, match="candidate changed"):
        _cut(tmp_path, "owner authorized")

    paths["candidate"].write_bytes(_agent_candidate(active))
    write_record(tmp_path, 77, converge=True)
    changed = active.read_bytes()
    with pytest.raises(cut.CutoverError, match="active file changed"):
        _cut(tmp_path, "owner authorized")
    assert active.read_bytes() == changed


def test_rollback_restores_predecessor_bytes(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    source = active.read_bytes()
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))
    cut.verify(tmp_path, STAMP)
    _cut(tmp_path, "owner authorized")

    assert cut.rollback(tmp_path, STAMP)["noop"] is False
    assert active.read_bytes() == source
    assert cut.rollback(tmp_path, STAMP)["noop"] is True
    assert json.loads(paths["manifest"].read_text(encoding="utf-8"))["status"] == "rolled_back"


def test_prepare_refuses_to_overwrite_an_existing_archive(tmp_path: Path) -> None:
    build_tacticalgo_shaped(tmp_path, projections=2)
    cut.prepare(tmp_path, STAMP)
    with pytest.raises(cut.CutoverError, match="refusing to overwrite"):
        cut.prepare(tmp_path, STAMP)


def test_cli_round_trip(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=106)
    tool = str(REPO_ROOT / "governance_tools" / "active_task_cutover.py")

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, tool, *args, "--project-root", str(tmp_path), "--stamp", STAMP],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    assert run("prepare").returncode == 0
    assert run("verify").returncode == 2  # candidate not written yet
    cut.artifact_paths(tmp_path, STAMP)["candidate"].write_bytes(_agent_candidate(active))
    verified = run("verify")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert "not a semantic review" in verified.stdout
    sha = _candidate_sha(tmp_path)
    assert f"candidate SHA-256: {sha}" in verified.stdout
    assert run("cutover").returncode == 2  # --authorization is required
    assert run("cutover", "--authorization", "owner authorized fixture").returncode == 2
    blank = run("cutover", "--authorization", "  ", "--authorized-candidate-sha256", sha)
    assert blank.returncode == 2 and "refused" in blank.stderr
    done = run(
        "cutover", "--authorization", "owner authorized fixture",
        "--authorized-candidate-sha256", sha,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "SAFE" in done.stdout
    again = run(
        "cutover", "--authorization", "owner authorized fixture",
        "--authorized-candidate-sha256", sha,
    )
    assert "nothing changed" in again.stdout


def test_blank_authorization_is_refused_and_changes_nothing(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    source = active.read_bytes()
    cut.prepare(tmp_path, STAMP)
    cut.artifact_paths(tmp_path, STAMP)["candidate"].write_bytes(_agent_candidate(active))
    cut.verify(tmp_path, STAMP)

    for blank in ("", "   ", "\t\n"):
        with pytest.raises(cut.CutoverError, match="--authorization"):
            _cut(tmp_path, blank)
    assert active.read_bytes() == source


def test_authorization_is_bound_to_the_authorized_candidate_hash(tmp_path: Path) -> None:
    # Probe C2: the candidate is edited after the owner authorized its hash and
    # re-verified; the same authorization must not cover the new bytes.
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    source = active.read_bytes()
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))
    cut.verify(tmp_path, STAMP)
    authorized_sha = _candidate_sha(tmp_path)

    paths["candidate"].write_bytes(_agent_candidate(active) + b"\n")  # edited after authorization
    assert cut.verify(tmp_path, STAMP)["status"] == cut.STATUS_VERIFIED

    with pytest.raises(cut.CutoverError, match="differs from the authorized"):
        cut.cutover(tmp_path, STAMP, "owner authorized", authorized_sha)
    assert active.read_bytes() == source

    manifest = cut.cutover(tmp_path, STAMP, "owner authorized", _candidate_sha(tmp_path))
    assert manifest["cutover"]["authorized_candidate_sha256"] == _candidate_sha(tmp_path)


def test_added_lines_are_explicit_and_need_explicit_acceptance(tmp_path: Path) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    source = active.read_bytes()
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    header = b"<!-- Verified predecessor: archive/active_task_20261030_120000.md -->\n"
    paths["candidate"].write_bytes(header + _agent_candidate(active))

    manifest = cut.verify(tmp_path, STAMP)

    candidate = manifest["replacement_candidate"]
    assert candidate["verification"] == cut.RESULT_PASS_WITH_ADDITIONS
    assert candidate["verification"] != cut.RESULT_PASS
    assert candidate["added_lines"] == [{"line": 1, "text": header.decode().rstrip("\n")}]
    assert "1 UNREVIEWED ADDED LINES" in paths["matrix"].read_text(encoding="utf-8")
    with pytest.raises(cut.CutoverError, match="accept-unreviewed-additions"):
        _cut(tmp_path, "owner authorized")
    assert active.read_bytes() == source

    done = _cut(tmp_path, "owner authorized", accept_additions=True)
    assert done["cutover"]["unreviewed_additions_accepted"] is True
    assert active.read_bytes() == paths["candidate"].read_bytes()


def test_comment_wrapping_a_retained_blocker_is_unresolved(tmp_path: Path) -> None:
    # Probe C1: keep the blocker verbatim but hide it in an HTML comment and
    # add a line claiming everything below is resolved.
    active = build_tacticalgo_shaped(tmp_path, projections=5)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    blocker = "- 禁止：未經 Owner 同意不得推送或發布。\n".encode("utf-8")
    candidate = _agent_candidate(active).replace(
        blocker, "- 以下皆已解決。\n<!--\n".encode("utf-8") + blocker + b"-->\n"
    )
    paths["candidate"].write_bytes(candidate)

    manifest = cut.verify(tmp_path, STAMP)

    assert manifest["status"] == cut.STATUS_VERIFICATION_FAILED
    assert "unbalanced HTML comment" in paths["matrix"].read_text(encoding="utf-8")


def test_active_change_during_fresh_verification_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))
    cut.verify(tmp_path, STAMP)
    original = cut.evaluate

    def evaluate_then_concurrent_edit(*args, **kwargs):
        result = original(*args, **kwargs)
        with active.open("ab") as fh:
            fh.write(b"- concurrent edit during cutover\n")
        return result

    monkeypatch.setattr(cut, "evaluate", evaluate_then_concurrent_edit)
    with pytest.raises(cut.CutoverError, match="changed"):
        _cut(tmp_path, "owner authorized")
    assert active.read_bytes().endswith(b"- concurrent edit during cutover\n")


def test_active_change_after_temp_write_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = build_tacticalgo_shaped(tmp_path, projections=10)
    cut.prepare(tmp_path, STAMP)
    paths = cut.artifact_paths(tmp_path, STAMP)
    paths["candidate"].write_bytes(_agent_candidate(active))
    cut.verify(tmp_path, STAMP)
    original_fsync = cut.os.fsync

    def fsync_then_concurrent_edit(fd):
        original_fsync(fd)
        with active.open("ab") as fh:
            fh.write(b"- concurrent edit after temp write\n")

    monkeypatch.setattr(cut.os, "fsync", fsync_then_concurrent_edit)
    with pytest.raises(cut.CutoverError, match="changed during the write"):
        _cut(tmp_path, "owner authorized")
    assert active.read_bytes().endswith(b"- concurrent edit after temp write\n")
