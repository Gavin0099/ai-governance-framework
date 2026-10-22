#!/usr/bin/env python3
"""Thin lifecycle bridge for VS Code and GitHub Copilot hooks.

The bridge owns payload normalization only. Governance decisions remain in the
canonical session envelope and session-end implementations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


PROVIDER_BY_SURFACE = {
    "vscode": "github-copilot-vscode",
    "copilot": "github-copilot",
}
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]{0,127}$")
FRAMEWORK_ROOT_CONFIG = "ai-governance-framework-root"
FRAMEWORK_CANDIDATES = (
    Path(".ai-governance-framework"),
    Path("ai-governance-framework"),
    Path("additional/ai-governance-framework"),
)


def _first_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _resolve_surface(payload: dict[str, Any], surface: str) -> str:
    if surface in PROVIDER_BY_SURFACE:
        return surface
    if surface != "auto":
        raise ValueError(f"unsupported Copilot surface: {surface}")
    if any(key in payload for key in ("session_id", "hook_event_name", "transcript_path")):
        return "vscode"
    if any(key in payload for key in ("sessionId", "hookEventName", "transcriptPath")):
        return "copilot"
    raise ValueError("Copilot lifecycle payload surface could not be inferred")


def _validate_session_id(session_id: str) -> str:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(
            "Copilot lifecycle session_id/sessionId must be one safe path segment "
            "(1-128 ASCII letters, digits, dot, underscore, or hyphen)"
        )
    return session_id


def normalize_lifecycle_payload(
    payload: dict[str, Any],
    *,
    event_type: str,
    surface: str,
) -> dict[str, Any]:
    if event_type not in {"session_start", "session_end"}:
        raise ValueError(f"unsupported lifecycle event_type: {event_type}")
    resolved_surface = _resolve_surface(payload, surface)

    session_id = _validate_session_id(_first_text(payload, "session_id", "sessionId"))
    cwd = _first_text(payload, "cwd")
    if not session_id:
        raise ValueError("Copilot lifecycle payload is missing session_id/sessionId")
    if not cwd:
        raise ValueError("Copilot lifecycle payload is missing cwd")

    project_root = Path(cwd).expanduser().resolve()
    if not project_root.is_dir():
        raise ValueError(f"Copilot lifecycle cwd does not exist: {project_root}")

    transcript = _first_text(payload, "transcript_path", "transcriptPath")
    return {
        "event_type": event_type,
        "surface": resolved_surface,
        "provider": PROVIDER_BY_SURFACE[resolved_surface],
        "session_id": session_id,
        "project_root": project_root,
        "transcript_path": Path(transcript).expanduser().resolve() if transcript else None,
        "hook_event_name": _first_text(payload, "hook_event_name", "hookEventName"),
        "stop_hook_active": bool(payload.get("stop_hook_active", False)),
        "reason": _first_text(payload, "reason"),
    }


def _is_framework_root(path: Path) -> bool:
    return (
        (path / "governance_tools" / "session_end_hook.py").is_file()
        and (path / "runtime_hooks" / "core" / "_canonical_closeout.py").is_file()
    )


def _git_hook_config_path(project_root: Path) -> Path | None:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={project_root.as_posix()}",
            "-C",
            str(project_root),
            "rev-parse",
            "--git-path",
            f"hooks/{FRAMEWORK_ROOT_CONFIG}",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    raw_path = (completed.stdout or "").strip()
    if completed.returncode != 0 or not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def resolve_framework_root(project_root: Path) -> Path:
    candidates: list[Path] = []

    env_root = os.environ.get("AI_GOVERNANCE_FRAMEWORK_ROOT", "").strip()
    if env_root:
        path = Path(env_root).expanduser()
        candidates.append(path if path.is_absolute() else project_root / path)

    hook_config = _git_hook_config_path(project_root)
    if hook_config and hook_config.is_file():
        configured = hook_config.read_text(encoding="utf-8").strip().lstrip("\ufeff")
        if configured:
            path = Path(configured).expanduser()
            candidates.append(path if path.is_absolute() else project_root / path)

    for parent in Path(__file__).resolve().parents:
        candidates.append(parent)
    candidates.extend(project_root / relative for relative in FRAMEWORK_CANDIDATES)

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _is_framework_root(resolved):
            return resolved
    raise RuntimeError(
        "AI Governance framework root could not be resolved from environment, "
        "git hook config, adapter location, or supported consumer paths"
    )


def _write_session_envelope(
    session_id: str,
    project_root: Path,
    *,
    provider: str,
) -> dict[str, Any]:
    from runtime_hooks.core._canonical_closeout import write_session_envelope

    return write_session_envelope(session_id, project_root, provider=provider)


def _installed_project_root() -> Path | None:
    """The consumer root this bridge was installed into, independent of any payload.

    hook_installer copies this file to <root>/.github/hooks/ai-governance-lifecycle.py.
    Only from that location is there an anchor that a payload's cwd can be checked
    against; anywhere else (e.g. run from the framework source) returns None.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "hooks" and here.parent.parent.name == ".github":
        return here.parents[2]
    return None


def _start_vscode_session(
    payload: dict[str, Any],
    normalized: dict[str, Any],
) -> dict[str, Any]:
    """VS Code SessionStart: root-bound identity when provable, else today's v1.0.

    Binding is granted only through establish_root_bound_session, the same checks
    Codex uses.  When a root-bound identity cannot be proven (bridge not in its
    installed location, a resolved framework without root-bound support, no
    SessionStart event name, or a session_id outside the root-bound format) the
    legacy unbound envelope is written exactly as before, so nothing that worked
    stops working and nothing unbound is treated as bound.
    """
    try:
        from runtime_hooks.core._canonical_closeout import (
            _ROOT_BOUND_SESSION_ID,
            establish_root_bound_session,
        )
    except ImportError:
        # Bridge newer than the framework it resolved: that framework cannot
        # write or read root-bound VS Code envelopes, so keep its v1.0 path.
        _ROOT_BOUND_SESSION_ID = establish_root_bound_session = None

    session_id = normalized["session_id"]
    installed_root = _installed_project_root()
    event_name = _first_text(payload, "hook_event_name", "hookEventName")
    if installed_root is None:
        reason = "bridge_not_in_installed_location"
    elif establish_root_bound_session is None:
        reason = "framework_without_root_bound_support"
    elif not event_name:
        reason = "payload_has_no_event_name"
    elif not _ROOT_BOUND_SESSION_ID.fullmatch(session_id):
        reason = "session_id_not_root_bound_format"
    else:
        if event_name != "SessionStart":
            raise ValueError("Expected a SessionStart payload")
        bound = establish_root_bound_session(
            session_id=session_id,
            cwd=payload.get("cwd"),
            installed_root=installed_root,
            provider=normalized["provider"],
            require_existing=payload.get("source") in {"resume", "compact"},
            lock_name=".vscode-start.lock",
        )
        return {
            "binding": "root_bound",
            "identity_status": bound["status"],
            "session_envelope_path": bound["session_envelope_path"],
        }
    envelope = _write_session_envelope(
        session_id,
        normalized["project_root"],
        provider=normalized["provider"],
    )
    return {
        "binding": "legacy_unbound",
        "binding_reason": reason,
        "session_envelope_path": envelope.get("artifact_path"),
    }


def _run_session_end(
    project_root: Path,
    *,
    session_id: str,
    transcript_path: Path | None,
) -> dict[str, Any]:
    from governance_tools.session_end_hook import run_session_end_hook

    return run_session_end_hook(
        project_root,
        hook_session_id=session_id,
        transcript_path=transcript_path,
    )


def run_lifecycle_event(
    payload: dict[str, Any],
    *,
    event_type: str,
    surface: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    normalized = normalize_lifecycle_payload(
        payload,
        event_type=event_type,
        surface=surface,
    )
    framework_root = resolve_framework_root(normalized["project_root"])
    if str(framework_root) not in sys.path:
        sys.path.insert(0, str(framework_root))

    common = {
        "continue": True,
        "event_type": normalized["event_type"],
        "surface": normalized["surface"],
        "provider": normalized["provider"],
        "session_id": normalized["session_id"],
        "project_root": str(normalized["project_root"]),
        "framework_root": str(framework_root),
    }
    if dry_run:
        return {
            **common,
            "ok": True,
            "status": "dry_run",
            "would_write_session_envelope": event_type == "session_start",
            "would_invoke_session_end": event_type == "session_end",
        }

    if event_type == "session_start":
        if normalized["surface"] == "vscode":
            return {
                **common,
                "ok": True,
                "status": "session_envelope_written",
                **_start_vscode_session(payload, normalized),
            }
        envelope = _write_session_envelope(
            normalized["session_id"],
            normalized["project_root"],
            provider=normalized["provider"],
        )
        return {
            **common,
            "ok": True,
            "status": "session_envelope_written",
            "session_envelope_path": envelope.get("artifact_path"),
        }

    result = _run_session_end(
        normalized["project_root"],
        session_id=normalized["session_id"],
        transcript_path=normalized["transcript_path"],
    )
    return {
        **common,
        "ok": bool(result.get("ok")),
        "status": "session_end_invoked",
        "closeout_status": result.get("closeout_status"),
        "decision": result.get("decision"),
        "session_binding_status": (result.get("session_binding") or {}).get("status"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bridge VS Code/Copilot lifecycle payloads to canonical AI Governance runtime."
    )
    parser.add_argument("--event-type", required=True, choices=("session_start", "session_end"))
    parser.add_argument(
        "--surface",
        required=True,
        choices=("auto", *PROVIDER_BY_SURFACE),
        help="Use auto for shared repo hook configs; explicit values remain available for diagnostics.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Normalize and resolve the payload without writing an envelope or invoking session_end.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(sys.stdin.read())
        result = run_lifecycle_event(
            payload,
            event_type=args.event_type,
            surface=args.surface,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        result = {
            "continue": True,
            "ok": False,
            "status": "bridge_error",
            "error": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
