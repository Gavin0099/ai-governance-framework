"""Read-only Codex hook trust reporting using the local app-server protocol."""

from __future__ import annotations

import argparse
import json
import math
import ntpath
import os
import posixpath
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path


_EVENTS = (
    "PreModelRequest", "PostModelRequest", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PreCompact", "PostCompact", "SessionStart", "SessionEnd",
    "UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop", "Interrupt",
)
_EVENT_KEYS = {event: re.sub(r"(?<!^)(?=[A-Z])", "_", event).lower() for event in _EVENTS}
_EXPECTED_EVENTS = ("SessionStart", "Stop")
_TRUST_STATES = {
    "trusted": "installed_trusted", "managed": "installed_trusted",
    "untrusted": "installed_untrusted", "modified": "installed_modified",
}
STATE_MEANINGS = {
    "not_installed": "未安裝",
    "installed_not_loaded": "定義存在，但 Codex 未載入",
    "installed_untrusted": "已安裝但未信任",
    "installed_modified": "信任後定義已變更，Codex 會略過",
    "installed_trusted": "信任前置條件已滿足",
    "trust_unknown": "信任狀態未驗證",
}
CLAIM_BOUNDARY = (
    "Trusted does not mean executed or closed out; existing R1/R2 evidence "
    "decides execution and closeout. This diagnostic never trusts or executes hooks."
)


class _ProbeError(Exception):
    pass


def diagnostic_command(repo_root: str | Path) -> str:
    repo = str(repo_root)
    quoted = "'" + repo.replace("'", "''") + "'" if os.name == "nt" else shlex.quote(repo)
    return "python -X utf8 -m governance_tools.codex_hook_trust_status --repo " + quoted


def _path_identity(path: str) -> str:
    if ntpath.isabs(path) and (ntpath.splitdrive(path)[0] or path.startswith("\\\\")):
        return "windows:" + ntpath.normcase(ntpath.normpath(path))
    if path.startswith("/"):
        return "posix:" + posixpath.normpath(path)
    raise _ProbeError("Expected an absolute path in the hooks/list response.")


def _hook_identity(key: str) -> tuple[str, str, int, int]:
    # Split from the right: a Windows drive letter also contains a colon.
    parts = key.rsplit(":", 3)
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        raise _ProbeError("Unexpected hook key in the hooks/list response.")
    return _path_identity(parts[0]), parts[1], int(parts[2]), int(parts[3])


def _row(event: str, group: int | None, hook: int | None, state: str, reason: str) -> dict:
    return {
        "event": event, "group_index": group, "hook_index": hook,
        "state": state, "enabled": None, "trust_status": None,
        "current_hash": None, "adopted": False, "reason": reason,
    }


def _missing_rows(state: str, reason: str) -> list[dict]:
    return [_row(event, None, None, state, reason) for event in _EXPECTED_EVENTS]


def _configured_rows(raw: bytes) -> list[dict]:
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        raise ValueError("Unexpected hooks file format")
    rows = []
    for event, groups in data["hooks"].items():
        if event not in _EVENT_KEYS or not isinstance(groups, list):
            raise ValueError("Unexpected hook event or groups")
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError("Unexpected hook group")
            for hook_index, hook in enumerate(group["hooks"]):
                if not isinstance(hook, dict):
                    raise ValueError("Unexpected hook definition")
                rows.append(_row(event, group_index, hook_index, "trust_unknown",
                                 "Run the diagnostic CLI to query Codex hooks/list."))
    present = {row["event"] for row in rows}
    rows.extend(_row(event, None, None, "not_installed", "No hook definition for this event.")
                for event in _EXPECTED_EVENTS if event not in present)
    return rows


def _resolve_codex(explicit: str | Path | None) -> list[str]:
    selected = str(explicit) if explicit is not None else os.environ.get("CODEX_BINARY")
    binary = shutil.which(selected) if selected else shutil.which("codex")
    if not binary:
        raise _ProbeError("Codex binary unavailable; use --codex or CODEX_BINARY, or add codex to PATH.")
    return [str(Path(binary).resolve())]


def _exchange(proc: subprocess.Popen, repo: str) -> dict:
    def send(message: dict) -> None:
        proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        proc.stdin.flush()

    def receive(request_id: int):
        while True:
            line = proc.stdout.readline(1024 * 1024 + 1)
            if not line or len(line) > 1024 * 1024:
                raise _ProbeError("App-server closed its output or returned an oversized reply.")
            message = json.loads(line)
            if not isinstance(message, dict):
                raise _ProbeError("Unexpected JSON-RPC reply.")
            if "id" not in message and isinstance(message.get("method"), str):
                continue  # Protocol notifications may precede a reply.
            if (type(message.get("id")) is not int or message["id"] != request_id
                    or "result" not in message or "error" in message):
                raise _ProbeError("App-server error or unexpected JSON-RPC reply.")
            return message["result"]

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"clientInfo": {"name": "governance-hook-trust", "version": "1"}}})
    if not isinstance(receive(1), dict):
        raise _ProbeError("Unexpected initialize response.")
    send({"jsonrpc": "2.0", "method": "initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "hooks/list", "params": {"cwds": [repo]}})
    return receive(2)


def _query_hooks(repo: Path, command: list[str], timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    try:
        proc = subprocess.Popen(
            [*command, "app-server"], cwd=repo, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        raise _ProbeError("Could not start the local Codex app-server.") from None
    replies = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            replies.put((_exchange(proc, str(repo)), None))
        except (_ProbeError, ValueError, OSError) as exc:
            reason = str(exc) if isinstance(exc, _ProbeError) else "Malformed or unreadable app-server reply."
            replies.put((None, reason))

    reader = threading.Thread(target=worker, daemon=True)
    try:
        reader.start()
        try:
            response, error = replies.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            raise _ProbeError("Codex app-server timed out.") from None
        if error:
            raise _ProbeError(error)
        return response
    finally:
        # Kill even after a successful reply: app-server normally stays running.
        try:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=1)
        finally:
            if reader.ident is not None:
                reader.join(timeout=1)
            proc.stdin.close()
            proc.stdout.close()


def _apply_response(rows: list[dict], repo: str, hooks_path: str, response: dict) -> None:
    if not isinstance(response, dict) or not isinstance(response.get("data"), list):
        raise _ProbeError("Unexpected hooks/list response format.")
    entries = response["data"]
    if any(not isinstance(e, dict) or not isinstance(e.get("cwd"), str) for e in entries):
        raise _ProbeError("Unexpected hooks/list cwd entry.")
    matching = [e for e in entries if _path_identity(e["cwd"]) == _path_identity(repo)]
    if len(matching) != 1:
        raise _ProbeError("hooks/list did not return exactly one entry for the requested cwd.")
    entry = matching[0]
    if (not isinstance(entry.get("hooks"), list) or not isinstance(entry.get("errors"), list)
            or not isinstance(entry.get("warnings"), list) or entry["errors"]):
        raise _ProbeError("hooks/list reported load errors or an unexpected entry format.")
    hooks_identity = _path_identity(hooks_path)
    by_key = {}
    for metadata in entry["hooks"]:
        if (not isinstance(metadata, dict)
                or any(not isinstance(metadata.get(k), str) or not metadata[k]
                       for k in ("key", "sourcePath", "eventName", "currentHash", "source"))
                or type(metadata.get("enabled")) is not bool
                or not isinstance(metadata.get("trustStatus"), str)
                or metadata.get("trustStatus") not in _TRUST_STATES):
            raise _ProbeError("Unexpected hook metadata in hooks/list.")
        if _path_identity(metadata["sourcePath"]) != hooks_identity:
            continue
        identity = _hook_identity(metadata["key"])
        if identity[0] != hooks_identity or identity in by_key:
            raise _ProbeError("Ambiguous hook identity in hooks/list.")
        by_key[identity] = metadata
    for row in rows:
        if row["state"] == "not_installed":
            continue
        identity = (hooks_identity, _EVENT_KEYS[row["event"]], row["group_index"], row["hook_index"])
        metadata = by_key.get(identity)
        if metadata is None:
            row.update(state="installed_not_loaded", reason="Codex did not return this configured hook.")
            continue
        event_name = row["event"][0].lower() + row["event"][1:]
        if metadata["eventName"] != event_name:
            raise _ProbeError("Hook event and key disagree in hooks/list.")
        state = _TRUST_STATES[metadata["trustStatus"]]
        row.update(state=state, enabled=metadata["enabled"], trust_status=metadata["trustStatus"],
                   current_hash=metadata["currentHash"],
                   adopted=state == "installed_trusted" and metadata["enabled"],
                   reason="Codex hooks/list trust status; enabled is reported separately.")


def inspect_codex_hook_trust(
    repo_root: str | Path, *, codex_binary: str | Path | None = None,
    timeout_seconds: float = 5.0, query_server: bool = True,
) -> dict:
    repo = Path(repo_root).resolve()
    path = repo / ".codex" / "hooks.json"
    attempted = False
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        rows = _missing_rows("not_installed", "No repository .codex/hooks.json file.")
    except OSError:
        rows = _missing_rows("trust_unknown", "Cannot read repository .codex/hooks.json.")
    else:
        try:
            rows = _configured_rows(raw)
        except (ValueError, UnicodeError):
            rows = _missing_rows("trust_unknown", "Malformed or unsupported .codex/hooks.json.")
        else:
            if query_server and any(row["state"] != "not_installed" for row in rows):
                try:
                    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
                        raise _ProbeError("Timeout must be finite and greater than zero.")
                    command = _resolve_codex(codex_binary)
                    attempted = True
                    response = _query_hooks(repo, command, timeout_seconds)
                    if path.read_bytes() != raw:
                        raise _ProbeError("Hook definitions changed during the probe; run it again.")
                    _apply_response(rows, str(repo), str(path), response)
                except (_ProbeError, OSError, subprocess.TimeoutExpired) as exc:
                    reason = str(exc) if isinstance(exc, _ProbeError) else "App-server probe or cleanup failed."
                    for row in rows:
                        if row["state"] != "not_installed":
                            row.update(state="trust_unknown", enabled=None, trust_status=None,
                                       current_hash=None, adopted=False, reason=reason)
    states = {row["state"] for row in rows}
    priority = ("trust_unknown", "installed_modified", "installed_untrusted",
                "installed_not_loaded", "not_installed", "installed_trusted")
    return {
        "report_only": True, "probe_attempted": attempted,
        "state": next(state for state in priority if state in states),
        "adopted": all(row["adopted"] for row in rows), "hooks": rows,
        "diagnostic_command": diagnostic_command(repo), "claim_boundary": CLAIM_BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--codex", help="Local binary; otherwise CODEX_BINARY, then PATH")
    parser.add_argument("--timeout", type=float, default=5.0, help="Whole-probe timeout in seconds")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and greater than zero")
    report = inspect_codex_hook_trust(args.repo, codex_binary=args.codex, timeout_seconds=args.timeout)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for row in report["hooks"]:
            identity = row["event"]
            if row["group_index"] is not None:
                identity += f"[{row['group_index']}:{row['hook_index']}]"
            print(f"{identity}: "
                  f"{row['state']} — {STATE_MEANINGS[row['state']]}; "
                  f"enabled={row['enabled']}; adopted={row['adopted']}")
            print("  " + row["reason"])
        print(report["claim_boundary"])
    return 0  # Diagnostic states never introduce a blocking gate.


if __name__ == "__main__":
    raise SystemExit(main())
