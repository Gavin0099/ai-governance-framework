#!/usr/bin/env python3
"""Run one command and atomically capture UTF-8 stdout/stderr and its exit."""
from __future__ import annotations

import argparse
import os
import subprocess

from evidence_io import atomic_write_bytes, atomic_write_text


def run_and_capture(
    command: list[str],
    *,
    stdout_path: str,
    stderr_path: str,
    exit_code_path: str,
) -> int:
    if not command:
        raise ValueError("capture command is empty")
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    atomic_write_bytes(stdout_path, completed.stdout)
    atomic_write_bytes(stderr_path, completed.stderr)
    atomic_write_text(exit_code_path, f"{completed.returncode}\n")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--exit-code-out", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    return run_and_capture(
        command,
        stdout_path=args.stdout,
        stderr_path=args.stderr,
        exit_code_path=args.exit_code_out,
    )


if __name__ == "__main__":
    raise SystemExit(main())
