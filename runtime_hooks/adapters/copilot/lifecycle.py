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
    if event_type not in {"session_start", "session_end", "agent_stop"}:
        raise ValueError(f"unsupported lifecycle event_type: {event_type}")
    resolved_surface = _resolve_surface(payload, surface)
    if event_type == "agent_stop" and resolved_surface != "vscode":
        raise ValueError("agent_stop is the VS Code Stop execution point only")

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


def _installed_project_root() -> Path | None:
    """The consumer root this bridge was installed into, independent of any payload.

    hook_installer copies this file to <root>/.github/hooks/ai-governance-lifecycle.py,
    and that installed copy is what VS Code runs.  Anywhere else (e.g. run from the
    framework source in development or tests) there is no install anchor: None.
    """
    here = Path(__file__).resolve()
    if here.parent.name == "hooks" and here.parent.parent.name == ".github":
        return here.parents[2]
    return None


def _require_installed_root(project_root: Path, installed_root: Path) -> None:
    """The payload root must be the installed root itself, before anything else.

    Checked in the bridge (not only in the framework) so it also holds when the
    resolved framework is too old to bind; a subdirectory fails closed, as for
    payload-derived roots.
    """
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
        text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5,
    )
    toplevel = (completed.stdout or "").strip()
    expected = os.path.normcase(str(installed_root.resolve()))
    if (completed.returncode != 0 or not toplevel
            or os.path.normcase(str(Path(toplevel).resolve())) != expected
            or os.path.normcase(str(project_root.resolve())) != expected):
        raise ValueError("Payload cwd and installed project root do not match")


def _write_session_envelope(
    session_id: str,
    project_root: Path,
    *,
    provider: str,
    hook_event_name: str = "",
    source: object = None,
) -> dict[str, Any]:
    if provider == "github-copilot-vscode":
        # Same payload rules as Codex SessionStart, checked before any write:
        # only a SessionStart event may establish an identity, and resume or
        # compact never invents one that does not already exist.
        if hook_event_name != "SessionStart":
            raise ValueError("Expected a SessionStart payload")
        require_existing = source in {"resume", "compact"}
        # Like Codex's install-time --project-root, the installed bridge's own
        # location is the root the payload cwd must match (project_root itself is
        # derived from that payload).  Checked before the framework import so a
        # wrong project is never treated as a version-compatibility case.
        installed_root = _installed_project_root()
        if installed_root is not None:
            _require_installed_root(project_root, installed_root)
        try:
            from runtime_hooks.core._bound_session_start import establish_bound_session
        except ModuleNotFoundError as exc:
            # Only the root-bound module itself being absent means "framework too
            # old".  A broken dependency inside it, or a module without the
            # function, is a real error and propagates instead of downgrading.
            if exc.name != _BOUND_SESSION_MODULE:
                raise
            return _legacy_vscode_envelope(
                session_id, project_root, provider=provider, require_existing=require_existing,
            )
        # VS Code keeps its own identity but gets the same worktree binding as Codex.
        anchor = installed_root or project_root
        started = establish_bound_session(
            session_id, anchor, str(project_root),
            provider=provider, lock_name=_COPILOT_RUNTIME_START_LOCK,
            require_existing=require_existing,
        )
        return {
            "artifact_path": started["session_envelope_path"],
            "schema_version": started["envelope_schema_version"],
            "envelope_status": started["status"],
        }

    # The shared Copilot registration (.github/hooks/ai-governance-copilot.json) runs for
    # the standalone Copilot CLI and, because VS Code loads that file too, for VS Code
    # agent mode, with the same session id. One entry decides, so hook order cannot.
    # The provider is the client the Copilot runtime itself recorded for this session
    # (owner ruling 2026-11-11); an unknown or missing record establishes nothing.
    # Resumes keep the same sessionId and send source "resume": an existing identity,
    # including a v1.0 one, is preserved and never migrated or rebound.
    require_existing = source == "resume"
    installed_root = _installed_project_root()
    if installed_root is not None:
        _require_installed_root(project_root, installed_root)
    try:
        from runtime_hooks.core._bound_session_start import establish_bound_session
        from governance_tools.copilot_session_state import provider_for_session
    except ModuleNotFoundError as exc:
        # A framework without root-bound support or the runtime record reader keeps
        # the previous v1.0 behaviour; any other import failure is a real error.
        if exc.name not in (_BOUND_SESSION_MODULE, _SESSION_STATE_MODULE):
            raise
        return _preserving_envelope(
            session_id, project_root, provider=provider, require_existing=require_existing,
        )
    try:
        resolved = provider_for_session(session_id)
    except ValueError:
        # A resume of an identity that already exists needs no new decision: the
        # envelope already names its provider and is only preserved. Anything else
        # without the runtime's own record establishes nothing.
        from runtime_hooks.core._canonical_closeout import read_session_envelope
        existing = read_session_envelope(session_id, installed_root or project_root) if require_existing else None
        if not existing:
            raise
        resolved = existing["provider"]
    anchor = installed_root or project_root
    started = establish_bound_session(
        session_id, anchor, str(project_root),
        provider=resolved, lock_name=_COPILOT_RUNTIME_START_LOCK,
        require_existing=require_existing,
    )
    return {
        "artifact_path": started["session_envelope_path"],
        "schema_version": started["envelope_schema_version"],
        "envelope_status": started["status"],
        "provider": resolved,
    }


_BOUND_SESSION_MODULE = "runtime_hooks.core._bound_session_start"
# One lock for every SessionStart that runs on the Copilot runtime (VS Code payload and
# shared Copilot payload), so two registrations for one session id serialize; name kept from #225.
_COPILOT_RUNTIME_START_LOCK = ".vscode-start.lock"
_SESSION_STATE_MODULE = "governance_tools.copilot_session_state"
_LEGACY_REASON = "framework_without_root_bound_support"
VSCODE_PROVIDER = "github-copilot-vscode"


COPILOT_PROVIDERS = (VSCODE_PROVIDER, "github-copilot")


def _prepared_owner(root: Path, sid: str) -> dict[str, Any] | None:
    """None when this session is the R2 owner of a prepared candidate, else the reason not to act.

    Read only: no owner record means nothing was prepared, and the R2 lock file is not
    even created. The protected entry re-checks everything under the lock.
    """
    from governance_tools import shared_closeout_ownership as ownership

    if not (root / ownership.AREA / "owner.json").exists():
        return {"ok": True, "status": "no_prepared_candidate"}
    try:
        with ownership.execution_exclusion(root, create=False) as lease:
            owner = ownership._owner(lease)
    except (ValueError, OSError) as exc:
        return {"ok": False, "status": "ownership_unavailable", "error": str(exc)}
    if not owner or owner.get("session_id") != sid or owner.get("state") != "OWNED":
        return {"ok": True, "status": "no_prepared_candidate"}
    return None


def _protected_closeout(root: Path, sid: str, transcript: Path | None, framework_root: Path) -> dict[str, Any]:
    """The same protected, receipt-producing entry Codex's native Stop uses; it alone releases R2."""
    command = [sys.executable, str(framework_root / "governance_tools" / "session_closeout_entry.py"),
               "--project-root", str(root), "--format", "json", "--agent-id", "copilot",
               "--trigger-mode", "native_hook", "--session-id", sid]
    completed = subprocess.run(
        command, input=json.dumps({"session_id": sid, "transcript_path": str(transcript) if transcript else None}),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    try:
        entry = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        entry = {}
    return {
        "ok": completed.returncode == 0,
        "status": "closeout_invoked",
        "closeout_exit_code": completed.returncode,
        "closeout_status": entry.get("closeout_status"),
        "closeout_error": entry.get("error"),
        "closeout_receipt_artifact": entry.get("closeout_receipt_artifact"),
    }


def _agent_stop(normalized: dict[str, Any], framework_root: Path) -> dict[str, Any]:
    """VS Code Stop: an execution point for an already prepared closeout, nothing more.

    Stop fires at the end of every agent turn and is not session end. It never prepares
    a candidate, never releases ownership by itself and never treats task DONE as the
    end of the session. Only when this VS Code session is the R2 owner of a prepared
    candidate does it run the same protected entry Codex's native Stop uses, which
    validates identity, transcript and release proof again and fails closed.
    """
    root = normalized["project_root"]
    sid = normalized["session_id"]
    from runtime_hooks.core._canonical_closeout import read_session_envelope

    envelope = read_session_envelope(sid, root) or {}
    if envelope.get("schema_version") != "1.1" or envelope.get("provider") != VSCODE_PROVIDER:
        return {"ok": True, "status": "no_governed_vscode_identity"}
    not_prepared = _prepared_owner(root, sid)
    if not_prepared is not None:
        return not_prepared
    return _protected_closeout(root, sid, normalized["transcript_path"], framework_root)


def _prepared_session_end(normalized: dict[str, Any], framework_root: Path) -> dict[str, Any] | None:
    """Session end of a root-bound Copilot session that prepared an R2 candidate (review on #297).

    Root-bound Copilot CLI sessions can now prepare, so their sessionEnd must release R2
    through the protected entry; the direct session_end hook never produces release proof
    and would leave the owner OWNED. The transcript is the runtime's own record of the
    session (session-state/<id>/events.jsonl) when the payload names none; the entry
    validates it exactly as for VS Code. None means no prepared candidate: the existing
    session_end path runs unchanged.
    """
    root = normalized["project_root"]
    sid = normalized["session_id"]
    try:
        from runtime_hooks.core._canonical_closeout import read_session_envelope
        from governance_tools import copilot_session_state
    except ModuleNotFoundError:
        return None
    envelope = read_session_envelope(sid, root) or {}
    if envelope.get("schema_version") != "1.1" or envelope.get("provider") not in COPILOT_PROVIDERS:
        return None
    not_prepared = _prepared_owner(root, sid)
    if not_prepared is not None:
        # Nothing prepared: the existing path. R2 busy: fail closed rather than run a
        # closeout that cannot release while another closeout holds the lock.
        return None if not_prepared["status"] == "no_prepared_candidate" else not_prepared
    transcript = normalized["transcript_path"]
    if transcript is None:
        transcript = copilot_session_state.session_state_dir(sid) / "events.jsonl"
    return _protected_closeout(root, sid, transcript, framework_root)


def _session_id_context(result: dict[str, Any]) -> dict[str, Any]:
    """Tell a VS Code Copilot agent its own platform session id (owner ruling 2026-11-12).

    VS Code gives the agent no session id, yet formal closeout preparation needs it.
    Only after this hook has established or preserved a root-bound github-copilot-vscode
    identity does the hook hand the platform's id to the conversation, through the
    documented top-level SessionStart output, additionalContext, of the GitHub Copilot
    hook format that the shared registration uses. It only informs the agent; it
    proves nothing. R2 still checks the platform-created envelope,
    repository, transcript and ownership on its own.
    """
    if (result.get("provider") != VSCODE_PROVIDER
            or result.get("session_envelope_binding") != "root_bound"):
        return {}
    note = (
        f"AI Governance: the platform session id of this VS Code Copilot session is "
        f"{result['session_id']}. The SessionStart hook bound it to {result['project_root']}. "
        "Use it as <session-id> for prepare_closeout_candidate.py, and only at an "
        "owner-authorized closeout (AGENTS.base.md, Session Closeout Obligation); never take "
        "an id from artifacts/runtime/.current-session-id. After PREPARED, the VS Code Stop "
        "hook runs the formal closeout after your turn: report PREPARED / PENDING_HOOK, and do "
        "not run manual_fallback. Only R2 evidence (valid closeout, RELEASED ownership) "
        "confirms success. This note is not proof of identity."
    )
    return {"additionalContext": note}


def _legacy_vscode_envelope(
    session_id: str,
    project_root: Path,
    *,
    provider: str,
    require_existing: bool,
) -> dict[str, Any]:
    """A framework without root-bound support: its legacy v1.0 envelope, under
    the same identity rules as the bound path."""
    envelope = _preserving_envelope(
        session_id, project_root, provider=provider, require_existing=require_existing,
    )
    return {**envelope, "binding_reason": _LEGACY_REASON}


def _preserving_envelope(
    session_id: str,
    project_root: Path,
    *,
    provider: str,
    require_existing: bool,
) -> dict[str, Any]:
    """A v1.0 envelope under the bound path's identity rules.  An existing
    identity is preserved, never rewritten; one owned by another provider is
    refused; and resume/compact never invents an identity."""
    session_dir = project_root / "artifacts/runtime/sessions" / session_id
    path = session_dir / "session-envelope.json"
    if session_dir.is_symlink() or path.is_symlink():
        raise ValueError("Envelope path escapes project root")
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = None
        if not isinstance(existing, dict) or existing.get("session_id") != session_id:
            raise ValueError("Existing envelope is invalid; refusing to overwrite")
        if existing.get("provider") != provider:
            raise ValueError("Session identity belongs to another provider; refusing to adopt it")
        # Like the root-bound path: the resumed session owns the current-session
        # pointer again, which session end resolves without an explicit id.  A
        # framework older than that pointer never refreshed it on start either.
        from runtime_hooks.core import _canonical_closeout

        write_pointer = getattr(_canonical_closeout, "_write_current_session_id_payload", None)
        if write_pointer is not None:
            write_pointer(session_id, project_root / "artifacts/runtime/.current-session-id")
        return {**existing, "artifact_path": str(path), "envelope_status": "preserved"}
    if require_existing:
        raise ValueError("Existing envelope required for resume/compact; no start time invented")
    from runtime_hooks.core._canonical_closeout import write_session_envelope

    return write_session_envelope(session_id, project_root, provider=provider)


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

    if event_type == "agent_stop":
        return {**common, **_agent_stop(normalized, framework_root)}

    if event_type == "session_start":
        envelope = _write_session_envelope(
            normalized["session_id"],
            normalized["project_root"],
            provider=normalized["provider"],
            hook_event_name=normalized["hook_event_name"],
            source=payload.get("source"),
        )
        result = {
            **common,
            "provider": envelope.get("provider", common["provider"]),
            "ok": True,
            "status": (
                "session_envelope_preserved"
                if envelope.get("envelope_status") == "preserved"
                else "session_envelope_written"
            ),
            "session_envelope_path": envelope.get("artifact_path"),
            "session_envelope_binding": (
                "root_bound" if envelope.get("schema_version") == "1.1" else "legacy"
            ),
            **({"session_envelope_binding_reason": envelope["binding_reason"]}
               if envelope.get("binding_reason") else {}),
        }
        result.update(_session_id_context(result))
        return result

    prepared = _prepared_session_end(normalized, framework_root)
    if prepared is not None:
        return {**common, **prepared}

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
    parser.add_argument("--event-type", required=True, choices=("session_start", "session_end", "agent_stop"))
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
