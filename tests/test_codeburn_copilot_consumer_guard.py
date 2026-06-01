from __future__ import annotations

from pathlib import Path

from codeburn.phase2.copilot_billing_consumer_guard import (
    run_consumer_bypass_guard,
    validate_consumer_bypass_guard,
)


def test_consumer_guard_passes_for_current_phase2_tree():
    phase2_dir = Path(__file__).parent.parent / "codeburn" / "phase2"
    result = validate_consumer_bypass_guard(phase2_dir)
    assert result["ok"] is True
    assert result["finding_count"] == 0


def test_consumer_guard_fails_when_summary_imports_ingestor(tmp_path):
    phase2_dir = tmp_path / "phase2"
    phase2_dir.mkdir(parents=True, exist_ok=True)
    (phase2_dir / "copilot_billing_summary.py").write_text(
        "from codeburn.phase2.copilot_billing_ingestor import ingest_copilot_csv\n",
        encoding="utf-8",
    )
    findings = run_consumer_bypass_guard(phase2_dir)
    assert any(f.code == "CONSUMER_IMPORTS_INGESTOR" for f in findings)


def test_consumer_guard_fails_when_summary_missing_report_dependency(tmp_path):
    phase2_dir = tmp_path / "phase2"
    phase2_dir.mkdir(parents=True, exist_ok=True)
    (phase2_dir / "copilot_billing_summary.py").write_text(
        "def build_copilot_billing_summary():\n    return {}\n",
        encoding="utf-8",
    )
    findings = run_consumer_bypass_guard(phase2_dir)
    assert any(f.code == "SUMMARY_MISSING_REPORT_DEPENDENCY" for f in findings)

