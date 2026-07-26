#!/usr/bin/env python3
"""Compare the frozen prompt with the first user message in a Claude session."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from evidence_io import atomic_write_json


def _first_user_text(session_log: str) -> tuple[str | None, int | None]:
    with open(session_log, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # The operator may invoke this while Claude is appending the
                # first record. A partial final JSONL line is not yet evidence
                # of mismatch; a bounded caller retry decides the outcome.
                continue
            if row.get("type") != "user":
                continue
            message = row.get("message")
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                return content, line_number
    return None, None


def _first_difference(expected: str, actual: str) -> dict | None:
    limit = min(len(expected), len(actual))
    for index in range(limit):
        if expected[index] != actual[index]:
            return {
                "index": index,
                "expected_codepoint": f"U+{ord(expected[index]):04X}",
                "actual_codepoint": f"U+{ord(actual[index]):04X}",
            }
    if len(expected) != len(actual):
        return {
            "index": limit,
            "expected_codepoint": (
                f"U+{ord(expected[limit]):04X}" if limit < len(expected) else "<end>"
            ),
            "actual_codepoint": (
                f"U+{ord(actual[limit]):04X}" if limit < len(actual) else "<end>"
            ),
        }
    return None


def compare(prompt_path: str, session_log: str) -> dict:
    source_bytes = Path(prompt_path).read_bytes()
    source_text = source_bytes.decode("utf-8")
    session_text, line_number = _first_user_text(session_log)
    exact = session_text == source_text
    actual_bytes = session_text.encode("utf-8") if session_text is not None else b""
    return {
        "status": "GO" if exact else "NO-GO",
        "exact_prompt_match": exact,
        "prompt_path": prompt_path,
        "session_log": session_log,
        "session_user_line": line_number,
        "source_bytes": len(source_bytes),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "session_utf8_bytes": len(actual_bytes) if session_text is not None else None,
        "session_utf8_sha256": (
            hashlib.sha256(actual_bytes).hexdigest() if session_text is not None else None
        ),
        "source_codepoints": len(source_text),
        "session_codepoints": len(session_text) if session_text is not None else None,
        "first_difference": (
            _first_difference(source_text, session_text)
            if session_text is not None and not exact
            else None
        ),
        "errors": (
            [] if exact else
            ["session log contains no user message"] if session_text is None else
            ["first session user message is not exactly the frozen prompt"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--session-log", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=30.0,
        help="bounded wait for the first complete user record in an active JSONL log",
    )
    args = parser.parse_args()

    deadline = time.monotonic() + max(args.wait_seconds, 0.0)
    while True:
        result = compare(args.prompt, args.session_log)
        if result["session_user_line"] is not None or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    atomic_write_json(args.out, result)
    print(
        f"{result['status']}: exact_prompt_match="
        f"{str(result['exact_prompt_match']).lower()}"
    )
    if result["first_difference"]:
        print(f"  first_difference={result['first_difference']}")
    return 0 if result["exact_prompt_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
