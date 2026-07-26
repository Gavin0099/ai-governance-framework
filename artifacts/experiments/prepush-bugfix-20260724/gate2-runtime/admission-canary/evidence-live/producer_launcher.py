#!/usr/bin/env python3
"""Generate the byte-preserving Windows producer launcher used by the runbook."""
from __future__ import annotations

import argparse
import os
import subprocess

from evidence_io import atomic_write_text


def _safe_path(path: str) -> str:
    if any(char in path for char in ('"', "%", "\r", "\n")):
        raise ValueError(f"launcher path contains an unsafe cmd character: {path!r}")
    return path


def render_launcher(
    command: list[str],
    *,
    prompt: str,
    stdout: str,
    stderr: str,
    exit_code_out: str,
) -> str:
    """Render a batch file whose child stdin/stdout stay byte streams."""
    if not command:
        raise ValueError("launcher command is empty")
    for path in (prompt, stdout, stderr, exit_code_out):
        _safe_path(path)
    command_line = subprocess.list2cmdline(command)
    return (
        "@echo off\r\n"
        f'call {command_line} < "{prompt}" > "{stdout}" 2> "{stderr}"\r\n'
        'set "claudeExit=%errorlevel%"\r\n'
        f'> "{exit_code_out}" echo %claudeExit%\r\n'
        "exit /b %claudeExit%\r\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claude", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--exit-code-out", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    command = [
        args.claude,
        "-p",
        "--session-id", args.session_id,
        "--setting-sources", "project",
        "--permission-mode", "dontAsk",
        "--strict-mcp-config",
        "--output-format", "stream-json",
        "--verbose",
    ]
    launcher = render_launcher(
        command,
        prompt=os.path.abspath(args.prompt),
        stdout=os.path.abspath(args.stdout),
        stderr=os.path.abspath(args.stderr),
        exit_code_out=os.path.abspath(args.exit_code_out),
    )
    atomic_write_text(args.out, launcher)
    print(f"wrote byte-preserving launcher: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
