#!/usr/bin/env python3
"""
Rule pack discovery and loading helpers.
"""

from __future__ import annotations

import re
from pathlib import Path


DEFAULT_RULES_ROOT = Path(__file__).resolve().parent.parent / "governance" / "rules"


def parse_rule_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else value.split(",")
    parsed = []
    seen = set()
    for item in raw_items:
        name = item.strip()
        if not name or name in seen:
            continue
        parsed.append(name)
        seen.add(name)
    return parsed


def available_rule_packs(rules_root: Path = DEFAULT_RULES_ROOT) -> set[str]:
    if not rules_root.exists():
        return set()
    return {entry.name for entry in rules_root.iterdir() if entry.is_dir()}


def _read_rule_file(rule_file: Path, rules_root: Path) -> dict:
    text = rule_file.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else rule_file.stem
    return {
        "path": str(rule_file.relative_to(rules_root.parent.parent)),
        "title": title,
        "content": text.strip(),
    }


def load_rule_content(requested_rules: list[str], rules_root: Path = DEFAULT_RULES_ROOT) -> dict:
    available = available_rule_packs(rules_root)
    active_rules = []
    missing = []

    for name in requested_rules:
        pack_dir = rules_root / name
        if name not in available:
            missing.append(name)
            continue
        active_rules.append(
            {
                "name": name,
                "files": [_read_rule_file(rule_file, rules_root) for rule_file in sorted(pack_dir.glob("*.md"))],
            }
        )

    return {
        "requested": requested_rules,
        "active_rules": active_rules,
        "missing": missing,
        "valid": not missing,
    }


def describe_rule_selection(requested_rules: list[str], rules_root: Path = DEFAULT_RULES_ROOT) -> dict:
    loaded = load_rule_content(requested_rules, rules_root)
    resolved = []

    for pack in loaded["active_rules"]:
        resolved.append({"name": pack["name"], "files": [entry["path"] for entry in pack["files"]]})

    return {
        "requested": requested_rules,
        "resolved": resolved,
        "missing": loaded["missing"],
        "valid": loaded["valid"],
    }
