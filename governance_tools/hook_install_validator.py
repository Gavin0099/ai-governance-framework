#!/usr/bin/env python3
"""
Validate whether AI Governance git hooks are installed correctly for a target repo.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from governance_tools.copilot_instructions_projection import (
    CHECKPOINT_PROJECTION_VERSION,
    CANONICAL_SOURCE_REL,
    canonical_source_token,
    extract_canonical_section,
    extract_projection_region,
    section_digest,
)


FRAMEWORK_MARKER = "AI Governance Framework"
COPILOT_INSTRUCTIONS_MARKER = "AI Governance Framework: copilot-instructions"
COPILOT_BLOCK_BEGIN = "<!-- AI Governance Framework: copilot-instructions BEGIN -->"
COPILOT_BLOCK_END = "<!-- AI Governance Framework: copilot-instructions END -->"
COPILOT_LIFECYCLE_MARKER = "Thin lifecycle bridge for VS Code and GitHub Copilot hooks."
COPILOT_HOOK_COMMAND_MARKER = "ai-governance-lifecycle.py"
REQUIRED_FRAMEWORK_FILES = [
    "scripts/lib/python.sh",
    "scripts/run-runtime-governance.sh",
    "governance_tools/plan_freshness.py",
    "governance_tools/contract_validator.py",
]


@dataclass
class HookInstallResult:
    valid: bool
    repo_root: str
    hook_dir: str
    framework_root: str | None
    checks: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _contains_marker(path: Path, marker: str) -> bool:
    if not path.is_file():
        return False
    try:
        return marker in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _contains_framework_marker(path: Path) -> bool:
    return _contains_marker(path, FRAMEWORK_MARKER)


def _command_option(tokens: list[str], option: str) -> str | None:
    try:
        index = tokens.index(option)
    except ValueError:
        return None
    if index + 1 >= len(tokens):
        return None
    return tokens[index + 1]


def _managed_copilot_hook_config(
    path: Path,
    expected_events: dict[str, tuple[str, str]],
) -> bool:
    """Check that the config declares exactly the managed events, wired correctly.

    The set is exact on purpose. VS Code loads every `*.json` under
    `.github/hooks/` and converts the Copilot config's lowerCamelCase names to
    PascalCase, so `sessionStart` there is already VS Code's start handler.
    Declaring `SessionStart` in the VS Code config as well registers a second
    handler for the same boundary and writes the session envelope twice, so an
    extra event is a defect to report rather than a variation to tolerate.
    """
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    hooks = payload.get("hooks")
    if payload.get("version") != 1 or not isinstance(hooks, dict):
        return False
    if set(hooks) != set(expected_events):
        return False
    for event_name, (expected_event_type, expected_surface) in expected_events.items():
        entries = hooks.get(event_name)
        if not isinstance(entries, list) or len(entries) != 1:
            return False
        entry = entries[0]
        if not isinstance(entry, dict) or entry.get("type") != "command":
            return False
        command = str(entry.get("command", ""))
        try:
            tokens = shlex.split(command)
        except ValueError:
            return False
        if (
            COPILOT_HOOK_COMMAND_MARKER not in command
            or _command_option(tokens, "--event-type") != expected_event_type
            or _command_option(tokens, "--surface") != expected_surface
        ):
            return False
    return True


def _normalize_framework_root(raw_value: str) -> Path:
    """Accept Windows-native paths and Git Bash/MSYS paths like /e/work/repo."""
    candidate = raw_value.strip().lstrip("\ufeff")
    msys_match = re.match(r"^/([a-zA-Z])/(.*)$", candidate)
    if msys_match:
        drive = msys_match.group(1).upper()
        remainder = msys_match.group(2).replace("/", "\\")
        return Path(f"{drive}:\\{remainder}").expanduser()
    return Path(candidate).expanduser()


def _resolve_hook_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git / "hooks"
    if not dot_git.is_file():
        return dot_git / "hooks"

    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repo_root.as_posix()}",
            "-C",
            str(repo_root),
            "rev-parse",
            "--git-common-dir",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    common_dir = (completed.stdout or "").strip()
    if completed.returncode == 0 and common_dir:
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = repo_root / common_path
        return common_path.resolve() / "hooks"
    return repo_root / ".git" / "hooks"


_PROJECTION_CHECK_KEYS = (
    "copilot_instructions_managed_block_unique",
    "copilot_checkpoint_projection_present",
    "copilot_checkpoint_projection_inside_managed_block",
    "copilot_checkpoint_source_expected",
    "copilot_checkpoint_version_current",
    "copilot_checkpoint_body_matches_header",
    "copilot_checkpoint_matches_canonical",
)


def _check_copilot_instructions_projection(
    instructions_path: Path,
    framework_root: Path | None,
    checks: dict[str, bool],
    warnings: list[str],
) -> None:
    """Report-only checks on the installed Copilot instructions.

    The projection header is a claim, not evidence: the digest of the body that
    actually shipped is recomputed and compared against both the header and the
    canonical section. Nothing here matches checkpoint wording — prose is not a
    reliable signal that the rules are present and current. Every check is set on
    every path, so an unverifiable state reads as False rather than absent.
    """
    for key in _PROJECTION_CHECK_KEYS:
        checks[key] = False

    if not instructions_path.is_file():
        return

    try:
        text = instructions_path.read_text(encoding="utf-8")
    except OSError as exc:
        warnings.append(f"cannot read {instructions_path}: {exc}")
        return

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    begins = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_END]
    block_unique = len(begins) == 1 and len(ends) == 1 and begins[0] < ends[0]
    checks["copilot_instructions_managed_block_unique"] = block_unique
    if not block_unique:
        ordering = (
            " (END precedes BEGIN)"
            if len(begins) == 1 and len(ends) == 1 and begins[0] > ends[0]
            else ""
        )
        warnings.append(
            f"{instructions_path} has {len(begins)} managed BEGIN and {len(ends)} managed END "
            f"markers{ordering}; expected exactly one matched pair in order — reinstall will "
            "refuse to merge until this is resolved"
        )

    try:
        header, body, projection_begin, projection_end = extract_projection_region(text)
    except ValueError as exc:
        warnings.append(
            f"{instructions_path} has no usable checkpoint projection ({exc}); "
            "Governance Contract checkpoint rules are not known to be installed"
        )
        return
    checks["copilot_checkpoint_projection_present"] = True

    inside = block_unique and begins[0] < projection_begin and projection_end < ends[0]
    checks["copilot_checkpoint_projection_inside_managed_block"] = inside
    if not inside:
        warnings.append(
            f"{instructions_path} checkpoint projection sits outside the framework-managed "
            "block; reinstall will not refresh it"
        )

    expected_source = canonical_source_token()
    source_expected = header["source"] == expected_source
    checks["copilot_checkpoint_source_expected"] = source_expected
    if not source_expected:
        warnings.append(
            f"{instructions_path} checkpoint projection claims source {header['source']}; "
            f"framework projects from {expected_source}"
        )

    version_current = header["version"] == CHECKPOINT_PROJECTION_VERSION
    checks["copilot_checkpoint_version_current"] = version_current
    if not version_current:
        warnings.append(
            f"{instructions_path} checkpoint projection is version {header['version']}; "
            f"framework expects {CHECKPOINT_PROJECTION_VERSION} — reinstall to update"
        )

    body_digest = section_digest(body)
    body_matches_header = body_digest == header["sha256"]
    checks["copilot_checkpoint_body_matches_header"] = body_matches_header
    if not body_matches_header:
        warnings.append(
            f"{instructions_path} checkpoint projection body does not match its own header; "
            f"header sha256={header['sha256']}, body sha256={body_digest} — the rules were "
            "edited or removed after the header was written"
        )

    if framework_root is None:
        warnings.append(
            f"cannot verify {instructions_path} against canonical "
            f"{CANONICAL_SOURCE_REL}: framework root is unknown"
        )
        return

    canonical_path = framework_root / CANONICAL_SOURCE_REL
    try:
        expected = section_digest(
            extract_canonical_section(canonical_path.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError) as exc:
        warnings.append(f"cannot derive canonical checkpoint digest from {canonical_path}: {exc}")
        return

    # Both must hold: the header must claim the canonical digest, and the body
    # actually present must hash to it.
    matches = header["sha256"] == expected and body_digest == expected
    checks["copilot_checkpoint_matches_canonical"] = matches
    if not matches:
        warnings.append(
            f"{instructions_path} checkpoint projection does not match {canonical_path}; "
            f"expected sha256={expected}, header sha256={header['sha256']}, "
            f"body sha256={body_digest} — reinstall to update"
        )


def validate_hook_install(repo_root: Path, framework_root: Path | None = None) -> HookInstallResult:
    repo_root = repo_root.resolve()
    hook_dir = _resolve_hook_dir(repo_root)
    checks: dict[str, bool] = {}
    errors: list[str] = []
    warnings: list[str] = []

    if not hook_dir.is_dir():
        return HookInstallResult(
            valid=False,
            repo_root=str(repo_root),
            hook_dir=str(hook_dir),
            framework_root=None,
            checks={"git_hooks_dir_present": False},
            errors=[f"missing git hooks directory: {hook_dir}"],
        )

    checks["git_hooks_dir_present"] = True

    pre_commit = hook_dir / "pre-commit"
    pre_push = hook_dir / "pre-push"
    config_file = hook_dir / "ai-governance-framework-root"

    checks["pre_commit_installed"] = _contains_framework_marker(pre_commit)
    checks["pre_push_installed"] = _contains_framework_marker(pre_push)
    checks["framework_root_config_present"] = config_file.is_file()

    if not checks["pre_commit_installed"]:
        errors.append(f"missing AI Governance pre-commit hook: {pre_commit}")
    if not checks["pre_push_installed"]:
        errors.append(f"missing AI Governance pre-push hook: {pre_push}")

    # copilot-instructions check (warning only — not a blocking requirement)
    copilot_instructions = repo_root / ".github" / "copilot-instructions.md"
    copilot_present = copilot_instructions.is_file()
    copilot_governed = copilot_present and COPILOT_INSTRUCTIONS_MARKER in (
        copilot_instructions.read_text(encoding="utf-8") if copilot_present else ""
    )
    checks["copilot_instructions_present"] = copilot_present
    checks["copilot_instructions_governed"] = copilot_governed
    if not copilot_present:
        warnings.append(
            f"copilot-instructions.md not found: {copilot_instructions} "
            f"— run install-hooks.sh to deploy DONE boundary rules for Copilot Workspace"
        )
    elif not copilot_governed:
        warnings.append(
            f"copilot-instructions.md exists but was not deployed by AI Governance Framework: {copilot_instructions}"
        )

    lifecycle_bridge = repo_root / ".github" / "hooks" / "ai-governance-lifecycle.py"
    vscode_hooks = repo_root / ".github" / "hooks" / "ai-governance-vscode.json"
    copilot_hooks = repo_root / ".github" / "hooks" / "ai-governance-copilot.json"
    lifecycle_bridge_present = lifecycle_bridge.is_file()
    lifecycle_bridge_governed = lifecycle_bridge_present and _contains_marker(
        lifecycle_bridge,
        COPILOT_LIFECYCLE_MARKER,
    )
    vscode_hooks_present = vscode_hooks.is_file()
    # VS Code's start handler comes from the Copilot config's `sessionStart`
    # after name normalization; declaring it here too would double-register.
    vscode_hooks_governed = _managed_copilot_hook_config(
        vscode_hooks,
        {"Stop": ("session_end", "auto")},
    )
    copilot_hooks_present = copilot_hooks.is_file()
    copilot_hooks_governed = _managed_copilot_hook_config(
        copilot_hooks,
        {
            "sessionStart": ("session_start", "auto"),
            "sessionEnd": ("session_end", "auto"),
        },
    )
    checks["copilot_lifecycle_bridge_present"] = lifecycle_bridge_present
    checks["copilot_lifecycle_bridge_governed"] = lifecycle_bridge_governed
    checks["copilot_vscode_hooks_present"] = vscode_hooks_present
    checks["copilot_vscode_hooks_governed"] = vscode_hooks_governed
    checks["copilot_session_end_hooks_present"] = copilot_hooks_present
    checks["copilot_session_end_hooks_governed"] = copilot_hooks_governed
    checks["copilot_lifecycle_installed"] = all(
        (
            lifecycle_bridge_governed,
            vscode_hooks_governed,
            copilot_hooks_governed,
        )
    )
    if not checks["copilot_lifecycle_installed"]:
        warnings.append(
            "Copilot lifecycle hooks are not fully installed; expected managed "
            ".github/hooks lifecycle bridge plus VS Code Stop and Copilot sessionEnd configs. "
            "Note that the VS Code config declares Stop only: VS Code loads every *.json under "
            ".github/hooks and normalizes the Copilot config's sessionStart to SessionStart, so "
            "adding SessionStart to the VS Code config registers a second start handler and "
            "writes the session envelope twice"
        )

    resolved_framework_root = framework_root.resolve() if framework_root is not None else None
    if config_file.is_file():
        raw_value = config_file.read_text(encoding="utf-8").strip()
        if raw_value:
            resolved_framework_root = _normalize_framework_root(raw_value)
        else:
            errors.append(f"framework root config is empty: {config_file}")
    elif resolved_framework_root is not None:
        warnings.append(
            f"ai-governance-framework-root not found; using explicit framework root: {resolved_framework_root}"
        )
    else:
        warnings.append(
            "ai-governance-framework-root not found; temporarily treating the target repo as the framework root."
        )
        resolved_framework_root = repo_root

    if resolved_framework_root is not None:
        checks["framework_root_exists"] = resolved_framework_root.is_dir()
        if not checks["framework_root_exists"]:
            errors.append(f"framework root does not exist: {resolved_framework_root}")
        else:
            for relpath in REQUIRED_FRAMEWORK_FILES:
                key = f"framework_file:{relpath}"
                present = (resolved_framework_root / relpath).is_file()
                checks[key] = present
                if not present:
                    errors.append(f"framework root missing required file: {resolved_framework_root / relpath}")
    else:
        checks["framework_root_exists"] = False

    _check_copilot_instructions_projection(
        copilot_instructions,
        resolved_framework_root if checks.get("framework_root_exists") else None,
        checks,
        warnings,
    )

    return HookInstallResult(
        valid=len(errors) == 0,
        repo_root=str(repo_root),
        hook_dir=str(hook_dir),
        framework_root=(
            str(resolved_framework_root.resolve())
            if resolved_framework_root and resolved_framework_root.exists()
            else (str(resolved_framework_root) if resolved_framework_root else None)
        ),
        checks=checks,
        errors=errors,
        warnings=warnings,
    )


def format_human(result: HookInstallResult) -> str:
    lines = [
        "AI Governance Hook Install Validation",
        "",
        f"valid              = {result.valid}",
        f"repo_root          = {result.repo_root}",
        f"hook_dir           = {result.hook_dir}",
        f"framework_root     = {result.framework_root or '<missing>'}",
        "",
        "[checks]",
    ]
    for key in sorted(result.checks):
        lines.append(f"{key:<32} = {result.checks[key]}")

    if result.errors:
        lines.append("")
        lines.append(f"errors: {len(result.errors)}")
        for item in result.errors:
            lines.append(f"- {item}")

    if result.warnings:
        lines.append("")
        lines.append(f"warnings: {len(result.warnings)}")
        for item in result.warnings:
            lines.append(f"- {item}")

    return "\n".join(lines)


def format_json(result: HookInstallResult) -> str:
    return json.dumps(
        {
            "valid": result.valid,
            "repo_root": result.repo_root,
            "hook_dir": result.hook_dir,
            "framework_root": result.framework_root,
            "checks": result.checks,
            "errors": result.errors,
            "warnings": result.warnings,
        },
        ensure_ascii=False,
        indent=2,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate AI Governance hook installation state for a target repo."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Target git repo root to inspect (default: current directory).",
    )
    parser.add_argument(
        "--framework-root",
        help="Optional explicit framework root to validate against when hooks are not installed yet.",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result = validate_hook_install(
        Path(args.repo),
        framework_root=Path(args.framework_root) if args.framework_root else None,
    )
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_human(result))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
