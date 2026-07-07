from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.consumer_fixture_runner import build_consumer_fixture_report, main, report_to_dict


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_contract(repo: Path, *validator_paths: str) -> None:
    lines = ["name: fixture-runner-test", "validators:"]
    for path in validator_paths:
        lines.append(f"  - {path}")
    _write(repo / "contract.yaml", "\n".join(lines) + "\n")


def _write_validator(repo: Path, rel_path: str, class_name: str, rule_id: str, fail_key: str = "fail") -> None:
    _write(
        repo / rel_path,
        "from governance_tools.validator_interface import DomainValidator, ValidatorResult\n"
        f"class {class_name}(DomainValidator):\n"
        "    @property\n"
        "    def rule_ids(self):\n"
        f"        return ['{rule_id}']\n"
        "    def validate(self, payload):\n"
        f"        ok = not bool(payload.get('checks', {{}}).get('{fail_key}'))\n"
        "        return ValidatorResult(\n"
        "            ok=ok,\n"
        "            rule_ids=self.rule_ids,\n"
        "            violations=[] if ok else ['fixture failed'],\n"
        "            evidence_summary='fixture validator ran',\n"
        "        )\n",
    )


def _write_manifest(repo: Path, fixtures: list[dict]) -> None:
    _write(repo / "fixtures" / "fixture_manifest.json", json.dumps({"fixtures": fixtures}))


def test_runner_matches_expected_true_and_false(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_validator.py")
    _write_validator(repo, "validators/refactor_validator.py", "RefactorValidator", "refactor")
    _write(repo / "fixtures" / "refactor_good.checks.json", "{}\n")
    _write(repo / "fixtures" / "refactor_bad.checks.json", '{"fail": true}\n')
    _write_manifest(
        repo,
        [
            {"file": "refactor_good.checks.json", "expected_ok": True, "expected_rule_ids": ["refactor"]},
            {"file": "refactor_bad.checks.json", "expected_ok": False, "expected_rule_ids": ["refactor"]},
        ],
    )

    report = build_consumer_fixture_report(repo)
    payload = report_to_dict(report)

    assert payload["schema"] == "consumer_fixture_runner.v0.1"
    assert payload["status"] == "report_only"
    assert payload["overall_status"] == "all_expected"
    assert payload["fixtures_total"] == 2
    assert payload["observations_total"] == 2
    assert payload["matched_expectations"] == 2
    assert payload["mismatched_expectations"] == 0
    assert {item["expected_ok"] for item in payload["observations"]} == {True, False}
    assert all(item["matched"] for item in payload["observations"])
    assert "test suite is industry-grade" in payload["cannot_claim"]


def test_runner_reports_mismatch_without_failing_gate(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_validator.py")
    _write_validator(repo, "validators/refactor_validator.py", "RefactorValidator", "refactor")
    _write(repo / "fixtures" / "refactor_bad.checks.json", '{"fail": true}\n')
    _write_manifest(
        repo,
        [{"file": "refactor_bad.checks.json", "expected_ok": True, "expected_rule_ids": ["refactor"]}],
    )

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "mismatch"
    assert report.observations_total == 1
    assert report.mismatched_expectations == 1
    assert report.observations[0]["observed_ok"] is False
    assert report.observations[0]["matched"] is False


def test_runner_reports_missing_validator(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/missing_validator.py")
    _write(repo / "fixtures" / "case.checks.json", "{}\n")
    _write_manifest(repo, [{"file": "case.checks.json", "expected_ok": True, "expected_rule_ids": ["missing"]}])

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "error"
    assert any("validator_load_error" in error for error in report.errors)


def test_runner_reports_invalid_fixture_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_validator.py")
    _write_validator(repo, "validators/refactor_validator.py", "RefactorValidator", "refactor")
    _write(repo / "fixtures" / "refactor_bad.checks.json", "{not-json")
    _write_manifest(
        repo,
        [{"file": "refactor_bad.checks.json", "expected_ok": False, "expected_rule_ids": ["refactor"]}],
    )

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "error"
    assert report.observations_total == 0
    assert "fixture_load_error: fixtures/refactor_bad.checks.json" in report.errors


def test_ambiguous_alias_fallback_is_not_counted_as_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/foo_validator.py", "validators/bar_validator.py")
    _write_validator(repo, "validators/foo_validator.py", "FooValidator", "foo")
    _write_validator(repo, "validators/bar_validator.py", "BarValidator", "bar")
    _write(repo / "fixtures" / "foo_bar_valid.checks.json", "{}\n")
    _write_manifest(repo, [{"file": "foo_bar_valid.checks.json", "expected_ok": True}])

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "error"
    assert report.observations_total == 0
    assert any("ambiguous_fixture_validator_match" in warning for warning in report.warnings)


def test_expected_rule_ids_route_to_one_validator_among_many(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/foo_validator.py", "validators/bar_validator.py")
    _write_validator(repo, "validators/foo_validator.py", "FooValidator", "foo")
    _write_validator(repo, "validators/bar_validator.py", "BarValidator", "bar")
    _write(repo / "fixtures" / "neutral.checks.json", "{}\n")
    _write_manifest(repo, [{"file": "neutral.checks.json", "expected_ok": True, "expected_rule_ids": ["bar"]}])

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "all_expected"
    assert report.observations_total == 1
    assert report.observations[0]["validator"] == "bar_validator"
    assert report.observations[0]["route"] == "expected_rule_ids"


def test_expected_rule_ids_do_not_fall_back_to_alias_when_unmatched(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_evidence_validator.py")
    _write_validator(repo, "validators/refactor_evidence_validator.py", "RefactorEvidenceValidator", "refactor")
    _write(repo / "fixtures" / "driver_evidence_violation.checks.json", '{"fail": true}\n')
    _write_manifest(
        repo,
        [{"file": "driver_evidence_violation.checks.json", "expected_ok": False, "expected_rule_ids": ["driver"]}],
    )

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "error"
    assert report.observations_total == 0
    assert "fixture_unmatched: fixtures/driver_evidence_violation.checks.json" in report.warnings


def test_runner_reports_manifest_missing_when_check_fixtures_exist(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_validator.py")
    _write_validator(repo, "validators/refactor_validator.py", "RefactorValidator", "refactor")
    _write(repo / "fixtures" / "refactor_good.checks.json", "{}\n")

    report = build_consumer_fixture_report(repo)

    assert report.overall_status == "manifest_missing"
    assert report.fixtures_total == 0
    assert report.observations_total == 0
    assert any("fixture_manifest_missing" in warning for warning in report.warnings)
    assert not report.errors


def test_cli_human_and_json_outputs_are_report_only(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    _write_contract(repo, "validators/refactor_validator.py")
    _write_validator(repo, "validators/refactor_validator.py", "RefactorValidator", "refactor")
    _write(repo / "fixtures" / "refactor_good.checks.json", "{}\n")
    _write_manifest(
        repo,
        [{"file": "refactor_good.checks.json", "expected_ok": True, "expected_rule_ids": ["refactor"]}],
    )

    assert main(["--repo", str(repo), "--format", "human"]) == 0
    human = capsys.readouterr().out
    assert "[consumer_fixture_runner]" in human
    assert "status=report_only" in human
    assert "overall_status=all_expected" in human
    assert "cannot_claim:" in human

    assert main(["--repo", str(repo), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "report_only"
    assert payload["overall_status"] == "all_expected"
