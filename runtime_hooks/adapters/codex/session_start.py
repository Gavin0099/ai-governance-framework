"""Codex SessionStart identity adapter; does not run closeout or change Stop."""
from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime_hooks.core._canonical_closeout import (
    _write_current_session_id_payload,
    read_session_envelope,
    write_session_envelope,
)


def _root(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("An existing absolute project root is required")
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=True, timeout=5)
    return Path(result.stdout.strip()).resolve()


def run(payload: dict, project_root: Path) -> dict:
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
        raise ValueError("Expected a SessionStart payload")
    source = payload.get("source")
    if source not in {"startup", "clear", "resume", "compact"}:
        raise ValueError("Unsupported SessionStart source")
    sid = payload.get("session_id")
    if (not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", sid)
            or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", sid, re.IGNORECASE)):
        raise ValueError("Missing or unsafe session_id; identity is never generated here")
    expected = project_root.resolve()
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or _root(cwd) != expected or _root(str(expected)) != expected:
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
    if not envelope_path.exists() and source in {"resume", "compact"}:
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
    lock = session_dir / ".codex-start.lock"
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
                    sid, expected, provider="codex", bound_consumer_root=expected,
                )
                status = "created"
            else:
                _write_current_session_id_payload(sid, marker)
                status = "preserved"
    finally:
        lock.unlink()
    return {"status": status, "session_id": sid, "project_root": str(expected),
            "session_envelope_path": envelope["artifact_path"]}


def hook_payload(project_root: Path) -> dict:
    entry = Path(__file__).resolve()
    args = [str(entry), "--project-root", str(project_root.resolve())]
    posix = "python3 " + shlex.join(args)
    def psquote(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"
    script = "& " + psquote(sys.executable) + " " + " ".join(map(psquote, args)) + "; exit $LASTEXITCODE"
    windows = "powershell -NoProfile -EncodedCommand " + base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return {"type": "command", "command": posix, "commandWindows": windows,
            "timeout": 30, "statusMessage": "Establishing governance session identity..."}


def install(project_root: Path) -> dict:
    root = project_root.resolve()
    if _root(str(root)) != root:
        raise ValueError("Install at the Git project root")
    path = root / ".codex/hooks.json"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Hook configuration escapes project root")
    data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    hooks = data.setdefault("hooks", {})
    groups = hooks.setdefault("SessionStart", [])
    if not isinstance(groups, list):
        raise ValueError("Invalid SessionStart configuration")
    expected = {"matcher": "^(startup|resume|clear|compact)$", "hooks": [hook_payload(root)]}
    owned = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
            raise ValueError("Invalid SessionStart group")
        for h in group.get("hooks", []):
            if isinstance(h, dict) and "runtime_hooks/adapters/codex/session_start.py" in str(h.get("command", "")).replace("\\", "/"):
                owned.append(group)
    if owned:
        if len(owned) == 1 and owned[0] == expected:
            return {"status": "already_installed", "path": str(path)}
        raise ValueError("Existing SessionStart binding differs; review before replacing")
    groups.append(expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": "installed", "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.project_root) if args.install else run(json.load(sys.stdin), args.project_root)
    except (ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError) as exc:
        print(json.dumps({"systemMessage": f"Governance SessionStart failed: {exc}"}))
        return 1
    # Native hook stdout uses documented fields; detail goes to stderr for audit.
    print(json.dumps(result), file=sys.stderr)
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
