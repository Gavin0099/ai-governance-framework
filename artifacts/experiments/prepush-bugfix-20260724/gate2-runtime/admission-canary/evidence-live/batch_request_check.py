#!/usr/bin/env python3
"""Prove whether one assistant message actually requested multiple tool calls."""
from __future__ import annotations

import argparse
import json
import time

from evidence_io import atomic_write_json


def inspect(session_log: str) -> dict:
    by_message: dict[str, dict[str, dict]] = {}
    with open(session_log, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("type") != "assistant":
                continue
            message = row.get("message")
            if not isinstance(message, dict):
                continue
            message_id = str(message.get("id") or row.get("uuid") or "")
            calls = by_message.setdefault(message_id, {})
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_id = str(block.get("id") or len(calls))
                    calls[tool_id] = {
                        "id": block.get("id"),
                        "name": block.get("name"),
                    }

    batches = [
        {"message_id": message_id, "tool_calls": list(calls.values())}
        for message_id, calls in by_message.items()
        if len(calls) > 1
    ]
    maximum = max((len(calls) for calls in by_message.values()), default=0)
    return {
        "status": "GO" if batches else "NO-GO",
        "multi_tool_message_observed": bool(batches),
        "assistant_messages": len(by_message),
        "max_tool_calls_in_one_message": maximum,
        "batches": batches,
        "claim_boundary": (
            "A multi-tool assistant message proves a batch request. "
            "Only adapter lock_wait_ms can prove overlapping execution."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-log", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--wait-seconds", type=float, default=30.0)
    args = parser.parse_args()

    deadline = time.monotonic() + max(args.wait_seconds, 0.0)
    while True:
        result = inspect(args.session_log)
        if result["multi_tool_message_observed"] or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    atomic_write_json(args.out, result)
    print(
        f"{result['status']}: max_tool_calls_in_one_message="
        f"{result['max_tool_calls_in_one_message']}"
    )
    return 0 if result["multi_tool_message_observed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
