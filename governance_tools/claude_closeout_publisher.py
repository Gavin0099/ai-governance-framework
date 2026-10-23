"""Claude SessionEnd snapshot publication. Tranche 1: admission only, no CLI.

Shares capture, stat stability and byte read-back with the native publisher on
purpose, so this path cannot drift to weaker evidence than the qualified Codex
path. Only the declared differences live here: the event provider, the snapshot
source kind, the platform key and the transcript record shape.

Owned bytes carry no completeness or decision authority, and explicit
invocation is not evidence that a native hook fired.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import closeout_handoff as h
from governance_tools import native_closeout_publisher as n
from governance_tools import shared_closeout_ownership as r2

# Format qualification provenance for the observed record shape, not an
# assertion about which Claude build produced it.
FORMAT_VERSION = "claude-code-session-jsonl-sessionid-cwd"

CLAUDE = n.Profile(event_provider="claude", source_kind=h.CLAUDE_SOURCE_KIND,
                   platform_key="claude_version", format_version=FORMAT_VERSION,
                   provider_class=h.ClaudeTranscriptProvider,
                   snapshot_validator=h._validate_claude_snapshot)

ENVELOPE_SCHEMA_VERSION = "1.0"
DEFAULT_CLOSEOUT_PATH = "artifacts/session-closeout.txt"


def write_session_envelope(consumer_root, session_id, *, repo_head_before,
                           started_at=None, closeout_path=DEFAULT_CLOSEOUT_PATH):
    """Write the session envelope a Claude session needs before publication.

    Provider-neutral in placement and shape; it writes the same six-key
    envelope the existing adapters write. It lives here rather than in the
    Claude adapter because that adapter file belongs to the still-open #232;
    wiring this from the adapter is a later tranche. Calling it is not evidence
    that a SessionStart hook fired.
    """
    root = Path(consumer_root).resolve(strict=True)
    h._require(bool(r2._ID.fullmatch(session_id)), "INVALID_SESSION")
    h._string(repo_head_before)
    h._string(closeout_path)
    h._require(not Path(closeout_path).is_absolute(), "INVALID_CLOSEOUT_PATH")
    envelope = {"schema_version": ENVELOPE_SCHEMA_VERSION, "session_id": session_id,
                "started_at": started_at or datetime.now(timezone.utc).isoformat(),
                "provider": "claude", "repo_head_before": repo_head_before,
                "closeout_path": closeout_path}
    directory = r2._path(root, f"artifacts/runtime/sessions/{session_id}")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "session-envelope.json"
    # Never silently replace an existing envelope: a second shape for one
    # session id would make envelope_sha256 unverifiable after the fact.
    h._require(not path.exists(), "ENVELOPE_ALREADY_PRESENT")
    temporary = directory / "session-envelope.json.partial"
    with temporary.open("xb") as stream:
        stream.write(json.dumps(envelope, indent=2, sort_keys=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    h._sync_directory(directory)
    return envelope


def publish(consumer_root, payload, *, deadline_ms=None, budget=None):
    """Publish a Claude SessionEnd snapshot request. Does not close out."""
    return n.publish(consumer_root, payload, deadline_ms=deadline_ms, budget=budget,
                     profile=CLAUDE)
