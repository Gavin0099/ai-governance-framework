from pathlib import Path


SCRIPT = Path("scripts/init-governance.sh")


def test_init_governance_declares_legacy_reporting_boundary() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "[legacy_reporting_path]" in text
    assert "final_report_requirement=not_reported" in text
    assert "human_readable_adoption_summary=not_reported" in text
    assert "canonical_reporting_entrypoint=python -m governance_tools.adopt_governance" in text
    assert "Use python -m governance_tools.adopt_governance" in text


def test_init_governance_reports_legacy_boundary_from_adopt_and_refresh_paths() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for expected in (
        'print_legacy_reporting_notice "adopt-existing-dry-run" "--dry-run"',
        'print_legacy_reporting_notice "adopt-existing"',
        'print_legacy_reporting_notice "refresh-baseline-dry-run" "--refresh"',
        'print_legacy_reporting_notice "refresh-baseline" "--refresh"',
    ):
        assert expected in text
