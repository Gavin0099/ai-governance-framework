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
    assert output.is_file()
