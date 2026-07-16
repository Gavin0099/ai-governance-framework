"""Tests for governance_tools.evaluation_summary.

Agent Runtime Evaluation tranche 1, Phase 3. Locked properties: no total
score can exist; detection tiers never merge; maturity is capped at
provisional without human diversity judgment; drift marks, never resets.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from governance_tools.evaluation_summary import (
    RECEIPTS_RELPATH,
    _parse_period,
    build_summary,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)


def _write_receipt(root: Path, name: str, *, schema_version: str = "1.4",
                   days_ago: int = 1, exit_code: int = 0,
                   coarse_id: str = "rp_aaa", full_id: str = "rp_fff",
                   detection_status: str = "full",
                   sample_origin: str = "natural_task",
                   blockers: list = (), validator_signal: dict = None,
                   output_mode_decision: str = None) -> None:
    receipts_dir = root / RECEIPTS_RELPATH
    receipts_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": schema_version,
        "timestamp": (_NOW - timedelta(days=days_ago)).isoformat(),
        "agent_id": "test",
        "exit_code": exit_code,
        "runtime_profile_id": full_id,
        "runtime_profile_coarse_id": coarse_id,
        "runtime_detection_status": detection_status,
        "sample_origin": sample_origin,
        "memory_workflow_blocker_codes": list(blockers),
    }
    if validator_signal:
        payload["validator_signal"] = validator_signal
    if output_mode_decision:
        payload["output_mode_decision"] = output_mode_decision
    (receipts_dir / f"{name}.json").write_text(
        json.dumps(payload), encoding="utf-8")


class TestGrouping:
    def test_groups_split_by_coarse_id_and_origin(self, tmp_path):
        _write_receipt(tmp_path, "a1", coarse_id="rp_claude")
        _write_receipt(tmp_path, "a2", coarse_id="rp_claude")
        _write_receipt(tmp_path, "b1", coarse_id="rp_codex",
                       detection_status="partial")
        _write_receipt(tmp_path, "s1", coarse_id="rp_claude",
                       sample_origin="synthetic")
        summary = build_summary(tmp_path, 30, now=_NOW)
        keys = {(g["coarse_id"], g["model_binding"], g["sample_origin"])
                for g in summary["groups"]}
        assert ("rp_claude", "verified", "natural_task") in keys
        assert ("rp_codex", "unknown", "natural_task") in keys
        assert ("rp_claude", "verified", "synthetic") in keys
        assert summary["excluded"]["non_natural_samples"] == 1

    def test_detection_tiers_never_merge(self, tmp_path):
        # Same coarse id, one full detection and one partial: two groups.
        _write_receipt(tmp_path, "a", coarse_id="rp_x", detection_status="full")
        _write_receipt(tmp_path, "b", coarse_id="rp_x", detection_status="partial")
        summary = build_summary(tmp_path, 30, now=_NOW)
        bindings = sorted(g["model_binding"] for g in summary["groups"])
        assert bindings == ["unknown", "verified"]


class TestFinalStatus:
    def test_status_derived_from_receipt_state(self, tmp_path):
        _write_receipt(tmp_path, "ok", exit_code=0)
        _write_receipt(tmp_path, "blocked", blockers=["b1"])
        _write_receipt(tmp_path, "blocked2", output_mode_decision="block")
        _write_receipt(tmp_path, "fail", exit_code=3)
        summary = build_summary(tmp_path, 30, now=_NOW)
        counts = summary["groups"][0]["counts"]
        assert counts == {"samples": 4, "verified": 1, "blocked": 2,
                          "unproven": 1}


class TestMaturity:
    def _ladder(self, tmp_path, n, **kwargs):
        for i in range(n):
            _write_receipt(tmp_path, f"r{i}", **kwargs)
        summary = build_summary(tmp_path, 30, now=_NOW)
        return summary["groups"][0]

    @pytest.mark.parametrize("n,expected", [
        (2, "uncalibrated"),
        (3, "observed"),
        (10, "provisional"),
        (35, "provisional"),
    ])
    def test_ladder_capped_at_provisional(self, tmp_path, n, expected):
        group = self._ladder(tmp_path, n)
        assert group["maturity"] == expected

    def test_thirty_plus_samples_get_diversity_note_not_established(self, tmp_path):
        group = self._ladder(tmp_path, 30)
        assert group["maturity"] == "provisional"
        assert "human judgment" in group["task_diversity_note"]

    def test_multiple_full_ids_mark_drifted(self, tmp_path):
        _write_receipt(tmp_path, "a", full_id="rp_v1")
        _write_receipt(tmp_path, "b", full_id="rp_v1")
        _write_receipt(tmp_path, "c", full_id="rp_v2")
        group = build_summary(tmp_path, 30, now=_NOW)["groups"][0]
        assert group["maturity"] == "drifted"
        assert group["drift_events"] == 1


class TestExclusions:
    def test_pre_binding_receipts_excluded_but_counted(self, tmp_path):
        _write_receipt(tmp_path, "old", schema_version="1.3")
        _write_receipt(tmp_path, "new", schema_version="1.4")
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert summary["excluded"]["pre_binding_receipts"] == 1
        assert sum(g["counts"]["samples"] for g in summary["groups"]) == 1

    def test_unreadable_receipt_counted(self, tmp_path):
        receipts_dir = tmp_path / RECEIPTS_RELPATH
        receipts_dir.mkdir(parents=True)
        (receipts_dir / "bad.json").write_text("{oops", encoding="utf-8")
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert summary["excluded"]["unreadable_receipts"] == 1

    def test_out_of_window_receipts_ignored(self, tmp_path):
        _write_receipt(tmp_path, "recent", days_ago=5)
        _write_receipt(tmp_path, "ancient", days_ago=90)
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert sum(g["counts"]["samples"] for g in summary["groups"]) == 1

    def test_empty_repo_yields_legal_empty_summary(self, tmp_path):
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert summary["groups"] == []


class TestRatesAndSignals:
    def test_rates_null_when_no_validator_data(self, tmp_path):
        _write_receipt(tmp_path, "a")
        rates = build_summary(tmp_path, 30, now=_NOW)["groups"][0]["rates"]
        assert rates["validator_execution_rate"] is None
        assert rates["validator_pass_rate"] is None
        assert rates["evidence_completeness_rate"] == 1.0

    def test_validator_signal_tiers_counted(self, tmp_path):
        _write_receipt(tmp_path, "a", validator_signal={
            "tier": "test_backed", "tier_source": "r-v1"})
        _write_receipt(tmp_path, "b", validator_signal={
            "tier": "structural_only", "tier_source": "r-v1"})
        _write_receipt(tmp_path, "c")
        tiers = build_summary(tmp_path, 30, now=_NOW)["groups"][0][
            "validator_signal_tiers"]
        assert tiers["test_backed"] == 1
        assert tiers["structural_only"] == 1

    def test_unknown_detection_ratio(self, tmp_path):
        _write_receipt(tmp_path, "a", detection_status="unknown",
                       coarse_id="unknown")
        _write_receipt(tmp_path, "b", detection_status="unknown",
                       coarse_id="unknown")
        group = build_summary(tmp_path, 30, now=_NOW)["groups"][0]
        assert group["rates"]["unknown_detection_ratio"] == 1.0


class TestLockedProperties:
    def test_no_total_score_anywhere(self, tmp_path):
        for i in range(5):
            _write_receipt(tmp_path, f"r{i}")
        dump = json.dumps(build_summary(tmp_path, 30, now=_NOW)).lower()
        for forbidden in ("total_score", "overall_score", "ranking", '"score"'):
            assert forbidden not in dump

    def test_generator_declares_zero_llm_calls(self, tmp_path):
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert summary["generator"]["llm_calls"] == 0

    def test_summary_conforms_to_schema_shape(self, tmp_path):
        schema = json.loads(
            (_REPO_ROOT / "schemas" / "evaluation_summary.schema.json")
            .read_text(encoding="utf-8"))
        _write_receipt(tmp_path, "a")
        _write_receipt(tmp_path, "drift", full_id="rp_other")
        summary = build_summary(tmp_path, 30, now=_NOW)
        assert set(summary) <= set(schema["properties"])
        for key in schema["required"]:
            assert key in summary
        group_spec = schema["properties"]["groups"]["items"]
        for group in summary["groups"]:
            assert set(group) <= set(group_spec["properties"])
            for key in group_spec["required"]:
                assert key in group
            assert group["maturity"] in group_spec["properties"]["maturity"]["enum"]
            assert (group["model_binding"]
                    in group_spec["properties"]["model_binding"]["enum"])


class TestCli:
    def test_cli_writes_and_prints(self, tmp_path, capsys):
        _write_receipt(tmp_path, "a", days_ago=0)
        out = tmp_path / "summary.json"
        assert main(["--repo", str(tmp_path), "--period", "30d",
                     "--out", str(out)]) == 0
        assert "no total score by design" in capsys.readouterr().out
        payload = json.loads(out.read_bytes().decode("utf-8"))
        assert payload["schema_version"] == "1.0"

    def test_bad_period_rejected(self, tmp_path, capsys):
        assert main(["--repo", str(tmp_path), "--period", "monthly"]) == 2
        assert "error" in capsys.readouterr().out

    def test_parse_period(self):
        assert _parse_period("30d") == 30
        with pytest.raises(ValueError):
            _parse_period("0d")
