from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE1_DIR = REPO_ROOT / "codeburn" / "phase1"
FIXTURE_SCRIPT = PHASE1_DIR / "create_distribution_smoke_fixture.py"
ANALYZE_SCRIPT = PHASE1_DIR / "codeburn_analyze.py"
REPORT_PS1 = PHASE1_DIR / "run_report.ps1"


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="distribution smoke uses PowerShell")


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_fixture(db_path: Path, *, cwd: Path) -> None:
    proc = _run(
        [sys.executable, str(FIXTURE_SCRIPT), "--db", str(db_path)],
        cwd=cwd,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"session_id": "distribution-smoke-session"' in proc.stdout


def _assert_analyze_output(proc: subprocess.CompletedProcess[str]) -> None:
    assert proc.returncode == 0, proc.stderr
    assert '"token_observability_level": "step_level"' in proc.stdout
    assert '"analysis_safe_for_decision": false' in proc.stdout
    assert '"decision_usage_allowed": false' in proc.stdout


def _assert_report_output(proc: subprocess.CompletedProcess[str]) -> None:
    assert proc.returncode == 0, proc.stderr
    assert "WRONG_MODULE" not in proc.stdout
    assert "WRONG_HEADER" not in proc.stdout
    assert '"token_observability_level": "step_level"' in proc.stdout
    assert '"token_source_summary": "mixed(provider, estimated)"' in proc.stdout
    assert '"decision_usage_allowed": false' in proc.stdout
    assert '"analysis_safe_for_decision": false' in proc.stdout


def test_distribution_smoke_minimal_flow_from_repo_root(tmp_path: Path) -> None:
    db_path = tmp_path / "distribution_smoke.db"
    _build_fixture(db_path, cwd=REPO_ROOT)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    analyze = _run(
        [
            sys.executable,
            str(ANALYZE_SCRIPT),
            "--db",
            str(db_path),
            "--session",
            "distribution-smoke-session",
            "--format",
            "json",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    _assert_analyze_output(analyze)

    report = _run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPORT_PS1),
            "-DatabasePath",
            str(db_path),
            "-SessionId",
            "distribution-smoke-session",
            "-Format",
            "json",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    _assert_report_output(report)


def test_distribution_smoke_report_runs_from_outside_repo(tmp_path: Path) -> None:
    db_path = tmp_path / "distribution_smoke.db"
    external_cwd = tmp_path / "outside"
    external_cwd.mkdir()
    _build_fixture(db_path, cwd=external_cwd)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    report = _run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPORT_PS1),
            "-DatabasePath",
            str(db_path),
            "-SessionId",
            "distribution-smoke-session",
            "-Format",
            "json",
        ],
        cwd=external_cwd,
        env=env,
    )
    _assert_report_output(report)


def test_distribution_smoke_report_ignores_wrong_pythonpath(tmp_path: Path) -> None:
    db_path = tmp_path / "distribution_smoke.db"
    _build_fixture(db_path, cwd=REPO_ROOT)

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

    report = _run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPORT_PS1),
            "-DatabasePath",
            str(db_path),
            "-SessionId",
            "distribution-smoke-session",
            "-Format",
            "json",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    _assert_report_output(report)