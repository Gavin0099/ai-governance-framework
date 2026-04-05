#!/usr/bin/env python3
"""
manage_agent_closeout.py — Agent integration manager for session closeout.

Manages the installation, verification, repair, and status reporting of
session closeout integrations across different AI agents.

The core closeout pipeline is agent-agnostic (session_closeout_entry.py).
This tool manages how each agent *triggers* that pipeline.

Usage:
    python -m governance_tools.manage_agent_closeout status
    python -m governance_tools.manage_agent_closeout install --agent claude
    python -m governance_tools.manage_agent_closeout verify --agent claude
    python -m governance_tools.manage_agent_closeout repair --agent claude
    python -m governance_tools.manage_agent_closeout install --agent all

Supported agents and capability tiers:
    claude    Tier A — Native auto-closeout via .claude/settings.json Stop hook
    copilot   Tier B — Wrapper-based; requires VS Code task or manual command
    gemini    Tier B — Wrapper-based; requires CLI wrapper or manual command
    chatgpt   Tier C — Manual only; no local hook surface available

Tier definitions:
    A  Native auto-closeout   Agent has a formal hook/event surface; fully automated
    B  Wrapper-based          No native hook; automated via launcher/task wrapper
    C  Manual only            No reliable automation surface; user must run manually
    D  Unsupported/unknown    No stable integration path defined yet
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Agent integration manifest ────────────────────────────────────────────────

AGENT_MANIFEST: dict[str, dict[str, Any]] = {
    "claude": {
        "display_name": "Claude Code",
        "capability_tier": "A",
        "capability_label": "native_auto_closeout",
        "description": (
            "Claude Code supports a Stop hook in .claude/settings.json. "
            "The closeout pipeline runs automatically at every session end."
        ),
        "config_paths": [
            # Project-level (repo-local) — checked first
            ".claude/settings.json",
            ".claude/settings.local.json",
        ],
        "global_config_paths": [
            # User-level (applies across all projects)
            "~/.claude/settings.json",
        ],
        "install_target": ".claude/settings.json",
        "hook_command": (
            "python {framework_root}/governance_tools/session_closeout_entry.py "
            "--project-root . 2>/dev/null || true"
        ),
        "hook_status_message": "Running governance session closeout...",
        "manual_command": None,  # Not needed — fully automated
        "verification_method": "check_claude_settings_hook",
    },
    "copilot": {
        "display_name": "GitHub Copilot",
        "capability_tier": "B",
        "capability_label": "wrapper_based",
        "description": (
            "GitHub Copilot (VS Code extension or CLI) does not expose a session "
            "end hook. Closeout is triggered via a VS Code task or a wrapper script "
            "that must be run manually at session end, or configured as a task shortcut."
        ),
        "config_paths": [
            ".vscode/tasks.json",
        ],
        "install_target": ".vscode/tasks.json",
        "hook_command": None,  # No native hook
        "manual_command": (
            "python {framework_root}/governance_tools/session_closeout_entry.py "
            "--project-root ."
        ),
        "vscode_task": {
            "label": "Governance: Session Closeout",
            "type": "shell",
            "command": (
                "python {framework_root}/governance_tools/session_closeout_entry.py "
                "--project-root ${workspaceFolder}"
            ),
            "group": "none",
            "presentation": {"reveal": "always", "panel": "shared"},
            "problemMatcher": [],
        },
        "verification_method": "check_vscode_task",
        "manual_command_note": (
            "Run the VS Code task 'Governance: Session Closeout' before ending "
            "each Copilot session, or run the manual command above."
        ),
    },
    "gemini": {
        "display_name": "Gemini CLI / IDE",
        "capability_tier": "B",
        "capability_label": "wrapper_based",
        "description": (
            "Gemini CLI and IDE integrations do not expose a session end hook in "
            "a standardized way. Closeout is triggered via a wrapper script or "
            "must be run manually at session end."
        ),
        "config_paths": [
            ".gemini/settings.json",
        ],
        "install_target": ".gemini/settings.json",
        "hook_command": None,  # Check at install time — Gemini CLI may support hooks
        "manual_command": (
            "python {framework_root}/governance_tools/session_closeout_entry.py "
            "--project-root ."
        ),
        "verification_method": "check_gemini_settings",
        "manual_command_note": (
            "Run the closeout command manually before ending each Gemini session. "
            "If using Gemini CLI with hook support, re-run install to configure automatically."
        ),
        "gemini_hook_key": "sessionEndHook",  # Key to check/write in .gemini/settings.json
    },
    "chatgpt": {
        "display_name": "ChatGPT",
        "capability_tier": "C",
        "capability_label": "manual_only",
        "description": (
            "ChatGPT (web or API) does not have a local session lifecycle hook. "
            "There is no automation surface for local repo closeout. "
            "The closeout command must be run manually."
        ),
        "config_paths": [],
        "install_target": None,
        "hook_command": None,
        "manual_command": (
            "python {framework_root}/governance_tools/session_closeout_entry.py "
            "--project-root ."
        ),
        "verification_method": "manual_only",
        "manual_command_note": (
            "Before ending each ChatGPT session that modified this repo, run the "
            "closeout command above in the project directory."
        ),
    },
}

KNOWN_AGENTS = list(AGENT_MANIFEST.keys())
TIER_LABELS = {
    "A": "Native auto-closeout",
    "B": "Wrapper-based closeout",
    "C": "Manual only",
    "D": "Unsupported / unknown",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_framework_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _format_command(template: str | None, framework_root: Path) -> str | None:
    if template is None:
        return None
    return template.replace("{framework_root}", str(framework_root).replace("\\", "/"))


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── Per-agent verification ────────────────────────────────────────────────────

def _verify_claude(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Check .claude/settings.json for the governance stop hook."""
    entry_script = str(framework_root / "governance_tools" / "session_closeout_entry.py").replace("\\", "/")

    # Check project-level first, then global
    candidates = [
        project_root / ".claude" / "settings.json",
        project_root / ".claude" / "settings.local.json",
        Path.home() / ".claude" / "settings.json",
    ]

    for settings_path in candidates:
        data = _read_json_safe(settings_path)
        stop_hooks = data.get("hooks", {}).get("Stop", [])
        for group in stop_hooks:
            hooks = group.get("hooks", []) if isinstance(group, dict) else []
            for h in hooks:
                if "session_closeout_entry" in h.get("command", "") or entry_script in h.get("command", ""):
                    return {
                        "installed": True,
                        "location": str(settings_path),
                        "note": f"Stop hook found in {settings_path.name}",
                    }

    return {
        "installed": False,
        "location": None,
        "note": "No governance stop hook found in .claude/settings.json or ~/.claude/settings.json",
    }


def _verify_copilot(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Check .vscode/tasks.json for the governance closeout task."""
    tasks_path = project_root / ".vscode" / "tasks.json"
    data = _read_json_safe(tasks_path)
    tasks = data.get("tasks", [])
    for task in tasks:
        if "session_closeout_entry" in task.get("command", "") or "Governance" in task.get("label", ""):
            return {
                "installed": True,
                "location": str(tasks_path),
                "note": f"VS Code task '{task.get('label')}' found in tasks.json",
            }
    return {
        "installed": False,
        "location": None,
        "note": "No governance closeout task found in .vscode/tasks.json",
    }


def _verify_gemini(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Check .gemini/settings.json for session end hook."""
    settings_path = project_root / ".gemini" / "settings.json"
    data = _read_json_safe(settings_path)
    hook_key = AGENT_MANIFEST["gemini"]["gemini_hook_key"]
    if hook_key in data and "session_closeout_entry" in data[hook_key]:
        return {
            "installed": True,
            "location": str(settings_path),
            "note": f"sessionEndHook found in .gemini/settings.json",
        }
    return {
        "installed": False,
        "location": None,
        "note": ".gemini/settings.json not configured or sessionEndHook missing",
    }


def _verify_chatgpt(_project_root: Path, _framework_root: Path) -> dict[str, Any]:
    """ChatGPT has no automatable integration."""
    return {
        "installed": False,
        "location": None,
        "note": "Manual only — no automatable integration surface exists for ChatGPT",
        "manual_only": True,
    }


_VERIFIERS = {
    "claude": _verify_claude,
    "copilot": _verify_copilot,
    "gemini": _verify_gemini,
    "chatgpt": _verify_chatgpt,
}


# ── Per-agent install ─────────────────────────────────────────────────────────

def _install_claude(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Install governance stop hook into .claude/settings.json."""
    settings_path = project_root / ".claude" / "settings.json"
    entry_cmd = _format_command(AGENT_MANIFEST["claude"]["hook_command"], framework_root)
    status_msg = AGENT_MANIFEST["claude"]["hook_status_message"]

    data = _read_json_safe(settings_path)
    data.setdefault("hooks", {}).setdefault("Stop", [])
    if not data["hooks"]["Stop"]:
        data["hooks"]["Stop"] = [{"hooks": []}]
    if "hooks" not in data["hooks"]["Stop"][0]:
        data["hooks"]["Stop"][0]["hooks"] = []

    # Check if already present
    existing_cmds = [h.get("command", "") for h in data["hooks"]["Stop"][0]["hooks"]]
    if any("session_closeout_entry" in cmd for cmd in existing_cmds):
        return {
            "status": "already_installed",
            "location": str(settings_path),
            "message": "Governance stop hook already present in .claude/settings.json",
        }

    data["hooks"]["Stop"][0]["hooks"].append({
        "type": "command",
        "command": entry_cmd,
        "statusMessage": status_msg,
    })
    _write_json(settings_path, data)
    return {
        "status": "installed",
        "location": str(settings_path),
        "message": f"Governance stop hook added to {settings_path}",
    }


def _install_copilot(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Install governance task into .vscode/tasks.json."""
    tasks_path = project_root / ".vscode" / "tasks.json"
    task_template = AGENT_MANIFEST["copilot"]["vscode_task"]

    # Format command
    task = dict(task_template)
    task["command"] = _format_command(task["command"], framework_root)

    data = _read_json_safe(tasks_path)
    if not data:
        data = {"version": "2.0.0", "tasks": []}
    data.setdefault("tasks", [])

    # Check if already present
    for existing in data["tasks"]:
        if "session_closeout_entry" in existing.get("command", "") or existing.get("label") == task["label"]:
            return {
                "status": "already_installed",
                "location": str(tasks_path),
                "message": f"VS Code task '{task['label']}' already present in tasks.json",
            }

    data["tasks"].append(task)
    _write_json(tasks_path, data)
    return {
        "status": "installed",
        "location": str(tasks_path),
        "message": (
            f"VS Code task '{task['label']}' added to {tasks_path}. "
            "Run this task manually before ending each Copilot session."
        ),
    }


def _install_gemini(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Install session end hook into .gemini/settings.json."""
    settings_path = project_root / ".gemini" / "settings.json"
    entry_cmd = _format_command(AGENT_MANIFEST["gemini"]["manual_command"], framework_root)
    hook_key = AGENT_MANIFEST["gemini"]["gemini_hook_key"]

    data = _read_json_safe(settings_path)

    if hook_key in data and "session_closeout_entry" in data.get(hook_key, ""):
        return {
            "status": "already_installed",
            "location": str(settings_path),
            "message": f"sessionEndHook already configured in .gemini/settings.json",
        }

    data[hook_key] = entry_cmd
    _write_json(settings_path, data)
    return {
        "status": "installed",
        "location": str(settings_path),
        "message": (
            f"sessionEndHook written to {settings_path}. "
            "Gemini CLI will execute this on session end if it supports the hook key. "
            "Verify with: manage_agent_closeout verify --agent gemini"
        ),
    }


def _install_chatgpt(_project_root: Path, framework_root: Path) -> dict[str, Any]:
    """ChatGPT has no automatable integration — return manual instructions."""
    manual_cmd = _format_command(AGENT_MANIFEST["chatgpt"]["manual_command"], framework_root)
    return {
        "status": "manual_only",
        "location": None,
        "message": (
            "ChatGPT (web/API) has no local session lifecycle hook. "
            "No automated integration can be installed.\n\n"
            "Manual closeout command — run this before ending each ChatGPT session:\n\n"
            f"    {manual_cmd}"
        ),
    }


_INSTALLERS = {
    "claude": _install_claude,
    "copilot": _install_copilot,
    "gemini": _install_gemini,
    "chatgpt": _install_chatgpt,
}


# ── Operations ────────────────────────────────────────────────────────────────

def status(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Return integration status for all known agents."""
    results = {}
    for agent_name, manifest in AGENT_MANIFEST.items():
        verifier = _VERIFIERS[agent_name]
        verification = verifier(project_root, framework_root)
        tier = manifest["capability_tier"]
        results[agent_name] = {
            "display_name": manifest["display_name"],
            "tier": tier,
            "tier_label": TIER_LABELS.get(tier, "Unknown"),
            "capability": manifest["capability_label"],
            "installed": verification["installed"],
            "location": verification.get("location"),
            "note": verification.get("note"),
            "manual_only": verification.get("manual_only", False),
        }
    return results


def verify(agent: str, project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Verify integration for a single agent."""
    if agent not in AGENT_MANIFEST:
        return {"ok": False, "error": f"Unknown agent: {agent}. Known: {KNOWN_AGENTS}"}
    manifest = AGENT_MANIFEST[agent]
    verification = _VERIFIERS[agent](project_root, framework_root)
    tier = manifest["capability_tier"]
    return {
        "agent": agent,
        "display_name": manifest["display_name"],
        "tier": tier,
        "tier_label": TIER_LABELS.get(tier),
        "capability": manifest["capability_label"],
        **verification,
    }


def install(agent: str, project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Install integration for a single agent."""
    if agent not in AGENT_MANIFEST:
        return {"ok": False, "error": f"Unknown agent: {agent}. Known: {KNOWN_AGENTS}"}
    result = _INSTALLERS[agent](project_root, framework_root)
    return {"agent": agent, **result}


def repair(agent: str, project_root: Path, framework_root: Path) -> dict[str, Any]:
    """
    Repair integration for a single agent.

    Repair = verify first; if not installed, install; if installed but broken,
    remove and reinstall. Currently: verify then install if missing.
    """
    verification = _VERIFIERS[agent](project_root, framework_root)
    if verification["installed"]:
        return {
            "agent": agent,
            "status": "no_repair_needed",
            "message": f"Integration for '{agent}' is already correctly installed.",
            "location": verification.get("location"),
        }
    result = _INSTALLERS[agent](project_root, framework_root)
    return {"agent": agent, "repaired": True, **result}


# ── Output formatting ─────────────────────────────────────────────────────────

def _format_status_human(results: dict[str, Any]) -> str:
    lines = ["[manage_agent_closeout] status\n"]
    for agent_name, info in results.items():
        tier = info["tier"]
        installed_marker = "✓" if info["installed"] else ("—" if info["manual_only"] else "✗")
        lines.append(
            f"  {installed_marker} {info['display_name']:<20} "
            f"Tier {tier} ({info['tier_label']:<28}) "
            f"{info['note']}"
        )
    lines.append("")
    lines.append("Legend: ✓ installed   ✗ not installed   — manual only (no automation possible)")
    return "\n".join(lines)


def _format_operation_human(result: dict[str, Any], operation: str) -> str:
    agent = result.get("agent", "?")
    # verify uses 'installed', install/repair uses 'status'
    if "installed" in result:
        status_val = "installed" if result["installed"] else (
            "manual_only" if result.get("manual_only") else "not_installed"
        )
    else:
        status_val = result.get("status", "?")
    message = result.get("message", result.get("note", ""))
    location = result.get("location")
    lines = [
        f"[manage_agent_closeout] {operation} --agent {agent}",
        f"status={status_val}",
    ]
    if location:
        lines.append(f"location={location}")
    if message:
        lines.append(f"message={message}")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Manage session closeout integrations for AI agents. "
            "The core closeout pipeline (session_closeout_entry.py) is agent-agnostic. "
            "This tool manages how each agent triggers that pipeline."
        )
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Path to the project root (default: current directory)",
    )
    parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
    )

    subparsers = parser.add_subparsers(dest="operation", required=True)

    # status
    subparsers.add_parser("status", help="Show integration status for all agents")

    # install
    install_p = subparsers.add_parser("install", help="Install integration for an agent")
    install_p.add_argument(
        "--agent",
        choices=KNOWN_AGENTS + ["all"],
        required=True,
        help=f"Agent to install: {KNOWN_AGENTS + ['all']}",
    )

    # verify
    verify_p = subparsers.add_parser("verify", help="Verify integration for an agent")
    verify_p.add_argument(
        "--agent",
        choices=KNOWN_AGENTS,
        required=True,
    )

    # repair
    repair_p = subparsers.add_parser("repair", help="Repair integration for an agent")
    repair_p.add_argument(
        "--agent",
        choices=KNOWN_AGENTS,
        required=True,
    )

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    framework_root = _resolve_framework_root()

    if args.operation == "status":
        result = status(project_root, framework_root)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(_format_status_human(result))
        return 0

    if args.operation == "install":
        agents = KNOWN_AGENTS if args.agent == "all" else [args.agent]
        results = [install(a, project_root, framework_root) for a in agents]
        if args.format == "json":
            print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(_format_operation_human(r, "install"))
        return 0

    if args.operation == "verify":
        result = verify(args.agent, project_root, framework_root)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(_format_operation_human(result, "verify"))
        return 0 if result.get("installed") or result.get("manual_only") else 1

    if args.operation == "repair":
        result = repair(args.agent, project_root, framework_root)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(_format_operation_human(result, "repair"))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
