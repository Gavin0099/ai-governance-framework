import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import check_token_telemetry_contract_consistency as contract_check


def test_token_telemetry_contract_consistency_is_clean_for_current_repo():
    results = contract_check.run_checks()
    failed = [result for result in results if not result["ok"]]

    assert failed == []


def test_token_telemetry_contract_consistency_flags_missing_runtime_transitional_rule(monkeypatch):
    original_read_text = contract_check._read_text

    def fake_read_text(path: Path) -> str:
        text = original_read_text(path)
        if path == contract_check.RUNTIME_CONTRACT:
            text = text.replace("## Transitional Rule", "## Removed Transitional Rule")
            text = text.replace(
                "Absence of `provenance_warning` MUST NOT be interpreted as absence of mixed sources.",
                "Absence guard removed.",
            )
        return text

    monkeypatch.setattr(contract_check, "_read_text", fake_read_text)

    results = contract_check.run_checks()
    failed_ids = {result["id"] for result in results if not result["ok"]}

    assert "runtime_has_transitional_step_level_rule" in failed_ids
    assert "runtime_has_absence_guard" in failed_ids