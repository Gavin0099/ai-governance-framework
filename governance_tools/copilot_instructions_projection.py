#!/usr/bin/env python3
"""
Project the canonical Governance Contract checkpoint rules into every agent
instruction surface.

`governance/SYSTEM_PROMPT.md` §2.8 is the single source of truth for when a
`[Governance Contract]` block must be emitted. Agents receive those rules by
reading their own instruction file at session start — not by hook injection; the
Copilot session_start hook returns no `additionalContext` and never has. Each
agent reads a different markdown file, so cross-agent parity means projecting the
same canonical section into each of them:

    governance/copilot-instructions-template.md   -> GitHub Copilot
    AGENTS.md                                     -> Codex

The copy is a projection, not a second source of truth: `--check` recomputes the
section and its digest from SYSTEM_PROMPT.md and fails when a surface has
drifted. Validators read the header token instead of grepping prose, so an
installed surface can be checked without matching natural-language wording.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence


CHECKPOINT_PROJECTION_VERSION = "1.1"
CANONICAL_SOURCE_REL = "governance/SYSTEM_PROMPT.md"
CANONICAL_SECTION_ID = "2.8"
CANONICAL_SECTION_HEADING = "### 2.8 Governance Contract Output"
TEMPLATE_REL = "governance/copilot-instructions-template.md"

# Every agent surface that must carry the canonical checkpoint rules.
#
# The rules reach an agent by being in the file it reads at session start, not
# by hook injection — the Copilot session_start hook returns no additionalContext
# and never has. Each agent reads a different markdown file, so parity is a
# matter of projecting into each of them, not of four different hook APIs.
PROJECTION_TARGETS: tuple[tuple[str, str], ...] = (
    (TEMPLATE_REL, "copilot"),
    ("AGENTS.md", "codex"),
)

PROJECTION_BEGIN_PREFIX = "<!-- ai-governance:checkpoint-projection BEGIN"
PROJECTION_END = "<!-- ai-governance:checkpoint-projection END -->"

_HEADER_PATTERN = re.compile(
    r"^<!-- ai-governance:checkpoint-projection BEGIN"
    r" version=(?P<version>\S+)"
    r" source=(?P<source>\S+)"
    r" sha256=(?P<sha256>[0-9a-f]{64}) -->$"
)
_SECTION_BOUNDARY = re.compile(r"^(#{2,3} |---\s*$)")


@dataclass
class ProjectionCheckResult:
    ok: bool
    framework_root: str
    template_path: str
    canonical_source: str
    expected_version: str
    surface: str | None = None
    found_version: str | None = None
    expected_sha256: str | None = None
    found_sha256: str | None = None
    drift: bool = False
    written: bool = False
    errors: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_canonical_section(system_prompt_text: str) -> str:
    """Return §2.8 verbatim, from its heading to the next section boundary."""
    lines = _normalize(system_prompt_text).split("\n")
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == CANONICAL_SECTION_HEADING
        )
    except StopIteration as exc:  # pragma: no cover - guarded by caller
        raise ValueError(
            f"canonical section not found in {CANONICAL_SOURCE_REL}: {CANONICAL_SECTION_HEADING}"
        ) from exc

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _SECTION_BOUNDARY.match(lines[index]):
            end = index
            break

    section = "\n".join(lines[start:end]).rstrip()
    if not section:
        raise ValueError(f"canonical section is empty: {CANONICAL_SECTION_HEADING}")
    return section


def section_digest(section_text: str) -> str:
    return hashlib.sha256(_normalize(section_text).rstrip().encode("utf-8")).hexdigest()


def render_projection_block(section_text: str) -> str:
    digest = section_digest(section_text)
    header = (
        f"{PROJECTION_BEGIN_PREFIX}"
        f" version={CHECKPOINT_PROJECTION_VERSION}"
        f" source={CANONICAL_SOURCE_REL}#{CANONICAL_SECTION_ID}"
        f" sha256={digest} -->"
    )
    body = _normalize(section_text).rstrip()
    return f"{header}\n{body}\n{PROJECTION_END}"


def canonical_source_token() -> str:
    return f"{CANONICAL_SOURCE_REL}#{CANONICAL_SECTION_ID}"


def parse_projection_header(text: str) -> dict[str, str] | None:
    """Return the machine-readable projection header fields, or None when absent.

    Validators use this instead of matching checkpoint wording: the version and
    digest are exact tokens, prose is not. The header alone is not evidence that
    the rules are present — pair it with `extract_projection_region`, which
    recomputes the digest of the body that actually shipped.
    """
    for line in _normalize(text).split("\n"):
        match = _HEADER_PATTERN.match(line.strip())
        if match:
            return dict(match.groupdict())
    return None


def extract_projection_region(text: str) -> tuple[dict[str, str], str, int, int]:
    """Return (header fields, body, begin line index, end line index).

    Raises ValueError when the region is missing, duplicated, out of order, or
    carries a malformed header.
    """
    lines = _normalize(text).split("\n")
    begins = [i for i, line in enumerate(lines) if line.strip().startswith(PROJECTION_BEGIN_PREFIX)]
    ends = [i for i, line in enumerate(lines) if line.strip() == PROJECTION_END]
    if len(begins) != 1 or len(ends) != 1:
        raise ValueError(
            f"expected exactly one checkpoint projection region "
            f"(found {len(begins)} BEGIN / {len(ends)} END markers)"
        )
    if ends[0] < begins[0]:
        raise ValueError("checkpoint projection END marker precedes BEGIN marker")

    match = _HEADER_PATTERN.match(lines[begins[0]].strip())
    if match is None:
        raise ValueError("checkpoint projection header is malformed")

    body = "\n".join(lines[begins[0] + 1 : ends[0]]).rstrip()
    return dict(match.groupdict()), body, begins[0], ends[0]


def _projection_bounds(template_text: str) -> tuple[int, int]:
    lines = _normalize(template_text).split("\n")
    begins = [i for i, line in enumerate(lines) if line.startswith(PROJECTION_BEGIN_PREFIX)]
    ends = [i for i, line in enumerate(lines) if line.strip() == PROJECTION_END]
    if len(begins) != 1 or len(ends) != 1:
        raise ValueError(
            f"template must contain exactly one checkpoint projection region "
            f"(found {len(begins)} BEGIN / {len(ends)} END markers)"
        )
    if ends[0] < begins[0]:
        raise ValueError("checkpoint projection END marker precedes BEGIN marker")
    return begins[0], ends[0]


def render_template(template_text: str, system_prompt_text: str) -> str:
    """Return the template with its projection region regenerated from canon."""
    lines = _normalize(template_text).split("\n")
    begin, end = _projection_bounds(template_text)
    block = render_projection_block(extract_canonical_section(system_prompt_text)).split("\n")
    rendered = "\n".join(lines[:begin] + block + lines[end + 1 :])
    return rendered if rendered.endswith("\n") else rendered + "\n"


def check_all_projections(
    framework_root: Path,
    *,
    write: bool = False,
) -> list[ProjectionCheckResult]:
    """Check every agent surface that must carry the canonical checkpoint rules.

    A surface listed in PROJECTION_TARGETS but missing its projection region is
    an error, not a skip: an agent reading a file with no rules emits no contract,
    which is the parity gap this exists to close.
    """
    return [
        check_projection(framework_root, template_rel=relative_path, surface=surface, write=write)
        for relative_path, surface in PROJECTION_TARGETS
    ]


def check_projection(
    framework_root: Path,
    *,
    template_rel: str = TEMPLATE_REL,
    surface: str | None = None,
    write: bool = False,
) -> ProjectionCheckResult:
    framework_root = framework_root.resolve()
    template_path = framework_root / template_rel
    source_path = framework_root / CANONICAL_SOURCE_REL
    result = ProjectionCheckResult(
        ok=False,
        framework_root=str(framework_root),
        template_path=str(template_path),
        surface=surface,
        canonical_source=str(source_path),
        expected_version=CHECKPOINT_PROJECTION_VERSION,
    )

    if not source_path.is_file():
        result.errors.append(f"missing canonical source: {source_path}")
    if not template_path.is_file():
        result.errors.append(f"missing template: {template_path}")
    if result.errors:
        return result

    try:
        section = extract_canonical_section(source_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        result.errors.append(str(exc))
        return result

    result.expected_sha256 = section_digest(section)
    template_text = template_path.read_text(encoding="utf-8")
    header = parse_projection_header(template_text)
    if header:
        result.found_version = header["version"]
        result.found_sha256 = header["sha256"]

    try:
        rendered = render_template(template_text, source_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        result.errors.append(str(exc))
        return result

    current = _normalize(template_text)
    if not current.endswith("\n"):
        current += "\n"
    result.drift = rendered != current

    if result.drift and write:
        template_path.write_text(rendered, encoding="utf-8", newline="\n")
        result.written = True
        result.drift = False
        result.found_version = CHECKPOINT_PROJECTION_VERSION
        result.found_sha256 = result.expected_sha256
    elif result.drift:
        result.errors.append(
            f"copilot instructions template has drifted from {CANONICAL_SOURCE_REL}"
            f"#{CANONICAL_SECTION_ID}; re-run with --write"
        )

    result.ok = not result.errors
    return result


def format_human(result: ProjectionCheckResult) -> str:
    lines = [
        "Copilot Checkpoint Projection",
        "",
        f"ok               = {result.ok}",
        f"drift            = {result.drift}",
        f"written          = {result.written}",
        f"surface          = {result.surface or '(default)'}",
        f"template         = {result.template_path}",
        f"canonical_source = {result.canonical_source}",
        f"expected_version = {result.expected_version}",
        f"found_version    = {result.found_version or '<missing>'}",
        f"expected_sha256  = {result.expected_sha256 or '<unknown>'}",
        f"found_sha256     = {result.found_sha256 or '<missing>'}",
    ]
    if result.errors:
        lines.append("")
        lines.append(f"errors: {len(result.errors)}")
        lines.extend(f"- {item}" for item in result.errors)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check or regenerate the canonical checkpoint projection inside "
            "governance/copilot-instructions-template.md."
        )
    )
    parser.add_argument("--framework-root", default=".", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing (the default).",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Rewrite the template projection region when it has drifted.",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = check_all_projections(args.framework_root, write=args.write)
    if args.format == "json":
        print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(format_human(item) for item in results))
    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
