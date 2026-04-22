from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from governance_tools.enumd_observe_only_probe import format_human, probe_report, run_probe
from integrations.enumd.enumd_adapter import adapt_enumd_report
from integrations.enumd.ingestor import ingest


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "enumd"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _write_report(tmp_path: Path, report: dict) -> Path:
    report_path = tmp_path / "governance_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def _run_authority_upgrade_chain(tmp_path: Path, fixture_name: str) -> dict:
    report = copy.deepcopy(_load_fixture(fixture_name))
    report.setdefault("gate_result", "pass")
    report_path = _write_report(tmp_path, report)

    ingested = ingest(report_path, repo_root=tmp_path, dry_run=True)
    assert ingested["ok"] is True, ingested["errors"]

    envelope = adapt_enumd_report(report)
    sample = probe_report(report, sample_id=fixture_name)
    batch = run_probe([report_path])
    human = format_human(batch)

    return {
        "report": report,
        "ingested": ingested,
        "canonical": ingested["observation"],
        "envelope": envelope,
        "sample": sample,
        "batch": batch,
        "human": human,
    }


@pytest.mark.parametrize(
    "fixture_name",
    [
        "authority_upgrade_unconsumed_no_change_case",
        "authority_upgrade_consumed_no_change_case",
        "authority_upgrade_consumed_major_version_case",
    ],
)
def test_authority_upgrade_metadata_survives_transfer_chain(tmp_path: Path, fixture_name: str) -> None:
    result = _run_authority_upgrade_chain(tmp_path, fixture_name)
    report = result["report"]
    canonical = result["canonical"]
    envelope = result["envelope"]
    sample = result["sample"]

    payload = canonical["payload"]
    assert payload["event_name"] == report["event_name"]
    assert payload["event_channel"] == report["event_channel"]
    assert payload["nodeSignals_consumed"] is report["nodeSignals_consumed"]
    assert payload["instrumentation_version"] == report["instrumentation_version"]
    assert payload["instrumentation_version_baseline"] == report["instrumentation_version_baseline"]
    assert payload["gate_result"] == "pass"

    provenance = envelope["enumd_provenance"]
    assert provenance["nodeSignals_consumed"] is report["nodeSignals_consumed"]
    assert provenance["instrumentation_version"] == report["instrumentation_version"]
    assert provenance["event_metadata"]["event_name"] == report["event_name"]
    assert provenance["event_metadata"]["event_channel"] == report["event_channel"]
    assert provenance["event_metadata"]["run_type"] == report["run_type"]
    assert provenance["event_metadata"]["observation_type"] == report["observation_type"]
    assert provenance["event_metadata"]["semantic_scope"] == report["semantic_scope"]

    assert envelope["source"]["source_id"] == f"enumd:{report['run_id']}"
    assert envelope["source"]["source_type"] == "enumd_governance_report"
    assert envelope["observation"]["evidence_refs"] == [f"enumd-run:{report['run_id']}"]

    assert sample["event_metadata"]["event_name"] == report["event_name"]
    assert sample["event_metadata"]["event_channel"] == report["event_channel"]
    assert sample["source_provenance"]["run_id"] == report["run_id"]
    assert sample["source_provenance"]["source_id"] == f"enumd:{report['run_id']}"
    assert sample["source_provenance"]["evidence_refs"] == [f"enumd-run:{report['run_id']}"]


def test_consumed_no_change_stays_review_required_but_not_semantic_candidate_e2e(tmp_path: Path) -> None:
    result = _run_authority_upgrade_chain(tmp_path, "authority_upgrade_consumed_no_change_case")
    sample = result["sample"]
    human = result["human"].lower()

    assert sample["reevaluation_required"] is True
    assert sample["semantic_shift_candidate"] is False
    assert sample["semantic_shift_candidate_reasons"] == []
    assert sample["boundary_status"] == "pass"
    assert sample["sample_conclusion"] == "observe_only_with_inducement_risk"
    assert "escalated" not in human
    assert "blocked" not in human
    assert "boundary_fail_do_not_progress" not in human


def test_consumed_major_change_stays_candidate_only_without_hard_fail_e2e(tmp_path: Path) -> None:
    result = _run_authority_upgrade_chain(tmp_path, "authority_upgrade_consumed_major_version_case")
    sample = result["sample"]
    batch = result["batch"]
    human = result["human"].lower()

    assert sample["reevaluation_required"] is True
    assert sample["semantic_shift_candidate"] is True
    assert sample["semantic_shift_candidate_reasons"] == ["instrumentation_major_change"]
    assert sample["boundary_status"] == "pass"
    assert sample["instrumentation_version_change"]["major_changed"] is True
    assert batch["batch_conclusion"] == "observe_only_with_inducement_risk"
    assert sample["sample_conclusion"] == "observe_only_with_inducement_risk"
    assert "escalated" not in human
    assert "blocked" not in human
    assert "fail" not in human
