#!/usr/bin/env python3
"""
plan_summary.py — source-linked PLAN context with exact safety excerpts.

Open work includes in-progress items, continuations and nested conditions.
Authorization, navigation and constraint text is carried verbatim. Everything
else has a line-range index and must be reread before task-dependent action.
Legacy JSON fields and CLI/provenance behavior remain available.

Usage:
  python scripts/plan_summary.py
  python scripts/plan_summary.py --plan PLAN.md
  python scripts/plan_summary.py --format json
  python scripts/plan_summary.py --out artifacts/plan-summary.md
  python scripts/plan_summary.py --startup --plan PLAN.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.state_generator import (
    parse_backlog_counts,
    parse_current_phase,
    parse_gate_status,
    parse_header,
    parse_plan_headings,
    parse_plan_tasks,
    parse_sprint_tasks,
    plan_source_lines,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _head_commit(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=project_root, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _parse_active_blockers(text: str) -> list[str]:
    """Keep the list-of-strings interface, without dropping nested conditions."""
    return [task["text"] for task in parse_plan_tasks(text)
            if not task["done"] and not task["historical"] and any(
                marker in task["text"] for marker in
                ("❌", "[FAIL]", "Blocker", "NOT_READY", "blocked", "待辦", "未達標"))]


def _parse_open_phase_e_tasks(text: str) -> list[str]:
    """Support both the old named sprint and the current Phase E sprint."""
    heading = next((h for h in parse_plan_headings(text)
                    if re.match(r"Phase E Sprint\b", h["heading"], re.I)), None)
    if heading:
        return [t["name"] for t in parse_plan_tasks(text) if not t["done"] and not t["historical"]
                and heading["line"] < t["line"] <= heading["end_line"]]
    if parse_current_phase(text)["id"] == "PhaseE":
        return [t["name"] for t in parse_sprint_tasks(text) if not t["done"]]
    return []


def _parse_decision_table_tail(text: str, n: int = 5) -> list[dict]:
    """Extract the last n rows from the decision table."""
    match = re.search(r"##\s*決策紀錄(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if not match:
        return []
    rows: list[dict] = []
    for line in match.group(1).splitlines():
        parts = [p.strip() for p in line.split("|")]
        # markdown table rows have at least 4 parts (empty | date | decision | note | empty)
        if len(parts) >= 4 and parts[1] and not parts[1].startswith("-") and not parts[1].startswith("日"):
            rows.append({"date": parts[1], "decision": parts[2], "note": parts[3]})
    return rows[-n:]


def _parse_sa_layer1_log(text: str) -> list[dict]:
    """Extract the Layer 1 execution log table for SpecAuthority."""
    match = re.search(r"Layer 1 執行紀錄.*?\n(.*?)(?=\n\s*\*\*Layer 1 穩定|\Z)", text, re.DOTALL)
    if not match:
        return []
    rows: list[dict] = []
    for line in match.group(1).splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 7 and parts[1] and not parts[1].startswith("-") and not parts[1].startswith("次"):
            rows.append({
                "run": parts[1],
                "date": parts[2],
                "session_id": parts[3],
                "artifact_state": parts[5],
                "note": parts[7] if len(parts) > 7 else "",
            })
    return rows


def _parse_sa_layer1_status(text: str) -> str:
    m = re.search(r"\*\*Layer 1 穩定狀態\*\*[：:]\s*(.+)", text)
    return m.group(1).strip() if m else "unknown"


def _parse_phase2_gate_status(text: str) -> list[str]:
    """Extract Phase 2 gate conditions from the G6 five-condition list."""
    # Find the updated gate conditions block (after the lifecycle_active_ratio replacement)
    match = re.search(
        r"Phase 2 readiness gate.*?\*\*五條件\*\*.*?\n((?:\s*-[^\n]+\n){3,8})",
        text, re.DOTALL
    )
    if not match:
        # fallback: find numbered gate lines near 'readiness gate'
        match2 = re.search(r"readiness gate[（(].*?[)）].*?\n((?:.*?\n){1,10})", text, re.DOTALL)
        if not match2:
            return []
        block = match2.group(1)
    else:
        block = match.group(1)
    lines = []
    for line in block.splitlines():
        stripped = line.strip()
        if re.match(r"[-\d]", stripped) and stripped:
            lines.append(stripped)
    return lines[:6]


# ── compression provenance ────────────────────────────────────────────────

# These values are fixed for plan_summary.py output.
# fidelity=summarized: agent sees extracted subset, not full PLAN.md
# origin: which tool produced this view
# summary_kind: deterministic_extract = rule-based extraction, not AI-rewritten narrative
_PLAN_CONTEXT_PROVENANCE: dict = {
    "fidelity": "summarized",
    "origin": "plan_summary.py",
    "summary_kind": "deterministic_extract",
}

# Marker embedded at line 1 of human-format output so session_start.py can
# detect without parsing the full file.
_PROVENANCE_MARKER = (
    "<!-- plan_context_provenance "
    "fidelity=summarized origin=plan_summary.py summary_kind=deterministic_extract -->"
)

_PROVENANCE_SIDECAR_PATH = Path("artifacts") / "runtime" / "plan-context-provenance.json"


# ── main summary builder ───────────────────────────────────────────────────

def _summary_backlog_counts(text: str) -> dict:
    """Compatibility alias; both derived views now use the same parser."""
    return parse_backlog_counts(text)


_READ_RULE = (
    "When a task touches a section that is only indexed (or partially carried), "
    "read those PLAN lines before acting. Decision effects are navigation aids, "
    "not complete grants of authority. Use current owner authorization; open "
    "checkboxes can be standing constraints, not permission to execute. Regenerate "
    "a saved summary if the source SHA-256 changes. Dated grants may be superseded; "
    "they do not authorize this session. Follow SYSTEM_PROMPT.md section 2.2: use "
    "summary context only when startup_read=summary, coverage is complete and no "
    "warnings are reported. Read the full PLAN before editing it, on command "
    "failure/warnings, or when the owner asks."
)
_CONSTRAINT_HEADING = re.compile(
    r"claim (?:ceiling|boundar)|cannot claim|constraints?|non-goals?|anti-goals?|"
    r"dirty workspace policy|definition of done|blocking relationships|funding gate|"
    r"phase e posture|per-surface decisions|^decisions$", re.I)
_CONSTRAINT_TEXT = re.compile(
    r"claim ceiling|\b(?:NOT[ _]CLAIMED|CANNOT CLAIM|cannot claim|do not claim|unclaimed)\b|"
    r"\b(?:unauthori[sz]ed|not authori[sz]ed|does not authori[sz]e|do not|must not|"
    r"standing constraint|not funded|only after)\b|\bno [^\n.]{0,160}authori[sz]ed\b", re.I)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# Small plans cost less to read directly. A complete index alone does not prove
# semantic extraction: only the evaluated framework outline is supported for
# summary-first loading. Dates and source-commit labels are not layout changes.
FULL_READ_MAX_BYTES = 16_384
_SUPPORTED_OUTLINES = {
    "18acabad91f071ca7f626bfb112551db2332a77abb375c098fb45007cc97bc27": "framework_plan",
}


def _outline_digest(text: str) -> str:
    headings = [re.sub(r"\b[0-9a-f]{7,40}\b", "<commit>", _DATE.sub("<date>", h["heading"]))
                for h in parse_plan_headings(text) if h["level"] == 2]
    return hashlib.sha256("\n".join(headings).encode("utf-8")).hexdigest()


def _complete_index(text: str, sections: list[dict]) -> bool:
    """Validate actual inclusive coverage, not the presence of an index key."""
    cursor = 1
    try:
        for section in sections:
            start, end = section["line"], section["end_line"]
            if type(start) is not int or type(end) is not int or start != cursor or end < start:
                return False
            cursor = end + 1
        if cursor != len(text.splitlines()) + 1:
            return False
        indexed = {s["line"]: s["heading"] for s in sections if s["kind"] == "markdown"}
        return all(indexed.get(h["line"]) == h["heading"] for h in parse_plan_headings(text))
    except (KeyError, TypeError):
        return False


def _startup_loading(text: str, summary: dict) -> dict:
    """Select context only; this signal grants no execution or gate authority."""
    lines, code = plan_source_lines(text)
    sections = summary["section_index"]
    coverage = _complete_index(text, sections)
    outline = _outline_digest(text)
    layout = _SUPPORTED_OUTLINES.get(outline)
    warnings = []
    if not coverage:
        warnings.append("incomplete_index")
    if summary["source"]["bytes"] > FULL_READ_MAX_BYTES:
        if not layout:
            warnings.append("unverified_layout")
        if not summary["current_phase"]["id"]:
            warnings.append("current_phase_not_parsed")
        history = [(s["line"], s.get("subtree_end_line", s["end_line"])) for s in sections
                   if re.match(r"^(?:Historical\b|History\b|Archive[ds]?\b|歷史|封存)", s["heading"], re.I)]
        expected = {n for n, line in enumerate(lines, 1)
                    if n not in code and re.match(r"\s*(?:[-+*]|\d+[.)])\s+\[[ >~]\]", line)
                    and not any(a <= n <= b for a, b in history)}
        items = summary["open_items"]
        if ({t["line"] for t in items} != expected or any(
                t["text"] != "\n".join(lines[t["line"] - 1:t["end_line"]]) for t in items)):
            warnings.append("open_item_coverage_incomplete")
        carried = {n for span in summary["carried_sections"]
                   for n in range(span["line"], span["end_line"] + 1)}
        if any(span["content"] != "\n".join(lines[span["line"] - 1:span["end_line"]])
               for span in summary["carried_sections"]):
            warnings.append("constraint_text_mismatch")
        headings = parse_plan_headings(text)
        first_section = next((h["line"] for h in headings if h["level"] == 2), len(lines) + 1)
        if any(line.strip() and not re.match(r"^#\s+", line.lstrip("\ufeff")) for line in lines[:first_section - 1]):
            warnings.append("unclassified_preamble")
        required = {"Canonical Planning Surface", "Active Claim Boundaries", "Dirty Workspace Policy",
                    "Definition Of Done For Current Planning Slice", "Cannot Claim From This PLAN Alone"}
        found = set()
        for index, heading in enumerate(headings):
            if heading["heading"] not in required:
                continue
            found.add(heading["heading"])
            end = heading["end_line"]
            if heading["heading"] == "Cannot Claim From This PLAN Alone" and index + 1 < len(headings):
                end = headings[index + 1]["line"] - 1
            if any(n not in carried for n in range(heading["line"], end + 1) if lines[n - 1].strip()):
                warnings.append("startup_constraints_not_carried")
        if found != required:
            warnings.append("startup_constraints_not_found")
        fence = None
        for line in lines:
            match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
            if not match:
                continue
            if fence is None:
                fence = match[1]
            elif match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
        if fence:
            warnings.append("unclosed_code_fence")
        if any(n not in code and re.match(r"\s*(?:[-+*]|\d+[.)])\s+\[[^\]]*\]", line)
               and not re.match(r"\s*(?:[-+*]|\d+[.)])\s+\[[ xX>~]\]", line)
               for n, line in enumerate(lines, 1)):
            warnings.append("unsupported_checkbox_marker")
    small = summary["source"]["bytes"] <= FULL_READ_MAX_BYTES
    return {"startup_read": "full" if small or warnings else "summary",
            "reason": "small_plan" if small else warnings[0] if warnings else "supported_layout",
            "full_read_max_bytes": FULL_READ_MAX_BYTES, "index_coverage_complete": coverage,
            "layout": layout, "outline_sha256": outline, "warnings": list(dict.fromkeys(warnings))}


def _paragraphs(lines: list[str], code: set[int]) -> list[tuple[int, int]]:
    """Source paragraphs/list entries, keeping wrapped and nested text exact."""
    spans = []
    start = None
    for number, line in enumerate(lines, 1):
        # Separate adjacent root bullets, but keep their continuation lines.
        boundary = number not in code and re.match(
            r"^(?:(?:[-+*]|\d+[.)])\s+|#{1,6}\s+|P\d+(?:-[A-Z][A-Z0-9]*)?\s+[-—–]|"
            r"Current (?:refresh|sprint)|Historical\b|(?:Claim ceiling|Non-goals?|Anti-goals?)[ :])", line, re.I)
        if not line.strip() or boundary:
            if start is not None:
                spans.append((start, number - 1))
                start = None
        if line.strip() and start is None:
            start = number
    if start is not None:
        spans.append((start, len(lines)))
    return spans


def _section_index(text: str) -> list[dict]:
    """A gap-free partition, including PLAN's plain, sometimes wrapped labels.

    Markdown headings have subtree ranges as well as disjoint own ranges.
    Plain labels (priority groups, refreshes, colon headings) are navigation
    boundaries too. Dates, checkbox state, and heading age never erase authority.
    """
    lines, code = plan_source_lines(text)
    headings = parse_plan_headings(text)
    starts = {h["line"]: dict(h, kind="markdown") for h in headings}
    for start, end in _paragraphs(lines, code):
        first = lines[start - 1]
        if start in starts or start in code or not first or first[0] in " \t-|>+*`~<":
            continue
        paragraph = " ".join(line.strip() for line in lines[start - 1:end])
        inline = re.match(r"(Claim ceiling(?: for [^:]+)?):\s*\S", paragraph, re.I)
        if inline or (len(paragraph) <= 300 and paragraph.endswith(":")):
            title = inline[1] if inline else paragraph.rstrip(":")
            starts[start] = {"heading": title, "line": start, "kind": "label",
                             "heading_end_line": end, "inline": bool(inline)}
    if lines and 1 not in starts:
        starts[1] = {"heading": "Preamble", "line": 1, "kind": "preamble"}
    sections = [starts[line] for line in sorted(starts)]
    for index, section in enumerate(sections):
        if "end_line" in section:
            section["subtree_end_line"] = section["end_line"]
        section["end_line"] = sections[index + 1]["line"] - 1 if index + 1 < len(sections) else len(lines)
        parents = [h["heading"] for h in headings if h["line"] < section["line"] <= h["end_line"]]
        section["path"] = " / ".join(parents + [section["heading"]])
        parent_level = max((h["level"] for h in headings if h["line"] < section["line"] <= h["end_line"]), default=0)
        is_context = re.match(r"^(?:P\d+(?:-[A-Z][A-Z0-9]*)?\s+[-—–]|Current refresh|Historical sprint|Completed \d{4})", section["heading"], re.I)
        section["logical_level"] = section.get("level", parent_level + (1 if is_context else 2))
    for index, section in enumerate(sections):
        if section["kind"] != "markdown":
            section["subtree_end_line"] = next((other["line"] - 1 for other in sections[index + 1:]
                                                if other["logical_level"] <= section["logical_level"]), len(lines))
    return sections


def _fidelity_context(text: str) -> dict:
    lines, code = plan_source_lines(text)
    sections = _section_index(text)
    all_tasks = parse_plan_tasks(text)
    spans: list[tuple[int, int, str]] = []
    navigation = re.compile(r"^Canonical Planning Surface$|^Authori[sz]ed\b|^Owner-recommended\b|"
                            r"^Phase Overview$|^Work Item Glossary$", re.I)
    for section in sections:
        if navigation.search(section["heading"]):
            end = section.get("subtree_end_line", section["end_line"]) if section["heading"] == "Canonical Planning Surface" else section["end_line"]
            spans.append((section["line"], end, "authorization/navigation"))
        if _CONSTRAINT_HEADING.search(section["heading"]):
            end = section["heading_end_line"] if section.get("inline") else section["end_line"]
            spans.append((section["line"], end, "constraint section"))
    # Carry all children of explicitly named safety sections, but do not absorb
    # later decision appendices merely because they use a lower heading level.
    safety_parent = None
    for section in sections:
        if section["kind"] == "markdown" and section.get("level", 0) <= 2:
            safety_parent = section["heading"] if _CONSTRAINT_HEADING.search(section["heading"]) else None
        nested_safety = safety_parent and re.search(r"active claim boundar|constraints?", safety_parent, re.I)
        if safety_parent and (section["kind"] != "markdown" or (nested_safety and section.get("level", 0) > 2)):
            spans.append((section["line"], section["end_line"], "constraint section"))
    for start, end in _paragraphs(lines, code):
        content = "\n".join(lines[start - 1:end])
        completed_context = any(t["done"] and t["line"] <= start <= t["end_line"] for t in all_tasks)
        # Completed implementation narratives remain indexed. Explicit safety
        # headings and labelled claim paragraphs are carried even inside them;
        # a past-tense "did not change" is not itself a standing instruction.
        explicit_label = re.match(r"\s*(?:-\s*)?(?:Claim ceiling|NOT[ _]CLAIMED|CANNOT CLAIM|Non-goals?|Anti-goals?)\b", content, re.I)
        if start not in code and (not completed_context or explicit_label) and _CONSTRAINT_TEXT.search(content):
            spans.append((start, end, "constraint paragraph"))
    # Merge overlaps to avoid repeating the same source in the human view.
    merged = []
    for start, end, reason in sorted(spans):
        if merged and (start <= merged[-1]["end_line"] + 1 or
                       not any(line.strip() for line in lines[merged[-1]["end_line"]:start - 1])):
            merged[-1]["end_line"] = max(end, merged[-1]["end_line"])
            if reason not in merged[-1]["reasons"]:
                merged[-1]["reasons"].append(reason)
        else:
            merged.append({"line": start, "end_line": end, "reasons": [reason]})
    for span in merged:
        span["content"] = "\n".join(lines[span["line"] - 1:span["end_line"]])
    decisions = []
    paragraphs = _paragraphs(lines, code)
    heading_lines = {number for section in sections for number in
                     range(section["line"], section.get("heading_end_line", section["line"]) + 1)}
    for section in sections:
        heading = section["heading"]
        if re.match(r"Current Sprint\b", heading, re.I):
            continue
        if _CONSTRAINT_HEADING.search(heading):
            continue
        if not (_DATE.search(heading) or re.search(r"decision|adoption|ratifi|funding gate|決策", heading, re.I)):
            continue
        if re.search(r"historical|completed in|milestone commits|scoped evidence|encoding repair", heading, re.I):
            continue
        body_start = section.get("heading_end_line", section["line"]) + 1
        end_line = section.get("subtree_end_line", section["end_line"])
        first_content = next((n for n in range(body_start, end_line + 1)
                              if n not in heading_lines and n not in code and lines[n - 1].strip()), None)
        body = next(((first_content, min(b, end_line)) for a, b in paragraphs
                     if first_content is not None and a <= first_content <= b), None)
        effect = " ".join(lines[body[0] - 1:body[1]]) if body else heading
        # An effect is an intact first sentence, not a cut-off first line.
        effect = re.split(r"(?<=[.!?])\s+(?=[A-Z])", effect, maxsplit=1)[0]
        date = _DATE.search(heading) or _DATE.search(effect)
        decisions.append({"heading": heading, "date": date[0] if date else None,
                          "effect": effect, "line": section["line"], "end_line": end_line,
                          "effect_line": body[0] if body else section["line"]})
    # A decision can also be recorded as a completed checkbox, rather than a
    # heading. Keep the explicit date and whole first sentence for those grants.
    for task in all_tasks:
        if re.match(r"P\d+(?:-[A-Z][A-Z0-9]*)?\s+decided\s+\d{4}-\d{2}-\d{2}", task["name"], re.I):
            effect = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(task["name"].split()), maxsplit=1)[0]
            decisions.append({"heading": task["name"].splitlines()[0], "date": _DATE.search(task["name"])[0],
                              "effect": effect, "line": task["line"], "end_line": task["end_line"],
                              "effect_line": task["line"]})
    decisions.sort(key=lambda item: item["line"])
    tasks = [task for task in all_tasks if not task["done"] and not task["historical"]]
    for task in tasks:
        task["section"] = next(s["path"] for s in sections if s["line"] <= task["line"] <= s["end_line"])
    carried_lines = {n for span in merged + tasks for n in range(span["line"], span["end_line"] + 1)}
    for section in sections:
        covered = len(carried_lines.intersection(range(section["line"], section["end_line"] + 1)))
        length = section["end_line"] - section["line"] + 1
        section["coverage"] = "carried" if covered == length else "partial" if covered else "indexed"
    return {"read_rule": _READ_RULE, "open_items": tasks,
            "carried_sections": merged, "decision_index": decisions, "section_index": sections}


def build_plan_summary(plan_path: Path, project_root: Path) -> dict:
    payload = plan_path.read_bytes()
    text = payload.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    header = parse_header(text)
    phase = parse_current_phase(text)
    gates = parse_gate_status(text)
    sprint = parse_sprint_tasks(text)
    backlogs = _summary_backlog_counts(text)

    open_sprint = [t["name"] for t in sprint if not t["done"]]
    open_phase_e = _parse_open_phase_e_tasks(text)
    blockers = _parse_active_blockers(text)
    decisions = _parse_decision_table_tail(text, n=5)
    sa_log = _parse_sa_layer1_log(text)
    sa_status = _parse_sa_layer1_status(text)
    phase2_gate = _parse_phase2_gate_status(text)
    head = _head_commit(project_root)

    summary = {
        "read_rule": _READ_RULE,
        "source": {"sha256": hashlib.sha256(payload).hexdigest(),
                   "bytes": len(payload), "lines": len(text.splitlines())},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "head_commit": head,
        "plan_path": str(plan_path),
        "last_updated": header.get("最後更新") or header.get("last_updated"),
        "owner": header.get("Owner"),
        "current_phase": phase,
        "gate_status": gates,
        "open_sprint_items": open_sprint,
        "open_phase_e_tasks": open_phase_e,
        "active_blockers": blockers,
        "backlog_open": backlogs,
        "sa_layer1_log": sa_log,
        "sa_layer1_stability": sa_status,
        "phase2_gate_conditions": phase2_gate,
        "recent_decisions": decisions,
        # Compression provenance — always present in plan_summary output.
        # Lets session_start and session_end know context was compressed.
        "plan_context_provenance": _PLAN_CONTEXT_PROVENANCE,
        **_fidelity_context(text),
    }
    summary["startup_loading"] = _startup_loading(text, summary)
    return summary


def format_human(summary: dict) -> str:
    lines: list[str] = []
    # Provenance marker MUST be line 1 so session_start.py can detect it by
    # reading only the first line of the file (cheap, no full parse needed).
    lines.append(_PROVENANCE_MARKER)
    lines.append("# PLAN.md Compressed View")
    if "section_index" in summary:
        lines.append(summary["read_rule"])
    if "startup_loading" in summary:
        loading = summary["startup_loading"]
        lines.append(f"startup_read={loading['startup_read']} | index_coverage_complete={str(loading['index_coverage_complete']).lower()} | layout={loading['layout']} | warnings={json.dumps(loading['warnings'])}")
    lines.append(f"generated: {summary['generated_at']}  |  HEAD: {summary['head_commit']}")
    lines.append(f"plan: {summary['plan_path']}  |  last_updated: {summary['last_updated']}  |  owner: {summary['owner']}")
    lines.append("")

    if "section_index" in summary:
        source = summary["source"]
        lines.append(f"Source: {source['bytes']} bytes / {source['lines']} lines / SHA-256 {source['sha256']}")
        phase = summary["current_phase"]
        lines.append(f"Current phase: {phase['id']} — {phase['name']}")
        lines.append("Phase status: " + ", ".join(f"{key}={value}" for key, value in summary["gate_status"].items()))
        bl = summary["backlog_open"]
        lines.append(f"Backlog Open (unchecked, including constraints): P0={bl['P0']} P1={bl['P1']} P2={bl['P2']}")
        lines.extend(["", "## Open and in-progress items (not execution authorization)"])
        priorities = sorted({t["priority"] for t in summary["open_items"] if t["priority"]}, key=lambda p: int(p[1:]))
        for priority in priorities + [None]:
            items = [t for t in summary["open_items"] if t["priority"] == priority]
            if not items:
                continue
            lines.append(f"### {priority or 'Unprioritized'}")
            for item in items:
                lines.extend([f"PLAN.md:{item['line']}-{item['end_line']} | {item['status']} | {item['section']}", item["text"], ""])
        lines.append("## Authorization, navigation and standing constraints (exact source excerpts)")
        for span in summary["carried_sections"]:
            lines.extend([f"\nPLAN.md:{span['line']}-{span['end_line']}", span["content"]])
        lines.extend(["", "## Decisions and dated checkpoints (effects are navigation, reread before relying)"])
        for decision in summary["decision_index"]:
            lines.append(f"- PLAN.md:{decision['line']}-{decision['end_line']} | {decision['date'] or 'date not stated'} | {decision['heading']}\n  Effect: {decision['effect']}")
        lines.extend(["", "## Complete section index (inclusive source ranges, no gaps)",
                      "carried = whole range above; partial = some excerpts above; indexed = reread source. "
                      "Subsections have their own rows; a subtree extends through subtree_end_line in JSON."])
        for section in summary["section_index"]:
            lines.append(f"- PLAN.md:{section['line']}-{section['end_line']} [{section['coverage']}] {section['heading']}")
        # These legacy observations are still exposed in JSON in their original
        # shapes; retain nonempty observations in human output as well.
        if summary["sa_layer1_log"] or summary["sa_layer1_stability"] != "unknown":
            lines.append(f"\nSpecAuthority Layer 1: {summary['sa_layer1_stability']}")
            lines.extend(f"{row['run']} | {row['date']} | {row['session_id']} | artifact_state={row['artifact_state']}" for row in summary["sa_layer1_log"])
        if summary["phase2_gate_conditions"]:
            lines.extend(["\nPhase 2 Gate Conditions:"] + summary["phase2_gate_conditions"])
        if summary["recent_decisions"]:
            lines.append("\nLegacy decision table (last 5):")
            lines.extend(f"{d['date']} | {d['decision']} | {d['note']}" for d in summary["recent_decisions"])
        return "\n".join(lines)

    # Phase + gates
    phase = summary["current_phase"]
    lines.append(f"## Current Phase: {phase.get('id')} — {phase.get('name')}")
    gate_lines = [f"  {'[x]' if v == 'passed' else '[>]' if v == 'in_progress' else '[ ]'} {k}: {v}"
                  for k, v in summary["gate_status"].items()]
    lines.extend(gate_lines)
    lines.append("")

    # Open sprint
    if summary["open_sprint_items"]:
        lines.append("## Open Sprint Items")
        for item in summary["open_sprint_items"]:
            lines.append(f"  - [ ] {item}")
        lines.append("")

    # Open Phase E tasks
    if summary["open_phase_e_tasks"]:
        lines.append("## Open Phase E Tasks")
        for item in summary["open_phase_e_tasks"]:
            lines.append(f"  - [ ] {item}")
        lines.append("")

    # Active blockers
    if summary["active_blockers"]:
        lines.append("## Active Blockers")
        for b in summary["active_blockers"]:
            lines.append(f"  {b}")
        lines.append("")

    # Backlog counts
    bl = summary["backlog_open"]
    lines.append(f"## Backlog Open: P0={bl.get('P0',0)}  P1={bl.get('P1',0)}  P2={bl.get('P2',0)}")
    lines.append("")

    # SA Layer 1 status
    lines.append(f"## SpecAuthority Layer 1: {summary['sa_layer1_stability']}")
    if summary["sa_layer1_log"]:
        lines.append("  Execution log:")
        for row in summary["sa_layer1_log"]:
            lines.append(f"    {row['run']} | {row['date']} | {row['session_id']} | artifact_state={row['artifact_state']}")
    lines.append("")

    # Phase 2 gate
    if summary["phase2_gate_conditions"]:
        lines.append("## Phase 2 Gate Conditions")
        for c in summary["phase2_gate_conditions"]:
            lines.append(f"  {c}")
        lines.append("")

    # Recent decisions
    if summary["recent_decisions"]:
        lines.append("## Recent Decisions (last 5)")
        for d in summary["recent_decisions"]:
            lines.append(f"  {d['date']} | {d['decision']}")
        lines.append("")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────

def _emit_output(args: argparse.Namespace, output: str) -> None:
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"[plan_summary] wrote {args.out}")
    else:
        print(output)


def _emit_full_plan(args: argparse.Namespace, plan_path: Path, reason: str, warnings: list[str]) -> None:
    text = plan_path.read_text(encoding="utf-8")
    status = {"startup_read": "full", "reason": reason, "warnings": warnings,
              "full_read_max_bytes": FULL_READ_MAX_BYTES}
    if warnings:
        print(f"[plan_summary] WARNING: {', '.join(warnings)}; read the full {plan_path} below before acting.", file=sys.stderr)
    output = (json.dumps({"startup_loading": status, "plan_path": str(plan_path), "full_plan_text": text}, ensure_ascii=False, indent=2)
              if args.format == "json" else f"# PLAN startup: startup_read=full | reason={reason} | source_lines={len(text.splitlines())}\n\n{text}")
    _emit_output(args, output)
    # No compressed view was delivered. Existing summary CLI sidecar behavior
    # below is unchanged; a full startup read does not write compression evidence.


def main() -> None:
    parser = argparse.ArgumentParser(description="PLAN.md source-linked session context and section index")
    parser.add_argument("--plan", default="PLAN.md", help="Path to PLAN.md")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--out", help="Write output to file instead of stdout")
    parser.add_argument("--startup", action="store_true", help="Read small or unsupported PLANs in full; otherwise emit a checked summary")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"[plan_summary] ERROR: {plan_path} not found; read the full PLAN before acting.", file=sys.stderr)
        sys.exit(1)

    project_root = plan_path.parent.resolve()
    try:
        if args.startup and plan_path.stat().st_size <= FULL_READ_MAX_BYTES:
            _emit_full_plan(args, plan_path, "small_plan", [])
            return
        try:
            summary = build_plan_summary(plan_path, project_root)
        except Exception:
            if not args.startup:
                raise
            _emit_full_plan(args, plan_path, "summary_failed", ["summary_failed"])
            return
        loading = summary["startup_loading"]
        eligible = (loading.get("startup_read") == "summary" and loading.get("index_coverage_complete") is True
                    and loading.get("layout") in _SUPPORTED_OUTLINES.values() and loading.get("warnings") == [])
        if args.startup and not eligible:
            reason, warnings = loading.get("reason", "invalid_loading_signal"), loading.get("warnings", [])
            if loading.get("startup_read") == "summary":
                reason, warnings = "invalid_loading_signal", ["invalid_loading_signal"]
            _emit_full_plan(args, plan_path, reason, warnings)
            return
    except Exception as exc:
        print(f"[plan_summary] ERROR: {type(exc).__name__}; read the full {plan_path} before acting.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output = json.dumps(summary, ensure_ascii=False, indent=2)
    else:
        output = format_human(summary)

    _emit_output(args, output)

    # Always write provenance sidecar so session_end_hook can read it
    # even when plan_summary output goes to stdout (not to a file).
    sidecar_path = project_root / _PROVENANCE_SIDECAR_PATH
    try:
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(
            json.dumps(_PLAN_CONTEXT_PROVENANCE, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass  # Non-blocking: sidecar write failure must not abort summary output


if __name__ == "__main__":
    main()
