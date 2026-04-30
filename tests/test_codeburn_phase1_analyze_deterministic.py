from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


def test_phase1_analyze_output_is_deterministic(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    conn = sqlite3.connect(db_path)
    schema = Path("codeburn/phase1/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute(
        """
        INSERT INTO sessions(session_id, task, repo_path, git_branch, created_at, data_quality)
        VALUES('s1', 'deterministic', '.', 'main', '2026-04-30T00:00:00+00:00', 'complete')
        """
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, git_status_before, git_status_after
        ) VALUES
        ('st1', 's1', 'execution', 'cmd /c exit 1', 'local', '2026-04-30T00:00:01+00:00', '2026-04-30T00:00:01+00:00', 1000, 1, 0, 0, 'unknown', '', ''),
        ('st2', 's1', 'execution', 'cmd /c exit 1', 'local', '2026-04-30T00:00:02+00:00', '2026-04-30T00:00:02+00:00', 1000, 1, 0, 0, 'unknown', '', ''),
        ('st3', 's1', 'execution', 'cmd /c exit 1', 'local', '2026-04-30T00:00:03+00:00', '2026-04-30T00:00:03+00:00', 1000, 1, 0, 0, 'unknown', '', '')
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

    cmd = [
        sys.executable,
        "codeburn/phase1/codeburn_analyze.py",
        "--db",
        str(db_path),
        "--session",
        "s1",
        "--format",
        "json",
    ]
    out1 = subprocess.check_output(cmd, text=False)
    out2 = subprocess.check_output(cmd, text=False)
    assert out1 == out2
