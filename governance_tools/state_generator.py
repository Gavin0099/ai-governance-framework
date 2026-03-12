#!/usr/bin/env python3
"""
Generate .governance-state.yaml from PLAN.md plus runtime inputs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.plan_freshness import check_freshness
from governance_tools.rule_pack_loader import describe_rule_selection, parse_rule_list


def _yaml_str(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if (
        not text
        or any(
            c in text
            for c in (":", "#", "[", "]", "{", "}", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`", "\n", "\r")
        )
    ):
        return json.dumps(text, ensure_ascii=False)
    return text


def dict_to_yaml(data: dict, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dict_to_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(dict_to_yaml(item, indent + 2))
                else:
                    lines.append(f"{prefix}  - {_yaml_str(item)}")
        else:
            lines.append(f"{prefix}{key}: {_yaml_str(value)}")
    return "\n".join(lines)


def parse_header(text: str) -> dict:
    header = {}
    for match in re.finditer(r">\s*\*\*([^*]+)\*\*\s*:\s*(.+)", text):
        header[match.group(1).strip()] = match.group(2).strip()
    return header


def parse_current_phase(text: str) -> dict:
    for match in re.finditer(r"\[([xX>~ ])\]\s*(Phase\s+\w+)\s*:\s*(.+)", text):
        if match.group(1) in {">", "~"}:
            return {
                "id": match.group(2).replace(" ", ""),
                "name": match.group(3).strip(),
            }
    return {"id": None, "name": None}


def parse_gate_status(text: str) -> dict:
    statuses = {}
    for match in re.finditer(r"\[([xX>~ ])\]\s*(Phase\s+\w+)", text):
        marker = match.group(1)
        phase = match.group(2).replace(" ", "")
        if marker in {"x", "X"}:
            statuses[phase] = "passed"
        elif marker in {">", "~"}:
            statuses[phase] = "in_progress"
        else:
            statuses[phase] = "pending"
    return statuses


def parse_sprint_tasks(text: str) -> list[dict]:
    match = re.search(r"##\s*Current Sprint(.*?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    tasks = []
    for item in re.finditer(r"-\s*\[([ xX])\]\s*(.+)", match.group(1)):
        tasks.append({"name": item.group(2).strip(), "done": item.group(1).lower() == "x"})
    return tasks


def parse_backlog_counts(text: str) -> dict:
    counts = {"P0": 0, "P1": 0, "P2": 0}
    match = re.search(r"##\s*Backlog(.*?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return counts

    current_priority = None
    for line in match.group(1).splitlines():
        priority_match = re.search(r"(P[012])", line)
        if priority_match and line.lstrip().startswith("###"):
            current_priority = priority_match.group(1)
            continue
        if current_priority and re.match(r"\s*-\s*\[\s*\]", line):
            counts[current_priority] += 1
    return counts


def generate_state(
    plan_path: Path,
    rules: str = "common",
    risk: str = "medium",
    oversight: str = "auto",
    memory_mode: str = "candidate",
) -> dict:
    if not plan_path.exists():
        return {
            "error": f"PLAN.md not found: {plan_path}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    text = plan_path.read_text(encoding="utf-8")
    header = parse_header(text)
    freshness = check_freshness(plan_path)
    current_phase = parse_current_phase(text)
    requested_rules = parse_rule_list(rules)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_path": str(plan_path),
        "project": {
            "owner": header.get("Owner"),
            "freshness_policy": header.get("Freshness"),
        },
        "current_phase": current_phase,
        "gate_status": parse_gate_status(text),
        "active_sprint": parse_sprint_tasks(text),
        "backlog_counts": parse_backlog_counts(text),
        "freshness": {
            "status": freshness.status,
            "last_updated": freshness.last_updated.isoformat() if freshness.last_updated else None,
            "days_since_update": freshness.days_since_update,
            "threshold_days": freshness.threshold_days,
        },
        "runtime_contract": {
            "task": current_phase["id"] or "unspecified",
            "rules": requested_rules,
            "risk": risk,
            "oversight": oversight,
            "memory_mode": memory_mode,
        },
        "rule_packs": describe_rule_selection(requested_rules),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate .governance-state.yaml from PLAN.md")
    parser.add_argument("--plan", "-p", default="PLAN.md")
    parser.add_argument("--output", "-o", default=".governance-state.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    parser.add_argument("--rules", default="common")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--oversight", default="auto")
    parser.add_argument("--memory-mode", default="candidate")
    args = parser.parse_args()

    state = generate_state(
        Path(args.plan),
        rules=args.rules,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
    )

    if args.format == "json":
        output = json.dumps(state, ensure_ascii=False, indent=2)
    else:
        output = (
            "# .governance-state.yaml\n"
            "# Auto-generated by governance_tools/state_generator.py\n"
            "# DO NOT edit manually; update PLAN.md or runtime inputs instead.\n"
            "#\n"
            + dict_to_yaml(state)
        )

    if args.dry_run:
        print(output)
    else:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
