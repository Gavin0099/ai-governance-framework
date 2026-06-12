from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/run-runtime-governance.sh")


def test_runtime_governance_smoke_sets_no_ledger_write_mode() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    run_smoke_start = text.index("run_smoke()")
    run_pytest_start = text.index("run_pytest_suite()")
    run_smoke_block = text[run_smoke_start:run_pytest_start]

    assert "export AI_GOVERNANCE_NO_LEDGER_WRITE=1" in run_smoke_block
