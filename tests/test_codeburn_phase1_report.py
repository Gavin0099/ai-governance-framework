from __future__ import annotations

import sqlite3
import subprocess
import sys
import os
from pathlib import Path

from codeburn.phase1.codeburn_report import _print_text, build_report


def _create_report_db(db_path: Path) -> None:
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
      "complete",
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
      stdout_bytes, stderr_bytes, token_source, prompt_tokens, completion_tokens, total_tokens, git_status_before, git_status_after
    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
      "st1",
      "s1",
      "execution",
      "echo hi",
      "local",
      "2026-04-30T00:00:00+00:00",
      "2026-04-30T00:00:01+00:00",
      1000,
      0,
      2,
      0,
      "provider",
      70,
      29,
      99,
      "",
      "",
    ),
  )
  conn.commit()
  conn.close()


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
    assert report["token_source_summary"] == "unknown"
    assert report["provenance_warning"] == "provenance_unverified"
    assert report["token_count"] == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }
    assert (
        report["non_authoritative_notice"]
        == "Token fields are observational only and MUST NOT be used for automated decision, gating, or quality inference."
    )
    assert report["file_activity"]["git_visible_only"] is True
    assert report["file_activity"]["file_reads_visible"] is False
    assert report["observability_boundary_disclosed"] is True
    assert report["file_reads"] == "unsupported"
    assert report["governance_decision_usage_allowed"] is False
    assert report["operational_guard_usage_allowed"] is False
    assert report["decision_safety"] == "NON_DECISIONAL"
    assert "token_count" in report["non_authoritative_fields"]
    assert "token_observability_level" in report["non_authoritative_fields"]


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
          stdout_bytes, stderr_bytes, token_source, prompt_tokens, completion_tokens, total_tokens, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'execution', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'provider', 70, 29, 99, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["ok"] is True
    assert report["token_observability_level"] == "step_level"
    assert report["token_count"]["prompt_tokens"] == 70
    assert report["token_count"]["completion_tokens"] == 29
    assert report["token_count"]["total_tokens"] == 99
    assert report["token_source_summary"] == "provider"
    assert report["provenance_warning"] == "none"


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
    assert report["token_count"]["total_tokens"] == 99
    assert report["token_source_summary"] == "estimated"
    assert report["provenance_warning"] == "provenance_unverified"


def test_report_mixed_step_level_discloses_mixed_sources(tmp_path: Path) -> None:
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
          stdout_bytes, stderr_bytes, token_source, prompt_tokens, completion_tokens, total_tokens, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'execution', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'provider', 60, 39, 99, '', '')
        """
    )
    conn.execute(
        """
        INSERT INTO steps(
          step_id, session_id, step_kind, command, provider, started_at, ended_at, duration_ms, exit_code,
          stdout_bytes, stderr_bytes, token_source, total_tokens, git_status_before, git_status_after
        ) VALUES('st2', 's1', 'execution', 'echo hi again', 'local', '2026-04-30T00:00:02+00:00',
                 '2026-04-30T00:00:03+00:00', 1000, 0, 2, 0, 'estimated', 42, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["ok"] is True
    assert report["token_observability_level"] == "step_level"
    assert report["token_count"]["prompt_tokens"] == 60
    assert report["token_count"]["completion_tokens"] == 39
    assert report["token_count"]["total_tokens"] == 141
    assert report["token_source_summary"] == "mixed(provider, estimated)"
    assert report["provenance_warning"] == "mixed_sources"
    assert report["decision_usage_allowed"] is False
    assert report["governance_decision_usage_allowed"] is False
    assert report["operational_guard_usage_allowed"] is False
    assert report["decision_safety"] == "NON_DECISIONAL"


def test_report_text_omits_mixed_warning_for_provider_only_step_level(tmp_path: Path, capsys) -> None:
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
          stdout_bytes, stderr_bytes, token_source, prompt_tokens, completion_tokens, total_tokens, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'execution', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'provider', 50, 49, 99, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    _print_text(report)
    captured = capsys.readouterr()

    assert "Token source summary: provider" in captured.out
    assert "Provenance warning:" not in captured.out
    assert "Token fields are observational only and MUST NOT be used for automated decision, gating, or quality inference." in captured.out


def test_report_provider_total_only_is_coarse_not_step_level(tmp_path: Path) -> None:
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
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'provider', 200, '', '')
        """
    )
    conn.commit()
    conn.close()

    report = build_report(db_path, "s1")
    assert report["token_observability_level"] == "coarse"
    assert report["token_count"] == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": 200,
    }


def test_report_cli_absolute_path_succeeds_outside_repo_without_pythonpath(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    _create_report_db(db_path)
    script_path = Path("codeburn/phase1/codeburn_report.py").resolve()

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db",
            str(db_path),
            "--format",
            "json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert proc.returncode == 0
    assert '"token_observability_level": "step_level"' in proc.stdout
    assert '"token_source_summary": "provider"' in proc.stdout


def test_report_cli_ignores_shadowed_pythonpath_modules(tmp_path: Path) -> None:
    db_path = tmp_path / "phase1.db"
    _create_report_db(db_path)
    script_path = Path("codeburn/phase1/codeburn_report.py").resolve()

    shadow_root = tmp_path / "shadow"
    (shadow_root / "codeburn" / "phase1").mkdir(parents=True)
    (shadow_root / "codeburn" / "__init__.py").write_text("", encoding="utf-8")
    (shadow_root / "codeburn" / "phase1" / "__init__.py").write_text("", encoding="utf-8")
    (shadow_root / "codeburn" / "phase1" / "token_observability.py").write_text(
        "def token_observability_level(rows):\n    return 'WRONG_MODULE'\n",
        encoding="utf-8",
    )
    (shadow_root / "codeburn_phase1_header.py").write_text(
        "def print_phase1_header():\n    print('WRONG_HEADER')\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(shadow_root)

    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--db",
            str(db_path),
            "--format",
            "text",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert proc.returncode == 0
    assert "WRONG_HEADER" not in proc.stdout
    assert "WRONG_MODULE" not in proc.stdout
    assert "Token observability level: step_level" in proc.stdout


def test_report_cli_runs_from_repo_root_without_pythonpath_override(tmp_path: Path) -> None:
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
          stdout_bytes, stderr_bytes, token_source, git_status_before, git_status_after
        ) VALUES('st1', 's1', 'planning', 'echo hi', 'local', '2026-04-30T00:00:00+00:00',
                 '2026-04-30T00:00:01+00:00', 1000, 0, 2, 0, 'unknown', '', '')
        """
    )
    conn.commit()
    conn.close()

    proc = subprocess.run(
        [
            sys.executable,
            "codeburn/phase1/codeburn_report.py",
            "--db",
            str(db_path),
            "--session-id",
            "s1",
            "--format",
            "json",
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"ok": true' in proc.stdout
