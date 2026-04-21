from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.enumd_observe_only_probe import probe_report, run_probe


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "enumd"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_probe_report_emits_required_fields():
    sample = _load_fixture("valid_wave5")
    result = probe_report(sample, sample_id="valid_wave5")

    required = {
        "sample_id",
        "ingestion_valid",
        "boundary_status",
        "runtime_eligible_result",
        "semantic_inducement_risk",
        "consumer_misread_risk",
        "notes",
    }
    assert required <= set(result.keys())
    assert result["sample_id"] == "valid_wave5"


def test_run_probe_flags_boundary_fail_when_runtime_eligible_true(tmp_path):
    report = _load_fixture("valid_wave5")
    report["semantic_boundary"]["represents_agent_behavior"] = True
    path = tmp_path / "runtime-eligible.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    result = run_probe([path])

    assert result["batch_conclusion"] == "boundary_fail_do_not_progress"
    sample = result["samples"][0]
    assert sample["boundary_status"] == "fail"
    assert sample["runtime_eligible_result"]["pass"] is False


def test_run_probe_reports_inducement_risk_for_forbidden_authority_fixture():
    path = FIXTURES_DIR / "forbidden_authority_fields.json"
    result = run_probe([path])
    sample = result["samples"][0]

    assert sample["semantic_inducement_risk"] == "high"
    assert sample["consumer_misread_risk"] == "high"
    assert sample["sample_conclusion"] == "observe_only_with_inducement_risk"
    assert result["batch_conclusion"] == "observe_only_with_inducement_risk"


def test_probe_cli_json_output_and_file_write(tmp_path):
    output = tmp_path / "probe.json"
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/enumd_observe_only_probe.py",
            "--sample",
            str(FIXTURES_DIR / "valid_wave5.json"),
            "--sample",
            str(FIXTURES_DIR / "forbidden_authority_fields.json"),
            "--format",
            "json",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["advisory_only"] is True
    assert payload["sample_count"] == 2
    assert payload["review_required_advisory_only"] is True
    assert "review_required_sample_count" in payload
    assert "review_required_sample_ids" in payload
    assert output.is_file()


def test_node_signals_consumed_false_keeps_safe_pass_profile():
    sample = _load_fixture("looks_safe_not_tested")
    sample["nodeSignals_consumed"] = False
    sample["advisories"] = []

    result = probe_report(sample, sample_id="looks_safe_not_tested")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is False
    assert result["sample_conclusion"] == "safe_for_observe_only"


def test_node_signals_consumed_true_requires_reevaluation_without_hard_fail():
    sample = _load_fixture("looks_safe_not_tested")
    sample["nodeSignals_consumed"] = True
    sample["advisories"] = []

    result = probe_report(sample, sample_id="looks_safe_not_tested")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is True
    assert result["sample_conclusion"] == "observe_only_with_inducement_risk"
    assert "node_signals_consumed_requires_semantic_reevaluation" in result["notes"]


def test_instrumentation_major_change_triggers_advisory_not_gate_block():
    sample = _load_fixture("looks_safe_not_tested")
    sample["advisories"] = []
    sample["instrumentation_version"] = {"major": 2, "minor": 0}
    sample["instrumentation_version_baseline"] = {"major": 1, "minor": 9}

    result = probe_report(sample, sample_id="major-change")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is True
    assert result["instrumentation_version_change"]["major_changed"] is True
    assert "instrumentation_major_change_advisory" in result["notes"]


def test_instrumentation_minor_change_has_no_gate_escalation():
    sample = _load_fixture("looks_safe_not_tested")
    sample["advisories"] = []
    sample["instrumentation_version"] = {"major": 1, "minor": 2}
    sample["instrumentation_version_baseline"] = {"major": 1, "minor": 1}

    result = probe_report(sample, sample_id="minor-change")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is False
    assert result["instrumentation_version_change"]["minor_changed"] is True
    assert "instrumentation_minor_change_no_gate_escalation" in result["notes"]


def test_domain_advisory_consumed_fixture_requires_review_only():
    sample = _load_fixture("domain_advisory_consumed_advisory_case")
    result = probe_report(sample, sample_id="domain_advisory_consumed_advisory_case")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is True
    assert result["sample_conclusion"] == "observe_only_with_inducement_risk"


def test_domain_advisory_major_change_fixture_requires_review_only():
    sample = _load_fixture("domain_advisory_major_version_change_case")
    result = probe_report(sample, sample_id="domain_advisory_major_version_change_case")

    assert result["boundary_status"] == "pass"
    assert result["reevaluation_required"] is True
    assert result["instrumentation_version_change"]["major_changed"] is True
    assert result["sample_conclusion"] == "observe_only_with_inducement_risk"


def test_run_probe_emits_review_required_summary_surface():
    result = run_probe(
        [
            FIXTURES_DIR / "domain_advisory_consumed_advisory_case.json",
            FIXTURES_DIR / "domain_advisory_major_version_change_case.json",
            FIXTURES_DIR / "looks_safe_not_tested.json",
        ]
    )

    assert result["review_required_advisory_only"] is True
    assert result["review_required_sample_count"] == 2
    assert set(result["review_required_sample_ids"]) == {
        "domain_advisory_consumed_advisory_case",
        "domain_advisory_major_version_change_case",
    }
