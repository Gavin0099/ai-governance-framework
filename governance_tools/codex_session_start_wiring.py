"""Report-only check of the Codex SessionStart identity hook a consumer needs.

A formal closeout on request needs the schema 1.1 session identity that the
Codex SessionStart hook establishes. F-7 does not install that hook: installing
it changes the agent's lifecycle, so it stays an explicit owner decision. This
check only reports whether the hook is wired, whether it agrees with the Stop
closeout hook, and the command that would wire it. It never writes.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import shlex
from pathlib import Path
from typing import Any

from governance_tools.manage_agent_closeout import CodexCLIAdapter
from runtime_hooks.adapters.codex.session_start import SESSION_START_MATCHER

ENTRY = "runtime_hooks/adapters/codex/session_start.py"
# The installer writes `python3` and, for Windows, sys.executable (python.exe,
# python3.11, ...).
PYTHON_NAME = re.compile(r"python[0-9.]*(\.exe)?", re.IGNORECASE)
NOT_APPLICABLE = "not_applicable"
NOT_INSTALLED = "not_installed"
INSTALLED_INCORRECTLY = "installed_incorrectly"
INSTALLED_CORRECTLY = "installed_correctly"
CLAIM_BOUNDARY = (
    "configuration only; not proof that Codex trusts or runs the hook, "
    "or that a closeout will succeed"
)


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(Path(right).resolve()))
    except (OSError, ValueError, TypeError):
        return False


def _powershell_tokens(script: str) -> list[str]:
    """Split the installer's PowerShell script by PowerShell's own quoting.

    POSIX splitting would read the `''` that PowerShell uses for an apostrophe
    inside single quotes as two empty quotes and drop the apostrophe.
    """
    tokens: list[str] = []
    word: list[str] | None = None
    index = 0
    while index < len(script):
        char = script[index]
        if char in " \t\r\n;":
            if word is not None:
                tokens.append("".join(word))
                word = None
            if char == ";":
                tokens.append(";")
            index += 1
        elif char == "'":
            word = word or []
            index += 1
            while True:
                if index >= len(script):
                    raise ValueError("unterminated single quote")
                if script[index] == "'":
                    if script[index + 1:index + 2] == "'":
                        word.append("'")
                        index += 2
                        continue
                    index += 1
                    break
                word.append(script[index])
                index += 1
        else:
            word = (word or []) + [char]
            index += 1
    if word is not None:
        tokens.append("".join(word))
    return tokens


def _field_tokens(hook: dict[str, Any]) -> list[tuple[str, list[str] | None, str]]:
    """(field, tokens, text) for the POSIX command and the decoded Windows command.

    tokens is None when the command cannot be parsed; text is still returned so
    a malformed binding is recognised rather than mistaken for a missing one.
    """
    found: list[tuple[str, list[str] | None, str]] = []
    for field in ("command", "commandWindows"):
        command = hook.get(field)
        if not isinstance(command, str):
            continue
        text = command
        try:
            outer = shlex.split(command)
            if len(outer) == 4 and outer[:3] == ["powershell", "-NoProfile", "-EncodedCommand"]:
                text = base64.b64decode(outer[3], validate=True).decode("utf-16-le")
                tokens = _powershell_tokens(text)
            else:
                tokens = outer
        except (ValueError, UnicodeError, binascii.Error):
            found.append((field, None, text))
            continue
        found.append((field, tokens, text))
    return found


def _is_python(token: str) -> bool:
    return PYTHON_NAME.fullmatch(token.replace("\\", "/").rsplit("/", 1)[-1]) is not None


def _binding(tokens: list[str]) -> tuple[str, str | None] | None:
    """(entry, project root) when the command runs the identity entry, else None.

    Only the installer's invocation forms count: `python3 <entry> ...` and
    PowerShell's `& <python> <entry> ...`, optionally with -B. A command that
    merely mentions the entry (for example `echo <entry>`) does not run it.
    """
    start = 1 if tokens[:1] == ["&"] else 0
    if len(tokens) <= start + 1 or not _is_python(tokens[start]):
        return None
    index = start + 2 if tokens[start + 1] == "-B" else start + 1
    if index >= len(tokens) or not tokens[index].replace("\\", "/").endswith("/" + ENTRY):
        return None
    rest = tokens[index + 1:]
    if "--project-root" in rest[:-1]:
        return tokens[index], rest[rest.index("--project-root") + 1]
    return tokens[index], None


def _owned(hook: Any) -> bool:
    # Same textual ownership the installer uses: a hook that names the entry is
    # one the installer refuses to replace, so it is never reported as missing,
    # whether or not it actually runs the entry.
    return isinstance(hook, dict) and any(
        ENTRY in text.replace("\\", "/") for _, _tokens, text in _field_tokens(hook)
    )


def _groups(hooks: dict[str, Any], event: str) -> list[dict[str, Any]]:
    groups = hooks.get(event)
    return [g for g in groups if isinstance(g, dict)] if isinstance(groups, list) else []


def _hook_list(group: dict[str, Any]) -> list[Any]:
    hooks = group.get("hooks")
    return hooks if isinstance(hooks, list) else []


def _stop_wiring(hooks: dict[str, Any], framework_root: Path) -> str:
    governance = [
        hook
        for group in _groups(hooks, "Stop")
        for hook in _hook_list(group)
        if CodexCLIAdapter._is_governance_hook(hook)
    ]
    if not governance:
        return "not_found"
    if len(governance) == 1 and CodexCLIAdapter._is_current_hook(governance[0], framework_root):
        return "consistent"
    return "inconsistent"


def _has_session_end_publisher(hooks: dict[str, Any]) -> bool:
    return any(
        tokens is not None
        and any(t.replace("\\", "/").endswith("/governance_tools/native_closeout_publisher.py") for t in tokens)
        for group in _groups(hooks, "SessionEnd")
        for hook in _hook_list(group)
        if isinstance(hook, dict)
        for _, tokens, _text in _field_tokens(hook)
    )


def _session_start_reasons(hooks: dict[str, Any], repo_root: Path, framework_root: Path) -> list[str]:
    expected_entry = framework_root / ENTRY
    reasons: list[str] = []
    owned = [
        (group, hook)
        for group in _groups(hooks, "SessionStart")
        for hook in _hook_list(group)
        if _owned(hook)
    ]
    if len(owned) > 1:
        reasons.append(f"{len(owned)} identity hooks are registered under SessionStart; expected one")
    for group, hook in owned:
        if group.get("matcher") != SESSION_START_MATCHER:
            reasons.append(
                f"SessionStart matcher is {group.get('matcher')!r}; expected {SESSION_START_MATCHER!r}"
            )
        for field, tokens, _text in _field_tokens(hook):
            if tokens is None:
                reasons.append(f"SessionStart {field} cannot be decoded")
                continue
            bound = _binding(tokens)
            if bound is None:
                reasons.append(f"SessionStart {field} does not run the identity entry")
                continue
            entry, root = bound
            if not _same_path(entry, expected_entry):
                reasons.append(f"SessionStart {field} runs {entry}, not this framework checkout's entry")
            if root is None or not _same_path(root, repo_root):
                reasons.append(f"SessionStart {field} binds project root {root}, not this consumer")
    return reasons


def assess_codex_session_start(repo_root: Path, framework_root: Path) -> dict[str, Any]:
    repo_root, framework_root = Path(repo_root).resolve(), Path(framework_root).resolve()
    path = repo_root / ".codex" / "hooks.json"
    report: dict[str, Any] = {
        "report_only": True,
        "status": NOT_APPLICABLE,
        "stop_wiring": NOT_APPLICABLE,
        "reasons": [],
        "repair": None,
        "stop_repair": None,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if not path.is_file():
        report["reasons"] = ["no .codex/hooks.json; this consumer does not declare Codex use"]
        return report
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        report.update(
            status=INSTALLED_INCORRECTLY,
            stop_wiring="not_verified",
            reasons=[f".codex/hooks.json cannot be read ({type(exc).__name__})"],
            repair="fix .codex/hooks.json by hand; no installer is run on an unreadable file",
        )
        return report
    hooks = data.get("hooks") if isinstance(data, dict) else None
    hooks = hooks if isinstance(hooks, dict) else {}

    misplaced = sorted(
        event
        for event in hooks
        if event != "SessionStart"
        for group in _groups(hooks, event)
        for hook in _hook_list(group)
        if _owned(hook)
    )
    reasons = [f"identity hook is registered under {event}, not SessionStart" for event in misplaced]
    has_session_start = any(_owned(hook) for group in _groups(hooks, "SessionStart") for hook in _hook_list(group))
    reasons.extend(_session_start_reasons(hooks, repo_root, framework_root))
    if not has_session_start and not misplaced:
        report["status"] = NOT_INSTALLED
        report["reasons"] = ["no Codex SessionStart identity hook; formal closeout on request will be rejected"]
        report["repair"] = (
            f'python "{(framework_root / ENTRY).as_posix()}" --project-root "{repo_root.as_posix()}" --install'
        )
    elif reasons:
        report["status"] = INSTALLED_INCORRECTLY
        report["reasons"] = reasons
        report["repair"] = (
            "review the identity hook in .codex/hooks.json; the installer refuses to replace "
            "a differing binding, and custom hooks are never rewritten"
        )
    else:
        report["status"] = INSTALLED_CORRECTLY

    report["stop_wiring"] = _stop_wiring(hooks, framework_root)
    if report["stop_wiring"] == "not_found" and _has_session_end_publisher(hooks):
        # The SessionEnd publisher only publishes a request; adding a Stop
        # closeout next to it would be a second, different closeout path.
        report["stop_repair"] = (
            "a SessionEnd closeout publisher is wired instead of a Stop closeout hook; "
            "review that path before adding a Stop hook"
        )
    elif report["stop_wiring"] != "consistent":
        report["stop_repair"] = (
            f'from "{framework_root.as_posix()}": python -m governance_tools.manage_agent_closeout '
            f'--project-root "{repo_root.as_posix()}" install --agent codex'
        )
    return report


def diagnostic_warnings(report: dict[str, Any]) -> list[str]:
    """f7-diagnostic lines for a gap; empty when the consumer does not use Codex or is wired."""
    warnings: list[str] = []
    status = report.get("status")
    if status == NOT_INSTALLED:
        warnings.append(
            "codex SessionStart identity hook is not installed; formal closeout on request needs it. "
            f"Install only with the owner's approval: {report.get('repair')}"
        )
    elif status == INSTALLED_INCORRECTLY:
        warnings.append(
            "codex SessionStart identity hook is installed incorrectly: "
            + "; ".join(report.get("reasons") or [])
        )
    if status not in (NOT_APPLICABLE, None) and report.get("stop_wiring") != "consistent":
        warnings.append(
            f"codex Stop closeout hook is {report.get('stop_wiring')} for this framework checkout; "
            f"SessionStart and Stop must use the same checkout. With the owner's approval: "
            f"{report.get('stop_repair')}"
        )
    return warnings


def format_stage(report: dict[str, Any]) -> list[str]:
    lines = [
        f"codex_session_start={report.get('status')}",
        f"codex_session_start.stop_wiring={report.get('stop_wiring')}",
    ]
    lines.extend(f"codex_session_start.reason={reason}" for reason in report.get("reasons") or [])
    for key in ("repair", "stop_repair"):
        if report.get(key):
            lines.append(f"codex_session_start.{key}={report[key]}")
    lines.append(f"codex_session_start.claim_boundary={report.get('claim_boundary')}")
    return lines
