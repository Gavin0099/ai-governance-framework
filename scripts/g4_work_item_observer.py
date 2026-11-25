#!/usr/bin/env python3
"""Read-only G4 Work Item Observer (pilot).

Aggregates verifiable delivery evidence, human intervention records, Codex/Guardian/Sub-agent
token usage from raw rollout JSONL files, and Observer self-cost into a concise 1-page
Markdown report plus a redacted machine-readable evidence index.

STRICTLY READ-ONLY against consumer repos, PRs, receipts, and memory.
Never uploads or copies raw rollout JSONL files. Never fabricates missing numbers.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Callable


def _default_gh_runner(args: list[str]) -> str:
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout


def _file_ref(path: Path) -> str:
    """Redacted file identifier: basename + sha256[:12], never exposing local absolute paths."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return f"{path.name}#sha256:{digest}"


def _classify_role(source: Any) -> str:
    if isinstance(source, str):
        if source in {"exec", "cli", "vscode", "interactive", "app_server"}:
            return "main"
        return "unknown"
    if isinstance(source, dict):
        sub = source.get("subagent")
        if isinstance(sub, dict) and sub.get("other") == "guardian":
            return "guardian"
        if sub == "guardian":
            return "guardian"
        if sub is not None:
            return "subagent"
    return "unknown"


def _empty_bucket() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "uncached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
    }


def _add_usage(target: dict[str, int], usage: dict[str, int]) -> None:
    for key in target:
        target[key] += int(usage.get(key, 0))


def _normalize_usage(raw: dict[str, Any]) -> dict[str, int]:
    inp = int(raw.get("input_tokens") or 0)
    cached = int(raw.get("cached_input_tokens") or 0)
    uncached = max(0, inp - cached)
    out = int(raw.get("output_tokens") or 0)
    reasoning = int(raw.get("reasoning_output_tokens") or 0)
    total = int(raw.get("total_tokens") if raw.get("total_tokens") is not None else (inp + out))
    return {
        "input_tokens": inp,
        "cached_input_tokens": cached,
        "uncached_input_tokens": uncached,
        "output_tokens": out,
        "reasoning_output_tokens": reasoning,
        "total_tokens": total,
    }


def parse_codex_rollout_dirs(
    rollout_dirs: list[Path],
    *,
    include_session_ids: set[str] | None = None,
    exclude_session_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Parse Codex rollout JSONL files, deduplicating cumulative counts and resumed sessions."""
    anomalies: list[str] = []
    files: list[Path] = []
    for root in rollout_dirs:
        p = Path(root)
        if not p.exists():
            anomalies.append(f"missing_rollout_dir:{p.name}")
            continue
        if p.is_file() and p.suffix == ".jsonl":
            files.append(p)
        elif p.is_dir():
            for candidate in sorted(p.rglob("*.jsonl")):
                if candidate.name == "session_index.jsonl":
                    continue
                files.append(candidate)

    if not files:
        anomalies.append("no_rollout_jsonl_files_found")

    # Group parsed file summaries by session_id so cross-file resumed sessions never double-count.
    sessions_by_id: dict[str, dict[str, Any]] = {}
    seen_file_hashes: set[str] = set()

    for path in files:
        ref = _file_ref(path)
        file_hash = ref.split("#sha256:", 1)[1]
        if file_hash in seen_file_hashes:
            continue
        seen_file_hashes.add(file_hash)

        session_id: str | None = None
        role = "unknown"
        models: set[str] = set()
        prev_total = -1
        best_usage: dict[str, int] | None = None
        token_events = 0
        non_monotonic = False
        corrupt_lines = 0

        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                corrupt_lines += 1
                continue
            if not isinstance(obj, dict):
                corrupt_lines += 1
                continue
            kind = obj.get("type")
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue
            if kind == "session_meta" and session_id is None:
                raw_id = payload.get("id")
                if isinstance(raw_id, str) and raw_id.strip():
                    session_id = raw_id.strip()
                role = _classify_role(payload.get("source"))
            elif kind == "turn_context":
                model = payload.get("model")
                if isinstance(model, str) and model.strip():
                    models.add(model.strip())
            elif kind == "event_msg" and payload.get("type") == "token_count":
                info = payload.get("info")
                if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                    usage = _normalize_usage(info["total_token_usage"])
                    token_events += 1
                    if usage["total_tokens"] < prev_total:
                        non_monotonic = True
                    prev_total = usage["total_tokens"]
                    if best_usage is None or usage["total_tokens"] > best_usage["total_tokens"]:
                        best_usage = usage

        if session_id is None:
            if corrupt_lines:
                anomalies.append(f"corrupt_json_line:{ref}:count={corrupt_lines}")
            anomalies.append(f"missing_session_id:{ref}")
            continue
        if include_session_ids is not None and session_id not in include_session_ids:
            continue
        if exclude_session_ids is not None and session_id in exclude_session_ids:
            continue
        if corrupt_lines:
            anomalies.append(f"corrupt_json_line:{ref}:count={corrupt_lines}")
        if non_monotonic:
            anomalies.append(f"non_monotonic_token_count:{session_id}:{ref}")
        if best_usage is None:
            anomalies.append(f"missing_token_count:{session_id}:{ref}")
        if not models:
            anomalies.append(f"missing_model:{session_id}:{ref}")
        if role == "unknown":
            anomalies.append(f"unknown_session_role:{session_id}:{ref}")

        entry = sessions_by_id.get(session_id)
        if entry is None:
            sessions_by_id[session_id] = {
                "session_id": session_id,
                "role": role,
                "models": sorted(models),
                "source_refs": [ref],
                "token_events": token_events,
                "usage": best_usage or _empty_bucket(),
                "has_token_usage": best_usage is not None,
                "resumed_across_files": False,
            }
        else:
            entry["resumed_across_files"] = True
            entry["source_refs"].append(ref)
            entry["models"] = sorted(set(entry["models"]) | models)
            entry["token_events"] += token_events
            if entry["role"] == "unknown" and role != "unknown":
                entry["role"] = role
            if best_usage is not None:
                if not entry["has_token_usage"] or best_usage["total_tokens"] > entry["usage"]["total_tokens"]:
                    entry["usage"] = best_usage
                    entry["has_token_usage"] = True

    by_role: dict[str, dict[str, int]] = {
        "main": _empty_bucket(),
        "guardian": _empty_bucket(),
        "subagent": _empty_bucket(),
        "unknown": _empty_bucket(),
    }
    known_totals = _empty_bucket()
    session_list = sorted(sessions_by_id.values(), key=lambda s: s["session_id"])
    for sess in session_list:
        _add_usage(by_role[sess["role"]], sess["usage"])
        _add_usage(known_totals, sess["usage"])

    complete = bool(session_list) and not anomalies
    return {
        "cost_completeness": "complete" if complete else "incomplete",
        "comparability_token": 1 if complete else 0,
        "kpi_template_fill_allowed": complete,
        "estimated_usd": "UNKNOWN",
        "known_totals": known_totals,
        "verified_complete_totals": dict(known_totals) if complete else None,
        "by_role": by_role,
        "sessions": session_list,
        "anomalies": anomalies,
    }


def collect_delivery_evidence(
    *,
    repo: str | None,
    work_item_id: str | None = None,
    pr_numbers: list[int] | None = None,
    product_verification_status: str | None = None,
    deployed_status: str | None = None,
    gh_runner: Callable[[list[str]], str] = _default_gh_runner,
) -> dict[str, Any]:
    """Read-only GitHub PR/CI verification. Never equates CI PASS to product verification."""
    discovered_prs: list[int] = list(pr_numbers or [])
    notes: list[str] = []

    if repo and not discovered_prs and work_item_id:
        try:
            raw = gh_runner(
                [
                    "pr",
                    "list",
                    "--repo",
                    repo,
                    "--state",
                    "all",
                    "--search",
                    work_item_id,
                    "--json",
                    "number",
                ]
            )
            discovered_prs = sorted({int(item["number"]) for item in json.loads(raw)})
        except Exception as exc:
            notes.append(f"pr_discovery_failed:{type(exc).__name__}")

    pr_records: list[dict[str, Any]] = []
    if repo and discovered_prs:
        for num in discovered_prs:
            try:
                pr_data = json.loads(
                    gh_runner(
                        [
                            "pr",
                            "view",
                            str(num),
                            "--repo",
                            repo,
                            "--json",
                            "number,title,state,headRefOid,mergeCommit,url",
                        ]
                    )
                )
            except Exception as exc:
                notes.append(f"pr_view_failed:#{num}:{type(exc).__name__}")
                continue
            merge_sha = (pr_data.get("mergeCommit") or {}).get("oid")
            post_merge_ci = "NOT_APPLICABLE"
            if pr_data.get("state") == "MERGED" and merge_sha:
                try:
                    runs = json.loads(
                        gh_runner(
                            [
                                "run",
                                "list",
                                "--repo",
                                repo,
                                "--commit",
                                merge_sha,
                                "--json",
                                "databaseId,status,conclusion,name",
                            ]
                        )
                    )
                    if not runs:
                        post_merge_ci = "NOT_TRIGGERED"
                    elif all(r.get("status") == "completed" and r.get("conclusion") == "success" for r in runs):
                        post_merge_ci = "PASS"
                    else:
                        post_merge_ci = "FAIL_OR_PENDING"
                except Exception as exc:
                    post_merge_ci = "UNKNOWN"
                    notes.append(f"ci_check_failed:#{num}:{type(exc).__name__}")
            pr_records.append(
                {
                    "number": pr_data.get("number"),
                    "state": pr_data.get("state"),
                    "head_sha": pr_data.get("headRefOid"),
                    "merge_sha": merge_sha,
                    "post_merge_ci": post_merge_ci,
                    "url": pr_data.get("url"),
                }
            )

    has_lookup_failure = any(n.startswith(("pr_view_failed:", "pr_discovery_failed:")) for n in notes)
    if not pr_records:
        code_completed = "UNKNOWN"
        merged_and_ci = "UNKNOWN"
    else:
        any_open_or_merged = any(r["state"] in {"OPEN", "MERGED"} for r in pr_records)
        code_completed = "YES" if any_open_or_merged else "NO"
        all_merged = all(r["state"] == "MERGED" for r in pr_records)
        all_ci_ok = all(r["post_merge_ci"] in {"PASS", "NOT_TRIGGERED"} for r in pr_records)
        any_ci_pass = any(r["post_merge_ci"] == "PASS" for r in pr_records)
        if has_lookup_failure:
            merged_and_ci = "PARTIAL" if any_ci_pass else "UNKNOWN"
        elif all_merged and all_ci_ok and any_ci_pass:
            merged_and_ci = "YES"
        elif all_merged:
            merged_and_ci = "PARTIAL"
        else:
            merged_and_ci = "NO"

    return {
        "code_completed": code_completed,
        "merged_and_ci": merged_and_ci,
        "product_verified": product_verification_status or "NOT_VERIFIED",
        "deployed_or_enabled": deployed_status or "UNKNOWN",
        "prs": pr_records,
        "notes": notes,
    }


def summarize_human_interventions(
    events_path: Path | None,
    *,
    confirmed_minutes: float | None = None,
) -> dict[str, Any]:
    """Summarize Owner decisions vs unplanned rescues; never default missing records to 0."""
    planned: int | str = "UNKNOWN"
    unplanned: int | str = "UNKNOWN"
    source_ref: str | None = None
    notes: list[str] = []

    if events_path is not None:
        p = Path(events_path)
        if not p.is_file():
            notes.append(f"missing_events_file:{p.name}")
        else:
            source_ref = _file_ref(p)
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                events = data if isinstance(data, list) else data.get("events")
                if isinstance(events, list):
                    planned = sum(1 for e in events if isinstance(e, dict) and e.get("category") == "planned_owner_decision")
                    unplanned = sum(1 for e in events if isinstance(e, dict) and e.get("category") == "unplanned_rescue")
                else:
                    notes.append("invalid_events_structure")
            except Exception as exc:
                notes.append(f"events_parse_error:{type(exc).__name__}")

    return {
        "planned_owner_decisions": planned,
        "unplanned_rescues": unplanned,
        "human_minutes": confirmed_minutes if confirmed_minutes is not None else "UNKNOWN",
        "human_minutes_source": "owner_confirmed" if confirmed_minutes is not None else "unmeasured",
        "wall_clock_excluded": True,
        "source_ref": source_ref,
        "notes": notes,
    }


def render_markdown_report(evidence: dict[str, Any]) -> str:
    delivery = evidence["delivery"]
    human = evidence["human_interventions"]
    tokens = evidence["ai_cost"]
    self_cost = evidence["observer_self_cost"]

    known = tokens["known_totals"]["total_tokens"]
    main_tok = tokens["by_role"]["main"]["total_tokens"]
    guard_tok = tokens["by_role"]["guardian"]["total_tokens"]
    sub_tok = tokens["by_role"]["subagent"]["total_tokens"]
    unk_tok = tokens["by_role"]["unknown"]["total_tokens"]
    comp = tokens["cost_completeness"]

    if known > 0:
        breakdown = f"Main {main_tok:,} / Guardian {guard_tok:,} / Sub-agent {sub_tok:,}"
        if unk_tok > 0:
            breakdown += f" / Unknown {unk_tok:,}"
        token_cell = f"{known:,}（{comp}；{breakdown}；金額 UNKNOWN）"
    else:
        token_cell = f"UNKNOWN（{comp}）"

    obs_cell = f"{self_cost['duration_ms']} ms（純腳本零額外 LLM Tokens；ai_usage_available={self_cost['ai_usage_available']}）"

    lines = [
        f"# G4 Observer — {evidence['title']}（`{evidence['work_item_id']}`）",
        "",
        "| 項目 | 觀察結果 |",
        "| --- | --- |",
        f"| 程式完成（Code Completed） | {delivery['code_completed']} |",
        f"| 合併與 CI（Merged + CI） | {delivery['merged_and_ci']} |",
        f"| 產品驗收（Product Verified） | {delivery['product_verified']} |",
        f"| 正式部署／啟用（Deployed / Enabled） | {delivery['deployed_or_enabled']} |",
        f"| 必要 Owner 決策 | {human['planned_owner_decisions']} |",
        f"| 意外人工救援 | {human['unplanned_rescues']} |",
        f"| 人工實際分鐘數 | {human['human_minutes']}（不使用 Wall-clock 冒充） |",
        f"| 完整 AI Tokens / 成本 | {token_cell} |",
        f"| Observer 自身成本 | {obs_cell} |",
        "",
        "**評估與非宣稱**：本報告僅做唯讀證據彙總，不影響 PR 合併資格、不建立 ROI 分數或跨任務排名；"
        f"`cost_completeness={comp}`、`comparability_token={tokens['comparability_token']}`。詳細 Session 與 PR 證據見 `evidence_index.json`。",
        "",
    ]
    return "\n".join(lines)


def run_observer(
    *,
    work_item_id: str,
    title: str,
    repo: str | None,
    pr_numbers: list[int] | None,
    rollout_dirs: list[Path],
    output_dir: Path,
    exclude_session_ids: set[str] | None = None,
    events_path: Path | None = None,
    confirmed_minutes: float | None = None,
    product_verification_status: str | None = None,
    deployed_status: str | None = None,
    gh_runner: Callable[[list[str]], str] = _default_gh_runner,
) -> tuple[Path, Path]:
    started_perf = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()

    delivery = collect_delivery_evidence(
        repo=repo,
        work_item_id=work_item_id,
        pr_numbers=pr_numbers,
        product_verification_status=product_verification_status,
        deployed_status=deployed_status,
        gh_runner=gh_runner,
    )
    ai_cost = parse_codex_rollout_dirs(rollout_dirs, exclude_session_ids=exclude_session_ids)
    human = summarize_human_interventions(events_path, confirmed_minutes=confirmed_minutes)

    duration_ms = int(round((time.perf_counter() - started_perf) * 1000))
    evidence = {
        "schema_version": "0.1-pilot",
        "observed_at_utc": started_utc,
        "work_item_id": work_item_id,
        "title": title,
        "repo": repo or "UNKNOWN",
        "read_only": True,
        "delivery": delivery,
        "human_interventions": human,
        "ai_cost": ai_cost,
        "observer_self_cost": {
            "duration_ms": duration_ms,
            "ai_usage_available": False,
            "observer_ai_tokens": 0,
            "mode": "deterministic_read_only_script",
        },
        "not_claimed": [
            "ROI proven",
            "cross-task agent ranking",
            "causal governance effectiveness proof",
            "merge gate authority",
        ],
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "report.md"
    index_path = out / "evidence_index.json"
    report_path.write_text(render_markdown_report(evidence), encoding="utf-8")
    index_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report_path, index_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only G4 Work Item Observer (pilot)")
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--repo", default=None, help="GitHub owner/repo slug (optional)")
    parser.add_argument("--pr", dest="prs", type=int, action="append", default=[], help="PR number (repeatable)")
    parser.add_argument("--rollout-dir", dest="rollout_dirs", type=Path, action="append", default=[])
    parser.add_argument("--exclude-session-id", dest="exclude_session_ids", action="append", default=[])
    parser.add_argument("--events-file", type=Path, default=None)
    parser.add_argument("--owner-minutes-confirmed", type=float, default=None)
    parser.add_argument("--product-verified", default=None)
    parser.add_argument("--deployed-status", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    report_path, index_path = run_observer(
        work_item_id=args.work_item_id,
        title=args.title,
        repo=args.repo,
        pr_numbers=args.prs,
        rollout_dirs=args.rollout_dirs,
        output_dir=args.output_dir,
        exclude_session_ids=set(args.exclude_session_ids) or None,
        events_path=args.events_file,
        confirmed_minutes=args.owner_minutes_confirmed,
        product_verification_status=args.product_verified,
        deployed_status=args.deployed_status,
    )
    print(f"report={report_path}")
    print(f"evidence_index={index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
