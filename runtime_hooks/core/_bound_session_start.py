"""Provider-neutral creation of a consumer-root-bound session identity; never runs closeout."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from runtime_hooks.core._canonical_closeout import (
    _write_current_session_id_payload,
    read_session_envelope,
    write_session_envelope,
)

_SAFE_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
_RESERVED_DEVICE = re.compile(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", re.IGNORECASE)


def git_toplevel(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("An existing absolute project root is required")
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=True, timeout=5)
    return Path(result.stdout.strip()).resolve()


def establish_bound_session(
    sid: object,
    project_root: Path,
    cwd: object,
    *,
    provider: str,
    lock_name: str,
    require_existing: bool = False,
) -> dict:
    """Create or preserve one root-bound envelope; existing identity is never rebound."""
    if not isinstance(sid, str) or not _SAFE_SESSION_ID.fullmatch(sid) or _RESERVED_DEVICE.fullmatch(sid):
        raise ValueError("Missing or unsafe session_id; identity is never generated here")
    expected = project_root.resolve()
    if not isinstance(cwd, str) or git_toplevel(cwd) != expected or git_toplevel(str(expected)) != expected:
        raise ValueError("Payload cwd and installed project root do not match")
    session_dir = expected / "artifacts/runtime/sessions" / sid
    # Reject redirected artifact directories before any write.
    if session_dir.resolve() != session_dir:
        raise ValueError("Session artifact path escapes project root")
    marker = expected / "artifacts/runtime/.current-session-id"
    if marker.resolve() != marker:
        raise ValueError("Session pointer escapes project root")
    envelope_path = session_dir / "session-envelope.json"
    if envelope_path.resolve() != envelope_path:
        raise ValueError("Envelope path escapes project root")
    if not envelope_path.exists() and require_existing:
        raise ValueError("Existing envelope required for resume/compact; no start time invented")
    # Reject known invalid/wrong-root identity before even creating a lock.
    # Re-read under exclusion below so this preflight is not a TOCTOU authority.
    if envelope_path.exists() and read_session_envelope(sid, expected) is None:
        raise ValueError("Existing envelope is invalid; refusing to overwrite")
    if (not envelope_path.exists()
            and (expected / "artifacts/runtime/closeout-completions" / f"{sid}.json").exists()):
        raise ValueError("Completion marker exists without envelope")
    session_dir.mkdir(parents=True, exist_ok=True)
    # Serialize creation; existing v1.0/v1.1 identity is never migrated or rebound.
    lock = session_dir / lock_name
    try:
        fd = lock.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError("SessionStart already running; retry without resetting identity") from exc
    try:
        with fd:
            envelope = read_session_envelope(sid, expected)
            if envelope_path.exists() and envelope is None:
                raise ValueError("Existing envelope is invalid; refusing to overwrite")
            if envelope is None:
                # Completion without identity is inconsistent, never repair it implicitly.
                if (expected / "artifacts/runtime/closeout-completions" / f"{sid}.json").exists():
                    raise ValueError("Completion marker exists without envelope")
                envelope = write_session_envelope(
                    sid, expected, provider=provider, bound_consumer_root=expected,
                )
                status = "created"
            else:
                _write_current_session_id_payload(sid, marker)
                status = "preserved"
    finally:
        lock.unlink()
    return {"status": status, "session_id": sid, "project_root": str(expected),
            "session_envelope_path": envelope["artifact_path"],
            "envelope_schema_version": envelope["schema_version"]}
