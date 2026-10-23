"""Claude SessionEnd snapshot publication. Tranche 1: admission only, no CLI.

Shares capture, stat stability and byte read-back with the native publisher on
purpose, so this path cannot drift to weaker evidence than the qualified Codex
path. Only the declared differences live here: the event provider, the snapshot
source kind, the platform key and the transcript record shape.

Owned bytes carry no completeness or decision authority, and explicit
invocation is not evidence that a native hook fired.

Session envelopes are deliberately NOT written here. The canonical writer is
`runtime_hooks/core/_canonical_closeout.write_session_envelope`, and R1
ownership requires the root-bound schema 1.1 it issues
(`shared_closeout_ownership._identity`). That writer's root-bound provider
allow-list currently admits only codex and github-copilot-vscode, so no
qualified Claude envelope can exist yet. An earlier revision of this module
duplicated the writer and emitted a legacy 1.0 envelope, which R1 rejects with
`INVALID_OWNER: qualified R1 binding required`; the duplicate is removed rather
than fixed, because admitting claude to that allow-list is a SessionStart
identity decision and its file belongs to the still-open #232.
"""
from __future__ import annotations

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import closeout_handoff as h
from governance_tools import native_closeout_publisher as n

# Format qualification provenance for the observed record shape, not an
# assertion about which Claude build produced it.
FORMAT_VERSION = "claude-code-session-jsonl-sessionid-cwd"

CLAUDE = n.Profile(event_provider="claude", source_kind=h.CLAUDE_SOURCE_KIND,
                   platform_key="claude_version", format_version=FORMAT_VERSION,
                   provider_class=h.ClaudeTranscriptProvider,
                   snapshot_validator=h._validate_claude_snapshot)


def publish(consumer_root, payload, *, deadline_ms=None, budget=None):
    """Publish a Claude SessionEnd snapshot request. Does not close out.

    Requires a session envelope whose provider is claude; see the module
    docstring for why one cannot be produced yet.
    """
    return n.publish(consumer_root, payload, deadline_ms=deadline_ms, budget=budget,
                     profile=CLAUDE)
