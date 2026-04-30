from __future__ import annotations

import sqlite3
from pathlib import Path

from codeburn.phase1.codeburn_analyze import build_analysis


def test_build_analysis_basics(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    conn = sqlite3.connect(db_path)
    schema = Path("codeburn/phase1/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, repo_path, git_branch, created_at, data_quality)
        VALUES('s1', 'analyze', '.', 'main', '2026-04-30T00:00:00+00:00', 'complete')
        """
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, git_status_before, git_status_after
        ) VALUES
        ('st1', 's1', 'test', 'cmd /c exit 1', 'local', '2026-04-30T00:00:01+00:00', '2026-04-30T00:00:01+00:00', 1000, 1, 0, 0, 'unknown', '', ''),
        ('st2', 's1', 'test', 'cmd /c exit 1', 'local', '2026-04-30T00:00:02+00:00', '2026-04-30T00:00:02+00:00', 2000, 1, 0, 0, 'unknown', '', ''),
        ('st3', 's1', 'test', 'cmd /c exit 1', 'local', '2026-04-30T00:00:03+00:00', '2026-04-30T00:00:03+00:00', 3000, 1, 0, 0, 'unknown', '', '')
        """
    )
    conn.execute(
        """
        INSERT INTO signals(session_id, step_id, signal, type, advisory_only, can_block, confidence, source, created_at)
        VALUES('s1', 'st3', 'retry_pattern_inferred', 'cost_risk', 1, 0, 'low', 'phase1_fallback', '2026-04-30T00:00:04+00:00')
        """
    )
    conn.commit()
    conn.close()

    result = build_analysis(db_path, "s1")
    assert result["ok"] is True
    assert result["task"] == "analyze"
    assert result["step_count"] == 3
    assert result["total_duration_ms"] == 6000
    assert result["slowest_step"]["step_kind"] == "test"
    assert result["changed_files"] == []
    assert result["signals"][0]["signal"] == "retry_pattern_inferred"
    assert result["signals"][0]["derived_from_steps"] == ["st1", "st2", "st3"]
    assert result["analysis_boundary"]["analysis_type"] == "observation"
    assert result["analysis_boundary"]["interpretation_level"] == "low"
    assert result["analysis_boundary"]["claims"] is False
