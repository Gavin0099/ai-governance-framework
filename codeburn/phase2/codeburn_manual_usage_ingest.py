#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_session(
    conn: sqlite3.Connection,
    session_id: str,
    task: str,
    repo_path: str | None,
) -> None:
    existing = conn.execute(
        "SELECT 1 FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if existing is not None:
        return
    conn.execute(
        """
        INSERT INTO sessions(
            session_id, task, repo_path, created_at, data_quality,
            comparability_token, comparability_duration, comparability_change
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, task, repo_path, _now_iso(), "partial", 0, 1, 1),
    )


def _insert_manual_usage_record(
    conn: sqlite3.Connection,
    db_path: Path,
    session_id: str,
    task: str,
    repo_path: str | None,
    agent: str,
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    source_note: str | None,
    total_tokens: int | None = None,
) -> dict:
    _ensure_session(conn, session_id, task, repo_path)

    step_id = str(uuid.uuid4())
    now = _now_iso()
    command = f"manual-usage-ingest agent={agent} model={model} provider={provider}"
    conn.execute(
        """
        INSERT INTO steps(
            step_id, session_id, step_kind, command,
            provider, started_at,
            prompt_tokens, completion_tokens, total_tokens, token_source
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            step_id,
            session_id,
            "other",
            command,
            provider,
            now,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            "unknown",
        ),
    )
    conn.execute(
        """
        INSERT INTO step_ingestion_provenance(
            step_id, provider, epistemic_class, acquisition_mode,
            source_artifact_path, source_record_line, source_record_offset,
            real_time_observed, analysis_safe_for_decision,
            provider_truthfulness_assumed, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            step_id,
            provider,
            "Class E",
            "manual_reported_usage",
            str(db_path.resolve()),
            1,
            None,
            0,
            0,
            0,
            now,
        ),
    )
    if source_note:
        conn.execute(
            """
            INSERT INTO signals(
                session_id, step_id, signal, type, advisory_only,
                can_block, confidence, source, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                step_id,
                "manual_report_note",
                "metadata",
                1,
                0,
                "low",
                source_note[:512],
                now,
            ),
        )

    return {
        "ok": True,
        "session_id": session_id,
        "step_id": step_id,
        "agent": agent,
        "model": model,
        "provider": provider,
        "analysis_safe_for_decision": False,
        "decision_usage_allowed": False,
    }


def ingest_manual_usage(
    db_path: Path,
    session_id: str,
    task: str,
    repo_path: str | None,
    agent: str,
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    source_note: str | None,
    total_tokens: int | None = None,
) -> dict:
    from codeburn.phase1.claude_log_ingestor import _ensure_schema

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(conn)
    conn.execute("BEGIN")
    try:
        result = _insert_manual_usage_record(
            conn=conn,
            db_path=db_path,
            session_id=session_id,
            task=task,
            repo_path=repo_path,
            agent=agent,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            source_note=source_note,
            total_tokens=total_tokens,
        )
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _validate_non_negative_int(name: str, value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _validate_non_empty(name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _load_input_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("record must be a JSON object")
    required = [
        "session_id",
        "task",
        "agent",
        "model",
        "provider",
        "prompt_tokens",
        "completion_tokens",
    ]
    for key in required:
        if key not in payload:
            raise ValueError(f"missing required field: {key}")
    return payload


def _normalize_record(payload: dict) -> dict:
    session_id = _validate_non_empty("session_id", payload["session_id"])
    task = _validate_non_empty("task", payload["task"])
    agent = _validate_non_empty("agent", payload["agent"])
    model = _validate_non_empty("model", payload["model"])
    provider = _validate_non_empty("provider", payload["provider"])
    prompt_tokens = _validate_non_negative_int("prompt_tokens", payload["prompt_tokens"])
    completion_tokens = _validate_non_negative_int("completion_tokens", payload["completion_tokens"])
    total_tokens = None
    if "total_tokens" in payload and payload["total_tokens"] is not None:
        total_tokens = _validate_non_negative_int("total_tokens", payload["total_tokens"])
    return {
        "session_id": session_id,
        "task": task,
        "repo_path": payload.get("repo_path"),
        "agent": agent,
        "model": model,
        "provider": provider,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "source_note": payload.get("source_note"),
    }


def ingest_manual_usage_batch(db_path: Path, records: list[dict]) -> dict:
    from codeburn.phase1.claude_log_ingestor import _ensure_schema

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(conn)
    conn.execute("BEGIN")
    try:
        inserted = []
        for record in records:
            result = _insert_manual_usage_record(
                conn=conn,
                db_path=db_path,
                session_id=record["session_id"],
                task=record["task"],
                repo_path=record.get("repo_path"),
                agent=record["agent"],
                model=record["model"],
                provider=record["provider"],
                prompt_tokens=record["prompt_tokens"],
                completion_tokens=record["completion_tokens"],
                source_note=record.get("source_note"),
                total_tokens=record.get("total_tokens"),
            )
            inserted.append(
                {"session_id": result["session_id"], "step_id": result["step_id"]}
            )
        conn.commit()
        return {
            "ok": True,
            "batch_mode": True,
            "inserted_count": len(inserted),
            "inserted": inserted,
            "analysis_safe_for_decision": False,
            "decision_usage_allowed": False,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CodeBurn L0 manual usage ingest (analysis-only evidence)."
    )
    parser.add_argument("--db", required=True)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--task", default=None)
    parser.add_argument("--repo-path", default=None)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--prompt-tokens", type=int, default=None)
    parser.add_argument("--completion-tokens", type=int, default=None)
    parser.add_argument("--total-tokens", type=int, default=None)
    parser.add_argument("--source-note", default=None)
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.input_json:
        raw_payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if isinstance(raw_payload, dict):
            payload = _load_input_json(Path(args.input_json))
            normalized = _normalize_record(payload)
            result = ingest_manual_usage(
                db_path=Path(args.db),
                session_id=normalized["session_id"],
                task=normalized["task"],
                repo_path=normalized.get("repo_path"),
                agent=normalized["agent"],
                model=normalized["model"],
                provider=normalized["provider"],
                prompt_tokens=normalized["prompt_tokens"],
                completion_tokens=normalized["completion_tokens"],
                source_note=normalized.get("source_note"),
            )
        elif isinstance(raw_payload, list):
            if not raw_payload:
                raise ValueError("--input-json array must contain at least one record")
            normalized_records = []
            for idx, item in enumerate(raw_payload):
                if not isinstance(item, dict):
                    raise ValueError(f"record[{idx}] must be a JSON object")
                try:
                    payload = item
                    for key in ["session_id", "task", "agent", "model", "provider", "prompt_tokens", "completion_tokens"]:
                        if key not in payload:
                            raise ValueError(f"missing required field: {key}")
                    normalized_records.append(_normalize_record(payload))
                except ValueError as exc:
                    raise ValueError(f"record[{idx}] invalid: {exc}") from exc
            result = ingest_manual_usage_batch(
                db_path=Path(args.db),
                records=normalized_records,
            )
        else:
            raise ValueError("--input-json must contain a JSON object or JSON array")
    else:
        required_cli = [
            ("session_id", args.session_id),
            ("task", args.task),
            ("agent", args.agent),
            ("model", args.model),
            ("provider", args.provider),
            ("prompt_tokens", args.prompt_tokens),
            ("completion_tokens", args.completion_tokens),
        ]
        for key, value in required_cli:
            if value is None:
                raise ValueError(f"missing required CLI argument: --{key.replace('_', '-')}")
        session_id = args.session_id
        task = args.task
        repo_path = args.repo_path
        agent = args.agent
        model = args.model
        provider = args.provider
        prompt_tokens = args.prompt_tokens
        completion_tokens = args.completion_tokens
        source_note = args.source_note
        total_tokens_raw = args.total_tokens

        session_id = _validate_non_empty("session_id", session_id)
        task = _validate_non_empty("task", task)
        agent = _validate_non_empty("agent", agent)
        model = _validate_non_empty("model", model)
        provider = _validate_non_empty("provider", provider)
        prompt_tokens = _validate_non_negative_int("prompt_tokens", prompt_tokens)
        completion_tokens = _validate_non_negative_int("completion_tokens", completion_tokens)
        total_tokens = _validate_non_negative_int("total_tokens", total_tokens_raw) if total_tokens_raw is not None else None

        result = ingest_manual_usage(
            db_path=Path(args.db),
            session_id=session_id,
            task=task,
            repo_path=repo_path,
            agent=agent,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            source_note=source_note,
            total_tokens=total_tokens,
        )
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        if result.get("batch_mode"):
            print(f"ok={result['ok']} batch_mode=true inserted_count={result['inserted_count']}")
        else:
            print(f"ok={result['ok']} session_id={result['session_id']} step_id={result['step_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
