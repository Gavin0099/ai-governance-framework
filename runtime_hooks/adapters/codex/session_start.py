"""Codex SessionStart identity adapter; does not run closeout or change Stop."""
from __future__ import annotations

import argparse
import base64
import json
import shlex
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime_hooks.core._canonical_closeout import (
    _git_toplevel as _root,
    establish_root_bound_session,
)


def run(payload: dict, project_root: Path) -> dict:
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
        raise ValueError("Expected a SessionStart payload")
    source = payload.get("source")
    if source not in {"startup", "clear", "resume", "compact"}:
        raise ValueError("Unsupported SessionStart source")
    # Identity checks are shared with every root-bound provider; see
    # establish_root_bound_session for what is enforced.
    return establish_root_bound_session(
        session_id=payload.get("session_id"),
        cwd=payload.get("cwd"),
        installed_root=project_root,
        provider="codex",
        require_existing=source in {"resume", "compact"},
        lock_name=".codex-start.lock",
    )


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
