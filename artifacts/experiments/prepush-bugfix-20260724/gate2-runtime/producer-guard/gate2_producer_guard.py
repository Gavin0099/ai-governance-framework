#!/usr/bin/env python3
"""Gate 2 producer guard — PreToolUse hook.

Three jobs, all required before Gate 2 resource admission:

1. TECHNICAL ADAPTER EXCLUSIVITY. The producer context may invoke exactly one
   thing: the managed adapter, with a verb and arguments admitted by the shared
   policy file. Every other tool call -- `docker exec`, reading host files, git,
   network, editors -- is DENIED by the harness before it executes.

2. ONE CONTRACT, NOT TWO. The verb/argument contract lives in a policy JSON
   (see gate2_policy.py) that the adapter loads too, so guard and adapter cannot
   drift apart. The policy id and digest are stamped into every transcript event
   so a reviewer can tell which contract was in force.

3. MODEL TRANSCRIPT CAPTURE THAT CANNOT SILENTLY GO MISSING. Every decision is
   appended to a JSONL transcript keyed by the harness-supplied `tool_use_id`,
   the same id the PostToolUse / PostToolUseFailure hooks receive, so request and
   result are joined by identity rather than guessed at by command digest. If the
   transcript cannot be written, the call is BLOCKED: an unauditable call is not
   allowed to run.

Wiring (producer context settings only -- NOT the design session's settings):

    "hooks": {
      "PreToolUse":         [{"hooks": [{"type": "command",
         "command": "python <this file>"}]}],
      "PostToolUse":        [{"hooks": [{"type": "command",
         "command": "python <sibling>/gate2_producer_posttool.py"}]}],
      "PostToolUseFailure": [{"hooks": [{"type": "command",
         "command": "python <sibling>/gate2_producer_posttool.py"}]}]
    }

Environment:
    GATE2_ADAPTER      absolute path to the sanctioned adapter script (required)
    GATE2_POLICY       absolute path to the shared policy JSON (required)
    GATE2_RUN_ID       run identifier (default: "unset")
    GATE2_TRANSCRIPT   transcript path (default: ./gate2-transcript.jsonl)

Output contract (matches the documented hook semantics: JSON on stdout is only
processed at exit 0, and exit 2 blocks with stderr as the reason -- so the two
are never mixed):

    allow                       -> allow JSON on stdout, exit 0
    decided deny                -> deny  JSON on stdout, exit 0
    undecidable / unauditable   -> reason on stderr,     exit 2  (blocks)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate2_policy import Policy, PolicyError, load_policy  # noqa: E402

# Everything that could chain, redirect, substitute, expand or continue a line.
# Backslash is deliberately NOT here: Windows adapter paths contain it, and with
# quotes, `$`, backticks and newlines already banned, a backslash can at most
# escape a space -- which merges tokens and then fails the policy's strict
# verb/argument patterns. (An earlier version banned it and thereby denied every
# legitimate call on Windows; the hostile suite caught that.)
_METACHARS = ";|&<>`$(){}[]!*?\n\r\"'"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def transcript_path() -> str:
    return os.environ.get("GATE2_TRANSCRIPT", "gate2-transcript.jsonl")


def emit(record: dict) -> None:
    """Append one transcript event. Raises OSError -- the caller must block."""
    with open(transcript_path(), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _preflight_transcript() -> None:
    """Prove the transcript is writable BEFORE admitting anything.

    The earlier version swallowed OSError, so pointing GATE2_TRANSCRIPT at an
    unwritable location produced allow decisions with no audit record at all.
    """
    with open(transcript_path(), "a", encoding="utf-8", newline="\n") as fh:
        fh.flush()


def _decide(allow: bool, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allow else "deny",
            "permissionDecisionReason": reason,
        }
    }


def offending_metachars(command: str) -> list[str]:
    """Which banned characters appear, in the order they appear."""
    seen, out = set(), []
    for ch in command:
        if ch in _METACHARS and ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out


def _tokenize(command: str) -> list[str] | None:
    """Split a Bash command the adapter way: no shell metacharacters allowed.

    Rejected outright rather than parsed -- the guard must not try to out-clever
    a shell.
    """
    if offending_metachars(command):
        return None
    return command.split()


def guidance(policy: Policy, adapter: str) -> str:
    """What the producer is allowed to do, in the refusal itself.

    A refusal that names no permitted route is not merely unhelpful: two live
    sessions read a series of bare denials as a hostile or broken environment
    and declined to proceed at all -- correct behaviour on their part, and a
    deadlock on ours. Saying what IS permitted costs nothing, reveals nothing
    about the transcript, and is what an operator would tell a human.
    """
    verbs = ", ".join(sorted(policy.verbs))
    return (f"This session can invoke exactly one program: {adapter} . "
            f"Write it as a bare command -- the path unquoted, followed by a verb and its "
            f"arguments, with no quotes, redirection, pipes, substitution or chaining. "
            f"Verbs: {verbs}. Nothing else is reachable from here, and that is by design "
            f"rather than a fault.")


def evaluate(policy: Policy, adapter: str, tool_name: str, tool_input: dict) -> tuple[bool, str, dict]:
    """Return (allow, reason, detail). Pure: no side effects, so it is testable."""
    detail: dict = {"tool": tool_name}

    if not adapter:
        return False, "GATE2_ADAPTER is not configured; guard fails closed", detail

    # The producer context is given Bash solely to reach the adapter. Every
    # other tool is outside the sanctioned channel.
    if tool_name != "Bash":
        return False, f"tool {tool_name!r} is outside the adapter channel", detail

    command = (tool_input or {}).get("command", "")
    if not isinstance(command, str) or not command.strip():
        return False, "empty command", detail
    detail["command"] = command

    tokens = _tokenize(command.strip())
    if tokens is None:
        bad = " ".join(repr(c) for c in offending_metachars(command.strip()))
        # Naming the characters matters: a quoted Windows path is the commonest
        # way to trip this, and "shell metacharacters are not permitted" gives a
        # producer no way to see that the quotes were the problem.
        return False, f"shell metacharacters are not permitted in the adapter channel: {bad}", detail
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
    # realpath() happily resolves a path that does not exist, so two equally
    # bogus paths would compare equal without this.
    if not os.path.isfile(sanctioned):
        return False, "the sanctioned adapter path does not exist", detail
    if invoked != sanctioned:
        return False, "only the sanctioned adapter may be invoked", detail

    rest = tokens[1:]
    if not rest:
        return False, "missing verb", detail
    verb, args = rest[0], rest[1:]
    detail["verb"] = verb
    detail["args"] = args
    ok, reason = policy.check(verb, args)
    return ok, reason, detail


def _block(reason: str, payload: dict | None = None) -> int:
    """Undecidable or unauditable: block via exit 2 with the reason on stderr.

    No JSON is printed here on purpose -- JSON output is only processed at exit
    0, so emitting both would be a contradiction rather than belt-and-braces.

    A block is also RECORDED where that is possible at all. A live session was
    lost to exactly this hole: every call was refused and no artifact existed
    afterwards, which is byte-for-byte indistinguishable from a session where
    the hooks never loaded. "The guard blocked everything" and "there was no
    guard" must not look the same to a reviewer.

    Best-effort by construction: if the transcript cannot be written -- which is
    itself one of the reasons for blocking -- the call is still blocked, and the
    stderr line remains the record of last resort.
    """
    print(f"gate2 producer guard BLOCKED the call: {reason}", file=sys.stderr)
    try:
        emit({
            "ts": _now(),
            "run_id": os.environ.get("GATE2_RUN_ID", "unset"),
            "tool_use_id": (payload or {}).get("tool_use_id"),
            "event": "guard_blocked",
            "tool": (payload or {}).get("tool_name", "<unknown>"),
            "decision": "block",
            "reason": reason,
            "reason_shown": reason,
            "session_id": (payload or {}).get("session_id"),
        })
    except OSError:
        pass
    return 2


def main() -> int:
    request_id = uuid.uuid4().hex[:12]
    run_id = os.environ.get("GATE2_RUN_ID", "unset")

    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
    except Exception as exc:
        return _block(f"unreadable hook payload ({exc})")

    tool_name = payload.get("tool_name", "<unknown>")
    tool_input = payload.get("tool_input", {}) or {}
    tool_use_id = payload.get("tool_use_id")

    # Correlation is not optional. Without the harness id, request and result
    # cannot be joined, and an uncorrelatable call is not auditable evidence.
    if not isinstance(tool_use_id, str) or not tool_use_id:
        return _block("hook payload carries no tool_use_id; the call cannot be correlated", payload)

    policy_path = os.environ.get("GATE2_POLICY", "")
    if not policy_path:
        return _block("GATE2_POLICY is not configured", payload)
    try:
        policy = load_policy(policy_path)
    except PolicyError as exc:
        return _block(str(exc), payload)

    try:
        _preflight_transcript()
    except OSError as exc:
        return _block(f"transcript {transcript_path()!r} is not writable ({exc})")

    try:
        allow, reason, detail = evaluate(policy, os.environ.get("GATE2_ADAPTER", ""), tool_name, tool_input)
    except Exception as exc:  # a guard defect must never open the channel
        return _block(f"guard error: {exc}", payload)

    # What the producer is actually told. A denial carries the route it may
    # legitimately take; an allow does not need one. Recorded verbatim, because
    # the producer's next move is only interpretable against what it was shown.
    shown = reason if allow else f"{reason}. {guidance(policy, os.environ.get('GATE2_ADAPTER', ''))}"

    cmd = detail.get("command", "")
    args = detail.get("args") or []
    record = {
        "ts": _now(),
        "run_id": run_id,
        "tool_use_id": tool_use_id,
        "request_id": request_id,
        "event": "pre_tool_use",
        "tool": tool_name,
        # The command is kept for a reviewer to read, but truncated: a `write`
        # carries a whole file as base64 and the transcript is an audit record,
        # not a second copy of the workspace. The digest below covers the full
        # text either way.
        "command": cmd if len(cmd) <= 512 else cmd[:512] + f"...<truncated, {len(cmd)} chars total>",
        "command_sha256": _sha(cmd) if cmd else None,
        "verb": detail.get("verb"),
        # Paths in full; a large payload argument (a base64 file body) is
        # reduced to a digest so the transcript stays an audit record rather
        # than a second copy of the workspace. args_sha256 covers the arguments
        # exactly as given and is what joins this event to the adapter log.
        "args_summary": [a if len(a) <= 96 else f"<b64 len={len(a)} sha256={_sha(a)[:16]}>" for a in args],
        "args_sha256": _sha("\x00".join(args)),
        "arg_count": len(args),
        "decision": "allow" if allow else "deny",
        "reason": reason,
        "reason_shown": shown,
        "policy_id": policy.policy_id,
        "policy_sha256": policy.sha256,
        "session_id": payload.get("session_id"),
        "prompt_id": payload.get("prompt_id"),
    }
    try:
        emit(record)
    except OSError as exc:
        return _block(f"could not append to the transcript ({exc})", payload)

    print(json.dumps(_decide(allow, shown)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
