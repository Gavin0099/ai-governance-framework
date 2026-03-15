#!/usr/bin/env python3
"""
Check release-facing documentation readiness for the current repository state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.human_summary import build_summary_line


def assess_release_readiness(project_root: Path, *, version: str) -> dict:
    readme_path = project_root / "README.md"
    changelog_path = project_root / "CHANGELOG.md"
    release_note_path = project_root / "docs" / "releases" / f"{version}.md"
    alpha_checklist_path = project_root / "docs" / "releases" / "alpha-checklist.md"
    limitations_path = project_root / "docs" / "LIMITATIONS.md"
    status_path = project_root / "docs" / "status" / "runtime-governance-status.md"

    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, object]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            errors.append(f"{name}: {detail}")

    add_check("release_note", release_note_path.is_file(), "missing docs/releases release note")
    add_check("alpha_checklist", alpha_checklist_path.is_file(), "missing docs/releases/alpha-checklist.md")
    add_check("changelog", changelog_path.is_file(), "missing CHANGELOG.md")
    add_check("limitations", limitations_path.is_file(), "missing docs/LIMITATIONS.md")
    add_check("status_doc", status_path.is_file(), "missing runtime-governance status doc")

    readme_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    changelog_text = changelog_path.read_text(encoding="utf-8") if changelog_path.is_file() else ""
    release_note_text = release_note_path.read_text(encoding="utf-8") if release_note_path.is_file() else ""
    alpha_checklist_text = alpha_checklist_path.read_text(encoding="utf-8") if alpha_checklist_path.is_file() else ""

    add_check("readme_exists", readme_path.is_file(), "missing README.md")
    if readme_text:
        add_check(
            "readme_version_badge",
            version.replace("v", "") in readme_text,
            "README.md does not mention the current release version",
        )
        add_check(
            "readme_release_link",
            f"docs/releases/{version}.md" in readme_text,
            "README.md does not link to the current release note",
        )
        if "prototype" not in readme_text.lower():
            warnings.append("README.md no longer mentions the prototype boundary")

    if changelog_text:
        add_check(
            "changelog_version_entry",
            re.search(rf"^##\s+{re.escape(version)}\b", changelog_text, re.MULTILINE) is not None,
            "CHANGELOG.md does not contain a heading for the requested version",
        )
        add_check(
            "changelog_release_link",
            f"docs/releases/{version}.md" in changelog_text,
            "CHANGELOG.md does not link to the release note",
        )

    if release_note_text:
        add_check(
            "release_note_version_heading",
            re.search(rf"^#\s+{re.escape(version)}\b", release_note_text, re.MULTILINE) is not None,
            "release note heading does not match the requested version",
        )
        if "Known Limits" not in release_note_text:
            warnings.append("Release note is missing a 'Known Limits' section")
        if "Supported AI Adapter" not in release_note_text and "Supported AI Adapter Surfaces" not in release_note_text:
            warnings.append("Release note is missing adapter coverage information")

    if alpha_checklist_text:
        add_check(
            "alpha_checklist_version",
            version in alpha_checklist_text,
            "alpha checklist does not mention the requested version",
        )
        add_check(
            "alpha_checklist_quickstart",
            "quickstart_smoke.py" in alpha_checklist_text,
            "alpha checklist does not mention quickstart verification",
        )
        add_check(
            "alpha_checklist_auditor",
            "governance_auditor.py" in alpha_checklist_text,
            "alpha checklist does not mention governance self-audit",
        )

    return {
        "ok": len(errors) == 0,
        "project_root": str(project_root),
        "version": version,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "paths": {
            "readme": str(readme_path),
            "changelog": str(changelog_path),
            "release_note": str(release_note_path),
            "alpha_checklist": str(alpha_checklist_path),
            "limitations": str(limitations_path),
            "status_doc": str(status_path),
        },
    }


def format_human_result(result: dict) -> str:
    lines = [
        "[release_readiness]",
        build_summary_line(
            f"ok={result['ok']}",
            f"version={result['version']}",
            f"checks={len(result['checks'])}",
            f"warnings={len(result['warnings'])}",
            f"errors={len(result['errors'])}",
        ),
        f"ok={result['ok']}",
        f"version={result['version']}",
    ]
    for check in result["checks"]:
        lines.append(f"check[{check['name']}]={check['ok']}")
    for warning in result["warnings"]:
        lines.append(f"warning: {warning}")
    for error in result["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release-facing documentation readiness.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--version", required=True)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    result = assess_release_readiness(Path(args.project_root).resolve(), version=args.version)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
