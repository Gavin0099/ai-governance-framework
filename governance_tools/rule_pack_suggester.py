#!/usr/bin/env python3
"""
Suggest rule packs from repository signals and optional task metadata.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LANGUAGE_SIGNALS = [
    ("csharp", [r"\.csproj$", r"\.cs$", r"\.sln$"]),
    ("swift", [r"Package\.swift$", r"\.swift$"]),
    ("objective-c", [r"\.m$", r"\.mm$", r"\.h$", r"\.xcodeproj$"]),
    ("cpp", [r"\.vcxproj$", r"\.cpp$", r"\.cc$", r"\.cxx$", r"\.hpp$", r"\.h$"]),
    ("python", [r"\.py$", r"pyproject\.toml$", r"requirements\.txt$"]),
]

FRAMEWORK_SIGNAL_PATTERNS = [
    ("avalonia", [r"Avalonia", r"Avalonia\.Headless", r"Dispatcher\.UIThread"]),
    ("electron", [r"electron", r"BrowserWindow", r"ipcMain", r"ipcRenderer", r"preload"]),
]

SCOPE_SIGNAL_PATTERNS = {
    "refactor": [
        r"\brefactor\b",
        r"\brename\b",
        r"\bextract\b",
        r"\bmove\b",
        r"\brestructure\b",
    ],
    "release": [
        r"\brelease\b",
        r"\bversion\b",
        r"\bpackage\b",
        r"\bdeploy\b",
    ],
}


def _iter_files(project_root: Path) -> list[Path]:
    return [path for path in project_root.rglob("*") if path.is_file() and ".git" not in path.parts]


def _detect_languages(files: list[Path], project_root: Path) -> list[dict]:
    suggestions = []
    rel_paths = [str(path.relative_to(project_root)).replace("\\", "/") for path in files]

    for pack, patterns in LANGUAGE_SIGNALS:
        matched = []
        for rel_path in rel_paths:
            if any(re.search(pattern, rel_path, re.IGNORECASE) for pattern in patterns):
                matched.append(rel_path)
        if matched:
            suggestions.append(
                {
                    "name": pack,
                    "category": "language",
                    "confidence": "high",
                    "reasons": matched[:5],
                }
            )
    return suggestions


def _detect_frameworks(files: list[Path], project_root: Path) -> list[dict]:
    suggestions = []
    text_files = []
    for path in files:
        if path.suffix.lower() in {".cs", ".fs", ".vb", ".swift", ".m", ".mm", ".h", ".js", ".ts", ".tsx", ".json", ".toml", ".xml", ".props", ".targets", ".csproj", ".vcxproj"}:
            text_files.append(path)

    joined_preview = []
    for path in text_files[:50]:
        try:
            joined_preview.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    corpus = "\n".join(joined_preview)

    for pack, patterns in FRAMEWORK_SIGNAL_PATTERNS:
        matched = [pattern for pattern in patterns if re.search(pattern, corpus, re.IGNORECASE)]
        if matched:
            suggestions.append(
                {
                    "name": pack,
                    "category": "framework",
                    "confidence": "medium",
                    "reasons": matched,
                }
            )
    return suggestions


def _suggest_scope(task_text: str) -> list[dict]:
    if not task_text.strip():
        return []

    suggestions = []
    for pack, patterns in SCOPE_SIGNAL_PATTERNS.items():
        matched = [pattern for pattern in patterns if re.search(pattern, task_text, re.IGNORECASE)]
        if matched:
            suggestions.append(
                {
                    "name": pack,
                    "category": "scope",
                    "confidence": "low",
                    "reasons": matched,
                    "advisory_only": True,
                }
            )
    return suggestions


def suggest_rule_packs(project_root: Path, task_text: str = "") -> dict:
    files = _iter_files(project_root)
    language_packs = _detect_languages(files, project_root)
    framework_packs = _detect_frameworks(files, project_root)
    scope_packs = _suggest_scope(task_text)

    return {
        "project_root": str(project_root),
        "language_packs": language_packs,
        "framework_packs": framework_packs,
        "scope_packs": scope_packs,
        "suggested_rules": ["common"] + [item["name"] for item in language_packs + framework_packs],
        "notes": [
            "language/framework packs are auto-suggested from repository signals",
            "scope packs are advisory only and should be confirmed by the contract or human reviewer",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest rule packs from repository signals.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--task", default="")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    result = suggest_rule_packs(Path(args.project_root).resolve(), task_text=args.task)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("suggested_rules=" + ",".join(result["suggested_rules"]))
        for group in ("language_packs", "framework_packs", "scope_packs"):
            for item in result[group]:
                advisory = " advisory-only" if item.get("advisory_only") else ""
                print(f"{group}:{item['name']} [{item['confidence']}{advisory}]")
                for reason in item["reasons"]:
                    print(f"  - {reason}")


if __name__ == "__main__":
    main()
