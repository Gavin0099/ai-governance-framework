from __future__ import annotations

import sqlite3
import subprocess
from argparse import Namespace
from pathlib import Path

from codeburn.phase1 import codeburn_run
from codeburn.phase1.codeburn_analyze import build_analysis
from codeburn.phase1.codeburn_report import build_report
from codeburn.phase1.validate_phase1_data import validate


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    (path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def _create_session(db_path: Path, schema_path: Path, repo_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    session_id = "sess-1"
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, repo_path, git_branch, created_at, data_quality)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (session_id, "m2 test", str(repo_path), "main", "2026-04-30T00:00:00+00:00", "complete"),
    )
    conn.commit()
    conn.close()
    return session_id


def test_codeburn_run_success_and_changed_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")

    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _create_session(db_path, schema_path, repo)

    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="execution",
        provider="local",
        token_source="unknown",
        retry_of=None,
        command=["python", "-c", "print('ok')"],
    )

    rc = codeburn_run.run_step(args)
    assert rc == 0

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT exit_code, duration_ms, stdout_bytes, stderr_bytes FROM steps").fetchone()
    assert row is not None
    assert row[0] == 0
    assert row[1] is not None
    assert row[2] >= 0
    assert row[3] >= 0

    changed = conn.execute("SELECT file_path FROM changed_files").fetchall()
    assert changed
    assert changed[0][0] == "tracked.txt"
    conn.close()

    result = validate(db_path)
    assert result["ok"] is True


def test_codeburn_run_start_failure_contract_marks_partial(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _create_session(db_path, schema_path, repo)

    real_run = codeburn_run.subprocess.run

    def _mock_run(*args, **kwargs):
        cmd = args[0]
        if isinstance(cmd, str):
            raise OSError("failed to start command")
        return real_run(*args, **kwargs)

    monkeypatch.setattr(codeburn_run.subprocess, "run", _mock_run)

    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="execution",
        provider="local",
        token_source="unknown",
        retry_of=None,
        command=["python", "-c", "print('ok')"],
    )

    rc = codeburn_run.run_step(args)
    assert rc == 1

    conn = sqlite3.connect(db_path)
    step = conn.execute("SELECT exit_code, duration_ms, stderr_bytes FROM steps").fetchone()
    assert step is not None
    assert step[0] is None
    assert step[1] is None
    assert step[2] > 0

    session_quality = conn.execute("SELECT data_quality FROM sessions WHERE session_id='sess-1'").fetchone()
    assert session_quality is not None
    assert session_quality[0] == "partial"
    conn.close()

    result = validate(db_path)
    assert result["ok"] is True


def test_codeburn_run_token_fields_stored(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _create_session(db_path, schema_path, repo)

    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="planning",
        provider="local",
        token_source="estimated",
        prompt_tokens=512,
        completion_tokens=128,
        total_tokens=640,
        retry_of=None,
        command=["python", "-c", "print('ok')"],
    )

    rc = codeburn_run.run_step(args)
    assert rc == 0

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT prompt_tokens, completion_tokens, total_tokens, token_source FROM steps"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 512
    assert row[1] == 128
    assert row[2] == 640
    assert row[3] == "estimated"


def test_codeburn_run_token_fields_default_null(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    _create_session(db_path, schema_path, repo)

    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="execution",
        provider="local",
        token_source="unknown",
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        retry_of=None,
        command=["python", "-c", "print('ok')"],
    )

    rc = codeburn_run.run_step(args)
    assert rc == 0

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT prompt_tokens, completion_tokens, total_tokens FROM steps"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] is None
    assert row[1] is None
    assert row[2] is None


def test_codeburn_run_estimated_tokens_flow_to_analysis_and_report(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    db_path = tmp_path / "phase1.db"
    schema_path = Path("codeburn/phase1/schema.sql").resolve()
    session_id = _create_session(db_path, schema_path, repo)

    args = Namespace(
        db=str(db_path),
        schema=str(schema_path),
        repo=str(repo),
        step_kind="planning",
        provider="local",
        token_source="estimated",
        prompt_tokens=512,
        completion_tokens=128,
        total_tokens=640,
        retry_of=None,
        command=["python", "-c", "print('ok')"],
    )

    rc = codeburn_run.run_step(args)
    assert rc == 0

    analysis = build_analysis(db_path, session_id)
    report = build_report(db_path, session_id)

    conn = sqlite3.connect(db_path)
    comparability_token = conn.execute(
        "SELECT comparability_token FROM sessions WHERE session_id=?",
        (session_id,),
    ).fetchone()
    conn.close()

    assert analysis["ok"] is True
    assert analysis["token_observability_level"] == "coarse"
    assert analysis["analysis_safe_for_decision"] is False
    assert analysis["decision_usage_allowed"] is False
    assert analysis["token_comparability"] is False

    assert report["ok"] is True
    assert report["token_observability_level"] == "coarse"
    assert report["analysis_safe_for_decision"] is False
    assert report["decision_usage_allowed"] is False
    assert report["token_comparability"] is False

    assert comparability_token is not None
    assert comparability_token[0] == 0
