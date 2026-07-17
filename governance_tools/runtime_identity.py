#!/usr/bin/env python3
"""Runtime identity detection — report-only, no LLM calls, no network calls.

Detects which agent, model, and surface the current session runs under and
writes a profile conforming to schemas/runtime_identity.schema.json.

Claim boundary: "verified" means verified against an approved runtime signal
(environment marker, harness-written artifact, or hook payload), NOT
cryptographically proven runtime identity; runtime signals can be inherited,
overwritten, or forged. Detection failure degrades to "unknown" — this tool
never guesses, never blocks work, and never emits "reported" values.

Primary signals are environment markers and the SessionStart hook payload.
Parent-process-chain detection is deliberately not implemented in this
version: spike evidence (spikes/runtime-detect/SIGNALS.md) showed the chain
breaks when intermediate shells exit, making it too fragile for anything but
a future fallback.

Budget entry: docs/governance/agent-runtime-evaluation-budget-entry-2026-07-16.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RUNTIME_IDENTITY_SCHEMA_VERSION = "1.0"
FINGERPRINT_SCHEMA_VERSION = "1.0"
TOOL_NAME = "governance_tools.runtime_identity"
TOOL_VERSION = "0.1.0"
DEFAULT_PROFILE_RELPATH = Path(".governance") / "runtime-profile.json"

RUNTIME_IDENTITY_CLAIM_BOUNDARY = (
    "signal-verified runtime identity only; not cryptographic proof, "
    "not an evaluation, not a gate"
)

# Agent identity markers: exact env var (or prefix ending in "_") -> agent id.
# Evidence for each marker: spikes/runtime-detect/SIGNALS.md.
_AGENT_ENV_MARKERS = (
    ("CLAUDECODE", "claude_code"),
    ("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "codex"),
    ("COPILOT_AGENT", "github_copilot"),
    ("GEMINI_CLI", "gemini_cli"),
    ("CURSOR_TRACE_ID", "cursor"),
    ("CURSOR_AGENT", "cursor"),
)

# Declarative model-id normalization. Unrecognized ids map to family
# "unknown" — never string-guessed.
_MODEL_PATTERNS: tuple = (
    (
        re.compile(r"^claude-([a-z]+)-(\d+)(?:-(\d+))?$"),
        lambda m: {
            "provider": "anthropic",
            "family": f"claude-{m.group(1)}",
            "version": m.group(2) + (f".{m.group(3)}" if m.group(3) else ""),
        },
    ),
    (
        re.compile(r"^gpt-(\d+)(?:\.(\d+))?(?:-([a-z0-9]+))?$"),
        lambda m: {
            "provider": "openai",
            "family": f"gpt-{m.group(1)}",
            "version": m.group(1) + (f".{m.group(2)}" if m.group(2) else ""),
            **({"variant": m.group(3)} if m.group(3) else {}),
        },
    ),
    (
        re.compile(r"^gemini-(\d+(?:\.\d+)?)-([a-z0-9-]+)$"),
        lambda m: {
            "provider": "google",
            "family": f"gemini-{m.group(1).split('.')[0]}",
            "version": m.group(1),
            "variant": m.group(2),
        },
    ),
)

_SURFACE_CLASS_BY_VALUE = {
    "claude-desktop": "desktop_app",
    "cli": "cli",
    "vscode": "ide",
    "jetbrains": "ide",
    "cursor": "ide",
    "windows_terminal": "cli",
    "github_actions": "ci",
}

_README_VERSION_PATTERNS = (
    re.compile(r"- version:\s*`([^`]+)`"),
    re.compile(r"badge/version-(\d+\.\d+\.\d+(?:-[^-\s]+)?)-"),
    re.compile(r"\*\*Version (\d+\.\d+\.\d+(?:-[^*\s]+)?)\*\*"),
)


# ---------------------------------------------------------------------------
# Field constructors
# ---------------------------------------------------------------------------

def _field(value, detection: str, signal_source: Optional[str] = None,
           binding_scope: str = "unknown", evidence: str = "") -> dict:
    out: dict[str, Any] = {"value": value, "detection": detection}
    if signal_source is not None:
        out["signal_source"] = signal_source
    if binding_scope != "unknown":
        out["binding_scope"] = binding_scope
    if evidence:
        out["evidence"] = evidence
    return out


def _unknown(evidence: str = "") -> dict:
    out: dict[str, Any] = {"value": None, "detection": "unknown"}
    if evidence:
        out["evidence"] = evidence
    return out


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_model_id(raw_id: str) -> dict:
    """Map a raw model id to structured identity via the declarative table."""
    raw_id = raw_id.strip()
    for pattern, build in _MODEL_PATTERNS:
        match = pattern.match(raw_id)
        if match:
            identity = build(match)
            identity["raw_id"] = raw_id
            return identity
    return {"provider": "unknown", "family": "unknown", "raw_id": raw_id}


def classify_surface(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    if value in _SURFACE_CLASS_BY_VALUE:
        return _SURFACE_CLASS_BY_VALUE[value]
    if value.startswith("sdk"):
        return "sdk"
    if "desktop" in value:
        return "desktop_app"
    return "unknown"


# ---------------------------------------------------------------------------
# Detection (pure functions over an env mapping; every probe fails closed)
# ---------------------------------------------------------------------------

def detect_agent(env: Mapping[str, str]) -> dict:
    for marker, agent in _AGENT_ENV_MARKERS:
        if marker.endswith("_"):
            hits = sorted(k for k in env if k.startswith(marker))
            if hits:
                return _field(agent, "verified", f"env:{hits[0]}", "session")
        elif env.get(marker):
            return _field(agent, "verified", f"env:{marker}", "session")
    return _unknown("no approved agent env marker present")


def detect_agent_version(env: Mapping[str, str], agent: Optional[str]) -> dict:
    execpath = env.get("CLAUDE_CODE_EXECPATH", "")
    match = re.search(r"claude-code[\\/]+(\d+\.\d+\.\d+)", execpath)
    if match and agent == "claude_code":
        return _field(match.group(1), "verified", "env:CLAUDE_CODE_EXECPATH",
                      "session", "version segment of running executable path")
    return _unknown("no session-bound version signal; CLI probing is not "
                    "done here (installation-bound at best)")


def detect_model(env: Mapping[str, str], agent: Optional[str],
                 home: Path) -> dict:
    for key in ("ANTHROPIC_MODEL", "CLAUDE_MODEL", "OPENAI_MODEL", "GEMINI_MODEL"):
        raw = env.get(key)
        if raw:
            return _field(normalize_model_id(raw), "verified", f"env:{key}",
                          "session")
    if agent == "claude_code":
        sid = env.get("CLAUDE_CODE_SESSION_ID")
        if sid and _SAFE_ID_RE.match(sid):
            try:
                for transcript in (home / ".claude" / "projects").glob(f"*/{sid}.jsonl"):
                    models = re.findall(
                        r'"model"\s*:\s*"([^"]+)"',
                        transcript.read_text(encoding="utf-8", errors="ignore"))
                    if models:
                        return _field(
                            normalize_model_id(models[-1]), "verified",
                            "harness_transcript", "session",
                            "session-id-keyed transcript written by harness")
            except OSError:
                pass
    if agent == "codex":
        try:
            config = home / ".codex" / "config.toml"
            if config.is_file():
                match = re.search(r'^\s*model\s*=\s*"([^"]+)"',
                                  config.read_text(encoding="utf-8", errors="ignore"),
                                  re.MULTILINE)
                if match:
                    return _field(
                        normalize_model_id(match.group(1)), "detected",
                        "config:codex_config_toml", "config_default",
                        "configured default; this session may have overridden it")
        except OSError:
            pass
    if agent == "gemini_cli":
        try:
            settings = home / ".gemini" / "settings.json"
            if settings.is_file():
                raw = json.loads(settings.read_text(encoding="utf-8", errors="ignore")).get("model")
                if isinstance(raw, str) and raw:
                    return _field(
                        normalize_model_id(raw), "detected",
                        "config:gemini_settings_json", "config_default",
                        "configured default; this session may have overridden it")
        except (OSError, ValueError):
            pass
    return _unknown("no approved model signal for this agent")


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")


def detect_surface(env: Mapping[str, str]) -> dict:
    entrypoint = env.get("CLAUDE_CODE_ENTRYPOINT")
    if entrypoint:
        field = _field(entrypoint, "verified", "env:CLAUDE_CODE_ENTRYPOINT",
                       "session")
    elif env.get("CURSOR_TRACE_ID") or env.get("CURSOR_AGENT"):
        field = _field("cursor", "verified", "env:CURSOR_*", "session")
    elif env.get("TERM_PROGRAM") == "vscode":
        field = _field("vscode", "verified", "env:TERM_PROGRAM", "session")
    elif "JetBrains" in env.get("TERMINAL_EMULATOR", ""):
        field = _field("jetbrains", "verified", "env:TERMINAL_EMULATOR", "session")
    elif env.get("GITHUB_ACTIONS"):
        field = _field("github_actions", "verified", "env:GITHUB_ACTIONS", "session")
    elif env.get("WT_SESSION"):
        field = _field("windows_terminal", "verified", "env:WT_SESSION", "session")
    else:
        field = _unknown("no surface marker")
    field["surface_class"] = classify_surface(field["value"])
    return field


def detect_session_id(env: Mapping[str, str]) -> dict:
    for key in ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):
        value = env.get(key)
        if value:
            return _field(value, "verified", f"env:{key}", "session")
    return _unknown("no session id marker")


def detect_governance_version(repo_root: Path) -> dict:
    try:
        readme = repo_root / "README.md"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="ignore")
            for pattern in _README_VERSION_PATTERNS:
                match = pattern.search(text)
                if match:
                    return _field(match.group(1), "verified", "repo:README.md",
                                  "repo")
    except OSError:
        pass
    return _unknown("no README version marker")


def extract_hook_payload_fields(payload: Optional[Mapping[str, Any]]) -> tuple:
    """permission_mode and tools come only from a hook payload."""
    if not isinstance(payload, Mapping):
        reason = "hook payload not provided; not visible from shell env"
        return _unknown(reason), _unknown(reason)
    mode = payload.get("permission_mode")
    permission = (
        _field(mode, "verified", "hook_payload:permission_mode", "session")
        if isinstance(mode, str) and mode
        else _unknown("hook payload has no permission_mode")
    )
    raw_tools = payload.get("tools")
    tools = (
        _field(sorted(str(t) for t in raw_tools), "verified",
               "hook_payload:tools", "session")
        if isinstance(raw_tools, (list, tuple)) and raw_tools
        else _unknown("hook payload has no tools list")
    )
    return permission, tools


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------

def _hash_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"rp_{digest[:12]}"


def build_fingerprint(agent: dict, model: dict, surface: dict,
                      agent_version: dict, governance_version: dict) -> dict:
    agent_family = agent["value"] or "unknown"
    model_value = model["value"] or {}
    model_family = model_value.get("family", "unknown")
    surface_class = surface.get("surface_class", "unknown")

    if agent_family == "unknown" and model_family == "unknown":
        coarse_id = "unknown"
    else:
        coarse_id = _hash_id(agent_family, model_family, surface_class)

    # full_id covers all normalized identity fields but deliberately excludes
    # session_id and timestamps: it must be stable across sessions on the
    # same runtime, changing only when the runtime itself changes.
    full_inputs = json.dumps({
        "agent": agent_family,
        "agent_version": agent_version["value"] or "unknown",
        "model": {k: model_value.get(k, "unknown")
                  for k in ("provider", "family", "variant", "version",
                            "revision", "raw_id")},
        "surface": surface["value"] or "unknown",
        "surface_class": surface_class,
        "governance_version": governance_version["value"] or "unknown",
    }, sort_keys=True)
    full_id = ("unknown" if coarse_id == "unknown"
               else _hash_id(full_inputs))

    return {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "coarse_id": coarse_id,
        "full_id": full_id,
        "coarse_inputs": {
            "agent_family": agent_family,
            "model_family": model_family,
            "surface_class": surface_class,
        },
    }


# ---------------------------------------------------------------------------
# Profile assembly
# ---------------------------------------------------------------------------

def build_profile(env: Mapping[str, str], home: Path, repo_root: Path,
                  hook_payload: Optional[Mapping[str, Any]] = None,
                  now: Optional[datetime] = None) -> dict:
    agent = detect_agent(env)
    agent_version = detect_agent_version(env, agent["value"])
    model = detect_model(env, agent["value"], home)
    surface = detect_surface(env)
    session_id = detect_session_id(env)
    governance_version = detect_governance_version(repo_root)
    permission_mode, tools = extract_hook_payload_fields(hook_payload)

    identity_fields = (agent, agent_version, model, surface, session_id)
    if all(f["detection"] == "verified" for f in (agent, model, surface)):
        detection_status = "full"
    elif any(f["detection"] != "unknown" for f in identity_fields):
        detection_status = "partial"
    else:
        detection_status = "none"

    return {
        "schema_version": RUNTIME_IDENTITY_SCHEMA_VERSION,
        "detected_at": (now or datetime.now(timezone.utc)).isoformat(),
        "detection_status": detection_status,
        "agent": agent,
        "agent_version": agent_version,
        "model": model,
        "surface": surface,
        "session_id": session_id,
        "permission_mode": permission_mode,
        "tools": tools,
        "governance_version": governance_version,
        "fingerprint": build_fingerprint(agent, model, surface, agent_version,
                                         governance_version),
        "generator": {
            "tool": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "llm_calls": 0,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _render_summary(profile: dict) -> str:
    lines = [
        f"runtime identity ({RUNTIME_IDENTITY_CLAIM_BOUNDARY})",
        f"detection_status: {profile['detection_status']}",
    ]
    for name in ("agent", "agent_version", "model", "surface", "session_id",
                 "permission_mode", "tools", "governance_version"):
        field = profile[name]
        value = field["value"]
        if name == "model" and isinstance(value, dict):
            value = value.get("raw_id", "unknown")
        if isinstance(value, list):
            value = ",".join(value)
        source = field.get("signal_source", "")
        lines.append(f"  {name:20} {field['detection']:9} "
                     f"{value if value is not None else '-'}"
                     f"{'  <- ' + source if source else ''}")
    fp = profile["fingerprint"]
    lines.append(f"  coarse_id: {fp['coarse_id']}  full_id: {fp['full_id']}  "
                 f"(fingerprint schema {fp['fingerprint_schema_version']})")
    return "\n".join(lines)


def _print_console_safe(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding))
    sys.stdout.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Report-only runtime identity detection. "
                    + RUNTIME_IDENTITY_CLAIM_BOUNDARY,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="detect and write runtime profile")
    detect.add_argument("--repo", default=".", help="repo root (default: cwd)")
    detect.add_argument("--hook-payload", default=None,
                        help="path to a SessionStart hook payload JSON file")
    detect.add_argument("--out", default=None,
                        help="output path (default: <repo>/.governance/runtime-profile.json)")
    detect.add_argument("--print", dest="print_json", action="store_true",
                        help="also print the profile JSON to stdout")

    show = sub.add_parser("show", help="show the stored runtime profile")
    show.add_argument("--repo", default=".", help="repo root (default: cwd)")
    return parser


def main(argv: Optional[list] = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = Path(args.repo).resolve()

    if args.command == "show":
        profile_path = repo_root / DEFAULT_PROFILE_RELPATH
        if not profile_path.is_file():
            _print_console_safe(f"no runtime profile at {DEFAULT_PROFILE_RELPATH}; "
                                "run: python -m governance_tools.runtime_identity detect")
            return 0
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _print_console_safe(f"runtime profile unreadable ({type(exc).__name__}); "
                                "re-run detect")
            return 0
        _print_console_safe(_render_summary(profile))
        return 0

    hook_payload = None
    if args.hook_payload:
        try:
            hook_payload = json.loads(
                Path(args.hook_payload).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            hook_payload = None  # degrade: payload fields stay unknown

    profile = build_profile(os.environ, Path.home(), repo_root, hook_payload)

    out_path = Path(args.out) if args.out else repo_root / DEFAULT_PROFILE_RELPATH
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(
            json.dumps(profile, indent=2, ensure_ascii=False).encode("utf-8"))
    except OSError as exc:
        # Report-only tool: failure to persist must not block work.
        _print_console_safe(f"warning: could not write profile ({type(exc).__name__}); "
                            "detection output follows")
        _print_console_safe(_render_summary(profile))
        return 0

    _print_console_safe(_render_summary(profile))
    if args.print_json:
        _print_console_safe(json.dumps(profile, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
