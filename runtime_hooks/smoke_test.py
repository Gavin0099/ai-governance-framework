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
    ("claude_code", "session_start"): Path("runtime_hooks/examples/claude_code/session_start.native.json"),
    ("claude_code", "pre_task"): Path("runtime_hooks/examples/claude_code/pre_task.native.json"),
    ("claude_code", "post_task"): Path("runtime_hooks/examples/claude_code/post_task.native.json"),
    ("codex", "session_start"): Path("runtime_hooks/examples/codex/session_start.native.json"),
    ("codex", "pre_task"): Path("runtime_hooks/examples/codex/pre_task.native.json"),
    ("codex", "post_task"): Path("runtime_hooks/examples/codex/post_task.native.json"),
    ("gemini", "session_start"): Path("runtime_hooks/examples/gemini/session_start.native.json"),
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


def format_human_envelope(envelope: dict, harness: str | None = None) -> str:
    lines: list[str] = []
    result = envelope["result"]
    if harness:
        lines.append(f"harness={harness}")
    lines.append(f"event_type={envelope['event_type']}")
    lines.append(f"payload_file={envelope['payload_file']}")
    lines.append(f"ok={result['ok']}")

    if envelope["event_type"] == "session_start":
        rules = result.get("runtime_contract", {}).get("rules", []) or []
        if rules:
            lines.append(f"rules={','.join(rules)}")
        preview = result.get("suggested_rules_preview") or []
        if preview:
            lines.append(f"suggested_rules_preview={','.join(preview)}")
        skills = result.get("suggested_skills") or []
        if skills:
            lines.append(f"suggested_skills={','.join(skills)}")
        agent = result.get("suggested_agent")
        if agent:
            lines.append(f"suggested_agent={agent}")
        guidance = result.get("proposal_guidance") or {}
        validators = guidance.get("expected_validators") or []
        if validators:
            lines.append(f"expected_validators={','.join(validators)}")
        evidence = guidance.get("required_evidence") or []
        if evidence:
            lines.append(f"required_evidence={','.join(evidence)}")
    else:
        if result.get("snapshot"):
            lines.append(f"snapshot={result['snapshot']['snapshot_path']}")

    for warning in result.get("warnings", []):
        lines.append(f"warning: {warning}")
    for error in result.get("errors", []):
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a runtime smoke flow from native payload to governance result.")
    parser.add_argument("--harness", choices=sorted(NORMALIZERS))
    parser.add_argument("--event-type", choices=["session_start", "pre_task", "post_task"], required=True)
    parser.add_argument("--file", "-f", help="Native payload file. Defaults to the documented example.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--output", help="Write rendered smoke output to a file.")
    args = parser.parse_args()

    if args.event_type == "session_start":
        envelope = run_shared_smoke(
            event_type=args.event_type,
            payload_file=Path(args.file) if args.file else None,
        )
    else:
        if not args.harness:
            raise SystemExit("--harness is required for harness-based smoke flows")
        envelope = run_smoke(
            harness=args.harness,
            event_type=args.event_type,
            payload_file=Path(args.file) if args.file else None,
        )

    if args.format == "json":
        rendered = json.dumps(envelope, ensure_ascii=False, indent=2)
    else:
        rendered = format_human_envelope(envelope, harness=args.harness)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

    sys.exit(0 if envelope["result"]["ok"] else 1)


if __name__ == "__main__":
    main()
