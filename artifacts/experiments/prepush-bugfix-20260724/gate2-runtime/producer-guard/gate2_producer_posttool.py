#!/usr/bin/env python3
"""Gate 2 producer guard — PostToolUse hook (result half of the transcript).

Records the outcome of an allowed adapter call under the same run_id as the
PreToolUse event, so a reviewer can follow one chain:

    model request  (pre_tool_use event: verb, arg, command digest)
      -> adapter   (adapter log line: verb, exit, out_bytes, out_sha256)
        -> container output
          -> model  (post_tool_use event: exit, output digest)

It records digests, never payloads: a nonce that only exists inside the
container must not be copied into the transcript.

Environment: GATE2_RUN_ID, GATE2_TRANSCRIPT (see the PreToolUse guard).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(record: dict) -> None:
    try:
        path = os.environ.get("GATE2_TRANSCRIPT", "gate2-transcript.jsonl")
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _digest(value) -> tuple[str | None, int | None]:
    if value is None:
        return None, None
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    tool_input = payload.get("tool_input", {}) or {}
    response = payload.get("tool_response")
    out_sha, out_len = _digest(response)
    cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    _emit(
        {
            "ts": _now(),
            "run_id": os.environ.get("GATE2_RUN_ID", "unset"),
            "event": "post_tool_use",
            "tool": payload.get("tool_name", "<unknown>"),
            # correlates to the pre_tool_use event with the same command digest
            "command_sha256": hashlib.sha256(cmd.encode("utf-8")).hexdigest() if cmd else None,
            "output_sha256": out_sha,
            "output_len": out_len,
            "session_id": payload.get("session_id"),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
