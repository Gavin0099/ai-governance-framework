"""Producer-side tests for the test_evidence receipt writer.

Contract: docs/governance/self-governance-evidence-artifact-metadata-design-2026-07-04.md

The writer must produce receipts the guard's validator accepts, tee raw
output, and stay a transparent wrapper (exit code passthrough). It proves
recording, never truth: fabricating the JSON directly remains possible.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from governance_tools.memory_authority_guard import (
    _validate_evidence_receipt,
    run_guard,
)
from governance_tools.evidence_roots import find_evidence_tokens, policy_from_values
from governance_tools.memory_provenance import _is_closeout_companion_path
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


@pytest.mark.parametrize("compress_output", [False, True])
def test_out_of_root_output_is_rejected_before_running_the_command(
    tmp_path: Path, compress_output: bool,
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
            compress_output=compress_output,
        )

    # Zero side effects on rejection: the command never ran and no half-baked
    # artifacts were written outside the boundary.
    assert not marker.exists()
    assert not outside.exists()
    assert not outside.with_suffix(".txt").exists()
    assert not outside.with_suffix(".txt.gz").exists()


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


@pytest.mark.parametrize("compress_output", [False, True])
def test_produced_receipt_satisfies_guard_end_to_end(
    tmp_path: Path, compress_output: bool,
) -> None:
    # Full loop: writer produces a receipt, a memory entry references it as
    # success evidence, and the guard's metadata layer stays silent.
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "print('ok')"],
        output=Path("artifacts/runtime/test-results/e2e.json"),
        compress_output=compress_output,
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


@pytest.mark.parametrize("compress_output", [False, True])
def test_failing_run_referenced_as_success_contradicts_claim(
    tmp_path: Path, compress_output: bool,
) -> None:
    # The loop the design exists for: a run that failed cannot be quoted as
    # passing evidence without the guard noticing the contradiction.
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", "import sys; sys.exit(1)"],
        output=Path("artifacts/runtime/test-results/lied.json"),
        compress_output=compress_output,
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


@pytest.mark.parametrize(
    "text, expected_summary",
    [
        ("", {"bytes": 0, "lines": 0, "sha256":
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}),
        ("abc", {"bytes": 3, "lines": 1, "sha256":
                 "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}),
    ],
)
def test_compressed_output_records_exact_counts_and_known_digest(
    tmp_path: Path, text: str, expected_summary: dict,
) -> None:
    receipt_path, exit_code = write_receipt(
        tmp_path,
        [sys.executable, "-c", f"import sys; sys.stdout.write({text!r})"],
        output=Path("artifacts/evidence/test-results/receipt-counts.json"),
        compress_output=True,
    )
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw = tmp_path / payload["output_artifacts"][0]

    assert exit_code == 0
    assert payload["raw_output"] == expected_summary
    assert _validate_evidence_receipt(payload) is None
    assert raw.name == "receipt-counts.txt.gz"
    assert gzip.decompress(raw.read_bytes()) == text.encode("utf-8")
    assert not raw.with_suffix("").exists()


def test_compressed_output_preserves_plain_writer_bytes_and_console(
    tmp_path: Path, capsys,
) -> None:
    # Characterization: compressed recording must restore the bytes the
    # existing text writer stores, including the platform's newline encoding.
    command = [sys.executable, "-X", "utf8", "-u", "-c",
               "import sys; print('42 passed'); "
               "print('\\u8b66\\u544a', file=sys.stderr); sys.stdout.write('tail')"]
    plain, _ = write_receipt(tmp_path, command, output=Path("plain.json"))
    plain_console = capsys.readouterr().out
    compressed, _ = write_receipt(
        tmp_path, command, output=Path("compressed.json"), compress_output=True,
    )
    compressed_console = capsys.readouterr().out
    plain_payload = json.loads(plain.read_text(encoding="utf-8"))
    payload = json.loads(compressed.read_text(encoding="utf-8"))
    plain_bytes = (tmp_path / plain_payload["output_artifacts"][0]).read_bytes()
    restored = gzip.decompress((tmp_path / payload["output_artifacts"][0]).read_bytes())

    assert restored == plain_bytes
    assert compressed_console == plain_console == "42 passed\n\u8b66\u544a\ntail"
    assert payload["raw_output"]["bytes"] == len(plain_bytes)
    assert payload["raw_output"]["lines"] == 3
    assert payload["raw_output"]["sha256"] == hashlib.sha256(plain_bytes).hexdigest()
    assert "raw_output" not in plain_payload
    for field in ("receipt_schema", "status", "command", "runner", "linked_commit", "cannot_claim"):
        assert payload[field] == plain_payload[field]


@pytest.mark.parametrize("exit_code, suffix, verdict", [(0, ".txt.gz", "PASS"), (3, ".txt", "FAIL")])
def test_compress_option_cli_cites_actual_output_and_preserves_exit_code(
    tmp_path: Path, exit_code: int, suffix: str, verdict: str,
) -> None:
    writer = Path(__file__).resolve().parents[1] / "governance_tools/test_evidence_receipt_writer.py"
    outputs = []
    for name in ("first", "second"):
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", str(writer), "--project-root", str(tmp_path),
             "--output", f"artifacts/evidence/test-results/receipt-{name}.json",
             "--compress-output", "--", sys.executable, "-c",
             f"import sys; sys.stdout.write('result'); sys.exit({exit_code})"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        assert completed.returncode == exit_code, completed.stdout + completed.stderr
        assert f"test_evidence: {verdict}:" in completed.stdout
        payload = json.loads((tmp_path / f"artifacts/evidence/test-results/receipt-{name}.json").read_text(encoding="utf-8"))
        assert payload["exit_code"] == exit_code
        evidence = next(line for line in completed.stdout.splitlines() if "test_evidence:" in line)
        cited = set(find_evidence_tokens(evidence, policy_from_values(None)))
        raw = payload["output_artifacts"][0]
        assert raw == f"artifacts/evidence/test-results/receipt-{name}{suffix}"
        assert cited == {f"artifacts/evidence/test-results/receipt-{name}.json", raw}
        assert _is_closeout_companion_path(raw, plan_updated=False, cited_artifacts=cited)
        output = (tmp_path / payload["output_artifacts"][0]).read_bytes()
        if exit_code == 0:
            assert gzip.decompress(output) == b"result"
            assert "raw_output" in payload
            assert not (tmp_path / raw).with_suffix("").exists()
        else:
            assert output == b"result"
            assert "raw_output" not in payload
            assert not (tmp_path / (raw + ".gz")).exists()
        outputs.append(output)
    assert outputs[0] == outputs[1]


def test_compress_option_failure_matches_default_bytes_receipt_and_console(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    monkeypatch.setattr(
        "governance_tools.test_evidence_receipt_writer._utc_now_iso",
        lambda: "2026-01-01T00:00:00Z",
    )
    command = [sys.executable, "-X", "utf8", "-u", "-c",
               "import sys; print('\\u5931\\u6557'); "
               "print('failure detail', file=sys.stderr); sys.stdout.write('tail'); sys.exit(3)"]
    runs = []
    for compress_output in (False, True):
        project = tmp_path / ("requested" if compress_output else "default")
        project.mkdir()
        receipt, exit_code = write_receipt(
            project, command, output=Path("artifacts/evidence/test-results/receipt-failure.json"),
            compress_output=compress_output,
        )
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        assert exit_code == 3
        assert payload["output_artifacts"] == ["artifacts/evidence/test-results/receipt-failure.txt"]
        assert "raw_output" not in payload
        raw = project / payload["output_artifacts"][0]
        assert not raw.with_suffix(".txt.gz").exists()
        runs.append((raw.read_bytes(), receipt.read_bytes(), capsys.readouterr().out))

    assert runs[0] == runs[1]
    assert runs[0][2] == "\u5931\u6557\nfailure detail\ntail"


def test_compressed_output_survives_git_checkout(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    subprocess.run(["git", "-C", str(project), "init", "-q"], check=True)
    receipt, _ = write_receipt(
        project, [sys.executable, "-c", "print('42 passed')"],
        output=Path("artifacts/evidence/test-results/receipt-durable.json"),
        compress_output=True,
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    relative = receipt.relative_to(project).as_posix()
    raw = payload["output_artifacts"][0]
    (project / ".gitignore").write_text("artifacts/runtime/\nartifacts/session/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(project), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "record evidence"], check=True,
    )
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "clone", "-q", str(project), str(checkout)], check=True)

    assert (checkout / relative).read_bytes() == receipt.read_bytes()
    assert (checkout / raw).read_bytes() == (project / raw).read_bytes()
    assert gzip.decompress((checkout / raw).read_bytes()).decode("utf-8").splitlines() == ["42 passed"]


def test_compressed_output_write_failure_does_not_publish_receipt(
    tmp_path: Path, monkeypatch,
) -> None:
    def unavailable(self, data):
        raise OSError("output unavailable")

    monkeypatch.setattr(Path, "write_bytes", unavailable)
    receipt = tmp_path / "receipt.json"
    with pytest.raises(OSError, match="output unavailable"):
        write_receipt(
            tmp_path, [sys.executable, "-c", "print('ok')"],
            output=receipt, compress_output=True,
        )
    assert not receipt.exists()
