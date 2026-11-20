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

from runtime_hooks.core._bound_session_start import establish_bound_session, git_toplevel


_root = git_toplevel
# Every source re-binds the same identity; resume and compact must keep firing.
SESSION_START_MATCHER = "^(startup|resume|clear|compact)$"


def run(payload: dict, project_root: Path) -> dict:
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
        raise ValueError("Expected a SessionStart payload")
    source = payload.get("source")
    if source not in {"startup", "clear", "resume", "compact"}:
        raise ValueError("Unsupported SessionStart source")
    return establish_bound_session(
        payload.get("session_id"), project_root, payload.get("cwd"),
        provider="codex", lock_name=".codex-start.lock",
        require_existing=source in {"resume", "compact"},
    )


FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
_PORTABLE_REL = re.compile(r"[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*")


def portable_framework_path(project_root: Path | None, framework_root: Path) -> str | None:
    """Framework checkout path relative to the consumer root, or None.

    A hook that names this relative path and resolves the repository root at
    run time carries no machine-, user- or clone-specific path, so the consumer
    can commit it (#288). Only plain path characters are accepted, so the path
    needs no quoting in either shell; anything else keeps the absolute form.
    """
    if project_root is None:
        return None
    try:
        rel = Path(framework_root).resolve().relative_to(Path(project_root).resolve()).as_posix()
    except (ValueError, OSError):
        return None
    if rel in ("", ".") or not _PORTABLE_REL.fullmatch(rel) or ".." in rel.split("/"):
        return None
    return rel


# The resolved repository must itself declare Codex hooks. Without this, a hook
# run from inside a nested repository that has no .codex/hooks.json would run
# that repository's copy of the entry instead of the consumer's (#288 review).
POSIX_ROOT = (
    'repo_root="$(git rev-parse --show-toplevel)" && '
    '[ -f "$repo_root/.codex/hooks.json" ] && '
)


def windows_python_prologue(purpose: str) -> str:
    """Resolve the repository root and a Python at run time (no sys.executable)."""
    return (
        "$repo = git rev-parse --show-toplevel; "
        "if (-not (Test-Path (Join-Path $repo '.codex\\hooks.json'))) "
        "{ Write-Error 'The resolved repository has no .codex/hooks.json'; exit 1 }; "
        "$candidates = @((Join-Path $repo '.venv-ci\\Scripts\\python.exe'), "
        "(Join-Path $repo '.venv\\Scripts\\python.exe')); "
        "$python = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1; "
        "if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }; "
        f"if (-not $python) {{ Write-Error 'No Python interpreter found for {purpose}'; exit 1 }}; "
    )


def encode_powershell(script: str) -> str:
    return "powershell -NoProfile -EncodedCommand " + base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def portable_hook_payload(project_root: Path, framework_root: Path | None = None) -> dict | None:
    rel = portable_framework_path(project_root, framework_root if framework_root is not None else FRAMEWORK_ROOT)
    if not rel:
        return None
    entry = f"{rel}/runtime_hooks/adapters/codex/session_start.py"
    posix = POSIX_ROOT + f'python3 "$repo_root/{entry}" --project-root "$repo_root"'
    script = (
        windows_python_prologue("Codex SessionStart")
        + f'& $python "$repo/{entry}" --project-root $repo; exit $LASTEXITCODE'
    )
    return {"type": "command", "command": posix, "commandWindows": encode_powershell(script),
            "timeout": 30, "statusMessage": "Establishing governance session identity..."}


def hook_payload(project_root: Path) -> dict:
    """Absolute form, kept for a framework checkout outside the consumer and
    as an accepted existing binding."""
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
    portable = portable_hook_payload(root)
    expected = {"matcher": SESSION_START_MATCHER, "hooks": [portable or hook_payload(root)]}
    # An existing absolute binding for this checkout stays accepted; it is not rewritten.
    accepted = [expected, {"matcher": SESSION_START_MATCHER, "hooks": [hook_payload(root)]}]
    owned = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
            raise ValueError("Invalid SessionStart group")
        for h in group.get("hooks", []):
            if isinstance(h, dict) and "runtime_hooks/adapters/codex/session_start.py" in str(h.get("command", "")).replace("\\", "/"):
                owned.append(group)
    if owned:
        if len(owned) == 1 and owned[0] in accepted:
            return {"status": "already_installed", "path": str(path)}
        raise ValueError("Existing SessionStart binding differs; review before replacing")
    groups.append(expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result = {"status": "installed", "path": str(path), "portable": portable is not None}
    if portable is None:
        result["note"] = ("absolute paths: the framework checkout is outside the consumer or its path "
                          "needs shell quoting, so this hook is not portable to another machine or clone")
    return result


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
