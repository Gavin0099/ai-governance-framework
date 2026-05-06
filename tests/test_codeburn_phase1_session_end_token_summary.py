from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from codeburn.phase1 import codeburn_run, codeburn_session


def _start(db_path: Path, schema_path: Path, repo: Path, task: str) -> int:
    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        operator="test",
        cmd="session-start",
        task=task,
        idle_timeout_minutes=60,
        open_session_action="auto_close_previous",
    )
    return codeburn_session.session_start(args)


def _end(db_path: Path, schema_path: Path, repo: Path, analyze: bool = False) -> int:
    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        operator="test",
        cmd="session-end",
        analyze=analyze,
    )
    return codeburn_session.session_end(args)


def test_session_end_always_emits_token_summary_for_empty_session(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()

    assert _start(db_path, schema_path, repo, "token-summary-empty") == 0
    _ = capsys.readouterr()  # clear start output

    assert _end(db_path, schema_path, repo, analyze=False) == 0
    out = capsys.readouterr().out

    first_json_end = out.find("}\n")
    payload = json.loads(out[: first_json_end + 1])
    token = payload["token_summary"]
    assert token["prompt_tokens"] is None
    assert token["completion_tokens"] is None
    assert token["total_tokens"] is None
    assert token["token_source_summary"] == "unknown"
    assert token["token_observability_level"] == "none"
    assert token["decision_usage_allowed"] is False
    assert token["analysis_safe_for_decision"] is False
    assert "Token summary:" in out


def test_session_end_token_summary_reflects_estimated_step_tokens(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    repo = Path(".").resolve()

    assert _start(db_path, schema_path, repo, "token-summary-estimated") == 0
    _ = capsys.readouterr()

    run_args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="planning",
        provider="local",
        token_source="estimated",
        prompt_tokens=120,
        completion_tokens=45,
        total_tokens=165,
        retry_of=None,
        command=["cmd", "/c", "exit", "0"],
    )
    assert codeburn_run.run_step(run_args) == 0
    _ = capsys.readouterr()

    assert _end(db_path, schema_path, repo, analyze=False) == 0
    out = capsys.readouterr().out
    first_json_end = out.find("}\n")
    payload = json.loads(out[: first_json_end + 1])
    token = payload["token_summary"]
    assert token["prompt_tokens"] == 120
    assert token["completion_tokens"] == 45
    assert token["total_tokens"] == 165
    assert token["token_source_summary"] == "estimated"
    assert token["token_observability_level"] == "step_level"
    assert token["provenance_warning"] == "provenance_unverified"
    assert token["decision_usage_allowed"] is False
    assert token["analysis_safe_for_decision"] is False
