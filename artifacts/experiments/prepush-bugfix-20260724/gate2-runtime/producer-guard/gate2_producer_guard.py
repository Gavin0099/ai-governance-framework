#!/usr/bin/env python3
"""Gate 2 producer guard — PreToolUse hook.

Two jobs, both required before Gate 2 resource admission:

1. TECHNICAL ADAPTER EXCLUSIVITY. The producer context is allowed to invoke
   exactly one thing: the managed adapter, with an allowlisted verb and a
   regex-checked argument. Every other tool call -- `docker exec`, reading host
   files, git, network, editors -- is DENIED by the harness before it executes.
   This replaces the previous prompt-plus-log corroboration, under which a
   bypass simply would not appear in the adapter log.

2. MODEL TRANSCRIPT CAPTURE. Every decision is appended to a JSONL transcript
   with a run_id and a per-call request_id, recording the model's own tool
   request. The companion PostToolUse hook records the result under the same
   request_id, so `model request -> adapter -> container -> output` is a single
   correlated chain that artifacts alone can verify.

Wiring (producer context settings only -- NOT the design session's settings):

    "hooks": {
      "PreToolUse":  [{"hooks": [{"type": "command",
         "command": "python <this file>"}]}],
      "PostToolUse": [{"hooks": [{"type": "command",
         "command": "python <sibling>/gate2_producer_posttool.py"}]}]
    }

Environment:
    GATE2_ADAPTER      absolute path to the sanctioned adapter script (required)
    GATE2_RUN_ID       run identifier (default: "unset")
    GATE2_TRANSCRIPT   transcript path (default: ./gate2-transcript.jsonl)

Fail-closed: any error in this guard denies the call. A guard that cannot decide
must never let a call through.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

# The adapter's own contract, mirrored here so the guard can validate the whole
# invocation without executing anything.
VERB_RE = re.compile(r"^(ls|log|read)$")
ARG_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _transcript_path() -> str:
    return os.environ.get("GATE2_TRANSCRIPT", "gate2-transcript.jsonl")


def _emit(record: dict) -> None:
    """Append one transcript event. Never raises into the decision path."""
    try:
        with open(_transcript_path(), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _decide(allow: bool, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allow else "deny",
            "permissionDecisionReason": reason,
        }
    }


# Everything that could chain, redirect, substitute, expand or continue a line.
# Backslash is deliberately NOT here: Windows adapter paths contain it, and with
# quotes, `$`, backticks and newlines already banned, a backslash can at most
# escape a space -- which merges tokens and then fails the strict verb/arg
# patterns below. (An earlier version banned it and thereby denied every
# legitimate call on Windows; the hostile suite caught that.)
_METACHARS = ";|&<>`$(){}[]!*?\n\r\"'"


def _tokenize(command: str) -> list[str] | None:
    """Split a Bash command the adapter way: no shell metacharacters allowed.

    Rejected outright rather than parsed -- the guard must not try to out-clever
    a shell.
    """
    if any(ch in command for ch in _METACHARS):
        return None
    return command.split()


def evaluate(tool_name: str, tool_input: dict) -> tuple[bool, str, dict]:
    """Return (allow, reason, detail). Pure: no side effects, so it is testable."""
    adapter = os.environ.get("GATE2_ADAPTER", "")
    detail: dict = {"tool": tool_name}

    if not adapter:
        return False, "GATE2_ADAPTER is not configured; guard fails closed", detail

    # The producer context is given Bash solely to reach the adapter. Every
    # other tool is outside the sanctioned channel.
    if tool_name != "Bash":
        return False, f"tool {tool_name!r} is outside the adapter channel", detail

    command = (tool_input or {}).get("command", "")
    detail["command"] = command
    if not isinstance(command, str) or not command.strip():
        return False, "empty command", detail

    tokens = _tokenize(command.strip())
    if tokens is None:
        return False, "shell metacharacters are not permitted in the adapter channel", detail
    if not tokens:
        return False, "empty command", detail

    # Token 0 must be the adapter itself, compared by resolved path so that a
    # relative path, a symlink or an alias cannot smuggle a different binary.
    try:
        invoked = os.path.realpath(tokens[0])
        sanctioned = os.path.realpath(adapter)
    except OSError:
        return False, "could not resolve invoked path", detail
    detail["invoked_path"] = invoked
    if invoked != sanctioned:
        return False, "only the sanctioned adapter may be invoked", detail

    rest = tokens[1:]
    if not rest:
        return False, "missing verb", detail
    verb, args = rest[0], rest[1:]
    detail["verb"] = verb
    if not VERB_RE.match(verb):
        return False, f"verb {verb!r} is not in the allowlist (ls, log, read)", detail

    if verb in ("ls", "log"):
        if args:
            return False, f"verb {verb!r} takes no argument", detail
        return True, "sanctioned adapter call", detail

    # verb == "read"
    if len(args) != 1:
        return False, "verb 'read' takes exactly one argument", detail
    detail["arg"] = args[0]
    if not ARG_RE.match(args[0]):
        return False, "argument failed the allowlist pattern", detail
    if args[0] in (".", ".."):
        return False, "argument is not a file", detail
    return True, "sanctioned adapter call", detail


def main() -> int:
    request_id = uuid.uuid4().hex[:12]
    run_id = os.environ.get("GATE2_RUN_ID", "unset")
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    tool_name = payload.get("tool_name", "<unknown>")
    tool_input = payload.get("tool_input", {}) or {}

    try:
        allow, reason, detail = evaluate(tool_name, tool_input)
    except Exception as exc:  # fail-closed on any guard defect
        allow, reason, detail = False, f"guard error: {exc}", {"tool": tool_name}

    cmd = detail.get("command", "")
    _emit(
        {
            "ts": _now(),
            "run_id": run_id,
            "request_id": request_id,
            "event": "pre_tool_use",
            "tool": tool_name,
            "command": cmd,
            "command_sha256": hashlib.sha256(cmd.encode("utf-8")).hexdigest() if cmd else None,
            "verb": detail.get("verb"),
            "arg": detail.get("arg"),
            "decision": "allow" if allow else "deny",
            "reason": reason,
            "session_id": payload.get("session_id"),
        }
    )

    print(json.dumps(_decide(allow, reason)))
    # Exit 0: the JSON decision carries the verdict. Exit 2 is the fallback for
    # harnesses that key off the exit code instead.
    return 0 if allow else 2


if __name__ == "__main__":
    sys.exit(main())
