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
from governance_tools.architecture_impact_estimator import estimate_architecture_impact
from governance_tools.rule_pack_loader import describe_rule_selection, load_rule_content, parse_rule_list
from governance_tools.rule_pack_suggester import suggest_rule_packs


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
    lines, code = plan_source_lines(text)
    for number, line in enumerate(lines, 1):
        match = re.match(r"\s*(?:[-+*]\s+)?\[([xX>~ ])\]\s*(Phase\s+\w+)\s*:\s*(.+)", line)
        if number in code or not match:
            continue
        if match.group(1) in {">", "~"}:
            return {
                "id": match.group(2).replace(" ", ""),
                "name": match.group(3).strip(),
            }
    return {"id": None, "name": None}


def parse_gate_status(text: str) -> dict:
    statuses = {}
    lines, code = plan_source_lines(text)
    for number, line in enumerate(lines, 1):
        match = re.match(r"\s*(?:[-+*]\s+)?\[([xX>~ ])\]\s*(Phase\s+\w+)(?:\s*:\s*(.*))?", line)
        if number in code or not match:
            continue
        marker = match.group(1)
        phase = match.group(2).replace(" ", "")
        detail = (match.group(3) or "").strip().lower()
        if marker in {"x", "X"}:
            statuses[phase] = "passed"
        elif marker in {">", "~"}:
            statuses[phase] = "in_progress"
        elif "resumable" in detail:
            statuses[phase] = "resumable"
        else:
            statuses[phase] = "pending"
    return statuses


_PLAN_CHECKBOX = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+\[([ xX>~])\]\s*(.*)$")
_PLAN_LIST = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+")
_PLAN_PRIORITY = re.compile(r"^P(\d+)(?:-[A-Z][A-Z0-9]*)?(?:\s*[-:—–]|\s*$)")
_PLAN_HISTORY = re.compile(r"^(?:historical\b|history\b|archive[ds]?\b|歷史|封存)", re.I)


def plan_source_lines(text: str) -> tuple[list[str], set[int]]:
    """Return source lines and fenced-code line numbers (one based)."""
    lines = text.splitlines()
    code = set()
    fence = None
    for number, line in enumerate(lines, 1):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence:
            code.add(number)
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
        elif match:
            fence = match[1]
            code.add(number)
    return lines, code


def parse_plan_headings(text: str) -> list[dict]:
    """Markdown heading subtrees, ignoring examples inside fenced code."""
    lines, code = plan_source_lines(text)
    headings = []
    for number, line in enumerate(lines, 1):
        match = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line.lstrip("\ufeff"))
        if match and number not in code:
            headings.append({"heading": match[2], "level": len(match[1]), "line": number})
    for index, heading in enumerate(headings):
        heading["end_line"] = next((other["line"] - 1 for other in headings[index + 1:]
                                    if other["level"] <= heading["level"]), len(lines))
    return headings


def parse_plan_tasks(text: str) -> list[dict]:
    """Extract exact list-item spans, including nested conditions and continuations.

    A sibling/ancestor list item, a heading, or an unindented paragraph after
    a blank line ends an item. Explicit historical headings suppress current
    work classification; age and completed siblings never do. Priority labels
    must be headings or standalone labels, never words in a task's prose.
    """
    lines, code = plan_source_lines(text)
    headings = parse_plan_headings(text)
    by_line = {heading["line"]: heading for heading in headings}
    priority = None
    priority_level = None
    historical_until = 0
    tasks = []
    for number, line in enumerate(lines, 1):
        if number in code:
            continue
        heading = by_line.get(number)
        if heading:
            if priority_level is not None and heading["level"] <= priority_level:
                priority = priority_level = None
            label = heading["heading"]
            if _PLAN_HISTORY.match(label):
                historical_until = heading["end_line"]
        else:
            label = line.strip("* ") if line == line.lstrip() else ""
            if _PLAN_HISTORY.match(label):
                # A plain historical label lasts to the next peer Markdown
                # section, or an explicit current refresh, rather than EOF.
                historical_until = min((h["end_line"] for h in headings
                                        if h["line"] <= number <= h["end_line"]), default=len(lines))
            elif re.match(r"Current (?:refresh|sprint)\b", label, re.I):
                historical_until = 0
        priority_match = _PLAN_PRIORITY.match(label)
        if priority_match:
            priority = "P" + priority_match[1]
            priority_level = heading["level"] if heading else max(
                (h["level"] + 1 for h in headings if h["line"] <= number <= h["end_line"]), default=1)
        match = _PLAN_CHECKBOX.match(line)
        if not match:
            continue
        indent = len(match[1].expandtabs(4))
        end = number
        for following in range(number + 1, len(lines) + 1):
            candidate = lines[following - 1]
            if (re.match(r"^(?:`{3,}|~{3,})", candidate) and not lines[following - 2].strip()):
                break
            if following not in code:
                sibling = _PLAN_LIST.match(candidate)
                if following in by_line or (sibling and len(sibling[1].expandtabs(4)) <= indent):
                    break
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                    label_boundary = re.match(r"^(?:Current (?:refresh|sprint)|Historical\b|Claim ceiling|Non-goals?|Anti-goals?)", candidate, re.I)
                    if not lines[following - 2].strip() or _PLAN_PRIORITY.match(candidate) or label_boundary:
                        break
            end = following
        while end > number and not lines[end - 1].strip():
            end -= 1
        raw = "\n".join(lines[number - 1:end])
        tasks.append({
            "name": "\n".join([match[3]] + lines[number:end]),
            "done": match[2].lower() == "x",
            "status": "done" if match[2].lower() == "x" else "in_progress" if match[2] in ">~" else "open",
            "text": raw, "line": number, "end_line": end,
            "priority": priority, "historical": number <= historical_until,
        })
    return tasks


def parse_sprint_tasks(text: str) -> list[dict]:
    section = next((h for h in parse_plan_headings(text)
                    if re.match(r"Current Sprint\b", h["heading"], re.I)), None)
    if not section:
        return []
    # Keep the existing name/done interface for state-generator consumers.
    return [{"name": task["name"], "done": task["done"]} for task in parse_plan_tasks(text)
            if section["line"] < task["line"] <= section["end_line"] and not task["historical"]]


def parse_backlog_counts(text: str) -> dict:
    counts = {"P0": 0, "P1": 0, "P2": 0}
    headings = parse_plan_headings(text)
    section = next((h for h in headings if re.match(r"Backlog\b", h["heading"], re.I)), None)
    if section is None:
        section = next((h for h in headings if re.match(r"Pending Work\s*[-—–]\s*Ordered\b", h["heading"], re.I)), None)
    if section is None:
        return counts
    for task in parse_plan_tasks(text):
        if (section["line"] < task["line"] <= section["end_line"] and not task["historical"]
                and task["status"] == "open" and task["priority"] in counts):
            counts[task["priority"]] += 1
    return counts


def _proposal_guidance(impact_preview: dict | None) -> dict | None:
    if not impact_preview:
        return None
    return {
        "recommended_risk": impact_preview.get("recommended_risk"),
        "recommended_oversight": impact_preview.get("recommended_oversight"),
        "expected_validators": impact_preview.get("expected_validators", []) or [],
        "required_evidence": impact_preview.get("required_evidence", []) or [],
        "concerns": impact_preview.get("concerns", []) or [],
    }


def generate_state(
    plan_path: Path,
    rules: str = "common",
    risk: str = "medium",
    oversight: str = "auto",
    memory_mode: str = "candidate",
    project_root: Path | None = None,
    task_text: str | None = None,
    impact_before_files: list[Path] | None = None,
    impact_after_files: list[Path] | None = None,
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
    resolved_project_root = (project_root or plan_path.parent).resolve()
    effective_task_text = task_text if task_text is not None else (current_phase["name"] or current_phase["id"] or "")
    suggestions = suggest_rule_packs(resolved_project_root, task_text=effective_task_text)
    impact_before_files = impact_before_files or []
    impact_after_files = impact_after_files or []
    impact_preview = None

    if impact_before_files or impact_after_files:
        scope = "refactor" if "refactor" in requested_rules else "feature"
        impact_preview = estimate_architecture_impact(
            impact_before_files,
            impact_after_files,
            scope=scope,
            active_rules=requested_rules,
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_surface_contract": {
            "surface_role": "derived_context_snapshot",
            "authority_scope": "session_context_only",
            "source_of_truth": {
                "plan": str(plan_path),
                "runtime_artifacts": "artifacts/runtime/*",
            },
            "non_authoritative_for": [
                "gate_verdict",
                "classification_validation",
                "escalation_closure",
            ],
            "operator_note": (
                "This file is a convenience snapshot for session bootstrap. "
                "It must not be used as sole authority for closure or promotion decisions."
            ),
        },
        "plan_path": str(plan_path),
        "project_root": str(resolved_project_root),
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
        "suggested_rules_preview": suggestions.get("suggested_rules_preview", []),
        "suggested_skills": suggestions.get("suggested_skills", []),
        "suggested_agent": suggestions.get("suggested_agent"),
        "rule_pack_suggestions": suggestions,
        "architecture_impact_preview": impact_preview,
        "proposal_guidance": _proposal_guidance(impact_preview),
        "rule_packs": describe_rule_selection(requested_rules),
        "active_rules": load_rule_content(requested_rules),
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
    parser.add_argument("--project-root")
    parser.add_argument("--task-text")
    parser.add_argument("--impact-before", action="append", default=[])
    parser.add_argument("--impact-after", action="append", default=[])
    args = parser.parse_args()

    state = generate_state(
        Path(args.plan),
        rules=args.rules,
        risk=args.risk,
        oversight=args.oversight,
        memory_mode=args.memory_mode,
        project_root=Path(args.project_root) if args.project_root else None,
        task_text=args.task_text,
        impact_before_files=[Path(path) for path in args.impact_before],
        impact_after_files=[Path(path) for path in args.impact_after],
    )

    if args.format == "json":
        output = json.dumps(state, ensure_ascii=False, indent=2)
    else:
        output = (
            "# .governance-state.yaml\n"
            "# Auto-generated by governance_tools/state_generator.py\n"
            "# Surface role: derived context snapshot (session bootstrap only)\n"
            "# NOT authority for gate verdict, classification validation, or escalation closure.\n"
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
