"""Validate a pre-staged exact Codex executable for C1 pair-02.

The executable is an input artifact, not a publication location. Its path is
caller-supplied, while its complete byte identity is frozen here and
revalidated before any random-number access. This module performs no network
access, copying, cleanup, or work on import.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


CLI_VERSION = "codex-cli 0.148.0-alpha.9"
CLI_VERSION_STDOUT = b"codex-cli 0.148.0-alpha.9\n"
NATIVE_BYTES = 295_151_920
NATIVE_SHA256 = "f29f609375f3731d8db507a95124862a84e306982e30ba4300ddce5638bc6946"


class DistributionError(RuntimeError):
    """The pre-staged executable does not match the frozen identity."""


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_staged_executable(path: Path, *, cwd: Path) -> dict[str, object]:
    """Validate whole-file identity and a zero-session version launch."""

    executable = path.resolve()
    if not executable.is_file():
        raise DistributionError("pre-staged Codex executable is absent")
    if executable.stat().st_size != NATIVE_BYTES:
        raise DistributionError("pre-staged Codex executable byte count differs")
    if _digest(executable) != NATIVE_SHA256:
        raise DistributionError("pre-staged Codex executable SHA-256 differs")
    try:
        version = subprocess.run(
            [str(executable), "--version"],
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DistributionError("pre-staged Codex executable launch failed") from exc
    if (
        version.returncode != 0
        or version.stderr
        or version.stdout != CLI_VERSION_STDOUT
    ):
        raise DistributionError("pre-staged Codex version probe failed")
    return {
        "executable": executable,
        "native_bytes": NATIVE_BYTES,
        "native_sha256": NATIVE_SHA256,
        "version_stdout": version.stdout,
    }
