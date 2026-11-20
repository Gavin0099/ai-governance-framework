"""Gemini CLI snapshot publisher; never runs closeout or claims native execution.

Captures a Gemini CLI session transcript into the owned snapshot area and
publishes a version 1.3 closeout request under R2 execution exclusion. The
heavy closeout pipeline still runs only through explicit consumption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance_tools import closeout_handoff as h
from governance_tools import native_closeout_publisher as n

# Schema/format identifier for the snapshot validator, not the Gemini CLI binary's
# release version; keeps manifest verification deterministic without running gemini.
FORMAT_VERSION = "gemini-cli-session-jsonl-sessionid-projecthash"
GEMINI = n.Profile(event_provider="gemini",
                   source_kind=h.GEMINI_SOURCE_KIND,
                   platform_key="gemini_version",
                   format_version=FORMAT_VERSION,
                   provider_class=h.GeminiTranscriptProvider,
                   snapshot_validator=h._validate_gemini_snapshot,
                   cwd_matches_root=h._same_worktree_root)


def publish(consumer_root, payload, *, deadline_ms=None, budget=None):
    return n.publish(consumer_root, payload, deadline_ms=deadline_ms,
                     budget=budget, profile=GEMINI)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--deadline-ms", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        budget = n.Budget(args.deadline_ms)
        raw = sys.stdin.buffer.read(n.MAX_PAYLOAD_BYTES + 1)
        h._require(len(raw) <= n.MAX_PAYLOAD_BYTES, "PAYLOAD_TOO_LARGE")

        def pairs(items):
            obj = {}
            for key, value in items:
                h._require(key not in obj, "DUPLICATE_PAYLOAD_KEY")
                obj[key] = value
            return obj

        payload = json.loads(raw, object_pairs_hook=pairs)
        result = publish(args.consumer_root, payload, budget=budget)
        budget.check()
        print(json.dumps(result))
        return 0
    except (ValueError, TypeError, KeyError, OSError, TimeoutError, RuntimeError) as exc:
        print(json.dumps({"status": "UNCONFIRMED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
