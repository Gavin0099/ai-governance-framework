#!/usr/bin/env python3
"""
Dispatch shared runtime events to the correct governance core check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime_hooks.core.post_task_check import run_post_task_check
from runtime_hooks.core.pre_task_check import run_pre_task_check


def dispatch_event(event: dict) -> dict:
    event_type = event["event_type"]

    if event_type == "pre_task":
        result = run_pre_task_check(
            project_root=Path(event["project_root"]),
            rules=",".join(event.get("rules", [])),
            risk=event["risk"],
            oversight=event["oversight"],
            memory_mode=event["memory_mode"],
        )
    elif event_type == "post_task":
        response_text = ""
        response_file = event.get("response_file")
        if response_file:
            response_text = Path(response_file).read_text(encoding="utf-8")

        result = run_post_task_check(
            response_text=response_text,
            risk=event["risk"],
            oversight=event["oversight"],
            memory_mode=event["memory_mode"],
            memory_root=Path(event["project_root"]) / "memory" if event.get("create_snapshot") else None,
            snapshot_task=event.get("task"),
            snapshot_summary=event.get("snapshot_summary"),
            create_snapshot=event.get("create_snapshot", False),
        )
    else:
        raise ValueError(f"Unsupported event_type: {event_type}")

    return {
        "event_type": event_type,
        "result": result,
    }


def _load_event(file_path: str | None) -> dict:
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch a shared runtime event to governance core checks.")
    parser.add_argument("--file", "-f", help="Shared event JSON file; defaults to stdin")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    event = _load_event(args.file)
    envelope = dispatch_event(event)

    if args.format == "json":
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    else:
        print(f"event_type={envelope['event_type']}")
        print(f"ok={envelope['result']['ok']}")
        for warning in envelope["result"].get("warnings", []):
            print(f"warning: {warning}")
        for error in envelope["result"].get("errors", []):
            print(f"error: {error}")

    sys.exit(0 if envelope["result"]["ok"] else 1)


if __name__ == "__main__":
    main()
