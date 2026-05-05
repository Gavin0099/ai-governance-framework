from __future__ import annotations

import sqlite3
from pathlib import Path

from codeburn.phase1.codeburn_report import build_report


def test_report_fixed_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    conn = sqlite3.connect(db_path)
    schema = Path("codeburn/phase1/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute(
        """
        INSERT INTO sessions(
          session_id, task, repo_path, git_branch, created_at, ended_at, ended_by, data_quality,
          provider_summary, comparability_token, comparability_duration, comparability_change
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "s1",
            "report test",
            ".",
            "main",
            "2026-04-30T00:00:00+00:00",
            None,
            "manual",
            "partial",
            None,
            0,
            1,
            1,
        ),
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, git_status_before, git_status_after
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "st1",
            "s1",
            "planning",
            "echo hi",
            "local",
            "2026-04-30T00:00:00+00:00",
            "2026-04-30T00:00:01+00:00",
            1000,
            0,
            2,
            0,
            "unknown",
            "",
            "",
        ),
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["ok"] is True
    assert report["data_quality"] == "partial"
    assert report["token_comparability"] is False
    assert report["token_observability_level"] == "none"
    assert report["file_activity"]["git_visible_only"] is True
    assert report["file_activity"]["file_reads_visible"] is False
    assert report["observability_boundary_disclosed"] is True
    assert report["file_reads"] == "unsupported"


def test_report_token_observability_step_level(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    conn = sqlite3.connect(db_path)
    schema = Path("codeburn/phase1/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute(
        """
        INSERT INTO sessions(
          session_id, task, repo_path, git_branch, created_at, data_quality
        ) VALUES('s1', 'report test', '.', 'main', '2026-04-30T00:00:00+00:00', 'complete')
        """
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, total_tokens, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'execution', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'provider', 99, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["ok"] is True
    assert report["token_observability_level"] == "step_level"


def test_report_token_observability_coarse_for_estimated_tokens(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    conn = sqlite3.connect(db_path)
    schema = Path("codeburn/phase1/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute(
        """
        INSERT INTO sessions(
          session_id, task, repo_path, git_branch, created_at, data_quality
        ) VALUES('s1', 'report test', '.', 'main', '2026-04-30T00:00:00+00:00', 'complete')
        """
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, total_tokens, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'execution', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'estimated', 99, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["ok"] is True
    assert report["token_observability_level"] == "coarse"
