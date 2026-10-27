#!/usr/bin/env python3
"""
manage_agent_closeout.py — Agent integration manager for session closeout.

Manages installation, verification, repair, uninstallation, and capability
reporting of session closeout integrations across AI agents.

The core closeout pipeline (session_closeout_entry.py) is agent-agnostic.
This tool manages how each agent *triggers* that pipeline. Each agent is
implemented as an adapter with a defined contract:

    detect()        — detect if the agent is present/configured in this repo
    capability()    — report tier, label, surface description
    install()       — install the closeout trigger
    verify()        — verify the trigger is correctly installed
    repair()        — install if missing, re-install if broken
    uninstall()     — remove the installed trigger
    print_manual()  — print manual steps for agents without automation

Capability tiers are assigned based on *integration surface*, not product brand:

    Tier A  Native lifecycle hooks
            Agent has a formal session/lifecycle hook surface.
            Closeout fires automatically.
            Current: Claude Code, Copilot CLI/cloud agent, Gemini CLI, Codex

    Tier B  Wrapper-based integration
            No stable native session-end hook, but can be connected via
            launcher, task wrapper, or equivalent mechanism.
            Current: no adapter is currently assigned to this tier

    Tier C  Manual only
            No reliable automation surface. User must run closeout manually.
            Current: ChatGPT web

    Tier D  Unknown / unverified
            Insufficient documentation to classify. Stub provided.

Usage:
    python -m governance_tools.manage_agent_closeout status
    python -m governance_tools.manage_agent_closeout capabilities
    python -m governance_tools.manage_agent_closeout install --agent claude
    python -m governance_tools.manage_agent_closeout install --agent all
    python -m governance_tools.manage_agent_closeout verify --agent copilot
    python -m governance_tools.manage_agent_closeout repair --agent gemini
    python -m governance_tools.manage_agent_closeout uninstall --agent claude
    python -m governance_tools.manage_agent_closeout print-manual --agent chatgpt-web
"""

from __future__ import annotations

import abc
import argparse
import base64
import binascii
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Capability tier constants ─────────────────────────────────────────────────

TIER_A = "A"
TIER_B = "B"
TIER_C = "C"
TIER_D = "D"

TIER_LABELS = {
    TIER_A: "Native lifecycle hooks (fully automated)",
    TIER_B: "Wrapper-based integration (semi-automated)",
    TIER_C: "Manual only (no automation surface)",
    TIER_D: "Unknown / unverified",
}


# ── Adapter base contract ─────────────────────────────────────────────────────

class AgentAdapter(abc.ABC):
    """
    Abstract base for all agent closeout adapters.

    Each adapter knows:
    - Which config files to read/write
    - How to detect whether the agent is present
    - How to install, verify, repair, and uninstall the closeout trigger
    - What tier this agent belongs to (and why)
    - What manual steps to print for partially/non-automated agents
    """

    @property
    @abc.abstractmethod
    def agent_id(self) -> str:
        """Unique identifier, e.g. 'claude', 'copilot', 'gemini'."""

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. 'Claude Code'."""

    @property
    @abc.abstractmethod
    def tier(self) -> str:
        """Capability tier: A, B, C, or D."""

    @property
    @abc.abstractmethod
    def surface_description(self) -> str:
        """One sentence describing the integration surface and why it has this tier."""

    def capability(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "tier": self.tier,
            "tier_label": TIER_LABELS.get(self.tier, "Unknown"),
            "surface_description": self.surface_description,
            "auto_trigger_capable": self.tier == TIER_A,
            "fallback_required": self.tier in {TIER_B, TIER_C},
        }

    @abc.abstractmethod
    def detect(self, project_root: Path) -> dict[str, Any]:
        """
        Detect whether this agent appears to be active in the project.
        Returns: {"detected": bool, "evidence": str}
        """

    @abc.abstractmethod
    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        """
        Install the closeout trigger.
        Returns: {"status": str, "location": str|None, "message": str}
        Status values: installed | already_installed | manual_only | blocked | error
        """

    @abc.abstractmethod
    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        """
        Verify the trigger is correctly installed.
        Returns: {"installed": bool, "location": str|None, "note": str,
                  "manual_only": bool}
        """

    def repair(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        """
        Repair the integration. Default: verify then install if missing.
        Adapters may override for agent-specific repair logic.
        """
        v = self.verify(project_root, framework_root)
        if v["installed"] or v.get("manual_only"):
            return {
                "agent": self.agent_id,
                "status": "no_repair_needed",
                "message": "Integration is already correctly configured.",
                "location": v.get("location"),
            }
        result = self.install(project_root, framework_root)
        return {
            "agent": self.agent_id,
            **result,
            "repaired": result.get("status") == "installed",
        }

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        """
        Remove the installed trigger.
        Default implementation: no-op with explanation.
        Override in adapters that write config files.
        """
        return {
            "agent": self.agent_id,
            "status": "not_implemented",
            "message": f"Uninstall not implemented for {self.display_name}.",
        }

    @abc.abstractmethod
    def print_manual(self, framework_root: Path) -> str:
        """
        Return human-readable manual closeout instructions for this agent.
        Always implemented — even Tier A agents benefit from a manual fallback doc.
        """


# ── Shared helpers ────────────────────────────────────────────────────────────

def _resolve_framework_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fmt_cmd(template: str, framework_root: Path, project_root: Path | str) -> str:
    """Render a closeout command with an explicit, canonical project root.

    `project_root` is never defaulted to the current directory: the canonical
    artifact root is an explicit contract (owner-ratified 2026-06-23). Callers
    that know the root pass the resolved absolute path; the human-facing manual
    command passes a placeholder the operator must replace.
    """
    rendered = template.replace(
        "{framework_root}", str(framework_root).replace("\\", "/")
    )
    if isinstance(project_root, Path):
        project_root = str(project_root.resolve())
    return rendered.replace("{project_root}", str(project_root).replace("\\", "/"))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_MANUAL_ROOT_PLACEHOLDER = "<PROJECT_ROOT>"

_CLOSEOUT_CMD = (
    "python {framework_root}/governance_tools/session_closeout_entry.py "
    "--project-root {project_root} 2>/dev/null || true"
)
_CLOSEOUT_CMD_BARE = (
    "python {framework_root}/governance_tools/session_closeout_entry.py "
    "--project-root {project_root}"
)


def _manual_closeout_cmd(framework_root: Path, agent_id: str, trigger_mode: str = "manual_fallback") -> str:
    base = _fmt_cmd(_CLOSEOUT_CMD_BARE, framework_root, _MANUAL_ROOT_PLACEHOLDER)
    if agent_id == "codex":
        base += " --session-id <SESSION_ID>"
    return f"{base} --agent-id {agent_id} --trigger-mode {trigger_mode}"


_PREPARE_ENTRY = "governance_tools/prepare_closeout_candidate.py"
_SUBMODULE_PATH = r"^submodule\..*\.path$"


def _registered_submodule_paths(consumer: Path) -> list[str] | None:
    """Submodule paths registered in the consumer's .gitmodules.

    Returns None when the registration cannot be read, which is reported as
    undetermined rather than as a failed precondition.
    """
    modules = consumer / ".gitmodules"
    if not modules.is_file():
        return []
    # Explicit -C and --file must select the repository and the registration
    # file; inherited Git selectors must not supply a different one.
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", "-C", str(consumer), "config", "--null", "--file", str(modules),
             "--get-regexp", _SUBMODULE_PATH],
            capture_output=True, encoding="utf-8", timeout=15, env=env, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 1:  # documented "no matching key", not a failure
        return []
    if result.returncode != 0:
        return None
    paths = []
    for record in result.stdout.rstrip("\0").split("\0"):
        if not record:
            continue
        _, _, relative = record.partition("\n")
        if relative:
            paths.append(relative)
    return paths


def closeout_execution_readiness(project_root: Path, framework_root: Path) -> dict[str, Any]:
    """Report whether the save-progress command an install declares could run.

    `install` writes a hook whose command is rejected outright when the
    framework is not a registered submodule of the project, or when the
    project root is missing its governance markers. Both are stable
    properties of the layout and are cheap to check here, so reporting
    `installed` without checking them overclaims (#257).

    Only those stable preconditions are checked. A dirty framework checkout
    or a moved gitlink is transient and stays with the pipeline's own
    fail-closed validation. `unmet` and `undetermined` are kept apart so a
    layout that could not be read is never reported as a failed precondition.
    """
    unmet: list[str] = []
    undetermined: list[str] = []
    try:
        consumer = project_root.resolve(strict=True)
        framework = framework_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return {"ready": False, "unmet": [], "undetermined": [f"PATHS_UNRESOLVABLE: {exc}"],
                "declared_entry": _PREPARE_ENTRY}

    # The pipeline's own root predicate, so this reports what it would report.
    # Imported here to keep the closeout pipeline off this CLI import path.
    from governance_tools.session_closeout_entry import (
        RootBindingError, _validate_explicit_project_root,
    )
    try:
        _validate_explicit_project_root(str(consumer))
    except RootBindingError as exc:
        unmet.append(f"ROOT_BINDING_WOULD_FAIL: {exc}")

    if framework == consumer or not framework.is_relative_to(consumer):
        unmet.append("FRAMEWORK_NOT_INSIDE_PROJECT: the declared command requires the "
                     "framework to be a registered submodule of the project root")
    else:
        registrations = _registered_submodule_paths(consumer)
        if registrations is None:
            undetermined.append("SUBMODULE_REGISTRATION_UNREADABLE: .gitmodules could not be read")
        else:
            matched = []
            for relative in registrations:
                try:
                    candidate = (consumer / relative).resolve()
                except (OSError, RuntimeError):
                    continue
                if candidate == framework:
                    matched.append(relative)
            if len(matched) != 1:
                unmet.append("FRAMEWORK_NOT_REGISTERED_SUBMODULE: the framework path has "
                             f"{len(matched)} submodule registrations in .gitmodules, not 1")
    return {"ready": not unmet and not undetermined, "unmet": unmet,
            "undetermined": undetermined, "declared_entry": _PREPARE_ENTRY}


def _readiness_note(readiness: dict[str, Any]) -> str:
    """One sentence naming what would reject the declared command, or nothing."""
    if readiness["ready"]:
        return ""
    reasons = list(readiness["unmet"]) + list(readiness["undetermined"])
    return (" The declared save-progress command cannot be shown to run in this layout: "
            + "; ".join(reasons) + ".")


# ── Claude Code adapter ───────────────────────────────────────────────────────

class ClaudeAdapter(AgentAdapter):
    """
    Claude Code (claude.ai/code, VS Code extension, CLI).

    Integration surface: .claude/settings.json or ~/.claude/settings.json
    Hook keys: hooks.SessionStart / hooks.SessionEnd [].hooks[].command

    Claude Code's Stop fires every time Claude finishes a response, not at
    session end, so governance no longer closes out on Stop (a legacy
    governance Stop hook is removed on install).  SessionStart establishes the
    root-bound identity and reads back the latest checkpoint; SessionEnd writes
    a resumable checkpoint within a 5 s budget.  Formal closeout is an explicit
    operation.  Design: docs/proposals/2026-10-claude-code-session-lifecycle.md.
    """

    LIFECYCLE_SCRIPT = "runtime_hooks/adapters/claude_code/session_lifecycle.py"
    SESSION_END_TIMEOUT = 5
    MANAGED_EVENTS = ("SessionStart", "SessionEnd", "Stop")

    @property
    def agent_id(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Claude Code"

    @property
    def tier(self) -> str:
        return TIER_A

    @property
    def surface_description(self) -> str:
        return (
            "Claude Code SessionStart (identity, read-back) and SessionEnd (resumable "
            "checkpoint) hooks in .claude/settings.json; formal closeout is explicit."
        )

    def detect(self, project_root: Path) -> dict[str, Any]:
        has_dir = (project_root / ".claude").is_dir()
        return {
            "detected": has_dir,
            "evidence": ".claude/ directory present" if has_dir else "no .claude/ directory",
        }

    @classmethod
    def _command(cls, project_root: Path, framework_root: Path, event: str) -> str:
        script = (framework_root.resolve() / cls.LIFECYCLE_SCRIPT).as_posix()
        return "python " + shlex.join(
            [script, "--event", event, "--project-root", project_root.resolve().as_posix()])

    @classmethod
    def _expected_hooks(cls, project_root: Path, framework_root: Path) -> dict[str, dict[str, Any]]:
        return {
            "SessionStart": {"type": "command",
                             "command": cls._command(project_root, framework_root, "session_start"),
                             "statusMessage": "Establishing governance session identity..."},
            "SessionEnd": {"type": "command",
                           "command": cls._command(project_root, framework_root, "session_end"),
                           "timeout": cls.SESSION_END_TIMEOUT},
        }

    @classmethod
    def _is_governance_hook(cls, hook: Any) -> bool:
        """Governance-owned hooks: the lifecycle entry, or the legacy Stop closeout."""
        if not isinstance(hook, dict) or hook.get("type", "command") != "command":
            return False
        try:
            tokens = shlex.split(hook.get("command", ""))
        except (ValueError, TypeError):
            return False
        if len(tokens) < 2 or tokens[0] not in ("python", "python3"):
            return False
        if len(tokens) == 3 and tokens[1] == "-c":
            return tokens[2].startswith("# governance:claude-closeout-v1\n")
        target = tokens[1].replace("\\", "/")
        return (target.endswith("/governance_tools/session_closeout_entry.py")
                or target.endswith("/" + cls.LIFECYCLE_SCRIPT))

    def _binding_state(self, project_root: Path, framework_root: Path) -> tuple[str, str | None]:
        expected = self._expected_hooks(project_root, framework_root)
        found: dict[str, list[tuple[bool, str]]] = {event: [] for event in self.MANAGED_EVENTS}
        for path in (project_root / ".claude/settings.json",
                     project_root / ".claude/settings.local.json",
                     Path.home() / ".claude/settings.json"):
            hooks = _read_json(path).get("hooks", {})
            if not isinstance(hooks, dict):
                continue
            for event in self.MANAGED_EVENTS:
                for group in hooks.get(event, []) if isinstance(hooks.get(event), list) else []:
                    if not isinstance(group, dict):
                        continue
                    for hook in group.get("hooks", []):
                        if not self._is_governance_hook(hook):
                            continue
                        want = expected.get(event)
                        current = (want is not None
                                   and hook.get("command") == want["command"]
                                   and hook.get("timeout") == want.get("timeout")
                                   and not hook.get("async", False)
                                   and not hook.get("if") and not group.get("matcher"))
                        found[event].append((current, str(path)))
        complete = (not found["Stop"] and all(
            len(found[event]) == 1 and found[event][0][0] for event in ("SessionStart", "SessionEnd")))
        if complete:
            return "CORRECTLY_INSTALLED", found["SessionStart"][0][1]
        for event in self.MANAGED_EVENTS:
            if found[event]:
                return "STALE_OR_WRONG_BINDING", found[event][0][1]
        return "NOT_INSTALLED", None

    def _find_installed(self, project_root: Path, framework_root: Path) -> tuple[bool, str | None]:
        state, location = self._binding_state(project_root, framework_root)
        return state == "CORRECTLY_INSTALLED", location

    @classmethod
    def _read_settings_for_install(cls, path: Path) -> dict[str, Any]:
        """Read the settings to be rewritten without treating errors as empty data."""
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("settings must contain a JSON object")
        hooks = data.get("hooks", {})
        if not isinstance(hooks, dict):
            raise ValueError("settings hooks must be an object")
        for event in cls.MANAGED_EVENTS:
            groups = hooks.get(event, [])
            if not isinstance(groups, list):
                raise ValueError(f"settings hooks.{event} must be a list")
            for group in groups:
                if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
                    raise ValueError(f"settings {event} groups must be objects with hook lists")
        return data

    @classmethod
    def _remove_governance_hooks(cls, hooks: dict[str, Any]) -> bool:
        """Drop governance hooks; groups and events emptied by that removal go too."""
        changed = False
        for event in cls.MANAGED_EVENTS:
            groups = hooks.get(event)
            if not isinstance(groups, list):
                continue
            kept_groups = []
            event_changed = False
            for group in groups:
                if not isinstance(group, dict) or "hooks" not in group:
                    kept_groups.append(group)
                    continue
                kept = [h for h in group["hooks"] if not cls._is_governance_hook(h)]
                if len(kept) != len(group["hooks"]):
                    event_changed = True
                    if not kept:
                        continue
                    group["hooks"] = kept
                kept_groups.append(group)
            if kept_groups:
                hooks[event] = kept_groups
            elif event_changed:
                del hooks[event]
            changed = changed or event_changed
        return changed

    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        settings_path = project_root / ".claude/settings.json"
        try:
            data = self._read_settings_for_install(settings_path)
        except (OSError, ValueError, RecursionError) as exc:
            return {"status": "blocked", "location": str(settings_path),
                    "message": f"Unable to safely read Claude settings; not modified: {exc}"}
        state, loc = self._binding_state(project_root, framework_root)
        readiness = closeout_execution_readiness(project_root, framework_root)
        if state == "CORRECTLY_INSTALLED":
            return {"status": "already_installed", "location": loc,
                    "closeout_readiness": readiness,
                    "message": "Governance SessionStart/SessionEnd hooks match the requested binding."
                               + _readiness_note(readiness)}
        for path in (project_root / ".claude/settings.local.json",
                     Path.home() / ".claude/settings.json"):
            hooks = _read_json(path).get("hooks", {})
            for event in self.MANAGED_EVENTS:
                groups = hooks.get(event, []) if isinstance(hooks, dict) else []
                for group in groups if isinstance(groups, list) else []:
                    if isinstance(group, dict) and any(self._is_governance_hook(h)
                                                      for h in group.get("hooks", [])):
                        return {"status": "blocked", "location": str(path),
                                "message": "Conflicting Governance hook outside scoped settings.json; not modified."}
        hooks = data.setdefault("hooks", {})
        removed = self._remove_governance_hooks(hooks)
        for event, hook in self._expected_hooks(project_root, framework_root).items():
            hooks.setdefault(event, []).append({"hooks": [hook]})
        _write_json(settings_path, data)
        return {"status": "installed", "previous_binding_state": state,
                "location": str(settings_path), "closeout_readiness": readiness,
                "message": ("Governance SessionStart/SessionEnd hooks installed"
                            + ("; previous governance hooks (incl. any Stop closeout) replaced." if removed else ".")
                            + _readiness_note(readiness))}

    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        state, loc = self._binding_state(project_root, framework_root)
        readiness = closeout_execution_readiness(project_root, framework_root)
        return {"installed": state == "CORRECTLY_INSTALLED", "manual_only": False,
                "binding_state": state, "location": loc, "closeout_readiness": readiness,
                "note": "Configuration binding only; native execution is not verified."
                        + _readiness_note(readiness)}

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        settings_path = project_root / ".claude" / "settings.json"
        data = _read_json(settings_path)
        hooks = data.get("hooks", {})
        if isinstance(hooks, dict) and self._remove_governance_hooks(hooks):
            _write_json(settings_path, data)
            return {
                "agent": self.agent_id,
                "status": "uninstalled",
                "location": str(settings_path),
                "message": "Governance Claude hooks removed from .claude/settings.json",
            }
        return {
            "agent": self.agent_id,
            "status": "not_found",
            "message": "No governance Claude hook found to remove.",
        }

    def print_manual(self, framework_root: Path) -> str:
        cmd = _manual_closeout_cmd(framework_root, self.agent_id, "manual_fallback")
        return (
            f"[{self.display_name}] Exiting only writes a resumable checkpoint; formal "
            f"closeout is a separate explicit operation.\n\n"
            f"Known gap: the manual command below uses --trigger-mode manual_fallback, which "
            f"session_closeout_entry currently rejects (R2 release proof), so there is no "
            f"working explicit closeout command yet:\n\n"
            f"    {cmd}\n\n"
            f"Install the SessionStart/SessionEnd hooks:\n\n"
            f"    python -m governance_tools.manage_agent_closeout install --agent claude"
        )


# ── Copilot adapter ───────────────────────────────────────────────────────────

class CopilotAdapter(AgentAdapter):
    """
    GitHub Copilot CLI / cloud agent.

    Integration surface: .github/hooks/session-end.json (or session_end.json)
    Hook key: hooks.sessionEnd[].bash / .powershell
    Reference: https://docs.github.com/en/copilot/reference/hooks-configuration

    Tier A: Copilot CLI and cloud agent have a native sessionEnd lifecycle hook
    stored in .github/hooks/. Confirmed in official GitHub documentation.

    Fallback: .vscode/tasks.json task (for VS Code-only usage without CLI hooks).
    The fallback is NOT the primary path — it is recorded as secondary only.
    """

    HOOKS_DIR = ".github/hooks"
    HOOK_FILE = "session-end.json"

    @property
    def agent_id(self) -> str:
        return "copilot"

    @property
    def display_name(self) -> str:
        return "GitHub Copilot"

    @property
    def tier(self) -> str:
        return TIER_A

    @property
    def surface_description(self) -> str:
        return (
            "Copilot CLI / cloud agent: native sessionEnd lifecycle hook "
            "in .github/hooks/session-end.json. "
            "VS Code task in .vscode/tasks.json is a secondary fallback only."
        )

    def detect(self, project_root: Path) -> dict[str, Any]:
        has_github = (project_root / ".github").is_dir()
        return {
            "detected": has_github,
            "evidence": ".github/ directory present" if has_github else "no .github/ directory",
        }

    def _hook_path(self, project_root: Path) -> Path:
        return project_root / self.HOOKS_DIR / self.HOOK_FILE

    @staticmethod
    def _is_governance_hook(hook: Any) -> bool:
        if not isinstance(hook, dict):
            return False

        def recognized(tokens: list[str]) -> bool:
            if len(tokens) < 2 or not all(isinstance(t, str) for t in tokens):
                return False
            # Deliberately narrow: python/python3 (optionally a path), then
            # optional -B, then the entrypoint. No wrapper or shell grammar.
            interpreter = tokens[0].replace("\\", "/").rsplit("/", 1)[-1]
            if interpreter not in ("python", "python3"):
                return False
            index = 2 if tokens[1] == "-B" else 1
            return len(tokens) > index and tokens[index].replace("\\", "/").endswith(
                "/governance_tools/session_closeout_entry.py")

        args = hook.get("args", [])
        if isinstance(hook.get("exec"), str) and isinstance(args, list):
            if recognized([hook["exec"], *args]):
                return True
        for field in ("bash", "powershell", "command"):
            command = hook.get(field)
            if not isinstance(command, str):
                continue
            try:
                tokens = shlex.split(command)
            except ValueError:
                continue
            if recognized(tokens):
                return True
        return False

    @staticmethod
    def _hook_payload(project_root: Path, framework_root: Path) -> dict[str, Any]:
        entry = (framework_root.resolve() / "governance_tools" /
                 "session_closeout_entry.py").as_posix()
        root = project_root.resolve().as_posix()
        # Quote each shell independently. Preserve the existing failure policy.
        bash = (f"python {shlex.quote(entry)} --project-root {shlex.quote(root)} "
                "2>/dev/null || true")
        quote_ps = lambda value: "'" + value.replace("'", "''") + "'"
        powershell = (f"python {quote_ps(entry)} --project-root {quote_ps(root)} "
                      "2>$null || true")
        return {"type": "command", "bash": bash, "powershell": powershell,
                "timeoutSec": 30}

    def _configuration_blockers(self, project_root: Path) -> list[str]:
        """Read only the managed file and repository hook-directory conflicts.

        This is not a check of user, policy, plugin or inline settings sources.
        """
        managed = self._hook_path(project_root)
        blockers = []
        for path in sorted(managed.parent.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeError):
                if path == managed:
                    blockers.append(f"Unreadable configuration: {path}")
                continue
            if not isinstance(data, dict):
                if path == managed:
                    blockers.append(f"Invalid configuration object: {path}")
                continue
            if data.get("disableAllHooks") is True:
                if path == managed:
                    blockers.append(f"Hooks explicitly disabled: {path}")
                continue
            events = data.get("hooks", {})
            if (not isinstance(events, dict)
                    or any(not isinstance(value, list) for value in events.values())):
                if path == managed:
                    blockers.append(f"Invalid event-list structure: {path}")
                continue
            # Structurally invalid sibling files are rejected independently by
            # the platform. Never repair or delete those files here.
            if path == managed or type(data.get("version")) is not int or data["version"] != 1:
                continue
            if any(self._is_governance_hook(h) for h in events.get("sessionEnd", [])):
                blockers.append(f"Additional governance sessionEnd hook: {path}")
        return blockers

    def _binding_state(self, project_root: Path, framework_root: Path) -> str:
        if self._configuration_blockers(project_root):
            return "STALE_OR_WRONG_BINDING"
        path = self._hook_path(project_root)
        if not path.exists():
            return "NOT_INSTALLED"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
                return "STALE_OR_WRONG_BINDING"
            hooks = data["hooks"].get("sessionEnd", [])
            if (type(data.get("version")) is not int or data["version"] != 1
                    or not isinstance(hooks, list)):
                return "STALE_OR_WRONG_BINDING"
        except (OSError, ValueError, UnicodeError):
            return "STALE_OR_WRONG_BINDING"
        found = [h for h in hooks if self._is_governance_hook(h)]
        if not found:
            return "NOT_INSTALLED"
        expected = self._hook_payload(project_root, framework_root)
        if len(found) == 1 and found[0] == expected:
            return "CORRECTLY_INSTALLED"
        return "STALE_OR_WRONG_BINDING"

    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        blockers = self._configuration_blockers(project_root)
        if blockers:
            return {"status": "error", "location": str(hook_path),
                    "message": "; ".join(blockers)}
        if self._binding_state(project_root, framework_root) == "CORRECTLY_INSTALLED":
            return {"status": "already_installed", "location": str(hook_path),
                    "message": "Copilot sessionEnd hook already present."}
        # Do not discard unreadable or structurally ambiguous user configuration.
        try:
            data = json.loads(hook_path.read_text(encoding="utf-8")) if hook_path.exists() else {}
            if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
                raise ValueError("expected a hook configuration object")
            hooks = data.get("hooks", {}).get("sessionEnd", [])
            if not isinstance(hooks, list):
                raise ValueError("sessionEnd must be a list")
        except (OSError, ValueError, UnicodeError) as exc:
            return {"status": "error", "location": str(hook_path),
                    "message": f"Cannot safely repair Copilot hook configuration: {exc}"}
        data["version"] = 1
        data.setdefault("hooks", {})["sessionEnd"] = [
            h for h in hooks if not self._is_governance_hook(h)
        ] + [self._hook_payload(project_root, framework_root)]
        _write_json(hook_path, data)
        return {"status": "installed", "location": str(hook_path),
                "message": f"Copilot sessionEnd hook written to {hook_path}."}

    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        state = self._binding_state(project_root, framework_root)
        return {"installed": state == "CORRECTLY_INSTALLED", "manual_only": False,
                "binding_state": state,
                "location": str(self._hook_path(project_root)) if state != "NOT_INSTALLED" else None,
                "note": (f"Managed binding and recognized repository sessionEnd invocation check: {state}; "
                         "runtime and other configuration sources not verified. "
                         + "; ".join(self._configuration_blockers(project_root)))}

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        data = _read_json(hook_path)
        hooks = data.get("hooks", {}).get("sessionEnd", [])
        before = len(hooks)
        data["hooks"]["sessionEnd"] = [
            h for h in hooks
            if "session_closeout_entry" not in h.get("bash", "")
        ]
        if len(data["hooks"]["sessionEnd"]) < before:
            _write_json(hook_path, data)
            return {
                "agent": self.agent_id,
                "status": "uninstalled",
                "location": str(hook_path),
                "message": "Governance sessionEnd hook removed.",
            }
        return {"agent": self.agent_id, "status": "not_found", "message": "No governance hook found to remove."}

    def print_manual(self, framework_root: Path) -> str:
        cmd = _manual_closeout_cmd(framework_root, self.agent_id, "manual_fallback")
        return (
            f"[{self.display_name}] Manual closeout (if native hook is not active):\n\n"
            f"    {cmd}\n\n"
            f"Primary integration: sessionEnd hook in {self.HOOKS_DIR}/{self.HOOK_FILE}\n"
            f"Install with: python -m governance_tools.manage_agent_closeout install --agent copilot"
        )


# ── Gemini CLI adapter ────────────────────────────────────────────────────────

class GeminiAdapter(AgentAdapter):
    """
    Gemini CLI (and VS Code Gemini Code Assist in agent mode, which is CLI-driven).

    Integration surface: .gemini/settings.json (project) or ~/.gemini/settings.json (user)
    Hook key: hooks.SessionEnd (list of hook objects)
    Reference: https://geminicli.com/docs/hooks/reference/
               Google Cloud — Gemini CLI hooks documentation

    Hook object schema (confirmed):
        {"command": "...", "timeout": 30}
    Hook input: JSON via stdin with fields session_id, transcript_path, cwd,
                hook_event_name, timestamp.
    Exit codes: 0=success, 2=block, others=warning.

    Tier A: Gemini CLI has native SessionEnd lifecycle hook support, confirmed
    in official documentation. VS Code Gemini Code Assist agent mode is
    driven by Gemini CLI.
    """

    CONFIG_PATH = ".gemini/settings.json"
    HOOK_EVENT = "SessionEnd"

    @property
    def agent_id(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Gemini CLI"

    @property
    def tier(self) -> str:
        return TIER_A

    @property
    def surface_description(self) -> str:
        return (
            "Gemini CLI native SessionEnd hook in .gemini/settings.json. "
            "Also covers VS Code Gemini Code Assist agent mode (CLI-driven). "
            "Hook receives session_id, transcript_path, cwd via stdin JSON."
        )

    def detect(self, project_root: Path) -> dict[str, Any]:
        has_dir = (project_root / ".gemini").is_dir()
        return {
            "detected": has_dir,
            "evidence": ".gemini/ directory present" if has_dir else "no .gemini/ directory",
        }

    def _settings_path(self, project_root: Path) -> Path:
        return project_root / self.CONFIG_PATH

    def _is_hook_installed(self, project_root: Path) -> bool:
        data = _read_json(self._settings_path(project_root))
        hooks = data.get("hooks", {}).get(self.HOOK_EVENT, [])
        return any("session_closeout_entry" in h.get("command", "") for h in hooks)

    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        if self._is_hook_installed(project_root):
            return {
                "status": "already_installed",
                "location": str(self._settings_path(project_root)),
                "message": f"Gemini {self.HOOK_EVENT} hook already present.",
            }
        settings_path = self._settings_path(project_root)
        data = _read_json(settings_path)
        data.setdefault("hooks", {}).setdefault(self.HOOK_EVENT, [])
        data["hooks"][self.HOOK_EVENT].append({
            "command": _fmt_cmd(_CLOSEOUT_CMD, framework_root, project_root),
            "timeout": 30,
        })
        _write_json(settings_path, data)
        return {
            "status": "installed",
            "location": str(settings_path),
            "message": (
                f"Gemini {self.HOOK_EVENT} hook written to {settings_path}. "
                "Fires automatically when Gemini CLI session ends."
            ),
        }

    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        installed = self._is_hook_installed(project_root)
        p = self._settings_path(project_root)
        return {
            "installed": installed,
            "manual_only": False,
            "location": str(p) if installed else None,
            "note": (
                f"{self.HOOK_EVENT} hook found in {self.CONFIG_PATH}" if installed
                else f"No governance hook found in {self.CONFIG_PATH}"
            ),
        }

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        settings_path = self._settings_path(project_root)
        data = _read_json(settings_path)
        hooks = data.get("hooks", {}).get(self.HOOK_EVENT, [])
        before = len(hooks)
        data["hooks"][self.HOOK_EVENT] = [
            h for h in hooks
            if "session_closeout_entry" not in h.get("command", "")
        ]
        if len(data["hooks"][self.HOOK_EVENT]) < before:
            _write_json(settings_path, data)
            return {
                "agent": self.agent_id,
                "status": "uninstalled",
                "location": str(settings_path),
                "message": f"Governance {self.HOOK_EVENT} hook removed.",
            }
        return {"agent": self.agent_id, "status": "not_found", "message": "No governance hook found to remove."}

    def print_manual(self, framework_root: Path) -> str:
        cmd = _manual_closeout_cmd(framework_root, self.agent_id, "manual_fallback")
        return (
            f"[{self.display_name}] Manual closeout (if native hook is not active):\n\n"
            f"    {cmd}\n\n"
            f"Primary integration: {self.HOOK_EVENT} hook in {self.CONFIG_PATH}\n"
            f"Install with: python -m governance_tools.manage_agent_closeout install --agent gemini"
        )


# ── ChatGPT web adapter ───────────────────────────────────────────────────────

class ChatGPTWebAdapter(AgentAdapter):
    """
    ChatGPT web product (chat.openai.com).

    No local session lifecycle hook surface exists.
    ChatGPT web does not interact with local repo files or have a hook
    mechanism that can trigger local commands.

    Tier C: Manual only. Closeout must be run explicitly by the user.
    """

    @property
    def agent_id(self) -> str:
        return "chatgpt-web"

    @property
    def display_name(self) -> str:
        return "ChatGPT (web)"

    @property
    def tier(self) -> str:
        return TIER_C

    @property
    def surface_description(self) -> str:
        return (
            "ChatGPT web has no local session lifecycle hook. "
            "No automated integration is possible. Manual closeout only."
        )

    def detect(self, project_root: Path) -> dict[str, Any]:
        return {"detected": False, "evidence": "ChatGPT web leaves no detectable local artifacts"}

    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        return {
            "status": "manual_only",
            "location": None,
            "message": (
                "ChatGPT web has no local hook surface. No installation possible.\n"
                f"Run manually: {_fmt_cmd(_CLOSEOUT_CMD_BARE, framework_root, project_root)}"
            ),
        }

    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        return {
            "installed": False,
            "manual_only": True,
            "location": None,
            "note": "Manual only — no automatable integration surface exists for ChatGPT web",
        }

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        return {
            "agent": self.agent_id,
            "status": "not_applicable",
            "message": "ChatGPT web has no installed integration to remove.",
        }

    def print_manual(self, framework_root: Path) -> str:
        cmd = _manual_closeout_cmd(framework_root, self.agent_id, "manual_fallback")
        return (
            f"[{self.display_name}] Manual closeout — run this before ending each ChatGPT session:\n\n"
            f"    {cmd}\n\n"
            f"ChatGPT web has no local hook surface. Automation is not possible.\n"
            f"Recommended: add this command to your session-end checklist or shell alias."
        )


# ── Codex CLI adapter ─────────────────────────────────────────────────────────

class CodexCLIAdapter(AgentAdapter):
    """
    OpenAI Codex CLI and desktop app.

    Integration surface: project-local .codex/hooks.json, hooks.Stop[].hooks[].
    A Stop hook runs when Codex completes a turn.  The closeout entrypoint uses
    JSON output because Codex requires JSON on stdout for successful Stop hooks.

    Tier A: Codex has a documented project-local lifecycle hook surface.
    """

    @property
    def agent_id(self) -> str:
        return "codex"

    @property
    def display_name(self) -> str:
        return "OpenAI Codex CLI"

    @property
    def tier(self) -> str:
        return TIER_A

    @property
    def surface_description(self) -> str:
        return (
            "Codex Stop hook in .codex/hooks.json. "
            "Fires automatically when Codex completes a turn."
        )

    def detect(self, project_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        return {
            "detected": hook_path.exists(),
            "evidence": (
                ".codex/hooks.json present" if hook_path.exists()
                else "no .codex/hooks.json"
            ),
        }

    @staticmethod
    def _hook_path(project_root: Path) -> Path:
        return project_root / ".codex" / "hooks.json"

    @staticmethod
    def _is_governance_hook(hook: Any) -> bool:
        if not isinstance(hook, dict) or hook.get("type", "command") != "command":
            return False
        python_names = {"python", "python3", "python.exe", "python3.exe"}
        for field in ("command", "commandWindows"):
            command = hook.get(field, "")
            if not isinstance(command, str):
                continue
            try:
                tokens = shlex.split(command)
                windows_script = len(tokens) == 4 and tokens[:2] == ["powershell", "-NoProfile"]
                if windows_script and tokens[2] == "-EncodedCommand":
                    tokens = shlex.split(base64.b64decode(tokens[3], validate=True).decode("utf-16-le"))
                elif windows_script and tokens[2] == "-Command":
                    tokens = shlex.split(tokens[3])
                else:
                    windows_script = False
            except (ValueError, TypeError, UnicodeError, binascii.Error):
                continue

            # Recognize the direct legacy entry and marked Claude wrapper,
            # plus our generated shell invocations. A textual mention alone
            # does not give the installer ownership of a custom hook.
            if len(tokens) >= 2 and tokens[0].replace("\\", "/").rsplit("/", 1)[-1] in python_names:
                entry = tokens[1].replace("\\", "/")
                # Keep the exact historical bare command, but a same-named
                # custom executable elsewhere is not owned by Governance.
                if (entry.split("/")[-2:] == ["governance_tools", "session_closeout_entry.py"]
                        or (len(tokens) == 2 and entry == "session_closeout_entry.py")):
                    return True
                if len(tokens) == 3 and tokens[1] == "-c" and tokens[2].startswith("# governance:claude-closeout-v1\n"):
                    return True
            native_posix = command.startswith('repo_root="$(git rev-parse --show-toplevel)" && ')
            for index in range(2, len(tokens)):
                if tokens[index].replace("\\", "/").split("/")[-2:] != ["governance_tools", "session_closeout_entry.py"]:
                    continue
                if windows_script and tokens[index - 2:index] == ["&", "$python"]:
                    return True
                if (native_posix and tokens[index - 2] in ("then", "else")
                        and tokens[index - 1].replace("\\", "/").rsplit("/", 1)[-1] in python_names):
                    return True
        return False

    @classmethod
    def _is_current_hook(cls, hook: Any, framework_root: Path) -> bool:
        if not cls._is_governance_hook(hook):
            return False
        expected = cls._hook_payload(framework_root)
        return (
            hook.get("type") == expected["type"]
            and all(hook.get(field) == expected[field]
                    for field in ("command", "commandWindows"))
        )

    @staticmethod
    def _hook_payload(framework_root: Path) -> dict[str, Any]:
        entrypoint = framework_root / "governance_tools" / "session_closeout_entry.py"
        args = (
            f'"{entrypoint.as_posix()}" --format json '
            "--agent-id codex --trigger-mode native_hook"
        )
        posix_command = (
            'repo_root="$(git rev-parse --show-toplevel)" && '
            f'if [ -x "$repo_root/.venv/bin/python" ]; then "$repo_root/.venv/bin/python" {args} '
            f'--project-root "$repo_root"; else python3 {args} --project-root "$repo_root"; fi'
        )
        windows_entrypoint = entrypoint.as_posix().replace("'", "''")
        windows_script = (
            '$repo = git rev-parse --show-toplevel; '
            "$candidates = @((Join-Path $repo '.venv-ci\\Scripts\\python.exe'), "
            "(Join-Path $repo '.venv\\Scripts\\python.exe')); "
            '$python = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1; '
            "if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }; "
            "if (-not $python) { Write-Error 'No Python interpreter found for Codex closeout'; exit 1 }; "
            f"& $python '{windows_entrypoint}' --project-root $repo --format json "
            '--agent-id codex --trigger-mode native_hook; exit $LASTEXITCODE'
        )
        # Transport the literal script through the outer native-hook shell.
        # Quoted -Command lets outer PowerShell expand our variables too early.
        windows_command = "powershell -NoProfile -EncodedCommand " + base64.b64encode(
            windows_script.encode("utf-16-le")
        ).decode("ascii")
        return {
            "type": "command",
            "command": posix_command,
            "commandWindows": windows_command,
            "timeout": 30,
            "statusMessage": "Running governance session closeout...",
        }

    def _find_current_hook(self, project_root: Path, framework_root: Path) -> bool:
        data = _read_json(self._hook_path(project_root))
        governance_hooks = []
        for group in data.get("hooks", {}).get("Stop", []):
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []):
                if self._is_governance_hook(hook):
                    governance_hooks.append(hook)
        return (len(governance_hooks) == 1
                and self._is_current_hook(governance_hooks[0], framework_root))

    def install(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        if self._find_current_hook(project_root, framework_root):
            return {
                "status": "already_installed",
                "location": str(hook_path),
                "message": "Governance Codex Stop hook already matches the requested framework binding.",
            }

        data = _read_json(hook_path)
        hooks = data.setdefault("hooks", {})
        stop_groups = hooks.setdefault("Stop", [{"hooks": []}])
        if not stop_groups:
            stop_groups.append({"hooks": []})
        if not isinstance(stop_groups[0], dict):
            stop_groups.insert(0, {"hooks": []})
        target_group = stop_groups[0]
        target_hooks = target_group.setdefault("hooks", [])

        # Replace obsolete framework closeout commands rather than adding a
        # second closeout hook for the same Codex Stop event.
        for group in stop_groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                group["hooks"] = [
                    hook for hook in group["hooks"]
                    if not self._is_governance_hook(hook)
                ]
        target_hooks = target_group.setdefault("hooks", [])
        target_hooks.append(self._hook_payload(framework_root))
        _write_json(hook_path, data)
        return {
            "status": "installed",
            "location": str(hook_path),
            "message": f"Governance Codex Stop hook added to {hook_path}.",
        }

    def verify(self, project_root: Path, framework_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        installed = self._find_current_hook(project_root, framework_root)
        return {
            "installed": installed,
            "manual_only": False,
            "location": str(hook_path) if installed else None,
            "note": (
                f"Single governance Codex Stop hook matches requested framework root {framework_root}."
                if installed else
                f"Governance Codex Stop hook is missing, stale, or duplicated for requested framework root {framework_root}."
            ) + " Configuration binding only; native execution is not verified.",
        }

    def uninstall(self, project_root: Path) -> dict[str, Any]:
        hook_path = self._hook_path(project_root)
        data = _read_json(hook_path)
        changed = False
        for group in data.get("hooks", {}).get("Stop", []):
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                continue
            before = len(group["hooks"])
            group["hooks"] = [
                hook for hook in group["hooks"]
                if not self._is_governance_hook(hook)
            ]
            changed = changed or len(group["hooks"]) < before
        if changed:
            _write_json(hook_path, data)
            return {
                "agent": self.agent_id,
                "status": "uninstalled",
                "location": str(hook_path),
                "message": "Governance Codex Stop hook removed from .codex/hooks.json.",
            }
        return {
            "agent": self.agent_id,
            "status": "not_found",
            "message": "No governance Codex Stop hook found to remove.",
        }

    def print_manual(self, framework_root: Path) -> str:
        cmd = _manual_closeout_cmd(framework_root, self.agent_id, "manual_fallback")
        return (
            f"[{self.display_name}] Manual closeout (fallback if Stop hook is not installed):\n\n"
            f"    {cmd}\n\n"
            f"Or install the Stop hook:\n\n"
            f"    python -m governance_tools.manage_agent_closeout install --agent codex"
        )


# ── Registry ──────────────────────────────────────────────────────────────────

_ADAPTERS: dict[str, AgentAdapter] = {
    a.agent_id: a for a in [
        ClaudeAdapter(),
        CopilotAdapter(),
        GeminiAdapter(),
        ChatGPTWebAdapter(),
        CodexCLIAdapter(),
    ]
}

KNOWN_AGENTS = list(_ADAPTERS.keys())


def get_adapter(agent_id: str) -> AgentAdapter | None:
    return _ADAPTERS.get(agent_id)


# ── Operations ────────────────────────────────────────────────────────────────

def op_status(project_root: Path, framework_root: Path) -> list[dict[str, Any]]:
    results = []
    for agent_id, adapter in _ADAPTERS.items():
        v = adapter.verify(project_root, framework_root)
        cap = adapter.capability()
        fallback_required = bool(cap.get("fallback_required")) or not bool(v["installed"])
        enforcement_level = "NATIVE_HOOK" if cap.get("auto_trigger_capable", False) else "MANUAL_FALLBACK"
        compliance_status = "READY" if v["installed"] else "PENDING_INSTALL"
        if enforcement_level == "MANUAL_FALLBACK":
            compliance_status = "PENDING_MANUAL_ACTION"
        results.append({
            "agent": agent_id,
            "display_name": cap["display_name"],
            "tier": cap["tier"],
            "tier_label": cap["tier_label"],
            "hook_surface": cap["surface_description"],
            "enforcement_level": enforcement_level,
            "installed": v["installed"],
            "manual_only": v.get("manual_only", False),
            "auto_trigger_capable": cap.get("auto_trigger_capable", False),
            "fallback_required": fallback_required,
            "compliance_status": compliance_status,
            "location": v.get("location"),
            "note": v.get("note"),
        })
    return results


def _run_synthetic_smoke(project_root: Path, framework_root: Path, agent_id: str) -> dict[str, Any]:
    import subprocess

    cmd = [
        sys.executable,
        str(framework_root / "governance_tools" / "session_closeout_entry.py"),
        "--project-root",
        str(project_root),
        "--format",
        "json",
        "--agent-id",
        agent_id,
        "--trigger-mode",
        "synthetic_smoke",
    ]
    if agent_id == "codex":
        from uuid import uuid4
        from runtime_hooks.core._canonical_closeout import write_session_envelope

        # Synthetic execution owns a fresh identity; never consume a live
        # session candidate through the repository-wide fallback pointer.
        session_id = f"codex-smoke-{uuid4().hex}"
        write_session_envelope(session_id, project_root, provider="codex")
        cmd.extend(["--session-id", session_id])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    stdout = proc.stdout.strip()
    payload: dict[str, Any] = {}
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw_stdout": stdout}

    evidence_path = project_root / "artifacts" / "runtime" / "closeout-trigger-evidence.ndjson"
    receipt_dir = project_root / "artifacts" / "runtime" / "closeout-receipts"
    receipt_recorded = False
    receipt_path_latest: str | None = None
    receipt_exit_code_ok = False
    receipt_artifact_exists = False
    memory_eligibility_evaluated = False
    memory_write_required = False
    memory_write_performed = False
    evidence_recorded = False
    if evidence_path.exists():
        lines = [line for line in evidence_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in reversed(lines[-20:]):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("agent_id") == agent_id and row.get("trigger_mode") == "synthetic_smoke":
                evidence_recorded = True
                break
    if receipt_dir.exists():
        for receipt in sorted(receipt_dir.glob("closeout_receipt_*.json"), reverse=True):
            try:
                data = json.loads(receipt.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("agent_id") == agent_id and data.get("trigger_mode") == "synthetic_smoke":
                receipt_recorded = True
                receipt_path_latest = str(receipt)
                receipt_exit_code_ok = data.get("exit_code") == 0
                artifact_path = str(data.get("closeout_artifact_path") or "").strip()
                receipt_artifact_exists = bool(artifact_path) and Path(artifact_path).exists()
                memory_eligibility_evaluated = bool(data.get("memory_eligibility_evaluated"))
                memory_write_required = bool(data.get("memory_write_required"))
                memory_write_performed = bool(data.get("memory_write_performed"))
                break

    compliant = (
        proc.returncode == 0
        and evidence_recorded
        and receipt_recorded
        and receipt_exit_code_ok
        and receipt_artifact_exists
        and memory_eligibility_evaluated
        and (not memory_write_required or memory_write_performed)
    )
    return {
        "agent": agent_id,
        "status": "pass" if compliant else "fail",
        "compliance_status": "COMPLIANT" if compliant else "NON_COMPLIANT",
        "exit_code": proc.returncode,
        "evidence_recorded": evidence_recorded,
        "evidence_path": str(evidence_path) if evidence_path.exists() else None,
        "receipt_recorded": receipt_recorded,
        "receipt_exit_code_ok": receipt_exit_code_ok,
        "receipt_artifact_exists": receipt_artifact_exists,
        "memory_eligibility_evaluated": memory_eligibility_evaluated,
        "memory_write_required": memory_write_required,
        "memory_write_performed": memory_write_performed,
        "receipt_path": receipt_path_latest,
        "closeout_artifact_path": payload.get("canonical_closeout_artifact"),
    }


def op_capabilities() -> list[dict[str, Any]]:
    return [a.capability() for a in _ADAPTERS.values()]


# ── Output formatting ─────────────────────────────────────────────────────────

def _fmt_status_human(results: list[dict[str, Any]]) -> str:
    lines = ["[manage_agent_closeout] status\n"]
    for r in results:
        if r["installed"]:
            marker = "✓"
        elif r["manual_only"]:
            marker = "—"
        else:
            marker = "✗"
        lines.append(
            f"  {marker} {r['display_name']:<24} "
            f"Tier {r['tier']}  {r['note']}"
        )
    lines += [
        "",
        "Legend: ✓ installed   ✗ not installed   — manual/stub only",
    ]
    return "\n".join(lines)


def _fmt_capabilities_human(caps: list[dict[str, Any]]) -> str:
    lines = ["[manage_agent_closeout] capabilities\n"]
    for c in caps:
        lines.append(f"  {c['display_name']:<24} Tier {c['tier']}  {c['tier_label']}")
        lines.append(f"      {c['surface_description']}")
        lines.append("")
    return "\n".join(lines)


def _fmt_op_human(result: dict[str, Any], operation: str) -> str:
    agent = result.get("agent", "?")
    if "installed" in result and operation in ("verify",):
        status_val = (
            "installed" if result["installed"]
            else "manual_only" if result.get("manual_only")
            else "not_installed"
        )
    else:
        status_val = result.get("status", "?")
    lines = [
        f"[manage_agent_closeout] {operation} --agent {agent}",
        f"status={status_val}",
    ]
    if result.get("location"):
        lines.append(f"location={result['location']}")
    if operation == "smoke":
        lines.append(f"exit_code={result.get('exit_code')}")
        lines.append(f"evidence_recorded={result.get('evidence_recorded')}")
        lines.append(f"receipt_recorded={result.get('receipt_recorded')}")
        lines.append(f"receipt_exit_code_ok={result.get('receipt_exit_code_ok')}")
        lines.append(f"receipt_artifact_exists={result.get('receipt_artifact_exists')}")
        lines.append(f"memory_eligibility_evaluated={result.get('memory_eligibility_evaluated')}")
        lines.append(f"memory_write_required={result.get('memory_write_required')}")
        lines.append(f"memory_write_performed={result.get('memory_write_performed')}")
        lines.append(f"compliance_status={result.get('compliance_status')}")
        if result.get("evidence_path"):
            lines.append(f"evidence_path={result['evidence_path']}")
        if result.get("receipt_path"):
            lines.append(f"receipt_path={result['receipt_path']}")
        if result.get("closeout_artifact_path"):
            lines.append(f"closeout_artifact_path={result['closeout_artifact_path']}")
    msg = result.get("message") or result.get("note", "")
    if msg:
        lines.append(f"message={msg}")
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
    parser.add_argument("--project-root", default=".", help="Project root (default: .)")
    parser.add_argument("--format", choices=["human", "json"], default="human")

    sub = parser.add_subparsers(dest="operation", required=True)

    sub.add_parser("status", help="Show integration status for all agents")
    sub.add_parser("capabilities", help="Show capability tiers for all agents")

    for op in ("install", "verify", "repair", "uninstall", "smoke"):
        p = sub.add_parser(op, help=f"{op.capitalize()} integration for an agent")
        p.add_argument("--agent", choices=KNOWN_AGENTS + ["all"], required=True)

    pm = sub.add_parser("print-manual", help="Print manual closeout instructions for an agent")
    pm.add_argument("--agent", choices=KNOWN_AGENTS, required=True)

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    framework_root = _resolve_framework_root()

    if args.operation == "status":
        results = op_status(project_root, framework_root)
        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(_fmt_status_human(results))
        return 0

    if args.operation == "capabilities":
        caps = op_capabilities()
        if args.format == "json":
            print(json.dumps(caps, ensure_ascii=False, indent=2))
        else:
            print(_fmt_capabilities_human(caps))
        return 0

    if args.operation == "print-manual":
        adapter = get_adapter(args.agent)
        if not adapter:
            print(f"Unknown agent: {args.agent}", file=sys.stderr)
            return 1
        print(adapter.print_manual(framework_root))
        return 0

    # install / verify / repair / uninstall
    agents = KNOWN_AGENTS if args.agent == "all" else [args.agent]
    results = []
    for agent_id in agents:
        adapter = get_adapter(agent_id)
        if not adapter:
            results.append({"agent": agent_id, "status": "unknown_agent"})
            continue
        if args.operation == "install":
            r = adapter.install(project_root, framework_root)
            results.append({"agent": agent_id, **r})
        elif args.operation == "verify":
            r = adapter.verify(project_root, framework_root)
            results.append({"agent": agent_id, **r})
        elif args.operation == "repair":
            results.append(adapter.repair(project_root, framework_root))
        elif args.operation == "uninstall":
            results.append(adapter.uninstall(project_root))
        elif args.operation == "smoke":
            results.append(_run_synthetic_smoke(project_root, framework_root, agent_id))

    if args.format == "json":
        out = results[0] if len(results) == 1 else results
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(_fmt_op_human(r, args.operation))

    if args.operation == "verify":
        all_ok = all(r.get("installed") or r.get("manual_only") for r in results)
        return 0 if all_ok else 1
    if args.operation == "smoke":
        all_ok = all(r.get("status") == "pass" for r in results)
        return 0 if all_ok else 1
    if args.operation in {"install", "repair"}:
        failed = any(r.get("status") in {"blocked", "error", "unknown_agent"} for r in results)
        return 1 if failed else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
