from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance_tools.skill_ab_scorer import (
    FrozenBundleError,
    format_human,
    main,
    score_experiment,
    score_findings,
    validate_frozen_bundle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN = "docs/governance/skill-ab-codex-review-fast.frozen.json"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_frozen_bundle_hashes_match_repo_materials() -> None:
    frozen = validate_frozen_bundle(FROZEN, REPO_ROOT)

    assert frozen["status"] == "step1_frozen_materials"
    assert frozen["controls"]["a_b_runs_completed"] is False
    assert frozen["controls"]["ledger_decision_effect_updated"] is False


def test_scores_line_alias_anchor_fp_and_unscored_findings(tmp_path: Path) -> None:
    findings = tmp_path / "run-a1.json"
    _write_json(
        findings,
        {
            "run_id": "run-a1",
            "findings": [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 13,
                    "type": "comparison-boundary",
                    "text": "risk_score >= policy.max_risk allows the boundary",
                },
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 99,
                    "type": "guard-removed",
                    "text": "request.owner_approved or not policy.require_owner bypasses blocked state",
                },
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 24,
                    "type": "naming",
                    "text": "summarize_recent could be named differently",
                },
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 80,
                    "type": "style",
                    "text": "not in seed or allowlist",
                },
            ],
        },
    )

    result = score_findings(FROZEN, findings, REPO_ROOT)

    assert result.TP == 2
    assert result.FN == 4
    assert result.FP == 1
    assert result.recall == 2 / 6
    assert result.precision == 2 / 3
    dispositions = [item.disposition for item in result.scored_findings]
    assert dispositions == ["TP", "TP", "FP", "unscored"]
    assert result.matched_defects == ["D1", "D3"]
    assert "D2" in result.missed_defects


def test_aggregate_scoring_applies_frozen_decision_rule(tmp_path: Path) -> None:
    paths: list[Path] = []

    def write_run(name: str, condition: str, findings: list[dict[str, object]]) -> None:
        path = tmp_path / f"{name}.json"
        _write_json(path, {"run_id": name, "condition": condition, "findings": findings})
        paths.append(path)

    for index in range(3):
        write_run(
            f"a{index}",
            "A",
            [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 13,
                    "type": "boundary-flip",
                    "text": "risk_score >= policy.max_risk",
                }
            ],
        )
        write_run(
            f"b{index}",
            "B",
            [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 13,
                    "type": "boundary-flip",
                    "text": "risk_score >= policy.max_risk",
                },
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 16,
                    "type": "reversed-condition",
                    "text": "request.user_is_admin now denies admins",
                },
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 26,
                    "type": "off-by-one",
                    "text": "limit + 1 selects too many results",
                },
            ],
        )

    result = score_experiment(FROZEN, paths, REPO_ROOT)

    assert result.mean_recall_A == 1 / 6
    assert result.mean_recall_B == 3 / 6
    assert result.mean_precision_A == 1.0
    assert result.mean_precision_B == 1.0
    assert result.delta_recall == pytest.approx(2 / 6)
    assert result.delta_precision == 0
    assert result.decision_effect == "positive"


def test_precision_is_na_when_no_findings_match_or_hit_allowlist(tmp_path: Path) -> None:
    findings = tmp_path / "empty.json"
    _write_json(findings, {"run_id": "empty", "findings": []})

    result = score_findings(FROZEN, findings, REPO_ROOT)

    assert result.TP == 0
    assert result.FN == 6
    assert result.FP == 0
    assert result.precision is None
    assert result.to_dict()["precision"] == "n/a"


def test_hash_mismatch_aborts_scoring(tmp_path: Path) -> None:
    frozen_payload = json.loads((REPO_ROOT / FROZEN).read_text(encoding="utf-8"))
    frozen_payload["hashes"]["target_diff_sha256"] = "0" * 64
    frozen = tmp_path / "bad-frozen.json"
    _write_json(frozen, frozen_payload)

    try:
        validate_frozen_bundle(frozen, REPO_ROOT)
    except FrozenBundleError as exc:
        assert "frozen_bundle_hash_mismatch" in str(exc)
    else:
        raise AssertionError("expected FrozenBundleError")


def test_cli_outputs_json_and_human(tmp_path: Path, capsys) -> None:
    findings = tmp_path / "run-b1.json"
    _write_json(
        findings,
        {
            "run_id": "run-b1",
            "findings": [
                {
                    "file": "skill_ab_target/review_target.py",
                    "line": 26,
                    "type": "loop-bound-error",
                    "text": "limit + 1 selects too many results",
                }
            ],
        },
    )

    assert main(["--repo", str(REPO_ROOT), "--frozen", FROZEN, "--findings", str(findings), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["valid"] is True
    assert data["TP"] == 1
    assert data["matched_defects"] == ["D4"]

    assert main(["--repo", str(REPO_ROOT), "--frozen", FROZEN, "--findings", str(findings), "--format", "human"]) == 0
    text = capsys.readouterr().out
    assert "[skill_ab_scorer]" in text
    assert "claim_boundary=" in text
    assert "cannot_claim:" in text


def test_format_human_preserves_non_claims(tmp_path: Path) -> None:
    findings = tmp_path / "run-c1.json"
    _write_json(findings, {"run_id": "run-c1", "findings": []})

    text = format_human(score_findings(FROZEN, findings, REPO_ROOT))

    assert "A/B experiment has been run" in text
    assert "ledger decision_effect is ready to update" in text
