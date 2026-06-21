#!/usr/bin/env python3
"""
Deterministic Hermes-like mock backend runner for adapter smoke testing.

This is not a model integration and not a verified external Hermes runtime.
It simulates a function-calling runtime by accepting Hermes-style model output,
executing one safe allowlisted stub tool, writing a response_file, and routing
the pre_task/post_task events through the existing Hermes adapter.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime_hooks.adapters.hermes.normalize_event import normalize_event
from runtime_hooks.adapters.shared_adapter_runner import run_adapter_event

TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
STUB_TOOL_NAME = "write_governed_response"


def make_stub_tool_call(task: str) -> str:
    """Return a deterministic Hermes-style tool_call proposal."""
    payload = {
        "name": STUB_TOOL_NAME,
        "arguments": {
            "summary": f"Stub runner completed accepted-input smoke for: {task}",
        },
    }
    return "<tool_call>\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n</tool_call>"


def parse_tool_call(text: str) -> dict[str, Any]:
    """Parse the single stub tool_call JSON object."""
    match = TOOL_CALL_RE.search(text)
    if not match:
        raise ValueError("missing <tool_call> block")
    parsed = json.loads(match.group(1))
    if parsed.get("name") != STUB_TOOL_NAME:
        raise ValueError(f"unsupported stub tool: {parsed.get('name')}")
    arguments = parsed.get("arguments")
    if not isinstance(arguments, dict):
        raise ValueError("tool_call arguments must be an object")
    return parsed


def execute_stub_tool(tool_call: dict[str, Any], response_file: Path, *, task: str) -> dict[str, Any]:
    """Execute the only allowed stub tool and write the response artifact."""
    response_file.parent.mkdir(parents=True, exist_ok=True)
    summary = str(tool_call["arguments"].get("summary") or "Stub runner completed accepted-input smoke.")
    response_file.write_text(
        "\n".join(
            [
                "[Governance Contract]",
                "LANG = Python",
                "LEVEL = L1",
                "SCOPE = tooling",
                "PLAN = Hermes stub runner accepted-input smoke",
                "LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT, runtime_hooks/adapters/hermes/HERMES_RUNTIME_INTERFACE.md",
                "CONTEXT = runtime_hooks/examples/hermes -> deterministic stub; NOT: verified external Hermes runtime",
                "PRESSURE = SAFE (10/200)",
                "RULES = common,python",
                "RISK = medium",
                "OVERSIGHT = review-required",
                "MEMORY_MODE = candidate",
                "",
                "[Stub Runner Result]",
                f"task = {task}",
                f"summary = {summary}",
                "claim = response_file produced by deterministic stub, not by a model",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "tool_name": tool_call["name"],
        "response_file": str(response_file),
        "executed": True,
        "summary": summary,
    }


def _blocked_result(
    *,
    reason: str,
    response_file: Path,
    pre_envelope: dict[str, Any],
    model_output: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "blocked": reason,
        "claim_class": "accepted-input-mock-backend-smoke",
        "not_claimed": _not_claimed(),
        "model_output": model_output,
        "tool_call": None,
        "tool_result": {
            "tool_name": None,
            "response_file": str(response_file),
            "executed": False,
        },
        "pre_task": pre_envelope,
        "post_task": None,
    }


def _not_claimed() -> list[str]:
    return [
        "verified external Hermes runtime integration",
        "model-generated tool-call reliability",
        "non-bypassable governance enforcement",
    ]


def build_pre_task_payload(*, project_root: Path, task: str, run_id: str) -> dict[str, Any]:
    return {
        "_note": "Hermes stub runner accepted-input event; not a verified external Hermes payload.",
        "workspace": str(project_root),
        "request": task,
        "rule_packs": ["common", "python"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "event_name": "pre_task",
        "run_id": run_id,
    }


def build_post_task_payload(
    *,
    project_root: Path,
    task: str,
    response_file: Path,
    run_id: str,
) -> dict[str, Any]:
    return {
        "_note": "Hermes stub runner accepted-input event; not a verified external Hermes payload.",
        "workspace": str(project_root),
        "task": task,
        "rules": ["common", "python"],
        "risk": "medium",
        "oversight": "review-required",
        "memory_mode": "candidate",
        "output_file": str(response_file),
        "emit_snapshot": False,
        "summary": "Hermes stub runner produced response_file",
        "event_name": "post_task",
        "run_id": run_id,
    }


def run_stub_task(
    *,
    project_root: Path,
    output_dir: Path,
    task: str = "Run Hermes accepted-input stub smoke",
    run_id: str = "hermes-stub-run-01",
    model_output: str | None = None,
) -> dict[str, Any]:
    """Run deterministic pre_task -> model-output parse -> tool -> post_task smoke."""
    project_root = project_root.resolve()
    output_dir = output_dir.resolve()
    response_file = output_dir / "hermes_stub_response.txt"

    pre_payload = build_pre_task_payload(project_root=project_root, task=task, run_id=run_id)
    pre_envelope = run_adapter_event(normalize_event, event_type="pre_task", payload=pre_payload)

    model_text = model_output if model_output is not None else make_stub_tool_call(task)
    try:
        tool_call = parse_tool_call(model_text)
    except (json.JSONDecodeError, ValueError) as exc:
        return _blocked_result(
            reason=f"tool_call_parse_or_allowlist_error: {exc}",
            response_file=response_file,
            pre_envelope=pre_envelope,
            model_output=model_text,
        )
    tool_result = execute_stub_tool(tool_call, response_file, task=task)

    post_payload = build_post_task_payload(
        project_root=project_root,
        task=task,
        response_file=response_file,
        run_id=run_id,
    )
    post_envelope = run_adapter_event(normalize_event, event_type="post_task", payload=post_payload)

    return {
        "ok": pre_envelope["result"]["ok"] and post_envelope["result"]["ok"],
        "blocked": None,
        "claim_class": "accepted-input-mock-backend-smoke",
        "not_claimed": _not_claimed(),
        "model_output": model_text,
        "tool_call": tool_call,
        "tool_result": tool_result,
        "pre_task": pre_envelope,
        "post_task": post_envelope,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic Hermes accepted-input stub smoke.")
    parser.add_argument("--project-root", default=".", help="Project root for governance checks.")
    parser.add_argument("--output-dir", default="artifacts/runtime/hermes-stub", help="Directory for response_file.")
    parser.add_argument("--task", default="Run Hermes accepted-input stub smoke")
    parser.add_argument("--model-output-file", help="Hermes-style model output text; defaults to deterministic output.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    model_output = Path(args.model_output_file).read_text(encoding="utf-8") if args.model_output_file else None
    result = run_stub_task(
        project_root=Path(args.project_root),
        output_dir=Path(args.output_dir),
        task=args.task,
        model_output=model_output,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("harness=hermes")
        print("runner=mock-backend-stub")
        print(f"ok={result['ok']}")
        print(f"blocked={result['blocked']}")
        print(f"pre_task_ok={result['pre_task']['result']['ok']}")
        print(f"post_task_ok={result['post_task']['result']['ok'] if result['post_task'] else False}")
        print(f"response_file={result['tool_result']['response_file']}")
        print(f"claim_class={result['claim_class']}")
        for item in result["not_claimed"]:
            print(f"not_claimed: {item}")

    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
