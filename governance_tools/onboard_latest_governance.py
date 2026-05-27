#!/usr/bin/env python3
"""
One-command onboarding helper driven by the latest governance matrix snapshot.

Usage examples:
  python -m governance_tools.onboard_latest_governance --repo E:/repo --mode plan
  python -m governance_tools.onboard_latest_governance --repo E:/repo --mode apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _normalize(path_text: str) -> str:
    return str(Path(path_text).resolve()).lower()


def _find_latest_snapshot(project_root: Path) -> Path:
    session_dir = project_root / "artifacts" / "session"
    candidates = sorted(session_dir.glob("governance_repo_matrix_snapshot_*.json"))
    if not candidates:
        raise FileNotFoundError("No governance_repo_matrix_snapshot_*.json found under artifacts/session")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _repo_matches(candidate: str, requested: Path) -> bool:
    candidate_norm = _normalize(candidate)
    requested_norm = _normalize(str(requested))
    if candidate_norm == requested_norm:
        return True
    return Path(candidate_norm).name == requested.name.lower()


def _select_repo_row(snapshot: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    rows = snapshot.get("operational_maturity", {}).get("remediation_suggestions", [])
    for row in rows:
        repo = row.get("repo", "")
        if isinstance(repo, str) and _repo_matches(repo, repo_path):
            return row
    raise ValueError(f"Target repo not found in remediation_suggestions: {repo_path}")


def _replace_repo_placeholder(text: str, repo_path: Path) -> str:
    return text.replace("<repo>", str(repo_path))


def _run_powershell_command(command: str, workdir: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _bool_cmd(repo_path: Path, command: str) -> bool:
    code, _, _ = _run_powershell_command(command, repo_path)
    return code == 0


def _signal_hooks(repo_path: Path) -> bool:
    cmd = f'python -m governance_tools.manage_agent_closeout --project-root "{repo_path}" verify --agent all'
    return _bool_cmd(repo_path, cmd)


def _signal_fw(repo_path: Path) -> bool:
    return (repo_path / "governance" / "framework.lock.json").exists()


def _signal_agents(repo_path: Path) -> bool:
    return (repo_path / "AGENTS.md").exists()


def _load_latest_closeout_receipt(repo_path: Path) -> dict[str, Any] | None:
    receipts_dir = repo_path / "artifacts" / "runtime" / "closeout-receipts"
    if not receipts_dir.is_dir():
        return None
    files = sorted(receipts_dir.glob("closeout_receipt_*.json"))
    if not files:
        return None
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return _load_json(latest)


def _signal_evidence_head_ts(repo_path: Path, window_days: int) -> tuple[bool, bool, bool]:
    receipt = _load_latest_closeout_receipt(repo_path)
    if not receipt:
        return False, False, False

    evidence_ok = True
    linked_head = str(receipt.get("linked_head_commit", "")).strip()
    if not linked_head:
        return False, False, False

    safe_repo = str(repo_path).replace("'", "''")
    code, stdout, _ = _run_powershell_command(f"git -c safe.directory='{safe_repo}' rev-parse HEAD", repo_path)
    if code != 0:
        return evidence_ok, False, False
    current_head = stdout.strip()
    head_ok = current_head == linked_head

    ts_text = str(receipt.get("timestamp", "")).strip()
    if not ts_text:
        return evidence_ok, head_ok, False

    try:
        dt = datetime.fromisoformat(ts_text.replace("Z", "+00:00"))
    except ValueError:
        return evidence_ok, head_ok, False
    age_days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400.0
    ts_ok = age_days <= float(window_days)
    return evidence_ok, head_ok, ts_ok


def _compute_acceptance(repo_path: Path, window_days: int) -> dict[str, Any]:
    hooks = _signal_hooks(repo_path)
    fw = _signal_fw(repo_path)
    agents = _signal_agents(repo_path)
    evidence, head_ok, ts_ok = _signal_evidence_head_ts(repo_path, window_days)
    verified = hooks and fw and agents and evidence and head_ok and ts_ok
    return {
        "hooks": hooks,
        "fw": fw,
        "agents": agents,
        "evidence": evidence,
        "head_ok": head_ok,
        "ts_ok": ts_ok,
        "repo_native_verified": verified,
    }


def _render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "[onboard_latest_governance]",
        f"mode={payload['mode']}",
        f"repo={payload['repo']}",
        f"snapshot={payload['snapshot']}",
        f"classification_before={payload['classification_before']}",
        f"classification_after={payload['classification_after']}",
        f"stopped_for_human_required={payload['stopped_for_human_required']}",
        "",
        "[acceptance_after]",
    ]
    for key in ("hooks", "fw", "agents", "evidence", "head_ok", "ts_ok", "repo_native_verified"):
        lines.append(f"{key}={payload['acceptance_after'][key]}")
    lines.append("")
    lines.append("[actions]")
    for item in payload["actions"]:
        status = item.get("status", "planned")
        lines.append(f"- blocker={item['blocker']} type={item['remediation_type']} human_required={item['human_required']} status={status}")
        if item.get("resolved_command"):
            lines.append(f"  command: {item['resolved_command']}")
        if item.get("action"):
            lines.append(f"  action: {item['action']}")
    return "\n".join(lines)


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Apply latest matrix remediation suggestions for one repo.")
    parser.add_argument("--repo", required=True, help="Target repository path.")
    parser.add_argument("--mode", choices=["plan", "apply"], default="plan")
    parser.add_argument("--snapshot", help="Optional snapshot JSON path; default is latest under artifacts/session.")
    parser.add_argument("--project-root", default=".", help="Framework project root.")
    parser.add_argument("--refresh-snapshot-command", help="Optional command to refresh matrix snapshot after apply.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    parser.add_argument("--write-report", action="store_true", help="Write result JSON under artifacts/session.")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    repo_path = Path(args.repo).resolve()
    snapshot_path = Path(args.snapshot).resolve() if args.snapshot else _find_latest_snapshot(project_root)
    snapshot = _load_json(snapshot_path)
    row = _select_repo_row(snapshot, repo_path)
    window_days = int(snapshot.get("evidence_window_days", 7))

    actions: list[dict[str, Any]] = []
    stopped_for_human = False

    for suggestion in row.get("suggestions", []):
        cmd = str(suggestion.get("command", "")).strip()
        action_text = str(suggestion.get("action", "")).strip()
        resolved_cmd = _replace_repo_placeholder(cmd, repo_path) if cmd else ""
        action_item: dict[str, Any] = {
            "blocker": suggestion.get("blocker"),
            "remediation_type": suggestion.get("remediation_type"),
            "human_required": bool(suggestion.get("human_required", False)),
            "action": action_text,
            "resolved_command": resolved_cmd,
            "status": "planned",
        }

        if args.mode == "apply" and not stopped_for_human:
            if action_item["human_required"]:
                action_item["status"] = "stopped_human_required"
                stopped_for_human = True
            elif resolved_cmd:
                code, stdout, stderr = _run_powershell_command(resolved_cmd, project_root)
                action_item["status"] = "executed" if code == 0 else "failed"
                action_item["exit_code"] = code
                action_item["stdout_tail"] = "\n".join(stdout.splitlines()[-20:])
                action_item["stderr_tail"] = "\n".join(stderr.splitlines()[-20:])
                if code != 0:
                    stopped_for_human = True
            else:
                action_item["status"] = "no_command"
        actions.append(action_item)

    refreshed_snapshot_path = snapshot_path
    if args.mode == "apply" and args.refresh_snapshot_command and not stopped_for_human:
        code, _, _ = _run_powershell_command(args.refresh_snapshot_command, project_root)
        if code == 0:
            refreshed_snapshot_path = _find_latest_snapshot(project_root)

    after_snapshot = _load_json(refreshed_snapshot_path)
    try:
        after_row = _select_repo_row(after_snapshot, repo_path)
        classification_after = str(after_row.get("classification", "unknown"))
    except ValueError:
        classification_after = "unknown"

    acceptance_after = _compute_acceptance(repo_path, window_days)
    if acceptance_after["repo_native_verified"] and classification_after != "repo_native_verified":
        classification_after = "repo_native_verified"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "repo": str(repo_path),
        "project_root": str(project_root),
        "snapshot": str(snapshot_path),
        "snapshot_after": str(refreshed_snapshot_path),
        "classification_before": row.get("classification"),
        "classification_after": classification_after,
        "stopped_for_human_required": stopped_for_human,
        "actions": actions,
        "acceptance_after": acceptance_after,
    }

    if args.write_report:
        out_dir = project_root / "artifacts" / "session"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"onboard_latest_governance_{repo_path.name}_{_utc_now_compact()}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(out)

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_render_summary(payload))
        if payload.get("report_path"):
            print(f"\nreport_path={payload['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
