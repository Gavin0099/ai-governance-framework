#!/usr/bin/env python3
"""A stand-in for the Claude Code hook dispatcher, for the admission canary.

WHAT THIS IS. It performs, per tool call, exactly the sequence the documented
hook contract specifies:

    1. build a PreToolUse payload with a fresh `tool_use_id`
    2. run the PreToolUse hook; honour its decision
         exit 0 + permissionDecision  -> allow / deny
         exit 2                       -> blocked, with stderr as the reason
    3. if and only if allowed, execute the Bash command
    4. run the PostToolUse hook with `tool_response`, or the PostToolUseFailure
       hook with `error`, under the SAME tool_use_id

WHAT THIS IS NOT. It is not Claude Code, and no model is in the loop. It proves
what the guard, adapter, container and transcript do when driven by the
documented contract; it does not prove that a real producer session drives them
that way. Two things stay unproven until a real harness run:

    - that Claude Code's own dispatcher supplies `tool_use_id` on all three
      events and honours exit-0 deny JSON (taken here from the published hooks
      reference, not observed);
    - the exact structure of `tool_response` for Bash. RESPONSE_SHAPE below is
      an assumption, which is why the post hook tolerates a plain string too.

Both are stated in the run report rather than papered over.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "..", "producer-guard", "gate2_producer_guard.py")
POST = os.path.join(HERE, "..", "producer-guard", "gate2_producer_posttool.py")


def _resolve_bash() -> str:
    """Find git-bash, not WSL's bash.

    On Windows `shutil.which("bash")` returns C:\\Windows\\System32\\bash.exe --
    the WSL launcher -- which cannot see the Windows filesystem the same way and
    fails with a bare exit 1. That produced a first canary run in which every
    call was allowed, nothing executed, and the driver still reported success.
    Hence: resolve explicitly, and refuse to guess.
    """
    for cand in (
        os.environ.get("GATE2_BASH"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if cand and os.path.isfile(cand):
            return cand
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    raise SystemExit("cannot find a usable bash (set GATE2_BASH); WSL's bash is not usable here")


BASH = _resolve_bash()

# Assumed Bash tool_response shape; see the module docstring.
RESPONSE_SHAPE = ("stdout", "stderr", "interrupted", "isImage")


def new_tool_use_id() -> str:
    return "toolu_" + uuid.uuid4().hex[:24]


def _common(session_id: str, prompt_id: str, event: str, tool_name: str, tool_input: dict, tool_use_id: str) -> dict:
    return {
        "session_id": session_id,
        "prompt_id": prompt_id,
        "transcript_path": "<emulated>",
        "cwd": HERE,
        "permission_mode": "default",
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_use_id": tool_use_id,
    }


def _hook(script: str, payload: dict, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, script],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=120,
    )


def run_step(
    tool_name: str,
    tool_input: dict,
    env: dict,
    session_id: str = "canary-session",
    prompt_id: str = "canary-prompt",
    deliver_failure_as: str = "PostToolUseFailure",
    tool_use_id: str | None = None,
    omit_tool_use_id: bool = False,
) -> dict:
    """Drive one tool call end to end. Returns a record of what happened."""
    tool_use_id = tool_use_id or new_tool_use_id()
    pre = _common(session_id, prompt_id, "PreToolUse", tool_name, tool_input, tool_use_id)
    if omit_tool_use_id:
        pre.pop("tool_use_id")

    cp = _hook(GUARD, pre, env)
    outcome: dict = {
        "tool_use_id": None if omit_tool_use_id else tool_use_id,
        "tool_name": tool_name,
        "command": tool_input.get("command"),
        "guard_exit": cp.returncode,
        "guard_stdout": cp.stdout.strip(),
        "guard_stderr": cp.stderr.strip(),
        "executed": False,
    }

    if cp.returncode == 0:
        try:
            decision = json.loads(cp.stdout)["hookSpecificOutput"]["permissionDecision"]
        except Exception as exc:
            outcome["result"] = f"malformed decision ({exc})"
            return outcome
        outcome["decision"] = decision
        if decision != "allow":
            outcome["result"] = "denied by decision JSON"
            return outcome
    elif cp.returncode == 2:
        outcome["decision"] = "blocked"
        outcome["result"] = "blocked by exit 2"
        return outcome
    else:
        outcome["decision"] = "error"
        outcome["result"] = f"guard exited {cp.returncode} (non-blocking per the hook contract)"
        return outcome

    # Allowed: run it the way the Bash tool would.
    run = subprocess.run(
        [BASH, "-c", tool_input["command"]],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    outcome.update(executed=True, exit_code=run.returncode)

    if run.returncode != 0 and deliver_failure_as == "PostToolUseFailure":
        post = _common(session_id, prompt_id, "PostToolUseFailure", tool_name, tool_input, tool_use_id)
        post["error"] = (run.stdout or "") + (run.stderr or "")
        outcome["post_event"] = "PostToolUseFailure"
    else:
        post = _common(session_id, prompt_id, "PostToolUse", tool_name, tool_input, tool_use_id)
        post["tool_response"] = {
            "stdout": run.stdout,
            "stderr": run.stderr,
            "interrupted": False,
            "isImage": False,
        }
        outcome["post_event"] = "PostToolUse"

    cp2 = _hook(POST, post, env)
    outcome["post_exit"] = cp2.returncode
    outcome["post_stderr"] = cp2.stderr.strip()
    outcome["result"] = "executed"
    outcome["stdout_tail"] = (run.stdout or "").strip().splitlines()[-3:]
    # Full text for the driver's own assertions; the caller drops it before
    # writing the report, so the evidence stays digests-and-tails.
    outcome["_stdout"] = run.stdout or ""
    return outcome
