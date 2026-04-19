from __future__ import annotations

import json

import governance_tools.e1b_consumer_audit as reviewer_lint
from governance_tools.e1b_consumer_audit import (
    lint_reviewer_summary_text,
    scan_reviewer_summary_text,
)


def _ids(text: str) -> set[str]:
    return {v["pattern_id"] for v in scan_reviewer_summary_text(text)}


class TestReviewerSummaryViolations:
    def test_explicit_violation_claims_are_flagged(self):
        text = (
            "這已足以 support promote。readiness 已成立，"
            "可視為穩定。"
        )
        pids = _ids(text)
        assert "R1" in pids
        assert "R2" in pids
        assert "R3" in pids

    def test_wrapped_violation_claims_are_flagged(self):
        text = (
            "看起來已經成熟很多，目前趨勢偏正向，"
            "整體狀態令人安心。"
        )
        pids = _ids(text)
        assert "R4" in pids

    def test_ambiguous_directional_hints_are_flagged(self):
        text = (
            "可作為後續升格參考，已具備進一步判讀基礎，"
            "可朝 interpretation 討論前進。"
        )
        pids = _ids(text)
        assert "R5" in pids

    def test_confidence_laundering_is_flagged(self):
        text = (
            "雖然不能直接下結論，但大致上可視為穩定；"
            "不構成正式 promote 依據，但已呈現健康訊號。"
        )
        pids = _ids(text)
        assert "R6" in pids


class TestReviewerSummaryCleanCases:
    def test_clean_observation_restatement_passes(self):
        text = (
            "Observation only: state_transition_matrix 與 repo_state_breakdown "
            "已更新。此摘要僅重述 raw observation，不做 readiness/promotion/stability 判斷。"
        )
        result = lint_reviewer_summary_text(text)
        assert result["status"] == "clean"
        assert result["violation_count"] == 0


class TestReviewerSummaryCli:
    def test_main_returns_non_clean_status_on_violation(self, monkeypatch, capsys):
        text = "readiness 已成立，可作為後續升格參考。"
        monkeypatch.setattr(reviewer_lint, "_read_text_input", lambda _path: text)
        assert reviewer_lint.main(["--input", "-", "--json"]) == 2

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["status"] == "non-clean"
        assert payload["violation_count"] >= 1

