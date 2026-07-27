#!/usr/bin/env python3
"""Stream one admission input into the writable /work tmpfs.

Docker ``cp`` refuses a read-only container even when its destination is a
writable tmpfs.  The operator therefore sends bytes to a fixed ``cp
/dev/stdin`` argv inside the container.  Only the two admission seed targets
are accepted.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


TARGETS = {
    "baseline": "/work/sanitized-baseline.tar",
    "pytest": "/work/vendor/offline-pytest.zip",
    "task": "/work/input/TASK.md",
    "skill": "/work/input/SKILL.md",
    "governance": "/work/input/GOVERNANCE.md",
    "validators": "/work/input/VALIDATORS.md",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--kind", choices=sorted(TARGETS), required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    payload = args.source.read_bytes()
    completed = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "-u",
            "65532:65532",
            args.container,
            "cp",
            "/dev/stdin",
            TARGETS[args.kind],
        ],
        input=payload,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
