#!/usr/bin/env python3
"""
Rule pack discovery and loading helpers.
"""

from __future__ import annotations

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


def describe_rule_selection(requested_rules: list[str], rules_root: Path = DEFAULT_RULES_ROOT) -> dict:
    available = available_rule_packs(rules_root)
    resolved = []
    missing = []

    for name in requested_rules:
        pack_dir = rules_root / name
        if name not in available:
            missing.append(name)
            continue
        files = sorted(str(path.relative_to(rules_root.parent.parent)) for path in pack_dir.glob("*.md"))
        resolved.append({"name": name, "files": files})

    return {
        "requested": requested_rules,
        "resolved": resolved,
        "missing": missing,
        "valid": not missing,
    }
