from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path("scripts/run-runtime-governance.sh")


def test_runtime_governance_smoke_sets_no_ledger_write_mode() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    run_smoke_start = text.index("run_smoke()")
    run_pytest_start = text.index("run_pytest_suite()")
    run_smoke_block = text[run_smoke_start:run_pytest_start]

    assert "run_smoke() (" in run_smoke_block
    assert "export AI_GOVERNANCE_NO_LEDGER_WRITE=1" in run_smoke_block
    assert 'pytest_basetemp="$(mktemp -d "${TMPDIR:-/tmp}/ai-governance-runtime.XXXXXX")"' in text
    assert '--basetemp "$pytest_basetemp"' in text


def _find_bash() -> str | None:
    candidates = [
        os.environ.get("BASH"),
        shutil.which("bash"),
        "/bin/bash",
        r"C:\Program Files\Git\bin\bash.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def test_runtime_governance_smoke_explicitly_propagates_injected_failure() -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required to execute the runtime-governance wrapper contract")

    text = SCRIPT.read_text(encoding="utf-8")
    run_smoke_start = text.index("run_smoke()")
    run_smoke_block = text[run_smoke_start:text.index("run_pytest_suite()")]

    assert run_smoke_block.count("run_smoke_step ") == 14
    assert run_smoke_block.count("|| return $?") == 14
    assert "set -e" not in run_smoke_block

    probe = r"""
export PATH="/usr/bin:/mingw64/bin:$PATH"
fake_python() {
    if [[ "$*" == *"runtime_hooks/smoke_test.py"* && "$*" == *"--event-type post_task"* ]]; then
        return 23
    fi
    return 0
}
export -f fake_python
export AI_GOVERNANCE_PYTHON=fake_python
./scripts/run-runtime-governance.sh --mode smoke
"""
    result = subprocess.run(
        [bash, "-c", probe],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "[runtime-governance] complete" not in result.stdout
    assert "step=claude-post-task rc=23" in result.stderr
