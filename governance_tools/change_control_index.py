#!/usr/bin/env python3
"""
Build an index over generated change-control artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _extract_summary_line(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("summary="):
            return line
    return None


def build_change_control_index(artifacts_dir: Path) -> str:
    summary_files = sorted(artifacts_dir.glob("*_change_control_summary.txt"))
    session_files = sorted(artifacts_dir.glob("*_session_start.txt"))
    json_files = sorted(artifacts_dir.glob("*_session_start.json"))

    lines = ["[change_control_index]", f"artifacts_dir={artifacts_dir}"]
    lines.append(
        "summary="
        + " | ".join(
            [
                f"change_control_summaries={len(summary_files)}",
                f"session_start_notes={len(session_files)}",
                f"session_start_envelopes={len(json_files)}",
            ]
        )
    )
    lines.append("[review_order]")
    lines.append("1. read *_change_control_summary.txt")
    lines.append("2. inspect *_session_start.txt if proposal/startup context needs more detail")
    lines.append("3. inspect *_session_start.json for machine-readable detail")

    if summary_files:
        lines.append("[change_control_summaries]")
        for path in summary_files:
            summary_line = _extract_summary_line(path)
            if summary_line:
                lines.append(f"{path.name} | {summary_line}")
            else:
                lines.append(path.name)

    if session_files:
        lines.append("[session_start_notes]")
        for path in session_files:
            lines.append(path.name)

    if json_files:
        lines.append("[session_start_envelopes]")
        for path in json_files:
            lines.append(path.name)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an index for change-control artifacts.")
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    rendered = build_change_control_index(Path(args.artifacts_dir))
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
