#!/usr/bin/env python3
"""Read-only freshness probe for required repos.

This tool reports how many days remain before required repos fall outside the
current evidence freshness window. It does not mutate repo state and does not
run closeout.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass
class RepoFreshness:
    repo_name: str
    repo_path: str
    classification: str
    has_evidence: bool
    evidence_timestamp: str
    age_days: float | None
    remaining_days: float | None
    status: str


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    text = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_required_repo_names(scope_path: Path) -> set[str]:
    if not scope_path.exists():
        return set()
    if yaml is not None:
        obj = yaml.safe_load(scope_path.read_text(encoding="utf-8")) or {}
        repos = (
            obj.get("tiers", {})
            .get("required", {})
            .get("repos", [])
        )
        names: set[str] = set()
        for item in repos:
            path = str((item or {}).get("path", "")).strip()
            if path:
                names.add(Path(path).name)
        return names

    names = set()
    in_required = False
    in_required_repos = False
    for raw in scope_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("required:"):
            in_required = True
            in_required_repos = False
            continue
        if in_required and line.endswith(":") and not line.startswith("repos:"):
            if not line.startswith("meaning:"):
                in_required = False
                in_required_repos = False
        if in_required and line.startswith("repos:"):
            in_required_repos = True
            continue
        if in_required and in_required_repos and line.startswith("- path:"):
            p = line.split(":", 1)[1].strip()
            if p:
                names.add(Path(p).name)
    return names


def _load_latest_snapshot(snapshot: Path | None, root: Path) -> dict[str, Any]:
    if snapshot is not None:
        return json.loads(snapshot.read_text(encoding="utf-8-sig"))
    session_dir = root / "artifacts" / "session"
    files = sorted(
        session_dir.glob("governance_repo_matrix_snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError("No matrix snapshot json found under artifacts/session")
    return json.loads(files[0].read_text(encoding="utf-8-sig"))


def _status_for_remaining(remaining_days: float | None) -> str:
    if remaining_days is None:
        return "no_evidence"
    if remaining_days < 0:
        return "expired"
    if remaining_days <= 1:
        return "critical"
    if remaining_days <= 2:
        return "warning"
    return "ok"


def run(project_root: Path, snapshot_path: Path | None) -> dict[str, Any]:
    snapshot = _load_latest_snapshot(snapshot_path, project_root)
    details = (
        snapshot.get("operational_maturity", {})
        .get("repo_native_governance_breakdown", {})
        .get("overall", {})
        .get("details", [])
    )
    window_days = int(snapshot.get("evidence_window_days", 7))
    now = datetime.now(timezone.utc)

    required_names = _load_required_repo_names(
        project_root / "governance" / "fleet" / "governance_scope.yaml"
    )

    rows: list[RepoFreshness] = []
    for d in details:
        repo_path = str(d.get("repo", "")).strip()
        repo_name = Path(repo_path).name if repo_path else ""
        if repo_name not in required_names:
            continue
        ev = d.get("repo_native_hook_evidence") or {}
        ts_text = str(ev.get("timestamp", "")).strip()
        ts = _parse_iso(ts_text)
        age_days = None
        rem_days = None
        if ts is not None:
            age = now - ts
            age_days = age.total_seconds() / 86400.0
            rem_days = window_days - age_days
        rows.append(
            RepoFreshness(
                repo_name=repo_name,
                repo_path=repo_path,
                classification=str(d.get("classification", "")),
                has_evidence=bool(d.get("repo_native_hook_evidence_exists", False)),
                evidence_timestamp=ts_text,
                age_days=age_days,
                remaining_days=rem_days,
                status=_status_for_remaining(rem_days),
            )
        )

    rows.sort(key=lambda r: (9999 if r.remaining_days is None else r.remaining_days))
    summary = {
        "required_total": len(rows),
        "window_days": window_days,
        "status_counts": {
            s: sum(1 for r in rows if r.status == s)
            for s in ["ok", "warning", "critical", "expired", "no_evidence"]
        },
        "probe_generated_at": now.isoformat(),
    }

    return {
        "summary": summary,
        "repos": [
            {
                "repo_name": r.repo_name,
                "repo_path": r.repo_path,
                "classification": r.classification,
                "has_evidence": r.has_evidence,
                "evidence_timestamp": r.evidence_timestamp,
                "age_days": None if r.age_days is None else round(r.age_days, 3),
                "remaining_days": None if r.remaining_days is None else round(r.remaining_days, 3),
                "status": r.status,
            }
            for r in rows
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only freshness probe for required repos (no auto-closeout)."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--snapshot", help="Optional matrix snapshot JSON path.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    snapshot = Path(args.snapshot).resolve() if args.snapshot else None
    result = run(root, snapshot)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    s = result["summary"]
    print("[required_freshness_probe]")
    print(f"required_total={s['required_total']}")
    print(f"window_days={s['window_days']}")
    print(
        "status_counts="
        f"ok:{s['status_counts']['ok']},"
        f"warning:{s['status_counts']['warning']},"
        f"critical:{s['status_counts']['critical']},"
        f"expired:{s['status_counts']['expired']},"
        f"no_evidence:{s['status_counts']['no_evidence']}"
    )
    for r in result["repos"]:
        rem = "n/a" if r["remaining_days"] is None else f"{r['remaining_days']:.3f}"
        print(
            f"- {r['repo_name']}: status={r['status']} "
            f"class={r['classification']} remaining_days={rem}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
