from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from governance_tools.reviewer_linter_calibration_summary import (
    build_calibration_summary,
    format_human_summary,
)


def test_build_calibration_summary_default_dataset_has_no_critical_hotspots():
    dataset = json.loads(
        Path("tests/fixtures/reviewer_linter_calibration_dataset.json").read_text(
            encoding="utf-8"
        )
    )
    summary = build_calibration_summary(dataset)
    assert summary["advisory_only"] is True
    assert summary["dataset_case_count"] >= 1
    assert summary["hotspots"]["high_risk_missing_subtle_coverage"] == []


def test_build_calibration_summary_detects_sparse_and_missing_subtle():
    dataset = [
        {
            "id": "p1",
            "semantic_family": "promotion",
            "ambiguity_tier": "tier_a_explicit",
            "surface_type": "summary_sentence",
            "expected_status": "non-clean",
            "text": "support promote",
            "must_include_claim_types": ["promotion_claim"],
        },
        {
            "id": "s1",
            "semantic_family": "safe_disclaimer",
            "ambiguity_tier": "tier_a_explicit",
            "surface_type": "summary_sentence",
            "expected_status": "clean",
            "text": "does not support readiness",
            "must_exclude_claim_types": ["readiness_claim"],
        },
    ]
    summary = build_calibration_summary(dataset)
    assert "promotion" in summary["hotspots"]["high_risk_missing_subtle_coverage"]
    assert "promotion" in summary["hotspots"]["sparse_families"]


def test_format_human_summary_contains_hotspot_section():
    summary = {
        "advisory_only": True,
        "dataset_case_count": 2,
        "overall_case_fail_count": 0,
        "families": {"promotion": {"sample_count": 2, "surface_count": 2, "tier_distribution": {"tier_a_explicit": 1, "tier_c_subtle": 1}, "case_fail_count": 0}},
        "hotspots": {
            "sparse_families": [],
            "high_risk_missing_subtle_coverage": [],
            "failing_families": [],
        },
    }
    rendered = format_human_summary(summary)
    assert "[reviewer_linter_calibration_summary]" in rendered
    assert "[hotspots]" in rendered


def test_calibration_summary_cli_supports_json_and_output(tmp_path):
    output = tmp_path / "summary.json"
    result = subprocess.run(
        [
            sys.executable,
            "governance_tools/reviewer_linter_calibration_summary.py",
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
    assert output.is_file()
