from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "codex-pytest.ps1"
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="codex-pytest.ps1 is a PowerShell wrapper",
)


def _run_codex_pytest(test_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            str(test_file),
            "-q",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _receipt_path_from_stdout(stdout: str) -> Path:
    for line in stdout.splitlines():
        if line.startswith("[test_evidence_receipt] receipt="):
            receipt = line.split("receipt=", 1)[1].split(" ", 1)[0]
            return REPO_ROOT / receipt
    raise AssertionError(f"receipt line not found in stdout:\n{stdout}")


@pytest.mark.skipif(not VENV_PYTHON.is_file(), reason="repo .venv is not installed")
def test_codex_pytest_writes_receipt_for_passing_run(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample_pass.py"
    test_file.write_text(
        "def test_sample_pass():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    proc = _run_codex_pytest(test_file)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt_path = _receipt_path_from_stdout(proc.stdout)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw_output = REPO_ROOT / payload["output_artifacts"][0]
    try:
        assert payload["receipt_schema"] == "test_evidence_receipt.v0.1"
        assert payload["runner"] == "scripts/codex-pytest.ps1"
        assert payload["exit_code"] == 0
        assert payload["linked_commit"] != "no_git_worktree"
        assert str(VENV_PYTHON) in payload["command"]
        assert "-m pytest" in payload["command"]
        assert str(test_file) in payload["command"]
        assert raw_output.is_file()
        assert "1 passed" in raw_output.read_text(encoding="utf-8")
    finally:
        receipt_path.unlink(missing_ok=True)
        raw_output.unlink(missing_ok=True)


@pytest.mark.skipif(not VENV_PYTHON.is_file(), reason="repo .venv is not installed")
def test_codex_pytest_preserves_failure_exit_code_in_receipt(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample_fail.py"
    test_file.write_text(
        "def test_sample_fail():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    proc = _run_codex_pytest(test_file)

    assert proc.returncode == 1
    receipt_path = _receipt_path_from_stdout(proc.stdout)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw_output = REPO_ROOT / payload["output_artifacts"][0]
    try:
        assert payload["runner"] == "scripts/codex-pytest.ps1"
        assert payload["exit_code"] == 1
        assert raw_output.is_file()
        assert "1 failed" in raw_output.read_text(encoding="utf-8")
    finally:
        receipt_path.unlink(missing_ok=True)
        raw_output.unlink(missing_ok=True)
