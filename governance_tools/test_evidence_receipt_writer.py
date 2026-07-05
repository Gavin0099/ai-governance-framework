#!/usr/bin/env python3
"""Run a command and emit a test_evidence_receipt.v0.1 artifact.

Producer side of the R3 evidence receipt design
(docs/governance/self-governance-evidence-artifact-metadata-design-2026-07-04.md).

Usage:
    python -m governance_tools.test_evidence_receipt_writer \
        [--project-root .] [--output artifacts/runtime/test-results/run.json] \
        [--runner NAME] -- <command> [args...]

Behavior:
  - runs the command, teeing combined stdout/stderr to a sibling .txt artifact;
  - writes a receipt recording command, exit_code, timestamps, runner,
    linked_commit (git HEAD when available), and the output artifact path;
  - prints the receipt path and a ready-to-paste test_evidence line;
  - exits with the wrapped command's exit code (transparent wrapper).

Claim ceiling: the receipt proves only that this wrapper recorded a run. Every
field can be fabricated by writing the JSON directly; consumers must never
treat a receipt as proof the command truly ran.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.memory_authority_guard import (
    _TEST_EVIDENCE_RECEIPT_SCHEMA,
    _validate_evidence_receipt,
)

_DEFAULT_OUTPUT_DIR = "artifacts/runtime/test-results"
_DEFAULT_RUNNER = "governance_tools.test_evidence_receipt_writer"
_CANNOT_CLAIM = [
    "semantic correctness of the tested behavior",
    "receipt authenticity: every field is fabricatable by a direct writer",
]


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head(project_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    head = completed.stdout.strip()
    return head if completed.returncode == 0 and head else "no_git_worktree"


def _relpath(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def write_receipt(
    project_root: Path,
    command: list[str],
    *,
    output: Path | None = None,
    runner: str = _DEFAULT_RUNNER,
) -> tuple[Path, int]:
    """Run `command`, write receipt + raw output artifacts, return (receipt_path, exit_code)."""
    if output is None:
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = project_root / _DEFAULT_OUTPUT_DIR / f"receipt-{stamp}.json"
    elif not output.is_absolute():
        output = project_root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path = output.with_suffix(".txt")

    started_at = _utc_now_iso()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    finished_at = _utc_now_iso()

    raw_output_path.write_text(completed.stdout or "", encoding="utf-8")
    if completed.stdout:
        sys.stdout.write(completed.stdout)

    payload = {
        "receipt_schema": _TEST_EVIDENCE_RECEIPT_SCHEMA,
        "status": "report_only",
        "command": subprocess.list2cmdline(command),
        "exit_code": completed.returncode,
        "started_at": started_at,
        "finished_at": finished_at,
        "runner": runner,
        "linked_commit": _git_head(project_root),
        "output_artifacts": [_relpath(raw_output_path, project_root)],
        "cannot_claim": list(_CANNOT_CLAIM),
    }

    error = _validate_evidence_receipt(payload)
    if error is not None:
        raise SystemExit(f"error: produced receipt failed self-validation: {error}")

    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output, completed.returncode


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run a command and emit a test_evidence_receipt.v0.1 artifact.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Repository root the receipt paths are relative to (default: .)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Receipt path relative to project root "
            f"(default: {_DEFAULT_OUTPUT_DIR}/receipt-<utc>.json)"
        ),
    )
    parser.add_argument(
        "--runner",
        default=_DEFAULT_RUNNER,
        help="Runner identity recorded in the receipt.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run (prefix with -- to separate from options).",
    )
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("no command given; pass it after --")

    project_root = Path(args.project_root)
    output = Path(args.output) if args.output else None

    receipt_path, exit_code = write_receipt(
        project_root, command, output=output, runner=args.runner
    )
    relative_receipt = _relpath(receipt_path, project_root)
    verdict = "PASS" if exit_code == 0 else "FAIL"
    print(f"[test_evidence_receipt] receipt={relative_receipt} exit_code={exit_code}")
    print(f"  test_evidence: {verdict}: {relative_receipt} -> exit_code={exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
