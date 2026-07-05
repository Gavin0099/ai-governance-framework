"""Producer-side tests for the test_evidence receipt writer.

Contract: docs/governance/self-governance-evidence-artifact-metadata-design-2026-07-04.md

The writer must produce receipts the guard's validator accepts, tee raw
output, and stay a transparent wrapper (exit code passthrough). It proves
recording, never truth: fabricating the JSON directly remains possible.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.memory_authority_guard import (
    _validate_evidence_receipt,
    run_guard,
)
from governance_tools.test_evidence_receipt_writer import write_receipt


def test_passing_command_produces_valid_receipt(tmp_path: Path) -> None:
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "print('42 passed')"],
        output=Path("artifacts/runtime/test-results/run.json"),
    )

    assert exit_code == 0
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert _validate_evidence_receipt(payload) is None
    assert payload["exit_code"] == 0
    # Raw output is teed to a sibling artifact and referenced.
    raw = tmp_path / payload["output_artifacts"][0]
    assert raw.is_file()
    assert "42 passed" in raw.read_text(encoding="utf-8")
    # tmp_path is not itself a worktree top-level: linked_commit records that
    # honestly — even when the temp dir happens to live inside some outer
    # repository (review finding: `git -C` walks up parent directories).
    assert payload["linked_commit"] == "no_git_worktree"


def test_linked_commit_binds_only_when_project_root_is_the_worktree_root(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "seed"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    receipt_path, _ = write_receipt(
        tmp_path,
        [sys.executable, "-c", "print('ok')"],
        output=Path("artifacts/runtime/test-results/root.json"),
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["linked_commit"] == head

    # A subdirectory of the same repo is NOT the worktree root: the receipt
    # must not silently link the containing repo's HEAD.
    subdir = tmp_path / "nested" / "scratch"
    subdir.mkdir(parents=True)
    receipt_path, _ = write_receipt(
        subdir,
        [sys.executable, "-c", "print('ok')"],
        output=Path("artifacts/runtime/test-results/nested.json"),
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["linked_commit"] == "no_git_worktree"


def test_out_of_root_output_is_rejected_before_running_the_command(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "repo"
    project_root.mkdir()
    outside = tmp_path / "outside" / "receipt.json"
    marker = tmp_path / "command-ran.marker"

    with pytest.raises(SystemExit):
        write_receipt(
            project_root,
            [sys.executable, "-c", f"open(r'{marker}', 'w').close()"],
            output=outside,
        )

    # Zero side effects on rejection: the command never ran and no half-baked
    # artifacts were written outside the boundary.
    assert not marker.exists()
    assert not outside.exists()
    assert not outside.with_suffix(".txt").exists()


def test_failing_command_records_and_passes_through_exit_code(tmp_path: Path) -> None:
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        output=Path("artifacts/runtime/test-results/fail.json"),
    )

    assert exit_code == 3
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 3
    assert _validate_evidence_receipt(payload) is None


def test_produced_receipt_satisfies_guard_end_to_end(tmp_path: Path) -> None:
    # Full loop: writer produces a receipt, a memory entry references it as
    # success evidence, and the guard's metadata layer stays silent.
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "print('ok')"],
        output=Path("artifacts/runtime/test-results/e2e.json"),
    )
    assert exit_code == 0

    relative = receipt_path.resolve().relative_to(tmp_path.resolve()).as_posix()
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    (memory_root / "2026-07-05.md").write_text(
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: writer end-to-end fixture\n"
        f"  test_evidence: PASS: {relative} -> exit_code=0\n"
        "  next_step: none\n",
        encoding="utf-8",
    )

    result = run_guard(memory_root, tmp_path, skip_git=True)
    counts = result["violation_counts_by_code"]
    for code in (
        "test_evidence_provenance_not_found",
        "test_evidence_artifact_metadata_missing",
        "test_evidence_artifact_metadata_invalid",
        "test_evidence_exit_code_contradicts_claim",
    ):
        assert code not in counts


def test_failing_run_referenced_as_success_contradicts_claim(tmp_path: Path) -> None:
    # The loop the design exists for: a run that failed cannot be quoted as
    # passing evidence without the guard noticing the contradiction.
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "import sys; sys.exit(1)"],
        output=Path("artifacts/runtime/test-results/lied.json"),
    )
    assert exit_code == 1

    relative = receipt_path.resolve().relative_to(tmp_path.resolve()).as_posix()
    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    (memory_root / "2026-07-05.md").write_text(
        "- memory_type: session-derived\n"
        "  record_format_version: 1.0\n"
        "  writer: governance_tools.memory_record\n"
        "  what_changed: dishonest success claim fixture\n"
        f"  test_evidence: PASS: {relative} -> all good\n"
        "  next_step: none\n",
        encoding="utf-8",
    )

    result = run_guard(memory_root, tmp_path, skip_git=True)
    counts = result["violation_counts_by_code"]
    assert counts["test_evidence_exit_code_contradicts_claim"] == 1
