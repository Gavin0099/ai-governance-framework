#!/usr/bin/env python3
"""Small, failure-safe writers for live-canary evidence artifacts."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any


def atomic_write_json(path: str, value: Any) -> None:
    """Serialize completely, then atomically replace *path*.

    Serialization happens before a temporary file is created.  A value that
    JSON cannot represent therefore leaves neither a plausible partial artifact
    nor damage to an existing artifact at the destination.
    """
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    destination = os.path.abspath(path)
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        dir=directory,
        prefix=f".{os.path.basename(destination)}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
