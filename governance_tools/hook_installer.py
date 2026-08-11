#!/usr/bin/env python3
"""
Cross-platform AI Governance hook installer.

This is the Python equivalent of the hook deployment portion of
scripts/install-hooks.sh. It is intentionally narrow: copy managed hook files,
write the framework-root config without a BOM, and deploy Copilot instructions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence


FRAMEWORK_MARKER = "AI Governance Framework"
COPILOT_MARKER = "AI Governance Framework: copilot-instructions"
COPILOT_BLOCK_BEGIN = "<!-- AI Governance Framework: copilot-instructions BEGIN -->"
COPILOT_BLOCK_END = "<!-- AI Governance Framework: copilot-instructions END -->"
COPILOT_LIFECYCLE_MARKER = "Thin lifecycle bridge for VS Code and GitHub Copilot hooks."
# Content digests of every copilot-instructions template this framework has
# shipped, before the managed block existed. A target matching one of these is
# provably unedited framework content, so replacing it whole loses nothing.
# Regenerate with:
#   git log --format=%H -- governance/copilot-instructions-template.md
# hashing each revision's LF-normalized, newline-stripped bytes.
LEGACY_COPILOT_TEMPLATE_DIGESTS = frozenset(
    {
        "3bf3774cdfff3559fab50821e7789c96c0c8bbeb4557a8a5619b8574bacbc1bb",
        "545f348b14b23c6e1eaf374001cd33c8e07b54e09f0cfcf09fff230d003c20c0",
        "c6ba29f1079200f77e9d93adb434de1039468788b96f09cf6ed9760c31affe8e",
        "c9ae3e68d2065d8f3d19d7005a208a21567fce5748624b167398eb0e90d47659",
        "d4a6ec07b63b8335cc963f2a08b89ae1f97b89fd4fb8eb74cfac0bbb61645b7b",
        "d517bd05fdc866f9bbc603f6b0f0a917653ff05179b89a50fbf1f614212e5349",
        "e2974ed5cd88125561395c4d749d182b595bd865e219991c0a133579c9569ced",
    }
)
COPILOT_HOOK_COMMAND_MARKER = "ai-governance-lifecycle.py"
HOOK_NAMES = ("pre-commit", "pre-push")
# Records the digest of every managed lifecycle file this installer wrote, so a
# later install can tell "the framework wrote this" from "the consumer edited
# this". Without it, a marker check passes on an edited file and the edit is
# overwritten with no backup.
MANAGED_MANIFEST_REL = Path(".github/hooks/.ai-governance-managed.json")
COPILOT_LIFECYCLE_FILES = (
    (
        Path("runtime_hooks/adapters/copilot/lifecycle.py"),
        Path(".github/hooks/ai-governance-lifecycle.py"),
        COPILOT_LIFECYCLE_MARKER,
    ),
    (
        Path("governance/copilot-hooks-vscode-template.json"),
        Path(".github/hooks/ai-governance-vscode.json"),
        COPILOT_HOOK_COMMAND_MARKER,
    ),
    (
        Path("governance/copilot-hooks-session-end-template.json"),
        Path(".github/hooks/ai-governance-copilot.json"),
        COPILOT_HOOK_COMMAND_MARKER,
    ),
)


@dataclass
class HookInstallApplyResult:
    ok: bool
    repo_root: str
    framework_root: str
    installed_files: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    copilot_instructions_mode: str | None = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and _read_text(path) == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _write_bytes_if_changed(path: Path, payload: bytes) -> bool:
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


def _shell_hook_payload(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _framework_root_config_value(path: Path) -> str:
    return path.as_posix() if os.name == "nt" else str(path)


def _has_marker(path: Path, marker: str) -> bool:
    if not path.exists():
        return False
    try:
        return marker in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _content_digest(text: str) -> str:
    """Line-ending-insensitive content digest, so a CRLF checkout still matches."""
    return hashlib.sha256(_normalize_newlines(text).strip("\n").encode("utf-8")).hexdigest()


def _extract_managed_block(source_text: str) -> str:
    """Return the framework-managed region of the Copilot instructions template.

    Templates from framework versions that predate the managed block have no
    BEGIN/END markers; the whole file is framework content, so it is wrapped.
    """
    text = _normalize_newlines(source_text).strip("\n")
    lines = text.split("\n")
    begins = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_END]
    if not begins and not ends:
        return f"{COPILOT_BLOCK_BEGIN}\n{text}\n{COPILOT_BLOCK_END}"
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        raise ValueError(
            f"template must contain exactly one managed block "
            f"(found {len(begins)} BEGIN / {len(ends)} END markers)"
        )
    return "\n".join(lines[begins[0] : ends[0] + 1])


def _merge_managed_block(existing_text: str | None, block: str) -> tuple[str, str]:
    """Splice the managed block into the target, preserving consumer content.

    Returns the new file text and the mode describing what happened:
    `created`, `replaced`, `migrated` (pre-managed-block framework file), or
    `appended` (the target was written by the consumer, not the framework).
    """
    if existing_text is None:
        return f"{block}\n", "created"

    text = _normalize_newlines(existing_text)
    lines = text.split("\n")
    begins = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == COPILOT_BLOCK_END]

    if begins or ends:
        if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
            raise ValueError(
                f"target has {len(begins)} managed BEGIN and {len(ends)} managed END markers; "
                "expected exactly one matched pair — resolve manually before reinstalling"
            )
        merged = "\n".join(lines[: begins[0]] + block.split("\n") + lines[ends[0] + 1 :])
        return merged.rstrip("\n") + "\n", "replaced"

    if COPILOT_MARKER in text:
        # Written by a framework version that replaced the whole file. Migrating
        # means replacing all of it, so only do that when the content is provably
        # untouched framework output. A marker alone does not prove that: the
        # consumer may have added rules to the installed file, and those would
        # survive only in the backup.
        if _content_digest(text) in LEGACY_COPILOT_TEMPLATE_DIGESTS:
            return f"{block}\n", "migrated"
        raise ValueError(
            "target carries a framework marker but no managed block, and its content matches "
            "no template this framework has shipped — it was edited after install. Move the "
            "repository-specific parts outside the managed block markers (or delete the file "
            "to reinstall from scratch) before reinstalling"
        )

    preserved = text.rstrip("\n")
    if not preserved:
        return f"{block}\n", "created"
    return f"{preserved}\n\n{block}\n", "appended"


def _read_managed_manifest(repo_root: Path) -> dict[str, str]:
    path = repo_root / MANAGED_MANIFEST_REL
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    files = payload.get("files")
    if not isinstance(files, dict):
        return {}
    return {str(key): str(value) for key, value in files.items()}


def _write_managed_manifest(
    repo_root: Path,
    recorded: dict[str, str],
    changed: list[str],
    installed: list[str],
) -> None:
    path = repo_root / MANAGED_MANIFEST_REL
    payload = (
        json.dumps(
            {"version": 1, "files": dict(sorted(recorded.items()))},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    if _write_bytes_if_changed(path, payload.encode("utf-8")):
        changed.append(str(path))
    installed.append(str(path))


def _backup_file(path: Path, backups: list[str]) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup)
    backups.append(str(backup))


def _backup_unmanaged(path: Path, marker: str, backups: list[str]) -> None:
    if not path.exists() or _has_marker(path, marker):
        return
    _backup_file(path, backups)


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
    return dot_git / "hooks"


def _apply_copilot_instructions(
    repo_root: Path,
    framework_root: Path,
    *,
    installed: list[str],
    changed: list[str],
    backups: list[str],
    errors: list[str],
) -> str | None:
    source = framework_root / "governance" / "copilot-instructions-template.md"
    target = repo_root / ".github" / "copilot-instructions.md"
    if not source.is_file():
        errors.append(f"missing copilot instructions template: {source}")
        return None

    try:
        block = _extract_managed_block(_read_text(source))
        existing = _read_text(target) if target.is_file() else None
        merged, mode = _merge_managed_block(existing, block)
    except ValueError as exc:
        errors.append(f"cannot update {target}: {exc}")
        return None

    # Compare on normalized newlines: a repo with core.autocrlf=true checks this
    # file out as CRLF, and rewriting it every install would report a change that
    # is not one.
    if existing is not None and _normalize_newlines(existing) == merged:
        installed.append(str(target))
        return mode

    # `replaced` only touches the managed block, so the rest of the file is
    # already safe. `appended` and `migrated` rewrite content this installer did
    # not author in the current format — a consumer's own file, or a whole-file
    # install from an older framework version that may since have been edited by
    # hand. Keep a copy of those before writing.
    if existing is not None and mode in ("appended", "migrated"):
        _backup_file(target, backups)

    if _write_bytes_if_changed(target, merged.encode("utf-8")):
        changed.append(str(target))
    installed.append(str(target))
    return mode


def install_copilot_instructions(
    repo_root: Path,
    framework_root: Path,
) -> HookInstallApplyResult:
    """Install only the managed Copilot instructions block.

    scripts/install-hooks.sh delegates here so the shell and Python installers
    apply the same managed-block merge instead of two divergent copies.
    """
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()
    installed: list[str] = []
    changed: list[str] = []
    backups: list[str] = []
    errors: list[str] = []
    mode = _apply_copilot_instructions(
        repo_root,
        framework_root,
        installed=installed,
        changed=changed,
        backups=backups,
        errors=errors,
    )
    return HookInstallApplyResult(
        ok=not errors,
        repo_root=str(repo_root),
        framework_root=str(framework_root),
        installed_files=installed,
        changed_files=changed,
        backups=backups,
        errors=errors,
        copilot_instructions_mode=mode,
    )


def install_governance_hooks(
    repo_root: Path,
    framework_root: Path,
    *,
    include_copilot: bool = True,
) -> HookInstallApplyResult:
    repo_root = repo_root.resolve()
    framework_root = framework_root.resolve()
    hook_dir = _resolve_hook_dir(repo_root)
    source_hook_dir = framework_root / "scripts" / "hooks"
    errors: list[str] = []
    installed: list[str] = []
    changed: list[str] = []
    backups: list[str] = []
    copilot_mode: str | None = None

    if not (repo_root / ".git").exists():
        errors.append(f"not a git repo: {repo_root}")
    if not source_hook_dir.is_dir():
        errors.append(f"missing framework hooks source: {source_hook_dir}")
    if errors:
        return HookInstallApplyResult(
            ok=False,
            repo_root=str(repo_root),
            framework_root=str(framework_root),
            errors=errors,
        )

    hook_dir.mkdir(parents=True, exist_ok=True)
    for hook_name in HOOK_NAMES:
        source = source_hook_dir / hook_name
        target = hook_dir / hook_name
        if not source.is_file():
            errors.append(f"missing source hook: {source}")
            continue
        _backup_unmanaged(target, FRAMEWORK_MARKER, backups)
        if _write_bytes_if_changed(target, _shell_hook_payload(source)):
            changed.append(str(target))
        installed.append(str(target))

    config = hook_dir / "ai-governance-framework-root"
    # Python's utf-8 writer does not emit a BOM. Keep a trailing newline to match
    # shell-created config files while preserving deterministic content.
    config_payload = f"{_framework_root_config_value(framework_root)}\n".encode("utf-8")
    if _write_bytes_if_changed(config, config_payload):
        changed.append(str(config))
    installed.append(str(config))

    if include_copilot:
        copilot_mode = _apply_copilot_instructions(
            repo_root,
            framework_root,
            installed=installed,
            changed=changed,
            backups=backups,
            errors=errors,
        )

        # Lifecycle files are additive for framework versions that provide
        # them. Older framework fixtures remain installable, while the
        # validator reports the absent lifecycle surface as advisory.
        #
        # These are replaced whole — the bridge has to stay in step with the
        # framework — so anything that is not byte-for-byte what this installer
        # last wrote is backed up first. A marker check is not enough: an edited
        # file still carries the marker, and its edits would be lost silently.
        manifest = _read_managed_manifest(repo_root)
        wrote_lifecycle_file = False
        for source_rel, target_rel, _marker in COPILOT_LIFECYCLE_FILES:
            source = framework_root / source_rel
            if not source.is_file():
                continue
            target = repo_root / target_rel
            payload = source.read_bytes()
            payload_digest = _content_digest(payload.decode("utf-8", errors="replace"))
            key = target_rel.as_posix()

            if target.is_file():
                current_digest = _content_digest(
                    target.read_text(encoding="utf-8", errors="replace")
                )
                if current_digest != payload_digest and manifest.get(key) != current_digest:
                    _backup_file(target, backups)

            if _write_bytes_if_changed(target, payload):
                changed.append(str(target))
            manifest[key] = payload_digest
            installed.append(str(target))
            wrote_lifecycle_file = True

        if wrote_lifecycle_file:
            _write_managed_manifest(repo_root, manifest, changed, installed)

    return HookInstallApplyResult(
        ok=not errors,
        repo_root=str(repo_root),
        framework_root=str(framework_root),
        installed_files=installed,
        changed_files=changed,
        backups=backups,
        errors=errors,
        copilot_instructions_mode=copilot_mode,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install AI Governance hooks without requiring bash.")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--framework-root", required=True, type=Path)
    parser.add_argument(
        "--hooks-only",
        action="store_true",
        help="Install only .git/hooks managed files and framework-root config; do not touch tracked Copilot instructions.",
    )
    parser.add_argument(
        "--copilot-instructions-only",
        action="store_true",
        help="Install only the managed .github/copilot-instructions.md block; do not touch git hooks.",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    if args.copilot_instructions_only:
        if args.hooks_only:
            parser.error("--hooks-only and --copilot-instructions-only are mutually exclusive")
        result = install_copilot_instructions(args.repo, args.framework_root)
    else:
        result = install_governance_hooks(
            args.repo,
            args.framework_root,
            include_copilot=not args.hooks_only,
        )
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(f"ok={result.ok}")
        print(f"repo_root={result.repo_root}")
        print(f"framework_root={result.framework_root}")
        print(f"changed_files={len(result.changed_files)}")
        if result.copilot_instructions_mode:
            print(f"copilot_instructions_mode={result.copilot_instructions_mode}")
        # Backups are the only record of content this install replaced, so they
        # belong in the terminal output, not just the JSON payload.
        for backup in result.backups:
            print(f"backup: {backup}")
        for error in result.errors:
            print(f"error: {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
