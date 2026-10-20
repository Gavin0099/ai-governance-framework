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
EVENT_TYPES = ("session_start", "turn_stop", "prepare_closeout", "session_end", "explicit_closeout")


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
    if event_type not in EVENT_TYPES:
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
        "stop_reason": _first_text(payload, "stop_reason", "stopReason"),
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
    from runtime_hooks.core._canonical_closeout import read_session_envelope, write_session_envelope
    from governance_tools.shared_closeout_ownership import execution_exclusion

    with execution_exclusion(project_root):
        previous = read_session_envelope(session_id, project_root)
        if previous is not None:
            if previous.get("schema_version") != "1.0" or previous.get("provider") != provider:
                raise ValueError("Copilot SessionStart conflicts with existing session identity")
            return previous
        return write_session_envelope(session_id, project_root, provider=provider)


def _run_session_end(
    project_root: Path,
    *,
    session_id: str,
    transcript_path: Path | None,
) -> dict[str, Any]:
    from runtime_hooks.adapters.copilot.closeout import run
    from runtime_hooks.core._canonical_closeout import read_session_envelope

    envelope = read_session_envelope(session_id, project_root) or {}
    return run(project_root, session_id, str(envelope.get("provider") or ""), transcript_path)


def run_lifecycle_event(
    payload: dict[str, Any],
    *,
    event_type: str,
    surface: str,
    dry_run: bool = False,
    summary_input: dict[str, Any] | None = None,
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
    native_event = normalized["hook_event_name"]
    # Defense for already-installed legacy Stop -> session_end commands. Presence
    # of a summary never makes a turn boundary into a session-end authorization.
    if (event_type == "turn_stop" or normalized["stop_reason"] == "end_turn"
            or native_event in {"Stop", "agentStop", "SubagentStop", "subagentStop"}):
        return {**common, "ok": True, "status": "turn_observed",
                "closeout_eligibility": "not_yet_eligible", "would_invoke_session_end": False}
    allowed_native = {"session_start": {"SessionStart", "sessionStart"},
                      "session_end": {"SessionEnd", "sessionEnd"}}
    if native_event and native_event not in allowed_native.get(event_type, set()):
        raise ValueError("Native Copilot event conflicts with the requested lifecycle action")
    if (event_type == "session_end" and not native_event
            and normalized["reason"] not in {"complete", "error", "abort", "timeout", "user_exit"}):
        raise ValueError("Copilot session_end needs a native end event/reason; use explicit_closeout for owner closeout")
    if dry_run:
        return {
            **common,
            "ok": True,
            "status": "dry_run",
            "would_write_session_envelope": event_type == "session_start",
            "would_invoke_session_end": event_type in {"session_end", "explicit_closeout"},
        }

    if event_type == "session_start":
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

    if event_type == "prepare_closeout":
        from runtime_hooks.adapters.copilot.closeout import prepare
        return {**common, **prepare(normalized["project_root"], normalized["session_id"],
                                    normalized["provider"], summary_input)}
    result = _run_session_end(
        normalized["project_root"],
        session_id=normalized["session_id"],
        transcript_path=normalized["transcript_path"],
    )
    return {
        **common, **result,
        "status": "session_end_invoked",
        "closeout_status": result.get("closeout_status"),
        "decision": result.get("decision"),
        "session_binding_status": (result.get("session_binding") or {}).get("status"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bridge VS Code/Copilot lifecycle payloads to canonical AI Governance runtime."
    )
    parser.add_argument("--event-type", required=True, choices=EVENT_TYPES)
    parser.add_argument("--summary-input", type=Path, help="Agent-authored JSON for explicit prepare_closeout only.")
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
            summary_input=(json.loads(args.summary_input.read_text(encoding="utf-8"))
                           if args.summary_input else None),
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
