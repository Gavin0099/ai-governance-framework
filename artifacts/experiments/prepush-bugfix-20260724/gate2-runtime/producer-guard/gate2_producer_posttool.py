#!/usr/bin/env python3
"""Gate 2 producer guard — result half of the transcript.

Wire this ONE script to both post events:

    PostToolUse         the tool ran and returned a result   -> `tool_response`
    PostToolUseFailure  the tool call failed                 -> `error`

Both payloads carry the same `tool_use_id` the PreToolUse hook saw, so the chain
is joined by identity, not by re-hashing the command and hoping two identical
calls never happen:

    model request  (pre_tool_use   : tool_use_id, verb, args, command digest)
      -> adapter   (adapter log    : seq, verb, exit, stdout digest)
        -> container output
          -> model  (post_tool_use / post_tool_use_failure : same tool_use_id)

THE COMMON OBSERVABLE. The adapter hashes the exact bytes it writes to stdout,
normalised as `s.rstrip("\\r\\n")`; this hook hashes `tool_response["stdout"]`
with the identical normalisation and reports it as `stdout_sha256`. That is the
one value both sides define the same way, so a reviewer can join them. The
digest of the whole structured response is kept separately as `response_sha256`
-- useful, but it is not a shared observable and must not be compared with the
adapter's.

Digests, never payloads: a nonce that only exists inside the container must not
be copied into the transcript, so this records hashes, lengths and key names.

A post hook cannot block -- the tool has already run. If it cannot write, it
exits 2 so the failure is visible, and the transcript then has a pre event with
no terminal event, which the verifier reports as a broken chain rather than
silently accepting.

Environment: GATE2_RUN_ID, GATE2_TRANSCRIPT (see the PreToolUse guard).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

EVENT_FOR = {
    "PostToolUse": "post_tool_use",
    "PostToolUseFailure": "post_tool_use_failure",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(text: str) -> str:
    """The shared observable definition. Both sides MUST use this and only this."""
    return text.rstrip("\r\n")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _emit(record: dict) -> None:
    path = os.environ.get("GATE2_TRANSCRIPT", "gate2-transcript.jsonl")
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def observable(response) -> tuple[str | None, int | None, str]:
    """(stdout_sha256, stdout_len, source) for the shared observable."""
    if isinstance(response, dict):
        out = response.get("stdout")
        if isinstance(out, str):
            norm = normalise(out)
            return sha(norm), len(norm), "tool_response.stdout"
        return None, None, "tool_response has no string stdout"
    if isinstance(response, str):
        norm = normalise(response)
        return sha(norm), len(norm), "tool_response (plain string)"
    return None, None, f"tool_response is {type(response).__name__}"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as exc:
        print(f"gate2 post hook: unreadable payload ({exc})", file=sys.stderr)
        return 2

    hook_event = payload.get("hook_event_name", "PostToolUse")
    event = EVENT_FOR.get(hook_event)
    if event is None:
        print(f"gate2 post hook: wired to unexpected event {hook_event!r}", file=sys.stderr)
        return 2

    tool_use_id = payload.get("tool_use_id")
    if not isinstance(tool_use_id, str) or not tool_use_id:
        # Recorded anyway -- an uncorrelatable result is itself a finding, and
        # dropping it would hide the break.
        tool_use_id = None

    tool_input = payload.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    response = payload.get("tool_response")
    error = payload.get("error")

    stdout_sha, stdout_len, source = observable(response)
    canonical = None if response is None else json.dumps(response, sort_keys=True, default=str)

    record = {
        "ts": _now(),
        "run_id": os.environ.get("GATE2_RUN_ID", "unset"),
        "tool_use_id": tool_use_id,
        "event": event,
        "hook_event_name": hook_event,
        "tool": payload.get("tool_name", "<unknown>"),
        # kept as a cross-check on the pre event, NOT as the correlation key
        "command_sha256": sha(cmd) if cmd else None,
        "stdout_sha256": stdout_sha,
        "stdout_len": stdout_len,
        "observable_source": source,
        "response_sha256": sha(canonical) if canonical is not None else None,
        "response_keys": sorted(response) if isinstance(response, dict) else None,
        "error_sha256": sha(error) if isinstance(error, str) and error else None,
        "error_len": len(error) if isinstance(error, str) else None,
        "session_id": payload.get("session_id"),
    }

    try:
        _emit(record)
    except OSError as exc:
        print(f"gate2 post hook: could not append to the transcript ({exc})", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
