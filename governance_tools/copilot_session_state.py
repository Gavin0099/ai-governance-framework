"""Copilot runtime session state: which client owns a session, and its transcript.

VS Code agent mode runs on the GitHub Copilot runtime, the same one the standalone
Copilot CLI uses, and VS Code also loads the Copilot CLI hook file. A SessionStart hook
therefore cannot tell from its own registration which client started the session. The
runtime records that itself, before any hook runs, in

    $COPILOT_HOME/session-state/<session id>/workspace.yaml   (client_name)
    $COPILOT_HOME/session-state/<session id>/events.jsonl     (the session transcript)

with COPILOT_HOME defaulting to ~/.copilot. Observed values (2026-11-11, VS Code 1.145.3,
Copilot runtime 1.0.103): client_name "vscode-agent-host" for VS Code agent mode and
"github/cli" for the standalone CLI.

Everything here fails closed. A missing, unreadable or inconsistent record, or an unknown
client, means no provider: the caller must not guess one, and identity is not established.
This module reads the runtime's own files only; it never writes them and never stores
conversation content.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

PROVIDER_BY_CLIENT = {
    "vscode-agent-host": "github-copilot-vscode",
    "github/cli": "github-copilot",
}
_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*?)[ \t]*$")
MAX_TRANSCRIPT_BYTES = 256 * 1024 * 1024


class CopilotSessionStateError(ValueError):
    """The runtime's session record cannot establish what the caller needs."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CopilotSessionStateError(message)


def copilot_home(environ=None) -> Path:
    environ = os.environ if environ is None else environ
    configured = environ.get("COPILOT_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".copilot"


def session_state_dir(session_id: str, *, home: Path | None = None) -> Path:
    _require(isinstance(session_id, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", session_id)),
             "COPILOT_SESSION_ID_INVALID")
    return (home or copilot_home()) / "session-state" / session_id


def read_workspace(session_id: str, *, home: Path | None = None) -> dict[str, str]:
    """The top-level scalar fields of the runtime's workspace.yaml for this session."""
    path = session_state_dir(session_id, home=home) / "workspace.yaml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CopilotSessionStateError("COPILOT_WORKSPACE_MISSING") from exc
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = _TOP_LEVEL.match(line)
        if match and match.group(1) not in fields:
            value = match.group(2)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            fields[match.group(1)] = value
    _require(fields.get("id") == session_id, "COPILOT_WORKSPACE_SESSION_MISMATCH")
    return fields


def provider_for_session(session_id: str, *, home: Path | None = None) -> str:
    """The provider the runtime's own record names for this session, or an error."""
    client = read_workspace(session_id, home=home).get("client_name", "")
    provider = PROVIDER_BY_CLIENT.get(client)
    _require(provider is not None, "COPILOT_CLIENT_UNKNOWN")
    return provider


def validate_transcript(transcript_path, session_id: str, consumer_root: Path, *,
                        expected_provider: str, home: Path | None = None) -> Path:
    """Fail closed unless this transcript is the runtime's record of this session in this consumer.

    Checks: the path is <session-state>/<session id>/events.jsonl; the same directory's
    workspace.yaml names this session and a client mapping to expected_provider; the first
    record is session.start for this session; every session id the transcript names is this
    one; and every working directory and git root it names is the consumer worktree or its
    registered framework submodule (the #296 rule, resolved through Git, so drive-letter
    case does not matter but another repository still does).
    """
    from governance_tools import closeout_handoff as handoff

    path = Path(transcript_path)
    _require(path.name == "events.jsonl" and path.parent.name == session_id, "COPILOT_TRANSCRIPT_PATH_MISMATCH")
    expected_dir = session_state_dir(session_id, home=home).resolve()
    _require(path.resolve().parent == expected_dir, "COPILOT_TRANSCRIPT_PATH_MISMATCH")
    _require(provider_for_session(session_id, home=home) == expected_provider, "COPILOT_PROVIDER_MISMATCH")
    _require(path.is_file() and path.stat().st_size <= MAX_TRANSCRIPT_BYTES, "COPILOT_TRANSCRIPT_MISSING")
    root = Path(consumer_root).resolve()
    framework_root = None
    framework_checked = False
    checked: dict[str, bool] = {}

    def in_consumer(value) -> bool:
        nonlocal framework_root, framework_checked
        if not isinstance(value, str) or not value.strip():
            return False
        if value not in checked:
            allowed = handoff._same_worktree_root(value, root)
            if not allowed:
                if not framework_checked:
                    framework_root = handoff._registered_framework_root(root)
                    framework_checked = True
                allowed = handoff._transcript_cwd_in_consumer(value, root, framework_root)
            checked[value] = allowed
        return checked[value]

    first = True
    with path.open("rb") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CopilotSessionStateError("COPILOT_TRANSCRIPT_MALFORMED") from exc
            _require(isinstance(record, dict), "COPILOT_TRANSCRIPT_MALFORMED")
            data = record.get("data")
            data = data if isinstance(data, dict) else {}
            if first:
                _require(record.get("type") == "session.start" and data.get("sessionId") == session_id,
                         "COPILOT_TRANSCRIPT_SESSION_MISMATCH")
                context = data.get("context")
                context = context if isinstance(context, dict) else {}
                _require(in_consumer(context.get("gitRoot") or context.get("cwd")),
                         "COPILOT_TRANSCRIPT_REPOSITORY_MISMATCH")
                first = False
            inner = data.get("input")
            inner = inner if isinstance(inner, dict) else {}
            for holder in (data, inner):
                if "sessionId" in holder:
                    _require(holder["sessionId"] == session_id, "COPILOT_TRANSCRIPT_SESSION_MISMATCH")
            for holder, keys in ((inner, ("cwd",)), (data, ("workingDirectory",)),
                                 (data.get("context") if isinstance(data.get("context"), dict) else {},
                                  ("cwd", "gitRoot"))):
                for key in keys:
                    if key in holder:
                        _require(in_consumer(holder[key]), "COPILOT_TRANSCRIPT_REPOSITORY_MISMATCH")
    _require(not first, "COPILOT_TRANSCRIPT_EMPTY")
    return path
