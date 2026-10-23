"""Claude SessionEnd snapshot publication. Tranche 1: admission only, no CLI.

Shares capture, stat stability and byte read-back with the native publisher on
purpose, so this path cannot drift to weaker evidence than the qualified Codex
path. Only the declared differences live here: the event provider, the snapshot
source kind, the platform key, the transcript record shape and the cwd rule.
Claude may run from a subdirectory, so its cwd must share the consumer's Git
worktree root, the rule its SessionStart binding applies; Codex keeps the exact
root rule.

Owned bytes carry no completeness or decision authority, and explicit
invocation is not evidence that a native hook fired.

Session envelopes are deliberately NOT written here. The canonical writer is
`runtime_hooks/core/_canonical_closeout.write_session_envelope`, and R1
ownership requires the root-bound schema 1.1 it issues
(`shared_closeout_ownership._identity`). Claude's own SessionStart
(`runtime_hooks/adapters/claude_code/session_lifecycle.py`) issues that envelope
with provider claude; an envelope another provider's SessionStart issued is
rejected (`ENVELOPE_PROVIDER_MISMATCH`).
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
                   snapshot_validator=h._validate_claude_snapshot,
                   cwd_matches_root=h._same_worktree_root)


def publish(consumer_root, payload, *, deadline_ms=None, budget=None):
    """Publish a Claude SessionEnd snapshot request. Does not close out.

    Requires a root-bound session envelope whose provider is claude.
    """
    return n.publish(consumer_root, payload, deadline_ms=deadline_ms, budget=budget,
                     profile=CLAUDE)
