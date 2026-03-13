#!/usr/bin/env python3
"""
Run documented runtime smoke flows end-to-end.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime_hooks.adapters.claude_code.normalize_event import normalize_event as normalize_claude
from runtime_hooks.adapters.codex.normalize_event import normalize_event as normalize_codex
from runtime_hooks.adapters.gemini.normalize_event import normalize_event as normalize_gemini
from runtime_hooks.adapters.shared_adapter_runner import run_adapter_event
from runtime_hooks.dispatcher import dispatch_event


NORMALIZERS = {
    "claude_code": normalize_claude,
    "codex": normalize_codex,
    "gemini": normalize_gemini,
}


DEFAULT_EXAMPLES = {
    ("claude_code", "pre_task"): Path("runtime_hooks/examples/claude_code/pre_task.native.json"),
    ("claude_code", "post_task"): Path("runtime_hooks/examples/claude_code/post_task.native.json"),
    ("codex", "pre_task"): Path("runtime_hooks/examples/codex/pre_task.native.json"),
    ("codex", "post_task"): Path("runtime_hooks/examples/codex/post_task.native.json"),
    ("gemini", "pre_task"): Path("runtime_hooks/examples/gemini/pre_task.native.json"),
    ("gemini", "post_task"): Path("runtime_hooks/examples/gemini/post_task.native.json"),
}

DEFAULT_SHARED_EXAMPLES = {
    "session_start": Path("runtime_hooks/examples/shared/session_start.shared.json"),
}


def run_smoke(harness: str, event_type: str, payload_file: Path | None = None) -> dict:
    normalize_event = NORMALIZERS[harness]
    payload_path = payload_file or DEFAULT_EXAMPLES[(harness, event_type)]
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    envelope = run_adapter_event(normalize_event, event_type=event_type, payload=payload)
    envelope["payload_file"] = str(payload_path)
    return envelope


def run_shared_smoke(event_type: str, payload_file: Path | None = None) -> dict:
    payload_path = payload_file or DEFAULT_SHARED_EXAMPLES[event_type]
    event = json.loads(payload_path.read_text(encoding="utf-8"))
    envelope = dispatch_event(event)
    envelope["payload_file"] = str(payload_path)
    return envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a runtime smoke flow from native payload to governance result.")
    parser.add_argument("--harness", choices=sorted(NORMALIZERS))
    parser.add_argument("--event-type", choices=["session_start", "pre_task", "post_task"], required=True)
    parser.add_argument("--file", "-f", help="Native payload file. Defaults to the documented example.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    if args.event_type == "session_start":
        envelope = run_shared_smoke(
            event_type=args.event_type,
            payload_file=Path(args.file) if args.file else None,
        )
    else:
        if not args.harness:
            raise SystemExit("--harness is required for pre_task and post_task smoke flows")
        envelope = run_smoke(
            harness=args.harness,
            event_type=args.event_type,
            payload_file=Path(args.file) if args.file else None,
        )

    if args.format == "json":
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        if args.harness:
            print(f"harness={args.harness}")
        print(f"event_type={args.event_type}")
        print(f"payload_file={envelope['payload_file']}")
        print(f"ok={envelope['result']['ok']}")
        if envelope["result"].get("snapshot"):
            print(f"snapshot={envelope['result']['snapshot']['snapshot_path']}")
        for warning in envelope["result"].get("warnings", []):
            print(f"warning: {warning}")
        for error in envelope["result"].get("errors", []):
            print(f"error: {error}")

    sys.exit(0 if envelope["result"]["ok"] else 1)


if __name__ == "__main__":
    main()
