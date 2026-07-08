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


def test_invalid_fixture_name_is_not_counted_as_positive_fixture(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "invalid_case.json", '{"ok": false}\n')

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "negative_only_validator_fixture"
    assert report.validators[0].positive_fixtures == []
    assert report.validators[0].negative_fixtures == ["fixtures/check_docs/invalid_case.json"]


def test_noncompliant_fixture_name_is_not_counted_as_compliant_fixture(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "noncompliant.checks.json", '{"ok": false}\n')

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "negative_only_validator_fixture"
    assert report.validators[0].positive_fixtures == []
    assert report.validators[0].negative_fixtures == ["fixtures/check_docs/noncompliant.checks.json"]


def test_placeholder_validator_is_labeled_without_fixture_claim(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "# PLACEHOLDER validator until fixtures land\n")

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "placeholder_validator_declared"
    assert report.validators[0].placeholder_labeled is True
    assert report.validators[0].status == "placeholder_validator_declared"


def test_pass_statement_does_not_make_real_validator_placeholder(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(
        repo / "validators" / "check_docs.py",
        "def validate(payload):\n"
        "    try:\n"
        "        payload['required']\n"
        "    except KeyError:\n"
        "        pass\n"
        "    return True\n",
    )
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", '{"ok": true}\n')
    _write(repo / "fixtures" / "check_docs" / "invalid_case.json", '{"ok": false}\n')

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_fixture_pair_present"
    assert report.validators[0].placeholder_labeled is False
    assert report.validators[0].status == "validator_fixture_pair_present"


def test_missing_validator_reports_missing_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_missing"
    assert report.validators[0].exists is False
    assert report.validators[0].status == "validator_missing"


def test_multi_validator_aggregation_keeps_weakest_fixture_gap_visible(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "contract.yaml",
        "name: signal-test\n"
        "validators:\n"
        "  - validators/check_docs.py\n"
        "  - validators/check_claims.py\n",
    )
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "validators" / "check_claims.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", '{"ok": true}\n')
    _write(repo / "fixtures" / "check_docs" / "invalid_case.json", '{"ok": false}\n')
    _write(repo / "fixtures" / "check_claims" / "valid_case.json", '{"ok": true}\n')

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "positive_only_validator_fixture"
    statuses = {item.name: item.status for item in report.validators}
    assert statuses == {
        "check_docs": "validator_fixture_pair_present",
        "check_claims": "positive_only_validator_fixture",
    }


def test_fixture_manifest_expected_ok_and_rule_ids_associate_validator_fixtures(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/pcie_ltssm_json_validator.py")
    _write(repo / "validators" / "pcie_ltssm_json_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "smoke_compliant.checks.json", "{}\n")
    _write(repo / "fixtures" / "smoke_noncompliant_illegal_transition.checks.json", "{}\n")
    _write(
        repo / "fixtures" / "fixture_manifest.json",
        json.dumps(
            {
                "fixtures": [
                    {
                        "file": "smoke_compliant.checks.json",
                        "expected_ok": True,
                        "expected_rule_ids": ["common", "pcie-ltssm"],
                    },
                    {
                        "file": "smoke_noncompliant_illegal_transition.checks.json",
                        "expected_ok": False,
                        "expected_rule_ids": ["common", "pcie-ltssm"],
                    },
                ]
            }
        ),
    )

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_fixture_pair_present"
    assert report.validators[0].positive_fixtures == ["fixtures/smoke_compliant.checks.json"]
    assert report.validators[0].negative_fixtures == [
        "fixtures/smoke_noncompliant_illegal_transition.checks.json"
    ]
    assert report.validators[0].ambiguous_fixtures == []


def test_safe_alias_inference_associates_short_fixture_prefixes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/interrupt_safety_validator.py")
    _write(repo / "validators" / "interrupt_safety_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "interrupt_compliant.checks.json", "{}\n")
    _write(repo / "fixtures" / "interrupt_regression.checks.json", "{}\n")

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_fixture_pair_present"
    assert report.validators[0].positive_fixtures == ["fixtures/interrupt_compliant.checks.json"]
    assert report.validators[0].negative_fixtures == ["fixtures/interrupt_regression.checks.json"]


def test_ambiguous_fixture_matches_are_not_counted_as_fixture_pairs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(
        repo / "contract.yaml",
        "name: signal-test\n"
        "validators:\n"
        "  - validators/foo_validator.py\n"
        "  - validators/bar_validator.py\n",
    )
    _write(repo / "validators" / "foo_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "validators" / "bar_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "foo_bar_valid.checks.json", "{}\n")
    _write(repo / "fixtures" / "foo_bar_invalid.checks.json", "{}\n")

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "ambiguous_validator_fixture_match"
    assert {item.status for item in report.validators} == {"ambiguous_validator_fixture_match"}
    for item in report.validators:
        assert item.positive_fixtures == []
        assert item.negative_fixtures == []
        assert item.ambiguous_fixtures == [
            "fixtures/foo_bar_invalid.checks.json",
            "fixtures/foo_bar_valid.checks.json",
        ]
    assert "all contract validators have pass/fail fixture pairs" in report.cannot_claim


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
    assert "production_derived_expected_value candidate found" not in report.warnings
    assert "mock_only_weak_signal candidate found" not in report.warnings
    assert "time_or_random_uncontrolled candidate found" not in report.warnings
    assert "production_derived_expected_value candidate found" in report.lexical_advisories
    assert "mock_only_weak_signal candidate found" in report.lexical_advisories
    assert "time_or_random_uncontrolled candidate found" in report.lexical_advisories


def test_lexical_advisories_do_not_make_structurally_paired_report_weak(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", '{"ok": true}\n')
    _write(repo / "fixtures" / "check_docs" / "invalid_case.json", '{"ok": false}\n')
    _write(
        repo / "tests" / "test_check_docs.py",
        "def test_weak_proxy(mock_device):\n"
        "    result = {'status': 'invalid'}\n"
        "    expected = result\n"
        "    mock_device.send.assert_called_once()\n"
        "    assert result == expected\n",
    )

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_fixture_pair_present"
    assert report.overall_status == "partial"
    assert report.lexical_advisories == [
        "production_derived_expected_value candidate found",
        "mock_only_weak_signal candidate found",
    ]
    assert report.warnings == []


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
    assert "lexical_advisories" in data


def test_format_human_lists_validator_fixture_counts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "check_docs" / "valid_case.json", "{}\n")

    text = format_human(build_test_signal_quality_audit(repo))

    assert "validators:" in text
    assert "check_docs: status=positive_only_validator_fixture" in text
    assert "positive=1 negative=0" in text


def test_list_shaped_fixture_manifest_is_supported(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/ltssm_validator.py")
    _write(repo / "validators" / "ltssm_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "ltssm_case_a.checks.json", "{}\n")
    _write(repo / "fixtures" / "ltssm_case_b.checks.json", "{}\n")
    _write(
        repo / "fixtures" / "fixture_manifest.json",
        json.dumps(
            [
                {"file": "ltssm_case_a.checks.json", "expected_ok": True},
                {"file": "ltssm_case_b.checks.json", "expected_ok": False},
            ]
        ),
    )

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_fixture_pair_present"
    assert report.validators[0].positive_fixtures == ["fixtures/ltssm_case_a.checks.json"]
    assert report.validators[0].negative_fixtures == ["fixtures/ltssm_case_b.checks.json"]


def test_unparseable_fixture_manifest_reports_warning_not_crash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "fixture_manifest.json", "{not valid json")

    report = build_test_signal_quality_audit(repo)

    assert report.contract_validator_fixtures == "validator_without_fixture_harness"
    assert any("fixture manifest" in warning for warning in report.warnings)


def test_manifest_entry_without_rule_ids_falls_back_to_filename_alias(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/ltssm_validator.py")
    _write(repo / "validators" / "ltssm_validator.py", "def validate(payload):\n    return True\n")
    _write(repo / "fixtures" / "ltssm_blue.checks.json", "{}\n")
    _write(
        repo / "fixtures" / "fixture_manifest.json",
        json.dumps({"fixtures": [{"file": "ltssm_blue.checks.json", "expected_ok": False}]}),
    )

    report = build_test_signal_quality_audit(repo)

    assert report.validators[0].negative_fixtures == ["fixtures/ltssm_blue.checks.json"]
    assert report.validators[0].positive_fixtures == []
    assert report.contract_validator_fixtures == "negative_only_validator_fixture"


def test_fixture_runner_presence_is_reported_without_execution_claim(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo)
    _write(repo / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    _write(repo / "run_validators.py", "print('runner')\n")

    report = build_test_signal_quality_audit(repo)

    assert report.fixture_runner == "runner_script_present"
    assert report.fixture_runner_paths == ["run_validators.py"]
    assert "fixture runner scripts were executed or pass" in report.cannot_claim
    assert report.contract_validator_fixtures == "validator_without_fixture_harness"

    bare = tmp_path / "bare"
    _write_contract(bare)
    _write(bare / "validators" / "check_docs.py", "def validate(payload):\n    return True\n")
    assert build_test_signal_quality_audit(bare).fixture_runner == "not_found"
