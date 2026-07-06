from __future__ import annotations

import json
from pathlib import Path

from governance_tools.test_signal_quality_audit import (
    build_test_signal_quality_audit,
    format_human,
    main,
    report_to_dict,
)


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_contract(repo: Path, validator_relpath: str = "validators/check_docs.py") -> None:
    _write(
        repo / "contract.yaml",
        "name: signal-test\n"
        "validators:\n"
        f"  - {validator_relpath}\n",
    )


def test_validator_with_positive_and_negative_fixtures_reports_pair(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", '{"ok": true}\n')
    _write(repo / "fixtures" / "check_docs" / "invalid_case.json", '{"ok": false}\n')
    _write(
        repo / "tests" / "test_check_docs.py",
        "def test_invalid_boundary_case():\n"
        "    assert {'status': 'invalid'}['status'] == 'invalid'\n",
    )

    report = build_test_signal_quality_audit(repo)
    payload = report_to_dict(report)

    assert payload["report_only"] is True
    assert payload["contract_validator_fixtures"] == "validator_fixture_pair_present"
    assert payload["mutation_boundary"] == "negative_or_boundary_cases_present"
    assert payload["validators"][0]["status"] == "validator_fixture_pair_present"
    assert "all contract validators have pass/fail fixture pairs" not in payload["cannot_claim"]


def test_positive_only_validator_fixture_reports_warning_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", '{"ok": true}\n')
    _write(repo / "tests" / "test_check_docs.py", "def test_happy_path():\n    assert 1 == 1\n")

    report = build_test_signal_quality_audit(repo)

    assert report.overall_status == "weak"
    assert report.contract_validator_fixtures == "positive_only_validator_fixture"
    assert report.validators[0].positive_fixtures == ["fixtures/check_docs/valid_case.json"]
    assert report.validators[0].negative_fixtures == []
    assert "all contract validators have pass/fail fixture pairs" in report.cannot_claim


def test_placeholder_validator_is_labeled_without_fixture_claim(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "# PLACEHOLDER validator until fixtures land\n")

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "placeholder_validator_declared"
    assert report.validators[0].placeholder_labeled is True
    assert report.validators[0].status == "placeholder_validator_declared"


def test_lexical_weak_signal_candidates_are_reported(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(
        repo / "tests" / "test_weak_signal.py",
        "import time\n"
        "\n"
        "def test_weak(mock_device):\n"
        "    result = {'status': 'ok'}\n"
        "    expected = result\n"
        "    time.sleep(1)\n"
        "    mock_device.send.assert_called_once()\n"
        "    assert result == expected\n",
    )

    report = build_test_signal_quality_audit(repo)

    assert report.oracle_independence == "production_derived_expected_value"
    assert report.determinism == "time_or_random_uncontrolled"
    assert report.mock_signal == "mock_only_weak_signal"
    assert "production_derived_expected_value candidate found" in report.warnings
    assert "mock_only_weak_signal candidate found" in report.warnings
    assert "time_or_random_uncontrolled candidate found" in report.warnings


def test_missing_contract_is_report_only_unknown(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    report = build_test_signal_quality_audit(tmp_path)

    assert report.overall_status == "unknown"
    assert report.contract_path is None
    assert report.contract_validator_fixtures == "unknown"
    assert "contract.yaml not found" in report.warnings


def test_human_and_json_cli_outputs_are_available(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")

    assert main(["--repo", str(repo), "--format", "human"]) == 0
    human = capsys.readouterr().out
    assert "[test_signal_quality]" in human
    assert "report_only=true" in human
    assert "claim_boundary=" in human

    assert main(["--repo", str(repo), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["report_only"] is True
    assert data["claim_boundary"].startswith("This audit is report-only.")


def test_format_human_lists_validator_fixture_counts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", "{}\n")

    text = format_human(build_test_signal_quality_audit(repo))

    assert "validators:" in text
    assert "check_docs: status=positive_only_validator_fixture" in text
    assert "positive=1 negative=0" in text
