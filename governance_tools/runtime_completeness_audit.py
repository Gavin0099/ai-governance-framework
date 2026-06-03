#!/usr/bin/env python3
"""
Audit runtime completeness consistency using verdict artifacts as the truth set.

For each verdict session_id under artifacts/runtime/verdicts/:
- canonical closeout must exist at artifacts/runtime/closeouts/<session_id>.json
- claim-binding check must exist at artifacts/claim-enforcement/<session_id>/claim-enforcement-check.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_iso_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _session_sort_key(payload: dict[str, Any], verdict_path: Path) -> tuple[datetime, str]:
    generated_at = str(payload.get("generated_at", "")).strip()
    if generated_at:
        try:
            return _parse_iso_utc(generated_at), str(payload.get("session_id", ""))
        except Exception:
            pass
    return (
        datetime.fromtimestamp(verdict_path.stat().st_mtime, tz=timezone.utc),
        str(payload.get("session_id", "")),
    )


def build_runtime_completeness_audit(
    project_root: Path,
    *,
    since: str | None = None,
    only_new_sessions: bool = False,
    baseline_before: str | None = None,
) -> dict[str, Any]:
    verdicts_dir = project_root / "artifacts" / "runtime" / "verdicts"
    closeouts_dir = project_root / "artifacts" / "runtime" / "closeouts"
    # CE-1D.2: new raw packets write to artifacts/session/claim-enforcement/ (gitignored).
    # Historical packets remain at artifacts/claim-enforcement/ (legacy path).
    # Dual-read: check new path first, fall back to legacy path.
    claim_root_new = project_root / "artifacts" / "session" / "claim-enforcement"
    claim_root_legacy = project_root / "artifacts" / "claim-enforcement"

    verdict_files = sorted(verdicts_dir.glob("*.json")) if verdicts_dir.exists() else []
    loaded_sessions: list[dict[str, Any]] = []
    unreadable_verdicts: list[str] = []

    for vf in verdict_files:
        try:
            payload = json.loads(vf.read_text(encoding="utf-8"))
            session_id = str(payload.get("session_id", "")).strip()
            if not session_id:
                unreadable_verdicts.append(str(vf))
                continue
            loaded_sessions.append({
                "session_id": session_id,
                "verdict_path": vf,
                "sort_key": _session_sort_key(payload, vf),
            })
        except Exception:
            unreadable_verdicts.append(str(vf))

    loaded_sessions.sort(key=lambda item: item["sort_key"])
    scope_sessions = loaded_sessions
    scope_mode = "all_sessions"
    if baseline_before:
        boundary = _parse_iso_utc(baseline_before)
        historical = [x for x in loaded_sessions if x["sort_key"][0] < boundary]
        new_window = [x for x in loaded_sessions if x["sort_key"][0] >= boundary]
        scope_mode = "new_window" if only_new_sessions else "all_with_baseline"
        scope_sessions = new_window if only_new_sessions else loaded_sessions
    else:
        historical = []
        new_window = loaded_sessions

    if since:
        if since.startswith("session:"):
            since_sid = since.split(":", 1)[1].strip()
            scope_sessions = [x for x in scope_sessions if x["session_id"] >= since_sid]
        else:
            since_dt = _parse_iso_utc(since)
            scope_sessions = [x for x in scope_sessions if x["sort_key"][0] >= since_dt]
        scope_mode = "since_filter"

    closeout_missing: list[str] = []
    claim_missing: list[str] = []
    # CE-1D.3: evidence classification — where does the raw packet live?
    # runtime_only: gitignored path only; compact receipt is the repo-facing evidence.
    # legacy_only:  legacy tracked path only (historical sessions).
    # both_paths:   present at both (unusual; indicates a migration overlap).
    claim_runtime_only: list[str] = []
    claim_legacy_only: list[str] = []
    claim_both_paths: list[str] = []
    historical_closeout_missing: list[str] = []
    historical_claim_missing: list[str] = []
    new_window_closeout_missing: list[str] = []
    new_window_claim_missing: list[str] = []

    for item in scope_sessions:
        session_id = item["session_id"]
        closeout_path = closeouts_dir / f"{session_id}.json"
        # CE-1D.3: classify by evidence location rather than binary found/not-found.
        runtime_found = (claim_root_new / session_id / "claim-enforcement-check.json").exists()
        legacy_found = (claim_root_legacy / session_id / "claim-enforcement-check.json").exists()

        if not closeout_path.exists():
            closeout_missing.append(session_id)
        if not (runtime_found or legacy_found):
            claim_missing.append(session_id)
        elif runtime_found and not legacy_found:
            claim_runtime_only.append(session_id)
        elif legacy_found and not runtime_found:
            claim_legacy_only.append(session_id)
        else:
            claim_both_paths.append(session_id)

    if baseline_before:
        for item in historical:
            session_id = item["session_id"]
            if not (closeouts_dir / f"{session_id}.json").exists():
                historical_closeout_missing.append(session_id)
            if not (
                (claim_root_new / session_id / "claim-enforcement-check.json").exists()
                or (claim_root_legacy / session_id / "claim-enforcement-check.json").exists()
            ):
                historical_claim_missing.append(session_id)
        for item in new_window:
            session_id = item["session_id"]
            if not (closeouts_dir / f"{session_id}.json").exists():
                new_window_closeout_missing.append(session_id)
            if not (
                (claim_root_new / session_id / "claim-enforcement-check.json").exists()
                or (claim_root_legacy / session_id / "claim-enforcement-check.json").exists()
            ):
                new_window_claim_missing.append(session_id)

    silent_drop_sessions = sorted(set(closeout_missing) | set(claim_missing))
    historical_silent_drop_sessions = sorted(set(historical_closeout_missing) | set(historical_claim_missing))
    new_window_silent_drop_sessions = sorted(set(new_window_closeout_missing) | set(new_window_claim_missing))

    return {
        "ok": True,
        "project_root": str(project_root),
        "scope_mode": scope_mode,
        "since": since,
        "only_new_sessions": only_new_sessions,
        "baseline_before": baseline_before,
        "verdict_session_count": len(scope_sessions),
        "verdict_session_count_total": len(loaded_sessions),
        "closeout_missing_for_invoked_session": closeout_missing,
        "claim_binding_missing_for_invoked_session": claim_missing,
        # CE-1D.3: evidence classification breakdown
        # runtime_only: raw packet at gitignored path; compact receipt is repo-facing evidence.
        # legacy_only:  raw packet at legacy tracked path (historical data).
        # both_paths:   raw packet at both paths (migration overlap; rare).
        "claim_binding_runtime_only": claim_runtime_only,
        "claim_binding_legacy_only": claim_legacy_only,
        "claim_binding_both_paths": claim_both_paths,
        "unreadable_verdicts": unreadable_verdicts,
        "silent_drop_count": len(silent_drop_sessions),
        "silent_drop_sessions": silent_drop_sessions,
        "historical_silent_drop_count": len(historical_silent_drop_sessions),
        "historical_silent_drop_sessions": historical_silent_drop_sessions,
        "new_window_silent_drop_count": len(new_window_silent_drop_sessions),
        "new_window_silent_drop_sessions": new_window_silent_drop_sessions,
        "new_window_integrity_ok": len(new_window_silent_drop_sessions) == 0,
        "integrity_ok": len(silent_drop_sessions) == 0 and len(unreadable_verdicts) == 0,
    }


def format_human_result(result: dict[str, Any]) -> str:
    lines = [
        "[runtime_completeness_audit]",
        f"ok={result.get('ok')}",
        f"integrity_ok={result.get('integrity_ok')}",
        f"new_window_integrity_ok={result.get('new_window_integrity_ok')}",
        f"verdict_session_count={result.get('verdict_session_count')}",
        f"verdict_session_count_total={result.get('verdict_session_count_total')}",
        f"silent_drop_count={result.get('silent_drop_count')}",
        f"historical_silent_drop_count={result.get('historical_silent_drop_count')}",
        f"new_window_silent_drop_count={result.get('new_window_silent_drop_count')}",
    ]
    # CE-1D.3: evidence classification summary
    lines.append(
        f"claim_binding_runtime_only_count={len(result.get('claim_binding_runtime_only', []))}"
        "  # gitignored path; compact receipt is repo-facing evidence"
    )
    lines.append(
        f"claim_binding_legacy_only_count={len(result.get('claim_binding_legacy_only', []))}"
        "  # legacy tracked path (historical data)"
    )
    lines.append(
        f"claim_binding_both_paths_count={len(result.get('claim_binding_both_paths', []))}"
        "  # both paths (migration overlap)"
    )
    for sid in result.get("closeout_missing_for_invoked_session", []):
        lines.append(f"closeout_missing_session={sid}")
    for sid in result.get("claim_binding_missing_for_invoked_session", []):
        lines.append(f"claim_binding_missing_session={sid}")
    for path in result.get("unreadable_verdicts", []):
        lines.append(f"unreadable_verdict={path}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit runtime completeness consistency.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--since", help="ISO timestamp or 'session:<session_id>' lower bound.")
    parser.add_argument("--only-new-sessions", action="store_true", help="With --baseline-before, evaluate only sessions on/after baseline.")
    parser.add_argument("--baseline-before", help="ISO timestamp boundary to split historical vs new-window sessions.")
    args = parser.parse_args()

    result = build_runtime_completeness_audit(
        Path(args.project_root).resolve(),
        since=args.since,
        only_new_sessions=args.only_new_sessions,
        baseline_before=args.baseline_before,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human_result(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
