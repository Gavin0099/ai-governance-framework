#!/usr/bin/env python3
"""
Suggest rule packs from repository signals and optional task metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from governance_tools.rule_pack_loader import DEFAULT_RULES_ROOT, available_rule_packs


LANGUAGE_ORDER = ("csharp", "swift", "objective-c", "cpp", "python")

LANGUAGE_STRONG_PATH_PATTERNS = {
    "csharp": [r"\.csproj$"],
    "swift": [r"(?:^|/)Package\.swift$"],
    "objective-c": [],
    "cpp": [r"\.vcxproj$"],
    "python": [r"(?:^|/)pyproject\.toml$", r"(?:^|/)requirements\.txt$"],
}

LANGUAGE_SOURCE_PATTERNS = {
    "csharp": [r"\.cs$"],
    "swift": [r"\.swift$"],
    "objective-c": [r"\.m$", r"\.mm$"],
    "cpp": [r"\.cpp$", r"\.cc$", r"\.cxx$", r"\.hpp$"],
    "python": [r"\.py$"],
}

_SOLUTION_PROJECT_RE = re.compile(
    r'^\s*Project\([^)]*\)\s*=\s*"[^"]*"\s*,\s*"[^"]+\.(csproj|vcxproj)"',
    re.IGNORECASE | re.MULTILINE,
)
_MEDIUM_LANGUAGE_MIN_FILES = 3
_MEDIUM_LANGUAGE_MIN_SHARE = 0.05
_MEDIUM_LANGUAGE_DOMINANT_SHARE = 0.50

FRAMEWORK_SIGNAL_PATTERNS = [
    ("avalonia", [r"Avalonia", r"Avalonia\.Headless", r"Dispatcher\.UIThread"]),
    ("electron", [r"electron", r"BrowserWindow", r"ipcMain", r"ipcRenderer", r"preload"]),
]

# These roots carry documentation, fixtures, generated evidence, or copied
# framework internals rather than the consumer project's product language.
# Including them made a real Codex pilot and prior Enumd/Hearth checks suggest
# unrelated language/framework packs.
_NON_PRODUCT_SIGNAL_ROOTS = {
    "archive",
    "tests",
    "artifacts",
    "docs",
    "examples",
    "fixtures",
    "ai-governance-framework",
}


def _is_non_product_signal_path(path: Path, project_root: Path) -> bool:
    relative_parts = path.relative_to(project_root).parts
    if not relative_parts:
        return False
    # Fixture/example trees may be nested under runtime or an embedded
    # framework. Dot-prefixed directories are tool metadata or scratch space,
    # not product source; `.git` is included by that same boundary.
    return any(
        part in _NON_PRODUCT_SIGNAL_ROOTS
        or part.startswith(".")
        for part in relative_parts
    )

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

SKILL_SIGNAL_PATTERNS = {
    "human-readable-cli": [
        r"\bcli\b",
        r"--format human",
        r"\bhuman output\b",
        r"\bcommand[- ]line\b",
        r"\bdeveloper-facing\b",
    ],
    "governance-runtime": [
        r"\bgovernance\b",
        r"\bruntime\b",
        r"\bvalidator\b",
        r"\bevidence\b",
        r"\baudit\b",
        r"\bhook\b",
    ],
}


def _parse_contract_yaml_minimal(text: str) -> dict:
    """Minimal stdlib-only contract.yaml parser — flat key-value and list items only."""
    data: dict = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        stripped = raw_line.lstrip("\ufeff").strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line[:len(raw_line) - len(raw_line.lstrip(" "))]:
            if current_list_key and stripped.startswith("- "):
                value = stripped[2:].strip().strip("'\"")
                data.setdefault(current_list_key, [])
                cast = data[current_list_key]
                if isinstance(cast, list):
                    cast.append(value)
            continue
        current_list_key = None
        if ":" not in stripped:
            continue
        key, _, raw_value = stripped.partition(":")
        key = key.strip().lstrip("\ufeff")
        value = raw_value.strip().strip("'\"")
        if not value or value == "[]":
            data[key] = []
            current_list_key = key
        else:
            data[key] = value
    return data


def _detect_domain_contract(project_root: Path) -> list[dict]:
    """Read contract.yaml and return domain pack suggestions sourced from rule_roots and domain."""
    contract_path = project_root / "contract.yaml"
    if not contract_path.exists():
        return []
    try:
        text = contract_path.read_text(encoding="utf-8", errors="ignore")
        data = _parse_contract_yaml_minimal(text)
    except OSError:
        return []
    domain = data.get("domain", "")
    rule_roots = data.get("rule_roots", [])
    if not domain and not rule_roots:
        return []
    suggestions = []
    if domain and isinstance(domain, str):
        reasons = [f"contract.yaml: domain={domain}"]
        if isinstance(rule_roots, list):
            reasons += [f"contract.yaml rule_root: {r}" for r in rule_roots[:3]]
        suggestions.append(
            {
                "name": domain,
                "category": "domain",
                "confidence": "high",
                "reasons": reasons,
            }
        )
    return suggestions


def _file_sort_key(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix().casefold()


def _git_visible_files(project_root: Path) -> list[Path] | None:
    """Return Git-visible files when project_root is the worktree root.

    Tracked files and untracked, non-ignored files are both product candidates.
    A directory merely nested inside another repository must use the filesystem
    fallback so parent-repo ignore rules do not hide onboarding/test fixtures.
    """
    try:
        root_probe = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if root_probe.returncode != 0 or not root_probe.stdout.strip():
        return None
    if Path(root_probe.stdout.strip()).resolve() != project_root.resolve():
        return None

    try:
        visible = subprocess.run(
            ["git", "-C", str(project_root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if visible.returncode != 0:
        return None

    resolved_root = project_root.resolve()
    files: list[Path] = []
    for raw_path in visible.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = project_root / Path(os.fsdecode(raw_path))
        try:
            path.resolve().relative_to(resolved_root)
        except ValueError:
            continue
        if path.is_file() and not _is_non_product_signal_path(path, project_root):
            files.append(path)
    return sorted(files, key=lambda path: _file_sort_key(path, project_root))


def _iter_files(project_root: Path) -> list[Path]:
    git_visible = _git_visible_files(project_root)
    if git_visible is not None:
        return git_visible

    files = [
        path
        for path in project_root.rglob("*")
        if path.is_file() and not _is_non_product_signal_path(path, project_root)
    ]
    return sorted(files, key=lambda path: _file_sort_key(path, project_root))


def _filter_language_signal_files(files: list[Path], project_root: Path) -> list[Path]:
    if not (project_root / "contract.yaml").exists():
        return files

    ignored_roots = {"validators", "fixtures", "memory"}
    filtered = []
    for path in files:
        rel_parts = path.relative_to(project_root).parts
        if rel_parts and rel_parts[0] in ignored_roots:
            continue
        filtered.append(path)
    return filtered


def _matching_paths(rel_paths: list[str], patterns: list[str]) -> list[str]:
    return [
        rel_path
        for rel_path in rel_paths
        if any(re.search(pattern, rel_path, re.IGNORECASE) for pattern in patterns)
    ]


def _solution_project_signals(files: list[Path], project_root: Path) -> dict[str, list[str]]:
    signals = {"csharp": [], "cpp": []}
    for path in files:
        if path.suffix.lower() != ".sln":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        project_types = {match.group(1).lower() for match in _SOLUTION_PROJECT_RE.finditer(text)}
        rel_path = path.relative_to(project_root).as_posix()
        if "csproj" in project_types:
            signals["csharp"].append(rel_path)
        if "vcxproj" in project_types:
            signals["cpp"].append(rel_path)
    return signals


def _language_confidence(strong_matches: list[str], source_count: int, total_source_files: int) -> str:
    if strong_matches:
        return "high"
    share = source_count / total_source_files if total_source_files else 0.0
    if share >= _MEDIUM_LANGUAGE_DOMINANT_SHARE:
        return "medium"
    if source_count >= _MEDIUM_LANGUAGE_MIN_FILES and share >= _MEDIUM_LANGUAGE_MIN_SHARE:
        return "medium"
    return "low"


def _detect_languages(files: list[Path], project_root: Path) -> list[dict]:
    suggestions = []
    signal_files = _filter_language_signal_files(files, project_root)
    rel_paths = [path.relative_to(project_root).as_posix() for path in signal_files]
    source_matches = {
        pack: _matching_paths(rel_paths, LANGUAGE_SOURCE_PATTERNS[pack])
        for pack in LANGUAGE_ORDER
    }
    language_source_files = {
        rel_path
        for matches in source_matches.values()
        for rel_path in matches
    }
    total_source_files = len(language_source_files)
    solution_signals = _solution_project_signals(signal_files, project_root)
    header_paths = _matching_paths(rel_paths, [r"\.h$"])

    for pack in LANGUAGE_ORDER:
        strong_matches = _matching_paths(rel_paths, LANGUAGE_STRONG_PATH_PATTERNS[pack])
        strong_matches.extend(solution_signals.get(pack, []))
        matched_sources = source_matches[pack]
        if not strong_matches and not matched_sources:
            continue

        reasons = list(dict.fromkeys(strong_matches + matched_sources))
        if pack in {"cpp", "objective-c"} and header_paths:
            # `.h` is supporting evidence only after an unambiguous language
            # source or project signal establishes the companion language.
            reasons.extend(path for path in header_paths if path not in reasons)
        confidence = _language_confidence(strong_matches, len(matched_sources), total_source_files)
        suggestion = {
            "name": pack,
            "category": "language",
            "confidence": confidence,
            "reasons": reasons[:5],
        }
        if confidence == "low":
            suggestion["advisory_only"] = True
        suggestions.append(suggestion)
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


def _suggest_skills(language_packs: list[dict], framework_packs: list[dict], task_text: str) -> list[str]:
    skills = ["code-style", "governance-runtime"]

    if any(item["name"] == "python" and item.get("confidence") != "low" for item in language_packs):
        skills.append("python")

    matched_cli = [pattern for pattern in SKILL_SIGNAL_PATTERNS["human-readable-cli"] if re.search(pattern, task_text, re.IGNORECASE)]
    if matched_cli:
        skills.append("human-readable-cli")

    deduped = []
    for item in skills:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _suggest_agent(language_packs: list[dict], suggested_skills: list[str], task_text: str) -> str:
    if "human-readable-cli" in suggested_skills:
        return "cli-agent"
    if any(item["name"] == "python" and item.get("confidence") != "low" for item in language_packs):
        return "python-agent"
    return "advanced-agent"


def _suggested_rules_preview(
    language_packs: list[dict],
    framework_packs: list[dict],
    scope_packs: list[dict],
    domain_packs: list[dict] | None = None,
) -> list[str]:
    preview = ["common"]

    for item in (domain_packs or []) + language_packs + framework_packs + scope_packs:
        if item["name"] not in preview:
            preview.append(item["name"])

    return preview


def _loadable_pack_names(project_root: Path, domain_packs: list[dict]) -> set[str]:
    """Pack names that the loader can actually resolve for this project.

    Mirrors the pre_task_check selection roots: the contract's rule_roots
    (relative to the project) plus the framework's default rules root. A name
    outside this set would fail describe_rule_selection with
    "Unknown rule packs", so it must never be suggested as loadable.
    """
    roots: list[Path] = [DEFAULT_RULES_ROOT]
    for pack in domain_packs:
        for reason in pack.get("reasons", []):
            marker = "contract.yaml rule_root: "
            if reason.startswith(marker):
                roots.append(project_root / reason[len(marker):])
    return available_rule_packs(roots)


def suggest_rule_packs(project_root: Path, task_text: str = "") -> dict:
    files = _iter_files(project_root)
    language_packs = _detect_languages(files, project_root)
    framework_packs = _detect_frameworks(files, project_root)
    scope_packs = _suggest_scope(task_text)
    domain_packs = _detect_domain_contract(project_root)
    suggested_skills = _suggest_skills(language_packs, framework_packs, task_text)
    suggested_agent = _suggest_agent(language_packs, suggested_skills, task_text)

    loadable = _loadable_pack_names(project_root, domain_packs)
    detected_items = domain_packs + language_packs + framework_packs
    detected = ["common"] + [item["name"] for item in detected_items]
    recommendable = ["common"] + [
        item["name"]
        for item in detected_items
        if item.get("confidence") != "low"
    ]
    suggested_rules = [name for name in recommendable if name in loadable or name == "common"]
    unloadable = sorted({name for name in detected if name not in loadable and name != "common"})
    preview_all = _suggested_rules_preview(language_packs, framework_packs, scope_packs, domain_packs)
    preview = [name for name in preview_all if name in loadable or name == "common" or name in {p["name"] for p in scope_packs}]

    return {
        "project_root": str(project_root),
        "language_packs": language_packs,
        "framework_packs": framework_packs,
        "scope_packs": scope_packs,
        "domain_packs": domain_packs,
        "suggested_skills": suggested_skills,
        "suggested_agent": suggested_agent,
        "suggested_rules": suggested_rules,
        "suggested_rules_preview": preview,
        "unloadable_signals": unloadable,
        "notes": [
            "domain_packs are sourced from contract.yaml rule_roots and take highest priority",
            "language packs use language-specific structural signals before count/share source-file confidence",
            "low-confidence language packs remain advisory preview evidence and do not affect suggested rules, skills, or agents",
            "framework packs are auto-suggested from repository signals",
            "scope packs are advisory only and should be confirmed by the contract or human reviewer",
            "suggested_rules_preview includes advisory scope packs for convenience, but does not mutate the contract",
            "suggested_skills and suggested_agent are advisory only and do not auto-activate agent behavior",
            "suggested_rules and suggested_rules_preview only carry pack names the loader can resolve; detected-but-unloadable names are reported in unloadable_signals instead of being suggested",
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
        print("suggested_rules_preview=" + ",".join(result["suggested_rules_preview"]))
        print("suggested_skills=" + ",".join(result["suggested_skills"]))
        print("suggested_agent=" + result["suggested_agent"])
        for group in ("domain_packs", "language_packs", "framework_packs", "scope_packs"):
            for item in result[group]:
                advisory = " advisory-only" if item.get("advisory_only") else ""
                print(f"{group}:{item['name']} [{item['confidence']}{advisory}]")
                for reason in item["reasons"]:
                    print(f"  - {reason}")


if __name__ == "__main__":
    main()
