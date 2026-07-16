"""Throwaway runtime-detection spike.

Probes the current environment for agent / model / surface identity signals
WITHOUT any LLM or network call. Every field degrades to "unknown" on failure.

Detection tiers (plan 0.2): verified > detected > reported > unknown.
This script never emits "reported" — self-reported values are out of scope.

Usage:
    python -X utf8 spikes/runtime-detect/detect_spike.py          # human summary
    python -X utf8 spikes/runtime-detect/detect_spike.py --json   # machine JSON

Stdlib only, Python 3.9+. Delete this whole directory once the go/no-go
decision is made; only the recorded result JSONs / SIGNALS.md matter.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REDACT = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.IGNORECASE)
ENV_PREFIXES = (
    "CLAUDE", "ANTHROPIC", "CODEX", "GEMINI", "CURSOR", "COPILOT",
    "AIDER", "VSCODE", "TERM", "WT_", "TERMINAL_EMULATOR", "OPENAI",
)
CLI_PROBES = ("claude", "codex", "gemini", "aider")
AGENT_PROC_MARKERS = {
    "claude": "claude_code", "codex": "codex", "gemini": "gemini_cli",
    "cursor": "cursor", "aider": "aider",
}


def field(value, detection, source, evidence=None):
    out = {"value": value, "detection": detection, "source": source}
    if evidence:
        out["evidence"] = evidence
    return out


def unknown(reason):
    return field(None, "unknown", None, reason)


def scan_env():
    hits = {}
    for k, v in os.environ.items():
        if any(k.upper().startswith(p) for p in ENV_PREFIXES):
            hits[k] = "<redacted>" if REDACT.search(k) else v
    return dict(sorted(hits.items()))


def probe_clis():
    out = {}
    for name in CLI_PROBES:
        path = shutil.which(name)
        if not path:
            out[name] = {"on_path": False}
            continue
        version = None
        try:
            r = subprocess.run(
                [name, "--version"], capture_output=True, text=True, timeout=10
            )
            version = (r.stdout or r.stderr).strip().splitlines()[0][:120] if (r.stdout or r.stderr).strip() else None
        except Exception as exc:  # spike: never crash on a probe
            version = f"<probe failed: {type(exc).__name__}>"
        out[name] = {"on_path": True, "path": path, "version": version}
    return out


def parent_chain():
    """Best-effort process ancestry: [(pid, name), ...] from self upward."""
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=30,
            )
            procs = {p["ProcessId"]: p for p in json.loads(r.stdout)}
            chain, pid, seen = [], os.getpid(), set()
            while pid in procs and pid not in seen and len(chain) < 15:
                seen.add(pid)
                chain.append((pid, procs[pid].get("Name", "?")))
                pid = procs[pid].get("ParentProcessId")
            return chain
        chain, pid = [], os.getpid()
        while pid and pid != 1 and len(chain) < 15:
            stat = Path(f"/proc/{pid}/stat").read_text()
            name = stat[stat.index("(") + 1:stat.rindex(")")]
            chain.append((pid, name))
            pid = int(stat[stat.rindex(")") + 2:].split()[1])
        return chain
    except Exception:
        return []


def detect_agent(env, chain):
    if env.get("CLAUDECODE") == "1":
        return field("claude_code", "verified", "env:CLAUDECODE")
    for prefix, agent in (("CODEX_", "codex"), ("GEMINI_CLI", "gemini_cli"),
                          ("CURSOR_", "cursor"), ("COPILOT_AGENT", "github_copilot")):
        keys = [k for k in env if k.startswith(prefix)]
        if keys:
            return field(agent, "verified", f"env:{keys[0]}")
    for _, name in chain:
        for marker, agent in AGENT_PROC_MARKERS.items():
            if marker in name.lower():
                return field(agent, "detected", f"parent_process:{name}")
    return unknown("no env marker, no known parent process")


def detect_agent_version(env, clis, agent):
    execpath = env.get("CLAUDE_CODE_EXECPATH", "")
    m = re.search(r"claude-code[\\/]+(\d+\.\d+\.\d+)", execpath)
    if m:
        return field(m.group(1), "verified", "env:CLAUDE_CODE_EXECPATH")
    name = {"claude_code": "claude", "codex": "codex", "gemini_cli": "gemini"}.get(agent)
    info = clis.get(name or "", {})
    if info.get("on_path") and info.get("version") and not str(info["version"]).startswith("<"):
        # Installed CLI version == running version only probabilistically.
        return field(info["version"], "detected", f"cli:{name} --version (installed, not session-bound)")
    return unknown("no version in env; matching CLI not on PATH")


def detect_model(env, agent):
    for k in ("ANTHROPIC_MODEL", "CLAUDE_MODEL", "OPENAI_MODEL", "GEMINI_MODEL"):
        if env.get(k):
            return field(env[k], "verified", f"env:{k}")
    if agent == "claude_code":
        sid = env.get("CLAUDE_CODE_SESSION_ID")
        if sid:
            for tr in Path.home().joinpath(".claude", "projects").glob(f"*/{sid}.jsonl"):
                models = re.findall(r'"model":"([^"]+)"', tr.read_text(encoding="utf-8", errors="ignore"))
                if models:
                    return field(models[-1], "verified",
                                 f"harness_transcript:{tr.name}",
                                 f"{len(models)} occurrences, session-id-bound")
    if agent == "codex":
        cfg = Path.home() / ".codex" / "config.toml"
        if cfg.is_file():
            m = re.search(r'^\s*model\s*=\s*"([^"]+)"', cfg.read_text(encoding="utf-8", errors="ignore"), re.M)
            if m:
                return field(m.group(1), "detected", "config:~/.codex/config.toml (default, not session-bound)")
        rollouts = sorted(Path.home().joinpath(".codex", "sessions").rglob("rollout-*.jsonl"))
        if rollouts:
            models = re.findall(r'"model":"([^"]+)"', rollouts[-1].read_text(encoding="utf-8", errors="ignore"))
            if models:
                return field(models[-1], "detected", f"codex_rollout:{rollouts[-1].name} (latest file, session binding unproven)")
    if agent == "gemini_cli":
        cfg = Path.home() / ".gemini" / "settings.json"
        if cfg.is_file():
            try:
                model = json.loads(cfg.read_text(encoding="utf-8", errors="ignore")).get("model")
                if model:
                    return field(model, "detected", "config:~/.gemini/settings.json (default, not session-bound)")
            except Exception:
                pass
    return unknown("no env/harness-artifact model signal")


def detect_surface(env):
    ep = env.get("CLAUDE_CODE_ENTRYPOINT")
    if ep:
        return field(ep, "verified", "env:CLAUDE_CODE_ENTRYPOINT")
    if env.get("CURSOR_TRACE_ID") or env.get("CURSOR_AGENT"):
        return field("cursor", "verified", "env:CURSOR_*")
    if env.get("TERM_PROGRAM") == "vscode":
        return field("vscode", "verified", "env:TERM_PROGRAM")
    if "JetBrains" in env.get("TERMINAL_EMULATOR", ""):
        return field("jetbrains", "verified", "env:TERMINAL_EMULATOR")
    if env.get("WT_SESSION"):
        return field("windows_terminal", "verified", "env:WT_SESSION")
    return unknown("no surface marker")


def detect_governance_version():
    for base in (Path.cwd(), *Path.cwd().parents):
        readme = base / "README.md"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="ignore")
            m = (re.search(r"- version:\s*`([^`]+)`", text)
                 or re.search(r"badge/version-(\d+\.\d+\.\d+(?:-[^-\s]+)?)-", text)
                 or re.search(r"\*\*Version (\d+\.\d+\.\d+(?:-[^*\s]+)?)\*\*", text))
            if m:
                return field(m.group(1), "verified", f"readme:{readme}")
        if (base / ".git").exists():
            break
    return unknown("no README version marker up to repo root")


def main():
    env = scan_env()
    clis = probe_clis()
    chain = parent_chain()

    agent = detect_agent(env, chain)
    profile = {
        "agent": agent,
        "agent_version": detect_agent_version(env, clis, agent["value"]),
        "model": detect_model(env, agent["value"]),
        "surface": detect_surface(env),
        "session_id": (
            field(env["CLAUDE_CODE_SESSION_ID"], "verified", "env:CLAUDE_CODE_SESSION_ID")
            if env.get("CLAUDE_CODE_SESSION_ID") else unknown("no session id in env")
        ),
        "permission_mode": unknown("not exposed to shell; real impl must read hook payload"),
        "tools": unknown("not exposed to shell; real impl must read hook payload"),
        "governance_version": detect_governance_version(),
    }
    report = {
        "spike": "runtime-detect", "schema": "spike-0",
        "platform": sys.platform,
        "profile": profile,
        "raw": {"env_markers": env, "cli_probes": clis,
                "parent_chain": [{"pid": p, "name": n} for p, n in chain]},
    }

    if "--out" in sys.argv:
        # PowerShell 5.1 `>` redirection writes UTF-16; write bytes directly.
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.write_bytes(json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"))
        print(f"written: {out}")
        return
    if "--json" in sys.argv:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        return
    print(f"runtime-detect spike  (platform={sys.platform})")
    print("-" * 64)
    for name, f in profile.items():
        val = f["value"] if f["value"] is not None else "-"
        print(f"{name:20} {f['detection']:9} {val}")
        src = f.get("source") or f.get("evidence")
        if src:
            print(f"{'':20} {'':9} <- {src}")
    tiers = [f["detection"] for f in profile.values()]
    print("-" * 64)
    print(f"verified={tiers.count('verified')}  detected={tiers.count('detected')}  unknown={tiers.count('unknown')}")
    print("full evidence: rerun with --json")


if __name__ == "__main__":
    main()
