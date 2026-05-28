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
import re
import subprocess
import sys
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


def _repo_present_in_snapshot(snapshot: dict[str, Any], repo_path: Path) -> bool:
    rows = snapshot.get("operational_maturity", {}).get("remediation_suggestions", [])
    for row in rows:
        repo = row.get("repo", "")
        if isinstance(repo, str) and _repo_matches(repo, repo_path):
            return True
    return False


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


def _signal(status: str, *, reason: str = "", remediation: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "repo_failure": status == "N",
        "detector_failure": status == "DETECTOR_ERROR",
        "remediation": remediation,
    }


def _signal_hooks(repo_path: Path) -> tuple[bool, dict[str, Any]]:
    tool_path = (Path(__file__).resolve().parent / "manage_agent_closeout.py").as_posix()
    cmd = f'python "{tool_path}" --project-root "{repo_path}" verify --agent all'
    code, stdout, stderr = _run_powershell_command(cmd, repo_path)
    if code == 0:
        return True, _signal("Y", reason="hooks_verified")
    text = f"{stdout}\n{stderr}".lower()
    if "permission denied" in text or "access is denied" in text:
        return False, _signal(
            "DETECTOR_ERROR",
            reason="hooks_verify_permission_denied",
            remediation='re-run with permissions to read/write hook config paths, then verify again',
        )
    return False, _signal("N", reason="hooks_not_ready")


def _signal_fw(repo_path: Path) -> tuple[bool, dict[str, Any]]:
    exists = (repo_path / "governance" / "framework.lock.json").exists()
    if exists:
        return True, _signal("Y", reason="framework_lock_present")
    return False, _signal(
        "N",
        reason="framework_lock_missing",
        remediation="update governance/framework.lock.json through existing adoption/update path",
    )


def _signal_agents(repo_path: Path) -> tuple[bool, dict[str, Any]]:
    exists = (repo_path / "AGENTS.md").exists()
    if exists:
        return True, _signal("Y", reason="agents_present")
    return False, _signal("N", reason="agents_missing", remediation="add repo-specific AGENTS.md")


def _load_latest_closeout_receipt(repo_path: Path) -> dict[str, Any] | None:
    receipts_dir = repo_path / "artifacts" / "runtime" / "closeout-receipts"
    if not receipts_dir.is_dir():
        return None
    files = sorted(receipts_dir.glob("closeout_receipt_*.json"))
    if not files:
        return None
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return _load_json(latest)


def _signal_evidence_head_ts(repo_path: Path, window_days: int) -> tuple[bool, bool, bool, dict[str, dict[str, Any]]]:
    receipt = _load_latest_closeout_receipt(repo_path)
    details: dict[str, dict[str, Any]] = {}
    if not receipt:
        details["evidence"] = _signal("N", reason="closeout_receipt_missing", remediation="run session_closeout_entry")
        details["head_ok"] = _signal("UNKNOWN", reason="receipt_missing")
        details["ts_ok"] = _signal("UNKNOWN", reason="receipt_missing")
        return False, False, False, details

    evidence_ok = True
    details["evidence"] = _signal("Y", reason="closeout_receipt_present")
    linked_head = str(receipt.get("linked_head_commit", "")).strip()
    if not linked_head:
        details["evidence"] = _signal("N", reason="linked_head_missing", remediation="re-run session_closeout_entry")
        details["head_ok"] = _signal("UNKNOWN", reason="linked_head_missing")
        details["ts_ok"] = _signal("UNKNOWN", reason="linked_head_missing")
        return False, False, False, details

    safe_repo = str(repo_path).replace("'", "''")
    code, stdout, stderr = _run_powershell_command(f"git -c safe.directory='{safe_repo}' rev-parse HEAD", repo_path)
    if code != 0:
        err_text = f"{stdout}\n{stderr}".lower()
        if "dubious ownership" in err_text or "safe.directory" in err_text:
            details["head_ok"] = _signal(
                "DETECTOR_ERROR",
                reason="git_dubious_ownership",
                remediation="run git with -c safe.directory=<repo> or configure safe.directory",
            )
        else:
            reason = re.sub(r"\s+", " ", err_text).strip()[:180] or "git_rev_parse_failed"
            details["head_ok"] = _signal("DETECTOR_ERROR", reason=reason, remediation="fix git HEAD detector access")
        details["ts_ok"] = _signal("UNKNOWN", reason="head_detector_error")
        return evidence_ok, False, False, details
    current_head = stdout.strip()
    head_ok = current_head == linked_head
    if head_ok:
        details["head_ok"] = _signal("Y", reason="head_matches_receipt")
    else:
        details["head_ok"] = _signal("N", reason="head_mismatch", remediation="re-run session_closeout_entry at current HEAD")

    ts_text = str(receipt.get("timestamp", "")).strip()
    if not ts_text:
        details["ts_ok"] = _signal("N", reason="timestamp_missing", remediation="re-run session_closeout_entry")
        return evidence_ok, head_ok, False, details

    try:
        dt = datetime.fromisoformat(ts_text.replace("Z", "+00:00"))
    except ValueError:
        details["ts_ok"] = _signal("DETECTOR_ERROR", reason="timestamp_parse_error", remediation="fix receipt timestamp format")
        return evidence_ok, head_ok, False, details
    age_days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400.0
    ts_ok = age_days <= float(window_days)
    if ts_ok:
        details["ts_ok"] = _signal("Y", reason="timestamp_in_window")
    else:
        details["ts_ok"] = _signal("N", reason="timestamp_stale", remediation="refresh closeout receipt")
    return evidence_ok, head_ok, ts_ok, details


def _compute_acceptance(repo_path: Path, window_days: int) -> dict[str, Any]:
    hooks, hooks_detail = _signal_hooks(repo_path)
    fw, fw_detail = _signal_fw(repo_path)
    agents, agents_detail = _signal_agents(repo_path)
    evidence, head_ok, ts_ok, eht_details = _signal_evidence_head_ts(repo_path, window_days)
    verified = hooks and fw and agents and evidence and head_ok and ts_ok
    details = {
        "hooks": hooks_detail,
        "fw": fw_detail,
        "agents": agents_detail,
        "evidence": eht_details.get("evidence", _signal("UNKNOWN", reason="not_evaluated")),
        "head_ok": eht_details.get("head_ok", _signal("UNKNOWN", reason="not_evaluated")),
        "ts_ok": eht_details.get("ts_ok", _signal("UNKNOWN", reason="not_evaluated")),
    }
    detector_errors = sum(1 for x in details.values() if x.get("status") == "DETECTOR_ERROR")
    return {
        "hooks": hooks,
        "fw": fw,
        "agents": agents,
        "evidence": evidence,
        "head_ok": head_ok,
        "ts_ok": ts_ok,
        "signal_details": details,
        "detector_errors": detector_errors,
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
    lines.append(f"detector_errors={payload['acceptance_after'].get('detector_errors', 0)}")
    lines.append("")
    lines.append("[signal_details]")
    for key in ("hooks", "fw", "agents", "evidence", "head_ok", "ts_ok"):
        d = payload["acceptance_after"].get("signal_details", {}).get(key, {})
        lines.append(
            f"{key}: status={d.get('status', 'UNKNOWN')} reason={d.get('reason', '')} "
            f"repo_failure={d.get('repo_failure', False)} detector_failure={d.get('detector_failure', False)}"
        )
        remediation = d.get("remediation", "")
        if remediation:
            lines.append(f"  remediation: {remediation}")
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
    parser.add_argument(
        "--require-in-snapshot",
        action="store_true",
        default=True,
        help="Fail fast when target repo is not present in remediation_suggestions (default: true).",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    repo_path = Path(args.repo).resolve()
    snapshot_path = Path(args.snapshot).resolve() if args.snapshot else _find_latest_snapshot(project_root)
    snapshot = _load_json(snapshot_path)
    if args.require_in_snapshot and not _repo_present_in_snapshot(snapshot, repo_path):
        err = {
            "ok": False,
            "error": "repo_not_in_snapshot",
            "repo": str(repo_path),
            "snapshot": str(snapshot_path),
            "message": "Target repo not found in remediation_suggestions.",
            "next_steps": [
                "Add repo to fleet scope/inventory used by matrix generator.",
                "Regenerate matrix snapshot.",
                "Re-run onboarding with --snapshot <new_snapshot.json>.",
            ],
        }
        if args.format == "json":
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print("[onboard_latest_governance]")
            print("ok=False")
            print("error=repo_not_in_snapshot")
            print(f"repo={repo_path}")
            print(f"snapshot={snapshot_path}")
            print("message=Target repo not found in remediation_suggestions.")
            print("next_steps=add_repo_to_matrix_inventory -> regenerate_snapshot -> rerun_onboarding")
        return 2
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
