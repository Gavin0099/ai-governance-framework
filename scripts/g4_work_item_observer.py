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
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable, Iterator


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
    return _content_ref(path, path.read_bytes())


def _content_ref(path: Path, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()[:12]
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
    expected_session_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Parse Codex rollout JSONL files, separating parsed-file validity from whole-work-item completeness."""
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

    parsed_files_valid = bool(session_list) and not anomalies
    missing_expected: list[str] = []
    if expected_session_ids is not None:
        observed_ids = {s["session_id"] for s in session_list}
        missing_expected = sorted(expected_session_ids - observed_ids)
        for sid in missing_expected:
            anomalies.append(f"missing_expected_session:{sid}")

    # Whole work-item cost is only "complete" when all parsed files are valid AND an explicit
    # expected session inventory was supplied and fully accounted for (preventing silent omission
    # of Guardian or other sub-agent sessions that were never present in the scanned directory).
    work_item_cost_complete = (
        parsed_files_valid
        and expected_session_ids is not None
        and len(expected_session_ids) > 0
        and not missing_expected
    )
    return {
        "parsed_files_valid": parsed_files_valid,
        "work_item_cost_complete": work_item_cost_complete,
        "cost_completeness": "complete" if work_item_cost_complete else "incomplete",
        "comparability_token": 1 if work_item_cost_complete else 0,
        "kpi_template_fill_allowed": work_item_cost_complete,
        "estimated_usd": "UNKNOWN",
        "known_totals": known_totals,
        "verified_complete_totals": dict(known_totals) if work_item_cost_complete else None,
        "by_role": by_role,
        "sessions": session_list,
        "missing_expected_sessions": missing_expected,
        "anomalies": anomalies,
    }


_CLAUDE_TOKEN_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)
_GEMINI_TOKEN_FIELDS = ("input", "cached", "output", "thoughts", "tool")


def _provider_sources(
    paths: list[Path],
    suffixes: set[str],
    source_refs: set[str],
    anomalies: set[str],
    *,
    recursive: bool = False,
) -> Iterator[tuple[Path, str]]:
    seen: set[Path] = set()
    for root in map(Path, paths):
        try:
            if recursive and root.is_dir():
                candidates = sorted(
                    p for p in root.rglob("*") if p.suffix.lower() in suffixes and p.is_file()
                )
            else:
                candidates = [root] if root.suffix.lower() in suffixes and root.is_file() else []
        except OSError:
            candidates = []
        if not candidates:
            anomalies.add(f"no_provider_source:{root.name}")
        for path in candidates:
            try:
                resolved = path.resolve()
                if resolved in seen:
                    continue
                raw = path.read_bytes()
                content = raw.decode("utf-8-sig")
            except (OSError, UnicodeError, RuntimeError):
                anomalies.add(f"unreadable_provider_source:{path.name}")
                continue
            seen.add(resolved)
            source_refs.add(_content_ref(path, raw))
            yield path, content


def _transcript_records(content: str, suffix: str, anomalies: set[str]) -> tuple[str | None, list[dict]]:
    if suffix == ".json":
        try:
            document = json.loads(content)
        except ValueError:
            anomalies.add("invalid_transcript_json")
            return None, []
        if not isinstance(document, dict) or not isinstance(document.get("messages"), list):
            anomalies.add("invalid_transcript_messages")
            return None, []
        records = document["messages"]
        session_id = _transcript_session_id(document)
    else:
        records = []
        session_id = None
        for line in content.splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                anomalies.add("invalid_transcript_jsonl_line")
    objects = [record for record in records if isinstance(record, dict)]
    if len(objects) != len(records):
        anomalies.add("invalid_transcript_record")
    return session_id, objects


def _identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _transcript_session_id(record: dict) -> str | None:
    return _identifier(record.get("sessionId")) or _identifier(record.get("session_id"))


def _provider_session_rows(
    paths: list[Path],
    suffixes: set[str],
    record_type: str,
    expected: set[str],
    source_refs: set[str],
    anomalies: set[str],
) -> Iterator[tuple[str | Path, dict]]:
    for path, content in _provider_sources(paths, suffixes, source_refs, anomalies, recursive=True):
        session_id, records = _transcript_records(content, path.suffix.lower(), anomalies)
        explicit_ids = {sid for record in records if (sid := _transcript_session_id(record))}
        if session_id is None and len(explicit_ids) == 1:
            session_id = next(iter(explicit_ids))
        for record in records:
            if record.get("type") != record_type:
                continue
            row_session = _transcript_session_id(record) or session_id
            if row_session is None and explicit_ids:
                anomalies.add("ambiguous_transcript_session")
                continue
            if not expected or (row_session or path.stem) in expected:
                # A file stem can match an inventory without conflating separate anonymous files.
                yield row_session or path, record


def _token_count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _nullable_sum(values: Iterator[int | None]) -> int | None:
    total = 0
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _provider_presence(
    has_evidence: bool, confirmed_unused: bool, evidence_state: str, anomalies: set[str]
) -> str:
    if has_evidence:
        if confirmed_unused:
            anomalies.add("provider_evidence_conflicts_with_confirmed_unused")
        return evidence_state
    return "confirmed_unused" if confirmed_unused else "unknown"


def _token_provider_summary(
    turns: dict[tuple[str | Path, str | int], dict[str, int | None]],
    fields: tuple[str, ...],
    expected: set[str],
    confirmed_unused: bool,
    source_refs: set[str],
    anomalies: set[str],
) -> dict[str, Any]:
    state = _provider_presence(bool(turns), confirmed_unused, "measured", anomalies)
    measured_ids = {session.stem if isinstance(session, Path) else session for session, _ in turns}
    missing = sorted(expected - measured_ids)
    totals = (
        {field: _nullable_sum(turn[field] for turn in turns.values()) for field in fields}
        if turns else None
    )
    if state == "confirmed_unused" and missing:
        anomalies.add("expected_sessions_conflict_with_confirmed_unused")
    complete = (
        bool(expected)
        and not missing
        and not anomalies
        and totals is not None
        and all(count is not None for count in totals.values())
    )
    return {
        "presence_state": state,
        "unit": "tokens",
        "completeness_scope": "provider_sessions_only",
        "cost_completeness": "complete" if complete else "incomplete",
        "known_totals": totals,
        "missing_expected_sessions": missing,
        "source_refs": sorted(source_refs),
        "anomalies": sorted(anomalies),
    }


def parse_claude_transcripts(
    paths: list[Path],
    *,
    expected_session_ids: set[str] | None = None,
    confirmed_unused: bool = False,
) -> dict[str, Any]:
    expected = expected_session_ids or set()
    refs: set[str] = set()
    anomalies: set[str] = set()
    latest: dict[tuple[str | Path, str | int], dict[str, int | None]] = {}
    maxima: dict[tuple[str | Path, str | int], dict[str, int | None]] = {}
    decreasing: set[tuple[str | Path, str | int]] = set()
    for session, record in _provider_session_rows(paths, {".jsonl"}, "assistant", expected, refs, anomalies):
        message = record.get("message")
        if not isinstance(message, dict):
            anomalies.add("claude_invalid_message")
            continue
        message_id = _identifier(message.get("id"))
        if message_id is None:
            anomalies.add("claude_missing_message_id")
            continue
        raw = message.get("usage")
        if not isinstance(raw, dict):
            if raw is not None:
                anomalies.add("claude_invalid_usage")
            continue
        usage = {field: _token_count(raw.get(field)) for field in _CLAUDE_TOKEN_FIELDS}
        if any(raw.get(field) is not None and count is None for field, count in usage.items()):
            anomalies.add("claude_invalid_token_count")
        if not any(count is not None for count in usage.values()):
            continue
        key = (session, message_id)
        peak = maxima.setdefault(key, usage.copy())
        for field, count in usage.items():
            if count is None:
                continue
            previous = peak[field]
            if previous is not None and count < previous:
                decreasing.add(key)
            else:
                peak[field] = count
        latest[key] = usage
    if decreasing:
        anomalies.add("claude_non_monotonic_usage_update")
        for key in decreasing:
            latest[key] = maxima[key]
    return _token_provider_summary(latest, _CLAUDE_TOKEN_FIELDS, expected, confirmed_unused, refs, anomalies)


def parse_gemini_transcripts(
    paths: list[Path],
    *,
    expected_session_ids: set[str] | None = None,
    confirmed_unused: bool = False,
) -> dict[str, Any]:
    expected = expected_session_ids or set()
    refs: set[str] = set()
    anomalies: set[str] = set()
    pending: dict[tuple[str | Path, str | int], dict[str, int | None]] = {}
    for index, (session, record) in enumerate(
        _provider_session_rows(paths, {".json", ".jsonl"}, "gemini", expected, refs, anomalies)
    ):
        raw = record.get("tokens")
        if not isinstance(raw, dict):
            if raw is not None:
                anomalies.add("gemini_invalid_tokens")
            continue
        usage = {field: _token_count(raw.get(field)) for field in _GEMINI_TOKEN_FIELDS}
        if any(raw.get(field) is not None and count is None for field, count in usage.items()):
            anomalies.add("gemini_invalid_token_count")
            continue
        message_id = _identifier(record.get("id"))
        if not any(count is not None for count in usage.values()):
            continue
        if message_id is None:
            anomalies.add("gemini_missing_message_id")
        turn = pending.setdefault((session, message_id or index), {})
        turn.update({field: count for field, count in usage.items() if count is not None})

    fields = tuple(f"{field}_tokens" for field in _GEMINI_TOKEN_FIELDS) + ("uncached_input_tokens",)
    turns = {}
    for key, usage in pending.items():
        inp, cached = usage.get("input"), usage.get("cached")
        uncached = None
        if inp is not None and cached is not None:
            if cached > inp:
                anomalies.add("gemini_cached_tokens_exceed_input")
            else:
                uncached = inp - cached
        turns[key] = {f"{field}_tokens": usage.get(field) for field in _GEMINI_TOKEN_FIELDS}
        turns[key]["uncached_input_tokens"] = uncached
    return _token_provider_summary(turns, fields, expected, confirmed_unused, refs, anomalies)


_COPILOT_IGNORED_COLUMNS = {"aic_gross_amount", "gross_amount", "cost", "amount_usd"}


def _billing_date(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError("invalid billing date")


def _copilot_billing_rows(
    content: str, ignored_columns: set[str], anomalies: set[str]
) -> Iterator[tuple[tuple[str, str, str], float]]:
    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    try:
        headers = {header.strip().lower(): index for index, header in enumerate(next(reader, []))}
        ignored_columns.update(_COPILOT_IGNORED_COLUMNS & headers.keys())
        date_col = next((headers[h] for h in ("date", "report_date", "day") if h in headers), None)
        login_col = next((headers[h] for h in ("user_login", "login", "username", "user") if h in headers), None)
        model_col = next((headers[h] for h in ("model", "model_name") if h in headers), None)
        aic_col = next((headers[h] for h in ("aic_quantity", "ai_credits", "credits") if h in headers), None)
        if date_col is None or model_col is None or aic_col is None:
            anomalies.add("copilot_missing_required_columns")
            return
        for row in reader:
            if not row:
                continue
            try:
                day = _billing_date(row[date_col].strip())
                login = row[login_col].strip() if login_col is not None else ""
                model = row[model_col].strip()
                quantity = float(row[aic_col])
                if not model or (login_col is not None and not login) or not math.isfinite(quantity) or quantity < 0:
                    raise ValueError("invalid billing row")
            except (IndexError, ValueError):
                anomalies.add("copilot_invalid_billing_row")
                continue
            yield (day, login, model), quantity
    except csv.Error:
        anomalies.add("copilot_invalid_csv")


def parse_copilot_billing(paths: list[Path], *, confirmed_unused: bool = False) -> dict[str, Any]:
    refs: set[str] = set()
    anomalies: set[str] = set()
    ignored_columns: set[str] = set()
    rows: dict[tuple[str, str | tuple[Path, int], str], float] = {}
    conflicts: set[tuple[str, str | tuple[Path, int], str]] = set()
    for path, content in _provider_sources(paths, {".csv"}, refs, anomalies):
        billing_rows = _copilot_billing_rows(content, ignored_columns, anomalies)
        for index, ((day, login, model), quantity) in enumerate(billing_rows):
            # Without a login there is no daily-user key to match across exports.
            key = (day, login or (path, index), model)
            if rows.setdefault(key, quantity) != quantity:
                conflicts.add(key)
    if conflicts:
        anomalies.add("copilot_conflicting_daily_quantity")
    by_model: dict[str, float] = {}
    for key, quantity in rows.items():
        if key not in conflicts:
            model = key[2]
            by_model[model] = by_model.get(model, 0.0) + quantity
    if any(not math.isfinite(total) for total in by_model.values()):
        anomalies.add("copilot_billing_sum_out_of_range")
        by_model = {model: total for model, total in by_model.items() if math.isfinite(total)}
    days = [key[0] for key in rows]
    return {
        "presence_state": _provider_presence(bool(rows), confirmed_unused, "billing_reference_only", anomalies),
        "unit": "aic_quantity",
        "completeness_scope": "billing_window_only",
        "cost_completeness": "not_applicable",
        "completions_excluded": True,
        "work_item_attributable": False,
        "billing_window": {"start_date": min(days, default=None), "end_date": max(days, default=None)},
        "by_model_aic": dict(sorted(by_model.items())),
        "ignored_columns": sorted(ignored_columns),
        "source_refs": sorted(refs),
        "anomalies": sorted(anomalies),
    }


def _verify_evidence_file(path: Path | None) -> tuple[bool, str | None]:
    if path is None:
        return False, None
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return False, None
    return True, _file_ref(p)


def collect_delivery_evidence(
    *,
    repo: str | None,
    work_item_id: str | None = None,
    pr_numbers: list[int] | None = None,
    code_evidence_file: Path | None = None,
    product_evidence_file: Path | None = None,
    product_verification_status: str | None = None,
    deployed_status: str | None = None,
    gh_runner: Callable[[list[str]], str] = _default_gh_runner,
) -> dict[str, Any]:
    """Read-only GitHub PR/CI verification. Requires verifiable evidence for completion claims."""
    discovered_prs: list[int] = list(pr_numbers or [])
    notes: list[str] = []
    code_ev_ok, code_ev_ref = _verify_evidence_file(code_evidence_file)
    prod_ev_ok, prod_ev_ref = _verify_evidence_file(product_evidence_file)
    if code_evidence_file is not None and not code_ev_ok:
        notes.append(f"invalid_code_evidence_file:{Path(code_evidence_file).name}")
    if product_evidence_file is not None and not prod_ev_ok:
        notes.append(f"invalid_product_evidence_file:{Path(product_evidence_file).name}")

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
        code_completed = "NOT_VERIFIED"
        merged_and_ci = "UNKNOWN"
    else:
        all_merged = all(r["state"] == "MERGED" for r in pr_records)
        all_closed_unmerged = all(r["state"] == "CLOSED" for r in pr_records)
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

        # An OPEN PR alone never proves code completion; require either merged+CI PASS or a verifiable test evidence file.
        if all_closed_unmerged:
            code_completed = "NO"
        elif (merged_and_ci == "YES") or code_ev_ok:
            code_completed = "YES"
        else:
            code_completed = "NOT_VERIFIED"

    # Never accept an unbacked status string as product verification.
    if prod_ev_ok:
        product_verified = product_verification_status or "VERIFIED_WITH_EVIDENCE"
    else:
        product_verified = "NOT_VERIFIED"

    return {
        "code_completed": code_completed,
        "merged_and_ci": merged_and_ci,
        "product_verified": product_verified,
        "deployed_or_enabled": deployed_status or "UNKNOWN",
        "code_evidence_ref": code_ev_ref,
        "product_evidence_ref": prod_ev_ref,
        "prs": pr_records,
        "notes": notes,
    }


def summarize_human_interventions(
    events_path: Path | None,
    *,
    confirmed_minutes: float | None = None,
    rescue_evidence_refs: list[str] | None = None,
    rescue_confirmed_none: bool = False,
) -> dict[str, Any]:
    """Summarize Owner decisions vs unplanned rescues; never default missing records to 0."""
    planned: int | str = "UNKNOWN"
    unplanned: int | str = "UNKNOWN"
    source_ref: str | None = None
    notes: list[str] = []
    rescue_refs: set[str] = set()
    for ref in rescue_evidence_refs or []:
        ref = ref.strip()
        if not ref:
            continue
        if re.fullmatch(r"[A-Za-z0-9_.#:-]{1,120}", ref):
            rescue_refs.add(ref)
        else:
            digest = hashlib.sha256(ref.encode("utf-8")).hexdigest()[:12]
            rescue_refs.add(f"rescue-ref#sha256:{digest}")

    if events_path is not None:
        p = Path(events_path)
        if not p.is_file():
            notes.append(f"missing_events_file:{p.name}")
        else:
            try:
                raw = p.read_bytes()
                source_ref = _content_ref(p, raw)
                data = json.loads(raw.decode("utf-8-sig"))
                events = data if isinstance(data, list) else data.get("events")
                if isinstance(events, list):
                    planned = sum(1 for e in events if isinstance(e, dict) and e.get("category") == "planned_owner_decision")
                    unplanned = sum(1 for e in events if isinstance(e, dict) and e.get("category") == "unplanned_rescue")
                else:
                    notes.append("invalid_events_structure")
            except Exception as exc:
                notes.append(f"events_parse_error:{type(exc).__name__}")

    if isinstance(unplanned, int) and unplanned > 0 and source_ref is not None:
        rescue_refs.add(source_ref)
    if rescue_refs:
        unexpected_rescue = "yes"
        if rescue_confirmed_none:
            notes.append("rescue_evidence_conflicts_with_confirmed_none")
    else:
        unexpected_rescue = "no" if rescue_confirmed_none else "unknown"

    return {
        "planned_owner_decisions": planned,
        "unplanned_rescues": unplanned,
        "unexpected_rescue_observed": unexpected_rescue,
        "rescue_evidence_refs": sorted(rescue_refs),
        "human_minutes": confirmed_minutes if confirmed_minutes is not None else "UNKNOWN",
        "human_minutes_source": "owner_confirmed" if confirmed_minutes is not None else "unmeasured",
        "wall_clock_excluded": True,
        "source_ref": source_ref,
        "notes": notes,
    }


def _zh_code_status(value: str) -> str:
    return {
        "YES": "已完成（YES）",
        "NO": "未完成（NO）",
        "NOT_VERIFIED": "尚未驗證（NOT_VERIFIED，缺少合併通過或測試證據檔）",
        "UNKNOWN": "未知（UNKNOWN）",
    }.get(value, value)


def _zh_merged_status(value: str) -> str:
    return {
        "YES": "已合併且 Post-Merge CI 通過（YES）",
        "NO": "尚未合併（NO）",
        "PARTIAL": "部分合併或 CI 未全過（PARTIAL）",
        "UNKNOWN": "未知（UNKNOWN）",
    }.get(value, value)


def _zh_deployed_status(value: str) -> str:
    if value == "UNKNOWN":
        return "未知（UNKNOWN，未提供正式部署或啟用紀錄）"
    return value


def _zh_count(value: int | str) -> str:
    if value == "UNKNOWN":
        return "未知（UNKNOWN，未提供人工介入事件檔，不以 0 冒充）"
    return f"{value} 次"


def _zh_minutes(value: float | int | str) -> str:
    if value == "UNKNOWN":
        return "未知（UNKNOWN，未經負責人確認；不使用經過時間 Wall-clock 冒充）"
    return f"{value} 分鐘（負責人確認）"


def _markdown_cell(value: str) -> str:
    value = " ".join(value.splitlines())
    return html.escape(value).replace("|", "&#124;").replace("`", "&#96;")


def _provider_report_rows(providers: dict[str, Any]) -> list[str]:
    labels = {"claude": "Claude Code", "gemini": "Gemini CLI", "copilot": "Copilot Billing Reference"}
    rows = []
    for key, provider in providers.items():
        if key == "outer_orchestrator":
            name = _markdown_cell(provider["provider"])
            rows.append(f"| Outer Orchestrator（{name}） | `unknown`；單位未知；未評估完整度（無可驗證的本機用量紀錄） |")
            continue
        cell = (
            f"`{provider['presence_state']}`；單位 `{provider['unit']}`；"
            f"完整度 `{provider['cost_completeness']}`（範圍 `{provider['completeness_scope']}`）"
        )
        if key == "copilot" and provider["presence_state"] == "billing_reference_only":
            window = provider["billing_window"]
            cell += f"；帳務期間 {window['start_date']} 至 {window['end_date']}，涵蓋範圍排除程式碼補全，無法歸屬單一工作項目"
            for model, quantity in provider["by_model_aic"].items():
                cell += f"；{_markdown_cell(model)} {quantity:,}"
        if key == "copilot" and provider["ignored_columns"]:
            ignored = ", ".join(provider["ignored_columns"])
            cell += f"；已忽略金額欄位 `{ignored}`"
        if key == "copilot" and provider["anomalies"]:
            cell += "；帳務資料異常見證據索引"
        if provider.get("known_totals") is not None:
            for field, value in provider["known_totals"].items():
                count = f"{value:,}" if value is not None else "未知"
                cell += f"；`{field}` {count}"
        rows.append(f"| {labels[key]} | {cell} |")
    return rows


def render_markdown_report(evidence: dict[str, Any]) -> str:
    delivery = evidence["delivery"]
    human = evidence["human_interventions"]
    tokens = evidence["ai_cost"]
    self_cost = evidence["observer_self_cost"]

    known_totals = tokens["known_totals"]
    known = known_totals["total_tokens"]
    main_tok = tokens["by_role"]["main"]["total_tokens"]
    guard_tok = tokens["by_role"]["guardian"]["total_tokens"]
    sub_tok = tokens["by_role"]["subagent"]["total_tokens"]
    unk_tok = tokens["by_role"]["unknown"]["total_tokens"]
    comp = tokens["cost_completeness"]

    if known > 0:
        breakdown = f"主模型 Main {main_tok:,} / 審查 Guardian {guard_tok:,} / 子代理 Sub-agent {sub_tok:,}"
        if unk_tok > 0:
            breakdown += f" / 未知角色 Unknown {unk_tok:,}"
        scope_label = "完整驗證（相對於預期 Session 清單）" if tokens["work_item_cost_complete"] else "僅為已知合計（未證明涵蓋全部 Session）"
        token_detail = (
            f"輸入 {known_totals['input_tokens']:,}（快取命中 {known_totals['cached_input_tokens']:,}、"
            f"未快取 {known_totals['uncached_input_tokens']:,}）"
            f"＋輸出 {known_totals['output_tokens']:,}（含推理 {known_totals['reasoning_output_tokens']:,}）"
        )
        token_cell = f"{known:,}（{scope_label}；{breakdown}；{token_detail}；費用金額 UNKNOWN）"
    else:
        token_cell = f"未知（UNKNOWN；完整度 `{comp}`，未取得 Codex 原始 rollout 紀錄或尚無可用 Token 資料）"

    if delivery["product_verified"] == "NOT_VERIFIED":
        product_cell = "尚未驗證（NOT_VERIFIED，缺少可核對之產品驗收證據檔）"
    else:
        ev_ref = delivery.get("product_evidence_ref")
        product_cell = f"{delivery['product_verified']}（證據檔 `{ev_ref}`）" if ev_ref else str(delivery["product_verified"])

    if self_cost["mode"] == "script_only":
        obs_cell = (
            f"腳本耗時 {self_cost['duration_ms']} ms（純腳本執行 0 LLM Tokens；若另由 AI 協助解讀須單獨計入）"
        )
    else:
        obs_cell = (
            f"腳本耗時 {self_cost['duration_ms']} ms（外層協助 AI Tokens={self_cost['observer_ai_tokens']}；"
            f"可用量測 `ai_usage_available={self_cost['ai_usage_available']}`）"
        )

    rescue_state = human.get("unexpected_rescue_observed", "unknown")
    rescue_cell = {
        "yes": "`yes`（有事件紀錄或救援證據引用）",
        "no": "`no`（已明確確認無救援）",
        "unknown": "`unknown`（現有證據不足以確認是否曾發生救援）",
    }[rescue_state]

    lines = [
        f"# G4 Observer — {evidence['title']}（`{evidence['work_item_id']}`）",
        "",
        f"- **目標儲存庫**：`{evidence['repo']}`",
        f"- **觀測時間（UTC）**：`{evidence['observed_at_utc']}`",
        "",
        "## 一、交付與成本總覽",
        "",
        "| 項目 | 觀察結果 |",
        "| --- | --- |",
        f"| 程式完成（Code Completed） | {_zh_code_status(delivery['code_completed'])} |",
        f"| 合併與 CI（Merged + CI） | {_zh_merged_status(delivery['merged_and_ci'])} |",
        f"| 產品驗收（Product Verified） | {product_cell} |",
        f"| 正式部署／啟用（Deployed / Enabled） | {_zh_deployed_status(delivery['deployed_or_enabled'])} |",
        f"| 必要 Owner 決策 | {_zh_count(human['planned_owner_decisions'])} |",
        f"| 意外人工救援 | {_zh_count(human['unplanned_rescues'])} |",
        f"| 是否觀察到意外人工救援 | {rescue_cell} |",
        f"| 人工實際分鐘數 | {_zh_minutes(human['human_minutes'])} |",
        f"| 完整 AI Tokens / 成本 | {token_cell} |",
        *_provider_report_rows(tokens.get("providers", {})),
        f"| Observer 自身成本 | {obs_cell} |",
        "",
    ]
    if tokens.get("providers"):
        lines.extend(["「完整 AI Tokens / 成本」列呈現 Codex 用量。各供應商數字保留原單位，跨供應商合計已停用。", ""])

    prs = delivery.get("prs") or []
    if prs:
        lines.extend(
            [
                "## 二、PR 與 CI 證據",
                "",
                "| PR | 狀態 | Exact HEAD | Merge Commit | Post-Merge CI |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for pr in prs:
            num = pr.get("number")
            url = pr.get("url")
            pr_label = f"[#{num}]({url})" if url else f"#{num}"
            head_short = (pr.get("head_sha") or "UNKNOWN")[:8]
            merge_short = (pr.get("merge_sha") or "—")[:8]
            lines.append(
                f"| {pr_label} | `{pr.get('state', 'UNKNOWN')}` | `{head_short}` | `{merge_short}` | `{pr.get('post_merge_ci', 'UNKNOWN')}` |"
            )
        lines.append("")

    parsed_zh = "是（已找到的紀錄檔皆解析正常）" if tokens["parsed_files_valid"] else "否（無紀錄檔或含解析異常）"
    complete_zh = "是（預期 Session 清單皆已納入）" if tokens["work_item_cost_complete"] else "否（缺少預期清單或有遺漏 Session）"
    comp_zh = "完整（complete）" if comp == "complete" else "不完整（incomplete）"
    cmp_zh = "可納入跨任務 Token 比較（1）" if tokens["comparability_token"] == 1 else "不可納入跨任務比較（0）"

    lines.extend(
        [
            "## 三、判讀欄位與非宣稱邊界",
            "",
            f"- **紀錄檔解析有效（`parsed_files_valid={tokens['parsed_files_valid']}`）**：{parsed_zh}。",
            f"- **任務成本完整（`work_item_cost_complete={tokens['work_item_cost_complete']}`）**：{complete_zh}。",
            f"- **成本完整度（`cost_completeness={comp}`）**：{comp_zh}。",
            f"- **Token 可比較標記（`comparability_token={tokens['comparability_token']}`）**：{cmp_zh}。",
            "- **隱私與非宣稱**：本報告僅保存去識別化摘要與雜湊引用（不含原始 Codex JSONL、照片或本機絕對路徑），"
            "不影響 PR 合併資格、不構成 ROI 證明，也不作為跨任務代理排名依據。完整機器可讀欄位見同目錄 `evidence_index.json`。",
            "",
        ]
    )
    return "\n".join(lines)


def _safe_archive_slug(work_item_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", work_item_id.strip()).strip("-.")
    if not slug:
        raise ValueError(f"Invalid work_item_id for archive directory: {work_item_id!r}")
    return slug


def update_archive_index(archive_root: Path) -> Path:
    """Rebuild a concise Chinese summary table (INDEX.md) across all archived Work Items."""
    root = Path(archive_root)
    root.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, dict[str, Any]]] = []
    for index_file in sorted(root.glob("*/evidence_index.json")):
        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("work_item_id"):
            records.append((index_file.parent.name, data))

    lines = [
        "# G4 Observer 長期觀測紀錄總覽",
        "",
        "本目錄保存各自然產品任務（Work Item）的**去識別化**觀測報告（`report.md` 與 `evidence_index.json`），供跨任務長期追蹤與檢視。",
        "",
        "- 僅保存去識別化摘要與雜湊引用；完整 Codex rollout JSONL、課本照片與本機敏感路徑一律保留於本機，不上傳 GitHub。",
        "- 部分欄位若尚無可核對證據，仍會如實保存並標記為 `UNKNOWN`，不等待所有欄位補齊才歸檔。",
        "- 本總覽僅作唯讀觀察紀錄，不作為合併 Gate、ROI 證明或跨任務排名。",
        "",
        "| Work Item | 任務名稱 | 儲存庫 | 合併與 CI | 產品驗收 | Codex Tokens（完整度） | 人工介入 / 分鐘 | 詳細報告 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for slug, data in records:
        wid = data.get("work_item_id", slug)
        title = data.get("title", "")
        repo = data.get("repo", "UNKNOWN")
        delivery = data.get("delivery") or {}
        ai_cost = data.get("ai_cost") or {}
        human = data.get("human_interventions") or {}
        merged = delivery.get("merged_and_ci", "UNKNOWN")
        prod = delivery.get("product_verified", "UNKNOWN")
        known_tok = (ai_cost.get("known_totals") or {}).get("total_tokens", 0)
        comp = ai_cost.get("cost_completeness", "incomplete")
        tok_text = f"{known_tok:,}（`{comp}`）" if known_tok > 0 else f"UNKNOWN（`{comp}`）"
        human_text = f"決策 {human.get('planned_owner_decisions', 'UNKNOWN')} / 救援 {human.get('unplanned_rescues', 'UNKNOWN')} / {human.get('human_minutes', 'UNKNOWN')}"
        lines.append(
            f"| `{wid}` | {title} | `{repo}` | `{merged}` | {prod} | {tok_text} | {human_text} | "
            f"[report.md](./{slug}/report.md) · [json](./{slug}/evidence_index.json) |"
        )
    lines.append("")
    index_md = root / "INDEX.md"
    index_md.write_text("\n".join(lines), encoding="utf-8")
    return index_md


def run_observer(
    *,
    work_item_id: str,
    title: str,
    repo: str | None,
    pr_numbers: list[int] | None,
    rollout_dirs: list[Path],
    output_dir: Path | None = None,
    archive_root: Path | None = None,
    exclude_session_ids: set[str] | None = None,
    expected_session_ids: set[str] | None = None,
    claude_dirs: list[Path] | None = None,
    claude_expected_session_ids: set[str] | None = None,
    claude_confirmed_unused: bool = False,
    gemini_dirs: list[Path] | None = None,
    gemini_expected_session_ids: set[str] | None = None,
    gemini_confirmed_unused: bool = False,
    copilot_csvs: list[Path] | None = None,
    copilot_confirmed_unused: bool = False,
    outer_orchestrator: str | None = None,
    events_path: Path | None = None,
    confirmed_minutes: float | None = None,
    rescue_evidence_refs: list[str] | None = None,
    rescue_confirmed_none: bool = False,
    code_evidence_file: Path | None = None,
    product_evidence_file: Path | None = None,
    product_verification_status: str | None = None,
    deployed_status: str | None = None,
    observer_mode: str = "script_only",
    observer_ai_tokens: int | None = None,
    gh_runner: Callable[[list[str]], str] = _default_gh_runner,
) -> tuple[Path, Path]:
    if output_dir is None and archive_root is None:
        raise ValueError("Either output_dir or archive_root must be provided.")
    started_perf = time.perf_counter()
    started_utc = datetime.now(timezone.utc).isoformat()

    delivery = collect_delivery_evidence(
        repo=repo,
        work_item_id=work_item_id,
        pr_numbers=pr_numbers,
        code_evidence_file=code_evidence_file,
        product_evidence_file=product_evidence_file,
        product_verification_status=product_verification_status,
        deployed_status=deployed_status,
        gh_runner=gh_runner,
    )
    ai_cost = parse_codex_rollout_dirs(
        rollout_dirs,
        exclude_session_ids=exclude_session_ids,
        expected_session_ids=expected_session_ids,
    )
    ai_cost["cross_provider_summation_allowed"] = False
    providers = {}
    if claude_dirs or claude_expected_session_ids or claude_confirmed_unused:
        providers["claude"] = parse_claude_transcripts(
            claude_dirs or [],
            expected_session_ids=claude_expected_session_ids,
            confirmed_unused=claude_confirmed_unused,
        )
    if gemini_dirs or gemini_expected_session_ids or gemini_confirmed_unused:
        providers["gemini"] = parse_gemini_transcripts(
            gemini_dirs or [],
            expected_session_ids=gemini_expected_session_ids,
            confirmed_unused=gemini_confirmed_unused,
        )
    if copilot_csvs or copilot_confirmed_unused:
        providers["copilot"] = parse_copilot_billing(copilot_csvs or [], confirmed_unused=copilot_confirmed_unused)
    if outer_orchestrator is not None:
        providers["outer_orchestrator"] = {
            "provider": outer_orchestrator,
            "presence_state": "unknown",
            "unit": None,
            "reason": "no_verifiable_local_token_rollout",
        }
    if providers:
        ai_cost["providers"] = providers
    human = summarize_human_interventions(
        events_path,
        confirmed_minutes=confirmed_minutes,
        rescue_evidence_refs=rescue_evidence_refs,
        rescue_confirmed_none=rescue_confirmed_none,
    )

    duration_ms = int(round((time.perf_counter() - started_perf) * 1000))
    if observer_mode == "script_only":
        self_cost = {
            "duration_ms": duration_ms,
            "ai_usage_available": False,
            "observer_ai_tokens": 0,
            "mode": "script_only",
            "note": "Script executes deterministically with 0 LLM tokens; any external Observer AI interpretation must be accounted separately.",
        }
    else:
        self_cost = {
            "duration_ms": duration_ms,
            "ai_usage_available": observer_ai_tokens is not None,
            "observer_ai_tokens": observer_ai_tokens if observer_ai_tokens is not None else "UNKNOWN",
            "mode": observer_mode,
        }

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
        "observer_self_cost": self_cost,
        "not_claimed": [
            "ROI proven",
            "cross-task agent ranking",
            "causal governance effectiveness proof",
            "merge gate authority",
        ],
    }

    report_text = render_markdown_report(evidence)
    index_text = json.dumps(evidence, indent=2, ensure_ascii=False) + "\n"

    primary_dir = Path(output_dir) if output_dir is not None else Path(archive_root) / _safe_archive_slug(work_item_id)
    primary_dir.mkdir(parents=True, exist_ok=True)
    report_path = primary_dir / "report.md"
    index_path = primary_dir / "evidence_index.json"
    report_path.write_text(report_text, encoding="utf-8")
    index_path.write_text(index_text, encoding="utf-8")

    if archive_root is not None:
        arch_dir = Path(archive_root) / _safe_archive_slug(work_item_id)
        if arch_dir.resolve() != primary_dir.resolve():
            arch_dir.mkdir(parents=True, exist_ok=True)
            (arch_dir / "report.md").write_text(report_text, encoding="utf-8")
            (arch_dir / "evidence_index.json").write_text(index_text, encoding="utf-8")
        update_archive_index(Path(archive_root))

    return report_path, index_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only G4 Work Item Observer (pilot)")
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--repo", default=None, help="GitHub owner/repo slug (optional)")
    parser.add_argument("--pr", dest="prs", type=int, action="append", default=[], help="PR number (repeatable)")
    parser.add_argument("--rollout-dir", dest="rollout_dirs", type=Path, action="append", default=[])
    parser.add_argument("--exclude-session-id", dest="exclude_session_ids", action="append", default=[])
    parser.add_argument("--expected-session-id", dest="expected_session_ids", action="append", default=[])
    parser.add_argument("--claude-dir", dest="claude_dirs", type=Path, action="append", default=[], help="Claude JSONL file or directory (repeatable)")
    parser.add_argument("--claude-expected-session-id", action="append", default=[], help="Claude session inventory (repeatable)")
    parser.add_argument("--claude-confirmed-unused", action="store_true")
    parser.add_argument("--gemini-dir", dest="gemini_dirs", type=Path, action="append", default=[], help="Gemini JSON/JSONL file or directory (repeatable)")
    parser.add_argument("--gemini-expected-session-id", action="append", default=[], help="Gemini session inventory (repeatable)")
    parser.add_argument("--gemini-confirmed-unused", action="store_true")
    parser.add_argument("--copilot-csv", dest="copilot_csvs", type=Path, action="append", default=[], help="Copilot daily billing export (repeatable)")
    parser.add_argument("--copilot-confirmed-unused", action="store_true")
    parser.add_argument("--outer-orchestrator", help="Name of an explicitly observed outer orchestrator with unknown usage")
    parser.add_argument("--events-file", type=Path, default=None)
    parser.add_argument("--owner-minutes-confirmed", type=float, default=None)
    parser.add_argument("--rescue-evidence-ref", action="append", default=[], help="Short rescue evidence reference (repeatable)")
    parser.add_argument("--rescue-confirmed-none", action="store_true", help="Owner confirmation or complete event log confirms no rescue")
    parser.add_argument("--code-evidence-file", type=Path, default=None)
    parser.add_argument("--product-evidence-file", type=Path, default=None)
    parser.add_argument("--product-verified", default=None)
    parser.add_argument("--deployed-status", default=None)
    parser.add_argument("--observer-mode", choices=("script_only", "llm_assisted"), default="script_only")
    parser.add_argument("--observer-ai-tokens", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=None,
        help="Optional redacted archive root (e.g., docs/status/g4-observer); writes <id>/report.md, evidence_index.json and updates INDEX.md",
    )
    args = parser.parse_args(argv)
    if args.output_dir is None and args.archive_root is None:
        parser.error("Provide --output-dir and/or --archive-root.")

    report_path, index_path = run_observer(
        work_item_id=args.work_item_id,
        title=args.title,
        repo=args.repo,
        pr_numbers=args.prs,
        rollout_dirs=args.rollout_dirs,
        output_dir=args.output_dir,
        archive_root=args.archive_root,
        exclude_session_ids=set(args.exclude_session_ids) or None,
        expected_session_ids=set(args.expected_session_ids) or None,
        claude_dirs=args.claude_dirs,
        claude_expected_session_ids=set(args.claude_expected_session_id) or None,
        claude_confirmed_unused=args.claude_confirmed_unused,
        gemini_dirs=args.gemini_dirs,
        gemini_expected_session_ids=set(args.gemini_expected_session_id) or None,
        gemini_confirmed_unused=args.gemini_confirmed_unused,
        copilot_csvs=args.copilot_csvs,
        copilot_confirmed_unused=args.copilot_confirmed_unused,
        outer_orchestrator=args.outer_orchestrator,
        events_path=args.events_file,
        confirmed_minutes=args.owner_minutes_confirmed,
        rescue_evidence_refs=args.rescue_evidence_ref,
        rescue_confirmed_none=args.rescue_confirmed_none,
        code_evidence_file=args.code_evidence_file,
        product_evidence_file=args.product_evidence_file,
        product_verification_status=args.product_verified,
        deployed_status=args.deployed_status,
        observer_mode=args.observer_mode,
        observer_ai_tokens=args.observer_ai_tokens,
    )
    print(f"report={report_path}")
    print(f"evidence_index={index_path}")
    if args.archive_root is not None:
        print(f"archive_index={Path(args.archive_root) / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
