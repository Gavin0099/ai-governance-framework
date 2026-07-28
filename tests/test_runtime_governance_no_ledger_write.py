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
    assert "AI_GOVERNANCE_NO_LEDGER_WRITE/w" in run_smoke_block
    assert 'case ":${WSLENV:-}:" in' in run_smoke_block
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


def test_runtime_governance_smoke_explicitly_propagates_injected_failure(
    tmp_path: Path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required to execute the runtime-governance wrapper contract")

    text = SCRIPT.read_text(encoding="utf-8")
    run_smoke_start = text.index("run_smoke()")
    run_smoke_block = text[run_smoke_start:text.index("run_pytest_suite()")]

    assert run_smoke_block.count("run_smoke_step ") == 14
    assert run_smoke_block.count("|| return $?") == 14
    assert "set -e" not in run_smoke_block

    # The repository may be checked out with CRLF on Windows. This test locks
    # the shell control-flow contract, so execute an LF-normalized fixture
    # without rewriting the tracked script.
    fixture_script = tmp_path / "scripts" / "run-runtime-governance.sh"
    fixture_library = tmp_path / "scripts" / "lib" / "python.sh"
    fixture_library.parent.mkdir(parents=True)
    fixture_script.write_text(text, encoding="utf-8", newline="\n")
    fixture_library.write_text(
        (Path("scripts") / "lib" / "python.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    fake_python = tmp_path / "bin" / "fake_python"
    fake_python.parent.mkdir()
    fake_python.write_text(
        """#!/usr/bin/env bash
previous=""
saw_smoke=false
for arg in "$@"; do
    if [[ "$arg" == "runtime_hooks/smoke_test.py" ]]; then
        saw_smoke=true
    fi
    if [[ "$previous" == "--event-type" && "$arg" == "post_task" && "$saw_smoke" == true ]]; then
        exit 23
    fi
    previous="$arg"
done
exit 0
""",
        encoding="utf-8",
        newline="\n",
    )
    fake_python.chmod(0o755)

    probe = r"""
export PATH="$(pwd)/bin:/usr/bin:/mingw64/bin:$PATH"
export AI_GOVERNANCE_PYTHON=fake_python
./scripts/run-runtime-governance.sh --mode smoke
"""
    result = subprocess.run(
        [bash, "-c", probe],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "[runtime-governance] complete" not in result.stdout
    assert "step=claude-post-task rc=23" in result.stderr
