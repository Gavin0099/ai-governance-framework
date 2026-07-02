from pathlib import Path


SCRIPT = Path("scripts/apply-latest-governance-all.ps1")


def test_apply_latest_governance_all_relays_final_report_requirement_fields() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'final_report_requirement_status = "not_available"' in text
    assert 'final_report_required_marker = "[human_readable_adoption_summary]"' in text
    assert 'human_readable_adoption_summary = "not_relayed_in_aggregate"' in text
    assert "$j.final_report_requirement.status" in text
    assert "$j.final_report_requirement.required_marker" in text


def test_apply_latest_governance_all_declares_aggregate_boundary() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'aggregate_final_report_boundary = "aggregate_only; inspect report_path for final-report table rows"' in text
    assert "report_path could not be parsed for final-report fields" in text
    assert "report_path missing so final-report fields are not available" in text
