from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.skill_ab_blind_adapter import main, score_blind_experiment


REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN = "docs/governance/skill-ab-codex-review-fast.frozen.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_blind_adapter_uses_hidden_condition_map(tmp_path: Path) -> None:
    b_path = tmp_path / "R01.json"
    a_path = tmp_path / "R02.json"
    condition_map = tmp_path / "condition-map.json"
    _write_json(
        b_path,
        {
            "run_id": "R01",
            "findings": [
                {
                    "file": "skill_ab_target/tests/test_review_target.py",
                    "line": 11,
                    "type": "test-gap",
                    "text": "The new test only covers the happy path",
                }
            ],
        },
    )
    _write_json(
        a_path,
        {
            "run_id": "R02",
            "findings": [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 26,
                    "type": "off-by-one",
                    "text": "limit + 1 selects too many results",
                }
            ],
        },
    )
    _write_json(
        condition_map,
        {
            "shuffle_order": ["R01", "R02"],
            "runs": [
                {"run_id": "R01", "condition": "B", "source_run_id": "B2"},
                {"run_id": "R02", "condition": "A", "source_run_id": "A1"},
            ],
        },
    )

    result = score_blind_experiment(FROZEN, [b_path, a_path], condition_map, REPO_ROOT)

    assert result["controls"]["condition_labels_stripped_before_scoring"] is True
    assert result["controls"]["hidden_condition_map_kept_out_of_scorer_input"] is True
    assert result["scoring_order"] == ["R01", "R02"]
    assert result["run_table"][0]["condition"] == "B"
    assert result["aggregates"]["mean_recall_A"] == 1 / 6
    assert result["aggregates"]["mean_recall_B"] == 1 / 6


def test_blind_adapter_rejects_condition_labels_in_findings(tmp_path: Path) -> None:
    findings = tmp_path / "R01.json"
    condition_map = tmp_path / "condition-map.json"
    _write_json(findings, {"run_id": "R01", "condition": "B", "findings": []})
    _write_json(
        condition_map,
        {
            "shuffle_order": ["R01"],
            "runs": [{"run_id": "R01", "condition": "B"}],
        },
    )

    with pytest.raises(ValueError, match="must not contain condition labels"):
        score_blind_experiment(FROZEN, [findings, findings], condition_map, REPO_ROOT)


def test_blind_adapter_cli_writes_corrected_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    b_path = tmp_path / "R01.json"
    a_path = tmp_path / "R02.json"
    condition_map = tmp_path / "condition-map.json"
    reference_result = tmp_path / "reference-result.json"
    output = tmp_path / "result-blind.json"
    _write_json(
        b_path,
        {
            "run_id": "R01",
            "findings": [
                {
                    "file": "skill_ab_target/tests/test_review_target.py",
                    "line": 11,
                    "type": "test-gap",
                    "text": "The new test only covers the happy path",
                }
            ],
        },
    )
    _write_json(
        a_path,
        {
            "run_id": "R02",
            "findings": [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 26,
                    "type": "off-by-one",
                    "text": "limit + 1 selects too many results",
                }
            ],
        },
    )
    _write_json(
        condition_map,
        {
            "shuffle_order": ["R01", "R02"],
            "runs": [
                {"run_id": "R01", "condition": "B"},
                {"run_id": "R02", "condition": "A"},
            ],
        },
    )
    _write_json(
        reference_result,
        {
            "aggregates": {
                "mean_recall_A": 1 / 6,
                "mean_recall_B": 1 / 6,
                "mean_precision_A": 1.0,
                "mean_precision_B": 1.0,
                "delta_recall": 0.0,
                "delta_precision": 0.0,
                "decision_effect": "none",
            }
        },
    )

    exit_code = main(
        [
            "--repo",
            str(REPO_ROOT),
            "--frozen",
            FROZEN,
            "--condition-map",
            str(condition_map),
            "--findings",
            str(b_path),
            str(a_path),
            "--reference-result",
            str(reference_result),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "skill_ab_blind_result.v0.1" in captured.out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reproduction"]["decision_effect_matches_reference"] is True
    assert payload["controls"]["ledger_decision_effect_updated"] is False
